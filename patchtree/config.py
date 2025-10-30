from __future__ import annotations

from dataclasses import dataclass, field
from argparse import ArgumentParser
from importlib import metadata
from pathlib import Path

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
    Patch output header generator.

    The header is formatted as

    * shebang (optional)
    * patchtree version info
    * extra version info (empty by default)
    * license (empty by default)
    """

    config: Config
    context: Context

    name = "patchtree"
    """Program name shown in version info."""

    license = None
    """License text (optional)."""

    def __init__(self, config: Config, context: Context):
        self.config = config
        self.context = context

        self.write_shebang()
        self.write_version()
        self.write_version_extra()
        self.write_license()

    def write_shebang(self):
        """
        Write a shebang line to apply the output patch if the --shebang option was passed.
        """

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
        """
        Write the patchtree name and version number.
        """

        version = metadata.version("patchtree")
        self.context.output.write(f"{self.name} output (version {version})\n")

    def write_version_extra(self):
        """
        Write extra version information (empty).

        This method is meant to be implemented by subclasses of Header defined in the ptconfig.py of
        patchsets.
        """

        pass

    def write_license(self):
        """
        Write a license if it is defined.
        """

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
    """Context class type. Override this to add custom context variables."""

    patch: type[Patch] = Patch
    """Patch class type."""

    argument_parser: type[ArgumentParser] = ArgumentParser
    """ArgumentParser class type. Override this to add custom arguments."""

    process_delimiter: str = "#"
    """
    String used to delimit processors in patch source filenames.

    See: :ref:`processors`.
    """

    processors: dict[str, type[Process]] = field(default_factory=lambda: DEFAULT_PROCESSORS)
    """Maps processor specification string to :type:`Process` class type."""

    header: type[Header] = Header
    """Header class type. Override this to modify the patch header format."""

    diff_context: int = 3
    """Lines of context to include in the diffs."""

    output_shebang: bool = False
    """Whether to output a shebang line with the ``git patch`` command to apply the patch."""

    default_patch_sources: list[Path] = field(default_factory=list)
    """List of default sources."""

    default_root: str | None = None
    """Default value of the -C argument."""

    def __post_init__(self):
        self.processors = {**DEFAULT_PROCESSORS, **self.processors}
