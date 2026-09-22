"""Open a file for writing under a name that was not taken."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Any

from ._core import DEFAULT_MAX_NUM, DEFAULT_SUFFIX_FORMAT, PathLike, reserve_path

__all__ = ["uniq_open"]

# Reading an file that is unique by construction would always read nothing.
_WRITE_INTENTS = ("w", "x", "a")


@contextmanager
def uniq_open(
    path: PathLike,
    mode: str = "w",
    *,
    suffix_format: str = DEFAULT_SUFFIX_FORMAT,
    if_exists_only: bool = True,
    max_num: int = DEFAULT_MAX_NUM,
    parents: bool = True,
    buffering: int = -1,
    encoding: str | None = None,
    errors: str | None = None,
    newline: str | None = None,
) -> Iterator[IO[Any]]:
    """Reserve a free path and open it, in one step.

    This is :func:`reserve_path` plus :func:`open`, for the common case where
    you were going to write to the path anyway::

        with uniq_open("results.csv") as f:
            f.write("...")
            print("wrote", f.name)      # results_3.csv

    The path is reserved atomically before it is opened, so concurrent callers
    never write to the same file -- unlike ``open(unique_path(...), "w")``,
    where another process can slip in between the two calls.

    ``f.name`` holds the path that was actually used.

    Args:
        path: base file path.
        mode: any writing mode accepted by :func:`open` (``w``, ``a``, ``x``
            and their ``b``/``+`` variants). ``x`` behaves like ``w``, since
            the reservation already guarantees the file is new.
        suffix_format: suffix pattern, see :func:`~uniqpath.unique_path`.
        if_exists_only: use ``path`` itself when it is free.
        max_num: how many candidates to try before giving up.
        parents: create missing parent directories.
        buffering, encoding, errors, newline: passed straight to :func:`open`.

    Yields:
        The open file object.

    Raises:
        ValueError: ``mode`` is not a writing mode.
        MaxAttemptsError: no free path within ``max_num`` attempts.

    Note:
        If the body raises, the reserved file stays on disk -- possibly empty.
        Deleting it is left to you, because uniqpath cannot tell a failed run
        from a run that wrote something worth keeping.
    """
    if not any(intent in mode for intent in _WRITE_INTENTS):
        raise ValueError(
            f"uniq_open() needs a writing mode, got {mode!r}. "
            f"A freshly reserved file has nothing to read."
        )

    reserved = reserve_path(
        path,
        suffix_format=suffix_format,
        if_exists_only=if_exists_only,
        max_num=max_num,
        is_dir=False,
        parents=parents,
    )

    # The reservation created the file, so an exclusive mode would now fail on
    # our own file. We already hold it exclusively; "w" is the honest mode.
    handle = Path(reserved).open(  # noqa: SIM115 -- closed in the finally below
        mode.replace("x", "w"),
        buffering=buffering,
        encoding=encoding,
        errors=errors,
        newline=newline,
    )
    try:
        yield handle
    finally:
        handle.close()
