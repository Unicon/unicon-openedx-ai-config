"""Tests for the chapter text and change map renderers."""
import pytest

from guide_inputs import Anchor, Chapter, Finding, FileEntry
from guide_mapping import assign_findings, criteria_by_chapter, find_gaps
from guide_render import (
    code_ref,
    one_line,
    render_before_you_start,
    render_change_map,
    render_file_summary,
    render_finding,
    render_overview,
)


def test_one_line_collapses_whitespace():
    assert one_line("  a \n\n b\t c  ") == "a b c"


def test_code_ref_range():
    assert code_ref(Anchor("src/a.py", 40, 52)) == "`src/a.py` L40-L52"


def test_code_ref_single():
    assert code_ref(Anchor("src/a.py", 15, 15)) == "`src/a.py` L15"


@pytest.mark.parametrize("sev,kind", [("Bug", "WARNING"), ("Gap", "WARNING"), ("Question", "IMPORTANT"), ("Suggestion", "NOTE"), ("Nit", "NOTE")])
def test_finding_callout_kind(sev, kind):
    assert render_finding(Finding(sev, "T", Anchor("a.py", 1, 1), "W")).startswith(f"> [!{kind}] {sev}: T. W ")


def test_finding_exact_text():
    f = Finding("Bug", "Level is sent as a string", Anchor("src/data/api.ts", 22, 30), "The API expects an integer, so the PATCH returns 400.")
    assert render_finding(f) == (
        "> [!WARNING] Bug: Level is sent as a string. The API expects an integer, so the PATCH returns 400. `src/data/api.ts` L22-L30"
    )


def test_finding_title_with_period_gets_no_second_period():
    line = render_finding(Finding("Nit", "Already ends.", Anchor("a.py", 1, 1), "W"))
    assert line.startswith("> [!NOTE] Nit: Already ends. W ")


def test_finding_collapses_newlines():
    line = render_finding(Finding("Bug", "Two\nlines", Anchor("a.py", 1, 1), "Why\n> quoted"))
    assert "\n" not in line and "Two lines" in line


def test_step_overview_order(inputs):
    crit = criteria_by_chapter(inputs.criteria, inputs.chapters)
    text = render_overview(inputs.chapters[0], criteria=crit[0], findings=inputs.findings[:2], first_section_by_path={"src/pages/CompetencyPage.tsx": 2, "src/data/api.ts": 2}, this_section=2)
    marks = ["**Do:**", "**Expect:**", "**Covers:**", "> [!WARNING] Bug:", "> [!NOTE] Nit:", "**Code, in the order it runs:**"]
    assert [text.index(m) for m in marks] == sorted(text.index(m) for m in marks)
    assert text.count('AC1 "An author can add a competency"') == 1
    assert "- `src/pages/CompetencyPage.tsx` L12-L30: renders the Add button." in text
    assert "Sharpened" not in text
    assert "First read in" not in text


def test_step_overview_exact_blocks(inputs):
    text = render_overview(inputs.chapters[0], criteria=inputs.criteria[:1], findings=[], first_section_by_path={}, this_section=1)
    assert "**Do:** Open Studio > Competencies and click Add.\n\n**Expect:** The new competency appears in the list." in text
    assert text.split("\n\n")[:3] == [
        "**Do:** Open Studio > Competencies and click Add.",
        "**Expect:** The new competency appears in the list.",
        '**Covers:** AC1 "An author can add a competency".',
    ]


def test_sharpened_step_and_first_read(inputs):
    text = render_overview(inputs.chapters[1], criteria=[], findings=[], first_section_by_path={"src/data/api.ts": 2, "src/pages/CompetencyPage.tsx": 2}, this_section=3)
    assert "\n\n**Expect:** The list shows level 3.\n\nSharpened from the PR. Author's wording: \"check editing works\"" in text
    assert "patches the level. First read in chapter 2." in text
    assert "**Covers:**" not in text


def test_layer_overview_without_code_is_empty_of_step_lines(inputs):
    text = render_overview(inputs.chapters[2], criteria=[], findings=[], first_section_by_path={}, this_section=4)
    assert text == ""


def test_layer_overview_with_code_and_findings():
    ch = Chapter("layer", "L", None, None, None, (), ())
    finding = Finding("Nit", "T", Anchor("a.py", 1, 1), "W")
    text = render_overview(ch, criteria=[], findings=[finding], first_section_by_path={}, this_section=1)
    assert text == "> [!NOTE] Nit: T. W `a.py` L1"
    assert "**Do:**" not in text


def test_file_summary_with_tags(inputs):
    assert render_file_summary(FileEntry("src/data/api.ts", "Adds the create and patch calls."), inputs.criteria) == "Adds the create and patch calls. AC1 L5-L20, AC2 L22-L30."


def test_file_summary_without_tags(inputs):
    assert render_file_summary(FileEntry("src/data/api.test.ts", "Tests\nboth calls."), inputs.criteria) == "Tests both calls."


def test_before_you_start_lists_outside_findings(inputs):
    gaps = find_gaps(inputs.criteria, inputs.changed)
    outside = assign_findings(inputs.findings, inputs.chapters, inputs.changed).outside
    text = render_before_you_start(verdict=inputs.verdict, gaps=gaps, outside=outside, change_map_note=None)
    assert text.startswith("**Review verdict:** Ready to merge: no.")
    assert '- AC3 "Deleting a competency asks for confirmation"' in text
    assert "- `migrations/0002_add_level.py`" in text
    assert "> [!IMPORTANT] Question: Caller still passes the old prop." in text


def test_before_you_start_none_and_note():
    from guide_mapping import Gaps

    text = render_before_you_start(verdict="V", gaps=Gaps([], []), outside=[], change_map_note="Map at x.mmd")
    assert text == (
        "**Review verdict:** V\n\n"
        "**Acceptance criteria with no code in this PR:**\n- None.\n\n"
        "**Changed files no acceptance criterion points at:**\n- None.\n\n"
        "Map at x.mmd"
    )
    assert "outside the changed files" not in text


def test_change_map_structure(inputs):
    src = render_change_map(inputs.chapters)
    assert src.splitlines()[0] == "flowchart LR"
    assert "click " not in src
    for title in [c.title for c in inputs.chapters]:
        assert f'"{title}"' in src
    for path in inputs.changed:
        assert f'"{path}"' in src
    assert src.count(" --> ") == 7


def test_change_map_escapes_quotes():
    ch = Chapter("layer", 'Say "hi"', None, None, None, (), (FileEntry("a.py", "s"),))
    assert '"Say #quot;hi#quot;"' in render_change_map([ch])
