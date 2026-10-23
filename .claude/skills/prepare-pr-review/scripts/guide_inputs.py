#!/usr/bin/env python3
"""Input models and loaders for the prepare-pr-review scripts.

Reads the PR metadata, acceptance criteria, the mapper's labeled code pieces, and review
findings from JSON, validates them, and exposes them as frozen dataclasses. Also checks that
the mapper summarized every changed file and labeled at least one piece in it. Standard
library only.
"""
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

SEVERITIES = ("Bug", "Gap", "Question", "Suggestion", "Nit")
KINDS = ("implements", "edge case", "test", "refactor", "setup", "migration", "docs", "removal", "other")

_AC_ID_RE = re.compile(r"^AC[1-9][0-9]*$")
_PIECES_FILE_RE = re.compile(r"^pieces-([1-9][0-9]*)\.json$")

_ANCHOR_RE = re.compile(r"^(.+):(\d+)(?:-(\d+))?$")


@dataclass(frozen=True)
class Anchor:
    path: str
    start: int
    end: int


@dataclass(frozen=True)
class Criterion:
    """One acceptance criterion; ``text`` is the exact source text with LF line endings."""
    id: str
    text: str
    source: str
    verdict: str | None
    tested_by: tuple[str, ...]


@dataclass(frozen=True)
class Background:
    """A Gherkin ``Background:`` block shared by the scenarios of one ticket."""
    source: str
    text: str


@dataclass(frozen=True)
class Piece:
    """A labeled stretch of changed code: the criteria it serves, what kind of change it is, and why."""
    anchor: Anchor
    acs: tuple[str, ...]
    kind: str
    purpose: str
    key_for: tuple[str, ...]


@dataclass(frozen=True)
class FileSummary:
    path: str
    summary: str


@dataclass(frozen=True)
class MapperOutput:
    files: tuple[FileSummary, ...]
    pieces: tuple[Piece, ...]


@dataclass(frozen=True)
class Finding:
    severity: str
    title: str
    anchor: Anchor
    why: str


class MapperCheckError(ValueError):
    """Raised when the mapper's output and the PR's changed files or criteria disagree.

    ``missing_pieces`` lists changed files with no piece, ``missing_summaries`` lists changed
    files with no summary, ``unknown_files`` lists files the mapper mentioned that the PR did not
    change, and ``unknown_acs`` lists criterion ids the mapper used that do not exist. All four are
    sorted lists.
    """

    def __init__(self, missing_pieces, missing_summaries, unknown_files, unknown_acs):
        self.missing_pieces = missing_pieces
        self.missing_summaries = missing_summaries
        self.unknown_files = unknown_files
        self.unknown_acs = unknown_acs
        parts = []
        if missing_pieces:
            parts.append("changed files with no piece: " + ", ".join(missing_pieces))
        if missing_summaries:
            parts.append("changed files with no summary: " + ", ".join(missing_summaries))
        if unknown_files:
            parts.append("files the PR did not change: " + ", ".join(unknown_files))
        if unknown_acs:
            parts.append("unknown criterion ids: " + ", ".join(unknown_acs))
        super().__init__("; ".join(parts))


def one_line(text: str) -> str:
    """Collapse every whitespace run, newlines included, to one space and strip the ends."""
    return " ".join(text.split())


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


def _criterion(row: dict, index: int) -> Criterion:
    where = f"criteria.json criteria[{index}]"
    criterion_id = _require_str(row, "id", where)
    if not _AC_ID_RE.match(criterion_id):
        raise ValueError(f"{where}: field 'id' {criterion_id!r} must look like AC1, AC2, ...")
    where = f"criterion {criterion_id}"
    text = _require_str(row, "text", where).replace("\r\n", "\n")
    if not text.strip():
        raise ValueError(f"{where}: field 'text' must not be blank")
    return Criterion(
        criterion_id,
        text,
        _require_str(row, "source", where),
        _optional_str(row, "verdict", where),
        tuple(_require_str_list(row, "tested_by", where)),
    )


