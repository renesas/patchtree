from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProcessInputSpec:
    """Processor input specification (abstract base)"""


@dataclass
class FileInputSpec(ProcessInputSpec):
    """Processor input referencing a filename (abstract)"""

    path: Path


@dataclass
class TargetFileInputSpec(FileInputSpec):
    """Spec to use a file (referenced by name) in the target directory (concrete)"""


@dataclass
class PatchsetFileInputSpec(FileInputSpec):
    """Spec to use a file (referenced by name) in the patchset directory (concrete)"""


@dataclass
class DefaultInputSpec(ProcessInputSpec):
    """Spec to use the output of the previous processor as input (concrete)"""


@dataclass
class LiteralInputSpec(ProcessInputSpec):
    """Spec to use a literal string as input (concrete)"""

    content: str
