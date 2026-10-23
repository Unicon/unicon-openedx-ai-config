# prepare-pr-review: design

Date: 2026-10-23, revised 2026-10-24. Owner: Jesper Hodge. Status: draft for approval.

## Purpose

Jesper does a line-by-line human review of pull requests in the Open edX repositories
(`openedx-core`, `edx-platform`, `frontend-app-authoring`, and others), from upstream and from
the team's forks. Reading the lines is not what makes a review slow. The slow parts are working
out where to start, reconstructing what each chunk of the change is for, jumping between files
and docs for context, and matching the ticket's acceptance criteria to the code.

A skill, `prepare-pr-review`, prepares a PR for that human review. It reads a code review that
already exists as a markdown file (typically the output of `backend-code-review` or
`frontend-code-review`, run earlier by Jesper or someone else) and the acceptance criteria (ACs)
of the ticket the PR implements. Then it writes a Plannotator Guided Review: an ordered
walkthrough of the diff, one chapter at a time, each chapter showing the real diff. There is one
chapter per AC, in the ticket's order, followed by chapters for code that serves no AC (edge
cases, tests, refactoring and setup). Every changed code piece carries a short label saying what
it is there for, so Jesper can skim the purpose of each piece at a glance and then read every
line. Jesper reads every line in Plannotator, asks questions about specific lines, and posts
their own comments to GitHub.

The PR on GitHub and its branches never change. The layering exists only inside the review
session. That is what Jesper liked about `make-stacked-pr` (small ordered layers to review)
without its cost (stacked branches that complicate merging).

## Goals

1. One command, `/prepare-pr-review <PR URL> [review file]`, run from a Claude Code session in
   `/Users/jesperhodge/openedx`, prepares any GitHub PR the `gh` CLI can read: upstream
   `openedx/*` PRs and PRs on forks. When the command does not name the review markdown file,
   the skill asks Jesper for its path.
2. The guide is built from the ACs. Each AC gets one chapter, in the ticket's order, holding the
   code that implements it, its edge cases, and its tests. Code that serves no AC goes into
   purpose chapters after the AC chapters: "Edge cases", "Tests", "Refactoring and setup", and
   "Other changes", each present only when it has code.
3. Every changed file appears in exactly one chapter. Nothing is left unplaced.
4. Every changed code piece has exactly one short purpose label: the AC it implements, an edge
   case it handles, the AC a test covers, or a kind of change such as refactor, setup, migration,
   docs, or removal. A label is a few words a reader can skim. It is never commentary.
5. The notes in a chapter's left column follow the diffs on the right: grouped by file in the
   order the chapter shows its files, and by line number within a file. Review findings sit in
   the same order, next to the code they are about.
6. Each AC's text appears exactly as written in the ticket, copied character for character,
   under the AC's most important code piece (its "key piece"), next to that code. When the key
   piece's diff is shown in another chapter, the AC's own chapter repeats the text at its top.
   Everywhere else the AC is a short tag such as `AC2`.
7. Notes are unobtrusive. Plannotator has no collapsible element, so findings and labels are
   plain one-line bullets in the muted left column, with no colored callout boxes.
8. A "Before you start" chapter lists the review's verdict, the ACs with no code in the PR, the
   findings on files the PR did not change, and the path of the change map.
9. A diagram of the change ("change map") shows the chapters and the files each one touches. It
   is a separate `.mmd` file, and the summary message and the "Before you start" chapter give its
   path. When the review file names a component tree file (which `frontend-code-review`
   produces), the summary message gives that path too.
10. Questions Jesper asks on a line in Plannotator (Ask AI) are answered by the Claude Code
    session that ran the skill, which has the full workspace `.claude` config and has already
    read the PR, the tickets, and the review.
11. Before posting, Jesper can ask for a coverage check that lists the changed files they have
    not marked as viewed.
12. It uses Jesper's Claude Code Team seat login. No API key.

## Non-goals

- Running the code review. The review exists before the skill runs, and the skill only reads its
  markdown file.
- Using the PR's manual testing instructions. The guide does not depend on them.
- Changing the PR, its commits, or its branches, or creating any new branches or PRs.
- Changing `code-review-openedx`, `backend-code-review`, `frontend-code-review`, or
  `pr-component-tree`. The skill consumes their output as they produce it today.
