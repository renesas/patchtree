from __future__ import annotations
from typing import TYPE_CHECKING, Any, Callable

from tempfile import mkstemp
from jinja2 import Environment
from subprocess import Popen, run
from pathlib import Path
from os import fdopen, chmod, unlink
from dataclasses import dataclass, field

from .diff import File

if TYPE_CHECKING:
    from .context import Context


class Process:
    """
    Processor base interface.
    """

    context: Context
    """Patch file context."""

    @dataclass
    class Args:
        """
        Processor filename arguments.

        See :ref:`processors`.
        """

        name: str
        """The name the processor was called with."""
        argv: list[str] = field(default_factory=list)
        """The arguments passed to the processor"""
        argd: dict[str, str | None] = field(default_factory=dict)
        """The key/value arguments passed to the processor"""

    args: Args
    """Arguments passed to this processor."""

    def __init__(self, context: Context, args: Args):
        self.args = args
        self.context = context

    def transform(self, a: File, b: File) -> File:
        """
        Transform the input file.

        :param a: Content of file to patch.
        :param b: Content of patch input in patch tree or output of previous processor.
        :returns: Processed file.
        """
        raise NotImplementedError()


class ProcessJinja2(Process):
    """
    Jinja2 preprocessor.
    """

    environment: Environment = Environment(
        trim_blocks=True,
        lstrip_blocks=True,
    )

    def __init__(self, *args, **kwargs):
        super(ProcessJinja2, self).__init__(*args, **kwargs)

        if len(self.args.argv) > 0:
            raise Exception("too many arguments")

    def transform(self, a, b):
        template_vars = self.get_template_vars()
        assert b.content is not None
        assert not isinstance(b.content, bytes)
        b.content = self.environment.from_string(b.content).render(**template_vars)
        return b

    def get_template_vars(self) -> dict[str, Any]:
        """
        Generate template variables.

        This method returns an empty dict by default, and is meant to be implemented by subclassing the
        ProcessJinja2 class.

        :returns: A dict of variables defined in the template.
        """
        return {}


class ProcessCoccinelle(Process):
    """
    Coccinelle transformer.
    """

    def __init__(self, *args, **kwargs):
        super(ProcessCoccinelle, self).__init__(*args, **kwargs)

        if len(self.args.argv) > 0:
            raise Exception("too many arguments")

    def transform(self, a, b):
        assert not isinstance(a.content, bytes)
        assert not isinstance(b.content, bytes)
        content_a = a.content or ""
        content_b = b.content or ""

        if len(content_b.strip()) == 0:
            return a

        temp_a = Path(mkstemp()[1])
        temp_b = Path(mkstemp()[1])
        temp_sp = Path(mkstemp()[1])

        temp_a.write_text(content_a)
        temp_sp.write_text(content_b)
        cmd = (
            "spatch",
            "--very-quiet",
            "--no-show-diff",
            "--sp-file",
            str(temp_sp),
            str(temp_a),
            "-o",
            str(temp_b),
        )
        coccinelle = Popen(cmd)
        coccinelle.wait()

        b.content = temp_b.read_text()

        temp_a.unlink()
        temp_b.unlink()
        temp_sp.unlink()

        return b


class ProcessIdentity(Process):
    """
    Identity transformer.
    """

    def transform(self, a, b):
        return File(content=a.content, mode=b.mode)


class ProcessExec(Process):
    """
    Executable transformer.
    """

    def __init__(self, *args, **kwargs):
        super(ProcessExec, self).__init__(*args, **kwargs)

        if len(self.args.argv) > 0:
            raise Exception("too many arguments")

    def transform(self, a, b):
        assert b.content is not None
        assert not isinstance(b.content, bytes)

        fd, exec = mkstemp()
        with fdopen(fd, "wt") as f:
            f.write(b.content)
        chmod(exec, 0o700)

        proc = run((str(exec),), text=True, input=a.content, capture_output=True, check=True)
        b.content = proc.stdout

        unlink(exec)

        return b


class ProcessMerge(Process):
    """
    Merge transformer.
    """

    def merge_ignore(self, a: File, b: File) -> File:
        lines_a = a.lines()
        lines_b = b.lines()

        add_lines = set(lines_b) - set(lines_a)

        b.content = "\n".join((*lines_a, *add_lines))

        return b

    strategies: dict[str, Callable[[ProcessMerge, File, File], File]] = {
        "ignore": merge_ignore,
    }

    strategy: Callable[[ProcessMerge, File, File], File]

    def __init__(self, *args, **kwargs):
        super(ProcessMerge, self).__init__(*args, **kwargs)

        argv = self.args.argv
        if len(argv) < 1:
            raise Exception("not enough arguments")

        if len(argv) > 1:
            raise Exception("too many arguments")

        strategy = argv[0]
        if strategy not in self.strategies:
            raise Exception(f"unknown merge strategy: `{strategy}'")

        self.strategy = self.strategies[strategy]

    def transform(self, a, b):
        return self.strategy(self, a, b)
