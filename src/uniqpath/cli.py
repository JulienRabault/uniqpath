"""Command line interface: ``uniqpath PATH [options] [-- command...]``.

Prints one path on stdout, so it composes with shell scripts::

    OUT=$(uniqpath results/run --dir --reserve)

or runs a command with the reserved path substituted for ``{}``::

    uniqpath results/run --dir --exec -- python train.py --out {}
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys

from ._completions import SHELLS, completion_script
from ._core import DEFAULT_MAX_NUM, DEFAULT_SUFFIX_FORMAT, reserve_path, unique_path
from ._errors import UniqPathError
from ._format import supported_placeholders

__all__ = ["build_parser", "main"]

#: Replaced by the chosen path in every argument of an ``--exec`` command.
PLACEHOLDER = "{}"

_EPILOG = """\
placeholders:
  {num}        attempt counter starting at 1; {num:03d} pads it
  {timestamp}  UNIX timestamp in seconds
  {date}       current datetime, e.g. {date:%Y-%m-%d}
  {uuid}       UUID4 hex, {uuid:8} truncates it
  {rand}       random alphanumerics, {rand:4} sets the length
  {pid}        current process id

examples:
  uniqpath output.txt
  uniqpath run.log --format '_{date:%Y-%m-%d}_{num:03d}'
  uniqpath results --dir --reserve
  uniqpath results --dir --exec -- python train.py --out {}

shell completion:
  eval "$(uniqpath --completion bash)"        # or zsh, fish
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="uniqpath",
        description="Print a file or directory path that is not taken yet.",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", nargs="?", help="base file or directory path")
    parser.add_argument(
        "-f",
        "--format",
        dest="suffix_format",
        default=DEFAULT_SUFFIX_FORMAT,
        metavar="FMT",
        help=(
            "suffix pattern (default: %(default)s); placeholders: "
            + supported_placeholders()
        ),
    )
    parser.add_argument(
        "-r",
        "--reserve",
        action="store_true",
        help="atomically create the path, making the result race-free",
    )
    parser.add_argument(
        "-x",
        "--exec",
        dest="exec_",
        action="store_true",
        help=(
            "run the command after -- with every {} replaced by the path; "
            "implies --reserve, and exits with the command's status"
        ),
    )
    parser.add_argument(
        "--always-suffix",
        action="store_true",
        help="add a suffix even when the base path is free",
    )
    parser.add_argument(
        "--max-num",
        type=int,
        default=DEFAULT_MAX_NUM,
        metavar="N",
        help="give up after N attempts (default: %(default)s)",
    )
    kind = parser.add_mutually_exclusive_group()
    kind.add_argument(
        "--dir",
        dest="is_dir",
        action="store_true",
        default=None,
        help="treat the target as a directory",
    )
    kind.add_argument(
        "--file",
        dest="is_dir",
        action="store_false",
        help="treat the target as a file",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="log each attempt on stderr"
    )
    parser.add_argument(
        "--completion",
        choices=SHELLS,
        metavar="SHELL",
        help=f"print a shell completion script ({', '.join(SHELLS)}) and exit",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {_version()}")
    return parser


def _version() -> str:
    from . import __version__

    return __version__


def _split_command(argv: list[str]) -> tuple[list[str], list[str] | None]:
    """Split ``argv`` at the first ``--`` into uniqpath args and a command."""
    if "--" not in argv:
        return argv, None
    index = argv.index("--")
    return argv[:index], argv[index + 1 :]


def _enable_logging() -> None:
    """Send the library's INFO records to stderr, leaving stdout for the path.

    Idempotent: calling ``main()`` more than once in a single process, as the
    tests do, must not stack up handlers and duplicate every line.
    """
    logger = logging.getLogger("uniqpath")
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("uniqpath: %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    own_args, command = _split_command(raw)

    parser = build_parser()
    args = parser.parse_args(own_args)

    if args.completion:
        print(completion_script(args.completion), end="")
        return 0

    if args.path is None:
        parser.error("the following arguments are required: path")
    if args.exec_ and not command:
        parser.error(
            "--exec needs a command after --, e.g. -- python train.py --out {}"
        )
    if command and not args.exec_:
        parser.error("a command was given after -- but --exec was not passed")

    if args.verbose:
        _enable_logging()

    run = reserve_path if (args.reserve or args.exec_) else unique_path
    try:
        result = run(
            args.path,
            suffix_format=args.suffix_format,
            if_exists_only=not args.always_suffix,
            return_str=True,
            max_num=args.max_num,
            verbose=args.verbose,
            is_dir=args.is_dir,
        )
    except UniqPathError as exc:
        print(f"uniqpath: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"uniqpath: {exc}", file=sys.stderr)
        return 1

    if command:
        return _run_command(command, str(result))

    print(result)
    return 0


def _run_command(command: list[str], path: str) -> int:
    """Run ``command`` with every ``{}`` argument replaced by ``path``."""
    if not any(PLACEHOLDER in part for part in command):
        print(
            f"uniqpath: the command contains no {PLACEHOLDER}, so the reserved path "
            f"{path} would be ignored. Add {PLACEHOLDER} where the path belongs.",
            file=sys.stderr,
        )
        return 2

    filled = [part.replace(PLACEHOLDER, path) for part in command]
    try:
        return subprocess.call(filled)
    except FileNotFoundError:
        print(f"uniqpath: command not found: {filled[0]}", file=sys.stderr)
        return 127
    except PermissionError as exc:
        print(f"uniqpath: {filled[0]}: {exc.strerror}", file=sys.stderr)
        return 126


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
