# prepare-pr-review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A `prepare-pr-review` skill that reads an existing code review markdown file for a GitHub PR, maps the PR's manual testing steps to the code they run, and opens a self-written Plannotator Guided Review for Jesper's line-by-line review.

**Architecture:** `SKILL.md` drives the workflow in the top-level session: pin the PR, take the path of an existing review markdown file (asking for it when not given), dispatch a Sonnet mapper in the background, and write criteria and findings JSON from the review file. Deterministic standard-library Python scripts compose the saved guide, check coverage, and write fallback instructions. The skill never posts to GitHub and never adds Plannotator annotations.

**Tech Stack:** Python 3.12+ standard library (scripts), pytest 9 from `~/.virtualenvs/tutor` (tests), `gh` CLI, Plannotator 0.28.27 with its Claude Code plugin.

**Spec:** `/Users/jesperhodge/workspace/unicon-openedx-ai-config/.claude/plans/2026-10-23-prepare-pr-review-design.md`. Read it before any task.

## Global Constraints

- Repo: `/Users/jesperhodge/workspace/unicon-openedx-ai-config` (below: `CFG`). Branch `feat/prepare-pr-review-skill`, created from the current `ai/pr-component-tree-skill` in the main checkout. Never push.
- Skill directory: `CFG/.claude/skills/prepare-pr-review/` (below: `SKILL_DIR`).
- The main checkout has untracked files that are not ours (`.agents/`, `.claude/skills/quick-code-review/`, `.claude/worktrees/`, `AGENTS.md`). Stage files by explicit path only; never `git add -A` or `git add .`.
- Commit subjects follow the repo's style: `ai: ...` for skill work, `docs: ...` for plan and design changes. End every commit message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Scripts use only the standard library and run with `python3`. Tests run with: `source ~/.virtualenvs/tutor/bin/activate && cd SKILL_DIR && python -m pytest scripts/tests -v`. If that venv lacks a needed package, create a dedicated venv; never change the `tutor` venv.
- Do not modify `code-review-openedx`, `backend-code-review`, `frontend-code-review`, `pr-component-tree`, `CLAUDE.md`, or anything in `.claude/decisions/`.
- The skill never posts to GitHub, never calls Plannotator's external-annotations API, and never changes the PR or its branches.
- Delegation rule from `CLAUDE.md`: only the top-level session dispatches sub-agents, with `model` passed explicitly. Implementer sub-agents never dispatch; where a step needs a dispatch, it is marked "orchestrator".
- Prose (SKILL.md, references, guide text the scripts emit): full sentences, US spelling, no em dashes, they/them for Jesper.
- Plannotator facts (from its source, `packages/shared/guide-store.ts`, `packages/core/guide.ts`, `packages/core/guide-links.ts`, `packages/guide-viewer/renderMarkdownProse.tsx`, `packages/shared/review-progress.ts`):
  - Saved guide path: `<data-dir>/guides/<repo-key>/<id>.json`, data dir `$PLANNOTATOR_DATA_DIR` or `~/.plannotator`.
  - Repo key from a PR URL: `host__owner__repo`, each segment sanitized by replacing runs of `[^a-zA-Z0-9._-]` with `-` and trimming leading and trailing `.` and `-`.
  - Guide id: `^[A-Za-z0-9][A-Za-z0-9._-]*$`, at most 160 chars. Plannotator's own form is `<epoch-ms>-<slug>`, with the slug being the lowercased title, runs of non `[a-z0-9]` replaced by `-`, trimmed, cut to 60 chars, and trailing `-` removed.
  - Envelope: `{"version": 1, "savedAt": <ms>, "label": str, "title": str, "headSha": str, "prUrl": str, "guide": {"title": str, "intent": str, "overview"?: {"text": str, "diagram"?: {"kind": "mermaid", "source": str}}, "sections": [{"title": str, "overview": str, "diffs": [{"file": str, "summary": str}]}]}, "reviewed": [false, ...]}`. A section with `"diffs": []` is valid.
  - Prose renders paragraphs, `#` headings, `-` and `*` bullets (no numbered lists), fenced code, inline bold, italic, code, and links. Callouts are `> [!WARNING]`, `> [!IMPORTANT]`, and `> [!NOTE]`; the single-line form `> [!NOTE] text` works, and the lines of a multi-line callout are joined into one paragraph.
  - Links in prose are markdown links: `[label](code:path#L24-L40)`, `[label](code:path#L24)`, `[label](chapter:2)` (1-based over sections). Task 1 showed that the live review screen (0.28.27) renders these links as text and does not make them clickable, and that it never shows `guide.overview`. So the scripts write line and chapter references as plain text, and the change map is a separate `.mmd` file.
  - Review progress (PR mode): `<data-dir>/review-progress/<key>/<sha256-hex(path)>.json`, with `key = sha256-hex(JSON.stringify(["pr", prUrl, "layer"]))` and the record `{"v": 1, "path", "fingerprint", "viewed", "suppressed"}`.
- `TESTED_PLANNOTATOR_VERSION = "0.28.27"`.

## Review Focus

1. A PR that deletes or renames files: `gh` lists the deleted or new path, and the guide must still place it, or the placement check must name it. Pinned in Task 2 by `test_check_placement_requires_deleted_files`.
2. A PR URL pasted with `/files`, a trailing slash, or a `#fragment`: the repo key and the canonical URL must be the same as for the bare URL. Pinned in Task 5 by `test_repo_key_from_url_variants` and `test_canonical_pr_url`.
3. Ticket, finding, or step text containing newlines, double quotes, or a leading `>`: callouts must stay on one line, and Mermaid labels must stay valid. Pinned in Task 4 by `test_finding_collapses_newlines` and `test_change_map_escapes_quotes`.
4. A review finding anchored in a file the PR did not change (a caller, for example): it must be shown, not dropped and not a crash. Pinned in Task 3 by `test_findings_outside_changed_files` and in Task 4 by `test_before_you_start_lists_outside_findings`.
5. Several linked issues whose criteria are each numbered from 1: duplicate ids must be rejected, so the session renumbers them. Pinned in Task 2 by `test_load_criteria_rejects_duplicate_ids`; SKILL.md (Task 9) numbers criteria AC1 to ACn across all issues.

---

### Task 1: Install the plugin and settle the unverified facts (Jesper in the loop)

**Files:**
- Create: `CFG/.claude/plans/2026-10-23-prepare-pr-review-plan.md` (this file; commit it)
- Create: `SKILL_DIR/testdata/real/pr.json`
- Create: `~/.plannotator/guides/<repo-key>/<epoch-ms>-pr-<n>-spike.json`
- Create: `/Users/jesperhodge/openedx/pr-reviews/<repo>-<n>/task1-checklist.md`
- Modify: `CFG/.claude/plans/2026-10-23-prepare-pr-review-design.md` (facts table)

**Interfaces:**
- Produces: the facts table rows for checklist items 1 to 9 in the design document; `testdata/real/pr.json` (the `gh` JSON shape used by later tasks); the PR URL used in Tasks 8 and 10.

