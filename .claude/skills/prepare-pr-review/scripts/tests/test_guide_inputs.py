import json
import shutil

import pytest

import guide_inputs
from guide_inputs import (
    Anchor,
    Chapter,
    CodeRef,
    FileEntry,
    PlacementError,
    changed_files,
    check_placement,
    load_chapters,
    load_criteria,
    load_findings,
    load_pr,
    parse_anchor,
)


def test_parse_anchor_single_line():
    assert parse_anchor("src/a.py:40") == Anchor("src/a.py", 40, 40)


def test_parse_anchor_range():
    assert parse_anchor("src/a.py:40-52") == Anchor("src/a.py", 40, 52)


@pytest.mark.parametrize("bad", ["src/a.py", "src/a.py:", "src/a.py:52-40", "src/a.py:x", ":40", "src/a.py:0"])
def test_parse_anchor_rejects(bad):
    with pytest.raises(ValueError):
        parse_anchor(bad)


def test_load_chapters_reads_synthetic(synthetic):
    chapters = load_chapters(synthetic / "chapters.json")
    assert [c.kind for c in chapters] == ["step", "step", "layer"]
    assert chapters[0].code[0] == CodeRef(Anchor("src/pages/CompetencyPage.tsx", 12, 30), "renders the Add button")
    assert chapters[1].original == "check editing works"


def test_step_chapter_requires_do_and_expect(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"chapters": [{"kind": "step", "title": "S", "code": [], "files": []}]}))
    with pytest.raises(ValueError, match="do"):
        load_chapters(p)


def test_layer_chapter_rejects_do(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"chapters": [{"kind": "layer", "title": "L", "do": "x", "code": [], "files": []}]}))
    with pytest.raises(ValueError, match="layer"):
        load_chapters(p)


def test_load_criteria_reads_synthetic(synthetic):
    criteria = load_criteria(synthetic / "criteria.json")
    assert [c.id for c in criteria] == ["AC1", "AC2", "AC3"]
    assert criteria[0].implemented_at[1] == Anchor("src/data/api.ts", 5, 20)
    assert criteria[0].tested_by == ("src/data/api.test.ts::adds a competency",)


def test_load_criteria_rejects_duplicate_ids(tmp_path):
    p = tmp_path / "a.json"
    row = {"id": "AC1", "text": "t", "implemented_at": [], "tested_by": [], "verdict": "Covered"}
    p.write_text(json.dumps({"criteria": [row, row]}))
    with pytest.raises(ValueError, match="AC1"):
        load_criteria(p)


def test_load_findings_reads_synthetic(synthetic):
    verdict, findings = load_findings(synthetic / "findings.json")
    assert verdict.startswith("Ready to merge: no.")
    assert [f.severity for f in findings] == ["Bug", "Nit", "Question"]
    assert findings[1].anchor == Anchor("src/pages/CompetencyPage.tsx", 15, 15)


def test_load_findings_rejects_unknown_severity(tmp_path):
    p = tmp_path / "f.json"
    p.write_text(json.dumps({"verdict": "v", "findings": [{"severity": "Critical", "title": "t", "anchor": "a.py:1", "why": "w"}]}))
    with pytest.raises(ValueError, match="Critical"):
        load_findings(p)


def test_changed_files_keeps_gh_order(synthetic):
    assert changed_files(load_pr(synthetic / "pr.json"))[0] == "src/pages/CompetencyPage.tsx"
    assert len(changed_files(load_pr(synthetic / "pr.json"))) == 5


def test_check_placement_passes_for_synthetic(synthetic):
    check_placement(changed_files(load_pr(synthetic / "pr.json")), load_chapters(synthetic / "chapters.json"))


