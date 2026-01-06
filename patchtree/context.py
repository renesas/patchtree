from __future__ import annotations
from typing import TYPE_CHECKING, IO, TextIO, cast

import yaml

from argparse import Namespace
from pathlib import Path
from zipfile import is_zipfile
from os import path, environ
from sys import stdout
from subprocess import run
from logging import Logger, getLogger as get_logger

from yaml.events import DocumentEndEvent
from yaml.nodes import MappingNode, ScalarNode

from .diff import File
from .spec import (
    LiteralInputSpec,
    PatchsetFileInputSpec,
    ProcessInputSpec,
    TargetFileInputSpec,
)
from .target import Target
from .fs import FS, PERM_EXEC, DiskFS, ZipFS, MODE_FILE

if TYPE_CHECKING:
    from .config import Config, Header


class PatchspecLoader(yaml.Loader):
    """
    YAML loader for patch specifications.
    """

    patch: File
    """File content to parse."""

    input: Path
    """Path to file content."""

    context: Context
    """Parent context."""

    input_specs: list[ProcessInputSpec] = []
    """List of inputs used by this patch specification."""

    @staticmethod
    def tag_file_target(loader: PatchspecLoader, node: ScalarNode) -> TargetFileInputSpec:
        target_root = loader.input.parent.relative_to(loader.context.root)
        path = loader.construct_scalar(node)
        if len(path) == 0:
            path = loader.input.name
        spec = TargetFileInputSpec(path=target_root.joinpath(Path(path)))
        loader.input_specs.append(spec)
        return spec

    @staticmethod
    def tag_file_input(loader: PatchspecLoader, node: ScalarNode) -> PatchsetFileInputSpec:
        input_root = loader.input.parent
        path = loader.construct_scalar(node)
        if len(path) == 0:
            path = loader.input.name
        spec = PatchsetFileInputSpec(path=input_root.joinpath(Path(path)))
        loader.input_specs.append(spec)
        return spec

    @staticmethod
    def tag_patchspec(loader: PatchspecLoader, node: MappingNode) -> Target:
        data = loader.construct_mapping(node, deep=True)
        target_cls = loader.context.config.target
        target = target_cls(
            loader.context, loader.input.relative_to(loader.context.root), data
        )
        target.inputs += loader.input_specs
        return target

    def __init__(self, context: Context, patch: File, input: Path):
        self.context = context
        self.patch = patch
        self.input = input

        super().__init__(self.patch.get_str())

        self.add_constructor("!patchspec", self.tag_patchspec)
        self.add_constructor("!target", self.tag_file_target)
        self.add_constructor("!input", self.tag_file_input)

    def parse(self) -> Target:
        """
        Read the provided patch content and return a valid Target.

        This method will raise an exception if the provided input is not a patchspec.
        This method also removes the patchspec YAML header from the input patch file's content
        if a valid patchspec was read.
        """
        try:
            data = self.get_data()
            if not isinstance(data, Target):
                raise Exception("provided yaml is not a patchspec")

            # strip frontmatter from input content if it exists
            events = yaml.parse(self.patch.get_str())
            end = next(ev for ev in events if isinstance(ev, DocumentEndEvent))
            self.patch.content = self.patch.get_str()[end.end_mark.index :].lstrip()

            return data
        finally:
            self.dispose()


