from dataclasses import fields
from sys import stderr
from pathlib import Path
from argparse import ArgumentTypeError

from .context import Context
from .config import Config


def load_config() -> Config:
    """
    Create a new instance of the :any:`Config` dataclass and attempt to overwrite any members using the global
    variables defined in ptconfig.py (if it exists).
    """

    init = {}
    cfg = Path("ptconfig.py")
    if cfg.exists():
        exec(cfg.read_text(), init)
    valid_fields = [field.name for field in fields(Config)]
    init = {key: value for key, value in init.items() if key in valid_fields}
    return Config(**init)


def path_dir(path: str) -> Path:
    """
    Argparse helper type for a pathlib Path to a directory.
    """

    out = Path(path)
    if not out.is_dir():
        raise ArgumentTypeError(f"not a directory: `{path}'")
    return out


def parse_arguments(config: Config) -> Context:
    """
    Parse command-line arguments and return the application context.
    """

    parser = config.argument_parser(
        prog="patchtree",
        description="patch file generator",
    )
    parser.add_argument(
        "-o",
        "--out",
        help="output file (stdout by default)",
        type=str,
    )
    parser.add_argument(
        "-i",
        "--in-place",
        help="patch target in-place",
        action="store_true",
    )
    parser.add_argument(
        "-c",
        "--context",
        metavar="NUM",
        help="lines of context in output diff",
        type=int,
    )
    parser.add_argument(
        "-s",
        "--shebang",
        help="output shebang in resulting patch",
        action="store_true",
    )
    parser.add_argument(
        "-C",
        "--root",
        metavar="DIR",
        help="patchset root directory",
        type=path_dir,
    )
    parser.add_argument(
        "-g",
        "--glob",
        help="enable globbing for input(s)",
        action="store_true",
    )
    parser.add_argument(
        "target",
        metavar="TARGET",
        help="target directory or archive",
        type=Path,
    )
    parser.add_argument(
        "patch",
        metavar="PATCH",
        help="patchset input(s)",
        nargs="*",
        type=str,
    )

    options = parser.parse_args()

    if options.context is not None:
        config.diff_context = options.context

    if options.shebang:
        config.output_shebang = True

    if len(options.patch) == 0:
        options.patch = config.default_patch_sources

    try:
        return config.context(config, options)
    except Exception as e:
        parser.error(str(e))


def main():
    config = load_config()

    context = parse_arguments(config)

    if len(context.inputs) == 0:
        print("no files to patch!", file=stderr)
        return 0

    config.header(config, context)

    for file in context.inputs:
        patch = config.patch(config, file)
        patch.write(context)

    context.close()

    return 0


if __name__ == "__main__":
    exit(main())
