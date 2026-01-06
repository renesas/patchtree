from __future__ import annotations

from dataclasses import dataclass, field
from argparse import ArgumentParser
from pathlib import Path

from .context import Context
from .target import Target
from .header import Header
from .process import *
from .diff import *

DEFAULT_PROCESSORS: dict[str, type[Process]] = {
    "touch": TouchProcess,
    "cocci": CoccinelleProcess,
    "jinja": Jinja2Process,
    "exec": ExecProcess,
    "merge": MergeProcess,
}


@dataclass
class Config:
    """
    Configuration dataclass.

    This class contains all configuration options read from the :ref:`configuration file <ptconfig>`.
    """

    context: type[Context] = Context
    """Context class type."""

    target: type[Target] = Target
    """Target class type."""

    argument_parser: type[ArgumentParser] = ArgumentParser
    """ArgumentParser class type."""

    header: type[Header] = Header
    """Header class type."""

    processors: dict[str, type[Process]] = field(default_factory=lambda: DEFAULT_PROCESSORS)
    """
    Maps processor IDs to :type:`Process` class type (see :ref:`processors`).

    .. note::

       If this member is defined in the configuration file, it is automatically merged with the default dict,
       with the configuration file keys taking priority.
    """

    diff_context: int = 3
    """Lines of context to include in the diffs."""

    no_shebang: bool = False
    """Whether to suppress the shebang line with the ``git patch`` command to apply the patch."""

    default_patch_sources: list[Path] = field(default_factory=list)
    """List of default sources (empty by default)."""

    default_root: Path | None = None
    """Default value of the ``-C``/``--root`` argument."""

    patchspec_extensions: tuple[str, ...] = (
        ".yaml",
        ".yml",
    )
    """File extensions removed for standalone patch specifications (see :ref:`patchspec`)."""

    def __post_init__(self):
        self.processors = {**DEFAULT_PROCESSORS, **self.processors}
