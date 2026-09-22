"""Public API surface, the is_dir override, and error contracts."""

import logging

import pytest

import uniqpath
from uniqpath import (
    InvalidFormatError,
    MaxAttemptsError,
    UniqPathError,
    unique_path,
)

# -- exported surface ------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "unique_path",
        "reserve_path",
        "UniqPathError",
        "MaxAttemptsError",
        "InvalidFormatError",
        "PlaceholderFormatter",
        "SUPPORTED_PLACEHOLDERS",
        "__version__",
    ],
)
def test_public_names_are_exported(name):
    assert hasattr(uniqpath, name)
    assert name in uniqpath.__all__


def test_version_is_a_release_string():
    assert uniqpath.__version__.count(".") == 2


def test_package_ships_a_py_typed_marker():
    from pathlib import Path

    assert (Path(uniqpath.__file__).parent / "py.typed").is_file()


# -- error hierarchy -------------------------------------------------------


def test_errors_share_a_common_base():
    assert issubclass(MaxAttemptsError, UniqPathError)
    assert issubclass(InvalidFormatError, UniqPathError)


def test_max_attempts_stays_a_runtimeerror():
    """uniqpath < 0.2 raised RuntimeError; old handlers must keep catching."""
    assert issubclass(MaxAttemptsError, RuntimeError)


def test_invalid_format_stays_a_keyerror():
    assert issubclass(InvalidFormatError, KeyError)


def test_invalid_format_message_is_not_quoted():
    """Plain KeyError would render the message with surrounding quotes."""
    assert str(InvalidFormatError("boom")) == "boom"


def test_unique_path_raises_after_max_num(tmp_path):
    base = tmp_path / "f.txt"
    base.write_text("x")
    (tmp_path / "f_1.txt").write_text("x")
    (tmp_path / "f_2.txt").write_text("x")
    with pytest.raises(MaxAttemptsError, match="after 2 attempts"):
        unique_path(base, max_num=2)


# -- is_dir override -------------------------------------------------------


def test_is_dir_true_keeps_a_dotted_name_intact(tmp_path):
    d = tmp_path / "release.v1.0"
    d.mkdir()
    assert unique_path(d, is_dir=True).name == "release.v1.0_1"


def test_is_dir_true_on_a_path_that_does_not_exist_yet(tmp_path):
    """The legacy guess would split '.0' off as an extension here."""
    target = tmp_path / "release.v1.0"
    assert unique_path(target, if_exists_only=False, is_dir=True).name == (
        "release.v1.0_1"
    )


def test_is_dir_false_forces_extension_splitting(tmp_path):
    d = tmp_path / "archive.tar"
    d.mkdir()
    assert unique_path(d, is_dir=False).name == "archive_1.tar"


def test_is_dir_none_keeps_the_legacy_guess(tmp_path):
    f = tmp_path / "data.txt"
    f.write_text("x")
    assert unique_path(f).name == "data_1.txt"


# -- verbose logging -------------------------------------------------------


def test_verbose_logs_each_attempt(tmp_path, caplog):
    base = tmp_path / "f.txt"
    base.write_text("x")
    with caplog.at_level(logging.INFO, logger="uniqpath"):
        unique_path(base, verbose=True)
    assert any("Trying:" in r.message for r in caplog.records)
    assert any("Found:" in r.message for r in caplog.records)


def test_quiet_by_default(tmp_path, caplog):
    base = tmp_path / "f.txt"
    base.write_text("x")
    with caplog.at_level(logging.INFO, logger="uniqpath"):
        unique_path(base)
    assert caplog.records == []


# -- accepts anything path-like --------------------------------------------


def test_accepts_a_str(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert unique_path("out.txt").name == "out.txt"


def test_accepts_an_os_pathlike(tmp_path):
    class Wrapper:
        def __fspath__(self):
            return str(tmp_path / "out.txt")

    assert unique_path(Wrapper()).name == "out.txt"
