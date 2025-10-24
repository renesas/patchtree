from dataclasses import dataclass, field
from argparse import ArgumentParser

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

@dataclass
class Config:
  context: type[Context] = Context
  patch: type[Patch] = Patch
  argument_parser: type[ArgumentParser] = ArgumentParser
  process_delimiter: str = "#"
  processors: dict[str, type[Process]] = field(default_factory=lambda: DEFAULT_PROCESSORS)
  diff_strategies: dict[str, type[Diff]] = field(default_factory=lambda: DEFAULT_DIFFS)

  def __post_init__(self):
    self.processors = {**DEFAULT_PROCESSORS, **self.processors}
    self.diff_strategies = {**DEFAULT_DIFFS, **self.diff_strategies}

