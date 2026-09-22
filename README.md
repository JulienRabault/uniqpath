<h1 align="center">uniqpath</h1>

<p align="center">
  <em>Stop overwriting your files.</em><br>
  Three functions. Zero dependencies. Race-free when you need it.
</p>

<p align="center">
  <a href="https://github.com/JulienRabault/uniqpath/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/JulienRabault/uniqpath/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://pypi.org/project/uniqpath/"><img alt="PyPI" src="https://img.shields.io/pypi/v/uniqpath.svg"></a>
  <a href="https://pypi.org/project/uniqpath/"><img alt="Python versions" src="https://img.shields.io/pypi/pyversions/uniqpath.svg"></a>
  <a href="https://pypi.org/project/uniqpath/"><img alt="Downloads" src="https://img.shields.io/pypi/dm/uniqpath.svg"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
  <img alt="Dependencies" src="https://img.shields.io/badge/dependencies-0-brightgreen.svg">
</p>

---

We have all shipped this function:

```python
# every codebase, somewhere
i = 1
while os.path.exists(f"{name}_{i}.txt"):
    i += 1
```

And we have all watched a parallel job quietly overwrite three hours of
results, because two workers ran that loop at the same time.

```bash
pip install uniqpath
```

```python
from uniqpath import unique_path

unique_path("output.txt")   # → output.txt      nothing there yet
unique_path("output.txt")   # → output_1.txt    now there is
unique_path("output.txt")   # → output_2.txt    you get the idea
```

That is the whole library. Then there is the part that actually matters.

## The race nobody thinks about

`unique_path()` tells you a name that is free **right now**. Between that
answer and your `open()`, another process can grab it. In a single script,
who cares. In 16 parallel workers, that is your evening.

`reserve_path()` closes the gap: it **creates** the path in the same syscall
that tests it — `O_CREAT | O_EXCL` for a file, `mkdir` for a directory. The
loser of a race gets `FileExistsError` and quietly moves to the next candidate.

```python
from uniqpath import reserve_path

run_dir = reserve_path("experiments/run", is_dir=True)   # yours, guaranteed
```

```python
# 16 workers, 16 distinct directories, zero coordination
with ThreadPoolExecutor(max_workers=16) as pool:
    dirs = pool.map(lambda _: reserve_path("out/run", is_dir=True), range(16))

assert len({str(d) for d in dirs}) == 16   # run, run_1, run_2, ... run_15
```

And when you were going to write to the file anyway, skip the middleman:

```python
from uniqpath import uniq_open

with uniq_open("results.csv") as f:
    f.write("...")
    print("wrote", f.name)      # results_3.csv
```

`uniq_open()` reserves the path, opens it, and closes it on the way out.
`f.name` is the path it actually used.

|  | tells you a free name | creates it | opens it | safe under concurrency |
|---|:---:|:---:|:---:|:---:|
| `unique_path()` | ✅ | ❌ | ❌ | ❌ |
| `reserve_path()` | ✅ | ✅ | ❌ | ✅ |
| `uniq_open()` | ✅ | ✅ | ✅ | ✅ |

## Install

```bash
pip install uniqpath          # library + CLI
pipx install uniqpath         # just the CLI, isolated
uv tool install uniqpath      # same, with uv
uvx uniqpath output.txt       # no install at all
```

<details>
<summary>Homebrew, conda, Arch</summary>

```bash
brew install julienrabault/tap/uniqpath
conda install -c conda-forge uniqpath
yay -S python-uniqpath
```

Recipes and their status live in [`packaging/`](packaging/).

</details>

Python 3.9+. Linux, macOS, Windows. No runtime dependencies, ever.

## Name your files however you like

The suffix is a format string. Mix and match:

```python
unique_path("run.log",   suffix_format="_{date:%Y-%m-%d}_{num:03d}")
# → run_2026-09-22_001.log

unique_path("shard.parquet", suffix_format="_{pid}_{uuid:8}")
# → shard_48213_5ba950c1.parquet

unique_path("backup.tar.gz", suffix_format=".{timestamp}")
# → backup.tar.1790080200.gz
```

| Placeholder | What you get | Example |
|---|---|---|
| `{num}` | attempt counter, from 1 | `_7` |
| `{num:03d}` | …zero-padded, any format spec | `_007` |
| `{date}` | current datetime, **full strftime** | `{date:%Y-%m-%d}` → `_2026-09-22` |
| `{timestamp}` | UNIX seconds | `_1790080200` |
| `{rand}` | random alphanumerics, 6 by default | `{rand:4}` → `_a7Zq` |
| `{uuid}` | UUID4 hex, 32 by default | `{uuid:8}` → `_5ba950c1` |
| `{pid}` | current process id | `_48213` |

