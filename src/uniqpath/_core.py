"""Unique path generation, with an optional atomic reservation mode."""

from __future__ import annotations

import errno
import logging
import os
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Union

from ._errors import MaxAttemptsError
from ._format import PlaceholderFormatter, is_constant, validate_format

__all__ = ["DEFAULT_MAX_NUM", "DEFAULT_SUFFIX_FORMAT", "reserve_path", "unique_path"]

PathLike = Union[str, "os.PathLike[str]"]

DEFAULT_SUFFIX_FORMAT = "_{num}"
DEFAULT_MAX_NUM = 50_000

_logger = logging.getLogger("uniqpath")
# A library configures no handlers of its own; the application decides.
_logger.addHandler(logging.NullHandler())


def _guess_is_dir(p: Path) -> bool:
    """Guess whether ``p`` denotes a directory, the way uniqpath always has."""
    return not (p.suffix != "" and not p.is_dir())


def _split(p: Path, is_dir: bool | None) -> tuple[Path, str, str]:
    """Split ``p`` into ``(parent, stem, extension)``.

    When ``is_dir`` is None the target kind is guessed from the suffix. Pass
    ``is_dir`` explicitly to override that guess -- it matters for names such
    as ``release.v1.0`` that do not exist yet.
    """
    if is_dir is None:
        is_dir = _guess_is_dir(p)
    ext = "" if is_dir else p.suffix
    base = p.name[: -len(ext)] if ext else p.name
    return p.parent, base, ext


def _candidates(
    p: Path,
    suffix_format: str,
    max_num: int,
    is_dir: bool | None,
    verbose: bool,
) -> Iterator[Path]:
    """Yield successive candidate paths for ``p``, at most ``max_num`` of them."""
    validate_format(suffix_format)
    constant = is_constant(suffix_format)

    parent, base, ext = _split(p, is_dir)
    formatter = PlaceholderFormatter(datetime.now())

    for num in range(1, max_num + 1):
        formatter.extra_vars["num"] = num
        candidate = parent / f"{base}{formatter.apply(suffix_format)}{ext}"
        if verbose:
            _logger.info("Trying: %s", candidate)
        yield candidate
        if constant:
            raise MaxAttemptsError(
                f"suffix_format {suffix_format!r} is constant, so {candidate} is "
                f"the only candidate for {p} and it is already taken. Add one of "
                f"{{num}}, {{rand}} or {{uuid}} to the format."
            )


def unique_path(
    path: PathLike,
    suffix_format: str = DEFAULT_SUFFIX_FORMAT,
    if_exists_only: bool = True,
    return_str: bool = False,
    max_num: int = DEFAULT_MAX_NUM,
    verbose: bool = False,
    is_dir: bool | None = None,
) -> Path | str:
    """Return a path that does not exist yet, derived from ``path``.

    A formatted suffix is inserted between the stem and the extension, and
    retried until the resulting path is free.

    Supported placeholders in ``suffix_format``:
        - ``{num}``       : attempt counter starting at 1 (``{num:03d}`` pads it)
        - ``{timestamp}`` : UNIX timestamp, in seconds
        - ``{date}``      : current datetime, accepts strftime specs such as
          ``{date:%Y-%m-%d}``
        - ``{uuid}``      : UUID4 hex string, ``{uuid:n}`` truncates it to n chars
        - ``{rand}``      : random alphanumeric string, ``{rand:n}`` sets its length
        - ``{pid}``       : current process id

    Warning:
        The returned path is free at the moment it is checked, but nothing
        reserves it. Two processes racing on the same directory can receive
        the same path. Use :func:`reserve_path` when that matters.

    Args:
        path: base file or directory path.
        suffix_format: suffix pattern, see the placeholders above.
        if_exists_only: return ``path`` untouched when it is already free.
        return_str: return a ``str`` instead of a :class:`~pathlib.Path`.
        max_num: how many candidates to try before giving up.
        verbose: log every attempt at INFO level.
        is_dir: treat the target as a directory (``True``) or a file
            (``False``). Defaults to ``None``: guess from the suffix.

    Returns:
        The first free path, as a :class:`~pathlib.Path` or a ``str``.

    Raises:
        MaxAttemptsError: no free path within ``max_num`` attempts. Also a
            ``RuntimeError``, as in uniqpath < 0.2.
        InvalidFormatError: unknown or malformed placeholder. Also a
            ``KeyError``, as in uniqpath < 0.2.
    """
    p = Path(path)
    _configure_logging(verbose)
    validate_format(suffix_format)

    if if_exists_only and not p.exists():
        if verbose:
            _logger.info("Returning original path: %s", p)
        return str(p) if return_str else p

    for candidate in _candidates(p, suffix_format, max_num, is_dir, verbose):
        if not candidate.exists():
            if verbose:
                _logger.info("Found: %s", candidate)
            return str(candidate) if return_str else candidate

    raise MaxAttemptsError(
        f"Failed to find a unique path after {max_num} attempts for base path: "
        f"{p}. Try a different `suffix_format` or a larger `max_num`."
    )


