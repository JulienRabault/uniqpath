import logging
import random
import re
import string
import uuid
from datetime import datetime
from pathlib import Path
from typing import Union, Dict


class PlaceholderFormatter:
    def __init__(self, now: datetime, extra_vars: Dict[str, str]):
        self.now = now
        self.extra_vars = extra_vars
        self.random = random.Random()

        self.rand_regex = re.compile(r'\{rand(?::(\d+))?\}')
        self.uuid_regex = re.compile(r'\{uuid(?::(\d+))?\}')

    def _rand(self, match: re.Match) -> str:
        length = int(match.group(1)) if match.group(1) else 6
        return ''.join(self.random.choices(string.ascii_letters + string.digits, k=length))

    def _uuid(self, match: re.Match) -> str:
        length = int(match.group(1)) if match.group(1) else 32
        return uuid.uuid4().hex[:length]

    def apply(self, fmt: str) -> str:
        fmt = self.rand_regex.sub(self._rand, fmt)
        fmt = self.uuid_regex.sub(self._uuid, fmt)
        return fmt.format(**self.extra_vars)


def unique_path(
        path: Union[str, Path],
        suffix_format: str = "_{num}",
        verbose: bool = False,
        if_exists_only: bool = True,
        return_str: bool = False,
) -> Union[Path, str]:
    """
    Generate a unique file or directory path by appending a formatted suffix.
    The suffix is incremented until a non-existing path is found (if needed).

    Supported placeholders in suffix_format:
        - {num}       : incrementing integer starting from 1
        - {timestamp} : UNIX timestamp as integer
        - {uuid[:n]}  : UUID4 hex string truncated to n chars (default 32)
        - {rand[:n]}  : random alphanumeric string of length n (default 6)

    Notes:
        - Concurrency is NOT handled and may cause collisions.
        - Date placeholders replaced literally, no strftime support.

    Args:
        path (str or Path): base path.
        suffix_format (str): suffix format string.
        verbose (bool): log attempts if True.
        if_exists_only (bool): add suffix only if path exists.
        return_str (bool): return path as string if True.

    Returns:
        Path or str: unique path.
    """
    logger = logging.getLogger(__name__)
    if verbose and not logger.hasHandlers():
        logging.basicConfig(level=logging.INFO)
        logger.setLevel(logging.INFO)

    p = Path(path)
    now = datetime.now()

    extra_vars = {
        'timestamp': int(now.timestamp()),
    }

    if if_exists_only and not p.exists():
        if verbose:
            logger.info(f"Returning original path: {p}")
        return str(p) if return_str else p

    ext = p.suffix
    base = p.name[:-len(ext)] if ext else p.name
    parent = p.parent

    formatter = PlaceholderFormatter(now, extra_vars)
    num = 1

    while True:
        extra_vars['num'] = num
        try:
            suffix = formatter.apply(suffix_format)
        except KeyError as e:
            raise KeyError(f"Missing placeholder in suffix_format: {e}")

        candidate = parent / f"{base}{suffix}{ext}"
        if verbose:
            logger.info(f"Trying: {candidate}")
        if not candidate.exists():
            if verbose:
                logger.info(f"Found: {candidate}")
            return str(candidate) if return_str else candidate
        num += 1
