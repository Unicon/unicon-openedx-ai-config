import json
import shutil

import pytest

from compose_guide import (
    canonical_pr_url,
    compose,
    main,
    make_guide_id,
    repo_key_from_pr_url,
    version_warning,
)
from guide_inputs import changed_files, load_pr

BASE = "https://github.com/openedx/frontend-app-authoring/pull/123"


@pytest.mark.parametrize("url", [BASE, BASE + "/", BASE + "/files", BASE + "#discussion_r1", "http://github.com/openedx/frontend-app-authoring/pull/123"])
def test_repo_key_from_url_variants(url):
    assert repo_key_from_pr_url(url) == "github.com__openedx__frontend-app-authoring"


def test_canonical_pr_url():
    assert canonical_pr_url(BASE + "/files") == BASE
    with pytest.raises(ValueError):
        canonical_pr_url("https://github.com/openedx/x/issues/5")


def test_make_guide_id():
    assert make_guide_id("PR #123: Add a Competency!", 1761200000000) == "1761200000000-pr-123-add-a-competency"
    long_id = make_guide_id("x " * 100, 1)
    assert len(long_id.split("-", 1)[1]) <= 60 and not long_id.endswith("-")


def test_version_warning():
    assert version_warning("plannotator 0.28.27") is None
    assert "0.29.0" in version_warning("plannotator 0.29.0") and "0.28.27" in version_warning("plannotator 0.29.0")
    assert "not found" in version_warning(None)


def test_compose_end_to_end(tmp_path, synthetic):
    art = tmp_path / "art"
    shutil.copytree(synthetic, art)
    res = compose(art, data_dir=tmp_path / "pn", now_ms=1761200000000, prepared_at="2026-10-23 14:05", version_output="plannotator 0.28.27")
    env = json.loads(res.guide_path.read_text())
    assert res.guide_path.parent == tmp_path / "pn" / "guides" / "github.com__openedx__frontend-app-authoring"
    assert env["version"] == 1 and env["label"] == "PR #123 prepared 2026-10-23 14:05" and env["headSha"] == "abc123"
    assert env["prUrl"] == BASE and env["reviewed"] == [False] * len(env["guide"]["sections"])
    placed = [d["file"] for s in env["guide"]["sections"] for d in s["diffs"]]
    assert sorted(placed) == sorted(changed_files(load_pr(art / "pr.json")))
    assert (art / "change-map.mmd").read_text().startswith("flowchart LR")
    assert res.warnings == []
    assert not list(res.guide_path.parent.glob("*.tmp"))
    first = env["guide"]["sections"][0]
    assert first["title"] == "Before you start" and first["diffs"] == []
    assert "overview" not in env["guide"]
    assert f"Change map: {(art / 'change-map.mmd').resolve()}" in first["overview"]
    sections = env["guide"]["sections"]
    assert [s["title"] for s in sections] == [
        "Before you start",
        "AC1: Author adds a competency",
        "AC2: Author changes the level",
        "AC3: Deleting asks for confirmation",
        "Refactoring and setup",
    ]
    assert len(placed) == len(set(placed))
    assert sections[2]["diffs"] == [] and sections[3]["diffs"] == []
    assert len(env["reviewed"]) == 5
    assert "(key piece for AC1)" in sections[1]["overview"]
    api = next(d for s in sections for d in s["diffs"] if d["file"] == "src/data/api.ts")
    assert api["summary"].endswith("AC1, AC2. 1 finding.")
    assert env["guide"]["intent"] == (
        "Add competency levels. Prepared on 2026-10-23 14:05: 3 acceptance criteria, 4 chapters, 3 findings."
    )
    assert res.change_map_path == (art / "change-map.mmd").resolve()
    assert json.loads((art / "guide-envelope.json").read_text()) == env
    assert env["title"] == "PR #123: Add competency levels"
    assert env["savedAt"] == 1761200000000


def test_compose_reports_version_warning(tmp_path, synthetic):
    art = tmp_path / "art"
    shutil.copytree(synthetic, art)
    res = compose(art, data_dir=tmp_path / "pn", now_ms=1, prepared_at="2026-10-23 14:05", version_output=None)
    assert len(res.warnings) == 1 and "not found" in res.warnings[0]


def test_main_writes_guide_and_prints_paths(tmp_path, synthetic, capsys):
    art = tmp_path / "art"
    shutil.copytree(synthetic, art)
    assert main(["--artifacts", str(art), "--data-dir", str(tmp_path / "pn")]) == 0
    out = capsys.readouterr().out
    assert str(tmp_path / "pn" / "guides") in out and "change-map.mmd" in out


def test_main_fails_when_a_file_has_no_piece(tmp_path, synthetic, capsys):
    art = tmp_path / "art"
    shutil.copytree(synthetic, art)
    data = json.loads((art / "pieces-1.json").read_text())
    data["pieces"] = [p for p in data["pieces"] if not p["anchor"].startswith("src/old/Legacy.tsx")]
    (art / "pieces-1.json").write_text(json.dumps(data))
    assert main(["--artifacts", str(art), "--data-dir", str(tmp_path / "pn")]) == 1
    assert "src/old/Legacy.tsx" in capsys.readouterr().err


@pytest.mark.parametrize("field", ["url", "number", "title", "headRefOid", "changedFiles"])
@pytest.mark.parametrize("corrupt", ["missing", "wrong_type"])
def test_main_fails_on_malformed_pr_field(tmp_path, synthetic, capsys, field, corrupt):
    art = tmp_path / "art"
    shutil.copytree(synthetic, art)
    pr = json.loads((art / "pr.json").read_text())
    if corrupt == "missing":
        del pr[field]
    else:
        pr[field] = ["not", "valid"]
    (art / "pr.json").write_text(json.dumps(pr))
    assert main(["--artifacts", str(art), "--data-dir", str(tmp_path / "pn")]) == 1
    err = capsys.readouterr().err
    assert "pr.json" in err and field in err


def test_main_fails_on_bool_pr_number(tmp_path, synthetic, capsys):
    art = tmp_path / "art"
    shutil.copytree(synthetic, art)
    pr = json.loads((art / "pr.json").read_text())
    pr["number"] = True
    (art / "pr.json").write_text(json.dumps(pr))
    assert main(["--artifacts", str(art), "--data-dir", str(tmp_path / "pn")]) == 1
    assert "number" in capsys.readouterr().err
