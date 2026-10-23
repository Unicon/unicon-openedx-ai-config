import json
import shutil

import pytest

import guide_inputs
from guide_inputs import (
    Anchor,
    Background,
    MapperCheckError,
    MapperOutput,
    Piece,
    changed_files,
    check_mapper_output,
    load_criteria,
    load_findings,
    load_mapper_file,
    load_mapper_outputs,
    load_pr,
    main,
    one_line,
    parse_anchor,
)


def test_one_line_collapses_whitespace():
    assert one_line("  a \n\n b\t c  ") == "a b c"


def test_parse_anchor_single_line():
    assert parse_anchor("src/a.py:40") == Anchor("src/a.py", 40, 40)


def test_parse_anchor_range():
    assert parse_anchor("src/a.py:40-52") == Anchor("src/a.py", 40, 52)


@pytest.mark.parametrize("bad", ["src/a.py", "src/a.py:", "src/a.py:52-40", "src/a.py:x", ":40", "src/a.py:0"])
def test_parse_anchor_rejects(bad):
    with pytest.raises(ValueError):
        parse_anchor(bad)


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


def test_load_pr_requires_integer_changed_files(tmp_path, synthetic):
    base = json.loads((synthetic / "pr.json").read_text())
    for bad in ("missing", True, "5", None):
        pr = dict(base)
        if bad == "missing":
            del pr["changedFiles"]
        else:
            pr["changedFiles"] = bad
        p = tmp_path / "pr.json"
        p.write_text(json.dumps(pr))
        with pytest.raises(ValueError, match="changedFiles"):
            load_pr(p)


def test_changed_files_rejects_truncated_file_list(synthetic):
    pr = load_pr(synthetic / "pr.json")
    pr["changedFiles"] = 115
    with pytest.raises(ValueError, match=r"pr\.json.*5.*115"):
        changed_files(pr)


def _write(tmp_path, obj):
    p = tmp_path / "in.json"
    p.write_text(json.dumps(obj))
    return p


@pytest.mark.parametrize("loader, key", [(load_criteria, "criteria"), (load_findings, "findings")])
def test_loaders_reject_missing_top_level_key(tmp_path, loader, key):
    with pytest.raises(ValueError, match=key):
        loader(_write(tmp_path, {"verdict": "v"}))


@pytest.mark.parametrize("loader, key", [(load_criteria, "criteria"), (load_findings, "findings")])
def test_loaders_reject_non_object_row(tmp_path, loader, key):
    with pytest.raises(ValueError, match=rf"{key}\[0\]"):
        loader(_write(tmp_path, {key: ["not an object"], "verdict": "v"}))


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


def test_load_criteria_reads_synthetic(synthetic):
    criteria, backgrounds = load_criteria(synthetic / "criteria.json")
    assert [c.id for c in criteria] == ["AC1", "AC2", "AC3"]
    assert criteria[1].text.splitlines()[0] == "Scenario: Author changes the level"
    assert criteria[2].verdict is None
    assert backgrounds == [Background("openedx/frontend-app-authoring#99", "Background:\n  Given an author is logged in")]


def test_criteria_crlf_becomes_lf(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"criteria": [{"id": "AC1", "text": "Scenario: X\r\n  Given y  \r\n", "source": "s", "verdict": None, "tested_by": []}]}))
    assert load_criteria(p)[0][0].text == "Scenario: X\n  Given y  \n"


@pytest.mark.parametrize("row,match", [
    ({"id": "AC0", "text": "t", "source": "s", "verdict": None, "tested_by": []}, "id"),
    ({"id": "AC1", "text": "  ", "source": "s", "verdict": None, "tested_by": []}, "text"),
    ({"id": "AC1", "text": "t", "source": "s", "verdict": 3, "tested_by": []}, "verdict"),
])
def test_load_criteria_rejects(tmp_path, row, match):
    p = tmp_path / "c.json"; p.write_text(json.dumps({"criteria": [row]}))
    with pytest.raises(ValueError, match=match):
        load_criteria(p)


def test_load_criteria_rejects_duplicate_ids(tmp_path):
    p = tmp_path / "a.json"
    row = {"id": "AC1", "text": "t", "source": "s", "verdict": "Covered", "tested_by": []}
    p.write_text(json.dumps({"criteria": [row, row]}))
    with pytest.raises(ValueError, match="AC1"):
        load_criteria(p)


@pytest.mark.parametrize("value", ["src/a.py::test", None, [5]])
def test_load_criteria_rejects_non_list_of_strings(tmp_path, value):
    row = {"id": "AC1", "text": "t", "source": "s", "verdict": "Covered", "tested_by": value}
    with pytest.raises(ValueError, match="tested_by"):
        load_criteria(_write(tmp_path, {"criteria": [row]}))


