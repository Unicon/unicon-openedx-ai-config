#!/usr/bin/env python3
"""Compose the Plannotator saved guide from the four artifact JSON files and write it.

Reads ``pr.json``, ``chapters.json``, ``criteria.json`` and ``findings.json`` from an
artifacts folder, builds the guide sections with ``guide_mapping`` and ``guide_render``,
writes the Mermaid change map next to the inputs, and saves the envelope where Plannotator
lists saved guides: ``<data-dir>/guides/<repo-key>/<id>.json``. Standard library only.

Usage: ``python3 compose_guide.py --artifacts DIR [--data-dir DIR]``
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from guide_inputs import (
    changed_files,
    check_placement,
    load_chapters,
    load_criteria,
    load_findings,
    load_pr,
)
from guide_mapping import assign_findings, criteria_by_chapter, find_gaps
from guide_render import render_before_you_start, render_change_map, render_file_summary, render_overview

TESTED_PLANNOTATOR_VERSION = "0.28.27"

_PR_URL_RE = re.compile(r"^https?://github\.com/([^/#?]+)/([^/#?]+)/pull/(\d+)(?:/[^#?]*)?(?:[?#].*)?$")
_UNSAFE_RE = re.compile(r"[^a-zA-Z0-9._-]+")
_SLUG_RE = re.compile(r"[^a-z0-9]+")
_SLUG_MAX = 60


@dataclass(frozen=True)
class ComposeResult:
    """Where the saved guide and the change map were written, and any warnings for the user."""

    guide_path: Path
    label: str
    change_map_path: Path
    warnings: list[str]


def canonical_pr_url(url: str) -> str:
    """Return ``https://github.com/<owner>/<repo>/pull/<n>`` for a GitHub pull request URL.

    Accepts ``http`` or ``https``, a trailing slash, a trailing path such as ``/files``, and a
    query or fragment. Raises ``ValueError`` for anything that is not a GitHub pull request URL.
    """
    match = _PR_URL_RE.match(url.strip())
    if not match:
        raise ValueError(f"{url!r} is not a GitHub pull request URL")
    owner, repo, number = match.groups()
    return f"https://github.com/{owner}/{repo}/pull/{number}"


def _sanitize_segment(segment: str) -> str:
    return _UNSAFE_RE.sub("-", segment).strip(".-")


def repo_key_from_pr_url(url: str) -> str:
    """Return Plannotator's repo key, ``host__owner__repo``, for a PR URL; each segment is sanitized."""
    owner, repo = canonical_pr_url(url).split("/")[3:5]
    return "__".join(_sanitize_segment(part) for part in ("github.com", owner, repo))


def make_guide_id(title: str, now_ms: int) -> str:
    """Return a saved-guide id in Plannotator's form ``<epoch-ms>-<slug>``, the slug cut to 60 characters."""
    slug = _SLUG_RE.sub("-", title.lower()).strip("-")[:_SLUG_MAX].rstrip("-")
    return f"{now_ms}-{slug}" if slug else str(now_ms)


def data_dir() -> Path:
    """Return Plannotator's data directory: ``$PLANNOTATOR_DATA_DIR`` when set, else ``~/.plannotator``."""
    override = os.environ.get("PLANNOTATOR_DATA_DIR")
    return Path(override) if override else Path.home() / ".plannotator"


def version_warning(version_output: str | None) -> str | None:
    """Return a warning when Plannotator is missing or is not the tested version, else None.

    ``version_output`` is the text of ``plannotator --version``; the version is its last
    whitespace-separated token. ``None`` means the command was not found.
    """
    if version_output is None:
        return (
            "Plannotator was not found on PATH, so the saved guide cannot be checked against the "
            f"tested version {TESTED_PLANNOTATOR_VERSION}. The guide is written anyway; the "
            "fallback instructions in the skill describe how to open it."
        )
    tokens = version_output.split()
    version = tokens[-1] if tokens else ""
    if version == TESTED_PLANNOTATOR_VERSION:
        return None
    return (
        f"Plannotator version {version or 'unknown'} differs from the tested version "
        f"{TESTED_PLANNOTATOR_VERSION}. The saved-guide format may have changed. "
        "If the guide does not appear, use the fallback instructions in the skill."
    )


