#!/usr/bin/env python3
"""Render the text of each guide chapter and the Mermaid change map.

Pure functions over the dataclasses from ``guide_inputs`` and ``guide_mapping``. Plannotator
shows links as plain text, so line references are written as plain text too. Free text goes
through ``one_line``, so a stray newline cannot split a bullet. Acceptance criterion text is the
exception: it is copied exactly, inside a fenced block. Standard library only.
"""
from guide_inputs import Anchor, Background, Criterion, Finding, Piece, one_line
from guide_mapping import Chapter, _overlaps, ac_name

_ZWSP = "\u200b"
_CLOSERS = (".", "?", "!")


def lines(anchor: Anchor) -> str:
    """Return the line reference of an anchor: ``L5-L20`` for a range, ``L15`` for one line."""
    return f"L{anchor.start}" if anchor.start == anchor.end else f"L{anchor.start}-L{anchor.end}"


def piece_label(piece: Piece) -> str:
    """Return the short label that starts a piece's bullet.

    A piece with criteria is labeled by them: the ids alone for an ``implements`` piece, the ids
    and the kind otherwise. A piece with no criteria is labeled by its kind.
    """
    if not piece.acs:
        return piece.kind
    acs = ", ".join(piece.acs)
    return acs if piece.kind == "implements" else f"{acs} {piece.kind}"


def ac_block(text: str) -> str:
    """Return ``text`` in a fenced block, keeping every line exactly as written.

    A line whose left-trimmed text starts with three backticks gets a leading zero-width space, so
    it cannot close the fence early.
    """
    body = [_ZWSP + line if line.lstrip().startswith("```") else line for line in text.split("\n")]
    return "\n".join(["```", *body, "```"])


def _finding_text(finding: Finding) -> str:
    title = one_line(finding.title)
    if not title.endswith(_CLOSERS):
        title += "."
    return f"{finding.severity}: {title} {one_line(finding.why)}"


def _file_group(path, keys, pieces_by_path, findings_by_path, criteria_by_id) -> str:
    items = [(p.anchor.start, 0, p.anchor.end, p) for p in pieces_by_path.get(path, ())]
    items += [(f.anchor.start, 1, f.anchor.end, f) for f in findings_by_path.get(path, ())]
    items.sort(key=lambda item: item[:3])
    out = [f"### {path}"]
    for _, is_finding, _, item in items:
        if is_finding:
            out.append(f"- {lines(item.anchor)} {_finding_text(item)}")
            continue
        key_ids = [cid for cid in criteria_by_id if keys.get(cid) is item]
        suffix = f" (key piece for {', '.join(key_ids)})" if key_ids else ""
        out.append(f"- {lines(item.anchor)} {piece_label(item)}: {one_line(item.purpose)}{suffix}")
        out.extend(ac_block(criteria_by_id[cid].text) for cid in key_ids)
    return "\n".join(out)


def _also_groups(chapter, section, keys, findings_by_path, sections, titles_by_section) -> list[str]:
    by_section: dict[int, list[str]] = {}
    for piece in chapter.pieces:
        shown_in = sections.get(piece.anchor.path)
        if shown_in is None or shown_in == section:
            continue
        marks = []
        if chapter.ac is not None and keys.get(chapter.ac) is piece:
            marks.append("key piece")
        count = sum(_overlaps(f.anchor, piece.anchor) for f in findings_by_path.get(piece.anchor.path, ()))
        if count:
            marks.append(f"{count} finding" if count == 1 else f"{count} findings")
        suffix = f" ({', '.join(marks)})" if marks else ""
        by_section.setdefault(shown_in, []).append(
            f"- {piece.anchor.path} {lines(piece.anchor)} {piece_label(piece)}: {one_line(piece.purpose)}{suffix}")
    return [
        "\n".join([f"### Also in this chapter, diff shown in chapter {n}: {one_line(titles_by_section[n])}", *bullets])
        for n, bullets in sorted(by_section.items())
    ]


