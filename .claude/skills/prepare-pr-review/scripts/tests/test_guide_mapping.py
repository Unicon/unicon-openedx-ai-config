import pytest

from guide_inputs import Anchor, MapperOutput, Piece
from guide_mapping import (
    acs_without_code,
    ac_name,
    build_chapters,
    is_test_path,
    key_pieces,
    place_findings,
    section_of_file,
)


@pytest.mark.parametrize("path,expected", [
    ("src/data/api.test.ts", True), ("src/x/__tests__/a.tsx", True), ("tests/test_models.py", True),
    ("pkg/test_views.py", True), ("pkg/views_test.py", True), ("src/a.spec.js", True),
    ("src/__snapshots__/a.snap", True), ("src/latest.py", False), ("src/contest.py", False),
    ("src/pages/CompetencyPage.tsx", False),
])
def test_is_test_path(path, expected):
    assert is_test_path(path) is expected


def test_chapter_order_and_titles(inputs):
    chapters = build_chapters(inputs.criteria, inputs.mapper, inputs.changed)
    assert [c.title for c in chapters] == [
        "AC1: Author adds a competency", "AC2: Author changes the level",
        "AC3: Deleting asks for confirmation", "Refactoring and setup"]
    assert [c.kind for c in chapters] == ["ac", "ac", "ac", "purpose"]


def test_file_placement(inputs):
    chapters = build_chapters(inputs.criteria, inputs.mapper, inputs.changed)
    assert [c.files for c in chapters] == [
        ("src/pages/CompetencyPage.tsx", "src/data/api.ts", "src/data/api.test.ts"), (), (),
        ("migrations/0002_add_level.py", "src/old/Legacy.tsx")]


def test_shared_piece_serves_both_acs(inputs):
    chapters = build_chapters(inputs.criteria, inputs.mapper, inputs.changed)
    shared = inputs.mapper.pieces[5]
    assert shared in chapters[0].pieces and shared in chapters[1].pieces
    assert [c.id for c in acs_without_code(inputs.criteria, chapters)] == ["AC3"]


def test_key_pieces(inputs):
    keys = key_pieces(inputs.criteria, inputs.mapper, inputs.changed)
    assert keys["AC1"].anchor == Anchor("src/pages/CompetencyPage.tsx", 12, 30)
    assert keys["AC2"].anchor == Anchor("src/data/api.ts", 22, 30)
    assert "AC3" not in keys


def test_key_piece_falls_back_to_first_piece(inputs):
    only_tests = MapperOutput(inputs.mapper.files, (
        Piece(Anchor("src/data/api.test.ts", 50, 60), ("AC2",), "test", "covers b", ()),
        Piece(Anchor("src/data/api.test.ts", 10, 20), ("AC2",), "test", "covers a", ())))
    assert key_pieces(inputs.criteria, only_tests, inputs.changed)["AC2"].purpose == "covers a"


def test_key_piece_prefers_implements_when_several_are_marked(inputs):
    marked = MapperOutput(inputs.mapper.files, (
        Piece(Anchor("src/data/api.ts", 1, 2), ("AC2",), "edge case", "e", ("AC2",)),
        Piece(Anchor("src/data/api.ts", 9, 9), ("AC2",), "implements", "i", ("AC2",))))
    assert key_pieces(inputs.criteria, marked, inputs.changed)["AC2"].purpose == "i"


def test_place_findings(inputs):
    placed = place_findings(inputs.findings, inputs.changed)
    assert [f.severity for f in placed.by_path["src/data/api.ts"]] == ["Bug"]
    assert [f.severity for f in placed.by_path["src/pages/CompetencyPage.tsx"]] == ["Nit"]
    assert [f.anchor.path for f in placed.outside] == ["src/unchanged/Caller.tsx"]


@pytest.mark.parametrize("text,name", [
    ("Scenario: Author adds\n  Given x", "Author adds"),
    ("Scenario Outline: Many levels\n  Examples:", "Many levels"),
    ("\n- [ ] The migration is additive", "- [ ] The migration is additive"),
    ("x" * 100, "x" * 79 + "…"),
])
def test_ac_name(text, name):
    assert ac_name(text) == name


def test_section_of_file(inputs):
    sections = section_of_file(build_chapters(inputs.criteria, inputs.mapper, inputs.changed))
    assert sections["src/data/api.ts"] == 2 and sections["src/old/Legacy.tsx"] == 5
