#!/usr/bin/env python3
"""Write instructions for Plannotator's built-in guide generator.

When the saved-guide route breaks, the skill falls back to Plannotator's own guide generator.
That generator reads up to 2,000 characters of extra instructions from
``<data-dir>/guide-instructions.md`` each time it runs. This script composes that file from a
short base text and the PR's acceptance criteria, and shortens the criteria texts when the
result would be too long. Standard library only.

Usage: ``python3 fallback_instructions.py --artifacts DIR [--data-dir DIR]``
"""
import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

from compose_guide import data_dir
from guide_inputs import load_criteria

LIMIT = 2000
HEADER = "Acceptance criteria, one chapter each, in this order:"
BASE_FILE = Path(__file__).resolve().parents[1] / "references" / "guide-instructions-base.md"


def _first_line(text: str) -> str:
    return next((line for line in text.splitlines() if line.strip()), "")


def _assemble(base: str, criteria: list[tuple[str, str]]) -> str:
    parts = [base.rstrip("\n"), HEADER]
    parts.extend(f"{cid}:\n{text}" for cid, text in criteria)
    return "\n\n".join(parts) + "\n"


def compose_instructions(base: str, criteria: list[tuple[str, str]], limit: int = LIMIT) -> str:
    """Return the guide-instructions text: ``base``, then the ``(id, text)`` ``criteria`` in order.

    Each criterion appears as ``<id>:`` on its own line followed by its exact text. When the
    result is longer than ``limit`` characters, the texts are shortened in this order until it
    fits: each text cut to 300 characters, then to 150, then to its first line, and finally the
    whole result is cut at ``limit - 1`` characters with ``…`` appended.
    """
    shorteners = (
        lambda text: text,
        lambda text: text[:300],
        lambda text: text[:150],
        _first_line,
    )
    for shorten in shorteners:
        text = _assemble(base, [(cid, shorten(body)) for cid, body in criteria])
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
    parser.add_argument("--artifacts", required=True, type=Path, help="folder with criteria.json")
    parser.add_argument("--data-dir", type=Path, default=None, help="Plannotator data directory (default: $PLANNOTATOR_DATA_DIR or ~/.plannotator)")
    args = parser.parse_args(argv)
    try:
        criteria, _backgrounds = load_criteria(args.artifacts / "criteria.json")
        base = BASE_FILE.read_text(encoding="utf-8")
    except (ValueError, FileNotFoundError) as error:
        print(error, file=sys.stderr)
        return 1
    text = compose_instructions(base, [(c.id, c.text) for c in criteria])
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