- [ ] **Step 1: Create the branch and commit the design and plan**

```bash
cd /Users/jesperhodge/workspace/unicon-openedx-ai-config
git checkout -b feat/prepare-pr-review-skill
git add .claude/plans/2026-10-23-prepare-pr-review-design.md .claude/plans/2026-10-23-prepare-pr-review-plan.md
git commit -m "docs: add prepare-pr-review design and plan"
```

Expected: `git log -1 --stat` shows only those two files.

- [ ] **Step 2: Pick a small real PR**

Pick a public upstream PR in `openedx/frontend-app-authoring` or `openedx/openedx-core` with at most 8 changed files, a linked issue, and a testing-instructions section with at least two steps. Use `gh pr list --repo <repo> --state all --limit 50 --json number,title,body,files,closingIssuesReferences`. Then save the fixture:

```bash
mkdir -p SKILL_DIR/testdata/real
gh pr view <url> --json url,number,title,body,headRefOid,baseRefOid,headRepository,files,closingIssuesReferences > SKILL_DIR/testdata/real/pr.json
```

- [ ] **Step 3: Hand-write the spike guide**

Write the envelope (shape in Global Constraints) to `~/.plannotator/guides/<repo-key>/<epoch-ms>-pr-<n>-spike.json` with `label` `"PR #<n> spike"` and `headSha` = `headRefOid`. It contains:
- `guide.overview` with a short `text` and a Mermaid `diagram` with two nodes and one `click` line to a `code:` link.
- Section 1 "Before you start", `diffs: []`, with one single-line callout of each kind (`[!WARNING]`, `[!IMPORTANT]`, `[!NOTE]`) and a `[chapter 2](chapter:2)` link.
- Section 2 places every changed file, and its overview has `-` bullets with `code:` range links into one of them.
- `reviewed: [false, false]`.

Validate it: `python3 -c "import json,sys; json.load(open(sys.argv[1]))" <path>` exits 0.

- [ ] **Step 4: Write the checklist for Jesper**

`task1-checklist.md` lists, with the exact PR URL filled in:
1. In Claude Code, run `/plugin marketplace add backnotprop/plannotator`, then `/plugin install plannotator@plannotator`, then quit and restart Claude Code.
2. In a terminal, `cd /Users/jesperhodge/openedx && claude`, then run `/plannotator-review <url>`.
3. Click Guide, pick "PR #<n> spike" from the previous guides, and report on design checklist items 1 to 4: it loads; the three callouts render, and which colors they have; the empty "Before you start" chapter renders; the overview diagram renders; and the `code:` and `chapter:` links work.
4. Mark one file as viewed. Ask AI one question about a line, and note where the answer comes from (the terminal session, or something else) (items 5, 6, 9).
5. While the review is open, type "hello" in the terminal session and note whether it answers (item 9).
6. Open the post dialog and do **not** post. Note what it lists (item 8).
7. Optionally, repeat step 4 from the VS Code chat panel (item 5).

- [ ] **Step 5 (orchestrator): Hand the checklist to Jesper and wait for the results**

- [ ] **Step 6: Find the review-progress record (item 7)**

Compute `sha256(json.dumps(["pr", url, "layer"], separators=(",", ":")))` for the canonical URL `https://github.com/<owner>/<repo>/pull/<n>` and confirm that `~/.plannotator/review-progress/<key>/` exists and holds a record with `"viewed": true` for the file Jesper marked. If it does not, list `~/.plannotator/review-progress/` by modification time, read the newest record, and record which URL form matches.

- [ ] **Step 7: Record the results and commit**

Update the design's facts table: every "unverified" row becomes "Confirmed in Task 1" or "Failed in Task 1: <what happened>". Add one row per checklist item. Apply "What the results change" from the design: for item 4, record whether `EMBED_CHANGE_MAP` (Task 5) is `True`; for item 3, record whether the "Before you start" section stays a section or moves into `intent`; for item 7, record the URL form.

```bash
git add .claude/plans/2026-10-23-prepare-pr-review-design.md .claude/skills/prepare-pr-review/testdata/real/pr.json
git commit -m "docs: record Plannotator spike results for prepare-pr-review"
```

- [ ] **Step 8 (orchestrator): Gate**

If item 1 or item 8 failed, stop and decide with Jesper before Task 2, as the design says. Otherwise continue.

---

### Task 2: Input models, loaders, and the placement check

**Files:**
- Create: `SKILL_DIR/scripts/guide_inputs.py`
- Create: `SKILL_DIR/scripts/tests/conftest.py` (puts `SKILL_DIR/scripts` on `sys.path` and exposes a `synthetic` fixture returning `SKILL_DIR/testdata/synthetic`)
- Create: `SKILL_DIR/testdata/synthetic/{pr.json,chapters.json,criteria.json,findings.json}`
- Test: `SKILL_DIR/scripts/tests/test_guide_inputs.py`

**Interfaces:**
- Produces, in `guide_inputs.py`:
  - `SEVERITIES = ("Bug", "Gap", "Question", "Suggestion", "Nit")`
  - frozen dataclasses: `Anchor(path: str, start: int, end: int)`, `CodeRef(anchor: Anchor, role: str)`, `FileEntry(path: str, summary: str)`, `Chapter(kind: str, title: str, do: str | None, expect: str | None, original: str | None, code: tuple[CodeRef, ...], files: tuple[FileEntry, ...])`, `Criterion(id: str, text: str, implemented_at: tuple[Anchor, ...], tested_by: tuple[str, ...], verdict: str)`, `Finding(severity: str, title: str, anchor: Anchor, why: str)`
  - `parse_anchor(text: str) -> Anchor`, `load_chapters(path) -> list[Chapter]`, `load_criteria(path) -> list[Criterion]`, `load_findings(path) -> tuple[str, list[Finding]]` (verdict line, findings), `load_pr(path) -> dict`, `changed_files(pr: dict) -> list[str]`
  - `class PlacementError(ValueError)` with attributes `missing`, `duplicated`, `unknown` (sorted lists of paths); `check_placement(changed: list[str], chapters: list[Chapter]) -> None`

JSON formats (the mapper in Task 8 and the session in Task 9 write these):

```json
{"chapters": [
  {"kind": "step", "title": "Step 1: Add a competency", "do": "...", "expect": "...", "original": null,
   "code": [{"anchor": "src/pages/CompetencyPage.tsx:12-30", "role": "renders the Add button"}],
   "files": [{"path": "src/pages/CompetencyPage.tsx", "summary": "Adds the Add button."}]},
  {"kind": "layer", "title": "Migrations and removed code", "code": [], "files": []}
]}
```

`criteria.json`: `{"criteria": [{"id": "AC1", "text": "...", "implemented_at": ["path:5-20"], "tested_by": ["path::test_name"], "verdict": "Covered"}]}`. `findings.json`: `{"verdict": "Ready to merge: with fixes. ...", "findings": [{"severity": "Bug", "title": "...", "anchor": "path:22-30", "why": "..."}]}`.

