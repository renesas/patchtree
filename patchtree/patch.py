from __future__ import annotations
from typing import TYPE_CHECKING

from pathlib import Path

from .diff import Diff

if TYPE_CHECKING:
    from .process import Process
    from .context import Context
    from .config import Config


class Patch:
    config: Config
    patch: Path

    file: str
    file_name: str = ""
    file_type: str = ""
    processors: list[str] = []

    def __init__(self, config: Config, patch: Path):
        self.patch = patch
        self.config = config

        self.file_name = patch.name

        # find preprocessors
        idx = self.file_name.find(config.process_delimiter)
        if idx >= 0:
            self.processors = self.file_name[idx:].split(config.process_delimiter)
            self.processors = [template.strip() for template in self.processors]
            self.processors = [
                template for template in self.processors if len(template) > 0
            ]
            self.processors.reverse()
            self.file_name = self.file_name[:idx]

        # save the path to the target file
        self.file = str(patch.parent.joinpath(self.file_name))

        # find and split at file extension
        idx = self.file_name.find(".")
        if idx >= 0:
            self.file_type = self.file_name[idx:]
            self.file_name = self.file_name[:idx]

    def get_diff(self) -> type[Diff]:
        return self.config.diff_strategies.get(self.file_type, Diff)

    def get_processors(self) -> list[type[Process]]:
        processors = []
        for processor in self.processors:
            if processor not in self.config.processors:
                continue
            processors.append(self.config.processors[processor])
        return processors

    def write(self, context: Context) -> None:
        diff_class = self.get_diff()
        processor_classes = self.get_processors()

        diff = diff_class(self.file)

        # read file A contents
        content_a = context.get_content(self.file)

        # read file B contents
        content_b = self.patch.read_text()
        for processor_class in processor_classes:
            processor = processor_class(context)
            content_b = processor.transform(content_a, content_b)

        diff.content_a = content_a
        diff.content_b = content_b

        delta = diff.diff()
        context.output.write(delta)
