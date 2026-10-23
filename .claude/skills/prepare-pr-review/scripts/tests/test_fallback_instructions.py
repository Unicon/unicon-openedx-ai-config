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
        "manual testing steps",
        "order it runs",
        "docs and ADRs, models and migrations, API, REST views and serializers, "
        "frontend data layer, components, styles, remaining tests",
        "every changed file",
        "acceptance criterion",
    ):
        assert phrase in text


def test_short_inputs_kept_in_order():
    out = compose_instructions("BASE", ["Step 1: Add", "Step 2: Edit"], [("AC1", "Add works")])
    assert out.startswith("BASE\n") and out.index("1. Step 1: Add") < out.index("2. Step 2: Edit")
    assert "AC1: Add works" in out


def test_exact_layout():
    out = compose_instructions("BASE", ["A", "B"], [("AC1", "x"), ("AC2", "y")])
    assert out == "BASE\n\nManual testing steps:\n1. A\n2. B\n\nAcceptance criteria:\nAC1: x\nAC2: y\n"


def test_long_inputs_fit_limit():
    out = compose_instructions("B" * 900, ["s" * 300] * 30, [(f"AC{i}", "t" * 300) for i in range(20)])
    assert len(out) <= 2000 and out.startswith("B" * 900)
    assert out.endswith("…")


def test_criterion_text_shortened_first():
    steps = ["s" * 50] * 3
    criteria = [(f"AC{i}", "t" * 300) for i in range(8)]
    out = compose_instructions("B", steps, criteria)
    assert len(out) <= LIMIT
    assert "s" * 50 in out
    assert "t" * 100 not in out and "t" * 99 + "…" in out


def test_steps_shortened_after_criteria():
    steps = ["s" * 400] * 6
    out = compose_instructions("B", steps, [("AC1", "t" * 300)])
    assert len(out) <= LIMIT
    assert "t" * 99 + "…" in out
    assert "s" * 149 + "…" in out and "s" * 150 not in out


def test_criteria_reduced_to_ids_when_still_too_long():
    steps = ["s" * 150] * 10
    criteria = [(f"AC{i}", "t" * 100) for i in range(10)]
    out = compose_instructions("B", steps, criteria)
    assert len(out) <= LIMIT
    assert "s" * 149 + "…" not in out and "s" * 150 in out
    assert "AC9" in out and "t" * 10 not in out


def test_main_writes_file(tmp_path, synthetic, capsys):
    assert main(["--artifacts", str(synthetic), "--data-dir", str(tmp_path)]) == 0
    target = tmp_path / "guide-instructions.md"
    text = target.read_text()
    assert len(text) <= 2000 and "Step 1: Add a competency" in text
    assert "Migrations and removed code" not in text
    assert "AC1: An author can add a competency" in text
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
