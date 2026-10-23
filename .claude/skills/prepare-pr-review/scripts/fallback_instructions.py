#!/usr/bin/env python3
"""Write instructions for Plannotator's built-in guide generator.

When the saved-guide route breaks, the skill falls back to Plannotator's own guide generator.
That generator reads up to 2,000 characters of extra instructions from
``<data-dir>/guide-instructions.md`` each time it runs. This script composes that file from a
short base text, the PR's manual testing steps, and its acceptance criteria, and shortens the
steps and criteria when the result would be too long. Standard library only.

Usage: ``python3 fallback_instructions.py --artifacts DIR [--data-dir DIR]``
"""
import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

from compose_guide import data_dir
from guide_inputs import load_chapters, load_criteria

LIMIT = 2000
CRITERION_TEXT_LIMIT = 100
STEP_LIMIT = 150
BASE_FILE = Path(__file__).resolve().parents[1] / "references" / "guide-instructions-base.md"


def _clip(text: str, width: int) -> str:
    """Return ``text``, cut to ``width`` characters with a trailing ellipsis when it is longer."""
    return text if len(text) <= width else text[: width - 1] + "…"


def _assemble(base: str, steps: list[str], criteria: list[str]) -> str:
    parts = [base.rstrip("\n")]
    if steps:
        parts.append("Manual testing steps:\n" + "\n".join(f"{i}. {step}" for i, step in enumerate(steps, 1)))
    if criteria:
        parts.append("Acceptance criteria:\n" + "\n".join(criteria))
    return "\n\n".join(parts) + "\n"


def compose_instructions(
    base: str, steps: list[str], criteria: list[tuple[str, str]], limit: int = LIMIT
) -> str:
    """Return the guide-instructions text: ``base``, the numbered ``steps``, and the ``(id, text)`` ``criteria``.

    The result is at most ``limit`` characters. When the full text is longer, it is shortened
    in this order until it fits: each criterion text to 100 characters, each step to 150
    characters, criteria to their ids only, and finally the whole text cut at ``limit - 1``
    characters with ``…`` appended.
    """
    attempts = (
        (steps, [f"{cid}: {text}" for cid, text in criteria]),
        (steps, [f"{cid}: {_clip(text, CRITERION_TEXT_LIMIT)}" for cid, text in criteria]),
        ([_clip(step, STEP_LIMIT) for step in steps], [f"{cid}: {_clip(text, CRITERION_TEXT_LIMIT)}" for cid, text in criteria]),
        ([_clip(step, STEP_LIMIT) for step in steps], [cid for cid, _ in criteria]),
    )
    for attempt_steps, attempt_criteria in attempts:
        text = _assemble(base, attempt_steps, attempt_criteria)
        if len(text) <= limit:
            return text
    return text[: limit - 1] + "…"


def main(argv: list[str] | None = None) -> int:
    """Run the CLI; write ``guide-instructions.md`` into the data directory and print its path.

    The file applies to every later Plannotator guide, so an existing one is first copied to
    ``guide-instructions.md.bak-<YYYYmmdd-HHMMSS>`` in the same folder, and ``Backup: <path>`` is
    printed before the target path.

    Returns 0 on success and 1 (with a message on stderr) for invalid or missing inputs.
    """
    parser = argparse.ArgumentParser(description="Write guide-instructions.md for Plannotator's built-in guide generator.")
    parser.add_argument("--artifacts", required=True, type=Path, help="folder with chapters.json and criteria.json")
    parser.add_argument("--data-dir", type=Path, default=None, help="Plannotator data directory (default: $PLANNOTATOR_DATA_DIR or ~/.plannotator)")
    args = parser.parse_args(argv)
    try:
        chapters = load_chapters(args.artifacts / "chapters.json")
        criteria = load_criteria(args.artifacts / "criteria.json")
        base = BASE_FILE.read_text(encoding="utf-8")
    except (ValueError, FileNotFoundError) as error:
        print(error, file=sys.stderr)
        return 1
    steps = [f"{chapter.title}: {chapter.do}" for chapter in chapters if chapter.kind == "step"]
    text = compose_instructions(base, steps, [(c.id, c.text) for c in criteria])
    target = (args.data_dir or data_dir()) / "guide-instructions.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        backup = target.with_name(f"{target.name}.bak-{datetime.now():%Y%m%d-%H%M%S}")
        shutil.copy2(target, backup)
        print(f"Backup: {backup}")
    target.write_text(text, encoding="utf-8")
    print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
