from dataclasses import fields
from sys import stderr
from pathlib import Path

from .context import Context
from .config import Config

def load_config() -> Config:
  init = {}
  cfg = Path("ptconfig.py")
  if cfg.exists():
    exec(cfg.read_text(), init)
  valid_fields = [field.name for field in fields(Config)]
  init = {key: value for key, value in init.items() if key in valid_fields}
  return Config(**init)

def parse_arguments(config: Config) -> Context:
  parser = config.argument_parser(
    prog='patchtree',
    description='patch file generator',
  )
  parser.add_argument(
    '-o', '--out',
    help="output file (stdout by default)",
    type=str,
  )
  parser.add_argument('target', help="target directory or archive")
  parser.add_argument("patch", help="patch input glob(s)", nargs="+")

  options = parser.parse_args()

  try:
    return config.context(options)
  except Exception as e:
    parser.error(str(e))

def main():
  config = load_config()

  context = parse_arguments(config)

  file_set: set[Path] = set()
  for pattern in context.options.patch:
    for path in Path('.').glob(pattern):
      if not path.is_file():
        continue
      file_set.add(path)
  files = sorted(file_set)

  if len(files) == 0:
    print("no files to patch!", file=stderr)
    return 0

  config.header(context)

  for file in files:
    patch = config.patch(config, file)
    patch.write(context)

  context.output.flush()
  context.output.close()

  return 0

if __name__ == "__main__":
  exit(main())
