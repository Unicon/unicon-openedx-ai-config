"""Tests for the chapter text, file summary, opening section, and change map renderers."""
from types import SimpleNamespace

import pytest

from guide_inputs import Anchor, Finding
from guide_mapping import (
    build_chapters,
    key_pieces,
    place_findings,
    section_of_file,
)
from guide_render import (
    ac_block,
    lines,
    piece_label,
    render_before_you_start,
    render_change_map,
    render_file_summary,
    render_overview,
)

ZWSP = "\u200b"


@pytest.fixture
def ctx(inputs):
    chapters = build_chapters(inputs.criteria, inputs.mapper, inputs.changed)
    keys = key_pieces(inputs.criteria, inputs.mapper, inputs.changed)
    placed = place_findings(inputs.findings, inputs.changed)
    criteria_by_id = {c.id: c for c in inputs.criteria}
    pieces_by_path = {}
    ordered = sorted(inputs.mapper.pieces, key=lambda p: (inputs.changed.index(p.anchor.path), p.anchor.start, p.anchor.end))
    for piece in ordered:
        pieces_by_path.setdefault(piece.anchor.path, []).append(piece)
    sections = section_of_file(chapters)
    titles_by_section = {i + 2: chapter.title for i, chapter in enumerate(chapters)}

    def render(i):
        return render_overview(
            chapters[i],
            section=i + 2,
            criteria_by_id=criteria_by_id,
            keys=keys,
            pieces_by_path=pieces_by_path,
            findings_by_path=placed.by_path,
            sections=sections,
            titles_by_section=titles_by_section,
        )

    return SimpleNamespace(
        chapters=chapters, keys=keys, placed=placed, criteria_by_id=criteria_by_id,
        pieces_by_path=pieces_by_path, sections=sections, titles_by_section=titles_by_section, render=render,
    )


def test_lines_range_and_single():
    assert lines(Anchor("a.py", 5, 20)) == "L5-L20"
    assert lines(Anchor("a.py", 15, 15)) == "L15"


def test_piece_label(inputs):
    pieces = inputs.mapper.pieces
    assert piece_label(pieces[0]) == "AC1"
    assert piece_label(pieces[4]) == "AC2 edge case"
    assert piece_label(pieces[5]) == "AC1, AC2 test"
    assert piece_label(pieces[6]) == "migration"


def test_ac1_chapter_overview(ctx):
    text = ctx.render(0)
    assert text.startswith("Review verdict: Covered.\n\n### src/pages/CompetencyPage.tsx\n")
    assert "- L12-L30 AC1: renders the Add button (key piece for AC1)\n```\nScenario: Author adds a competency\n" in text
    assert "- L40-L44 AC2: opens the edit form" in text
    assert "- L22-L30 AC2: patches the level (key piece for AC2)\n```\nScenario: Author changes the level\n" in text
    assert "- L22-L30 Bug: Level is sent as a string. The API expects an integer, so the PATCH returns 400." in text
    assert "> [!" not in text and "Also in this chapter" not in text


def test_notes_interleave_by_line(ctx):
    text = ctx.render(0)
    api = text[text.index("### src/data/api.ts"):text.index("### src/data/api.test.ts")]
    marks = ["L5-L20 AC1", "L22-L30 AC2: patches", "L22-L30 Bug", "L31-L35 AC2 edge case"]
    assert [api.index(m) for m in marks] == sorted(api.index(m) for m in marks)
    assert text.index("### src/pages/CompetencyPage.tsx") < text.index("### src/data/api.ts") < text.index("### src/data/api.test.ts")


def test_also_section_lists_shared_piece(ctx):
    text = ctx.render(1)
    assert text.startswith("Review verdict: Implemented, untested.\n\n```\nScenario: Author changes the level\n")
    assert "### Also in this chapter, diff shown in chapter 2: AC1: Author adds a competency\n" in text
    assert "- src/data/api.ts L22-L30 AC2: patches the level (key piece, 1 finding)" in text
    assert "- src/data/api.test.ts L1-L40 AC1, AC2 test: covers the POST and PATCH calls" in text
    assert text.count("Scenario: Author changes the level") == 1


def test_ac_without_code(ctx):
    assert ctx.render(2) == "No code in this PR implements this AC.\n\n```\nScenario: Deleting asks for confirmation\n  When the author deletes a competency\n  Then a confirmation dialog appears\n```"


