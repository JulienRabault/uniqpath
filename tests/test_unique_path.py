import os
import re
from pathlib import Path

import pytest

from uniqpath import unique_path


@pytest.fixture
def tmp_file(tmp_path):
    file = tmp_path / "example.txt"
    file.write_text("dummy")
    return file


def test_unique_path_increments(tmp_file):
    path1 = unique_path(tmp_file, suffix_format="_{num}")
    path1.touch()
    path2 = unique_path(tmp_file, suffix_format="_{num}")
    assert path1 != path2
    assert re.match(r".*_1\.txt", path1.name)
    assert re.match(r".*_2\.txt", path2.name)


def test_unique_path_rand(tmp_file):
    path = unique_path(tmp_file, suffix_format="_{rand:6}")
    match = re.match(r".*_[a-zA-Z0-9]{6}\.txt", path.name)
    assert match is not None


def test_unique_path_uuid(tmp_file):
    path = unique_path(tmp_file, suffix_format="_{uuid:8}")
    match = re.match(r".*_[a-f0-9]{8}\.txt", path.name)
    assert match is not None


def test_unique_path_timestamp(tmp_file):
    path = unique_path(tmp_file, suffix_format="_{timestamp}")
    match = re.match(r".*_\d{10}\.txt", path.name)
    assert match is not None


def test_unique_path_without_extension(tmp_path):
    folder = tmp_path / "run"
    folder.mkdir()
    path = unique_path(folder, suffix_format="_{num}")
    assert path.name.startswith("run_")
    assert not path.exists()


def test_unique_path_returns_original_if_available(tmp_path):
    candidate = tmp_path / "fresh.txt"
    path = unique_path(candidate)
    assert path == candidate
    assert not path.exists()


def test_unique_path_raises_on_conflicting_reserved_kwarg(tmp_file):
    with pytest.raises(TypeError):
        unique_path(tmp_file, suffix_format="_{num}", num=5)


def test_unique_path_on_directory(tmp_path):
    folder = tmp_path / "results"
    folder.mkdir()
    p1 = unique_path(folder, suffix_format="_{num}")
    os.mkdir(p1)
    p2 = unique_path(folder, suffix_format="_{num}")
    assert p1.name == "results_1"
    assert p2.name == "results_2"


def test_unique_path_with_relative_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (Path("output.txt")).write_text("data")
    path = unique_path("output.txt", suffix_format="_{num}")
    assert isinstance(path, Path)
    assert path.name.startswith("output_")
    assert not path.exists()


def test_unique_path_multiple_calls(tmp_file):
    created_paths = []
    for _ in range(5):
        p = unique_path(tmp_file, suffix_format="_{num}")
        p.touch()
        created_paths.append(p)
    names = [p.name for p in created_paths]
    assert all(re.match(r"example_\d+\.txt", name) for name in names)
    assert len(set(names)) == len(names)


def test_unique_path_return_str(tmp_file):
    path_str = unique_path(tmp_file, suffix_format="_{num}", return_str=True)
    assert isinstance(path_str, str)
    assert re.match(r".*_1\.txt", path_str)
    path_obj = unique_path(tmp_file, suffix_format="_{num}", return_str=False)
    assert isinstance(path_obj, Path)


def test_unique_path_if_exists_only(tmp_path):
    file = tmp_path / "file.txt"
    file.write_text("content")
    path1 = unique_path(file, suffix_format="_{num}", if_exists_only=True)
    assert path1.name == "file_1.txt"
    new_file = tmp_path / "newfile.txt"
    path2 = unique_path(new_file, suffix_format="_{num}", if_exists_only=False)
    assert path2.name == "newfile_1.txt"
    path3 = unique_path(new_file, suffix_format="_{num}", if_exists_only=True)
    assert path3 == new_file


def test_unique_path_multiple_calls_varied_suffix(tmp_file):
    suffixes = ["_{num}", "_{rand:4}", "_{uuid:6}"]
    created_paths = []
    for suffix_format in suffixes:
        for _ in range(3):
            p = unique_path(tmp_file, suffix_format=suffix_format)
            p.touch()
            created_paths.append((p, suffix_format))
    names = [p.name for p, _ in created_paths]

    for p, suffix_format in created_paths:
        if "{num}" in suffix_format:
            assert re.match(r"example_\d+\.txt", p.name)
        elif "{rand" in suffix_format:
            assert re.match(r"example_[a-zA-Z0-9]{4}\.txt", p.name)
        elif "{uuid" in suffix_format:
            assert re.match(r"example_[a-f0-9]{6}\.txt", p.name)

    assert len(set(names)) == len(names)


def test_regression_suffix_format_default(tmp_path):
    base = tmp_path / "file.txt"
    base.write_text("x")
    p = unique_path(base)
    assert p.name == "file_1.txt"


def test_regression_suffix_with_multiple_placeholders(tmp_path):
    base = tmp_path / "log.txt"
    base.write_text("log")
    p = unique_path(base, suffix_format="_{num}_{rand:6}")
    assert re.match(r"log_\d+_[a-zA-Z0-9]{6}\.txt", p.name)


def test_regression_suffix_on_dir(tmp_path):
    d = tmp_path / "output"
    d.mkdir()
    p = unique_path(d, suffix_format="_{num}")
    assert p.name.startswith("output_")
    assert not p.exists()


def test_regression_path_with_dot_in_name(tmp_path):
    f = tmp_path / "a.b.c.txt"
    f.write_text("data")
    p = unique_path(f, suffix_format="_{num}")
    assert p.suffix == ".txt"
    assert p.name.startswith("a.b.c_")
