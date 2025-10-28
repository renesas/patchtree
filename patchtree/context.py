from __future__ import annotations
from typing import TYPE_CHECKING, IO, cast

from argparse import Namespace
from pathlib import Path
from zipfile import ZipInfo, is_zipfile
from tempfile import TemporaryFile
from os import path
from sys import stdout, stderr
from subprocess import run
from zipfile import ZipFile
from stat import S_IFDIR, S_IFREG

if TYPE_CHECKING:
    from .config import Config

ZIP_CREATE_SYSTEM_UNX = 3


class FS:
    target: Path

    def __init__(self, target: Path):
        self.target = target

    def get_dir(self, dir: str) -> list[str]:
        raise NotImplementedError()

    def get_content(self, file: str) -> str | None:
        raise NotImplementedError()

    def get_mode(self, file: str) -> int:
        raise NotImplementedError()


class DiskFS(FS):
    def __init__(self, target):
        super(DiskFS, self).__init__(target)

    def get_dir(self, dir: str) -> list[str]:
        here = self.target.joinpath(dir)
        return [path.name for path in here.iterdir()]

    def get_content(self, file: str) -> str | None:
        here = self.target.joinpath(file)
        if not here.exists():
            return None
        bytes = here.read_bytes()
        try:
            return bytes.decode()
        except:
            return ""

    def get_mode(self, file: str) -> int:
        here = self.target.joinpath(file)
        if not here.exists():
            return 0
        return here.stat().st_mode


class ZipFS(FS):
    zip: ZipFile
    files: dict[Path, ZipInfo] = {}

    def __init__(self, target):
        super(ZipFS, self).__init__(target)
        self.zip = ZipFile(str(target))
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
        bytes = self.zip.read(info)
        try:
            return bytes.decode()
        except:
            return ""

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
    """
    Global app context / state holder.
    """

    fs: FS
    output: IO

    root: Path
    target: Path
    inputs: list[Path] = []
    in_place: bool

    config: Config

    def __init__(self, config: Config, options: Namespace):
        self.config = config

        self.root = options.root
        self.target = options.target
        self.in_place = options.in_place
        self.inputs = self.collect_inputs(options)

        self.fs = self.get_fs()
        self.output = self.get_output(options)

        if self.in_place:
            self.apply(True)

    def close(self):
        # patch must have a trailing newline
        self.output.write("\n")
        self.output.flush()

        if self.in_place:
            self.apply(False)

        self.output.close()

    def collect_inputs(self, options: Namespace) -> list[Path]:
        inputs: set[Path] = set()

        if len(inputs) == 0:
            options.glob = True
            options.patch = [str(Path(options.root or ".").joinpath("**"))]

        if options.glob:
            for pattern in options.patch:
                for path in Path(".").glob(pattern):
                    if not path.is_file():
                        continue
                    inputs.add(path)
            return sorted(inputs)
        else:
            for input in options.patch:
                path = Path(input)
                if not path.exists():
                    raise Exception(f"cannot open `{input}'")
                if not path.is_file():
                    raise Exception(f"not a file: `{input}'")
                inputs.add(path)
            return list(inputs)

    def get_dir(self, dir: str) -> list[str]:
        return self.fs.get_dir(dir)

    def get_content(self, file: str) -> str | None:
        return self.fs.get_content(file)

    def get_mode(self, file: str) -> int:
        return self.fs.get_mode(file)

    def get_fs(self) -> FS:
        target = self.target

        if not target.exists():
            raise Exception(f"cannot open `{target}'")

        if path.isdir(target):
            return DiskFS(target)

        if is_zipfile(target):
            if self.in_place:
                raise Exception("cannot edit zip in-place!")
            return ZipFS(target)

        raise Exception("cannot read `{target}'")

    def get_output(self, options: Namespace) -> IO:
        if self.in_place:
            if options.out is not None:
                print("warning: --out is ignored when using --in-place", file=stderr)
            return TemporaryFile("w+")

        if options.out is not None:
            if options.out == "-":
                return stdout
            else:
                return open(options.out, "w+")

        return stdout

    def get_apply_cmd(self) -> list[str]:
        cmd = [
            "git",
            "apply",
            "--allow-empty",
        ]
        if self.config.diff_context == 0:
            cmd.append("--unidiff-zero")
        return cmd

    def apply(self, reverse: bool) -> None:
        location = cast(DiskFS, self.fs).target
        cache = location.joinpath(".patchtree.diff")
        cmd = self.get_apply_cmd()

        if reverse:
            if not cache.exists():
                return
            cmd.append("--reverse")
        else:
            self.output.seek(0)
            patch = self.output.read()
            cache.write_text(patch)

        cmd.append(str(cache.absolute()))
        run(cmd, cwd=str(location.absolute()))
