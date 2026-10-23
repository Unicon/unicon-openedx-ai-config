# prepare-pr-review: design

Date: 2026-10-23. Owner: Jesper Hodge. Status: draft for approval.

## Purpose

Jesper does a line-by-line human review of pull requests in the Open edX repositories
(`openedx-core`, `edx-platform`, `frontend-app-authoring`, and others), from upstream and from
the team's forks. Reading the lines is not what makes a review slow. The slow parts are working
out where to start, reconstructing what each chunk of the change is for, jumping between files
and docs for context, and matching the ticket's acceptance criteria to the code.

A new skill, `prepare-pr-review`, prepares a PR for that human review. It runs the existing full
code review, then writes a Plannotator Guided Review (an ordered walkthrough of the diff, one
chapter at a time, each chapter showing the real diff). The chapters follow the PR's manual
testing instructions, so Jesper can do a testing step in the devstack and then read the code
that step runs, in the order it runs. Each chapter shows the acceptance criteria it covers and
the review's findings on its code. Jesper then reads every line in Plannotator, asks questions
about specific lines, and posts their own comments to GitHub.

The PR on GitHub and its branches never change. The layering exists only inside the review
session. That is what Jesper liked about `make-stacked-pr` (small ordered layers to review)
without its cost (stacked branches that complicate merging).

## Goals

1. One command, `/prepare-pr-review <PR URL>`, run from a Claude Code session in
   `/Users/jesperhodge/openedx`, prepares any GitHub PR the `gh` CLI can read: upstream
   `openedx/*` PRs and PRs on forks.
2. The guide's chapters follow the PR's manual testing steps. Each testing-step chapter lists
   the changed code that step runs, in execution order, with the exact line ranges.
   Changed code that no testing step runs (migrations, refactors, settings, unrelated tests)
   goes into chapters after the testing steps, ordered by layer.
3. Every changed file appears in exactly one chapter. Nothing is left unplaced.
4. Each chapter opens with the acceptance criteria it covers, written out in full once, then the
   review findings on its code, then the code. File summaries carry short AC tags with line
   ranges.
5. The guide has a two-way gap list: acceptance criteria that no code implements, and changed
   code that matches no acceptance criterion.
6. A diagram of the change ("change map") shows the testing steps and the files each one runs
   through. It is a separate `.mmd` file, and the summary message and the "Before you start"
   chapter give its path. For frontend PRs, the component tree that `frontend-code-review` already produces is
   also available.
7. Questions Jesper asks on a line in Plannotator (Ask AI) are answered by the Claude Code
   session that ran the skill, which has the full workspace `.claude` config and has already
   read the PR, the tickets, and the review.
8. Before posting, Jesper can ask for a coverage check that lists the changed files they have not
   marked as viewed.
9. It uses Jesper's Claude Code Team seat login. No API key.

## Non-goals

- Changing the PR, its commits, or its branches, or creating any new branches or PRs.
- Changing `code-review-openedx`, `backend-code-review`, `frontend-code-review`, or
  `pr-component-tree`. The new skill consumes their output as they produce it today.
- Posting anything to GitHub. Jesper posts their own comments from Plannotator.
- Tracking coverage per hunk or per line. Plannotator tracks per file, and that is the
  granularity of the coverage check.
- Jira or other trackers. Tickets are the GitHub issues linked in the PR.

## Anti-goals

These would make the skill a failure even if it technically works:

- AI-written text that ends up posted to GitHub under Jesper's name. Findings and AC labels live
  in the guide text only, never as Plannotator annotations, because Plannotator posts every
  annotation, including externally added ones, as Jesper's own comments.
- A guide that is harder to read than the diff: long prose, repeated AC text, or findings that
  bury the code. Each finding is one line plus a code link. Each AC's full text appears once per
  chapter, and everywhere else it is a short tag.
- A guide that silently skips changed code.
- Prep that takes long enough that Jesper would rather start reading on GitHub. Prep runs
  unattended; Jesper starts it and comes back.

