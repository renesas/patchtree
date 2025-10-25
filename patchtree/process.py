from __future__ import annotations
from typing import TYPE_CHECKING, Any

from tempfile import mkstemp
from jinja2 import Environment
from subprocess import Popen
from pathlib import Path

from .diff import DiffFile

if TYPE_CHECKING:
    from .context import Context


class Process:
    context: Context

    def __init__(self, context: Context):
        self.context = context

    def transform(self, a: DiffFile, b: DiffFile) -> DiffFile:
        return b


class ProcessJinja2(Process):
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
    def transform(self, a, b):
        return DiffFile(content=a.content, mode=b.mode)