Typo a placeholder and you get told immediately, with the list of valid ones —
not a `KeyError` five minutes into a job.

## From the shell

```bash
$ uniqpath output.txt
output.txt

$ touch output.txt && uniqpath output.txt
output_1.txt

$ uniqpath results --dir --reserve     # creates it, then prints it
results_1
```

Or skip the variable entirely — `--exec` reserves the path and drops it into
your command wherever you put `{}`:

```bash
uniqpath results/run --dir --exec -- python train.py --out {}
```

uniqpath exits with your command's exit code, and leaves stdout alone so pipes
keep working.

Which makes job scripts boring, in the good way:

```bash
#!/bin/bash
#SBATCH --array=0-63

uniqpath "results/$SLURM_JOB_NAME" --dir --exec -- python train.py --out {}
```

64 array tasks, 64 directories, no `$SLURM_ARRAY_TASK_ID` arithmetic, no
collisions.

### Completion

```bash
eval "$(uniqpath --completion bash)"                               # bash
uniqpath --completion zsh  > "${fpath[1]}/_uniqpath"               # zsh
uniqpath --completion fish > ~/.config/fish/completions/uniqpath.fish
```

It completes paths, options, and the suffix formats above — so you stop
looking them up.

## Files vs directories

By default the kind is guessed: a path with an extension that is not already a
directory is a file, and the suffix goes before the extension.

```python
unique_path("archive.tar.gz")   # → archive.tar_1.gz
unique_path("results")          # → results_1
```

Guessing has limits. Say so explicitly when it matters:

```python
unique_path("release.v1.0", is_dir=True)    # → release.v1.0_1
unique_path("release.v1.0", is_dir=False)   # → release.v1_1.0
```

<details>
<summary><b>Full API</b></summary>

```python
unique_path(
    path,                        # str | os.PathLike
    suffix_format="_{num}",
    if_exists_only=True,         # return path untouched when it is already free
    return_str=False,            # return str instead of Path
    max_num=50_000,              # attempts before giving up
    verbose=False,               # log each attempt on the "uniqpath" logger
    is_dir=None,                 # None = guess, True = directory, False = file
) -> Path | str

reserve_path(
    ...,                         # everything above, plus:
    parents=True,                # create missing parent directories
) -> Path | str

uniq_open(                       # context manager
    path,
    mode="w",                    # any writing mode: w, a, x, +b variants
    *,                           # plus suffix_format, if_exists_only, max_num,
    ...,                         # parents, buffering, encoding, errors, newline
) -> IO                          # f.name is the path that was used
```

### Errors

```python
from uniqpath import UniqPathError, MaxAttemptsError, InvalidFormatError
```

- `MaxAttemptsError` — no free path within `max_num` attempts.
  Also a `RuntimeError`, so pre-0.2 handlers keep working.
- `InvalidFormatError` — unknown or malformed placeholder.
  Also a `KeyError`, for the same reason.

A suffix with no varying part (`"_backup"`, `"_{timestamp}"`) has exactly one
possible candidate. If it is taken, you get `MaxAttemptsError` straight away
instead of 50 000 pointless `stat` calls.

</details>

<details>
<summary><b>Gotchas worth knowing</b></summary>

- `unique_path()` does one `stat` per attempt. A directory holding thousands of
  `name_N` siblings costs thousands of syscalls — use `{rand}` or `{uuid}`
  there, they land on the first try.
- `reserve_path()` creates an **empty** file. Opening it afterwards in `"w"` is
  the normal flow, and it never truncates something that already existed.
- Reservations are not garbage-collected. A path you reserve and never use
  stays on disk.
- Atomicity rests on `O_EXCL` and `mkdir`. On NFS without working locking,
  `O_EXCL` guarantees are weaker — a filesystem limitation, not a uniqpath one.

</details>

## Contributing

Issues and PRs welcome.

```bash
git clone https://github.com/JulienRabault/uniqpath
cd uniqpath
pip install -e ".[dev]"

pytest -q --cov=uniqpath              # 190 tests
ruff check . && ruff format --check .
mypy                                  # strict
```

CI runs the suite on Linux, macOS and Windows across Python 3.9 → 3.13.

## License

MIT — [Julien Rabault](https://github.com/JulienRabault).

<p align="center">
  <sub>If this saved you a results directory, a ⭐ is appreciated.</sub>
</p>