## Facts this design relies on

These come from reading Plannotator's docs and source (version 0.28.28 at HEAD; 0.28.27 is
installed). "Confirmed" means stated in docs or seen in code. "Unverified" means nobody has run
it yet. Task 1 of the plan settles every unverified item.

| Fact | Status |
| --- | --- |
| The Claude Code plugin installs with `/plugin marketplace add backnotprop/plannotator`, then `/plugin install plannotator@plannotator`, then a restart. It adds `/plannotator-review`, the plan-review hook, and the "mod" that gives the session a `plannotator` tool. | Confirmed in docs |
| The `plannotator` tool returns at once. The session ends its turn, and the reviewer's decision arrives later as a new message, so the session can take other input while the review is open. | Confirmed in docs and the Plannotator skill. Not tested in Task 1 (item 9). `SKILL.md` tells Jesper to use a second session if the first one does not answer. |
| `/Users/jesperhodge/openedx/.claude` and `/Users/jesperhodge/openedx/openedx-core/.claude` are symlinks to the config repo's `.claude`, so a skill on the checked-out branch of the config repo is live in sessions started in `/Users/jesperhodge/openedx`. | Confirmed on disk |
| Local clones live at `/Users/jesperhodge/openedx/<repo-name>` (for example `openedx-core`, `edx-platform`, `frontend-app-authoring`, `frontend-app-learning`), each with remotes for upstream and Jesper's fork. Remote names differ per clone. | Confirmed on disk |
| With the mod, Ask AI in the review UI is answered by the Claude Code session that opened the review. The mod targets the interactive terminal, so it may not work from the VS Code chat panel. | Ask AI answers come from Claude (Task 1, items 5 and 6). Which session answered was not pinned down. The VS Code chat panel was not tested. |
| Plannotator's own AI features run the local `claude` binary, so they use the Team seat login. | Confirmed in Task 1: Ask AI answered with no API key set. |
| Plannotator's built-in guide agent runs `claude -p --setting-sources user`, which loads only `~/.claude`, never the workspace `.claude`. | Confirmed in code |
| Saved guides live at `~/.plannotator/guides/<repo-key>/<id>.json`. In PR mode the repo key comes from the PR URL, for example `github.com__openedx__frontend-app-authoring`. A guide file written there shows up in the Guide screen's list of previous guides. The format is undocumented. | Confirmed in Task 1: the hand-written guide appeared in the list and loaded. |
| Saved-guide envelope: `{version: 1, savedAt, label, title, headSha, prUrl, guide: {title, intent, sections: [{title, overview, diffs: [{file, summary}]}]}, reviewed: [false, ...]}`. Loading does not validate the file list against the live diff. | Confirmed in code |
| Section overviews render paragraphs, headings, bullets, fenced code, `> [!NOTE]` callouts, inline formatting, and links, including `code:path#L24-L40` line-range links and `chapter:N` links. Tables are probably not rendered. | Callouts, headings, bullets, and inline formatting confirmed in Task 1. Failed in Task 1: `code:` and `chapter:` links render as text and are not clickable in the live review screen, because the review editor passes no link handler to the guide renderer (only the export viewer handles them). Tables not tested. |
| A file can appear in only one section. A diff reference is a whole file, never a hunk. | Confirmed in code |
| A Mermaid diagram is supported only in the top-level `guide.overview.diagram` field of snapshot format v2. Whether a saved guide can carry it is unknown. | Failed in Task 1: the live review screen never shows `guide.overview` (text or diagram), because the review editor never reads it. |
| Plannotator stores per-file review progress at `~/.plannotator/review-progress/<snapshot-key>/<sha256(path)>.json` as `{v, path, fingerprint, viewed, suppressed}`. | Confirmed in Task 1 (item 7): see the item 7 row below. |
| The built-in guide agent reads extra instructions fresh from `~/.plannotator/guide-instructions.md` at each launch, capped at 2,000 characters. | Confirmed in code |
| `code-review-openedx` produces an acceptance-criteria table (criterion quoted, implemented at `file:line`, tested by, verdict) and findings with a severity and a `path:line` anchor. | Confirmed in the skill file |

