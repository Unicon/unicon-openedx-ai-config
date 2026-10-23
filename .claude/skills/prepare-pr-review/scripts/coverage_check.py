#!/usr/bin/env python3
"""List the PR's changed files that the reviewer has not marked as viewed in Plannotator.

Plannotator keeps one review-progress record per file at
``<data-dir>/review-progress/<key>/<sha256-hex(path)>.json``, where ``key`` is the SHA-256 of
the JSON array ``["pr", <PR URL>, "layer"]``. This script reads those records for the PR in
``pr.json`` and never writes to the data directory. Standard library only.

Usage: ``python3 coverage_check.py --artifacts DIR [--data-dir DIR]``
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

from compose_guide import canonical_pr_url, data_dir
from guide_inputs import changed_files, load_pr


def progress_key(pr_url: str, scope: str = "layer") -> str:
    """Return the directory name Plannotator uses for a PR's review progress: SHA-256 hex of ``["pr", pr_url, scope]``.

    The array is serialized the way JavaScript's ``JSON.stringify`` does: no spaces and no
    escaping of non-ASCII characters.
    """
    payload = json.dumps(["pr", pr_url, scope], separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def record_name(path: str) -> str:
    """Return the file name of the review-progress record for a changed file's path."""
    return hashlib.sha256(path.encode("utf-8")).hexdigest() + ".json"


def _is_viewed(progress_dir: Path, path: str) -> bool:
    try:
        record = json.loads((progress_dir / record_name(path)).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return (
        isinstance(record, dict)
        and record.get("v") == 1
        and record.get("path") == path
        and record.get("viewed") is True
    )


def unviewed_files(changed: list[str], progress_dir: Path) -> list[str]:
    """Return the changed files, in the given order, that have no valid viewed record in ``progress_dir``.

    A file counts as viewed when its record exists, parses as JSON, has ``v == 1``, stores the
    same ``path``, and has ``viewed`` set to true. The record's fingerprint is not compared, so a
    file that changed after it was marked still counts as viewed.
    """
    return [path for path in changed if not _is_viewed(progress_dir, path)]


def main(argv: list[str] | None = None) -> int:
    """Run the CLI; return 0 after reporting coverage, 2 when no progress exists, and 1 for invalid or missing inputs."""
    parser = argparse.ArgumentParser(description="List changed files not yet marked viewed in Plannotator.")
    parser.add_argument("--artifacts", required=True, type=Path, help="folder with pr.json")
    parser.add_argument("--data-dir", type=Path, default=None, help="Plannotator data directory (default: $PLANNOTATOR_DATA_DIR or ~/.plannotator)")
    args = parser.parse_args(argv)
    try:
        pr = load_pr(args.artifacts / "pr.json")
        pr_url = canonical_pr_url(pr["url"])
        changed = changed_files(pr)
    except (ValueError, FileNotFoundError) as error:
        print(error, file=sys.stderr)
        return 1
    progress_dir = (args.data_dir or data_dir()) / "review-progress" / progress_key(pr_url)
    if not progress_dir.is_dir():
        print(f"No review progress found for {pr_url} (looked in {progress_dir}).", file=sys.stderr)
        return 2
    missing = unviewed_files(changed, progress_dir)
    if missing:
        print(f"Not marked viewed ({len(missing)} of {len(changed)}):")
        for path in missing:
            print(f"- {path}")
    else:
        print(f"All {len(changed)} changed files are marked viewed.")
    print("A file changed after you marked it still counts as viewed here.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