def render_overview(
    chapter: Chapter,
    *,
    section: int,
    criteria_by_id: dict[str, Criterion],
    keys: dict[str, Piece],
    pieces_by_path: dict[str, list[Piece]],
    findings_by_path: dict[str, tuple[Finding, ...]],
    sections: dict[str, int],
    titles_by_section: dict[int, str],
) -> str:
    """Return a chapter's left-column text; blocks are joined by one blank line.

    An acceptance criterion chapter starts with its review verdict, when it has one, and its exact
    text when no code implements it or when its key piece's file is shown in another section.
    Then each of the chapter's files gets a ``###`` heading with one bullet per code piece and per
    finding in that file, interleaved by line number (every piece of the file, whichever criterion
    it serves). A key piece's bullet is followed by the exact text of each criterion it is the key
    piece for. Pieces of this chapter whose file is shown in another section are listed last, by
    section, with no criterion text. Each such group's heading names the section number and the
    title that ``titles_by_section`` gives for it.
    """
    blocks = []
    key = keys.get(chapter.ac) if chapter.ac is not None else None
    if chapter.kind == "ac":
        criterion = criteria_by_id[chapter.ac]
        if criterion.verdict:
            blocks.append(f"Review verdict: {one_line(criterion.verdict).rstrip('.')}.")
        if not chapter.pieces:
            blocks.append("No code in this PR implements this AC.")
            blocks.append(ac_block(criterion.text))
        elif key is not None and sections.get(key.anchor.path) != section:
            blocks.append(ac_block(criterion.text))
    blocks.extend(
        _file_group(path, keys, pieces_by_path, findings_by_path, criteria_by_id)
        for path in chapter.files
    )
    blocks.extend(_also_groups(chapter, section, keys, findings_by_path, sections, titles_by_section))
    return "\n\n".join(blocks)


def render_file_summary(summary: str, path: str, pieces_by_path: dict[str, list[Piece]], finding_count: int) -> str:
    """Return a file's one-line summary, then the criteria its pieces serve and its finding count.

    The summary ends with a period unless it already ends in ``.``, ``?`` or ``!``. Criteria are listed in numeric order of their ids, and the finding count
    is omitted when it is zero.
    """
    text = one_line(summary)
    if not text.endswith(_CLOSERS):
        text += "."
    acs = {ac for piece in pieces_by_path.get(path, ()) for ac in piece.acs}
    if acs:
        text += " " + ", ".join(sorted(acs, key=lambda ac: (len(ac), ac))) + "."
    if finding_count:
        text += f" {finding_count} finding." if finding_count == 1 else f" {finding_count} findings."
    return text


def render_before_you_start(
    *,
    verdict: str,
    backgrounds: list[Background],
    gaps: list[Criterion],
    outside: list[Finding],
    change_map_note: str | None,
) -> str:
    """Return the guide's opening text: the verdict, shared backgrounds, criteria with no code, and findings on unchanged files.

    ``gaps`` are the criteria no code implements. ``change_map_note`` is appended as the last block
    when it is not None.
    """
    blocks = [f"**Review verdict:** {one_line(verdict)}"]
    blocks.extend(f"Background from {one_line(b.source)}:\n{ac_block(b.text)}" for b in backgrounds)
    gap_lines = [f"- {c.id}: {ac_name(c.text)}" for c in gaps] or ["- None."]
    blocks.append("\n".join(["**Acceptance criteria with no code in this PR:**", *gap_lines]))
    if outside:
        blocks.append("\n".join([
            "**Findings on files this PR does not change:**",
            *(f"- {f.anchor.path} {lines(f.anchor)} {_finding_text(f)}" for f in outside),
        ]))
    if change_map_note is not None:
        blocks.append(change_map_note)
    return "\n\n".join(blocks)


def _label(text: str) -> str:
    return '"' + one_line(text).replace('"', "#quot;") + '"'


def render_change_map(chapters: list[Chapter]) -> str:
    """Return Mermaid source linking each chapter node ``c<i>`` to the file nodes ``f<j>`` of its pieces.

    File nodes are numbered in order of first appearance. There is one edge per distinct (chapter,
    file of one of its pieces) pair, and no click lines.
    """
    file_index: dict[str, int] = {}
    nodes = []
    edges = []
    for i, chapter in enumerate(chapters):
        nodes.append(f"    c{i}[{_label(chapter.title)}]")
        for path in dict.fromkeys(piece.anchor.path for piece in chapter.pieces):
            if path not in file_index:
                file_index[path] = len(file_index)
            edges.append(f"    c{i} --> f{file_index[path]}")
    nodes.extend(f"    f{j}[{_label(path)}]" for path, j in file_index.items())
    return "\n".join(["flowchart LR", *nodes, *edges]) + "\n"
