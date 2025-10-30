from __future__ import annotations
from typing import TYPE_CHECKING

from pathlib import Path

from .diff import Diff, File
from .process import Process

if TYPE_CHECKING:
    from .context import Context
    from .config import Config


class Patch:
    """A single patched file."""

    config: Config

    patch: Path
    """The patchset input location."""

    file: str
    """The name of the patched file in the target."""

    processors: list[tuple[type[Process], Process.Args]] = []
    """A list of processors to apply to the input before diffing."""

    def __init__(self, config: Config, patch: Path):
        self.patch = patch
        self.config = config

        self.processors.clear()
        self.file, *proc_strs = str(patch).split(config.process_delimiter)
        for proc_str in proc_strs:
            proc_name, *argv = proc_str.split(",")
            args = Process.Args(name=proc_name, argv=argv)
            proc_cls = config.processors.get(proc_name, None)
            if proc_cls is None:
                raise Exception(f"unknown processor: `{proc_cls}'")
            for arg in argv:
                key, value, *_ = (*arg.split("=", 1), None)
                args.argd[key] = value
            self.processors.insert(0, (proc_cls, args))

    def write(self, context: Context) -> None:
        """
        Apply all processors, compare to the target and write the delta to :any:`Context.output`.
        """

        if context.root is not None:
            self.file = str(Path(self.file).relative_to(context.root))

        diff = Diff(self.config, self.file)

        diff.a = File(
            content=context.get_content(self.file),
            mode=context.get_mode(self.file),
        )

        diff.b = File(
            content=None,
            mode=self.patch.stat().st_mode,
        )
        b_content = self.patch.read_bytes()
        try:
            diff.b.content = b_content.decode()
        except:
            diff.b.content = b_content

        for cls, args in self.processors:
            processor = cls(context, args)
            diff.b = processor.transform(diff.a, diff.b)

        delta = diff.compare()
        context.output.write(delta)
