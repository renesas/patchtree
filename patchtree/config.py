from dataclasses import dataclass, field
from argparse import ArgumentParser
from importlib import metadata

from .context import Context
from .patch import Patch
from .process import *
from .diff import *

DEFAULT_PROCESSORS: dict[str, type[Process]] = {
    "jinja": ProcessJinja2,
    "cocci": ProcessCoccinelle,
    "smpl": ProcessCoccinelle,
}

DEFAULT_DIFFS: dict[str, type[Diff]] = {
    ".gitignore": IgnoreDiff,
}


class Header:
    context: Context
    name = "patchtree"
    license = None

    def __init__(self, context: Context):
        self.context = context

        self.write_version()
        self.write_version_extra()
        self.write_license()

    def write_version(self):
        version = metadata.version("patchtree")
        self.context.output.write(f"{self.name} output (version {version})\n")

    def write_version_extra(self):
        pass

    def write_license(self):
        if self.license is None:
            return
        self.context.output.write(f"{self.license}\n")


@dataclass
class Config:
    context: type[Context] = Context
    patch: type[Patch] = Patch
    argument_parser: type[ArgumentParser] = ArgumentParser
    process_delimiter: str = "#"
    processors: dict[str, type[Process]] = field(
        default_factory=lambda: DEFAULT_PROCESSORS
    )
    diff_strategies: dict[str, type[Diff]] = field(
        default_factory=lambda: DEFAULT_DIFFS
    )
    header: type[Header] = Header

    def __post_init__(self):
        self.processors = {**DEFAULT_PROCESSORS, **self.processors}
        self.diff_strategies = {**DEFAULT_DIFFS, **self.diff_strategies}
