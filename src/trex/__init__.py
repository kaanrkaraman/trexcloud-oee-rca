"""trexCloud hackathon foundation package.

Submodules:
  loaders  — encoding-aware, boolean-correct CSV loaders + machine master
  signals  — canonical semantic signal map (vendor-agnostic roles)
  oee      — recompute A / P / Q / OEE from oee_summary JSON components
"""
from . import loaders, signals, oee  # noqa: F401

__all__ = ["loaders", "signals", "oee"]
