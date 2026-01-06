from __future__ import annotations
from typing import TYPE_CHECKING

from importlib import metadata
import shlex

if TYPE_CHECKING:
    from .context import Context
    from .config import Config


class Header:
    """
    Patch output header generator.

    The header is formatted as

    #. shebang
    #. patchtree version info
    #. extra version info (empty by default)
    #. license (empty by default)
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

    def write(self) -> str:
        return "".join(
            (
                self.write_shebang(),
                self.write_version(),
                self.write_version_extra(),
                self.write_license(),
            )
        )

    def write_shebang(self) -> str:
        """
        Write a shebang line to apply the output patch unless the ``--no-shebang`` option was passed.
        """

        if self.config.no_shebang:
            return ""

        # NOTE: the GIT_DIR environment variable is set in order to allow users to apply the
        # .patch file to a target tree already tracked using git (which may be under a
        # different directory relative to the repository root, causing the patch to be skipped
        # silently). This effectively makes git-apply always behave as if it is outside a git
        # tree, while still applying changes described using the extended git diff format.
        cmd = ["/usr/bin/env", "-S", "GIT_DIR="]
        cmd.append(shlex.join(self.context.get_apply_cmd()))
        cmdline = " ".join(cmd)
        return f"#!{cmdline}\n"

    def write_version(self) -> str:
        """
        Write the patchtree name and version number.
        """

        version = metadata.version("patchtree")
        return f"{self.name} output (version {version})\n"

    def write_version_extra(self) -> str:
        """
        Write extra version information (empty).

        This method is meant to be implemented by subclasses of Header defined in the :ref:`configuration file <ptconfig>`.
        """

        return ""

    def write_license(self) -> str:
        """
        Write a license if it is defined.
        """

        if self.license is None:
            return ""
        return f"{self.license}\n"
