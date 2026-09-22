"""Exception hierarchy for :mod:`uniqpath`.

Every exception derives from :class:`UniqPathError` *and* from the builtin
exception the pre-0.2 API used to raise, so existing ``except RuntimeError``
or ``except KeyError`` handlers keep working.
"""

from __future__ import annotations

__all__ = ["InvalidFormatError", "MaxAttemptsError", "UniqPathError"]


class UniqPathError(Exception):
    """Base class for all errors raised by :mod:`uniqpath`."""


class MaxAttemptsError(UniqPathError, RuntimeError):
    """No unique path was found within ``max_num`` attempts."""


class InvalidFormatError(UniqPathError, KeyError):
    """``suffix_format`` contains an unknown or malformed placeholder."""

    def __str__(self) -> str:  # KeyError.__str__ would add quotes
        return self.args[0] if self.args else ""
