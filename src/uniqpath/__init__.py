"""Generate unique file or directory paths with flexible formatting."""

from __future__ import annotations

from ._core import (
    DEFAULT_MAX_NUM,
    DEFAULT_SUFFIX_FORMAT,
    reserve_path,
    unique_path,
)
from ._errors import InvalidFormatError, MaxAttemptsError, UniqPathError
from ._format import SUPPORTED_PLACEHOLDERS, PlaceholderFormatter
from ._open import uniq_open

__version__ = "0.2.0"

__all__ = [
    "DEFAULT_MAX_NUM",
    "DEFAULT_SUFFIX_FORMAT",
    "SUPPORTED_PLACEHOLDERS",
    "InvalidFormatError",
    "MaxAttemptsError",
    "PlaceholderFormatter",
    "UniqPathError",
    "__version__",
    "reserve_path",
    "uniq_open",
    "unique_path",
]
