from __future__ import annotations
from typing import TYPE_CHECKING, Any, Callable

from tempfile import mkstemp
from jinja2 import Environment
from subprocess import Popen, run
from pathlib import Path
from shlex import split as shell_split
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
        name: str
        argv: list[str] = field(default_factory=list)
        argd: dict[str, str | None] = field(default_factory=dict)

    args: Args

    def __init__(self, context: Context, args: Args):
        self.args = args
        self.context = context

    def transform(self, a: File, b: File) -> File:
        """
        Transform the input file.

        :param a: content of file to patch
        :param b: content of patch input (in patch tree)
        :returns: processed file
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
        b.content = self.environment.from_string(b.content).render(**template_vars)
        return b

    def get_template_vars(self) -> dict[str, Any]:
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

        exec = Path(mkstemp()[1])
        exec.write_text(b.content)

        cmd = [str(exec)]

        if b.content.startswith("#!"):
            shebang = b.content.split("\n", 1)[0][2:]
            cmd = [*shell_split(shebang), *cmd]

        proc = run(cmd, text=True, input=a.content, capture_output=True, check=True)
        b.content = proc.stdout

        exec.unlink()

        return b


class ProcessMerge(Process):
    """
    Merge transformer.
    """

    def merge_ignore(self, a: File, b: File) -> File:
        lines_a = a.lines()
        lines_b = b.lines()

        add_lines = set(lines_b) - set(lines_a)

        b.content = "\n".join(
            (
                *lines_a,
                *add_lines,
            )
        )

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