def test_load_mapper_file_reads_synthetic(synthetic):
    m = load_mapper_file(synthetic / "pieces-1.json")
    assert len(m.files) == 5 and len(m.pieces) == 8
    assert m.pieces[5] == Piece(Anchor("src/data/api.test.ts", 1, 40), ("AC1", "AC2"), "test", "covers the POST and PATCH calls", ())


@pytest.mark.parametrize("change,match", [
    ({"kind": "rewrite"}, "kind"), ({"key_for": ["AC3"]}, "key_for"), ({"purpose": ""}, "purpose"), ({"acs": "AC1"}, "acs"),
])
def test_load_mapper_file_rejects(tmp_path, synthetic, change, match):
    data = json.loads((synthetic / "pieces-1.json").read_text()); data["pieces"][0].update(change)
    p = tmp_path / "pieces-1.json"; p.write_text(json.dumps(data))
    with pytest.raises(ValueError, match=match):
        load_mapper_file(p)


def test_load_mapper_outputs_merges_batches_in_order(tmp_path, synthetic):
    data = json.loads((synthetic / "pieces-1.json").read_text())
    first = {"files": data["files"][:2], "pieces": data["pieces"][:5]}
    second = {"files": data["files"][2:], "pieces": data["pieces"][5:]}
    (tmp_path / "pieces-10.json").write_text(json.dumps(second)); (tmp_path / "pieces-2.json").write_text(json.dumps(first))
    merged = load_mapper_outputs(tmp_path)
    assert [f.path for f in merged.files] == [f["path"] for f in data["files"]]


def test_load_mapper_outputs_rejects_duplicate_summary(tmp_path, synthetic):
    shutil.copy(synthetic / "pieces-1.json", tmp_path / "pieces-1.json"); shutil.copy(synthetic / "pieces-1.json", tmp_path / "pieces-2.json")
    with pytest.raises(ValueError, match="src/pages/CompetencyPage.tsx"):
        load_mapper_outputs(tmp_path)


def test_load_mapper_outputs_names_the_file_of_a_bad_piece(tmp_path, synthetic):
    data = json.loads((synthetic / "pieces-1.json").read_text())
    (tmp_path / "pieces-1.json").write_text(json.dumps({"files": data["files"][:2], "pieces": data["pieces"][:5]}))
    bad = {"files": data["files"][2:], "pieces": [dict(data["pieces"][5], kind="rewrite")]}
    (tmp_path / "pieces-2.json").write_text(json.dumps(bad))
    with pytest.raises(ValueError, match=r"pieces-2\.json piece 1: kind"):
        load_mapper_outputs(tmp_path)


def test_load_mapper_outputs_rejects_no_files(tmp_path):
    with pytest.raises(ValueError, match="pieces-"):
        load_mapper_outputs(tmp_path)


def test_check_passes_for_synthetic(inputs):
    check_mapper_output(inputs.changed, inputs.mapper, inputs.criteria)


def test_check_reports_every_problem(inputs):
    pieces = tuple(p for p in inputs.mapper.pieces if p.anchor.path != "src/old/Legacy.tsx") + (
        Piece(Anchor("z.py", 1, 1), ("AC9",), "implements", "x", ()),)
    files = tuple(f for f in inputs.mapper.files if f.path != "migrations/0002_add_level.py")
    with pytest.raises(MapperCheckError) as e:
        check_mapper_output(inputs.changed, MapperOutput(files, pieces), inputs.criteria)
    err = e.value
    assert (err.missing_pieces, err.missing_summaries, err.unknown_files, err.unknown_acs) == (
        ["src/old/Legacy.tsx"], ["migrations/0002_add_level.py"], ["z.py"], ["AC9"])
    for name in ("src/old/Legacy.tsx", "migrations/0002_add_level.py", "z.py", "AC9"):
        assert name in str(err)


def test_check_cli(tmp_path, synthetic, capsys):
    art = tmp_path / "a"; shutil.copytree(synthetic, art)
    assert main(["--check", str(art)]) == 0
    assert "Mapper output OK: 5 files, 8 pieces." in capsys.readouterr().out
    (art / "pieces-1.json").unlink()
    assert main(["--check", str(art)]) == 1


def test_check_batch_cli(tmp_path, synthetic):
    art = tmp_path / "a"; shutil.copytree(synthetic, art)
    (art / "batch-1.json").write_text(json.dumps(["src/pages/CompetencyPage.tsx", "src/data/api.ts", "src/data/api.test.ts", "migrations/0002_add_level.py", "src/old/Legacy.tsx"]))
    assert main(["--check-batch", str(art), "1"]) == 0
    (art / "batch-1.json").write_text(json.dumps(["src/pages/CompetencyPage.tsx"]))
    assert main(["--check-batch", str(art), "1"]) == 1


def test_check_cli_reports_missing_file(tmp_path, capsys):
    assert main(["--check", str(tmp_path)]) == 1
    assert "pr.json" in capsys.readouterr().err


def test_check_cli_usage_error(capsys):
    assert main(["--check"]) == 2
    assert main(["--check-batch", "d", "x"]) == 2
