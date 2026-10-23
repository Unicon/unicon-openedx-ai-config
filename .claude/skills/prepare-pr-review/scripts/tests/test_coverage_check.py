import hashlib
import json

from coverage_check import main, progress_key, record_name, unviewed_files
from guide_inputs import changed_files, load_pr

PR_URL = "https://github.com/openedx/frontend-app-authoring/pull/123"


def test_progress_key_matches_plannotator():
    expected = hashlib.sha256(b'["pr","https://github.com/o/r/pull/1","layer"]').hexdigest()
    assert progress_key("https://github.com/o/r/pull/1") == expected


def test_record_name():
    assert record_name("a.py") == hashlib.sha256(b"a.py").hexdigest() + ".json"


def test_record_name_hashes_non_ascii_path_as_utf8():
    assert record_name("é.py") == hashlib.sha256("é.py".encode("utf-8")).hexdigest() + ".json"


def write_record(d, path, viewed, stored_path=None):
    d.mkdir(parents=True, exist_ok=True)
    (d / record_name(path)).write_text(json.dumps({"v": 1, "path": stored_path or path, "fingerprint": "f", "viewed": viewed, "suppressed": False}))


def test_unviewed_files(tmp_path):
    write_record(tmp_path, "a.py", True)
    write_record(tmp_path, "b.py", False)
    assert unviewed_files(["a.py", "b.py", "c.py"], tmp_path) == ["b.py", "c.py"]


def test_ignores_record_for_other_path(tmp_path):
    write_record(tmp_path, "a.py", True, stored_path="x.py")
    assert unviewed_files(["a.py"], tmp_path) == ["a.py"]


def test_ignores_unreadable_or_wrong_version_record(tmp_path):
    (tmp_path / record_name("a.py")).write_text("not json")
    (tmp_path / record_name("b.py")).write_text(json.dumps({"v": 2, "path": "b.py", "viewed": True}))
    (tmp_path / record_name("c.py")).write_text(json.dumps(["c.py"]))
    assert unviewed_files(["a.py", "b.py", "c.py"], tmp_path) == ["a.py", "b.py", "c.py"]


def test_main_missing_progress(tmp_path, synthetic, capsys):
    assert main(["--artifacts", str(synthetic), "--data-dir", str(tmp_path)]) == 2
    assert "No review progress found" in capsys.readouterr().err


def test_main_all_viewed(tmp_path, synthetic, capsys):
    d = tmp_path / "review-progress" / progress_key(PR_URL)
    for p in changed_files(load_pr(synthetic / "pr.json")):
        write_record(d, p, True)
    assert main(["--artifacts", str(synthetic), "--data-dir", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "All 5 changed files are marked viewed." in out
    assert "A file changed after you marked it still counts as viewed here." in out


def test_main_lists_unviewed_files(tmp_path, synthetic, capsys):
    d = tmp_path / "review-progress" / progress_key(PR_URL)
    files = changed_files(load_pr(synthetic / "pr.json"))
    for p in files[:3]:
        write_record(d, p, True)
    assert main(["--artifacts", str(synthetic), "--data-dir", str(tmp_path)]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "Not marked viewed (2 of 5):"
    assert lines[1:3] == [f"- {files[3]}", f"- {files[4]}"]
    assert lines[3] == "A file changed after you marked it still counts as viewed here."


def test_main_uses_canonical_url_for_the_key(tmp_path, synthetic, capsys):
    pr = json.loads((synthetic / "pr.json").read_text())
    pr["url"] = PR_URL + "/files"
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "artifacts" / "pr.json").write_text(json.dumps(pr))
    d = tmp_path / "review-progress" / progress_key(PR_URL)
    for p in changed_files(pr):
        write_record(d, p, True)
    assert main(["--artifacts", str(tmp_path / "artifacts"), "--data-dir", str(tmp_path)]) == 0
    assert "All 5 changed files" in capsys.readouterr().out


def test_main_invalid_pr_json(tmp_path, capsys):
    (tmp_path / "pr.json").write_text("[]")
    assert main(["--artifacts", str(tmp_path), "--data-dir", str(tmp_path)]) == 1
    assert "pr.json" in capsys.readouterr().err
