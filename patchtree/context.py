from argparse import Namespace
from typing import Union, IO, cast
from pathlib import Path as DiskPath
from zipfile import is_zipfile, Path as ZipPath
from tempfile import TemporaryFile
from os import path
from sys import stdout, stderr
from subprocess import run


Path = Union[DiskPath, ZipPath]


class Context:
    fs: Path
    output: IO
    options: Namespace

    cache: DiskPath

    def __init__(self, options: Namespace):
        self.options = options
        self.fs = self.get_fs()
        self.output = self.get_output()

        if self.options.in_place:
            location = cast(DiskPath, self.fs)
            self.cache = location.joinpath(".patchtree.diff")
            if self.cache.exists():
                run(
                    ("git", "apply", "--reverse", str(self.cache.absolute())),
                    cwd=str(location.absolute()),
                )

    def __del__(self):
        # patch must have a trailing newline
        self.output.write("\n")
        self.output.flush()

        if self.options.in_place:
            self.output.seek(0)
            patch = self.output.read()
            location = cast(DiskPath, self.fs)
            if len(patch) > 0:
                self.cache.write_text(patch)
                run(
                    ("git", "apply", str(self.cache.absolute())),
                    cwd=str(location.absolute()),
                )

        self.output.close()

    def get_dir(self, dir: str) -> list[str]:
        here = self.fs.joinpath(dir)
        return [path.name for path in here.iterdir()]

    def get_content(self, file: str) -> str | None:
        here = self.fs.joinpath(file)
        if not here.exists():
            return None
        return here.read_bytes().decode()

    def get_mode(self, file: str) -> int:
        # TODO
        return 0
        here = self.fs.joinpath(file)
        if not here.exists():
            return 0
        return here.stat().st_mode

    def get_fs(self) -> Path:
        target: str = self.options.target

        if not path.exists(target):
            raise Exception(f"cannot open `{target}'")

        if path.isdir(target):
            return DiskPath(target)

        if is_zipfile(target):
            if self.options.in_place:
                raise Exception("cannot edit zip in-place!")
            return ZipPath(target)

        raise Exception("cannot read `{target}'")

    def get_output(self) -> IO:
        if self.options.in_place:
            if self.options.out is not None:
                print("warning: --out is ignored when using --in-place", file=stderr)
            return TemporaryFile("w+")

        if self.options.out is not None:
            if self.options.out == "-":
                return stdout
            else:
                return open(self.options.out, "w+")

        return stdout