class Context:
    """Global app context / state holder."""

    inputs: list[Path] = []
    """A list of patchset inputs (relative to the current working directory)."""

    root: Path
    """
    Patchset root folder. All patchset input paths will be treated relative to this folder.

    .. note::

       The ``root`` member only changes the appearance of paths. All internal logic uses the "real" paths.
    """

    header: Header
    """Patch header instance."""

    content: list[Target] = []
    """Patch targets (content)."""

    target_fs: FS
    """Target file system interface."""

    patchset_fs: FS
    """Target file system interface."""

    in_place: bool
    """Whether to apply the changes directly to the target instead of outputting the .patch file."""

    config: Config
    """Configuration class instance."""

    log: Logger
    """Global log instance reference."""

    is_empty: bool = False
    """Whether the output patch delta does not include any changes. Updated by :any:`make_patch`."""

    output: IO
    """Output IO stream used to write output patch to."""

    def __init__(self, config: Config, options: Namespace):
        self.config = config
        self.log = get_logger(self.__class__.__name__)

        self.root = options.root
        self.in_place = options.in_place

        # NOTE: this should NOT be options.root because input filenames are treated as relative
        # to the working directory by default (i.e. --root applies *after* the inputs are
        # collected)
        self.patchset_fs = DiskFS(Path("."))
        self.target_fs = self._get_target_fs(options.target)

        self.inputs = self.collect_inputs(options)
        self.content = self.collect_targets(self.inputs)

        self.output = self._get_output(options)
        self.header = config.header(config, self)

    def collect_inputs(self, options: Namespace) -> list[Path]:
        """
        Collect a list of patchset inputs depending on the globbing, patchset root and provided input path(s).
        """
        inputs: set[Path] = set()

        if len(options.patch) == 0 and options.root is not None:
            options.glob = True
            options.patch = [str(Path(options.root).joinpath("**"))]

        if options.glob:
            for pattern in options.patch:
                for path in Path(".").glob(pattern):
                    if not path.is_file():
                        continue
                    inputs.add(path)
            return sorted(inputs)
        else:
            for input in options.patch:
                path = Path(input)
                if not path.exists():
                    raise Exception(f"cannot open `{input}'")
                if not path.is_file():
                    raise Exception(f"not a file: `{input}'")
                inputs.add(path)
            return list(inputs)

    def create_target(self, input: Path, meta_inputs: list[Path] = []) -> Target:
        """Create a target instance from an input path."""
        file = input.relative_to(self.root)
        target: Target | None = None
        patch = self.patchset_fs.get_file(PatchsetFileInputSpec(path=input))
        target_cls = self.config.target

        try:
            patch.get_str()
        except:
            # binary files can't be patchspecs
            target = target_cls(self, file)

        # if the input is a yaml file, try to load it
        if target is None and input.suffix in self.config.patchspec_extensions:
            try:
                loader = PatchspecLoader(self, patch, input.parent.joinpath(input.stem))
                target = loader.parse()
                self.log.info(f"found direct yaml patchspec: {input}")
            except Exception as e:
                self.log.error(f"while parsing patchspec for {input}: {e}")
                raise e

        # try to load any frontmatter if we still don't have a target
        if target is None:
            try:
                loader = PatchspecLoader(self, patch, input)
                target = loader.parse()
                self.log.info(f"found frontmatter patchspec: {input}")
            except Exception as e:
                # exceptions while parsing frontmatter can be ignored silently since not all
                # files will have them
                target = None

        if target is None:
            self.log.info(f"treating as literal input: {input}")
            target = target_cls(self, file)

        target.patch = patch

        for input in (i.path for i in target.inputs if isinstance(i, PatchsetFileInputSpec)):
            meta_inputs.append(input)

        return target

    def collect_targets(self, inputs: list[Path]) -> list[Target]:
        """
        Create a list of targets and automatically resolve any patchspec naming conflicts.

        This function creates a list of targets from the input paths, and ensures no standalone
        patchspecs or files referenced as inputs by any patchspecs are still treated as literal
        inputs.

        :returns:
            List of targets to process for final clean patch.
        """

        meta_inputs: set[Path] = set()
        targets: dict[Path, Target] = {}

        for input in inputs:
            meta = []
            targets[input] = self.create_target(input, meta)
            meta_inputs.update(meta)

        missing = meta_inputs - set(inputs)
        if len(missing) > 0:
            for input in missing:
                self.log.error(f"{str(input)} referenced by patchspec but not in inputs")
            raise Exception("missing files")

        # files referenced as meta inputs shouldn't be treated as verbatim files
        for key in meta_inputs:
            if key not in targets:
                continue
            del targets[key]

        return sorted(targets.values(), key=lambda target: target.file)

    def get_file(self, spec: ProcessInputSpec) -> File:
        if isinstance(spec, LiteralInputSpec):
            return File(content=spec.content, mode=MODE_FILE)
        elif isinstance(spec, TargetFileInputSpec):
            return self.target_fs.get_file(spec)
        elif isinstance(spec, PatchsetFileInputSpec):
            return self.patchset_fs.get_file(spec)

        raise Exception(f"unable to read file: {spec}")

    def _get_target_fs(self, target: Path) -> FS:
        """
        Open the selected target, taking into account the --in-place option.

        :returns: Target filesystem interface.
        """
        if not target.exists():
            raise Exception(f"cannot open `{target}'")

        if path.isdir(target):
            return DiskFS(target)

        if is_zipfile(target):
            if self.in_place:
                raise Exception("cannot edit zip in-place!")
            return ZipFS(target)

        raise Exception(f"cannot read `{target}'")

    def _get_output(self, options: Namespace) -> IO:
        """
        Open the output stream, taking into account the --in-place and --out options.

        :returns: Output stream.
        """
        if options.in_place:
            if options.out is not None:
                self.log.warning("--out is ignored when using --in-place")
            return TextIO()

        if options.out is not None:
            if options.out == "-":
                return stdout
            else:
                return open(options.out, "w+")

        return stdout

    def get_apply_cmd(self) -> list[str]:
        """
        Create a command argument vector for applying the current patch.

        :returns: Command argument vector.
        """

        cmd = ["git", "apply"]
        if self.is_empty:
            cmd.append("--allow-empty")
        if self.config.diff_context == 0:
            cmd.append("--unidiff-zero")
        return cmd

    def make_patch(self) -> str:
        """
        Generate a clean patch using the header configuration and deltas from all targets.

        :returns:
          Clean patch contents
        """
        patch = ""
        for target in self.content:
            patch += target.write()

        self.is_empty = len(patch) == 0

        patch = self.header.write() + patch

        # patch must have a trailing newline
        patch += "\n"
        return patch

    def apply(self, reverse: bool) -> None:
        """
        Apply the patch in ``self.output`` and update the cache or reverse the patch in the cache.
        """

        location = cast(DiskFS, self.target_fs).target
        cache = location.joinpath(".patchtree.diff")
        cmd = [str(cache.absolute())]

        if reverse:
            if not cache.exists():
                return
            cmd.append("--reverse")
        else:
            patch = self.make_patch()
            cache.write_text(patch)
            cache.chmod(MODE_FILE | PERM_EXEC)

        run(cmd, cwd=str(location.absolute()))
        if reverse:
            cache.unlink()

    def write(self) -> None:
        """
        Write the clean patch to the selected output and close the output stream.
        """
        patch = self.make_patch()
        self.output.write(patch)
        self.output.close()
