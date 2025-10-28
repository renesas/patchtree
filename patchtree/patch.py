from __future__ import annotations
from typing import TYPE_CHECKING

from pathlib import Path

from .diff import Diff, File
from .process import Process

if TYPE_CHECKING:
    from .context import Context
    from .config import Config


class Patch:
    config: Config
    patch: Path

    file: str
    processors: list[tuple[type[Process], Process.Args]] = []

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
            self.processors.insert(
                0,
                (
                    proc_cls,
                    args,
                ),
            )

    def write(self, context: Context) -> None:
        diff = Diff(self.config, self.file)

        diff.a = File(
            content=context.get_content(self.file),
            mode=context.get_mode(self.file),
        )

        diff.b = File(
            content=self.patch.read_text(),
            mode=self.patch.stat().st_mode,
        )

        for cls, args in self.processors:
            processor = cls(context, args)
            diff.b = processor.transform(diff.a, diff.b)

        delta = diff.compare()
        context.output.write(delta)
