from __future__ import annotations
from typing import TYPE_CHECKING, Any

from jinja2 import Environment

if TYPE_CHECKING:
  from .context import Context

class Process:
  context: Context

  def __init__(self, context: Context):
    self.context = context

  def transform(self, input: str) -> str:
    return input

class ProcessJinja2(Process):
  environment: Environment = Environment(
    trim_blocks=True,
    lstrip_blocks=True,
  )

  def transform(self, input: str) -> str:
    template_vars = self.get_template_vars()
    return self.environment.from_string(input).render(**template_vars)

  def get_template_vars(self) -> dict[str, Any]:
    return {}

class ProcessCoccinelle(Process):
  pass

