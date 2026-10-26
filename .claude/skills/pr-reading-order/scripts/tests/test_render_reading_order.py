import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import render_reading_order as r

TICKET = """## Acceptance Criteria

```
Scenario: First thing works
  Given a thing
  When I do it
  Then it works

Scenario: Second thing works
  Given another thing
  Then it also works
```

Scenario: Not an AC because it is outside the fence
"""


def write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text)
    return path


def spec(**overrides):
    base = {
        "title": "Reading order for PR #1",
        "subtitle": "owner/repo PR #1, head abc1234.",
        "threads": [{
            "title": "Thread 1: the main flow",
            "summary": "Data flows from the API to the panel.",
            "steps": [
                {"name": "getThing", "where": "data/api.ts:10-20", "kind": "source",
                 "does": "Fetches the thing.", "blast": 80, "blastWhy": "Every consumer reads it.",
                 "acs": ["First thing works"], "notInAcs": ["Retries once on a 500."]},
                {"name": "api.test.ts", "where": "data/api.test.ts:5-30", "kind": "test",
                 "does": "Pins the request parameters.", "blast": 10},
            ],
        }],
        "elsewhere": [{"ac": "Second thing works", "where": "Panel.tsx:40", "note": "Implemented, untested."}],
        "leftovers": [{"where": "messages.ts:1-30", "does": "Adds strings.", "blast": 5}],
    }
    base.update(overrides)
    return base


@pytest.fixture
def acs(tmp_path):
    return r.load_acs([f"683={write(tmp_path, 't.md', TICKET)}"])


def test_parse_scenarios_reads_only_fenced_blocks_verbatim():
    scenarios = r.parse_scenarios(TICKET)
    assert list(scenarios) == ["First thing works", "Second thing works"]
    assert scenarios["First thing works"] == (
        "Scenario: First thing works\n  Given a thing\n  When I do it\n  Then it works"
    )


def test_parse_scenarios_without_fences_reads_whole_text():
    assert list(r.parse_scenarios("Scenario: A\n  Then b\n")) == ["A"]


def test_load_acs_keeps_ticket_and_order(acs):
    assert [(a.ticket, a.title) for a in acs] == [("683", "First thing works"), ("683", "Second thing works")]


def test_blast_hue_runs_from_green_to_red():
    assert r.blast_hue(0) == 120
    assert r.blast_hue(100) == 0
    assert r.blast_hue(50) == 60


def test_validate_accepts_a_complete_spec(acs):
    r.validate(spec(), acs)


def test_validate_rejects_unknown_ac_and_suggests_close_match(acs):
    bad = spec()
    bad["threads"][0]["steps"][0]["acs"] = ["First thing work"]
    with pytest.raises(SystemExit, match="First thing works"):
        r.validate(bad, acs)


def test_validate_rejects_an_ac_that_is_neither_in_a_thread_nor_elsewhere(acs):
    with pytest.raises(SystemExit, match="Second thing works"):
        r.validate(spec(elsewhere=[]), acs)


def test_validate_rejects_blast_out_of_range(acs):
    bad = spec()
    bad["threads"][0]["steps"][0]["blast"] = 101
    with pytest.raises(SystemExit, match="blast"):
        r.validate(bad, acs)


def test_validate_requires_ticket_prefix_when_titles_collide(tmp_path):
    dup = r.load_acs([f"1={write(tmp_path, 'a.md', TICKET)}", f"2={write(tmp_path, 'b.md', TICKET)}"])
    with pytest.raises(SystemExit, match="ambiguous"):
        r.validate(spec(), dup)
    ok = spec(elsewhere=[{"ac": f"{t}:{title}", "where": "x", "note": "y"}
                         for t in ("1", "2") for title in ("First thing works", "Second thing works")])
    ok["threads"][0]["steps"][0]["acs"] = ["1:First thing works"]
    r.validate(ok, dup)


def test_render_svg_is_well_formed_and_carries_ac_text_verbatim(acs):
    svg = r.render_svg(spec(), acs)
    root = ET.fromstring(svg)
    texts = "\n".join("".join(t.itertext()) for t in root.iter("{http://www.w3.org/2000/svg}text"))
    for line in ["Scenario: First thing works", "  Given a thing", "Scenario: Second thing works"]:
        assert line in texts
    assert "Retries once on a 500." in texts
    assert "getThing" in texts and "messages.ts:1-30" in texts