def load_criteria(path) -> tuple[list[Criterion], list[Background]]:
    """Load and validate criteria.json; return the criteria and the (possibly empty) backgrounds.

    Criterion ids must match ``AC<n>`` and be unique. CRLF line endings in text become LF; the text
    is otherwise kept exactly as written.
    """
    data = _read_json(path)
    criteria = []
    seen = set()
    for i, row in enumerate(_require_rows(data, "criteria", "criteria.json")):
        criterion = _criterion(row, i)
        if criterion.id in seen:
            raise ValueError(f"duplicate criterion id {criterion.id!r}")
        seen.add(criterion.id)
        criteria.append(criterion)
    backgrounds = []
    if "backgrounds" in data:
        for i, row in enumerate(_require_rows(data, "backgrounds", "criteria.json")):
            where = f"criteria.json backgrounds[{i}]"
            backgrounds.append(Background(
                _require_str(row, "source", where),
                _require_str(row, "text", where).replace("\r\n", "\n"),
            ))
    return criteria, backgrounds


def _piece(row: dict, index: int) -> Piece:
    where = f"piece {index + 1}"
    anchor = parse_anchor(_require_str(row, "anchor", where))
    acs = tuple(_require_str_list(row, "acs", where))
    kind = row.get("kind")
    if kind not in KINDS:
        raise ValueError(f"{where}: kind {kind!r} must be one of {KINDS}")
    purpose = _require_str(row, "purpose", where)
    key_for = tuple(_require_str_list(row, "key_for", where))
    outside = [a for a in key_for if a not in acs]
    if outside:
        raise ValueError(f"{where}: field 'key_for' lists {', '.join(outside)}, which are not in acs")
    return Piece(anchor, acs, kind, purpose, key_for)


def _require_unique_summaries(files, where: str) -> None:
    seen = set()
    for entry in files:
        if entry.path in seen:
            raise ValueError(f"{where}: {entry.path} is summarized more than once")
        seen.add(entry.path)


def load_mapper_file(path) -> MapperOutput:
    """Load and validate one ``pieces-<k>.json``. A piece's ``key_for`` must be a subset of its ``acs``."""
    data = _read_json(path)
    where = Path(path).name
    files = tuple(
        FileSummary(_require_str(row, "path", f"{where} files[{i}]"), _require_str(row, "summary", f"{where} files[{i}]"))
        for i, row in enumerate(_require_rows(data, "files", where))
    )
    _require_unique_summaries(files, where)
    pieces = tuple(_piece(row, i) for i, row in enumerate(_require_rows(data, "pieces", where)))
    return MapperOutput(files, pieces)