def reserve_path(
    path: PathLike,
    suffix_format: str = DEFAULT_SUFFIX_FORMAT,
    if_exists_only: bool = True,
    return_str: bool = False,
    max_num: int = DEFAULT_MAX_NUM,
    verbose: bool = False,
    is_dir: bool | None = None,
    parents: bool = True,
) -> Path | str:
    """Create a unique path atomically and return it.

    Same suffix logic as :func:`unique_path`, but the winning candidate is
    *created* -- an empty file via ``O_CREAT | O_EXCL``, or a directory via
    ``mkdir`` -- in the very operation that tests it. Two processes calling
    this concurrently on the same base path can never be handed the same
    path: the loser gets ``FileExistsError`` and moves on to the next
    candidate.

    Args:
        path: base file or directory path.
        suffix_format: suffix pattern, see :func:`unique_path`.
        if_exists_only: try to create ``path`` itself first.
        return_str: return a ``str`` instead of a :class:`~pathlib.Path`.
        max_num: how many candidates to try before giving up.
        verbose: log every attempt at INFO level.
        is_dir: create a directory (``True``) or an empty file (``False``).
            Defaults to ``None``: guess from the suffix.
        parents: create missing parent directories first.

    Returns:
        The path that was created, as a :class:`~pathlib.Path` or a ``str``.

    Raises:
        MaxAttemptsError: every candidate was taken by someone else.
        OSError: the filesystem refused the creation for any reason other
            than the path already existing.
    """
    p = Path(path)
    _configure_logging(verbose)
    validate_format(suffix_format)

    if is_dir is None:
        is_dir = _guess_is_dir(p)

    if parents:
        p.parent.mkdir(parents=True, exist_ok=True)

    if if_exists_only and _try_create(p, is_dir):
        if verbose:
            _logger.info("Reserved original path: %s", p)
        return str(p) if return_str else p

    for candidate in _candidates(p, suffix_format, max_num, is_dir, verbose):
        if _try_create(candidate, is_dir):
            if verbose:
                _logger.info("Reserved: %s", candidate)
            return str(candidate) if return_str else candidate

    raise MaxAttemptsError(
        f"Failed to reserve a unique path after {max_num} attempts for base "
        f"path: {p}. Try a different `suffix_format` or a larger `max_num`."
    )


def _try_create(candidate: Path, is_dir: bool) -> bool:
    """Atomically create ``candidate``; return False if it already existed."""
    try:
        if is_dir:
            candidate.mkdir()
        else:
            os.close(os.open(candidate, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o666))
    except FileExistsError:
        return False
    except OSError as exc:  # some filesystems report EEXIST without the subclass
        if exc.errno == errno.EEXIST:
            return False
        raise
    return True


def _configure_logging(verbose: bool) -> None:
    """Make INFO records reach handlers when the caller asked for them.

    Only the ``uniqpath`` logger's level is touched. Installing handlers is
    the application's job -- see ``cli.py`` for how the CLI does it.
    """
    if verbose and _logger.level > logging.INFO:
        _logger.setLevel(logging.INFO)
