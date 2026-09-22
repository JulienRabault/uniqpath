"""CLI: --exec, shell completions, and stdout/stderr discipline."""

import sys
from pathlib import Path

import pytest

from uniqpath._completions import SHELLS
from uniqpath.cli import main


@pytest.fixture
def cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def run(capture, *argv):
    """Invoke the CLI and return ``(exit_code, stdout, stderr)``.

    Pass ``capsys`` for uniqpath's own output, or ``capfd`` when a child
    process writes to the real file descriptors.
    """
    code = main(list(argv))
    captured = capture.readouterr()
    return code, captured.out.strip(), captured.err.strip()


# -- --exec -----------------------------------------------------------------

WRITE_MARKER = "import sys, pathlib; pathlib.Path(sys.argv[1]).write_text('done')"


def test_substitutes_the_path_into_the_command(cwd, capsys):
    code, _, _ = run(
        capsys, "out.txt", "--exec", "--", sys.executable, "-c", WRITE_MARKER, "{}"
    )
    assert code == 0
    assert (cwd / "out.txt").read_text() == "done"


def test_the_path_is_reserved_before_the_command_runs(cwd, capsys):
    """--exec implies --reserve, so the command receives a path it owns."""
    (cwd / "out.txt").write_text("existing")
    code, _, _ = run(
        capsys, "out.txt", "--exec", "--", sys.executable, "-c", WRITE_MARKER, "{}"
    )
    assert code == 0
    assert (cwd / "out.txt").read_text() == "existing"
    assert (cwd / "out_1.txt").read_text() == "done"


def test_substitutes_inside_a_longer_argument(cwd, capfd):
    script = "import sys; print(sys.argv[1])"
    code, out, _ = run(
        capfd, "run", "--dir", "--exec", "--", sys.executable, "-c", script, "--out={}"
    )
    assert code == 0
    assert out == "--out=run"


def test_substitutes_every_occurrence(cwd, capfd):
    script = "import sys; print(sys.argv[1], sys.argv[2])"
    code, out, _ = run(
        capfd, "run", "--dir", "--exec", "--", sys.executable, "-c", script, "{}", "{}"
    )
    assert code == 0
    assert out == "run run"


def test_exit_code_comes_from_the_command(cwd, capsys):
    code, _, _ = run(
        capsys,
        "out.txt",
        "--exec",
        "--",
        sys.executable,
        "-c",
        "import sys; sys.exit(3); {}",
    )
    assert code == 3


def test_path_is_not_printed_on_stdout(cwd, capsys):
    """stdout belongs to the command; uniqpath must not pollute it."""
    code, out, _ = run(
        capsys, "out.txt", "--exec", "--", sys.executable, "-c", "pass  # {}"
    )
    assert code == 0
    assert out == ""


def test_command_without_placeholder_is_refused(cwd, capsys):
    code, _, err = run(capsys, "out.txt", "--exec", "--", sys.executable, "-c", "pass")
    assert code == 2
    assert "contains no {}" in err


def test_missing_command_is_refused(cwd):
    with pytest.raises(SystemExit):
        main(["out.txt", "--exec"])


def test_command_without_exec_flag_is_refused(cwd):
    with pytest.raises(SystemExit):
        main(["out.txt", "--", "echo", "{}"])


def test_unknown_command_reports_127(cwd, capsys):
    code, _, err = run(
        capsys, "out.txt", "--exec", "--", "definitely-not-a-real-binary-xyz", "{}"
    )
    assert code == 127
    assert "command not found" in err


def test_exec_reserves_a_directory(cwd, capfd):
    script = "import sys, pathlib; print(pathlib.Path(sys.argv[1]).is_dir())"
    code, out, _ = run(
        capfd, "run", "--dir", "--exec", "--", sys.executable, "-c", script, "{}"
    )
    assert code == 0
    assert out == "True"


# -- completions ------------------------------------------------------------


@pytest.mark.parametrize("shell", SHELLS)
def test_completion_prints_a_script(capsys, shell):
    code, out, _ = run(capsys, "--completion", shell)
    assert code == 0
    assert "uniqpath" in out
    assert len(out.splitlines()) > 5


def test_bash_completion_registers_the_command(capsys):
    _, out, _ = run(capsys, "--completion", "bash")
    assert "complete -o filenames -F _uniqpath_completion uniqpath" in out


def test_zsh_completion_declares_compdef(capsys):
    _, out, _ = run(capsys, "--completion", "zsh")
    assert out.startswith("#compdef uniqpath")


def test_fish_completion_uses_complete_c(capsys):
    _, out, _ = run(capsys, "--completion", "fish")
    assert "complete -c uniqpath" in out


def test_completion_needs_no_path(capsys):
    code, _, _ = run(capsys, "--completion", "bash")
    assert code == 0


def test_unknown_shell_is_refused():
    with pytest.raises(SystemExit):
        main(["--completion", "powershell"])


def test_completion_script_rejects_unknown_shell_programmatically():
    from uniqpath._completions import completion_script

    with pytest.raises(ValueError, match="unsupported shell"):
        completion_script("powershell")


# -- argument handling ------------------------------------------------------


def test_path_is_still_required(cwd):
    with pytest.raises(SystemExit):
        main([])


def test_verbose_logs_to_stderr_not_stdout(cwd, capsys):
    (cwd / "out.txt").write_text("x")
    code, out, err = run(capsys, "out.txt", "--verbose")
    assert code == 0
    assert out == "out_1.txt"
    assert "Trying:" in err


def test_verbose_leaves_the_root_logger_alone(cwd, capsys):
    """A library must not install handlers on the root logger."""
    import logging

    before = list(logging.getLogger().handlers)
    run(capsys, "out.txt", "--verbose")
    assert logging.getLogger().handlers == before


def test_path_named_run_is_not_a_subcommand(cwd, capsys):
    """'run' must stay usable as a path; --exec is a flag, not a subcommand."""
    code, out, _ = run(capsys, "run", "--dir", "--reserve")
    assert code == 0
    assert out == "run"
    assert Path(cwd / "run").is_dir()
