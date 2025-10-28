from __future__ import annotations

from dataclasses import dataclass, field
from argparse import ArgumentParser
from importlib import metadata

from .context import Context
from .patch import Patch
from .process import *
from .diff import *

DEFAULT_PROCESSORS: dict[str, type[Process]] = {
    "id": ProcessIdentity,
    "cocci": ProcessCoccinelle,
    "jinja": ProcessJinja2,
    "exec": ProcessExec,
    "merge": ProcessMerge,
}


class Header:
    """
    Patch output header.
    """

    config: Config
    context: Context

    name = "patchtree"
    license = None

    def __init__(self, config: Config, context: Context):
        self.config = config
        self.context = context

        self.write_shebang()
        self.write_version()
        self.write_version_extra()
        self.write_license()

    def write_shebang(self):
        if not self.config.output_shebang:
            return
        cmd = [
            "/usr/bin/env",
            "-S",
            *self.context.get_apply_cmd(),
        ]
        cmdline = " ".join(cmd)
        self.context.output.write(f"#!{cmdline}\n")

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
    """
    Configuration dataclass.

    This class contains all configuration options read from the :ref: `configuration file <config>`.
    """

    context: type[Context] = Context
    """Context class type."""

    patch: type[Patch] = Patch
    """Patch class type."""

    argument_parser: type[ArgumentParser] = ArgumentParser
    """ArgumentParser class type."""

    process_delimiter: str = "#"
    """String used to delimit processors in patch source filenames."""

    processors: dict[str, type[Process]] = field(default_factory=lambda: DEFAULT_PROCESSORS)
    """Maps processor specification string to :type:`Process` class type."""

    header: type[Header] = Header
    """Header class type."""

    diff_context: int = 3
    """Lines of context to include in the default diffs."""

    output_shebang: bool = False
    """Whether to output a shebang line with the ``git patch`` command to apply
    the patch."""

    def __post_init__(self):
        self.processors = {**DEFAULT_PROCESSORS, **self.processors}