def _write_json_atomic(path: Path, data: dict) -> None:
    """Write ``data`` as JSON to ``path`` through a temporary file in the same folder and ``os.replace``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False,
    )
    try:
        with handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(handle.name, path)
    except BaseException:
        Path(handle.name).unlink(missing_ok=True)
        raise


def compose(artifacts: Path, *, data_dir: Path, now_ms: int, today: str, version_output: str | None) -> ComposeResult:
    """Build the saved guide from ``artifacts`` and write it under ``data_dir``.

    Raises ``PlacementError`` when the chapters do not place every changed file exactly once,
    and ``ValueError`` for malformed inputs or a PR URL that is not a GitHub pull request.
    Also writes ``change-map.mmd`` and a copy of the envelope, ``guide-envelope.json``, into
    ``artifacts``.
    """
    artifacts = Path(artifacts).resolve()
    pr = load_pr(artifacts / "pr.json")
    changed = changed_files(pr)
    chapters = load_chapters(artifacts / "chapters.json")
    criteria = load_criteria(artifacts / "criteria.json")
    verdict, findings = load_findings(artifacts / "findings.json")
    check_placement(changed, chapters)

    pr_url = canonical_pr_url(pr["url"])
    number, pr_title = pr["number"], pr["title"]

    change_map_path = artifacts / "change-map.mmd"
    change_map_path.write_text(render_change_map(chapters), encoding="utf-8")

    placement = assign_findings(findings, chapters, changed)
    criteria_rows = criteria_by_chapter(criteria, chapters)
    first_section_by_path: dict[str, int] = {}
    for i, chapter in enumerate(chapters):
        for entry in chapter.files:
            first_section_by_path.setdefault(entry.path, i + 2)

    note = f"Change map: {change_map_path}. Open it with plannotator annotate."
    sections = [{
        "title": "Before you start",
        "overview": render_before_you_start(
            verdict=verdict, gaps=find_gaps(criteria, changed), outside=placement.outside, change_map_note=note,
        ),
        "diffs": [],
    }]
    for i, chapter in enumerate(chapters):
        sections.append({
            "title": chapter.title,
            "overview": render_overview(
                chapter,
                criteria=criteria_rows[i],
                findings=placement.by_chapter[i],
                first_section_by_path=first_section_by_path,
                this_section=i + 2,
            ),
            "diffs": [{"file": entry.path, "summary": render_file_summary(entry, criteria)} for entry in chapter.files],
        })

    label = f"PR #{number} prepared {today}"
    title = f"PR #{number}: {pr_title}"
    envelope = {
        "version": 1,
        "savedAt": now_ms,
        "label": label,
        "title": title,
        "headSha": pr["headRefOid"],
        "prUrl": pr_url,
        "guide": {
            "title": title,
            "intent": f"{pr_title}. Prepared on {today}: {len(chapters)} chapters, {len(findings)} findings.",
            "sections": sections,
        },
        "reviewed": [False] * len(sections),
    }

    guide_path = Path(data_dir) / "guides" / repo_key_from_pr_url(pr_url) / f"{make_guide_id(title, now_ms)}.json"
    _write_json_atomic(guide_path, envelope)
    _write_json_atomic(artifacts / "guide-envelope.json", envelope)
    warning = version_warning(version_output)
    return ComposeResult(guide_path, label, change_map_path, [warning] if warning else [])


def _plannotator_version() -> str | None:
    """Return the output of ``plannotator --version``, or None when it is missing or does not answer in time."""
    try:
        result = subprocess.run(["plannotator", "--version"], capture_output=True, text=True, timeout=10)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip()


def main(argv: list[str] | None = None) -> int:
    """Run the CLI; return 0 on success and 1, with the message on stderr, for invalid or missing inputs."""
    parser = argparse.ArgumentParser(description="Write the prepare-pr-review saved guide for Plannotator.")
    parser.add_argument("--artifacts", required=True, type=Path, help="folder with pr, chapters, criteria and findings JSON")
    parser.add_argument("--data-dir", type=Path, default=None, help="Plannotator data directory (default: $PLANNOTATOR_DATA_DIR or ~/.plannotator)")
    args = parser.parse_args(argv)
    now = datetime.now()
    try:
        result = compose(
            args.artifacts,
            data_dir=args.data_dir or data_dir(),
            now_ms=int(now.timestamp() * 1000),
            today=now.strftime("%Y-%m-%d"),
            version_output=_plannotator_version(),
        )
    except (ValueError, FileNotFoundError) as error:
        print(error, file=sys.stderr)
        return 1
    print(f"Guide: {result.guide_path}")
    print(f"Label: {result.label}")
    print(f"Change map: {result.change_map_path}")
    for warning in result.warnings:
        print(f"Warning: {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