- Posting anything to GitHub. Jesper posts their own comments from Plannotator.
- Tracking coverage per hunk or per line. Plannotator tracks per file, and that is the
  granularity of the coverage check.
- Jira or other trackers. Tickets are the GitHub issues linked in the PR.

## Anti-goals

These would make the skill a failure even if it technically works:

- AI-written text that ends up posted to GitHub under Jesper's name. Labels, AC text, and
  findings live in the guide text only, never as Plannotator annotations, because Plannotator
  posts every annotation, including externally added ones, as Jesper's own comments.
- A guide that is harder to read than the diff: long prose, repeated AC text, notes that say
  nothing about purpose, or findings that bury the code. Each note is one line. Each AC's full
  text appears at most twice: next to its key piece, and at the top of its own chapter when the
  key piece's diff is shown elsewhere.
- AC text that is paraphrased, shortened, or reworded. Jesper checks the code against the
  ticket's exact words.
- A guide that silently skips changed code.
- Prep that takes long enough that Jesper would rather start reading on GitHub. Prep runs
  unattended once the ACs are found; Jesper starts it and comes back.

## Facts this design relies on

These come from reading Plannotator's source (version 0.28.28 at HEAD; 0.28.27 is installed)
and from a live check Jesper ran against Plannotator 0.28.27 and PR #3246 of
`openedx/frontend-app-authoring`.

| Fact | Status |
| --- | --- |
| The Claude Code plugin is installed (`plannotator@plannotator`, user scope). It adds `/plannotator-review` and the "mod" that gives a terminal session a `plannotator` tool. | Confirmed on disk |
| The `plannotator` tool returns at once. The reviewer's decision arrives later as a new message, so the session can take other input while the review is open. | Documented; not tested live. `SKILL.md` tells Jesper to use a second session if the first one does not answer. |
| `/Users/jesperhodge/openedx/.claude` and `/Users/jesperhodge/openedx/openedx-core/.claude` are symlinks to the config repo's `.claude`, so a skill on the checked-out branch of the config repo is live in sessions started in `/Users/jesperhodge/openedx`. | Confirmed on disk |
| Local clones live at `/Users/jesperhodge/openedx/<repo-name>`, each with remotes for upstream and Jesper's fork. Remote names differ per clone. | Confirmed on disk |
| Ask AI answers come from Claude with no API key set, so the Team seat login works. Which session answered was not pinned down. | Confirmed live |
| Saved guides live at `~/.plannotator/guides/<repo-key>/<id>.json`. In PR mode the repo key comes from the PR URL, for example `github.com__openedx__frontend-app-authoring`. A guide file written there appears in the Guide screen's list of previous guides and loads. The format is undocumented. | Confirmed live |
| Saved-guide envelope: `{version: 1, savedAt, label, title, headSha, prUrl, guide: {title, intent, sections: [{title, overview, diffs: [{file, summary}]}]}, reviewed: [false, ...]}`. Loading does not validate the file list against the live diff. | Confirmed in code |
| Chapter layout: on windows 768px and wider, a chapter's title and `overview` sit in a sticky left column (36% wide, 440px from 1024px), and the file diffs fill the right column. Below 768px the overview stacks above the diffs. Each `diffs[].summary` renders as one line of small muted text directly above that file's diff, untruncated. | Confirmed in code (`GuideSectionCard.tsx:197-199`, `GuideFileCard.tsx:88-92`) |
| `overview` renders paragraphs, `#` headings (one style), flat `-` bullets, fenced code blocks (line breaks kept), the callouts `[!WARNING]`, `[!IMPORTANT]`, `[!NOTE]`, and inline bold, italic, code, and links. Consecutive non-blank lines join into one paragraph. There is nothing collapsible, no nested or numbered lists, no tables, no plain blockquotes; raw HTML prints as text. `summary` gets inline formatting only. | Confirmed live (callouts, headings, bullets) and in code (`renderMarkdownProse.tsx`, `renderInlineMarkdown.tsx`) |
| `code:` and `chapter:` links render as text and are not clickable in the live review screen. Line and chapter references are plain text. | Confirmed live |
| The live review screen never shows `guide.overview` (text or diagram). | Confirmed live |
| A file can appear in only one section; the first placement wins. A diff reference is a whole file, never a hunk. Each file card shows the whole file diff, every hunk, in one scrollable box. | Confirmed in code |
| No mechanism attaches a never-posted note to a specific diff line: external annotations are posted to GitHub with Jesper's comments, and Code Tour opens as a modal that cannot be loaded from a file. | Confirmed in code |
| Plannotator stores per-file review progress at `~/.plannotator/review-progress/<key>/<sha256(path)>.json` as `{v, path, fingerprint, viewed, suppressed}`, with `key = sha256(json.dumps(["pr", url, "layer"], separators=(",", ":")))` for the canonical URL `https://github.com/<owner>/<repo>/pull/<n>`. | Confirmed live |
| The built-in guide agent reads extra instructions fresh from `~/.plannotator/guide-instructions.md` at each launch, capped at 2,000 characters. | Confirmed in code |
| `code-review-openedx` produces an acceptance-criteria table (criterion quoted, in scope, implemented at `file:line`, tested by, verdict) and findings with a severity and a `path:line` anchor. | Confirmed in the skill file |

