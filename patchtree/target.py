from __future__ import annotations
from typing import TYPE_CHECKING, Any, Hashable

from pathlib import Path

from .diff import Diff, File
from .spec import (
    DefaultInputSpec,
    ProcessInputSpec,
    TargetFileInputSpec,
)
from .process import Process

if TYPE_CHECKING:
    from .context import Context


class Target:
    """A single patched file, including its processors."""

    context: Context

    file: str
    """The name of the patched file in the target."""

    patch = File()

    processors: list[Process] = []

    inputs: list[ProcessInputSpec] = []

    def __init__(self, context: Context, file: Path, data: dict[Hashable, Any] = {}):
        self.context = context
        self.file = str(file)

        if "processors" not in data:
            data["processors"] = []
        if not isinstance(data["processors"], list):
            raise Exception("not a list: 'processors'")
        self.processors = []
        for processor_spec in data["processors"]:
            if "id" not in processor_spec:
                raise Exception("missing key 'id'")
            id = str(processor_spec["id"])
            del processor_spec["id"]

            config = context.config
            if id not in config.processors:
                raise Exception(f"no processor for id {id}")

            process_cls = config.processors[id]
            process = process_cls(self, processor_spec)

            self.processors.append(process)

    def get_file(self, spec: ProcessInputSpec) -> File:
        """Get the file contents from a :type:`ProcessInputSpec` (called by :type:`Processor`)."""
        if isinstance(spec, DefaultInputSpec):
            return self.patch
        return self.context.get_file(spec)

    def write(self) -> str:
        """
        Apply all processors, compare to the target and return the delta.
        """
        self.context.log.info(f"writing patch for `{self.file}'")

        for i, processor in enumerate(self.processors):
            try:
                self.patch = processor.transform()
            except Exception as e:
                self.context.log.error(
                    f"while running processor {i+1} ({processor.__class__.__name__}) for `{self.file}'"
                )
                raise e

        diff = Diff(self.context.config, self.file)
        diff.a = self.context.get_file(TargetFileInputSpec(path=Path(self.file)))
        diff.b = self.patch

        return diff.compare()

    def __repr__(self):
        return f"{self.__class__.__name__}(file={self.file})"