def test_render_svg_preserves_gherkin_indentation(acs):
    assert 'xml:space="preserve"' in r.render_svg(spec(), acs)


def test_main_writes_svg(tmp_path):
    ticket = write(tmp_path, "t.md", TICKET)
    spec_path = write(tmp_path, "spec.json", json.dumps(spec()))
    out = tmp_path / "out.svg"
    r.main([str(spec_path), "--acs", f"683={ticket}", "--svg", str(out)])
    assert out.read_text().startswith("<svg")


def test_main_prints_a_coverage_summary(tmp_path, capsys):
    ticket = write(tmp_path, "t.md", TICKET)
    spec_path = write(tmp_path, "spec.json", json.dumps(spec()))
    files = write(tmp_path, "files.txt", "src/data/api.ts\nsrc/Panel.tsx\n")
    r.main([str(spec_path), "--acs", f"683={ticket}", "--changed-files", str(files),
            "--svg", str(tmp_path / "o.svg")])
    assert capsys.readouterr().out.splitlines()[-1] == (
        "1 thread; 2 ACs: 1 in threads, 1 elsewhere (0 missing); 2 changed files all named"
    )


def test_long_leftover_location_wraps_instead_of_running_into_its_description(acs):
    where = "a/very/long/path/to/SomeComponent.test.tsx, another/long/path/OtherComponent.test.tsx"
    svg = r.render_svg(spec(leftovers=[{"where": where, "does": "Updates mocks.", "blast": 3}]), acs)
    texts = ["".join(t.itertext()) for t in ET.fromstring(svg).iter("{http://www.w3.org/2000/svg}text")]
    assert where not in texts
    assert " ".join(t for t in texts if "path" in t) == where


def test_validate_rejects_a_does_text_longer_than_one_sentence(acs):
    bad = spec()
    bad["threads"][0]["steps"][0]["does"] = "Fetches the thing. Then it caches it."
    with pytest.raises(SystemExit, match="one sentence"):
        r.validate(bad, acs)


def test_validate_accepts_file_names_inside_one_sentence(acs):
    ok = spec()
    ok["threads"][0]["steps"][0]["does"] = "Reads api.ts and calls getThing() with e.g. two keys."
    r.validate(ok, acs)


def test_validate_rejects_a_changed_file_missing_from_the_drawing(acs):
    with pytest.raises(SystemExit, match="Other.tsx"):
        r.validate(spec(), acs, changed_files=["src/data/api.ts", "src/data/api.test.ts", "src/Panel.tsx",
                                               "src/messages.ts", "src/Other.tsx"])
    r.validate(spec(), acs, changed_files=["src/data/api.ts", "src/data/api.test.ts", "src/Panel.tsx", "src/messages.ts"])


def test_missing_ac_renders_as_not_implemented(acs):
    s = spec(elsewhere=[{"ac": "Second thing works", "where": "Panel.tsx", "note": "Only one message exists.",
                         "missing": True}])
    svg = r.render_svg(s, acs)
    assert 'class="box missing"' in svg
    assert "NOT IMPLEMENTED" in svg


def test_main_checks_changed_files(tmp_path):
    ticket = write(tmp_path, "t.md", TICKET)
    spec_path = write(tmp_path, "spec.json", json.dumps(spec()))
    files = write(tmp_path, "files.txt", "src/data/api.ts\nsrc/Unlisted.tsx\n")
    with pytest.raises(SystemExit, match="Unlisted.tsx"):
        r.main([str(spec_path), "--acs", f"683={ticket}", "--changed-files", str(files),
                "--svg", str(tmp_path / "o.svg")])


def test_pr6_fixture_renders(tmp_path):
    data = Path(__file__).resolve().parents[2] / "testdata"
    out = tmp_path / "pr6.svg"
    r.main([str(data / "pr6-spec.json"), "--acs", f"683={data / 'ticket683.md'}",
            "--changed-files", str(data / "pr6-files.txt"), "--svg", str(out)])
    ET.parse(out)