## How a review runs, from Jesper's side

1. In a Claude Code terminal session started in `/Users/jesperhodge/openedx` (the VS Code
   integrated terminal is fine), Jesper runs `/prepare-pr-review <PR URL> [review file]`.
2. If the command did not name the review file, the skill asks for its path. It finds the ACs.
   If it finds none, it stops and asks Jesper for them. Otherwise it confirms the PR, the
   tickets, and the ACs in one message and runs unattended. Jesper can leave.
3. When prep finishes, the session has opened the PR in Plannotator and posted a short message:
   the guide's name to pick, the path of the change map, the ACs with no code, and the verdict
   line of the review.
4. In Plannotator, Jesper clicks Guide and picks the prepared guide from the previous-guides
   list. They work through the chapters, one AC at a time: skim the labels in the left column,
   read the AC's text under its key piece, read every line of the diffs, annotate lines, and tick
   the chapter off. For a confusing line they use Ask AI.
5. Before posting, they type "check coverage" in the session. The skill lists changed files not
   yet marked as viewed.
6. They post their annotations from Plannotator as one GitHub review.

## Components

### 1. Skill folder

`.claude/skills/prepare-pr-review/` in the config repo:

- `SKILL.md`: the workflow below.
- `references/mapper-brief.md`: the brief for the mapper sub-agent, which labels every changed
  code piece.
- `references/guide-instructions-base.md`: the stable part of the fallback instructions, well
  under 2,000 characters.
- `scripts/`: Python 3 standard-library scripts. Tests are `pytest` modules in `scripts/tests/`,
  with fixtures in `testdata/`. `fetch_pr.py`, `coverage_check.py`, and the envelope writer in
  `compose_guide.py` stay as they are; the input, mapping, and render modules change with this
  design.

### 2. Workflow inside the skill

**Step 1, pin the PR and find the ACs (top-level session, inline).**

