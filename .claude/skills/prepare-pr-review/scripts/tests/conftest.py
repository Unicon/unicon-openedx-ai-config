"""Pytest setup: make the skill's scripts importable and expose the synthetic fixture."""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SKILL_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SKILL_DIR / "scripts"))


@pytest.fixture
def synthetic():
    """Path to the hand-written PR fixture directory."""
    return SKILL_DIR / "testdata" / "synthetic"


@pytest.fixture
def inputs(synthetic):
    """The synthetic PR fixtures, loaded through guide_inputs."""
    import guide_inputs

    pr = guide_inputs.load_pr(synthetic / "pr.json")
    verdict, findings = guide_inputs.load_findings(synthetic / "findings.json")
    criteria, backgrounds = guide_inputs.load_criteria(synthetic / "criteria.json")
    return SimpleNamespace(
        pr=pr,
        changed=guide_inputs.changed_files(pr),
        criteria=criteria,
        backgrounds=backgrounds,
        mapper=guide_inputs.load_mapper_file(synthetic / "pieces-1.json"),
        verdict=verdict,
        findings=findings,
    )
