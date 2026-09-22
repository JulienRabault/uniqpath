"""Concurrency guarantees.

``reserve_path`` must hand out a distinct, really-created path to every
caller, even under maximum contention. ``unique_path`` makes no such promise
-- it only reports what was free at the time it looked.
"""

import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

from uniqpath import reserve_path

WORKERS = 16


def _reserve_after_barrier(args):
    base, barrier = args
    barrier.wait()
    return reserve_path(base, suffix_format="_{num}")


def _reserve_in_subprocess(base_str):
    """Top-level so it survives the spawn start method on Windows/macOS."""
    return str(reserve_path(base_str, suffix_format="_{num}"))


def test_threads_never_receive_the_same_file(tmp_path):
    base = tmp_path / "out.txt"
    base.write_text("taken")
    barrier = Barrier(WORKERS)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(_reserve_after_barrier, [(base, barrier)] * WORKERS))

    assert len({str(p) for p in results}) == WORKERS
    assert all(p.is_file() for p in results)


def test_threads_never_receive_the_same_directory(tmp_path):
    base = tmp_path / "run"
    base.mkdir()
    barrier = Barrier(WORKERS)

    def reserve(_):
        barrier.wait()
        return reserve_path(base, is_dir=True)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(reserve, range(WORKERS)))

    assert len({str(p) for p in results}) == WORKERS
    assert all(p.is_dir() for p in results)


def test_reservations_are_dense(tmp_path):
    """Every slot from 1..N is used exactly once: no gap, no duplicate."""
    base = tmp_path / "out.txt"
    base.write_text("taken")
    barrier = Barrier(WORKERS)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(_reserve_after_barrier, [(base, barrier)] * WORKERS))

    nums = sorted(int(p.stem.rsplit("_", 1)[1]) for p in results)
    assert nums == list(range(1, WORKERS + 1))


@pytest.mark.skipif(
    os.environ.get("UNIQPATH_SKIP_PROCESS_TESTS") == "1",
    reason="process pool disabled in this environment",
)
def test_processes_never_receive_the_same_file(tmp_path):
    base = tmp_path / "shared.txt"
    base.write_text("taken")
    n = 8

    with ProcessPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(_reserve_in_subprocess, [str(base)] * n))

    assert len(set(results)) == n
    assert all(Path(r).is_file() for r in results)
