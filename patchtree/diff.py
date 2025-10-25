from dataclasses import dataclass
from difflib import unified_diff


@dataclass
class DiffFile:
    content: str | None
    mode: int

    def lines(self) -> list[str]:
        return (self.content or "").splitlines()


class Diff:
    """
    The base Diff class just produces a regular diff from the (possibly absent)
    SDK10 file. This effectively adds a new file or replaces the SDK10 source file
    with the file in the patch directory.
    """

    file: str

    a: DiffFile
    b: DiffFile

    def __init__(self, file: str):
        self.file = file

    def compare(self) -> str:
        """
        Generate patch text in "git-diff-files -p" format (see https:
        //git-scm.com/docs/diff-format#generate_patch_text_with_p)
        """
        a = self.a
        b = self.b

        if a == b:
            return ""

        assert (a.content or b.content) is not None

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

        lines_a = a.lines()
        lines_b = b.lines()
        diff = unified_diff(lines_a, lines_b, fromfile, tofile, lineterm="")
        delta += "".join(f"{line}\n" for line in diff)

        return delta

    def diff(self) -> str:
        return self.compare()


class IgnoreDiff(Diff):
    """
    IgnoreDiff is slightly different and is used to ensure all the lines in the
    patch source ignore file are present in the SDK version. This ensures no
    duplicate ignore lines exist after patching.
    """

    def diff(self):
        lines_a = self.a.lines()
        lines_b = self.b.lines()

        add_lines = set(lines_b) - set(lines_a)

        self.b.content = "\n".join(
            (
                *lines_a,
                *add_lines,
            )
        )

        return self.compare()