def load_mapper_outputs(artifacts: Path) -> MapperOutput:
    """Merge every ``pieces-<k>.json`` in ``artifacts`` (k a positive integer) in numeric order of k.

    Raises ``ValueError`` when no such file exists or when a path is summarized more than once
    across the files.
    """
    found = sorted(
        (int(m.group(1)), entry)
        for entry in Path(artifacts).iterdir()
        if (m := _PIECES_FILE_RE.match(entry.name))
    )
    if not found:
        raise ValueError(f"no pieces-<k>.json file in {artifacts}")
    files, pieces = [], []
    for _, entry in found:
        output = load_mapper_file(entry)
        files.extend(output.files)
        pieces.extend(output.pieces)
    _require_unique_summaries(files, "pieces-*.json")
    return MapperOutput(tuple(files), tuple(pieces))


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
    ``number`` and ``changedFiles`` are integers. The composer builds the guide's identity from the
    first four, and ``changedFiles`` lets ``changed_files`` detect a truncated file list.
    """
    pr = _read_json(path)
    if not isinstance(pr, dict):
        raise ValueError("pr.json: must be a JSON object")
    for field in ("url", "title", "headRefOid"):
        _require_str(pr, field, "pr.json")
    for field in ("number", "changedFiles"):
        if not isinstance(pr.get(field), int) or isinstance(pr[field], bool):
            raise ValueError(f"pr.json: field {field!r} must be an integer")
    return pr


def changed_files(pr: dict) -> list[str]:
    """Return the PR's changed file paths in the order gh lists them, deleted files included.

    Raises ``ValueError`` when the number of listed files differs from ``changedFiles``, which
    means ``pr.json`` holds a truncated list (``gh pr view`` stops at 100 files).
    """
    paths = [_require_str(row, "path", f"pr.json files[{i}]") for i, row in enumerate(_require_rows(pr, "files", "pr.json"))]
    if len(paths) != pr["changedFiles"]:
        raise ValueError(
            f"pr.json lists {len(paths)} files but changedFiles is {pr['changedFiles']}; "
            "rebuild it with fetch_pr.py"
        )
    return paths


def check_mapper_output(expected: list[str], mapper: MapperOutput, criteria: list[Criterion]) -> None:
    """Raise MapperCheckError unless the mapper summarized and labeled every expected file, and only those.

    ``expected`` is the list of changed file paths (or a batch of them). Every expected file needs a
    summary and at least one piece. Pieces and summaries may name only expected files, and pieces may
    cite only the ids in ``criteria``.
    """
    expected_set = set(expected)
    with_pieces = {p.anchor.path for p in mapper.pieces}
    with_summary = {f.path for f in mapper.files}
    known_acs = {c.id for c in criteria}
    used_acs = {a for p in mapper.pieces for a in p.acs + p.key_for}
    missing_pieces = sorted(expected_set - with_pieces)
    missing_summaries = sorted(expected_set - with_summary)
    unknown_files = sorted((with_pieces | with_summary) - expected_set)
    unknown_acs = sorted(used_acs - known_acs)
    if missing_pieces or missing_summaries or unknown_files or unknown_acs:
        raise MapperCheckError(missing_pieces, missing_summaries, unknown_files, unknown_acs)


def main(argv=None) -> int:
    """Run the command line.

    ``--check DIR`` checks ``DIR/pr.json``, ``DIR/criteria.json`` and every ``DIR/pieces-<k>.json``
    together and prints ``Mapper output OK: <n> files, <p> pieces.``. ``--check-batch DIR K`` checks
    ``DIR/pieces-K.json`` against the path list in ``DIR/batch-K.json`` and prints
    ``Batch K OK: <n> files, <p> pieces.``. Returns 0 when the check passes, 1 with the problem on
    stderr when a file is missing or invalid or the check fails, and 2 on a usage error.
    """
    args = sys.argv[1:] if argv is None else list(argv)
    usage = "usage: guide_inputs.py --check ARTIFACT_DIR | --check-batch ARTIFACT_DIR K"
    if len(args) == 2 and args[0] == "--check":
        mode = "all"
    elif len(args) == 3 and args[0] == "--check-batch" and _PIECES_FILE_RE.match(f"pieces-{args[2]}.json"):
        mode = "batch"
    else:
        print(usage, file=sys.stderr)
        return 2
    folder = Path(args[1])
    try:
        if mode == "all":
            expected = changed_files(load_pr(folder / "pr.json"))
            criteria, _ = load_criteria(folder / "criteria.json")
            mapper = load_mapper_outputs(folder)
            label = "Mapper output"
        else:
            criteria, _ = load_criteria(folder / "criteria.json")
            expected = _read_json(folder / f"batch-{args[2]}.json")
            if not isinstance(expected, list) or not all(isinstance(p, str) for p in expected):
                raise ValueError(f"batch-{args[2]}.json: must be a list of path strings")
            mapper = load_mapper_file(folder / f"pieces-{args[2]}.json")
            label = f"Batch {args[2]}"
        check_mapper_output(expected, mapper, criteria)
    except (ValueError, FileNotFoundError) as error:
        print(error, file=sys.stderr)
        return 1
    print(f"{label} OK: {len(mapper.files)} files, {len(mapper.pieces)} pieces.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
