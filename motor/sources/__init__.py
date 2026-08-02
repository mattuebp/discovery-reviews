"""Adapters package. Re-exports the `ReviewSource` port so callers can do
`from motor.sources import ReviewSource` instead of reaching into `base`.
"""

from .base import ReviewSource

__all__ = ["ReviewSource"]
