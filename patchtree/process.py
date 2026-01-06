from __future__ import annotations
from stat import S_IFREG
from typing import TYPE_CHECKING, Any, Callable, Hashable

from tempfile import mkstemp
from jinja2 import Environment
from subprocess import PIPE, Popen, run
from pathlib import Path
from shlex import split

from .spec import (
    DefaultInputSpec,
    LiteralInputSpec,
    ProcessInputSpec,
    TargetFileInputSpec,
)
from .diff import File

if TYPE_CHECKING:
    from .target import Target


class Process:
    """
    Process base interface.
    """

    target: Target
    """Patch file context."""

    input_spec: ProcessInputSpec
    """Processor ``input`` option (see :ref:`processors`)"""
    target_spec: ProcessInputSpec
    """Processor ``target`` option (optionally used, see :ref:`processors`)"""

    def __init__(self, target: Target, data: dict[Hashable, Any] = {}):
        self.target = target

        if "input" in data:
            if isinstance(data["input"], ProcessInputSpec):
                self.input_spec = data["input"]
            elif isinstance(data["input"], str):
                self.input_spec = LiteralInputSpec(content=data["input"])
            else:
                raise Exception(f"type error for key input {type(data['input'])}")
            del data["input"]

        if "target" in data:
            if isinstance(data["target"], ProcessInputSpec):
                self.target_spec = data["target"]
            elif isinstance(data["target"], str):
                self.target_spec = LiteralInputSpec(content=data["target"])
            else:
                raise Exception(f"type error for key target {type(data['target'])}")
            del data["target"]

        assert target.file is not None

        self.input_spec = getattr(self, "input_spec", DefaultInputSpec())
        self.target_spec = getattr(
            self, "target_spec", TargetFileInputSpec(path=Path(target.file))
        )

    def transform(self) -> File:
        """
        Perform the transformation of this processor.

        :returns: Processed file.
        """
        raise NotImplementedError()


class Jinja2Process(Process):
    """
    Jinja2 preprocessor.
    """

    environment: Environment = Environment(
        trim_blocks=True,
        lstrip_blocks=True,
    )

    def transform(self):
        template_vars = self.get_template_vars()
        input = self.target.get_file(self.input_spec)
        input.content = self.environment.from_string(input.get_str()).render(**template_vars)

        return input

    def get_template_vars(self) -> dict[str, Any]:
        """
        Generate template variables.

        This method returns an empty dict by default and is meant to be implemented by the user by creating a subclass and registering it through the :ref:`configuration file <ptconfig>`.

        :returns: A dict of variables defined in the template.
        """
        return {}


class CoccinelleProcess(Process):
    """
    Coccinelle transformer.
    """

    def __init__(self, target, data):
        if "input" not in data:
            self.input_spec = TargetFileInputSpec(path=Path(target.file))

        if "target" not in data:
            self.target_spec = DefaultInputSpec()

        super().__init__(target, data)

    def transform(self):
        input = self.target.get_file(self.input_spec)
        patch = self.target.get_file(self.target_spec)

        content_input = input.get_str()
        content_patch = patch.get_str()

        # empty patch -> return input as-is (coccinelle gives errors in this case)
        if len(content_patch.strip()) == 0:
            return input

        temp_input = Path(mkstemp()[1])
        temp_output = Path(mkstemp()[1])
        temp_patch = Path(mkstemp()[1])

        temp_input.write_text(content_input)
        temp_patch.write_text(content_patch)
        cmd = (
            "spatch",
            "--very-quiet",
            "--no-show-diff",
            "--sp-file",
            str(temp_patch),
            str(temp_input),
            "-o",
            str(temp_output),
        )
        coccinelle = Popen(cmd)
        coccinelle.wait()

        input.content = temp_output.read_text()

        temp_input.unlink()
        temp_output.unlink()
        temp_patch.unlink()

        return input


class TouchProcess(Process):
    """
    Touch transformer.
    """

    mode: int | None = None

    def transform(self):
        input = self.target.get_file(self.input_spec)
        input.content = input.content or ""
        input.mode = self.mode or input.mode
        return input

    def __init__(self, target, data):
        super().__init__(target, data)

        if "mode" in data:
            if not isinstance(data["mode"], int):
                raise TypeError("invalid type of key 'mode'")
            self.mode = data["mode"] | S_IFREG
            del data["mode"]


class ExecProcess(Process):
    """
    Executable transformer.
    """

    cmd: list[str] = []

    def __init__(self, target, data):
        super().__init__(target, data)

        if "cmd" not in data:
            raise Exception("missing property `cmd'")
        if isinstance(data["cmd"], str):
            self.cmd = split(data["cmd"])
        elif isinstance(data["cmd"], list):
            self.cmd = data["cmd"]
            # TODO: check if each list item is actually a string
        else:
            raise TypeError("invalid type of key `cmd'")
        del data["cmd"]

    def transform(self):
        assert len(self.cmd) > 0

        input = self.target.get_file(self.input_spec)

        if input.content is None:
            input.content = ""
        if isinstance(input.content, str):
            input.content = input.content.encode()
        proc = run(self.cmd, input=input.content, stdout=PIPE, check=True)
        input.content = proc.stdout

        return input


class MergeProcess(Process):
    """
    Merge transformer.
    """

    def merge_ignore(self, a: File, b: File) -> File:
        lines_a = a.lines()
        lines_b = b.lines()

        add_lines = set(lines_b) - set(lines_a)

        return File(mode=a.mode, content="\n".join((*lines_a, *add_lines)))

    strategies: dict[str, Callable[[MergeProcess, File, File], File]] = {
        "ignore": merge_ignore,
    }

    strategy: Callable[[MergeProcess, File, File], File] | None = None

    def __init__(self, target, data):
        super().__init__(target, data)

        if "strategy" not in data:
            raise Exception("missing property `strategy'")
        if data["strategy"] not in self.strategies:
            raise Exception(f"unknown strategy {repr(data['strategy'])}")
        self.strategy = self.strategies[data["strategy"]]
        del data["strategy"]

    def transform(self):
        a = self.target.get_file(self.input_spec)
        b = self.target.get_file(self.target_spec)
        assert self.strategy is not None
        return self.strategy(self, a, b)
