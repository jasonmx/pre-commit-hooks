"""Refuse a commit whose files or message name a private detail.

A public repo can't hold its own blocklist, so the terms come from gitignored files in the repo's main checkout, which
also covers a linked worktree: by default `.private-terms` (one term per line) and `.private-terms.rig`; pass
`--terms-file NAME` (repeatable) to read others. A line may be `term<TAB>label`, reported by its label, so a secret is
never echoed. Lines starting with `#` are comments. Where no terms file exists (CI, a contributor's clone) the check
passes.

Usage: check-private [--terms-file NAME ...] FILE ...   (pre-commit passes staged files, or the message file at
commit-msg, and runs it from the repo root)
"""

import argparse
import subprocess
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

DEFAULT_TERMS_FILES = (".private-terms", ".private-terms.rig")


def main_checkout(repo: Path) -> Path:
    """The main checkout, which holds the gitignored terms files for every linked worktree; else `repo`."""
    try:
        common = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--path-format=absolute", "--git-common-dir"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return repo
    return Path(common).parent


def private_terms(files: Iterable[Path]) -> dict[str, str]:
    """Lowercased term -> label to report."""
    terms: dict[str, str] = {}
    for path in files:
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            term, _, label = line.partition("\t")
            if (term := term.strip()) and not term.startswith("#"):
                terms[term.lower()] = label.strip() or term
    return terms


def find(paths: Iterable[Path], terms: dict[str, str]) -> list[str]:
    hits = []
    for path in paths:
        try:
            lines = path.read_text().splitlines()
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        for number, line in enumerate(lines, 1):
            lowered = line.lower()
            hits.extend(f"{path}:{number}: {label}" for term, label in terms.items() if term in lowered)
    return hits


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refuse a commit naming a term from the gitignored terms files.")
    parser.add_argument("--terms-file", action="append", dest="terms_files", metavar="NAME")
    parser.add_argument("files", nargs="*", type=Path)
    args = parser.parse_args(argv)
    root = main_checkout(Path.cwd())
    names = args.terms_files or DEFAULT_TERMS_FILES
    try:
        terms = private_terms(root / name for name in names)
    except (OSError, UnicodeDecodeError) as err:
        print(f"Can't read the private terms, so the commit is refused: {err}")
        return 1
    if terms and (hits := find(args.files, terms)):
        print("Private details in a commit:", *hits, sep="\n  ")
        print("Remove them, or move them to a gitignored file.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
