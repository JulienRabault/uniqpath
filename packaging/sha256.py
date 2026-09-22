#!/usr/bin/env python3
"""Print the SHA-256 of a uniqpath sdist published on PyPI.

Every downstream recipe (Homebrew, conda-forge, AUR) needs this checksum.

    python packaging/sha256.py 0.2.0
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

API = "https://pypi.org/pypi/{package}/{version}/json"


def sdist_sha256(package: str, version: str) -> tuple[str, str]:
    """Return the ``(filename, sha256)`` of the sdist for that release."""
    url = API.format(package=package, version=version)
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise SystemExit(f"{package} {version} is not on PyPI yet") from exc
        raise

    for entry in payload["urls"]:
        if entry["packagetype"] == "sdist":
            return entry["filename"], entry["digests"]["sha256"]
    raise SystemExit(
        f"{package} {version} has no sdist; build one with `python -m build`"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("version", help="release to look up, e.g. 0.2.0")
    parser.add_argument("--package", default="uniqpath")
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="print only the checksum, for piping into a recipe",
    )
    args = parser.parse_args(argv)

    filename, digest = sdist_sha256(args.package, args.version)
    if args.quiet:
        print(digest)
    else:
        print(f"file   : {filename}")
        print(f"sha256 : {digest}")
        print()
        print("Paste it into:")
        print('  packaging/homebrew/uniqpath.rb   -> sha256 "..."')
        print("  packaging/conda/meta.yaml        -> sha256: ...")
        print("  packaging/aur/PKGBUILD           -> sha256sums=('...')")
    return 0


if __name__ == "__main__":
    sys.exit(main())
