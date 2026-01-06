from pathlib import Path
from zipfile import ZipFile, ZipInfo
from stat import S_IFDIR, S_IFREG
from os import path

from .spec import FileInputSpec
from .diff import File

ZIP_CREATE_SYSTEM_UNX = 3

MODE_NONEXISTANT = 0
MODE_FILE = 0o644 | S_IFREG
MODE_DIR = 0o755 | S_IFDIR

PERM_EXEC = 0o111


class FS:
    """Filesystem interface."""

    target: Path
    root: Path = Path()

    def __init__(self, target: Path):
        self.target = target

    def get_dir(self, dir: Path) -> list[Path]:
        """
        List all items (i.e. file and directories) in a subdirectory.

        :returns: A list of all item names.
        """

        raise NotImplementedError()

    def get_file(self, spec: FileInputSpec) -> File:
        """
        Get a :ref:`File` object with the content and mode of a file.

        :returns: A :ref:`File` object representing the content at ``spec``
        """
        return File(
            content=self.get_content(spec.path),
            mode=self.get_mode(spec.path),
        )

    def get_content(self, file: Path) -> bytes | str | None:
        """
        Get the content of a file.

        :returns:
          * The file content if it exists.
          * None if the file does not exist.
        """

        raise NotImplementedError()

    def get_mode(self, file: Path) -> int:
        """
        Get the mode of a file.

        :returns:
          * The mode as returned by stat(3)'s ``stat.st_mode``
          * 0 if the file does not exist
        """

        raise NotImplementedError()


class DiskFS(FS):
    """Implementation of :any:`FS` for a regular directory. Reads directly from the disk."""

    def __init__(self, target):
        super().__init__(target)

    def get_dir(self, dir):
        here = self.target.joinpath(self.root, dir)
        return list(here.iterdir())

    def get_content(self, file):
        here = self.target.joinpath(self.root, file)
        if not here.exists():
            return None
        bytes = here.read_bytes()
        try:
            return bytes.decode()
        except:
            return bytes

    def get_mode(self, file):
        here = self.target.joinpath(self.root, file)
        if not here.exists():
            return 0
        return here.stat().st_mode


class ZipFS(FS):
    """Implementation of :any:`FS` for zip files. Reads directly from the archive."""

    zip: ZipFile
    """Underlying zip file."""

    files: dict[Path, ZipInfo] = {}
    """Map of path -> ZipInfo for all files in the archive."""

    dirs: set[Path] = set()
    """
    List of directories in this archive.

    Some zip files may not include entries for all directories if they already define entries
    for files or subdirectories within. This set keeps all known directories.
    """

    def __init__(self, target):
        super().__init__(target)
        self.zip = ZipFile(str(target))
        for info in self.zip.infolist():
            path = Path(info.filename)
            self.files[path] = info
            while path.parent != path:
                self.dirs.add(path.parent)
                path = path.parent

    def get_info(self, path: Path) -> ZipInfo | None:
        """
        Get the ZipInfo for a file in the archive

        :returns:
          * The ZipInfo for the file at ``path``
          * None if the file does not exist
        """

        path = self.root.joinpath(path)
        return self.files.get(path, None)

    def get_dir(self, dir):
        items: set[Path] = set()
        dir = self.root.joinpath(dir)
        for zip_dir in (Path(name) for name in self.zip.namelist()):
            if not zip_dir.is_relative_to(dir):
                continue
            if zip_dir == dir:
                continue
            relative = zip_dir.relative_to(dir)
            items.add(dir.joinpath(relative.parts[0]))
        return list(items)

    def get_content(self, file):
        info = self.get_info(file)
        if info is None:
            return None
        bytes = self.zip.read(info)
        try:
            return bytes.decode()
        except:
            return bytes

    def get_mode(self, file):
        info = self.get_info(file)
        if info is None:
            if file in self.dirs:
                return MODE_DIR
            return MODE_NONEXISTANT

        if info.create_system == ZIP_CREATE_SYSTEM_UNX:
            return (info.external_attr >> 16) & 0xFFFF

        if info.is_dir():
            return MODE_DIR

        return MODE_FILE
