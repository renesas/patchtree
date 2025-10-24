from argparse import Namespace
from typing import Union, IO
from pathlib import Path as DiskPath
from zipfile import is_zipfile, Path as ZipPath
from os import path
from sys import stdout


class Context:
    """
    Generic "context" struct that Diff and the main() function depend on for
    application context.
    """

    fs: Union[DiskPath, ZipPath]
    output: IO = stdout
    options: Namespace

    def __init__(self, options: Namespace):
        self.options = options

        target = options.target
        if not path.exists(target):
            raise Exception(f"cannot open `{target}'")

        if options.out is not None:
            if options.out == "-":
                self.output = stdout
            else:
                self.output = open(options.out, "w+")

        if path.isdir(target):
            self.fs = DiskPath(target)
        elif is_zipfile(target):
            self.fs = ZipPath(target)
        else:
            raise Exception("cannot read `{target}'")

    def get_dir(self, dir: str) -> list[str]:
        here = self.fs.joinpath(dir)
        print(here)
        return [path.name for path in here.iterdir()]

    def get_content(self, file: str) -> str | None:
        here = self.fs.joinpath(file)
        if not here.exists():
            return None
        return here.read_bytes().decode()
