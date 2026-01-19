from __future__ import annotations
from typing import TYPE_CHECKING

from dataclasses import dataclass
from difflib import unified_diff

if TYPE_CHECKING:
    from .config import Config


@dataclass
class File:
    content: str | bytes | None = None
    """The file's contents, or ``None`` if it does not exist."""

    mode: int = 0
    """The file's mode as returned by stat(3)'s ``stat.st_mode``."""

    def is_binary(self) -> bool:
        """
        :returns: A boolean representing whether this file's content is binary.
        """
        return isinstance(self.content, bytes)

    def get_str(self) -> str:
        """
        Get the file content as a string.

        This function raises an Exception if the file is binary.

        :returns:
          * An empty string if the file is empty.
          * The contents if the file is already open in text mode.
          * The system locale decoded representation of the file content.
        """
        if self.content is None:
            return ""
        if isinstance(self.content, bytes):
            try:
                self.content = self.content.decode()
            except Exception:
                raise Exception("expected text file instead of binary")
        return self.content

    def lines(self) -> list[str]:
        """
        Get a list of lines in this file.

        :returns:
          * A list of strings for each line in the file
          * An empty list if the file is empty or nonexistent

        .. note::

           This function only works for text files. Use :any:`is_binary` to check this safely.
        """
        return self.get_str().splitlines()

    def __repr__(self):
        return f"{self.__class__.__name__}(mode={self.mode:06o}, content={repr(self.content)})"

    def __eq__(self, other):
        if not isinstance(other, File):
            return False
        if self.mode != other.mode:
            return False
        a = self.content or b""
        b = other.content or b""
        if isinstance(a, str):
            a = bytes(a, "utf-8")
        if isinstance(b, str):
            b = bytes(b, "utf-8")
        if a != b:
            return False
        return True


class Diff:
    """
    Produce a diff between two files.
    Either file may be absent, in which case extended header lines understood by ``git apply`` are generated.
    """

    config: Config

    file: str
    """Path to file relative to target dir."""

    a: File
    """Original (before) file."""

    b: File
    """Target (after) file."""

    def __init__(self, config: Config, file: str):
        self.config = config
        self.file = file

    def compare(self) -> str:
        """
        Generate delta in "git-diff-files -p" format (see
        `<https://git-scm.com/docs/diff-format#generate_patch_text_with_p>`_).
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
            binary = False
            lines_a = []
            lines_b = []

            try:
                lines_a = a.lines()
                lines_b = b.lines()
            except Exception:
                binary = True

            if not binary:
                diff = unified_diff(
                    lines_a, lines_b, fromfile, tofile, lineterm="", n=self.config.diff_context
                )
                delta += "".join(f"{line}\n" for line in diff)
            else:
                delta += f"Binary files {fromfile} and {tofile} differ\n"

        return delta
