"""Placeholder expansion and suffix_format validation."""

import os
import re
from datetime import datetime

import pytest

from uniqpath import InvalidFormatError, unique_path
from uniqpath._format import PlaceholderFormatter, is_constant, validate_format


@pytest.fixture
def tmp_file(tmp_path):
    file = tmp_path / "example.txt"
    file.write_text("dummy")
    return file


@pytest.fixture
def formatter():
    return PlaceholderFormatter(datetime(2026, 9, 22, 14, 30, 5), {"num": 3})


# -- placeholders ----------------------------------------------------------


def test_num_is_expanded(formatter):
    assert formatter.apply("_{num}") == "_3"


def test_num_accepts_a_format_spec(formatter):
    assert formatter.apply("_{num:03d}") == "_003"


def test_timestamp_is_an_integer(formatter):
    assert formatter.apply("{timestamp}").isdigit()


def test_date_accepts_strftime_specs(formatter):
    assert formatter.apply("{date:%Y-%m-%d}") == "2026-09-22"
    assert formatter.apply("{date:%Y%m%d_%H%M%S}") == "20260922_143005"


def test_pid_is_the_current_process(formatter):
    assert formatter.apply("{pid}") == str(os.getpid())


@pytest.mark.parametrize("length", [1, 6, 16])
def test_rand_honours_its_length(formatter, length):
    out = formatter.apply(f"{{rand:{length}}}")
    assert re.fullmatch(r"[a-zA-Z0-9]+", out)
    assert len(out) == length


def test_rand_defaults_to_six_chars(formatter):
    assert len(formatter.apply("{rand}")) == 6


def test_uuid_defaults_to_full_hex(formatter):
    assert re.fullmatch(r"[0-9a-f]{32}", formatter.apply("{uuid}"))


def test_uuid_can_be_truncated(formatter):
    assert re.fullmatch(r"[0-9a-f]{8}", formatter.apply("{uuid:8}"))


def test_rand_varies_between_calls(formatter):
    values = {formatter.apply("{rand:12}") for _ in range(20)}
    assert len(values) == 20


def test_now_is_frozen_for_the_whole_call(formatter):
    assert formatter.apply("{timestamp}") == formatter.apply("{timestamp}")


# -- validation ------------------------------------------------------------


def test_unknown_placeholder_is_rejected():
    with pytest.raises(InvalidFormatError, match="Unknown placeholder"):
        validate_format("_{nope}")


def test_unknown_placeholder_still_raises_keyerror():
    """Pre-0.2 code caught KeyError; that must keep working."""
    with pytest.raises(KeyError):
        validate_format("_{nope}")


def test_error_message_lists_supported_placeholders():
    with pytest.raises(InvalidFormatError) as excinfo:
        validate_format("_{nope}")
    assert "{num}" in str(excinfo.value)


@pytest.mark.parametrize(
    "fmt", ["_{num}", "_{rand}", "_{uuid:6}", "_{date:%Y}_{num}", "{{literal}}_{num}"]
)
def test_valid_formats_are_accepted(fmt):
    validate_format(fmt)


@pytest.mark.parametrize("fmt", ["_backup", "_{timestamp}", "_{date:%Y-%m-%d}", "_v2"])
def test_constant_formats_are_detected(fmt):
    assert is_constant(fmt)


@pytest.mark.parametrize(
    "fmt", ["_{num}", "_{rand:4}", "_{uuid}", "_{timestamp}_{num}"]
)
def test_varying_formats_are_detected(fmt):
    assert not is_constant(fmt)


def test_escaped_braces_are_not_placeholders():
    validate_format("{{num}}_{num}")
    assert is_constant("{{num}}") is True


# -- integration with unique_path ------------------------------------------


def test_unique_path_rejects_unknown_placeholder(tmp_file):
    with pytest.raises(InvalidFormatError):
        unique_path(tmp_file, suffix_format="_{nope}")


def test_unique_path_supports_padded_num(tmp_file):
    assert unique_path(tmp_file, suffix_format="_{num:04d}").name == "example_0001.txt"


def test_unique_path_supports_date_spec(tmp_file):
    today = datetime.now().strftime("%Y-%m-%d")
    p = unique_path(tmp_file, suffix_format="_{date:%Y-%m-%d}_{num}")
    assert p.name == f"example_{today}_1.txt"


def test_constant_format_fails_fast_when_taken(tmp_path):
    """A constant suffix has a single candidate: fail loudly, do not spin."""
    base = tmp_path / "data.txt"
    base.write_text("x")
    (tmp_path / "data_backup.txt").write_text("x")
    with pytest.raises(RuntimeError, match="constant"):
        unique_path(base, suffix_format="_backup", max_num=50_000)


def test_constant_format_is_fine_when_free(tmp_path):
    base = tmp_path / "data.txt"
    base.write_text("x")
    assert unique_path(base, suffix_format="_backup").name == "data_backup.txt"


def test_malformed_format_is_reported(tmp_file):
    with pytest.raises(InvalidFormatError, match="Malformed"):
        unique_path(tmp_file, suffix_format="_{num:!!!}")


def test_unbalanced_brace_is_reported(tmp_file):
    with pytest.raises(InvalidFormatError, match="Malformed"):
        unique_path(tmp_file, suffix_format="_{num}}")


# -- brace escaping (regression: {{rand}} / {{uuid}} used to be expanded) ----


@pytest.mark.parametrize("name", ["num", "rand", "uuid", "timestamp", "date", "pid"])
def test_doubled_braces_stay_literal(formatter, name):
    """'{{x}}' is an escaped literal for str.format; every placeholder agrees."""
    assert formatter.apply(f"_{{{{{name}}}}}_{{num}}") == f"_{{{name}}}_3"


def test_escaped_rand_is_not_expanded(formatter):
    assert formatter.apply("_{{rand}}_{num}") == "_{rand}_3"


def test_escaped_uuid_is_not_expanded(formatter):
    assert formatter.apply("_{{uuid:8}}_{num}") == "_{uuid:8}_3"


def test_escaped_and_real_placeholder_side_by_side(formatter):
    out = formatter.apply("_{{rand}}_{rand:4}")
    assert out.startswith("_{rand}_")
    assert re.fullmatch(r"_\{rand\}_[a-zA-Z0-9]{4}", out)


def test_unique_path_with_escaped_placeholder(tmp_file):
    p = unique_path(tmp_file, suffix_format="_{{rand}}_{num}")
    assert p.name == "example_{rand}_1.txt"


# -- validation happens even when the base path is free ---------------------


def test_bad_format_is_caught_even_when_the_path_is_free(tmp_path):
    """A typo must not lie dormant until the first collision."""
    with pytest.raises(InvalidFormatError):
        unique_path(tmp_path / "does_not_exist_yet.txt", suffix_format="_{nope}")