Results of Task 1, one row per checklist item. Jesper ran the checklist against Plannotator 0.28.27
and PR #3246 of `openedx/frontend-app-authoring`. The controller checked the two failures in
Plannotator's code.

| Item | Result |
| --- | --- |
| 1. The hand-written guide appears in the previous-guides list and renders. | Confirmed in Task 1: it appears and loads. |
| 1 (links). `code:` and `chapter:` links work. | Failed in Task 1: they render as text and are not clickable in the live review screen. The review editor passes no link handler to the guide renderer. The scripts write line and chapter references as plain text, such as `` `src/x/api.py` L40-L52 `` and "first read in chapter 1". |
| 2. Which callout kinds render. | Confirmed in Task 1: `[!WARNING]`, `[!IMPORTANT]`, and `[!NOTE]` single-line callouts render as labeled, tinted boxes. Findings can use any of the three kinds. |
| 3. A section with an empty `diffs` list is allowed. | Confirmed in Task 1: it renders. "Before you start" stays a section, always first, and does not move into `intent`. |
| 4. `guide.overview` with a Mermaid diagram renders from a saved guide. | Failed in Task 1: the live review screen does not show `guide.overview` at all. `EMBED_CHANGE_MAP` is `False`: the change map is always a separate `.mmd` file, and the summary message and "Before you start" give its path. |
| 5. Ask AI is answered by the terminal session, and from the VS Code chat panel. | Partly confirmed in Task 1: answers come from Claude. Which session answered was not pinned down, and the VS Code chat panel was not tested. |
| 6. The Team seat login works for Ask AI. | Confirmed in Task 1: Ask AI answered with no API key set. |
| 7. Review-progress files for this PR. | Confirmed in Task 1: the directory is `~/.plannotator/review-progress/d8098d292f430f6d22d3bf38b84681163d588211d9127df243cb10effda489ea/`, which is `sha256(json.dumps(["pr", url, "layer"], separators=(",", ":")))` for the canonical URL form `https://github.com/<owner>/<repo>/pull/<n>`. It holds a record with `"viewed": true` for `src/course-unit/CourseUnit.tsx`, named by the sha256 of that path. |
| 8. The post dialog posts only Jesper's annotations. | Not tested in Task 1. Ruling: the design never adds annotations, so the dialog can only hold Jesper's own. |
| 9. The `plannotator` tool returns at once, and the session answers "check coverage" while the review is open. | Not tested in Task 1. Ruling: the Plannotator skill documents the tool as non-blocking. `SKILL.md` tells Jesper to use a second session if the first one does not answer. |

## How a review runs, from Jesper's side

1. In a Claude Code terminal session started in `/Users/jesperhodge/openedx` (the VS Code
   integrated terminal is fine), Jesper runs `/prepare-pr-review <PR URL>`.
2. The skill confirms the PR, the linked issues, and the review skill it will use, then runs
   unattended. Jesper can leave.
3. When prep finishes, the session has opened the PR in Plannotator and posted a short message:
   the guide's name to pick, the path of the change map, the AC gap list, and the verdict line
   of the review.
4. In Plannotator, Jesper clicks Guide and picks the prepared guide from the previous-guides
   list. They work through the chapters: do the testing step, read its findings, read the code,
   annotate lines, and tick the chapter off. For a confusing line they use Ask AI.
5. Before posting, they type "check coverage" in the session. The skill lists changed files not
   yet marked as viewed.
6. They post their annotations from Plannotator as one GitHub review.

## Components

### 1. Plannotator plugin

