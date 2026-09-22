# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] — 2026-09-22

The public API of `unique_path()` is unchanged: same parameters, same defaults,
same return values. Existing code keeps working after upgrading.

### Fixed

- **The published wheel was broken.** `uniqpath` 0.1.3 installed `__init__.py`
  and `uniqpath.py` at the *root of `site-packages`*, because `pyproject.toml`
  declared no build backend and no package discovery. The stray top-level
  `__init__.py` could shadow or break unrelated imports in the same
  environment. The package now ships as a proper `uniqpath/` package built with
  Hatchling. **Anyone on 0.1.3 should upgrade.**
- **`pytest` was a runtime dependency**, pinned to `8.3.5`. Every user of the
  library installed pytest, and that exact version. `uniqpath` now has **zero**
  runtime dependencies; pytest moved to the `dev` extra.
- The test suite did not run at all (`ModuleNotFoundError: No module named
  'uniqpath'`), since the importable package was named `src`.
- A constant `suffix_format` such as `"_backup"` used to retry the same
  candidate up to `max_num` times before failing. It now fails immediately,
  with a message explaining why.
- Escaped placeholders `{{rand}}` and `{{uuid}}` were expanded instead of being
  left as literal text, and then raised a spurious `InvalidFormatError`. Only
  `{{num}}` escaped correctly, because it went through `str.format` rather than
  uniqpath's own pre-substitution.
- `.pyc` files were tracked in git.

### Added

- **`reserve_path()`** — same suffix logic as `unique_path()`, but it *creates*
  the winning candidate in the same operation that tests it (`O_CREAT | O_EXCL`
  for files, `mkdir` for directories). Concurrent callers can never be handed
  the same path. Covered by thread- and process-level concurrency tests.
- **`uniq_open()`** — a context manager that reserves a free path and opens
  it in one step: `with uniq_open("results.csv") as f: ...`. `f.name` holds the
  path that was used. Same concurrency guarantee as `reserve_path()`, which is
  what `open(unique_path(...), "w")` cannot give you.
- **`uniqpath` command line interface**, for shell and job scripts:
  `uniqpath results --dir --reserve`.
- **`uniqpath --exec`** runs a command with the reserved path substituted for
  every `{}` argument, and exits with that command's status:
  `uniqpath results/run --dir --exec -- python train.py --out {}`. stdout is
  left to the command, so pipes keep working.
- **Shell completion** for bash, zsh and fish via `uniqpath --completion SHELL`
  — completes paths, options and the suffix formats. Hand-written, so the
  package still has no runtime dependencies.
- **`{date}` placeholder** with full strftime support:
  `"_{date:%Y-%m-%d_%H%M%S}"`.
- **`{pid}` placeholder**, useful to disambiguate parallel workers.
- **Format specs on `{num}`**: `"_{num:03d}"` → `_007`.
- **`is_dir` parameter** on both functions, to override the file/directory
  guess. Fixes names such as `release.v1.0`, which the heuristic would
  otherwise split into stem `release.v1` and extension `.0`.
- **`parents` parameter** on `reserve_path()` (default `True`): create missing
  parent directories.
- **Typed exception hierarchy**: `UniqPathError`, `MaxAttemptsError`,
  `InvalidFormatError`. Each also derives from the builtin the pre-0.2 API
  raised (`RuntimeError` and `KeyError` respectively), so existing `except`
  clauses keep working.
- **Unknown placeholders are rejected up front**, with a message listing the
  supported ones, instead of failing mid-loop.
- `py.typed` marker: type hints are now visible to type checkers downstream.
- `__version__` exported from the package.
- CI on GitHub Actions: Linux, macOS and Windows × Python 3.9 → 3.13, plus
  ruff, `mypy --strict`, a coverage floor, and a check that the built wheel
  contains nothing but the `uniqpath` package.
- Automated PyPI publishing on release via Trusted Publishing (no stored token).
- Installation recipes for Homebrew, conda-forge and the AUR under
  [`packaging/`](packaging/).

### Changed

- Minimum Python is now **3.9** (3.8 reached end of life in October 2024).
- Random suffixes use `random.SystemRandom`, so two processes seeded at the
  same instant no longer draw the same `{rand}` value.
- Logging goes to the `uniqpath` logger rather than a module-path logger, and
  nothing is logged unless `verbose=True`.
- Error messages name the offending format string and suggest a fix.
- `suffix_format` is now validated on every call, including when the base path
  turns out to be free. Previously a typo like `"_{nope}"` stayed silent until
  the first collision, which could be much later. This is the one intentional
  behaviour change: a call that was always going to fail now fails right away.
- The library no longer calls `logging.basicConfig()`. That installed a handler
  on the *root* logger of the importing application — a well-known
  anti-pattern. A `NullHandler` is attached to the `uniqpath` logger instead,
  `verbose=True` only raises that logger's level, and the CLI installs its own
  stderr handler.
- The code is split into `_core`, `_format`, `_errors` and `cli` modules;
  everything public is re-exported from `uniqpath`.

### Notes

- `unique_path()` still performs one `stat` per attempt and offers no
  concurrency guarantee — that is what `reserve_path()` is for. The docstring
  and README now say so explicitly.

## [0.1.3] — 2025-05-15

### Added

- `max_num` parameter, capping the number of attempts.
- Tests for special characters and dots in names.

## [0.1.2] — 2025-05-15

### Changed

- Packaging metadata.

## [0.1.1] — 2025-05-15

### Changed

- Author metadata in `pyproject.toml`.

## [0.1.0] — 2025-05-15

### Added

- Initial release: `unique_path()` with `{num}`, `{timestamp}`, `{rand}` and
  `{uuid}` placeholders.

[Unreleased]: https://github.com/JulienRabault/uniqpath/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/JulienRabault/uniqpath/compare/v0.1.3...v0.2.0
[0.1.3]: https://github.com/JulienRabault/uniqpath/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/JulienRabault/uniqpath/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/JulienRabault/uniqpath/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/JulienRabault/uniqpath/releases/tag/v0.1.0