def test_purpose_chapter(ctx):
    text = ctx.render(3)
    assert text == "### migrations/0002_add_level.py\n- L1-L20 migration: adds the level column\n\n### src/old/Legacy.tsx\n- L1 removal: drops the old page"


def test_ac_block_keeps_text_and_fence():
    text = "Scenario: X\n  Given `code`  \n```js\nThen y"
    block = ac_block(text)
    assert block.splitlines()[0] == "```" and block.splitlines()[-1] == "```"
    assert block.splitlines()[1:-1] == ["Scenario: X", "  Given `code`  ", ZWSP + "```js", "Then y"]


def test_ac_block_guards_indented_fence():
    assert ac_block("a\n  ```\nb").splitlines()[2] == ZWSP + "  ```"


def test_finding_text_is_one_line_and_title_period_is_not_doubled(ctx):
    findings = {"migrations/0002_add_level.py": (
        Finding("Nit", "Already ends.", Anchor("migrations/0002_add_level.py", 1, 1), "Why\nnow"),)}
    text = render_overview(
        ctx.chapters[3], section=5, criteria_by_id=ctx.criteria_by_id, keys=ctx.keys,
        pieces_by_path=ctx.pieces_by_path, findings_by_path=findings, sections=ctx.sections,
        titles_by_section=ctx.titles_by_section)
    assert "- L1 Nit: Already ends. Why now" in text


@pytest.mark.parametrize("title", ["Why is this null?", "Remove this!", "Done."])
def test_finding_text_adds_no_period_after_closing_punctuation(ctx, title):
    findings = {"migrations/0002_add_level.py": (
        Finding("Question", title, Anchor("migrations/0002_add_level.py", 1, 1), "Because."),)}
    text = render_overview(
        ctx.chapters[3], section=5, criteria_by_id=ctx.criteria_by_id, keys=ctx.keys,
        pieces_by_path=ctx.pieces_by_path, findings_by_path=findings, sections=ctx.sections,
        titles_by_section=ctx.titles_by_section)
    assert f"- L1 Question: {title} Because." in text


def test_file_summary_adds_no_period_after_closing_punctuation(ctx):
    assert render_file_summary("Does it work?", "src/old/Legacy.tsx", ctx.pieces_by_path, 0) == "Does it work?"
    assert render_file_summary("Drops it!", "src/old/Legacy.tsx", ctx.pieces_by_path, 1) == "Drops it! 1 finding."


def test_file_summary(ctx):
    assert render_file_summary("Adds the create and patch calls.", "src/data/api.ts", ctx.pieces_by_path, 1) == "Adds the create and patch calls. AC1, AC2. 1 finding."
    assert render_file_summary("Deletes the old page", "src/old/Legacy.tsx", ctx.pieces_by_path, 0) == "Deletes the old page."
    assert render_file_summary("Tests both calls.", "src/data/api.test.ts", ctx.pieces_by_path, 2) == "Tests both calls. AC1, AC2. 2 findings."


def test_before_you_start(ctx, inputs):
    text = render_before_you_start(verdict=inputs.verdict, backgrounds=inputs.backgrounds, gaps=[inputs.criteria[2]], outside=list(ctx.placed.outside), change_map_note=None)
    assert text.startswith("**Review verdict:** Ready to merge: no.")
    assert "Background from openedx/frontend-app-authoring#99:\n```\nBackground:\n  Given an author is logged in\n```" in text
    assert "**Acceptance criteria with no code in this PR:**\n- AC3: Deleting asks for confirmation" in text
    assert "**Findings on files this PR does not change:**\n- src/unchanged/Caller.tsx L8 Question: Caller still passes the old prop." in text


def test_before_you_start_empty_and_note():
    text = render_before_you_start(verdict="Ok.", backgrounds=[], gaps=[], outside=[], change_map_note="See the map.")
    assert text == "**Review verdict:** Ok.\n\n**Acceptance criteria with no code in this PR:**\n- None.\n\nSee the map."


def test_change_map(ctx):
    src = render_change_map(ctx.chapters)
    assert src.splitlines()[0] == "flowchart LR" and "click " not in src
    assert src.count(" --> ") == 8
    assert 'c3["Refactoring and setup"]' in src
