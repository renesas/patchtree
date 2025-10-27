from __future__ import annotations
from typing import TYPE_CHECKING, Any

from tempfile import mkstemp
from jinja2 import Environment
from subprocess import Popen, run
from pathlib import Path
from shlex import split as shell_split

from .diff import DiffFile

if TYPE_CHECKING:
    from .context import Context


class Process:
    """
    Processor base interface.
    """

    context: Context
    """Patch file context."""

    def __init__(self, context: Context):
        self.context = context

    def transform(self, a: DiffFile, b: DiffFile) -> DiffFile:
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


class ProcessTouch(Process):
    """
    Touch transformer.
    """

    def transform(self, a, b):
        return DiffFile(content=a.content, mode=b.mode)


class ProcessExec(Process):
    """
    Executable transformer.
    """

    def transform(self, a, b):
        assert b.content is not None

        exec = Path(mkstemp()[1])
        exec.write_text(b.content)

        cmd = [str(exec)]

        if b.content.startswith("#!"):
            shebang = b.content.split("\n", 1)[0][2:]
            cmd = [*shell_split(shebang), *cmd]

        proc = run(cmd, text=True, input=a.content, capture_output=True)
        b.content = proc.stdout

        exec.unlink()

        return b
