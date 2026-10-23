"""Pytest setup: make the skill's scripts importable and expose the synthetic fixture."""
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SKILL_DIR / "scripts"))


@pytest.fixture
def synthetic():
    """Path to the hand-written PR fixture directory."""
    return SKILL_DIR / "testdata" / "synthetic"
