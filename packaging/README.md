# Packaging uniqpath for other channels

PyPI is the source of truth: every other channel below repackages the sdist
published there. So the order is always **release on PyPI first**, then update
these recipes.

All of them need the SHA-256 of the sdist. Get it with:

```bash
python packaging/sha256.py 0.2.0
```

## Summary

| Channel | Command for users | Effort | Who approves |
|---|---|---|---|
| PyPI | `pip install uniqpath` | done, automated | nobody |
| pipx / uv | `pipx install uniqpath` | nothing to do | nobody |
| Homebrew tap | `brew install julienrabault/tap/uniqpath` | ~15 min once | you |
| Homebrew core | `brew install uniqpath` | needs popularity | Homebrew maintainers |
| conda-forge | `conda install -c conda-forge uniqpath` | one PR | conda-forge reviewers |
| AUR | `yay -S python-uniqpath` | ~20 min once | you |
| Debian / Fedora | `apt install python3-uniqpath` | high, slow | distro maintainers |

## pipx and uv — nothing to do

Because `uniqpath` declares a console script entry point, these already work on
any Linux, macOS or Windows machine:

```bash
pipx install uniqpath
uv tool install uniqpath
uvx uniqpath output.txt      # run without installing
```

Worth putting in the README; no packaging work involved.

## Homebrew — your own tap (recommended)

A *tap* is just a GitHub repository named `homebrew-<something>`. You own it,
nobody reviews it, and it works on macOS **and Linuxbrew**.

1. Create a public repo `JulienRabault/homebrew-tap`.
2. Copy [`homebrew/uniqpath.rb`](homebrew/uniqpath.rb) to `Formula/uniqpath.rb`
   in it, with the real `sha256`.
3. Users then run:

   ```bash
   brew tap julienrabault/tap
   brew install uniqpath
   ```

The [`bump-homebrew.yml`](../.github/workflows/bump-homebrew.yml) workflow
updates the formula automatically on every GitHub release, once you add a
`HOMEBREW_TAP_TOKEN` secret (a fine-grained PAT with **Contents: write** on the
tap repo only).

### Homebrew core — later

`brew install uniqpath` with no tap requires acceptance into homebrew-core,
which has an explicit notability bar: roughly **75+ stars, 30+ forks, 30+
watchers**, or a comparable sign the project is widely used. A tap is the right
move until then; migrating later is a single PR.

## conda-forge

Used by the scientific Python crowd — likely relevant for this library.

1. Fork [conda-forge/staged-recipes](https://github.com/conda-forge/staged-recipes).
2. Add [`conda/meta.yaml`](conda/meta.yaml) as `recipes/uniqpath/meta.yaml`,
   with the real `sha256`.
3. Open a PR. Expect a few days to a couple of weeks for review.

Once merged, conda-forge creates a `uniqpath-feedstock` repository and its bot
opens a PR on it for every new PyPI release. Subsequent updates are one click.

## AUR (Arch Linux)

1. Create an account on [aur.archlinux.org](https://aur.archlinux.org) and add
   an SSH key.
2. ```bash
   git clone ssh://aur@aur.archlinux.org/python-uniqpath.git
   cd python-uniqpath
   cp /path/to/uniqpath/packaging/aur/PKGBUILD .
   # fill in sha256sums, then:
   updpkgsums
   makepkg --printsrcinfo > .SRCINFO
   makepkg -si          # build and install locally to verify
   git add PKGBUILD .SRCINFO && git commit -m "Initial import: 0.2.0" && git push
   ```

Updating later: bump `pkgver`, rerun `updpkgsums` and `makepkg --printsrcinfo`,
push.

## Debian, Ubuntu, Fedora

These ship `python3-<name>` packages built by distro maintainers, on the
distro's own release cadence. Getting a new package in means finding a sponsor
(Debian) or becoming a package maintainer (Fedora), and the version users get
then lags by months.

For a small pure-Python library this is rarely worth it. `pipx install
uniqpath` covers the same users today. Revisit if something in those
distributions ever depends on `uniqpath`.

## Nix

Nixpkgs accepts a `python3Packages.uniqpath` derivation via PR. Low priority,
but easy if a user asks for it.

## Release checklist

1. Bump `version` in `pyproject.toml` and `__version__` in
   `src/uniqpath/__init__.py`.
2. Move the `Unreleased` section of `CHANGELOG.md` under the new version.
3. `git tag v0.2.0 && git push --tags`, then publish the GitHub release.
   `publish.yml` uploads to PyPI and `bump-homebrew.yml` updates the tap.
4. `python packaging/sha256.py 0.2.0` and update the conda and AUR recipes.
