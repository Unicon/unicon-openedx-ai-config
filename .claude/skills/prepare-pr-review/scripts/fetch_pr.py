#!/usr/bin/env python3
"""Fetch the PR metadata the other prepare-pr-review scripts read, and write it as ``pr.json``.

``gh pr view --json files`` returns at most 100 files, so a larger PR would silently lose
files from the guide. This script compares the returned list with ``changedFiles`` and, when
the list is short, replaces it with every page of the REST ``pulls/<n>/files`` endpoint.
Standard library only.

Usage: ``python3 fetch_pr.py PR_URL --out FILE``
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from compose_guide import canonical_pr_url

VIEW_FIELDS = (
    "url,number,title,body,headRefOid,baseRefOid,headRepository,files,changedFiles,closingIssuesReferences"
)
# gh concatenates one JSON array per page under --paginate; --jq flattens that to one object per line.
FILES_JQ = ".[] | {path: .filename, additions, deletions}"


def _gh(run, command: list[str]) -> str:
    """Run a ``gh`` command through ``run`` and return its stdout; raise ``RuntimeError`` with stderr on failure."""
    result = run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(command[:3])} failed: {result.stderr.strip()}")
    return result.stdout


def fetch_pr(pr_url: str, run=subprocess.run) -> dict:
    """Return the PR's metadata with its complete file list.

    ``run`` has the signature of ``subprocess.run`` and is injectable for tests. The result is
    the ``gh pr view`` JSON, except that ``files`` holds every changed file when the PR has more
    than 100. Raises ``ValueError`` for a URL that is not a GitHub pull request or when the
    complete list still differs from ``changedFiles`` (GitHub lists at most 3000 files), and
    ``RuntimeError`` when ``gh`` fails.
    """
    url = canonical_pr_url(pr_url)
    pr = json.loads(_gh(run, ["gh", "pr", "view", url, "--json", VIEW_FIELDS]))
    if len(pr["files"]) < pr["changedFiles"]:
        owner, repo, _, number = url.split("/")[3:]
        output = _gh(run, ["gh", "api", "--paginate", f"repos/{owner}/{repo}/pulls/{number}/files", "--jq", FILES_JQ])
        pr["files"] = [json.loads(line) for line in output.splitlines() if line.strip()]
    if len(pr["files"]) != pr["changedFiles"]:
        raise ValueError(f"gh returned {len(pr['files'])} files but the PR has {pr['changedFiles']} changed files")
    return pr


def main(argv: list[str] | None = None) -> int:
    """Run the CLI; write the PR JSON to ``--out`` and print its path.

    Returns 0 on success and 1, with the message on stderr, for a bad URL, a failed ``gh`` call,
    or an incomplete file list.
    """
    parser = argparse.ArgumentParser(description="Write pr.json with the PR's complete changed-file list.")
    parser.add_argument("pr_url", help="GitHub pull request URL")
    parser.add_argument("--out", required=True, type=Path, help="file to write, usually <artifacts>/pr.json")
    args = parser.parse_args(argv)
    try:
        pr = fetch_pr(args.pr_url, run=subprocess.run)
    except (ValueError, RuntimeError, FileNotFoundError) as error:
        print(error, file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(pr, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
