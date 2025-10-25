from argparse import Namespace
from typing import IO, cast
from pathlib import Path
from zipfile import ZipInfo, is_zipfile
from tempfile import TemporaryFile
from os import path
from sys import stdout, stderr
from subprocess import run
from zipfile import ZipFile
from stat import S_IFDIR, S_IFREG

ZIP_CREATE_SYSTEM_UNX = 3


class FS:
    target: str

    def __init__(self, target: str):
        self.target = target

    def get_dir(self, dir: str) -> list[str]:
        raise NotImplementedError()

    def get_content(self, file: str) -> str | None:
        raise NotImplementedError()

    def get_mode(self, file: str) -> int:
        raise NotImplementedError()


class DiskFS(FS):
    path: Path

    def __init__(self, target: str):
        super(DiskFS, self).__init__(target)
        self.path = Path(target)

    def get_dir(self, dir: str) -> list[str]:
        here = self.path.joinpath(dir)
        return [path.name for path in here.iterdir()]

    def get_content(self, file: str) -> str | None:
        here = self.path.joinpath(file)
        if not here.exists():
            return None
        return here.read_bytes().decode()

    def get_mode(self, file: str) -> int:
        here = self.path.joinpath(file)
        if not here.exists():
            return 0
        return here.stat().st_mode


class ZipFS(FS):
    zip: ZipFile
    files: dict[Path, ZipInfo] = {}

    def __init__(self, target: str):
        super(ZipFS, self).__init__(target)
        self.zip = ZipFile(target)
        for info in self.zip.infolist():
            self.files[Path(info.filename)] = info

    def get_info(self, path: str) -> ZipInfo | None:
        return self.files.get(Path(path), None)

    def get_dir(self, dir: str) -> list[str]:
        items: set[str] = set()
        dir = path.normpath("/" + dir)
        for zip_dir in self.zip.namelist():
            zip_dir = path.normpath("/" + zip_dir)
            if not zip_dir.startswith(dir):
                continue
            if zip_dir == dir:
                continue
            relative = path.relpath(zip_dir, dir)
            top_level = relative.split("/")[0]
            items.add(top_level)
        return list(items)

    def get_content(self, file: str) -> str | None:
        info = self.get_info(file)
        if info is None:
            return None
        return self.zip.read(info).decode()

    def get_mode(self, file: str) -> int:
        info = self.get_info(file)
        if info is None:
            return 0
        if info.create_system == ZIP_CREATE_SYSTEM_UNX:
            return (info.external_attr >> 16) & 0xFFFF
        if info.is_dir():
            return 0o755 | S_IFDIR
        return 0o644 | S_IFREG


class Context:
    fs: FS
    output: IO
    options: Namespace

    cache: Path

    def __init__(self, options: Namespace):
        self.options = options
        self.fs = self.get_fs()
        self.output = self.get_output()

        if self.options.in_place:
            location = cast(DiskFS, self.fs).path
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
            location = cast(DiskFS, self.fs).path
            if len(patch) > 0:
                self.cache.write_text(patch)
                run(
                    ("git", "apply", str(self.cache.absolute())),
                    cwd=str(location.absolute()),
                )

        self.output.close()

    def get_dir(self, dir: str) -> list[str]:
        return self.fs.get_dir(dir)

    def get_content(self, file: str) -> str | None:
        return self.fs.get_content(file)

    def get_mode(self, file: str) -> int:
        return self.fs.get_mode(file)

    def get_fs(self) -> FS:
        target: str = self.options.target

        if not path.exists(target):
            raise Exception(f"cannot open `{target}'")

        if path.isdir(target):
            return DiskFS(target)

        if is_zipfile(target):
            if self.options.in_place:
                raise Exception("cannot edit zip in-place!")
            return ZipFS(target)

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