- Fetch the PR with `fetch_pr.py` (all changed files, past `gh`'s 100-file limit). When the
  command did not name the review file, ask Jesper for its path and wait. Check that the file
  exists and names this PR (its number, URL, or head SHA); if not, say so and ask again.
- Find the tickets: the issues GitHub links to the PR, and issue references or URLs in the PR
  description. Read each with `gh issue view`. When a ticket names a parent ticket that holds the
  ACs (for example "Parent: #123", or the child is a task in a parent's checklist), read the
  parent too.
- Decide which ticket's ACs apply, following `code-review-openedx`'s rule. When the PR's own
  ticket has an acceptance-criteria section, use only that ticket's ACs. When it has none and
  points to a parent that has one, use the parent's ACs, narrowed to the ones the child ticket's
  description (and the review's "In scope" column, when there is one) puts this PR on the hook
  for. ACs left out this way get no chapter and no gap entry; the summary message lists them
  under "Criteria set aside", with the reason.
- Split the AC section into ACs, following the team's ticket template
  (`.claude/ticket-template.md`, section 5): one AC per Gherkin `Scenario:` or
  `Scenario Outline:` (with its `Examples:`), running to the line before the next scenario or
  heading; one AC per top-level checkbox item (with its nested lines) for artifact tickets; and,
  for any other form, one AC per top-level list item or paragraph. A `Background:` block is not
  an AC: it is copied once into "Before you start", labeled with its ticket. When a ticket has no
  acceptance-criteria section, its `Scenario:` blocks elsewhere in the body are its ACs. A
  scenario that appears twice is taken once.
- Copy each AC exactly, character for character, keeping its keywords, indentation, and line
  breaks. Number them AC1 to ACn in ticket order and then the order within each ticket. Record
  each AC's source ticket.
- When the review file has an acceptance-criteria table, match its rows to the ticket's ACs by
  content. The ticket's text is what the guide shows; the review contributes its verdict, its
  "tested by" cell, and its "implemented at" anchors (passed to the mapper as hints). Rows whose
  "In scope" cell starts with "no" are listed in the summary message under "Criteria the review
  set aside".
- When neither the tickets (including parents) nor the review file holds any AC: stop. Tell
  Jesper where the skill looked (each ticket and the review file), and ask them to paste the ACs
  or name the ticket that holds them. Nothing else runs until they answer.
- Say in one message what was found (the tickets, the number of ACs and where each came from),
  then continue without waiting.

**Step 2, start the mapper (background dispatch).** Dispatch a `general-purpose` Sonnet
sub-agent, medium-high effort, model passed explicitly, with `references/mapper-brief.md`, the
PR facts, the ACs with their exact text, the review's "implemented at" hints, and the files it
covers. It reads the source at the PR head in a temporary git worktree of the local clone, which
it removes when done (clone location and head fetch as before: `/Users/jesperhodge/openedx/<repo-name>`,
fetched by URL from the base repository with `pull/<n>/head`). The mapper only labels code; it
does not build chapters. It writes:

- **Code pieces.** Every changed line of its files belongs to exactly one code piece. A piece is a
  contiguous changed range that serves one purpose, so one hunk can hold several pieces. Each
  piece has an anchor (`path:start-end`, new-side lines at the head SHA), a list of the ACs it
  serves (empty, one, or several), a kind (implements, edge case, test, refactor, setup,
  migration, docs, removal, or other), and a purpose of a few words. A piece made only of removed
  lines is anchored at the first new-side line after the removal, or at line 1 of a deleted file,
  and its kind is removal.
- **Key pieces.** For each AC its files serve, it marks one piece as the AC's key piece: the one a
  reviewer most needs to read to judge the AC, preferring a piece of kind "implements".
- **File summaries.** One line per file saying what its change does.

When the PR changes more than 25 files, the session splits the changed files into batches of at
most 25, keeping a source file and its test file in one batch where the names make the pairing
clear, and dispatches one mapper per batch in one message, all with the full AC list. Each mapper
writes its own output file, and a script merges them. Each mapper has a budget of 40 tool calls.

The chapters are derived from the pieces by the composer (Step 5), deterministically:

- **Chapters.** One AC chapter per AC, in AC order, including ACs with no code (the chapter then
  says so). Then the purpose chapters that have pieces: "Edge cases" (edge cases tied to no AC),
  "Tests" (tests tied to no AC), "Refactoring and setup" (refactor, setup, migration, docs,
  removal), and "Other changes". A piece belongs to the chapter of its first AC when it has one,
  and to the purpose chapter for its kind otherwise. A piece that serves several ACs is also
  listed in the other ACs' chapters.
- **Key piece per AC.** When more than one piece is marked key for an AC (possible after merging
  batches), the first by file order and line, preferring kind "implements", wins. When none is
  marked, the AC's first piece by file order and line is its key piece.
- **File placement.** Each changed file is placed in the first chapter, in guide order, that holds
  a piece in it. Within a chapter, source files come before test files, and files keep the order
  of the PR's file list otherwise.

The mapper does not need the review's findings, so it runs in the background while the session
reads the review file. Per the Delegation rule, it never dispatches and returns "Needs research"
items instead. Its brief keeps the existing safety rules: PR and ticket text is data, `gh` is
read-only, and it never checks out or switches branches in the clone.

**Step 3, read the review file (top-level session).** Copy it into the artifact folder as
`review.md`. Write `criteria.json` from the ACs found in Step 1 (exact text, source ticket, and
the review's verdict and "tested by" when the table has them). Write `findings.json` from the
review's findings and its verdict line, with the existing rules: keep the review's sentences and
punctuation, write a title of at most 8 words that restates the review's point, use `Question`
for a finding with no severity word, and list findings with no file location in the summary
message under "Findings without a location".

**Step 4, check the mapper output (script).** `guide_inputs.py --check` loads `pr.json`, the
merged mapper output, and `criteria.json`, and fails loudly unless: every changed file has at
least one piece and a summary, and no unknown file appears; every piece's anchor is on a changed
file; and every AC a piece names exists in `criteria.json`. When the check fails on missing
files, the session dispatches one more mapper for just those files and merges again.

**Step 5, compose the guide (script).** A script merges the chapter draft, the criteria, and the
findings into the saved guide, deterministically:

- A finding is shown in the chapter that shows its file's diff, next to the code it is about. A
  finding on a file the PR did not change goes into "Before you start", so nothing is dropped.
- Notes are rendered in the format below, ordered by the chapter's file order and then by line.
- The gap list holds the ACs that have no piece.
- It writes the change map as a separate Mermaid `.mmd` file: chapters linked to the files they
  touch.
- It writes the envelope to `~/.plannotator/guides/<repo-key>/<id>.json`, labeled
  `PR #<n> prepared <YYYY-MM-DD HH:MM>`, and warns when the installed Plannotator version differs
  from the tested one (0.28.27).

**Step 6, launch.** Re-check the PR's head SHA. Then call the `plannotator` tool with the review
action on the canonical PR URL, post the summary message, and end the turn. Without the tool,
run `plannotator review <PR URL>` in the background with a long timeout and say that Ask AI in
the browser lacks the workspace config.

**Step 7, answer questions.** Answer Ask AI questions from the PR, the tickets, the review file,
and the code at the head SHA, citing `file:line`. If no answer arrives while the review is open,
Jesper uses a second session in the same folder.

**Step 8, coverage check (script).** On "check coverage", `coverage_check.py` lists the changed
files not marked viewed.

### 3. Chapter format

An AC chapter's title is `AC<n>: <name>`, where the name is the Gherkin scenario name, or the
first line of the AC cut to 80 characters. Its overview (the left column) is, in this order:

An AC chapter whose files are shown here (AC1 in this example, which shows `src/data/api.ts`):

````
Review verdict: Covered.

### src/data/api.ts
- L5-L20 AC1: posts the new competency
- L22-L30 AC2: patches the level (key piece for AC2)
```
Scenario: Author changes the level
  Given a competency at level 2
  When the author picks level 3
  Then the list shows level 3
```
- L24 Bug: Level is sent as a string. The API expects an integer, so the PATCH returns 400.
- L31-L35 AC2 edge case: rejects an empty level
````

An AC chapter whose code is shown in an earlier chapter (AC2 here):

````
Review verdict: Implemented, untested.

```
Scenario: Author changes the level
  ...
```

### Also in this chapter, diff shown in chapter 2
- src/data/api.ts L22-L30 AC2: patches the level (key piece, 1 finding)
- src/data/api.ts L31-L35 AC2 edge case: rejects an empty level
````

- The verdict line appears only when the review gave one for this AC.
- One `###` heading per file whose diff this chapter shows, in its `diffs` order. Under it, every
  piece and every finding in that file, whichever AC they serve, sorted by start line; a finding
  that starts on the same line as a piece follows it. So the left column labels every line the
  reader sees on the right.
- Piece bullets read `L<range> <label>: <purpose>`. The label is `AC2` for implements,
  `AC2 edge case`, `AC2 test`, `AC2 <kind>` for other kinds, `AC1, AC2 ...` for a piece serving
  several ACs, or the kind alone (`refactor`, `setup`, `migration`, `docs`, `removal`, `other`)
  for pieces with no AC. A key piece adds "(key piece for AC2)".
- An AC's exact text follows its key piece as a fenced code block, next to the code. When the key
  piece's diff is shown in another chapter, the AC's own chapter also shows the text at its top,
  after the verdict line. So an AC's text appears at most twice.
- Finding bullets read `L<range> <Severity>: <title>. <why>`. There are no callout boxes.
- After the files, the pieces that serve this chapter (its AC, or its purpose kinds) but sit in
  files shown in another chapter are listed under one heading per such chapter, with the file
  path in each bullet and "(key piece)" and "(N findings)" markers. Findings are not repeated
  there.
- An AC chapter with no pieces says "No code in this PR implements this AC." and shows the AC's
  exact text in a fenced block.
- Each file's `summary` (the line above its diff) is the mapper's one-line summary, then the AC
  tags of its pieces and its finding count, for example "Adds the PATCH call. AC2, AC3.
  1 finding."
- Purpose chapters use the same note format, without a verdict line or AC text.
- "Before you start" is always the first section, with `diffs: []`: the review's verdict, any
  Gherkin `Background:` blocks (exact text, labeled with their ticket), the ACs with no code,
  findings on unchanged files, and the change map path.

### 4. Fallback: built-in guide

When the saved-guide route does not work (a later Plannotator version breaks it), the skill
offers to write `~/.plannotator/guide-instructions.md` from `references/guide-instructions-base.md`
plus the ACs (exact text, shortened only when the 2,000-character cap forces it). The base text
tells Plannotator's guide agent to build one chapter per AC in order, then the purpose chapters,
and to label each file summary with its ACs. It runs only after Jesper agrees, backs up an
existing file first, and tells Jesper the file applies to every later guide until deleted.
Findings then live only in the review file, not in the guide.

## Where files go

- Skill: `.claude/skills/prepare-pr-review/` in the config repo
  (`/Users/jesperhodge/workspace/unicon-openedx-ai-config`), branch
  `feat/prepare-pr-review-skill`, draft PR Unicon/unicon-openedx-ai-config#63.
- Per-PR artifacts: `/Users/jesperhodge/openedx/pr-reviews/<repo>-<number>/` (`pr.json`, the
  tickets, a copy of the review file, `criteria.json`, `findings.json`, `chapters.json`, the
  change map). This folder is local and not under version control.
- Saved guide: `~/.plannotator/guides/<repo-key>/<id>.json`.

## Verification

- Scripts: test-driven with `pytest` from the `tutor` venv (`source ~/.virtualenvs/tutor/bin/activate`), with `-W error`. Synthetic fixtures change to the AC-based format.
- Mapper brief: a live run on a real PR whose ticket has ACs, checked with `guide_inputs.py --check`
  and read by the controller for label quality.
- `SKILL.md`: with `superpowers:writing-skills`, including a scenario where no AC exists (the
  skill must stop and ask) and one where the review file has no criteria table (the skill must
  take the ACs from the ticket).
- End to end: one real PR with a real review file, run by Jesper.

## Left to the builder

- Script names, CLI arguments, module boundaries, and the exact JSON field names, within the
  shapes this design describes.
- How a fenced block is kept intact when an AC itself contains a line starting with three
  backticks.
- The guide `id` format, within `^[A-Za-z0-9][A-Za-z0-9._-]*$` and at most 160 characters.

## Calls Claude made that Jesper has not confirmed

- The rule that stopped prep when a PR had no usable testing section is gone, together with the
  testing-step chapters.
- An AC's tests and edge cases go in that AC's chapter. Only tests and edge cases tied to no AC go
  into the "Tests" and "Edge cases" chapters.
- A file sits in the first chapter, in guide order, that holds a piece in it. Pieces in that file
  for later chapters are listed in those chapters under "Also in this chapter".
- The guide always shows the ticket's AC text. The review's criteria table only adds its verdict,
  its "tested by" cell, and hints for the mapper.
- An AC section in any form counts as ACs, not only Gherkin; it is copied as written.
- Parent tickets are read when a ticket points to one.
- An AC chapter's first line shows the review's verdict for that AC.
- Every changed line belongs to exactly one piece; the mapper brief states this rule, and no
  script checks it.
- An AC chapter is kept even when no code implements the AC, so the gap is visible in place.
- A piece can serve several ACs. It belongs to its first AC's chapter and is listed in the
  others, so shared code never produces a false "no code" gap.
- Which ticket's ACs apply follows `code-review-openedx`: the PR's own ticket when it has ACs,
  otherwise the parent's ACs narrowed to this PR's scope. ACs out of scope get no chapter.
- An AC whose pieces are all tests or edge cases still gets its text, under its first piece.
- The mapper only labels pieces; the composer derives chapters and file placement. PRs over 25
  changed files are split across several mappers running in parallel.
- AC boundaries follow the team's ticket template: one Gherkin scenario per AC, or one checkbox
  item for artifact tickets. A `Background:` block is shown once in "Before you start".
- The chapter that shows a file's diff lists every piece and finding in that file, whichever AC
  they serve, so every line on the right has its label on the left. An AC chapter whose code is
  shown elsewhere lists its pieces under "Also in this chapter" and repeats the AC text at its
  top, so an AC's text appears at most twice.
