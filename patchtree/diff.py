from __future__ import annotations
from typing import TYPE_CHECKING

from dataclasses import dataclass
from difflib import unified_diff

if TYPE_CHECKING:
    from .config import Config


@dataclass
class File:
    content: str | None
    mode: int

    def lines(self) -> list[str]:
        return (self.content or "").splitlines()


class Diff:
    """
    Produce a regular diff from the (possibly absent) original file to the file in the patch input tree. This
    effectively overwrites whatever exists in the target sources with the file in the patch input tree.
    """

    config: Config
    file: str

    a: File
    b: File

    def __init__(self, config: Config, file: str):
        self.config = config
        self.file = file

    def compare(self) -> str:
        """
        Generate delta in "git-diff-files -p" format (see
        `<https://git-scm.com/docs/diff-format#generate_patch_text_with_p>`_)
        """
        a = self.a
        b = self.b

        if a == b:
            return ""

        fromfile = f"a/{self.file}"
        tofile = f"b/{self.file}"

        delta = f"diff --git {fromfile} {tofile}\n"

        if a.content is None:
            fromfile = "/dev/null"
            delta += f"new file mode {b.mode:06o}\n"

        if b.content is None:
            tofile = "/dev/null"
            delta += f"deleted file mode {a.mode:06o}\n"

        if a.content is not None and b.content is not None and a.mode != b.mode:
            delta += f"old mode {a.mode:06o}\n"
            delta += f"new mode {b.mode:06o}\n"

        if a.content != b.content:
            lines_a = a.lines()
            lines_b = b.lines()
            diff = unified_diff(lines_a, lines_b, fromfile, tofile, lineterm="", n=self.config.diff_context)
            delta += "".join(f"{line}\n" for line in diff)

        return delta