Installed once with the two slash commands above, then Claude Code is restarted. This changes
the user-level `~/.claude`, not the config repo. The CLI binary and the user-level Plannotator
skills are already installed.

### 2. Skill folder

`.claude/skills/prepare-pr-review/` in the config repo:

- `SKILL.md`: the workflow below.
- `references/mapper-brief.md`: the brief for the step-to-code mapping sub-agent.
- `references/guide-instructions-base.md`: the stable part of the fallback instructions (layer
  order and conventions), well under 2,000 characters.
- `scripts/`: Python 3 standard-library scripts. Tests are `pytest` modules in `scripts/tests/`,
  with fixtures in `testdata/`, following the `pr-component-tree` layout.

### 3. Workflow inside the skill

**Step 1, pin the PR (top-level session, inline).** From the PR URL: `gh pr view` for title,
body, base and head SHAs, head repository, and changed files; the linked issues from the body
and from GitHub's linked-issue field. Pick the review skill: `frontend-code-review` for
JavaScript and TypeScript MFE repositories, `backend-code-review` otherwise. Find the testing
instructions section in the PR body and judge whether it is usable:

- **No usable section:** there is no testing section, or it holds no actionable step (only "run
  the tests", "see the ticket", "N/A", or similar). Stop before the review starts and tell
  Jesper, with a short draft comment asking the author to add manual testing instructions.
  Jesper sends it; the skill never posts. Nothing else runs.
- **Vague steps:** the section has steps, but a step leaves out where to go, what to do, or what
  should happen. Continue. The mapper sharpens each vague step from the code into a concrete
  step (the page or URL, the action, the expected result). In the chapter, a sharpened step is
  labeled as sharpened, followed by the author's original wording on one line, so Jesper can
  tell the author's text from Claude's.
- **Usable steps:** continue, and use the steps as written.

Say in one message what was found, then continue without waiting.

**Step 2, start the mapper (one background dispatch).** Dispatch one `general-purpose` Sonnet
sub-agent, medium-high effort, model passed explicitly, with `references/mapper-brief.md`, the
PR facts, and the testing steps. It reads the source at the PR head in a temporary git worktree
of the local clone of that repository, which it removes when done. The clone is
`/Users/jesperhodge/openedx/<repo-name>`, matched by repository name whichever account owns the
PR. The PR head is fetched by URL from the PR's base repository
(`git fetch <base-repo-url> pull/<n>/head`), so no remote needs to exist for a fork. When no
local clone exists, the skill clones the base repository into the PR's artifact folder and uses
that. It returns a chapter draft
as JSON: for each testing step, the step text, the expected result, and the changed code that
step runs in execution order (file, line ranges, one-line role); then the remaining changed
files grouped by layer. It does not need the review's output, so it runs while the review runs.
Per the Delegation rule, it never dispatches and returns "Needs research" items instead.

**Step 3, run the full review (top-level session).** Run the chosen review skill on the PR,
exactly as that skill describes, including all of its phases. Jesper asked for the full review,
so phase D (the explanation for the implementer) runs too; it also gives Jesper text to draw on
when writing comments. There is no time target; prep runs unattended, and the review skill
estimates 15 to 20 minutes for a 1,000-line change. Save its complete output to the review
folder (see "Where files go"). From that output, write two JSON files: the acceptance criteria
(number, quoted text, implemented-at anchors, tested-by, verdict) and the findings (severity,
title, anchor, one-line why). An anchor is `path:line` or `path:start-end`. When the review
gives a single line, the session writes the range of the enclosing function or block, read at
the head SHA; the composer uses anchors as given and does no diff parsing.

**Step 4, compose the guide (script).** A script merges the chapter draft, the AC file, and the
findings file into a saved guide, deterministically:

- A finding goes into the first chapter whose traced code overlaps its anchor, and failing that,
  into the chapter that holds its file. A finding on a file the PR did not change (a caller, for
  example) goes into the "Before you start" chapter under its own heading, so nothing is dropped.
- A chapter lists the acceptance criteria whose implemented-at anchors overlap its traced code.
  A criterion that overlaps no traced code goes into the chapter that holds its file.
- A file summary gets an AC tag for each criterion implemented in that file, with the line
  range.
- The script checks that every changed file from `gh` is placed exactly once and that no
  unknown file is placed. It fails loudly otherwise.
- It computes the gap list: criteria with no implemented-at anchor in the diff, and changed
  source files (not tests) that no criterion's anchor touches.
- It writes the change map as a separate Mermaid `.mmd` file: testing steps as nodes, linked to
  the files each runs through, files grouped by layer. The summary message and the "Before you
  start" chapter give the file's path.
- It writes the envelope to `~/.plannotator/guides/<repo-key>/<id>.json`, with `label` set to
  "PR #<n> prepared <date>" so Jesper can find it in the list.

**Step 5, version guard (script).** The skill records the Plannotator version it was tested
against. If `plannotator --version` differs, the skill warns Jesper before launching that the
saved-guide format may have changed, and points at the fallback.

**Step 6, launch.** Call the `plannotator` tool with the review action on the PR URL, then post
the summary message and end the turn. If the session has no `plannotator` tool, run
`plannotator review <PR URL>` in the background with a long timeout and tell Jesper that Ask AI
in the browser will not have the workspace config, so questions work best in the chat.

**Step 7, answer questions.** While the review is open, Ask AI questions arrive in the session.
Answer from the PR, the tickets, the review output, and the code at the head SHA, citing
`file:line`.

**Step 8, coverage check (script).** On "check coverage", a script reads the review-progress
files for this PR and lists the changed files not marked viewed. Task 1 settles how to find the
right snapshot key.

### 4. Chapter format

A testing-step chapter's overview, in this order:

```
**Do:** <the testing step, as written in the PR>
**Expect:** <the expected result>

**Covers:** AC2 "<full text>". AC3 "<full text>".

> [!NOTE]
> [!WARNING] Bug, AC2: <one line>. `src/x/api.py` L40-L52
> [!NOTE] Question: <one line>. `src/x/views.py` L88

**Code, in the order it runs:**
- `src/x/Page.tsx` L12-L30: renders the Add button.
- `src/x/data/api.ts` L5-L20: posts the new competency.
- `src/x/models.py` L40-L60: runs here too. First read in chapter 1.
```

Each `diffs` entry's summary is one line, with AC tags: "Adds the POST handler. AC2 L40-L52."
Layer chapters use the same shape without **Do** and **Expect**. Severity words lead each
finding line. The live review screen renders `[!WARNING]`, `[!IMPORTANT]`, and `[!NOTE]`
single-line callouts as labeled, tinted boxes (Task 1). Line and chapter references are plain
text because the live review screen does not make `code:` and `chapter:` links clickable.
"Before you start" is always the first section, with `diffs: []`. It carries the gap list and the
path of the change map.

### 5. Fallback: built-in guide

When the saved-guide route does not work (Task 1 fails, or a later Plannotator version breaks
it), the skill writes `~/.plannotator/guide-instructions.md` from
`references/guide-instructions-base.md` plus the testing steps and the AC numbers and texts,
truncated to fit 2,000 characters, and tells Jesper to generate the guide with Plannotator's
Guide button. Findings then live only in the review file, not in the guide.

## Where files go

- Skill: `.claude/skills/prepare-pr-review/` in the config repo
  (`/Users/jesperhodge/workspace/unicon-openedx-ai-config`).
- Per-PR artifacts: `/Users/jesperhodge/openedx/pr-reviews/<repo>-<number>/` (review output, AC
  and findings JSON, chapter draft, change map). This folder is local and not under version
  control.
- Saved guide: `~/.plannotator/guides/<repo-key>/<id>.json`.

## Verification

- Scripts: test-driven with `pytest` from the `tutor` venv (`source ~/.virtualenvs/tutor/bin/activate`; Python 3.12, pytest 9.1), fixtures from a real PR's `gh` output. If that venv lacks a needed package, create a dedicated venv for this skill instead of changing the `tutor` venv.
- `SKILL.md`: written with `superpowers:writing-skills`, including its baseline-without-skill
  check.
- End to end: one real, small PR, run by Jesper, with the checklist from Task 1 re-run against
  the finished skill.

## Task 1: settle the unverified facts

Before any skill code: install the plugin, write one saved guide by hand for a small real PR,
and have Jesper open it. Claude prepares the guide file and the checklist; Jesper restarts
Claude Code after the plugin install, opens the review in a terminal session and in the browser,
and reports what they see. Task 1 ends with a hard stop: Task 2 starts only after every result is
recorded in the facts table. Check:

1. The hand-written guide appears in the previous-guides list and renders, with working
   `code:` links and `chapter:` links.
2. Which callout kinds render (`[!NOTE]`, `[!WARNING]`, others).
3. Whether a section with an empty `diffs` list is allowed.
4. Whether `guide.overview.diagram` with Mermaid renders from a saved guide.
5. Ask AI from the review UI is answered by the terminal session, and from the VS Code chat
   panel, if at all.
6. The Team seat login works for Ask AI.
7. Where the review-progress files for this PR land, and how to identify them from the PR URL.
8. The post dialog posts only Jesper's annotations.
9. The `plannotator` tool call returns at once, an Ask AI question arrives in the session as a
   new message, and the session can answer "check coverage" while the review is open.

Each answer goes into this document's facts table before Task 2 starts.

What the results change:

- Item 1 fails (the saved guide does not load): the composer, envelope writer, and version guard
  are not built. The fallback in component 5 becomes the main path, and the plan is rewritten
  before going on.
- Item 2: findings use the best callout kind that renders, and `[!NOTE]` when only that one
  does. No stop.
- Item 3 fails: the gap list goes into the guide's `intent` instead of a chapter. No stop.
- Item 4 fails: the change map is written as a `.mmd` file next to the other artifacts, and the
  summary message gives its path, so Jesper can open it with `plannotator annotate`. No stop.
- Items 5, 6, or 9 fail: Ask AI and "check coverage" move to the chat. Steps 6 to 8 change
  wording only. No stop.
- Item 7 fails: the coverage check is not built; Jesper uses Plannotator's own viewed marks.
- Item 8 fails: stop and decide with Jesper before going on, because the anti-goal about AI text
  posted under their name is at stake.

## Left to the builder

- Script names, CLI arguments, and module boundaries.
- How the testing section is detected in a PR body (heading variants).
- The layer order for leftover code per repository type, starting from: docs and ADRs, models
  and migrations, API, REST views and serializers, frontend data layer, components, styles,
  then tests not placed with a testing step.
- The guide `id` format, within `^[A-Za-z0-9][A-Za-z0-9._-]*$` and at most 160 characters.

## Calls Claude made that Jesper has not confirmed

- Work goes on a new branch of the config repo, branched from the current
  `ai/pr-component-tree-skill` branch, in the main checkout so the skill is live for the end to
  end test. Commits go on that branch locally; nothing is pushed.
- Plans and this design live in `.claude/plans/`.
- Per-PR artifacts go to `/Users/jesperhodge/openedx/pr-reviews/`.
- The scripts themselves use only the standard library, so running them needs no venv; only the tests need `pytest`.
- The mapper runs in parallel with the review, to shorten prep.
- Findings of every severity appear in the guide, one line each, including nits.
- Test files go into the testing-step chapter whose criteria they test, after the code.
- AC and finding anchors are ranges written by the session at the head SHA; the composer does no
  diff parsing.
- When the testing section is missing, the stop message includes a draft comment for the
  author. A sharpened step shows the author's original wording on one line under it.
- When a PR's repository has no local clone, the skill clones it into the PR's artifact folder.
