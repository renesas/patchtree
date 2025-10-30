# https://www.sphinx-doc.org/en/master/usage/configuration.html

from os import environ
from pathlib import Path
from tomllib import loads as toml_loads
import sys

repo_root = Path(__file__).parent.parent

sys.path.insert(0, str(repo_root.resolve()))
import patchtree

project = "patchtree"
release = "???"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx_automodapi.automodapi",
]
templates_path = []
exclude_patterns = []
html_theme = "sphinx_rtd_theme"
html_static_path = []
autodoc_mock_imports = [project]

try:
    toml = repo_root.joinpath("pyproject.toml").read_text()
    pyproject = toml_loads(toml)
    release = pyproject["project"]["version"]
except:
    pass

if "RENESAS_INTERNAL" in environ:
    extensions.append("lpc_cs_sphinx_renesas_theme")
    html_theme = "lpc_cs_sphinx_renesas_theme"
