"""Placeholder expansion for suffix format strings."""

from __future__ import annotations

import os
import random
import re
import string
import uuid
from datetime import datetime
from re import Match
from typing import Any

from ._errors import InvalidFormatError

__all__ = [
    "SUPPORTED_PLACEHOLDERS",
    "PlaceholderFormatter",
    "is_constant",
    "supported_placeholders",
    "validate_format",
]

#: Placeholders accepted in ``suffix_format``, in documentation order.
SUPPORTED_PLACEHOLDERS = ("num", "timestamp", "date", "rand", "uuid", "pid")


def supported_placeholders() -> str:
    """Human-readable list of the accepted placeholders, for error messages."""
    return ", ".join("{" + name + "}" for name in SUPPORTED_PLACEHOLDERS)


_ALPHABET = string.ascii_letters + string.digits

# ``{rand}`` and ``{uuid}`` take a *length* after the colon rather than a
# str.format spec, so they are expanded before str.format runs. The negative
# lookbehind keeps ``{{rand}}`` escaped, exactly as str.format would.
_RAND_RE = re.compile(r"(?<!\{)\{rand(?::(\d+))?\}")
_UUID_RE = re.compile(r"(?<!\{)\{uuid(?::(\d+))?\}")

# Any ``{name}`` or ``{name:spec}``, ignoring escaped ``{{``/``}}``.
_FIELD_RE = re.compile(r"(?<!\{)\{([a-zA-Z_][a-zA-Z_0-9]*)(?::[^{}]*)?\}")

# A format string that expands to the same value on every attempt would loop
# forever; only these placeholders make a suffix vary between attempts.
_VARYING = frozenset({"num", "rand", "uuid"})


class PlaceholderFormatter:
    """Expand the placeholders of a suffix format string.

    The formatter captures ``now`` once at construction time so that every
    attempt within a single :func:`~uniqpath.unique_path` call shares the same
    timestamp, and only the varying placeholders differ.
    """

    def __init__(self, now: datetime, extra_vars: dict[str, Any] | None = None):
        self.now = now
        self.extra_vars: dict[str, Any] = dict(extra_vars or {})
        self.random = random.SystemRandom()

    # -- placeholder expansion -------------------------------------------------

    def _rand(self, match: Match[str]) -> str:
        length = int(match.group(1)) if match.group(1) else 6
        return "".join(self.random.choices(_ALPHABET, k=length))

    def _uuid(self, match: Match[str]) -> str:
        length = int(match.group(1)) if match.group(1) else 32
        return uuid.uuid4().hex[:length]

    def _namespace(self) -> dict[str, Any]:
        ns: dict[str, Any] = {
            "timestamp": int(self.now.timestamp()),
            "date": self.now,
            "pid": os.getpid(),
        }
        ns.update(self.extra_vars)
        return ns

    def apply(self, fmt: str) -> str:
        """Return ``fmt`` with every placeholder replaced by its value."""
        expanded = _RAND_RE.sub(self._rand, fmt)
        expanded = _UUID_RE.sub(self._uuid, expanded)
        try:
            return expanded.format(**self._namespace())
        except KeyError as exc:
            raise InvalidFormatError(
                f"Unknown placeholder {exc} in suffix_format {fmt!r}. "
                f"Supported: {supported_placeholders()}"
            ) from exc
        except (ValueError, IndexError) as exc:
            raise InvalidFormatError(f"Malformed suffix_format {fmt!r}: {exc}") from exc


def validate_format(fmt: str) -> None:
    """Raise :class:`InvalidFormatError` if ``fmt`` uses an unknown placeholder."""
    unknown = set(_FIELD_RE.findall(fmt)) - set(SUPPORTED_PLACEHOLDERS)
    if unknown:
        raise InvalidFormatError(
            f"Unknown placeholder(s) {sorted(unknown)} in suffix_format {fmt!r}. "
            f"Supported: {supported_placeholders()}"
        )


def is_constant(fmt: str) -> bool:
    """Whether ``fmt`` expands to the same value on every attempt.

    A constant format is still usable -- it just cannot be retried, since
    every attempt would produce the very same candidate path.
    """
    return not set(_FIELD_RE.findall(fmt)) & _VARYING
