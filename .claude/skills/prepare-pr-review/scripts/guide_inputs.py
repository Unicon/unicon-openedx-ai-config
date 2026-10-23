#!/usr/bin/env python3
"""Input models and loaders for the prepare-pr-review scripts.

Reads the PR metadata, chapter draft, acceptance-criteria rows, and review findings
from JSON, validates them, and exposes them as frozen dataclasses. Also checks that
every changed file is placed in exactly one chapter. Standard library only.
"""
import json
import re
from collections import Counter
from dataclasses import dataclass

SEVERITIES = ("Bug", "Gap", "Question", "Suggestion", "Nit")
CHAPTER_KINDS = ("step", "layer")

_ANCHOR_RE = re.compile(r"^(.+):(\d+)(?:-(\d+))?$")


@dataclass(frozen=True)
class Anchor:
    path: str
    start: int
    end: int


@dataclass(frozen=True)
class CodeRef:
    anchor: Anchor
    role: str


@dataclass(frozen=True)
class FileEntry:
    path: str
    summary: str


@dataclass(frozen=True)
class Chapter:
    kind: str
    title: str
    do: str | None
    expect: str | None
    original: str | None
    code: tuple[CodeRef, ...]
    files: tuple[FileEntry, ...]


@dataclass(frozen=True)
class Criterion:
    id: str
    text: str
    implemented_at: tuple[Anchor, ...]
    tested_by: tuple[str, ...]
    verdict: str


@dataclass(frozen=True)
class Finding:
    severity: str
    title: str
    anchor: Anchor
    why: str


class PlacementError(ValueError):
    """Raised when changed files and chapter placement disagree.

    ``missing`` lists changed files no chapter places, ``duplicated`` lists files placed
    in more than one chapter entry, and ``unknown`` lists placed files the PR did not
    change. All three are sorted lists of paths.
    """

    def __init__(self, missing, duplicated, unknown):
        self.missing = missing
        self.duplicated = duplicated
        self.unknown = unknown
        parts = []
        if missing:
            parts.append("changed files placed in no chapter: " + ", ".join(missing))
        if duplicated:
            parts.append("files placed more than once: " + ", ".join(duplicated))
        if unknown:
            parts.append("placed files the PR did not change: " + ", ".join(unknown))
        super().__init__("; ".join(parts))


def parse_anchor(text: str) -> Anchor:
    """Parse ``path:LINE`` or ``path:START-END`` into an Anchor; lines are 1-based and start <= end."""
    match = _ANCHOR_RE.match(text)
    if not match:
        raise ValueError(f"anchor {text!r} is not of the form path:LINE or path:START-END")
    path, start, end = match.group(1), int(match.group(2)), match.group(3)
    end = int(end) if end is not None else start
    if start < 1 or end < start:
        raise ValueError(f"anchor {text!r} needs 1 <= start <= end")
    return Anchor(path, start, end)


def _read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _require_str(row: dict, field: str, where: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{where}: field {field!r} must be a non-empty string")
    return value


def _optional_str(row: dict, field: str, where: str) -> str | None:
    value = row.get(field)
    if value is not None and not isinstance(value, str):
        raise ValueError(f"{where}: field {field!r} must be a string or null")
    return value


def _require_rows(container, field: str, where: str) -> list:
    """Return ``container[field]``, which must be a list of JSON objects."""
    if not isinstance(container, dict):
        raise ValueError(f"{where}: must be a JSON object")
    rows = container.get(field)
    if not isinstance(rows, list):
        raise ValueError(f"{where}: field {field!r} must be a list")
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"{where}: {field}[{i}] must be a JSON object")
    return rows


def _require_str_list(row: dict, field: str, where: str) -> list[str]:
    """Return ``row[field]``, which must be a list of strings; an absent field is an empty list."""
    values = row.get(field, [])
    if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
        raise ValueError(f"{where}: field {field!r} must be a list of strings")
    return values