Synthetic fixture content (later tasks' tests depend on it):
- `pr.json`: `url` `https://github.com/openedx/frontend-app-authoring/pull/123`, `number` 123, `title` "Add competency levels", `headRefOid` `"abc123"`, files in this order: `src/pages/CompetencyPage.tsx`, `src/data/api.ts`, `src/data/api.test.ts`, `migrations/0002_add_level.py`, `src/old/Legacy.tsx`.
- `chapters.json`:
  - Chapter 1: step "Step 1: Add a competency". Do "Open Studio > Competencies and click Add." Expect "The new competency appears in the list." `original` null. Code refs `src/pages/CompetencyPage.tsx:12-30` "renders the Add button" and `src/data/api.ts:5-20` "posts the new competency". Files: `CompetencyPage.tsx` "Adds the Add button.", `api.ts` "Adds the create and patch calls.", `api.test.ts` "Tests both calls."
  - Chapter 2: step "Step 2: Edit the level". Do "Click a competency and change its level to 3." Expect "The list shows level 3." `original` "check editing works". Code refs `src/data/api.ts:22-30` "patches the level" and `src/pages/CompetencyPage.tsx:40-44` "opens the edit form". No files.
  - Chapter 3: layer "Migrations and removed code". No code refs. Files: `migrations/0002_add_level.py` "Adds the level column.", `src/old/Legacy.tsx` "Deleted."
- `criteria.json`: AC1 "An author can add a competency", implemented at `src/pages/CompetencyPage.tsx:12-30` and `src/data/api.ts:5-20`, tested by `src/data/api.test.ts::adds a competency`, verdict "Covered". AC2 "An author can change the level", implemented at `src/data/api.ts:22-30`, verdict "Implemented, untested". AC3 "Deleting a competency asks for confirmation", implemented at nothing, verdict "Not implemented".
- `findings.json`: verdict "Ready to merge: no. AC3 is not implemented." Findings: Bug `src/data/api.ts:22-30` "Level is sent as a string" / "The API expects an integer, so the PATCH returns 400."; Nit `src/pages/CompetencyPage.tsx:15` "Unused import" / "The import of Badge is unused."; Question `src/unchanged/Caller.tsx:8` "Caller still passes the old prop" / "Caller.tsx passes levelName, which the page no longer reads."

- [ ] **Step 1: Write the failing tests**

```python
def test_parse_anchor_single_line():
    assert parse_anchor("src/a.py:40") == Anchor("src/a.py", 40, 40)

def test_parse_anchor_range():
    assert parse_anchor("src/a.py:40-52") == Anchor("src/a.py", 40, 52)

@pytest.mark.parametrize("bad", ["src/a.py", "src/a.py:", "src/a.py:52-40", "src/a.py:x", ":40", "src/a.py:0"])
def test_parse_anchor_rejects(bad):
    with pytest.raises(ValueError):
        parse_anchor(bad)

def test_load_chapters_reads_synthetic(synthetic):
    chapters = load_chapters(synthetic / "chapters.json")
    assert [c.kind for c in chapters] == ["step", "step", "layer"]
    assert chapters[0].code[0] == CodeRef(Anchor("src/pages/CompetencyPage.tsx", 12, 30), "renders the Add button")
    assert chapters[1].original == "check editing works"

def test_step_chapter_requires_do_and_expect(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"chapters": [{"kind": "step", "title": "S", "code": [], "files": []}]}))
    with pytest.raises(ValueError, match="do"):
        load_chapters(p)

def test_layer_chapter_rejects_do(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"chapters": [{"kind": "layer", "title": "L", "do": "x", "code": [], "files": []}]}))
    with pytest.raises(ValueError, match="layer"):
        load_chapters(p)

def test_load_criteria_rejects_duplicate_ids(tmp_path):
    p = tmp_path / "a.json"
    row = {"id": "AC1", "text": "t", "implemented_at": [], "tested_by": [], "verdict": "Covered"}
    p.write_text(json.dumps({"criteria": [row, row]}))
    with pytest.raises(ValueError, match="AC1"):
        load_criteria(p)

def test_load_findings_rejects_unknown_severity(tmp_path):
    p = tmp_path / "f.json"
    p.write_text(json.dumps({"verdict": "v", "findings": [{"severity": "Critical", "title": "t", "anchor": "a.py:1", "why": "w"}]}))
    with pytest.raises(ValueError, match="Critical"):
        load_findings(p)

def test_changed_files_keeps_gh_order(synthetic):
    assert changed_files(load_pr(synthetic / "pr.json"))[0] == "src/pages/CompetencyPage.tsx"
    assert len(changed_files(load_pr(synthetic / "pr.json"))) == 5

def test_check_placement_passes_for_synthetic(synthetic):
    check_placement(changed_files(load_pr(synthetic / "pr.json")), load_chapters(synthetic / "chapters.json"))

def test_check_placement_reports_missing_duplicate_unknown():
    ch = lambda *paths: Chapter("layer", "L", None, None, None, (), tuple(FileEntry(p, "s") for p in paths))
    with pytest.raises(PlacementError) as e:
        check_placement(["a.py", "b.py", "c.py"], [ch("a.py", "b.py"), ch("a.py", "z.py")])
    assert (e.value.missing, e.value.duplicated, e.value.unknown) == (["c.py"], ["a.py"], ["z.py"])
    assert "c.py" in str(e.value) and "z.py" in str(e.value)

def test_check_placement_requires_deleted_files():
    ch = Chapter("layer", "L", None, None, None, (), (FileEntry("a.py", "s"),))
    with pytest.raises(PlacementError) as e:
        check_placement(["a.py", "src/old/Legacy.tsx"], [ch])
    assert e.value.missing == ["src/old/Legacy.tsx"]
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `source ~/.virtualenvs/tutor/bin/activate && cd SKILL_DIR && python -m pytest scripts/tests/test_guide_inputs.py -v`
Expected: collection error, `ModuleNotFoundError: No module named 'guide_inputs'`.

- [ ] **Step 3: Implement `guide_inputs.py`**

Use the signatures from Interfaces. Anchors match `^(.+):(\d+)(?:-(\d+))?$`, with `1 <= start <= end`. Loaders raise `ValueError` naming the offending field or value. Each module and public function gets a short docstring stating its contract.

- [ ] **Step 4: Run the tests and confirm they pass**

Same command. Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/prepare-pr-review/scripts/guide_inputs.py .claude/skills/prepare-pr-review/scripts/tests/conftest.py .claude/skills/prepare-pr-review/scripts/tests/test_guide_inputs.py .claude/skills/prepare-pr-review/testdata/synthetic
git commit -m "ai: add prepare-pr-review input loaders and placement check"
```

---

### Task 3: Attach criteria and findings to chapters, and compute the gaps

**Files:**
- Create: `SKILL_DIR/scripts/guide_mapping.py`
- Test: `SKILL_DIR/scripts/tests/test_guide_mapping.py`

**Interfaces:**
- Consumes: everything from `guide_inputs`.
- Produces:
  - `is_test_path(path: str) -> bool`
  - `FindingPlacement(by_chapter: list[list[Finding]], outside: list[Finding])`, `assign_findings(findings, chapters, changed: list[str]) -> FindingPlacement`. A finding on a changed file goes to the first chapter with a code ref that overlaps its anchor (same path, intersecting line range), and failing that, to the chapter whose `files` hold its path. A finding whose path is not a changed file goes to `outside`. Each list is sorted by `SEVERITIES` order, then path, then start line.
  - `criteria_by_chapter(criteria, chapters) -> list[list[Criterion]]`. A criterion belongs to every chapter with a code ref that overlaps one of its anchors (same path, intersecting line range). A criterion that overlaps no code ref anywhere belongs to the chapter whose `files` hold its first anchor whose path is placed. Order follows `criteria`.
  - `ac_tags_for_file(criteria, path: str) -> str`, for example `"AC1 L5-L20, AC2 L22-L30"`; single lines render as `L15`; `""` when there is none.
  - `Gaps(unimplemented: list[Criterion], unmatched_files: list[str])`, `find_gaps(criteria, changed: list[str]) -> Gaps`. `unimplemented` holds criteria with no anchor in a changed file. `unmatched_files` holds the changed files, tests excluded, that no criterion anchor names, in `changed` order.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.parametrize("path,expected", [
    ("src/data/api.test.ts", True), ("src/x/__tests__/a.tsx", True), ("tests/test_models.py", True),
    ("pkg/test_views.py", True), ("pkg/views_test.py", True), ("src/a.spec.js", True),
    ("src/__snapshots__/a.snap", True), ("src/latest.py", False), ("src/contest.py", False),
    ("src/pages/CompetencyPage.tsx", False),
])
def test_is_test_path(path, expected):
    assert is_test_path(path) is expected

def test_assign_findings_by_overlap(inputs):
    placed = assign_findings(inputs.findings, inputs.chapters, inputs.changed)
    assert [f.severity for f in placed.by_chapter[0]] == ["Nit"]
    assert [f.severity for f in placed.by_chapter[1]] == ["Bug"]
    assert placed.by_chapter[2] == []

def test_assign_findings_fall_back_to_file_placement(inputs):
    f = Finding("Gap", "No down migration", Anchor("migrations/0002_add_level.py", 1, 1), "w")
    placed = assign_findings([f], inputs.chapters, inputs.changed)
    assert placed.by_chapter[2] == [f]

def test_findings_outside_changed_files(inputs):
    placed = assign_findings(inputs.findings, inputs.chapters, inputs.changed)
    assert [f.anchor.path for f in placed.outside] == ["src/unchanged/Caller.tsx"]

def test_criteria_by_overlap(inputs):
    ids = [[c.id for c in row] for row in criteria_by_chapter(inputs.criteria, inputs.chapters)]
    assert ids == [["AC1"], ["AC2"], []]

def test_criteria_fall_back_to_file_placement(inputs):
    lone = Criterion("AC9", "t", (Anchor("migrations/0002_add_level.py", 3, 9),), (), "Covered")
    ids = [[c.id for c in row] for row in criteria_by_chapter([lone], inputs.chapters)]
    assert ids == [[], [], ["AC9"]]

def test_ac_tags_for_file(inputs):
    assert ac_tags_for_file(inputs.criteria, "src/data/api.ts") == "AC1 L5-L20, AC2 L22-L30"
    assert ac_tags_for_file(inputs.criteria, "src/old/Legacy.tsx") == ""

def test_find_gaps(inputs):
    gaps = find_gaps(inputs.criteria, inputs.changed)
    assert [c.id for c in gaps.unimplemented] == ["AC3"]
    assert gaps.unmatched_files == ["migrations/0002_add_level.py", "src/old/Legacy.tsx"]
```

Add an `inputs` fixture to `conftest.py` that loads the synthetic fixtures into a `SimpleNamespace(pr, changed, chapters, criteria, verdict, findings)`.

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `... python -m pytest scripts/tests/test_guide_mapping.py -v`. Expected: `ModuleNotFoundError: No module named 'guide_mapping'`.

- [ ] **Step 3: Implement `guide_mapping.py`**

`is_test_path` is true when any path segment is `tests` or `__tests__` or `__snapshots__`, or when the file name matches `test_*.py`, `*_test.py`, `*.test.*`, or `*.spec.*`.

- [ ] **Step 4: Run the tests and confirm they pass**

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/prepare-pr-review/scripts/guide_mapping.py .claude/skills/prepare-pr-review/scripts/tests/test_guide_mapping.py .claude/skills/prepare-pr-review/scripts/tests/conftest.py
git commit -m "ai: map criteria and findings to prepare-pr-review chapters"
```

---

### Task 4: Render chapter text and the change map

**Files:**
- Create: `SKILL_DIR/scripts/guide_render.py`
- Test: `SKILL_DIR/scripts/tests/test_guide_render.py`

**Interfaces:**
- Consumes: `guide_inputs`, `guide_mapping`.
- Produces:
  - `CALLOUT_BY_SEVERITY = {"Bug": "WARNING", "Gap": "WARNING", "Question": "IMPORTANT", "Suggestion": "NOTE", "Nit": "NOTE"}`
  - `one_line(text: str) -> str` (collapses whitespace runs, newlines included, to single spaces, and strips the ends)
  - `code_ref(anchor: Anchor) -> str`, for example ``"`src/a.py` L40-L52"`` or ``"`src/a.py` L15"``
  - `render_finding(f: Finding) -> str`, for example ``"> [!WARNING] Bug: Level is sent as a string. The API expects an integer, so the PATCH returns 400. `src/data/api.ts` L22-L30"``
  - `render_file_summary(entry: FileEntry, criteria) -> str`, which is `one_line(summary)` plus `" " + tags + "."` when there are tags. For example: `"Adds the create and patch calls. AC1 L5-L20, AC2 L22-L30."`
  - `render_overview(chapter, *, criteria: list[Criterion], findings: list[Finding], first_section_by_path: dict[str, int], this_section: int) -> str`
  - `render_before_you_start(*, verdict: str, gaps: Gaps, outside: list[Finding], change_map_note: str | None) -> str`
  - `render_change_map(chapters) -> str` (Mermaid source)

Exact text of a step overview, blocks separated by one blank line and omitted when empty:

```
**Do:** <do>
**Expect:** <expect>
Sharpened from the PR. Author's wording: "<original>"

**Covers:** AC1 "<text>". AC2 "<text>".

<one render_finding line per finding, each its own block>

**Code, in the order it runs:**
- <code_ref>: <role>.
- <code_ref>: <role>. First read in chapter N.
```

The "Sharpened" line appears only when `original` is set. The "First read in" suffix appears when `first_section_by_path[path] != this_section`, with N = `first_section_by_path[path]`. A layer overview is the same without the **Do**, **Expect**, and Sharpened lines; its code list is omitted when it has no code refs. `render_before_you_start` emits, in order: `**Review verdict:** <verdict>`; `**Acceptance criteria with no code in this PR:**` with `- AC3 "<text>"` bullets, or `- None.`; `**Changed files no acceptance criterion points at:**` with ``- `<path>` `` bullets, or `- None.`; `**Findings outside the changed files:**` followed by `render_finding` lines, with the heading omitted when there are none; then `change_map_note` when it is not `None`.

The change map starts with `flowchart LR`. It has one node `c<i>` per chapter, labeled with the chapter title, and one node `f<j>` per distinct path in code refs and files, labeled with the path. There is one edge `c<i> --> f<j>` per distinct (chapter, path) pair, and no `click` lines. Labels are wrapped in `"..."`, with `"` replaced by `#quot;`.

- [ ] **Step 1: Write the failing tests**

```python
def test_code_ref_range():
    assert code_ref(Anchor("src/a.py", 40, 52)) == "`src/a.py` L40-L52"

def test_code_ref_single():
    assert code_ref(Anchor("src/a.py", 15, 15)) == "`src/a.py` L15"

@pytest.mark.parametrize("sev,kind", [("Bug", "WARNING"), ("Gap", "WARNING"), ("Question", "IMPORTANT"), ("Suggestion", "NOTE"), ("Nit", "NOTE")])
def test_finding_callout_kind(sev, kind):
    assert render_finding(Finding(sev, "T", Anchor("a.py", 1, 1), "W")).startswith(f"> [!{kind}] {sev}: T. W ")

def test_finding_collapses_newlines():
    line = render_finding(Finding("Bug", "Two\nlines", Anchor("a.py", 1, 1), "Why\n> quoted"))
    assert "\n" not in line and "Two lines" in line

def test_step_overview_order(inputs):
    crit = criteria_by_chapter(inputs.criteria, inputs.chapters)
    text = render_overview(inputs.chapters[0], criteria=crit[0], findings=inputs.findings[:2], first_section_by_path={"src/pages/CompetencyPage.tsx": 2, "src/data/api.ts": 2}, this_section=2)
    marks = ["**Do:**", "**Expect:**", "**Covers:**", "> [!WARNING] Bug:", "> [!NOTE] Nit:", "**Code, in the order it runs:**"]
    assert [text.index(m) for m in marks] == sorted(text.index(m) for m in marks)
    assert text.count('AC1 "An author can add a competency"') == 1
    assert "- `src/pages/CompetencyPage.tsx` L12-L30: renders the Add button." in text

def test_sharpened_step_and_first_read(inputs):
    text = render_overview(inputs.chapters[1], criteria=[], findings=[], first_section_by_path={"src/data/api.ts": 2, "src/pages/CompetencyPage.tsx": 2}, this_section=3)
    assert "Sharpened from the PR. Author's wording: \"check editing works\"" in text
    assert "patches the level. First read in chapter 2." in text

def test_file_summary_with_tags(inputs):
    assert render_file_summary(FileEntry("src/data/api.ts", "Adds the create and patch calls."), inputs.criteria) == "Adds the create and patch calls. AC1 L5-L20, AC2 L22-L30."

def test_before_you_start_lists_outside_findings(inputs):
    gaps = find_gaps(inputs.criteria, inputs.changed)
    outside = assign_findings(inputs.findings, inputs.chapters, inputs.changed).outside
    text = render_before_you_start(verdict=inputs.verdict, gaps=gaps, outside=outside, change_map_note=None)
    assert text.startswith("**Review verdict:** Ready to merge: no.")
    assert '- AC3 "Deleting a competency asks for confirmation"' in text
    assert "- `migrations/0002_add_level.py`" in text
    assert "> [!IMPORTANT] Question: Caller still passes the old prop." in text

def test_change_map_structure(inputs):
    src = render_change_map(inputs.chapters)
    assert src.splitlines()[0] == "flowchart LR"
    assert "click " not in src
    for title in [c.title for c in inputs.chapters]:
        assert f'"{title}"' in src
    for path in inputs.changed:
        assert f'"{path}"' in src
    assert src.count(" --> ") == 7

def test_change_map_escapes_quotes():
    ch = Chapter("layer", 'Say "hi"', None, None, None, (), (FileEntry("a.py", "s"),))
    assert '"Say #quot;hi#quot;"' in render_change_map([ch])
```

The 7 edges are: chapter 1 to `CompetencyPage.tsx`, `api.ts`, and `api.test.ts`; chapter 2 to `api.ts` and `CompetencyPage.tsx`; chapter 3 to the migration and `Legacy.tsx`.

- [ ] **Step 2: Run the tests and confirm they fail** (`ModuleNotFoundError: No module named 'guide_render'`)
- [ ] **Step 3: Implement `guide_render.py`**, applying `one_line` to every piece of free text it emits.
- [ ] **Step 4: Run the tests and confirm they pass**
- [ ] **Step 5: Commit**

```bash
git add .claude/skills/prepare-pr-review/scripts/guide_render.py .claude/skills/prepare-pr-review/scripts/tests/test_guide_render.py
git commit -m "ai: render prepare-pr-review chapter text and change map"
```

---

### Task 5: Compose and write the saved guide

**Files:**
- Create: `SKILL_DIR/scripts/compose_guide.py`
- Test: `SKILL_DIR/scripts/tests/test_compose_guide.py`

**Interfaces:**
- Consumes: Tasks 2 to 4. Task 1 showed that an empty "Before you start" section renders and that `guide.overview` does not, which fixes steps 3 and 4 below.
- Produces:
  - `TESTED_PLANNOTATOR_VERSION = "0.28.27"`
  - `canonical_pr_url(url: str) -> str` (`https://github.com/<owner>/<repo>/pull/<n>`; raises `ValueError` for anything else)
  - `repo_key_from_pr_url(url: str) -> str`, `make_guide_id(title: str, now_ms: int) -> str`, `data_dir() -> Path`
  - `version_warning(version_output: str | None) -> str | None`
  - `ComposeResult(guide_path: Path, label: str, change_map_path: Path, warnings: list[str])`
  - `compose(artifacts: Path, *, data_dir: Path, now_ms: int, today: str, version_output: str | None) -> ComposeResult`
  - `main(argv: list[str] | None = None) -> int`, with CLI `python3 compose_guide.py --artifacts DIR [--data-dir DIR]`

`compose` reads `pr.json`, `chapters.json`, `criteria.json`, and `findings.json` from `artifacts`, then:
1. Runs `check_placement`.
2. Writes `artifacts/change-map.mmd`.
3. Builds the sections. "Before you start" comes first with `diffs: []`, and the chapters follow, numbered from 2. Each chapter's `diffs` are `{"file": path, "summary": render_file_summary(...)}`.
4. Builds the envelope: label `f"PR #{n} prepared {today}"`, title `f"PR #{n}: {pr title}"`, intent `f"{pr title}. Prepared on {today}: {chapter count} chapters, {finding count} findings."`, `headSha` = `headRefOid`, `prUrl` = the canonical URL, and `reviewed` all false. It sets no `guide.overview`. The `change_map_note` passed to `render_before_you_start` is `"Change map: <absolute path of change-map.mmd>. Open it with plannotator annotate."`.
5. Writes `<data_dir>/guides/<repo-key>/<id>.json` atomically (write a temporary file in the same directory, then `os.replace`). It also writes a copy to `artifacts/guide-envelope.json`.

`main` runs `plannotator --version` through `subprocess` (`None` on `FileNotFoundError`), uses `datetime.now()`, prints the guide path, the label, the change map path, and the warnings, and returns 0. On `PlacementError` or `ValueError`, it prints the message to stderr and returns 1.

- [ ] **Step 1: Write the failing tests**

```python
BASE = "https://github.com/openedx/frontend-app-authoring/pull/123"

@pytest.mark.parametrize("url", [BASE, BASE + "/", BASE + "/files", BASE + "#discussion_r1", "http://github.com/openedx/frontend-app-authoring/pull/123"])
def test_repo_key_from_url_variants(url):
    assert repo_key_from_pr_url(url) == "github.com__openedx__frontend-app-authoring"

def test_canonical_pr_url():
    assert canonical_pr_url(BASE + "/files") == BASE
    with pytest.raises(ValueError):
        canonical_pr_url("https://github.com/openedx/x/issues/5")

def test_make_guide_id():
    assert make_guide_id("PR #123: Add a Competency!", 1761200000000) == "1761200000000-pr-123-add-a-competency"
    long_id = make_guide_id("x " * 100, 1)
    assert len(long_id.split("-", 1)[1]) <= 60 and not long_id.endswith("-")

def test_version_warning():
    assert version_warning("plannotator 0.28.27") is None
    assert "0.29.0" in version_warning("plannotator 0.29.0") and "0.28.27" in version_warning("plannotator 0.29.0")
    assert "not found" in version_warning(None)

def test_compose_end_to_end(tmp_path, synthetic):
    art = tmp_path / "art"; shutil.copytree(synthetic, art)
    res = compose(art, data_dir=tmp_path / "pn", now_ms=1761200000000, today="2026-10-23", version_output="plannotator 0.28.27")
    env = json.loads(res.guide_path.read_text())
    assert res.guide_path.parent == tmp_path / "pn" / "guides" / "github.com__openedx__frontend-app-authoring"
    assert env["version"] == 1 and env["label"] == "PR #123 prepared 2026-10-23" and env["headSha"] == "abc123"
    assert env["prUrl"] == BASE and env["reviewed"] == [False] * len(env["guide"]["sections"])
    placed = [d["file"] for s in env["guide"]["sections"] for d in s["diffs"]]
    assert sorted(placed) == sorted(changed_files(load_pr(art / "pr.json")))
    assert (art / "change-map.mmd").read_text().startswith("flowchart LR")
    assert res.warnings == []
    assert not list(res.guide_path.parent.glob("*.tmp"))

def test_main_fails_on_unplaced_file(tmp_path, synthetic, capsys):
    art = tmp_path / "art"; shutil.copytree(synthetic, art)
    data = json.loads((art / "chapters.json").read_text())
    data["chapters"][2]["files"] = data["chapters"][2]["files"][:1]
    (art / "chapters.json").write_text(json.dumps(data))
    assert main(["--artifacts", str(art), "--data-dir", str(tmp_path / "pn")]) == 1
    assert "src/old/Legacy.tsx" in capsys.readouterr().err
```

Also assert `env["guide"]["sections"][0]["title"] == "Before you start"`, `env["guide"]["sections"][0]["diffs"] == []`, `"overview" not in env["guide"]`, and that the "Before you start" overview contains `"Change map: "` followed by the absolute path of `change-map.mmd`.

- [ ] **Step 2: Run the tests and confirm they fail** (`ModuleNotFoundError: No module named 'compose_guide'`)
- [ ] **Step 3: Implement `compose_guide.py`**
- [ ] **Step 4: Run the full suite and confirm it passes**: `... python -m pytest scripts/tests -v`
- [ ] **Step 5: Smoke-run the CLI against a temporary data dir**

Run: `python3 SKILL_DIR/scripts/compose_guide.py --artifacts <copy of testdata/synthetic> --data-dir <tmp>`. Expected: exit 0, and the printed guide path exists.

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/prepare-pr-review/scripts/compose_guide.py .claude/skills/prepare-pr-review/scripts/tests/test_compose_guide.py
git commit -m "ai: compose and write the prepare-pr-review saved guide"
```

---

### Task 6: Coverage check

**Files:**
- Create: `SKILL_DIR/scripts/coverage_check.py`
- Test: `SKILL_DIR/scripts/tests/test_coverage_check.py`

**Interfaces:**
- Consumes: `guide_inputs.load_pr`, `guide_inputs.changed_files`, `compose_guide.canonical_pr_url`, `compose_guide.data_dir`. Task 1's recorded URL form: canonical, unless Task 1 recorded another form.
- Produces: `progress_key(pr_url: str, scope: str = "layer") -> str`, `record_name(path: str) -> str`, `unviewed_files(changed: list[str], progress_dir: Path) -> list[str]`, and `main(argv: list[str] | None = None) -> int`, with CLI `python3 coverage_check.py --artifacts DIR [--data-dir DIR]`.

A file counts as viewed when its record exists, parses, has `v == 1`, its `path` equals the file, and `viewed` is true. `main` prints either `All <n> changed files are marked viewed.` or `Not marked viewed (<k> of <n>):` followed by one `- <path>` line per file. It then prints the line `A file changed after you marked it still counts as viewed here.` and returns 0. When the progress directory is missing, it prints `No review progress found for <url> (looked in <dir>).` to stderr and returns 2.

- [ ] **Step 1: Write the failing tests**

```python
def test_progress_key_matches_plannotator():
    expected = hashlib.sha256(b'["pr","https://github.com/o/r/pull/1","layer"]').hexdigest()
    assert progress_key("https://github.com/o/r/pull/1") == expected

def test_record_name():
    assert record_name("a.py") == hashlib.sha256(b"a.py").hexdigest() + ".json"

def write_record(d, path, viewed, stored_path=None):
    d.mkdir(parents=True, exist_ok=True)
    (d / record_name(path)).write_text(json.dumps({"v": 1, "path": stored_path or path, "fingerprint": "f", "viewed": viewed, "suppressed": False}))

def test_unviewed_files(tmp_path):
    write_record(tmp_path, "a.py", True); write_record(tmp_path, "b.py", False)
    assert unviewed_files(["a.py", "b.py", "c.py"], tmp_path) == ["b.py", "c.py"]

def test_ignores_record_for_other_path(tmp_path):
    write_record(tmp_path, "a.py", True, stored_path="x.py")
    assert unviewed_files(["a.py"], tmp_path) == ["a.py"]

def test_main_missing_progress(tmp_path, synthetic, capsys):
    assert main(["--artifacts", str(synthetic), "--data-dir", str(tmp_path)]) == 2
    assert "No review progress found" in capsys.readouterr().err

def test_main_all_viewed(tmp_path, synthetic, capsys):
    d = tmp_path / "review-progress" / progress_key("https://github.com/openedx/frontend-app-authoring/pull/123")
    for p in changed_files(load_pr(synthetic / "pr.json")):
        write_record(d, p, True)
    assert main(["--artifacts", str(synthetic), "--data-dir", str(tmp_path)]) == 0
    assert "All 5 changed files are marked viewed." in capsys.readouterr().out
```

- [ ] **Step 2: Run the tests and confirm they fail**
- [ ] **Step 3: Implement `coverage_check.py`**, computing the key with `json.dumps([...], separators=(",", ":"), ensure_ascii=False)`.
- [ ] **Step 4: Run the tests and confirm they pass**
- [ ] **Step 5: Run it against Task 1's real record**

Run: `python3 SKILL_DIR/scripts/coverage_check.py --artifacts <dir holding testdata/real/pr.json as pr.json>`. Expected: the file Jesper marked in Task 1 is absent from the "Not marked viewed" list.

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/prepare-pr-review/scripts/coverage_check.py .claude/skills/prepare-pr-review/scripts/tests/test_coverage_check.py
git commit -m "ai: add prepare-pr-review coverage check"
```

---

### Task 7: Fallback instructions for Plannotator's built-in guide

**Files:**
- Create: `SKILL_DIR/references/guide-instructions-base.md`
- Create: `SKILL_DIR/scripts/fallback_instructions.py`
- Test: `SKILL_DIR/scripts/tests/test_fallback_instructions.py`

**Interfaces:**
- Consumes: `load_chapters`, `load_criteria`, `compose_guide.data_dir`.
- Produces: `LIMIT = 2000`, `compose_instructions(base: str, steps: list[str], criteria: list[tuple[str, str]], limit: int = LIMIT) -> str`, and `main(argv: list[str] | None = None) -> int`, with CLI `python3 fallback_instructions.py --artifacts DIR [--data-dir DIR]`. `main` writes `<data-dir>/guide-instructions.md` and prints its path. Steps are the step chapters' `title: do` strings, in order.

`guide-instructions-base.md` (at most 900 characters, plain sentences) tells the guide agent to: order chapters by the manual testing steps listed after it; put each step's code in the order it runs; place leftover code after the steps in this order (docs and ADRs, models and migrations, API, REST views and serializers, frontend data layer, components, styles, remaining tests); place every changed file in a chapter and leave none unplaced; and tag file summaries with the acceptance criterion ids listed after it.

The output is `base`, a blank line, `Manual testing steps:` with `1. <step>` lines, a blank line, and `Acceptance criteria:` with `AC1: <text>` lines. When it is over `limit`, shorten in this order until it fits: each criterion text to 100 chars, then each step to 150 chars, then criteria to ids only, then cut at `limit - 1` and append `…`.

- [ ] **Step 1: Write the failing tests**

```python
def test_base_is_short():
    assert len((SKILL_DIR / "references" / "guide-instructions-base.md").read_text()) <= 900

def test_short_inputs_kept_in_order():
    out = compose_instructions("BASE", ["Step 1: Add", "Step 2: Edit"], [("AC1", "Add works")])
    assert out.startswith("BASE\n") and out.index("1. Step 1: Add") < out.index("2. Step 2: Edit")
    assert "AC1: Add works" in out

def test_long_inputs_fit_limit():
    out = compose_instructions("B" * 900, ["s" * 300] * 30, [(f"AC{i}", "t" * 300) for i in range(20)])
    assert len(out) <= 2000 and out.startswith("B" * 900)

def test_main_writes_file(tmp_path, synthetic):
    assert main(["--artifacts", str(synthetic), "--data-dir", str(tmp_path)]) == 0
    text = (tmp_path / "guide-instructions.md").read_text()
    assert len(text) <= 2000 and "Step 1: Add a competency" in text
```

- [ ] **Step 2: Run the tests and confirm they fail**
- [ ] **Step 3: Write the base file and implement `fallback_instructions.py`**
- [ ] **Step 4: Run the tests and confirm they pass**
- [ ] **Step 5: Commit**

```bash
git add .claude/skills/prepare-pr-review/references/guide-instructions-base.md .claude/skills/prepare-pr-review/scripts/fallback_instructions.py .claude/skills/prepare-pr-review/scripts/tests/test_fallback_instructions.py
git commit -m "ai: add prepare-pr-review fallback guide instructions"
```

---

### Task 8: The mapper brief

**Files:**
- Create: `SKILL_DIR/references/mapper-brief.md`

**Interfaces:**
- Consumes: the `chapters.json` format from Task 2.
- Produces: the brief that SKILL.md (Task 9) hands to the mapper sub-agent, with placeholders `{pr_url}`, `{repo_clone}`, `{base_repo_url}`, `{pr_number}`, `{head_sha}`, `{artifacts}`, `{testing_steps}`, and `{criteria_text}`.

The brief tells a `general-purpose` Sonnet sub-agent, with a budget of 40 tool calls, to:
- Create a temporary worktree: `git -C {repo_clone} fetch {base_repo_url} pull/{pr_number}/head`, then `git -C {repo_clone} worktree add --detach <tmp> {head_sha}`. Remove it with `git worktree remove --force` when done, even after an error. Never touch the clone's own checkout.
- For each testing step, trace the changed code that step runs, in execution order: entry point, UI, data layer, API, view, model. Record a code ref (`path:start-end`, role in under 10 words) only for changed lines, read at the head SHA.
- Sharpen a vague step into a concrete one (page or URL, action, expected result) from the code, and put the author's wording in `original`. Keep a usable step as written, with `original: null`.
- Place every changed file from `gh pr view {pr_url} --json files` exactly once. A file goes in the first step that runs it. A test file goes in the step whose behavior it tests, after the code. Deleted files and code that no step runs go in layer chapters, in the design's layer order.
- Write `{artifacts}/chapters.json`, then run `python3 SKILL_DIR/scripts/guide_inputs.py --check {artifacts}`. Add that `--check` entry point to `guide_inputs.py` in this task: it loads `pr.json` and `chapters.json` and runs `check_placement`, with exit 0 when placement is clean and exit 1 printing the `PlacementError` when it isn't. Fix the file until the check exits 0.
- Never dispatch. Return "Needs research" items for anything it cannot do. Return the path and one line per chapter.

- [ ] **Step 1: Write the failing test for `--check`**

```python
def test_check_cli(tmp_path, synthetic):
    art = tmp_path / "a"; shutil.copytree(synthetic, art)
    assert guide_inputs.main(["--check", str(art)]) == 0
    data = json.loads((art / "chapters.json").read_text()); data["chapters"][2]["files"] = []
    (art / "chapters.json").write_text(json.dumps(data))
    assert guide_inputs.main(["--check", str(art)]) == 1
```

- [ ] **Step 2: Run it and confirm it fails, implement `main`, and run it again to confirm it passes**
- [ ] **Step 3: Write `references/mapper-brief.md`**
- [ ] **Step 4 (orchestrator): Live check on Task 1's PR**

Dispatch the mapper (`general-purpose`, `model: sonnet`) with the brief filled in for Task 1's PR and `{artifacts}` = `/Users/jesperhodge/openedx/pr-reviews/<repo>-<n>/` (with `pr.json` copied in). Expected: `guide_inputs.py --check` exits 0, every step chapter has at least one code ref, and the temporary worktree is gone (`git -C <clone> worktree list` shows no extra entry). Fix the brief and rerun if any check fails.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/prepare-pr-review/references/mapper-brief.md .claude/skills/prepare-pr-review/scripts/guide_inputs.py .claude/skills/prepare-pr-review/scripts/tests/test_guide_inputs.py
git commit -m "ai: add prepare-pr-review mapper brief and placement check CLI"
```

---

### Task 9: SKILL.md and README entry

**Files:**
- Create: `SKILL_DIR/SKILL.md`
- Create: `SKILL_DIR/testdata/real/sample-review-3246.md`: a short review file for Task 1's PR in `code-review-openedx`'s output format (verdict, an acceptance-criteria table with "implemented at" anchors, findings by severity with `path:line` anchors), whose first line says it is a sample written to test this skill and not a real review. The orchestrator's scenarios use it.
- Modify: `CFG/README.md` (the skills list near line 20: add one line for `prepare-pr-review`)

**Interfaces:**
- Consumes: every script CLI above, the brief, and the JSON formats from Task 2.

Write it with `superpowers:writing-skills`. Its baseline (without the skill) and verification (with the skill) scenarios are dispatches, so they are orchestrator steps.

The frontmatter `description` is: "Use when asked to prepare a pull request for a human line-by-line review in Plannotator, or when the user runs /prepare-pr-review with a PR URL. Reads an existing code review markdown file (asking for its path when none is given), maps the PR's manual testing steps to the code they run, and opens a guided walkthrough in Plannotator. Never posts to GitHub."

The body covers the design's workflow Steps 1 to 8 and the fallback, with these exact decisions:
- **Artifacts:** `/Users/jesperhodge/openedx/pr-reviews/<repo>-<n>/`. Step 1 writes `pr.json` with the `gh pr view` command from Task 1, and one `issue-<n>.json` per linked issue (`gh issue view <n> --repo <owner/repo> --json number,title,body,updatedAt`).
- **Testing section:** the three outcomes from the design. The stop message includes a draft comment for the author and states that the skill does not post it.
- **Review file:** the skill never runs a code review. It takes the review markdown file's path from the command (`/prepare-pr-review <PR URL> [review file]`). When none is given, it asks Jesper for the path and waits, which is the skill's only question. It checks that the file exists and names this PR (its number, URL, or head SHA), and asks again if not.
- **Clone:** `/Users/jesperhodge/openedx/<repo-name>`. When it is missing, run `gh repo clone <base repo> <artifacts>/clone`.
- **Mapper:** dispatch it with `run_in_background: true` before reading the review file, as `general-purpose` with `model: sonnet`. Fill in every placeholder of `references/mapper-brief.md`, including `{skill_dir}`, with plain string replacement, never `str.format`, because the brief's JSON example has literal braces. `{base_repo_url}` is `https://github.com/<owner>/<repo>.git` of the PR's base repository.
- **Reading the review file:** copy it to `review.md` in the artifacts folder. Write `criteria.json` from its acceptance-criteria table, numbering criteria AC1 to ACn across all linked issues and widening single-line anchors to the enclosing function or block at the head SHA. Write `findings.json` with its findings and its verdict line. Handle a file without a criteria table, findings without a location or severity, and a missing verdict as the design's Step 3 says. Each finding's `why` is one full sentence ending in a period. Code-ref roles and finding titles carry no trailing period.
- **Compose:** `python3 SKILL_DIR/scripts/compose_guide.py --artifacts <dir>`. On exit 1, show the error and stop. Show any version warning and offer the fallback.
- **Launch:** call the `plannotator` tool with `{"action": "review", "target": "<canonical PR URL>"}` and end the turn after the summary message. The message holds: the guide label to pick, the change map path, the component tree file path when the review file names one, the AC gap list, any "Findings without a location", and the verdict line. Without the tool, run `plannotator review <url>` with `run_in_background: true` and `timeout: 7200000`, and say that Ask AI in the browser lacks the workspace config.
- **Ask AI questions:** answer from `review.md`, the issues, and the code at the head SHA, citing `file:line`.
- **"check coverage":** `python3 SKILL_DIR/scripts/coverage_check.py --artifacts <dir>`, and relay its output.
- **Fallback:** `python3 SKILL_DIR/scripts/fallback_instructions.py --artifacts <dir>`, then tell Jesper to click Guide and generate.
- **Rules:** never post to GitHub, never use Plannotator's external-annotations API, never change the PR, and only the top-level session dispatches.

- [ ] **Step 1 (orchestrator): Baseline**

Dispatch a `general-purpose` Sonnet sub-agent without the skill, with: "Prepare <Task 1 PR URL> for my line-by-line review in Plannotator, with chapters following the manual testing steps." Give it the path of a review file for that PR. Record where it goes wrong, for example: it posts, it uses annotations, it runs its own review, it misplaces files, or it ignores the review file.

- [ ] **Step 2: Write `SKILL.md` and the README line**
- [ ] **Step 3 (orchestrator): Verification scenario**

Dispatch a fresh `general-purpose` Sonnet sub-agent with the skill path and the same prompt, told to stop before the launch and to report the plan of action and the commands it would run. Expected: it follows Steps 1 to 6 with the exact commands, and none of the baseline failures recur. Revise `SKILL.md` until it does.

- [ ] **Step 4: Run the full test suite**: `... python -m pytest scripts/tests -v`. Expected: all pass.
- [ ] **Step 5: Commit**

```bash
git add .claude/skills/prepare-pr-review/SKILL.md README.md
git commit -m "ai: add prepare-pr-review skill"
```

---

### Task 10: End-to-end run with Jesper

**Files:**
- Modify: `CFG/.claude/plans/2026-10-23-prepare-pr-review-design.md` (status line, and any facts the run corrects)

- [ ] **Step 1 (orchestrator): Ask Jesper to run the skill on a real PR**

Jesper runs `/prepare-pr-review <url> <review file>` from a terminal Claude Code session in `/Users/jesperhodge/openedx`, on a PR of their choice that has testing instructions and an existing review markdown file, and works through Task 1's checklist items 1 to 9 against the real guide.

- [ ] **Step 2: Fix what the run shows**, going through `superpowers:systematic-debugging` for any failure, with a regression test in the owning script's test file.
- [ ] **Step 3: Set the design's status to "Implemented"**, then commit.

```bash
git add .claude/plans/2026-10-23-prepare-pr-review-design.md
git commit -m "docs: mark prepare-pr-review design implemented"
```

- [ ] **Step 4 (orchestrator): Remind Jesper about the evaluation log**

Per decision 0002, Jesper writes a short human evaluation line in `.claude/ai-output-evaluations/Output-evaluations.md`. Claude does not write that line.
