from __future__ import annotations
from typing import TYPE_CHECKING, IO, cast

from argparse import Namespace
from pathlib import Path
from zipfile import ZipInfo, is_zipfile
from tempfile import TemporaryFile
from os import path
from sys import stdout, stderr
from subprocess import run
from zipfile import ZipFile
from stat import S_IFDIR, S_IFREG

if TYPE_CHECKING:
    from .config import Config

ZIP_CREATE_SYSTEM_UNX = 3


class FS:
    """Target filesystem interface."""

    target: Path

    def __init__(self, target: Path):
        self.target = target

    def get_dir(self, dir: str) -> list[str]:
        """
        List all items in a subdirectory of the target.

        :returns: A list of all item names.
        """

        raise NotImplementedError()

    def get_content(self, file: str) -> bytes | str | None:
        """
        Get the content of a file relative to the target.

        :returns:
          * The file content if it exists.
          * None if the file does not exist.
        """

        raise NotImplementedError()

    def get_mode(self, file: str) -> int:
        """
        Get the mode of a file relative to the target.

        :returns:
          * The mode as returned by stat(3)'s ``stat.st_mode``
          * 0 if the file does not exist
        """

        raise NotImplementedError()


class DiskFS(FS):
    """Implementation of :any:`FS` for a regular directory. Reads directly from the disk."""

    def __init__(self, target):
        super(DiskFS, self).__init__(target)

    def get_dir(self, dir):
        here = self.target.joinpath(dir)
        return [path.name for path in here.iterdir()]

    def get_content(self, file):
        here = self.target.joinpath(file)
        if not here.exists():
            return None
        bytes = here.read_bytes()
        try:
            return bytes.decode()
        except:
            return bytes

    def get_mode(self, file):
        here = self.target.joinpath(file)
        if not here.exists():
            return 0
        return here.stat().st_mode


class ZipFS(FS):
    """Implementation of :any:`FS` for zip files. Reads directly from the archive."""

    zip: ZipFile
    """Underlying zip file."""

    files: dict[Path, ZipInfo] = {}
    """Map of path -> ZipInfo for all files in the archive."""

    def __init__(self, target):
        super(ZipFS, self).__init__(target)
        self.zip = ZipFile(str(target))
        for info in self.zip.infolist():
            self.files[Path(info.filename)] = info
        # todo: index implicit directories in tree

    def get_info(self, path: str) -> ZipInfo | None:
        """
        Get the ZipInfo for a file in the archive

        :returns:
          * The ZipInfo for the file at ``path``
          * None if the file does not exist
        """

        return self.files.get(Path(path), None)

    def get_dir(self, dir):
        items: set[str] = set()
        dir = path.normpath("/" + dir)
        for zip_dir in self.zip.namelist():
            zip_dir = path.normpath("/" + zip_dir)
            if not zip_dir.startswith(dir):
                continue
            if zip_dir == dir:
                continue
            relative = path.relpath(zip_dir, dir)
            top_level = relative.split("/")[0]
            items.add(top_level)
        return list(items)

    def get_content(self, file):
        info = self.get_info(file)
        if info is None:
            return None
        bytes = self.zip.read(info)
        try:
            return bytes.decode()
        except:
            return bytes

    def is_implicit_dir(self, file: str) -> bool:
        """
        Check if there is an implicit directory at ``file``.

        Some zip files may not include entries for all directories if they already define entries for files or
        subdirectories within. This function checks if any path that is a subdirectory of ``file`` exists.

        :returns: ``True`` if there is a directory at ``file``, else ``False``.
        """

        parent = Path(file)
        for child in self.files:
            if parent in child.parents:
                return True
        return False

    def get_mode(self, file):
        MODE_NONEXISTANT = 0
        MODE_FILE = 0o644 | S_IFREG
        MODE_DIR = 0o755 | S_IFDIR

        info = self.get_info(file)
        if info is None:
            # if self.is_implicit_dir(file):
            #     return MODE_DIR
            return MODE_NONEXISTANT

        if info.create_system == ZIP_CREATE_SYSTEM_UNX:
            return (info.external_attr >> 16) & 0xFFFF

        if info.is_dir():
            return MODE_DIR

        return MODE_FILE


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

    target: Path
    """Path to target."""

    fs: FS
    """Target file system interface."""

    output: IO
    """Output stream for writing the clean patch."""

    in_place: bool
    """Whether to apply the changes directly to the target instead of outputting the .patch file."""

    config: Config

    def __init__(self, config: Config, options: Namespace):
        self.config = config

        self.root = options.root
        self.target = options.target
        self.in_place = options.in_place
        self.inputs = self.collect_inputs(options)

        self.fs = self.get_fs()
        self.output = self.get_output(options)

        if self.in_place:
            self.apply(True)

    def close(self):
        """Finish writing the clean patch file and close it."""

        # patch must have a trailing newline
        self.output.write("\n")
        self.output.flush()

        if self.in_place:
            self.apply(False)

        self.output.close()

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

    def get_dir(self, dir: str) -> list[str]:
        """Get a target directory's content (see :any:`FS.get_dir()`)"""
        return self.fs.get_dir(dir)

    def get_content(self, file: str) -> bytes | str | None:
        """Get a target file's content (see :any:`FS.get_content()`)"""
        return self.fs.get_content(file)

    def get_mode(self, file: str) -> int:
        """Get a target file's mode (see :any:`FS.get_mode()`)"""
        return self.fs.get_mode(file)

    def get_fs(self) -> FS:
        """
        Open the selected target, taking into account the --in-place option.

        :returns: Target filesystem interface.
        """
        target = self.target

        if not target.exists():
            raise Exception(f"cannot open `{target}'")

        if path.isdir(target):
            return DiskFS(target)

        if is_zipfile(target):
            if self.in_place:
                raise Exception("cannot edit zip in-place!")
            return ZipFS(target)

        raise Exception("cannot read `{target}'")

    def get_output(self, options: Namespace) -> IO:
        """
        Open the output stream, taking into account the --in-place and --out options.

        :returns: Output stream.
        """
        if self.in_place:
            if options.out is not None:
                print("warning: --out is ignored when using --in-place", file=stderr)
            return TemporaryFile("w+")

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

        cmd = ["git", "apply", "--allow-empty"]
        if self.config.diff_context == 0:
            cmd.append("--unidiff-zero")
        return cmd

    def apply(self, reverse: bool) -> None:
        """
        Apply the patch in ``self.output`` and update the cache or reverse the patch in the cache.
        """

        location = cast(DiskFS, self.fs).target
        cache = location.joinpath(".patchtree.diff")
        cmd = self.get_apply_cmd()

        if reverse:
            if not cache.exists():
                return
            cmd.append("--reverse")
        else:
            self.output.seek(0)
            patch = self.output.read()
            cache.write_text(patch)

        cmd.append(str(cache.absolute()))
        run(cmd, cwd=str(location.absolute()))
