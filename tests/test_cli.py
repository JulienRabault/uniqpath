"""Command line interface."""

import pytest

from uniqpath import __version__
from uniqpath.cli import main


@pytest.fixture
def cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def run(capsys, *argv):
    code = main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out.strip(), captured.err.strip()


def test_prints_the_original_path_when_free(cwd, capsys):
    code, out, _ = run(capsys, "out.txt")
    assert code == 0
    assert out == "out.txt"


def test_suffixes_when_taken(cwd, capsys):
    (cwd / "out.txt").write_text("x")
    code, out, _ = run(capsys, "out.txt")
    assert code == 0
    assert out == "out_1.txt"


def test_custom_format(cwd, capsys):
    (cwd / "run.log").write_text("x")
    _, out, _ = run(capsys, "run.log", "--format", "_{num:03d}")
    assert out == "run_001.log"


def test_always_suffix(cwd, capsys):
    _, out, _ = run(capsys, "out.txt", "--always-suffix")
    assert out == "out_1.txt"


def test_reserve_creates_the_file(cwd, capsys):
    code, out, _ = run(capsys, "out.txt", "--reserve")
    assert code == 0
    assert (cwd / out).is_file()


def test_reserve_creates_the_directory(cwd, capsys):
    code, out, _ = run(capsys, "results", "--dir", "--reserve")
    assert code == 0
    assert (cwd / out).is_dir()


def test_dir_flag_keeps_dotted_names_intact(cwd, capsys):
    (cwd / "release.v1.0").mkdir()
    _, out, _ = run(capsys, "release.v1.0", "--dir")
    assert out == "release.v1.0_1"


def test_file_flag_splits_the_extension(cwd, capsys):
    (cwd / "release.v1.0").mkdir()
    _, out, _ = run(capsys, "release.v1.0", "--file")
    assert out == "release.v1_1.0"


def test_unknown_placeholder_exits_with_error(cwd, capsys):
    code, out, err = run(capsys, "out.txt", "--always-suffix", "--format", "_{nope}")
    assert code == 1
    assert out == ""
    assert "Unknown placeholder" in err


def test_max_num_is_honoured(cwd, capsys):
    (cwd / "out.txt").write_text("x")
    (cwd / "out_1.txt").write_text("x")
    code, _, err = run(capsys, "out.txt", "--max-num", "1")
    assert code == 1
    assert "after 1 attempts" in err


def test_dir_and_file_are_mutually_exclusive(cwd):
    with pytest.raises(SystemExit):
        main(["out.txt", "--dir", "--file"])


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_help_lists_the_placeholders(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    assert "{num}" in out and "{rand}" in out


def test_oserror_exits_with_error(cwd, capsys, monkeypatch):
    import os

    def boom(*args, **kwargs):
        raise PermissionError(13, "denied")

    monkeypatch.setattr(os, "open", boom)
    code, out, err = run(capsys, "out.txt", "--reserve")
    assert code == 1
    assert out == ""
    assert "denied" in err
