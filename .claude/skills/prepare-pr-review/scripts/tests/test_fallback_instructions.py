import re
from pathlib import Path

from fallback_instructions import LIMIT, compose_instructions, main

BASE_FILE = Path(__file__).resolve().parents[2] / "references" / "guide-instructions-base.md"


def test_base_is_short():
    assert len(BASE_FILE.read_text()) <= 900


def test_base_covers_each_instruction():
    text = BASE_FILE.read_text()
    assert "—" not in text
    for phrase in (
        "one chapter per acceptance criterion",
        "Edge cases",
        "Tests",
        "Refactoring and setup",
        "Other changes",
        "exactly one chapter",
        "criterion ids",
    ):
        assert phrase in text


def test_exact_layout():
    out = compose_instructions("BASE\n", [("AC1", "x\n  y"), ("AC2", "z")])
    assert out == "BASE\n\nAcceptance criteria, one chapter each, in this order:\n\nAC1:\nx\n  y\n\nAC2:\nz\n"


def test_short_inputs_keep_exact_text_in_order():
    text = "Scenario: A\n  Given b\n  Then c"
    out = compose_instructions("BASE", [("AC1", text), ("AC2", "second")])
    assert out.startswith("BASE\n\n") and f"AC1:\n{text}\n" in out
    assert out.index("AC1:") < out.index("AC2:")


def test_texts_cut_to_300_first():
    criteria = [(f"AC{i}", "t" * 400) for i in range(1, 7)]
    out = compose_instructions("B", criteria)
    assert len(out) <= LIMIT
    assert "t" * 300 in out and "t" * 301 not in out and "…" not in out


def test_texts_cut_to_150_next():
    criteria = [(f"AC{i}", "t" * 400) for i in range(1, 8)]
    out = compose_instructions("B", criteria)
    assert len(out) <= LIMIT
    assert "t" * 150 in out and "t" * 151 not in out and "…" not in out


def test_texts_cut_to_first_line_next():
    criteria = [(f"AC{i}", "Scenario: " + "a" * 140 + "\n" + "b" * 100) for i in range(1, 11)]
    out = compose_instructions("B", criteria)
    assert len(out) <= LIMIT
    assert "a" * 140 in out and "b" not in out.replace("B", "", 1) and "…" not in out


def test_hard_cut_last():
    criteria = [(f"AC{i}", "x" * 200) for i in range(1, 40)]
    out = compose_instructions("B" * 900, criteria)
    assert len(out) == LIMIT and out.endswith("…") and out.startswith("B" * 900)


def test_main_writes_file(tmp_path, synthetic, capsys):
    assert main(["--artifacts", str(synthetic), "--data-dir", str(tmp_path)]) == 0
    target = tmp_path / "guide-instructions.md"
    text = target.read_text()
    assert len(text) <= 2000 and BASE_FILE.read_text().rstrip("\n") in text
    assert "AC1:\nScenario: Author adds a competency\n  Given the competency list" in text
    assert "AC3:\nScenario: Deleting asks for confirmation" in text
    assert capsys.readouterr().out.strip() == str(target)


def test_main_reports_missing_input(tmp_path, capsys):
    assert main(["--artifacts", str(tmp_path), "--data-dir", str(tmp_path)]) == 1
    assert capsys.readouterr().err


def test_main_backs_up_an_existing_file(tmp_path, synthetic, capsys):
    target = tmp_path / "guide-instructions.md"
    target.write_text("my own instructions")
    assert main(["--artifacts", str(synthetic), "--data-dir", str(tmp_path)]) == 0
    backups = list(tmp_path.glob("guide-instructions.md.bak-*"))
    assert len(backups) == 1
    assert re.fullmatch(r"guide-instructions\.md\.bak-\d{8}-\d{6}", backups[0].name)
    assert backups[0].read_text() == "my own instructions"
    assert target.read_text() != "my own instructions"
    assert capsys.readouterr().out.splitlines() == [f"Backup: {backups[0]}", str(target)]


def test_main_makes_no_backup_without_an_existing_file(tmp_path, synthetic):
    assert main(["--artifacts", str(synthetic), "--data-dir", str(tmp_path)]) == 0
    assert not list(tmp_path.glob("*.bak-*"))
