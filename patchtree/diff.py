from difflib import unified_diff

class Diff:
  """
  The base Diff class just produces a regular diff from the (possibly absent)
  SDK10 file. This effectively adds a new file or replaces the SDK10 source file
  with the file in the patch directory.
  """

  file: str

  content_a: str | None
  content_b: str = ""

  def __init__(self, file: str):
    self.file = file

  def compare(self) -> str:
    a = [] if self.content_a is None else self.content_a.splitlines()
    fromfile = "/dev/null" if self.content_a is None else f"a/{self.file}"

    b = self.content_b.strip().splitlines()
    b = [line.rstrip() for line in b]
    tofile = f"b/{self.file}"

    diff = unified_diff(a, b, fromfile, tofile, n=0, lineterm="")
    return "\n".join(diff) + "\n"

  def diff(self) -> str:
    return self.compare()

class IgnoreDiff(Diff):
  """
  IgnoreDiff is slightly different and is used to ensure all the lines in the
  patch source ignore file are present in the SDK version. This ensures no
  duplicate ignore lines exist after patching.
  """

  def diff(self):
    if self.content_a is None:
      self.content_a = ""
    lines_a = self.content_a.splitlines()
    lines_b = self.content_b.splitlines()

    add_lines = set(lines_b) - set(lines_a)

    self.content_b = "\n".join((*lines_a, *add_lines,))

    return self.compare()

