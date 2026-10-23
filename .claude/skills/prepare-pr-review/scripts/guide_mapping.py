#!/usr/bin/env python3
"""Derive the guide's chapters, key pieces, and finding placement.

Pure functions over the dataclasses from ``guide_inputs``. There is one chapter per acceptance
criterion, then purpose chapters for pieces that serve no criterion. A range "overlaps" another
when both name the same path and their inclusive line ranges intersect. Standard library only.
"""
import re
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import PurePosixPath

from guide_inputs import SEVERITIES, Anchor, Criterion, Finding, MapperOutput, Piece, one_line

_TEST_DIRS = frozenset({"tests", "__tests__", "__snapshots__"})
_TEST_NAME_PATTERNS = ("test_*.py", "*_test.py", "*.test.*", "*.spec.*")
_NAME_MAX = 80
_SCENARIO_RE = re.compile(r"^Scenario(?: Outline)?:\s*")

PURPOSE_CHAPTERS = (
    ("Edge cases", ("edge case",)),
    ("Tests", ("test",)),
    ("Refactoring and setup", ("refactor", "setup", "migration", "docs", "removal")),
    ("Other changes", ("implements", "other")),
)


@dataclass(frozen=True)
class Chapter:
    """One guide chapter.

    ``kind`` is ``"ac"`` or ``"purpose"``. ``ac`` is the criterion id of an ``"ac"`` chapter, else
    None. ``pieces`` are all pieces serving the chapter, and ``files`` are the changed files whose
    diff the chapter shows, each file in exactly one chapter.
    """
    kind: str
    title: str
    ac: str | None
    pieces: tuple[Piece, ...]
    files: tuple[str, ...]


@dataclass(frozen=True)
class FindingPlacement:
    """Findings on changed files grouped by path, plus those on files the PR did not change."""
    by_path: dict[str, tuple[Finding, ...]]
    outside: tuple[Finding, ...]


def is_test_path(path: str) -> bool:
    """Return True for a test file: under a ``tests``, ``__tests__`` or ``__snapshots__`` directory, or named like a test."""
    parts = PurePosixPath(path).parts
    if any(part in _TEST_DIRS for part in parts):
        return True
    return any(fnmatchcase(parts[-1], pattern) for pattern in _TEST_NAME_PATTERNS)


def _overlaps(a: Anchor, b: Anchor) -> bool:
    return a.path == b.path and a.start <= b.end and b.start <= a.end


def _overlaps(a: Anchor, b: Anchor) -> bool:
    return a.path == b.path and a.start <= b.end and b.start <= a.end


def ac_name(text: str) -> str:
    """Return a short chapter name for criterion text.

    The name is the text after ``Scenario:`` or ``Scenario Outline:`` on the first non-blank line,
    otherwise that whole line. It is collapsed to one line and cut to 80 characters, ending in
    ``…`` when it was longer.
    """
    first = next((line for line in text.splitlines() if line.strip()), "")
    name = one_line(_SCENARIO_RE.sub("", first.strip(), count=1))
    return name if len(name) <= _NAME_MAX else name[: _NAME_MAX - 1] + "…"


def _piece_order(changed: list[str]):
    """Return the sort key for pieces: the file's index in ``changed``, then start line, then end line."""
    index = {path: i for i, path in enumerate(changed)}

    def order(piece: Piece):
        return (index.get(piece.anchor.path, len(index)), piece.anchor.start, piece.anchor.end)

    return order


def build_chapters(criteria: list[Criterion], mapper: MapperOutput, changed: list[str]) -> list[Chapter]:
    """Return the guide's chapters: one per criterion in order, then the purpose chapters that have pieces.

    A criterion chapter holds every piece citing the criterion, so a piece citing two criteria
    appears in both. A purpose chapter holds the pieces that cite no criterion and have one of its
    kinds. Each changed file goes to the first chapter, in guide order, holding a piece in it; the
    chapter lists non-test files before test files, each group in ``changed`` order.
    """
    order = _piece_order(changed)
    ordered = sorted(mapper.pieces, key=order)
    groups = [("ac", f"{c.id}: {ac_name(c.text)}", c.id, [p for p in ordered if c.id in p.acs]) for c in criteria]
    unassigned = [p for p in ordered if not p.acs]
    for title, kinds in PURPOSE_CHAPTERS:
        pieces = [p for p in unassigned if p.kind in kinds]
        if pieces:
            groups.append(("purpose", title, None, pieces))
    placed: list[list[str]] = [[] for _ in groups]
    for path in changed:
        for i, group in enumerate(groups):
            if any(p.anchor.path == path for p in group[3]):
                placed[i].append(path)
                break
    return [
        Chapter(kind, title, ac, tuple(pieces),
                tuple([f for f in files if not is_test_path(f)] + [f for f in files if is_test_path(f)]))
        for (kind, title, ac, pieces), files in zip(groups, placed)
    ]


def key_pieces(criteria: list[Criterion], mapper: MapperOutput, changed: list[str]) -> dict[str, Piece]:
    """Return each criterion's key piece, the one the guide shows first; criteria with no piece have no entry.

    Among the pieces marked ``key_for`` the criterion, an ``implements`` piece beats other kinds, then
    piece order decides. With no marked piece, the criterion's first piece in piece order is the key piece.
    """
    order = _piece_order(changed)
    result = {}
    for criterion in criteria:
        serving = sorted((p for p in mapper.pieces if criterion.id in p.acs), key=order)
        marked = [p for p in serving if criterion.id in p.key_for]
        if marked:
            result[criterion.id] = min(marked, key=lambda p: (p.kind != "implements", order(p)))
        elif serving:
            result[criterion.id] = serving[0]
    return result


def place_findings(findings: list[Finding], changed: list[str]) -> FindingPlacement:
    """Group findings on changed files by path, and collect the rest as ``outside``.

    Findings on one path are sorted by start line, end line, then severity. ``outside`` is sorted by
    severity, path, then start line.
    """
    changed_set = set(changed)
    by_path: dict[str, list[Finding]] = {}
    outside = []
    for finding in findings:
        if finding.anchor.path in changed_set:
            by_path.setdefault(finding.anchor.path, []).append(finding)
        else:
            outside.append(finding)
    return FindingPlacement(
        {path: tuple(sorted(rows, key=lambda f: (f.anchor.start, f.anchor.end, SEVERITIES.index(f.severity))))
         for path, rows in by_path.items()},
        tuple(sorted(outside, key=lambda f: (SEVERITIES.index(f.severity), f.anchor.path, f.anchor.start))),
    )


def acs_without_code(criteria: list[Criterion], chapters: list[Chapter]) -> list[Criterion]:
    """Return the criteria, in order, whose chapter has no piece."""
    with_code = {c.ac for c in chapters if c.kind == "ac" and c.pieces}
    return [c for c in criteria if c.id not in with_code]


def section_of_file(chapters: list[Chapter]) -> dict[str, int]:
    """Map each placed file to its guide section number.

    "Before you start" is section 1, so chapter ``i`` (0-based) is section ``i + 2``.
    """
    return {path: i + 2 for i, chapter in enumerate(chapters) for path in chapter.files}
