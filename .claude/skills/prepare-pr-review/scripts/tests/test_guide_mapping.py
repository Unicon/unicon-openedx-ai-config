import pytest

from guide_inputs import Anchor, Criterion, Finding
from guide_mapping import (
    ac_tags_for_file,
    assign_findings,
    criteria_by_chapter,
    find_gaps,
    is_test_path,
)


@pytest.mark.parametrize("path,expected", [
    ("src/data/api.test.ts", True), ("src/x/__tests__/a.tsx", True), ("tests/test_models.py", True),
    ("pkg/test_views.py", True), ("pkg/views_test.py", True), ("src/a.spec.js", True),
    ("src/__snapshots__/a.snap", True), ("src/latest.py", False), ("src/contest.py", False),
    ("src/pages/CompetencyPage.tsx", False),
])
def test_is_test_path(path, expected):
    assert is_test_path(path) is expected


def test_assign_findings_by_overlap(inputs):
    placed = assign_findings(inputs.findings, inputs.chapters, inputs.changed)
    assert [f.severity for f in placed.by_chapter[0]] == ["Nit"]
    assert [f.severity for f in placed.by_chapter[1]] == ["Bug"]
    assert placed.by_chapter[2] == []


def test_assign_findings_fall_back_to_file_placement(inputs):
    f = Finding("Gap", "No down migration", Anchor("migrations/0002_add_level.py", 1, 1), "w")
    placed = assign_findings([f], inputs.chapters, inputs.changed)
    assert placed.by_chapter[2] == [f]


def test_findings_outside_changed_files(inputs):
    placed = assign_findings(inputs.findings, inputs.chapters, inputs.changed)
    assert [f.anchor.path for f in placed.outside] == ["src/unchanged/Caller.tsx"]


def test_findings_sorted_by_severity_then_path_then_line(inputs):
    path = "src/pages/CompetencyPage.tsx"
    findings = [
        Finding("Nit", "b", Anchor(path, 20, 20), "w"),
        Finding("Nit", "a", Anchor(path, 13, 13), "w"),
        Finding("Bug", "c", Anchor(path, 25, 25), "w"),
    ]
    placed = assign_findings(findings, inputs.chapters, inputs.changed)
    assert [f.title for f in placed.by_chapter[0]] == ["c", "a", "b"]


def test_criteria_by_overlap(inputs):
    ids = [[c.id for c in row] for row in criteria_by_chapter(inputs.criteria, inputs.chapters)]
    assert ids == [["AC1"], ["AC2"], []]


def test_criteria_fall_back_to_file_placement(inputs):
    lone = Criterion("AC9", "t", (Anchor("migrations/0002_add_level.py", 3, 9),), (), "Covered")
    ids = [[c.id for c in row] for row in criteria_by_chapter([lone], inputs.chapters)]
    assert ids == [[], [], ["AC9"]]


def test_ac_tags_for_file(inputs):
    assert ac_tags_for_file(inputs.criteria, "src/data/api.ts") == "AC1 L5-L20, AC2 L22-L30"
    assert ac_tags_for_file(inputs.criteria, "src/old/Legacy.tsx") == ""


def test_ac_tags_render_single_line_as_one_number():
    c = Criterion("AC1", "t", (Anchor("a.py", 15, 15),), (), "Covered")
    assert ac_tags_for_file([c], "a.py") == "AC1 L15"


def test_find_gaps(inputs):
    gaps = find_gaps(inputs.criteria, inputs.changed)
    assert [c.id for c in gaps.unimplemented] == ["AC3"]
    assert gaps.unmatched_files == ["migrations/0002_add_level.py", "src/old/Legacy.tsx"]
