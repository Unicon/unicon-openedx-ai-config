#!/usr/bin/env python3
"""Render the text of each guide chapter and the Mermaid change map.

Pure functions over the dataclasses from ``guide_inputs`` and ``guide_mapping``. Plannotator
shows links as plain text, so line references are written as plain text too. Every piece of
free text goes through ``one_line``, so a stray newline cannot break a callout or a bullet.
Standard library only.
"""
from guide_inputs import Anchor, Chapter, Criterion, FileEntry, Finding
from guide_mapping import Gaps, ac_tags_for_file

CALLOUT_BY_SEVERITY = {
    "Bug": "WARNING",
    "Gap": "WARNING",
    "Question": "IMPORTANT",
    "Suggestion": "NOTE",
    "Nit": "NOTE",
}


def one_line(text: str) -> str:
    """Collapse every whitespace run, newlines included, to one space and strip the ends."""
    return " ".join(text.split())


def code_ref(anchor: Anchor) -> str:
    """Return the plain-text reference to an anchor, such as ```src/a.py` L40-L52`` or ```src/a.py` L15``."""
    lines = f"L{anchor.start}" if anchor.start == anchor.end else f"L{anchor.start}-L{anchor.end}"
    return f"`{anchor.path}` {lines}"


def render_finding(f: Finding) -> str:
    """Return one single-line callout for a finding: severity, title, why, then the code reference."""
    title = one_line(f.title)
    if not title.endswith("."):
        title += "."
    return f"> [!{CALLOUT_BY_SEVERITY[f.severity]}] {f.severity}: {title} {one_line(f.why)} {code_ref(f.anchor)}"


def render_file_summary(entry: FileEntry, criteria: list[Criterion]) -> str:
    """Return a file's summary, followed by the criterion tags that point at the file when there are any."""
    summary = one_line(entry.summary)
    tags = ac_tags_for_file(criteria, entry.path)
    return f"{summary} {tags}." if tags else summary


def render_overview(
    chapter: Chapter,
    *,
    criteria: list[Criterion],
    findings: list[Finding],
    first_section_by_path: dict[str, int],
    this_section: int,
) -> str:
    """Return a chapter's overview text; blocks are separated by a blank line and empty ones are omitted.

    A step chapter starts with its Do line, its Expect line, and, when the step was sharpened,
    the author's original wording, each as its own block because Plannotator joins adjacent
    lines into one paragraph. Both chapter kinds then list the criteria they cover, the findings
    (rendered in the order given), and the code in reading order. A code ref whose file an
    earlier chapter already showed gets a pointer to that chapter.
    """
    blocks = []
    if chapter.kind == "step":
        blocks.append(f"**Do:** {one_line(chapter.do)}")
        blocks.append(f"**Expect:** {one_line(chapter.expect)}")
        if chapter.original:
            blocks.append(f'Sharpened from the PR. Author\'s wording: "{one_line(chapter.original)}"')
    if criteria:
        covers = " ".join(f'{c.id} "{one_line(c.text)}".' for c in criteria)
        blocks.append(f"**Covers:** {covers}")
    blocks.extend(render_finding(f) for f in findings)
    if chapter.code:
        lines = ["**Code, in the order it runs:**"]
        for ref in chapter.code:
            line = f"- {code_ref(ref.anchor)}: {one_line(ref.role)}."
            first = first_section_by_path.get(ref.anchor.path, this_section)
            if first != this_section:
                line += f" First read in chapter {first}."
            lines.append(line)
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def render_before_you_start(*, verdict: str, gaps: Gaps, outside: list[Finding], change_map_note: str | None) -> str:
    """Return the guide's opening text: the verdict, the two gap lists, and findings on unchanged files.

    ``change_map_note`` is appended as the last block when it is not None.
    """
    criteria_lines = [f'- {c.id} "{one_line(c.text)}"' for c in gaps.unimplemented] or ["- None."]
    file_lines = [f"- `{path}`" for path in gaps.unmatched_files] or ["- None."]
    blocks = [
        f"**Review verdict:** {one_line(verdict)}",
        "\n".join(["**Acceptance criteria with no code in this PR:**", *criteria_lines]),
        "\n".join(["**Changed files no acceptance criterion points at:**", *file_lines]),
    ]
    if outside:
        blocks.append("**Findings outside the changed files:**")
        blocks.extend(render_finding(f) for f in outside)
    if change_map_note is not None:
        blocks.append(change_map_note)
    return "\n\n".join(blocks)


def _label(text: str) -> str:
    return '"' + one_line(text).replace('"', "#quot;") + '"'


def render_change_map(chapters: list[Chapter]) -> str:
    """Return Mermaid source linking each chapter node ``c<i>`` to the file nodes ``f<j>`` it shows or places.

    File nodes are numbered in order of first appearance, with code refs before file entries
    within a chapter. There is one edge per distinct (chapter, path) pair and no click lines.
    """
    file_index: dict[str, int] = {}
    nodes = []
    edges = []
    for i, chapter in enumerate(chapters):
        nodes.append(f"    c{i}[{_label(chapter.title)}]")
        paths = [ref.anchor.path for ref in chapter.code] + [entry.path for entry in chapter.files]
        for path in dict.fromkeys(paths):
            if path not in file_index:
                file_index[path] = len(file_index)
            edges.append(f"    c{i} --> f{file_index[path]}")
    nodes.extend(f"    f{j}[{_label(path)}]" for path, j in file_index.items())
    return "\n".join(["flowchart LR", *nodes, *edges]) + "\n"