def test_check_placement_reports_missing_duplicate_unknown():
    ch = lambda *paths: Chapter("layer", "L", None, None, None, (), tuple(FileEntry(p, "s") for p in paths))
    with pytest.raises(PlacementError) as e:
        check_placement(["a.py", "b.py", "c.py"], [ch("a.py", "b.py"), ch("a.py", "z.py")])
    assert (e.value.missing, e.value.duplicated, e.value.unknown) == (["c.py"], ["a.py"], ["z.py"])
    assert "c.py" in str(e.value) and "z.py" in str(e.value)


def test_check_placement_requires_deleted_files():
    ch = Chapter("layer", "L", None, None, None, (), (FileEntry("a.py", "s"),))
    with pytest.raises(PlacementError) as e:
        check_placement(["a.py", "src/old/Legacy.tsx"], [ch])
    assert e.value.missing == ["src/old/Legacy.tsx"]


def _write(tmp_path, obj):
    p = tmp_path / "in.json"
    p.write_text(json.dumps(obj))
    return p


@pytest.mark.parametrize("loader, key", [(load_chapters, "chapters"), (load_criteria, "criteria"), (load_findings, "findings")])
def test_loaders_reject_missing_top_level_key(tmp_path, loader, key):
    with pytest.raises(ValueError, match=key):
        loader(_write(tmp_path, {"verdict": "v"}))


@pytest.mark.parametrize("loader, key", [(load_chapters, "chapters"), (load_criteria, "criteria"), (load_findings, "findings")])
def test_loaders_reject_non_object_row(tmp_path, loader, key):
    with pytest.raises(ValueError, match=rf"{key}\[0\]"):
        loader(_write(tmp_path, {key: ["not an object"], "verdict": "v"}))


@pytest.mark.parametrize("field", ["code", "files"])
@pytest.mark.parametrize("value", [None, "text", ["not an object"]])
def test_load_chapters_rejects_bad_code_and_files(tmp_path, field, value):
    row = {"kind": "layer", "title": "L", "code": [], "files": [], field: value}
    with pytest.raises(ValueError, match=field):
        load_chapters(_write(tmp_path, {"chapters": [row]}))


@pytest.mark.parametrize("field", ["tested_by", "implemented_at"])
@pytest.mark.parametrize("value", ["src/a.py::test", None, [5]])
def test_load_criteria_rejects_non_list_of_strings(tmp_path, field, value):
    row = {"id": "AC1", "text": "t", "implemented_at": [], "tested_by": [], "verdict": "Covered", field: value}
    with pytest.raises(ValueError, match=field):
        load_criteria(_write(tmp_path, {"criteria": [row]}))


def test_load_chapters_rejects_non_string_original(tmp_path):
    row = {"kind": "step", "title": "S", "do": "d", "expect": "e", "original": 5, "code": [], "files": []}
    with pytest.raises(ValueError, match="original"):
        load_chapters(_write(tmp_path, {"chapters": [row]}))


@pytest.mark.parametrize("pr, match", [
    ({}, "files"),
    ({"files": None}, "files"),
    ({"files": ["a.py"]}, r"files\[0\]"),
    ({"files": [{"additions": 1}]}, "path"),
    ({"files": [{"path": 5}]}, "path"),
])
def test_changed_files_rejects_malformed_pr(pr, match):
    with pytest.raises(ValueError, match=match):
        changed_files(pr)


def test_check_cli(tmp_path, synthetic, capsys):
    art = tmp_path / "a"
    shutil.copytree(synthetic, art)
    assert guide_inputs.main(["--check", str(art)]) == 0
    assert capsys.readouterr().out.strip() == "Placement OK: 5 files in 3 chapters."
    data = json.loads((art / "chapters.json").read_text())
    data["chapters"][2]["files"] = []
    (art / "chapters.json").write_text(json.dumps(data))
    assert guide_inputs.main(["--check", str(art)]) == 1
    assert "changed files placed in no chapter" in capsys.readouterr().err


def test_check_cli_reports_missing_file(tmp_path, capsys):
    assert guide_inputs.main(["--check", str(tmp_path)]) == 1
    assert "pr.json" in capsys.readouterr().err
