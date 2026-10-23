#!/usr/bin/env python3
"""Attach acceptance criteria and review findings to chapters, and compute the gaps.

Pure functions over the dataclasses from ``guide_inputs``. A range "overlaps" another when
both name the same path and their inclusive line ranges intersect. Standard library only.
"""
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import PurePosixPath

from guide_inputs import SEVERITIES, Anchor, Chapter, Criterion, Finding

_TEST_DIRS = frozenset({"tests", "__tests__", "__snapshots__"})
_TEST_NAME_PATTERNS = ("test_*.py", "*_test.py", "*.test.*", "*.spec.*")


@dataclass(frozen=True)
class FindingPlacement:
    """Findings grouped per chapter, in chapter order, plus those on files the PR did not change."""

    by_chapter: list[list[Finding]]
    outside: list[Finding]


@dataclass(frozen=True)
class Gaps:
    """Criteria with no anchor in a changed file, and changed non-test files no criterion anchor names."""

    unimplemented: list[Criterion]
    unmatched_files: list[str]


def is_test_path(path: str) -> bool:
    """Return True for a test file: under a ``tests``, ``__tests__`` or ``__snapshots__`` directory, or named like a test."""
    parts = PurePosixPath(path).parts
    if any(part in _TEST_DIRS for part in parts):
        return True
    return any(fnmatchcase(parts[-1], pattern) for pattern in _TEST_NAME_PATTERNS)


def _overlaps(a: Anchor, b: Anchor) -> bool:
    return a.path == b.path and a.start <= b.end and b.start <= a.end


def _chapter_by_file(path: str, chapters: list[Chapter]) -> int | None:
    """Return the index of the chapter whose file entries hold ``path``, or None."""
    for i, chapter in enumerate(chapters):
        if any(entry.path == path for entry in chapter.files):
            return i
    return None


def assign_findings(findings: list[Finding], chapters: list[Chapter], changed: list[str]) -> FindingPlacement:
    """Place each finding in a chapter, or in ``outside`` when its file is not a changed file.

    A finding goes to the first chapter with a code ref overlapping its anchor, and failing
    that to the chapter whose files hold its path. Each list is sorted by severity, path,
    then start line. A changed file that no chapter places also lands in ``outside``.
    """
    by_chapter: list[list[Finding]] = [[] for _ in chapters]
    outside: list[Finding] = []
    changed_set = set(changed)
    for finding in findings:
        index = None
        if finding.anchor.path in changed_set:
            index = next(
                (i for i, chapter in enumerate(chapters)
                 if any(_overlaps(ref.anchor, finding.anchor) for ref in chapter.code)),
                None,
            )
            if index is None:
                index = _chapter_by_file(finding.anchor.path, chapters)
        (outside if index is None else by_chapter[index]).append(finding)

    def order(finding: Finding):
        return (SEVERITIES.index(finding.severity), finding.anchor.path, finding.anchor.start)

    return FindingPlacement([sorted(row, key=order) for row in by_chapter], sorted(outside, key=order))


def criteria_by_chapter(criteria: list[Criterion], chapters: list[Chapter]) -> list[list[Criterion]]:
    """Return, per chapter, the criteria that belong to it, in ``criteria`` order.

    A criterion belongs to every chapter with a code ref overlapping one of its anchors. One
    that overlaps no code ref anywhere belongs to the chapter whose files hold its first
    anchor with a placed path, and to no chapter when none of its paths is placed.
    """
    rows: list[list[Criterion]] = [[] for _ in chapters]
    for criterion in criteria:
        matched = [
            i for i, chapter in enumerate(chapters)
            if any(_overlaps(ref.anchor, anchor) for ref in chapter.code for anchor in criterion.implemented_at)
        ]
        if not matched:
            for anchor in criterion.implemented_at:
                index = _chapter_by_file(anchor.path, chapters)
                if index is not None:
                    matched = [index]
                    break
        for i in matched:
            rows[i].append(criterion)
    return rows


def _line_label(anchor: Anchor) -> str:
    return f"L{anchor.start}" if anchor.start == anchor.end else f"L{anchor.start}-L{anchor.end}"


def ac_tags_for_file(criteria: list[Criterion], path: str) -> str:
    """Return the criterion tags for ``path``, such as ``"AC1 L5-L20, AC2 L22-L30"``; empty when there are none."""
    return ", ".join(
        f"{criterion.id} {_line_label(anchor)}"
        for criterion in criteria
        for anchor in criterion.implemented_at
        if anchor.path == path
    )


def find_gaps(criteria: list[Criterion], changed: list[str]) -> Gaps:
    """Return the criteria with no anchor in a changed file, and the changed non-test files no criterion anchors name."""
    changed_set = set(changed)
    unimplemented = [
        criterion for criterion in criteria
        if not any(anchor.path in changed_set for anchor in criterion.implemented_at)
    ]
    named = {anchor.path for criterion in criteria for anchor in criterion.implemented_at}
    unmatched = [path for path in changed if not is_test_path(path) and path not in named]
    return Gaps(unimplemented, unmatched)
