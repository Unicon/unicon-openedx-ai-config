import json
from types import SimpleNamespace

import pytest

from fetch_pr import fetch_pr, main

URL = "https://github.com/openedx/frontend-app-learning/pull/1885"
VIEW_FIELDS = (
    "url,number,title,body,headRefOid,baseRefOid,headRepository,files,changedFiles,closingIssuesReferences"
)


def _files(count):
    return [{"path": f"src/f{i}.ts", "additions": i, "deletions": 0} for i in range(count)]


def _paginated(count):
    """gh --paginate with --jq prints one JSON object per line, across all pages."""
    return "".join(json.dumps(row) + "\n" for row in _files(count))


class FakeRun:
    """Stands in for subprocess.run; answers ``gh pr view`` and ``gh api`` and records the commands."""

    def __init__(self, view, api_stdout="", returncode=0):
        self.view, self.api_stdout, self.returncode = view, api_stdout, returncode
        self.calls = []

    def __call__(self, cmd, **kwargs):
        self.calls.append(cmd)
        out = json.dumps(self.view) if cmd[1] == "pr" else self.api_stdout
        return SimpleNamespace(returncode=self.returncode, stdout=out, stderr="boom")


def _view(listed, total):
    return {"url": URL, "number": 1885, "title": "t", "headRefOid": "abc", "files": _files(listed), "changedFiles": total}


def test_short_path_keeps_gh_files_and_skips_api():
    run = FakeRun(_view(100, 100))
    pr = fetch_pr(URL + "/files", run=run)
    assert len(pr["files"]) == 100 and pr["changedFiles"] == 100
    assert run.calls == [["gh", "pr", "view", URL, "--json", VIEW_FIELDS]]


def test_paginated_path_replaces_truncated_files():
    run = FakeRun(_view(100, 115), api_stdout=_paginated(115))
    pr = fetch_pr(URL, run=run)
    assert pr["files"] == _files(115) and pr["changedFiles"] == 115
    api = run.calls[1]
    assert api[:3] == ["gh", "api", "--paginate"]
    assert "repos/openedx/frontend-app-learning/pulls/1885/files" in api
    assert api[api.index("--jq") + 1] == ".[] | {path: .filename, additions, deletions}"


def test_paginated_output_tolerates_blank_lines():
    run = FakeRun(_view(100, 101), api_stdout="\n" + _paginated(101) + "\n")
    assert len(fetch_pr(URL, run=run)["files"]) == 101


def test_still_short_after_paging_is_an_error():
    run = FakeRun(_view(100, 3001), api_stdout=_paginated(3000))
    with pytest.raises(ValueError, match="3000.*3001"):
        fetch_pr(URL, run=run)


def test_gh_failure_is_reported():
    with pytest.raises(RuntimeError, match="boom"):
        fetch_pr(URL, run=FakeRun(_view(1, 1), returncode=1))


def test_rejects_non_pr_url():
    with pytest.raises(ValueError, match="pull request URL"):
        fetch_pr("https://example.com/x", run=FakeRun(_view(1, 1)))


def test_main_writes_out_file(tmp_path, monkeypatch, capsys):
    import fetch_pr as module

    monkeypatch.setattr(module.subprocess, "run", FakeRun(_view(2, 2)))
    out = tmp_path / "nested" / "pr.json"
    assert main([URL, "--out", str(out)]) == 0
    assert json.loads(out.read_text())["changedFiles"] == 2
    assert capsys.readouterr().out.strip() == str(out)


def test_main_reports_errors(tmp_path, capsys):
    assert main(["https://example.com/x", "--out", str(tmp_path / "pr.json")]) == 1
    assert "pull request URL" in capsys.readouterr().err
    assert not (tmp_path / "pr.json").exists()
