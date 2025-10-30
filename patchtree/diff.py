from __future__ import annotations
from typing import TYPE_CHECKING

from dataclasses import dataclass
from difflib import unified_diff

if TYPE_CHECKING:
    from .config import Config


@dataclass
class File:
    content: str | bytes | None
    mode: int

    def is_binary(self) -> bool:
        return isinstance(self.content, bytes)

    def lines(self) -> list[str]:
        assert not isinstance(self.content, bytes)
        return (self.content or "").splitlines()


class Diff:
    """
    Produce a regular diff from the (possibly absent) original file to the file in the patch input tree.
    """

    config: Config
    file: str
    """Path to file relative to target dir."""

    a: File
    """Original file."""

    b: File
    """Target file."""

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
            # make sure a file doesn't switch from text to binary or vice versa
            assert a.is_binary() == b.is_binary()

            if not b.is_binary():
                lines_a = a.lines()
                lines_b = b.lines()
                diff = unified_diff(
                    lines_a, lines_b, fromfile, tofile, lineterm="", n=self.config.diff_context
                )
                delta += "".join(f"{line}\n" for line in diff)
            else:
                delta += f"Binary files {fromfile} and {tofile} differ\n"

        return delta
