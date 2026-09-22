"""uniq_open(): reserve and open in one step."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

from uniqpath import InvalidFormatError, MaxAttemptsError, uniq_open


def test_writes_to_the_base_path_when_free(tmp_path):
    target = tmp_path / "out.txt"
    with uniq_open(target) as f:
        f.write("hello")
    assert target.read_text() == "hello"


def test_suffixes_when_the_base_path_is_taken(tmp_path):
    (tmp_path / "out.txt").write_text("existing")
    with uniq_open(tmp_path / "out.txt") as f:
        f.write("new")
    assert (tmp_path / "out.txt").read_text() == "existing"
    assert (tmp_path / "out_1.txt").read_text() == "new"


def test_name_exposes_the_path_actually_used(tmp_path):
    (tmp_path / "out.txt").write_text("x")
    with uniq_open(tmp_path / "out.txt") as f:
        used = Path(f.name)
    assert used.name == "out_1.txt"


def test_file_is_closed_on_exit(tmp_path):
    with uniq_open(tmp_path / "out.txt") as f:
        pass
    assert f.closed


def test_file_is_closed_even_when_the_body_raises(tmp_path):
    with pytest.raises(ZeroDivisionError), uniq_open(tmp_path / "out.txt") as f:
        f.write(str(1 / 0))
    assert f.closed


def test_binary_mode(tmp_path):
    with uniq_open(tmp_path / "blob.bin", "wb") as f:
        f.write(b"\x00\xff")
    assert (tmp_path / "blob.bin").read_bytes() == b"\x00\xff"


def test_encoding_is_honoured(tmp_path):
    with uniq_open(tmp_path / "text.txt", encoding="utf-8") as f:
        f.write("héllo 漢字")
    assert (tmp_path / "text.txt").read_text(encoding="utf-8") == "héllo 漢字"


def test_exclusive_mode_is_accepted(tmp_path):
    """'x' is redundant after a reservation, but must not blow up."""
    (tmp_path / "out.txt").write_text("x")
    with uniq_open(tmp_path / "out.txt", "x") as f:
        f.write("new")
    assert (tmp_path / "out_1.txt").read_text() == "new"


def test_append_mode_is_accepted(tmp_path):
    with uniq_open(tmp_path / "out.txt", "a") as f:
        f.write("one")
    assert (tmp_path / "out.txt").read_text() == "one"


@pytest.mark.parametrize("mode", ["r", "rb", "r+"])
def test_read_modes_are_rejected(tmp_path, mode):
    with (
        pytest.raises(ValueError, match="writing mode"),
        uniq_open(tmp_path / "out.txt", mode),
    ):
        pass


def test_custom_suffix_format(tmp_path):
    (tmp_path / "out.txt").write_text("x")
    with uniq_open(tmp_path / "out.txt", suffix_format="_{num:03d}") as f:
        assert Path(f.name).name == "out_001.txt"


def test_invalid_suffix_format_is_rejected(tmp_path):
    with (
        pytest.raises(InvalidFormatError),
        uniq_open(tmp_path / "out.txt", suffix_format="_{nope}"),
    ):
        pass


def test_creates_missing_parents(tmp_path):
    with uniq_open(tmp_path / "deep" / "nested" / "out.txt") as f:
        f.write("x")
    assert (tmp_path / "deep" / "nested" / "out.txt").read_text() == "x"


def test_max_num_is_honoured(tmp_path):
    (tmp_path / "out.txt").write_text("x")
    (tmp_path / "out_1.txt").write_text("x")
    with pytest.raises(MaxAttemptsError), uniq_open(tmp_path / "out.txt", max_num=1):
        pass


def test_dotted_name_is_treated_as_a_file(tmp_path):
    """uniq_open always writes a file, never a directory."""
    (tmp_path / "release.v1.0").write_text("x")
    with uniq_open(tmp_path / "release.v1.0") as f:
        assert Path(f.name).name == "release.v1_1.0"


def test_concurrent_writers_never_share_a_file(tmp_path):
    base = tmp_path / "shared.txt"
    base.write_text("taken")
    workers = 16
    barrier = Barrier(workers)

    def write(index):
        barrier.wait()
        with uniq_open(base) as f:
            f.write(str(index))
            return f.name

    with ThreadPoolExecutor(max_workers=workers) as pool:
        names = list(pool.map(write, range(workers)))

    assert len(set(names)) == workers
    # Nobody clobbered anybody: each file holds exactly one writer's payload.
    written = sorted(int(Path(n).read_text()) for n in names)
    assert written == sorted(range(workers))