def _chapter(row: dict, index: int) -> Chapter:
    where = f"chapter {index + 1}"
    kind = row.get("kind")
    if kind not in CHAPTER_KINDS:
        raise ValueError(f"{where}: kind {kind!r} must be one of {CHAPTER_KINDS}")
    title = _require_str(row, "title", where)
    if kind == "step":
        do = _require_str(row, "do", where)
        expect = _require_str(row, "expect", where)
        original = _optional_str(row, "original", where)
    else:
        extra = [f for f in ("do", "expect", "original") if row.get(f) is not None]
        if extra:
            raise ValueError(f"{where}: a layer chapter cannot have {', '.join(extra)}")
        do = expect = original = None
    code = tuple(
        CodeRef(parse_anchor(_require_str(ref, "anchor", where)), _require_str(ref, "role", where))
        for ref in _require_rows(row, "code", where)
    )
    files = tuple(
        FileEntry(_require_str(entry, "path", where), _require_str(entry, "summary", where))
        for entry in _require_rows(row, "files", where)
    )
    return Chapter(kind, title, do, expect, original, code, files)


def load_chapters(path) -> list[Chapter]:
    """Load and validate chapters.json. Step chapters need do and expect; layer chapters must not have them."""
    rows = _require_rows(_read_json(path), "chapters", "chapters.json")
    return [_chapter(row, i) for i, row in enumerate(rows)]


def load_criteria(path) -> list[Criterion]:
    """Load and validate criteria.json. Criterion ids must be unique."""
    criteria = []
    seen = set()
    for row in _require_rows(_read_json(path), "criteria", "criteria.json"):
        criterion_id = _require_str(row, "id", "criterion")
        if criterion_id in seen:
            raise ValueError(f"duplicate criterion id {criterion_id!r}")
        seen.add(criterion_id)
        where = f"criterion {criterion_id}"
        criteria.append(Criterion(
            criterion_id,
            _require_str(row, "text", where),
            tuple(parse_anchor(a) for a in _require_str_list(row, "implemented_at", where)),
            tuple(_require_str_list(row, "tested_by", where)),
            _require_str(row, "verdict", where),
        ))
    return criteria


def load_findings(path) -> tuple[str, list[Finding]]:
    """Load and validate findings.json; return the verdict line and the findings in file order."""
    data = _read_json(path)
    findings = []
    for i, row in enumerate(_require_rows(data, "findings", "findings.json")):
        where = f"finding {i + 1}"
        severity = row.get("severity")
        if severity not in SEVERITIES:
            raise ValueError(f"{where}: severity {severity!r} must be one of {SEVERITIES}")
        findings.append(Finding(
            severity,
            _require_str(row, "title", where),
            parse_anchor(_require_str(row, "anchor", where)),
            _require_str(row, "why", where),
        ))
    return _require_str(data, "verdict", "findings"), findings


def load_pr(path) -> dict:
    """Load the ``gh pr view --json`` output as a dict.

    Raises ``ValueError`` unless ``url``, ``title`` and ``headRefOid`` are non-empty strings and
    ``number`` is an integer, because the composer builds the guide's identity from them.
    """
    pr = _read_json(path)
    if not isinstance(pr, dict):
        raise ValueError("pr.json: must be a JSON object")
    for field in ("url", "title", "headRefOid"):
        _require_str(pr, field, "pr.json")
    if not isinstance(pr.get("number"), int) or isinstance(pr["number"], bool):
        raise ValueError("pr.json: field 'number' must be an integer")
    return pr


def changed_files(pr: dict) -> list[str]:
    """Return the PR's changed file paths in the order gh lists them, deleted files included."""
    return [_require_str(row, "path", f"pr.json files[{i}]") for i, row in enumerate(_require_rows(pr, "files", "pr.json"))]


def check_placement(changed: list[str], chapters: list[Chapter]) -> None:
    """Raise PlacementError unless every changed file is placed in exactly one chapter file entry."""
    placed = Counter(entry.path for chapter in chapters for entry in chapter.files)
    changed_set = set(changed)
    missing = sorted(changed_set - placed.keys())
    duplicated = sorted(p for p, n in placed.items() if n > 1)
    unknown = sorted(placed.keys() - changed_set)
    if missing or duplicated or unknown:
        raise PlacementError(missing, duplicated, unknown)
