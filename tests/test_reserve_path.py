"""Atomic reservation: reserve_path creates what it returns."""

import pytest

from uniqpath import MaxAttemptsError, reserve_path


def test_reserves_the_base_path_when_free(tmp_path):
    p = reserve_path(tmp_path / "out.txt")
    assert p == tmp_path / "out.txt"
    assert p.is_file()


def test_reserved_file_is_empty(tmp_path):
    p = reserve_path(tmp_path / "out.txt")
    assert p.read_bytes() == b""


def test_suffixes_when_the_base_path_is_taken(tmp_path):
    (tmp_path / "out.txt").write_text("existing")
    p = reserve_path(tmp_path / "out.txt")
    assert p.name == "out_1.txt"
    assert p.is_file()


def test_each_call_returns_a_fresh_path(tmp_path):
    base = tmp_path / "run.log"
    paths = [reserve_path(base) for _ in range(5)]
    assert len({p.name for p in paths}) == 5
    assert all(p.is_file() for p in paths)
    assert [p.name for p in paths[1:]] == [f"run_{i}.log" for i in range(1, 5)]


def test_reserves_directories(tmp_path):
    d = reserve_path(tmp_path / "results", is_dir=True)
    assert d.is_dir()
    d2 = reserve_path(tmp_path / "results", is_dir=True)
    assert d2.name == "results_1"
    assert d2.is_dir()


def test_creates_missing_parents_by_default(tmp_path):
    p = reserve_path(tmp_path / "deep" / "nested" / "out.txt")
    assert p.is_file()


def test_parents_false_propagates_the_oserror(tmp_path):
    with pytest.raises(OSError):
        reserve_path(tmp_path / "missing" / "out.txt", parents=False)


def test_always_suffix_skips_the_base_path(tmp_path):
    p = reserve_path(tmp_path / "out.txt", if_exists_only=False)
    assert p.name == "out_1.txt"
    assert not (tmp_path / "out.txt").exists()


def test_return_str(tmp_path):
    p = reserve_path(tmp_path / "out.txt", return_str=True)
    assert isinstance(p, str)


def test_raises_when_every_candidate_is_taken(tmp_path):
    base = tmp_path / "out.txt"
    base.write_text("x")
    for i in range(1, 4):
        (tmp_path / f"out_{i}.txt").write_text("x")
    with pytest.raises(MaxAttemptsError):
        reserve_path(base, max_num=3)


def test_max_attempts_error_is_a_runtimeerror(tmp_path):
    base = tmp_path / "out.txt"
    base.write_text("x")
    (tmp_path / "out_1.txt").write_text("x")
    with pytest.raises(RuntimeError):
        reserve_path(base, max_num=1)


def test_does_not_clobber_an_existing_file(tmp_path):
    taken = tmp_path / "out.txt"
    taken.write_text("precious")
    reserve_path(taken)
    assert taken.read_text() == "precious"


def test_uuid_format_reserves_too(tmp_path):
    base = tmp_path / "blob.bin"
    base.write_text("x")
    p = reserve_path(base, suffix_format="_{uuid:8}")
    assert p.is_file()
    assert len(p.stem) == len("blob_") + 8


def test_verbose_reservation_logs(tmp_path, caplog):
    import logging

    with caplog.at_level(logging.INFO, logger="uniqpath"):
        reserve_path(tmp_path / "out.txt", verbose=True)
    assert any("Reserved" in r.message for r in caplog.records)


def test_unexpected_oserror_is_propagated(tmp_path, monkeypatch):
    """Only EEXIST means 'try the next candidate'; anything else must surface."""
    import os

    def boom(*args, **kwargs):
        raise PermissionError(13, "denied")

    monkeypatch.setattr(os, "open", boom)
    with pytest.raises(PermissionError):
        reserve_path(tmp_path / "out.txt")
