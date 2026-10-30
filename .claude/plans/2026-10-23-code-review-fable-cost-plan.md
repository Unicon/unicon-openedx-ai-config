# Code review on a thin Fable orchestrator: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cut the Fable cost of one `backend-code-review` or `frontend-code-review` run from about $8.70 to at most $2.50 at API prices (about 2% of the weekly Fable limit), with the same findings and the same delivered file.

**Architecture:** The top-level session (Fable, medium effort) keeps three jobs: routing and the scope check, judging the verified candidates, and the one-line chat response. Every other step runs in a sub-agent that reads its instructions from a file under the skill directory and writes its output to a file in one working directory. Sub-agents return short hand-backs, so the top-level context holds paths and decisions, not reports, diffs, or drafts.

**Tech Stack:** Claude Code skills (Markdown), the Agent and SendMessage tools, `gh`, `git`.

**Spec:** the design agreed in chat on 2026-10-23, summarized under "Design" below. It builds on PR #62 (`ai/code-review-collapsible-cleanup`), whose cleaned-file layout and delivery rule are kept unchanged.

## Design

Measured Fable cost of the frontend review of AShatsila/frontend-app-authoring PR #7 (session 716f722b, calls 0 to 39), at $10 input, $50 output, $0.25 cache read, and $20 cache write per million tokens:

| Phase | Fable cost | What drove it |
| --- | --- | --- |
| Setup and phase A | $3.00 | 52K-token system prompt (about half uncached), 13K tokens of skill text read twice, the 13K-token diff and the ticket, and the 6.5K-token brief Fable wrote |
| Wave and waiting | $2.10 | 8.5K tokens of dispatch prompts that retype each remit, five full B reports (about 40K tokens) entering the context, and 17 logging calls |
| Phase C | $1.40 | verification reads at about 180K tokens of context, and the 7K-token structured review |
| Phase D and delivery | $2.10 | the 7K-token explanation draft and a 9.4K-token final message |

Cache writes were 47% of the cost and output 36%. A token that enters the Fable context costs $20 per million once, so the design keeps content out of that context.

What changes, and why quality holds:

| Piece | Today | After |
| --- | --- | --- |
| Phase A | Fable inline | Brief agent (Sonnet, high). The skill already calls phase A "lookups and quoting, not judgment". Fable checks the quoted criteria in the hand-back and asks the user about blockers and conflicts. |
| The diff | Fable reads it in full | Fable never reads it. The brief carries a short map of the diff, and every candidate arrives with its cited lines quoted. Phase C forbids new probes, so Fable's reading of the diff never produced findings. |
| Frontend step 0 | Fable pins, dispatches, renders, reads the outline | One Sonnet agent runs `pr-component-tree` steps 1 to 7 itself. Fable relays its summary. |
| B dispatch prompts | Fable retypes each remit | Remits live in `agents/*.md`. A dispatch prompt is a fixed template of about 100 words. |
| B reports | Returned into Fable's context | Written to files. The hand-back is at most 80 words. An observation outside an agent's remit becomes a one-line pointer, so the same defect is not investigated and reported by four agents. |
| Phase C legwork | Fable inline | Consolidation agent (Sonnet, high, which CLAUDE.md assigns to verifying claims): merges duplicates, reads every citation at the head SHA, fulfills "Needs research" items, builds the tables. It marks candidates and never drops one, so Fable still judges every candidate. |
| Judgment | Fable | Fable, from one candidate list of about 6K to 8K tokens, writing a decisions file of about 2K tokens. It may read up to three cited lines itself. |
| Structured review (C6) and explanation draft (D1) | Fable writes both | Writer agent (Sonnet, medium-high) renders both from the decisions file. Fable checks the per-severity candidate IDs in its hand-back against its decisions. |
| D2, D3, delivery | PR #62 | Unchanged layout and rules. The cleanup agent also applies the gate's fixes and appends the delivery blocks, so Fable never reads the cleaned file. |

Expected Fable cost after the change: about 18 calls, a peak context of about 80K tokens, about 56K tokens of cache writes, and 10K to 17K output tokens, which is $2.00 to $2.50. Sub-agent cost rises by about $2.50 to $3.50; the run's total falls from about $13 to about $9. Wall clock grows by about 5 minutes, to about 25 minutes for a 1,000-line change.

## Global Constraints

- Work in the worktree `/Users/jesperhodge/workspace/unicon-openedx-ai-config-worktrees/code-review-fable-cost`, branch `ai/code-review-fable-cost`, based on PR #62's head `d5b3293`. Its index already holds the review-question routing (A5) edits.
- Skill paths below are relative to `.claude/skills/` in that worktree. `<skill-dir>` means `.claude/skills/code-review-openedx`.
- Follow the "Writing style" and "Say it in full" sections of `.claude/CLAUDE.md`: complete sentences, no em dashes, US spelling, and the current state rather than its history.
- Move existing text verbatim. Change a moved sentence only where a task says so, for example where it said "you" for the orchestrator and now addresses a sub-agent.
- Keep every frontmatter `name` and `description` unchanged.
- Keep PR #62's cleaned-file layout and Deliver rule word for word: the D2 layout bullets and the Deliver list move into `agents/cleanup.md` unchanged.
- Keep the agent type, model, effort, and budget of B1 to B5, D2, and D3 unchanged, with one exception: B1 runs as `general-purpose` on Haiku instead of `Explore`, because an `Explore` agent has no Write tool and every B agent now writes its report to a file. B5 (`software-architect`, which also has no Write tool) writes its report with a Bash heredoc.
- Do not modify `.claude/CLAUDE.md`, anything in `.claude/decisions/`, `pr-component-tree`, `clean-up-text`, or the `doc-accuracy-reviewer` agent.
- Stage each task's files with `git add`. Commit only when the user has approved committing.

## Review Focus

1. A sub-agent returns its full report as its final message instead of the short hand-back, and the report lands in Fable's context. Every agents file ends with the hand-back as a fixed template, and Task 8 measures hand-back sizes.
2. The consolidation agent merges two different defects into one candidate, or marks a real defect DOES NOT HOLD, and the finding is lost. Its file forbids both drops and severity changes, and Task 8 checks that every finding of the original PR #7 review survives.
3. Fable reads `agents/*.md`, a B report, or the diff "to be sure", which puts the cost back. SKILL.md lists the only files Fable reads, red flags cover the temptation, and Task 8's paper test checks which files the orchestrator says it would read.
4. The brief agent finds no ticket, or a superseded criterion, and the review proceeds anyway. The brief hand-back has a "Needs the user" line; SKILL.md tells Fable to ask the user with the existing question text and stop. Task 8's paper test includes this case.
5. The cleanup agent is gone when Fable tries to continue it with the gate's fixes. SKILL.md names the fallback: dispatch a fresh cleanup agent with the same message and the file paths.

---

### Task 1: Layout check (the failing test)

**Files:**
- Create: `/private/tmp/claude-501/-Users-jesperhodge-openedx/c09a57e0-02a8-419c-9890-a50cfab64b7e/scratchpad/check_review_layout.sh` (test scaffolding, not shipped)

**Interfaces:**
- Produces: `bash check_review_layout.sh <worktree>` prints one `FAIL: <reason>` line per failed check and exits 1, or prints `OK` and exits 0. Every later task runs it.

- [ ] **Step 1: Write the script.** It checks, relative to `<worktree>/.claude/skills`:
  - These files exist: `code-review-openedx/review-rules.md`, `code-review-openedx/agents/{brief,report-format,b1-locate,b2-context,b3-mechanical,b4-behavior,b5-architecture,consolidate,write,cleanup}.md`, `backend-code-review/review-additions.md`, `frontend-code-review/review-additions.md`.
  - `code-review-openedx/SKILL.md` has at most 2,400 words (`wc -w`), and each child `SKILL.md` has at most 600.
  - `code-review-openedx/SKILL.md` contains none of these remit phrases: `Map and break`, `makemigrations --check`, `invariant | enforcement`, `Lean tests`, `with a blank line after`, `The draft has these parts`.
  - Every `agents/<name>.md` path that `code-review-openedx/SKILL.md` mentions exists.
  - Every file under `code-review-openedx/agents/` contains the word `hand-back`.
  - `agents/cleanup.md` contains the exact PR #62 sentence `The first section is "Review Details".`, and `code-review-openedx/SKILL.md` contains `only a link to the cleaned`.
  - No file under the three skill directories contains an em dash (`—`).
- [ ] **Step 2: Run it on the worktree.** Expected: exit 1, with FAIL lines for the missing files and for the remit phrases still in SKILL.md.

### Task 2: Shared rules, report format, and the five remit files

**Files:**
- Create: `code-review-openedx/review-rules.md`, `code-review-openedx/agents/report-format.md`, `code-review-openedx/agents/b1-locate.md`, `b2-context.md`, `b3-mechanical.md`, `b4-behavior.md`, `b5-architecture.md`
- Modify: `code-review-openedx/SKILL.md` (remove the moved text)

**Interfaces:**
- Produces: the B hand-back template (below), which Task 6 relies on. Each remit file is self-contained apart from `review-rules.md`, `report-format.md`, and the brief.

- [ ] **Step 1: Create `review-rules.md`.** Move verbatim from SKILL.md: "What the review must establish" (all ten points), "Review-wide rules" (all bullets), and the five severity definitions from C6 part 6 (`Bug` to `Nit`) under a heading "Severities". Add a "Red flags" table holding the existing rows about evidence and severity: "The comment is wrong but the code works", "I could not run it on the CI database", "The other ticket owns this", "The neighboring tests do the same", "A senior engineer would not raise this nit", "The ticket does not mention it", "The sub-agent found it", "That configuration is exotic". Open the file with one sentence: every agent in the review, and the top-level session, reads this file first.
- [ ] **Step 2: Create `agents/report-format.md`.** It holds the output format that A4 used to put in the brief: findings with Title, Severity, Anchor `path:line`, Evidence marked CONFIRMED or INFERRED with the inferred step named, Why it matters in one sentence, Suggested change; then the remit's required table; then "Checked and found acceptable"; then "Outside this remit"; then "Needs research"; full sentences, no em dashes, at most 2,500 words. Add:
  - The report goes to `b<n>-report.md` in the working directory the dispatch names (`b1-report.md` for B1, and so on), written with the Write tool, or with a Bash heredoc when the agent has no Write tool, never into the final message.
  - "Outside this remit": when an agent notices something another remit owns, it writes one line (title, `path:line`, the owning remit) and does not investigate it further.
  - Review questions: move the answering rule from A5 here (each question answered with its number; an answer that proposes a change is a finding whose title starts with the number; every other answer is a line in "Checked and found acceptable" that starts with the number; it may also raise any further concern in the same area).
  - The read-only, no-dispatch, worktree, and budget rules from the A4 brief description.
  - The hand-back, as an exact template:
    ```
    Report: <path>
    Candidates: <n> (Bug <n>, Gap <n>, Question <n>, Suggestion <n>, Nit <n>); outside-remit pointers: <n>
    Review questions answered: <Q numbers, or none>; unanswered: <Q numbers, or none>
    Needs research: <n>
    Blocked: <none, or one sentence>
    ```
    The final message is this template filled in, at most 80 words, and nothing else.
- [ ] **Step 3: Create the five remit files.** Each holds its remit body from Phase B verbatim (B1 to B5), with a first line naming its agent type, model, effort, and budget from the "Who does what" table, and a line telling the agent to read `review-rules.md`, the brief, and `report-format.md` first and to read its section of the extension skill's `review-additions.md` when the dispatch names one. Move these red-flag rows: "The migration check covers this criterion", "Existing tests cover this", "The tests pass, so the behavior works", "The test mocks the lock call", "More tests is safer" into `b4-behavior.md`; "There is no `AGENTS.md`" into `b1-locate.md` and `b5-architecture.md`; "This is a library change" into `b5-architecture.md`.
- [ ] **Step 4: Remove the moved text from SKILL.md** (the two rule sections, the Phase B remit bodies, the severity definitions, and the moved red-flag rows). Leave the headings that Task 6 rewrites.
- [ ] **Step 5: Run the layout check.** Expected: still exit 1, but no FAIL for the files this task created.
- [ ] **Step 6: Stage the files.**

### Task 3: The brief agent

**Files:**
- Create: `code-review-openedx/agents/brief.md`
- Modify: `code-review-openedx/SKILL.md` (remove A1 to A4 bodies)

**Interfaces:**
- Consumes: `review-rules.md` (Task 2).
- Produces: the working-directory file names and the brief hand-back template, which Task 6 relies on.

- [ ] **Step 1: Create `agents/brief.md`** (Sonnet, high, budget 30). Move A1, A2, A3, A4, and "Where the rules live" verbatim, addressed to the brief agent. Change these points:
  - The agent writes into the working directory the dispatch names, using these names: `pr<N>-body.md`, `ticket-<N>.json` for each ticket fetched, `pr<N>.diff`, and `brief-<slug>.md`, where `<slug>` is `pr<N>` for a pull request and the branch name with `/` replaced by `-` otherwise.
  - A4's output-format sentence becomes: the brief names `<skill-dir>/agents/report-format.md` as the output format.
  - The brief gains a "Diff map": one or two lines per changed file saying what changed and which symbols, at most 60 lines, inside the brief's 150-line limit.
  - When the dispatch names a component-tree outline path, the brief includes the line from `frontend-code-review` step 0 item 3 with that path.
  - A1's "stop and ask" cases become hand-back lines: the agent stops and reports `NO TICKET`, `CONFLICT: <one sentence per criterion>`, or `BLOCKED: <what could not be fetched>`; it never asks the user itself. The quoted question to the user ("Please provide the ticket or issue for this change...") stays in SKILL.md, where Task 6 uses it.
  - The hand-back, as an exact template, at most 300 words:
    ```
    Brief: <path>  Diff: <path> (<n> files, <n> lines)
    Target: <repo> <PR or branch>, base <sha>, head <sha>, merge-base <sha>; ticket #<n>, updated_at <timestamp>
    Criteria:
    1. "<quoted criterion>"
    Excluded criteria: <number and reason each, or none>
    Needs the user: <none | NO TICKET | CONFLICT: ... | BLOCKED: ...>
    Claims listed: <n>
    ```
- [ ] **Step 2: Remove the A1 to A4 bodies and "Where the rules live" from SKILL.md,** except the quoted question to the user, which stays.
- [ ] **Step 3: Run the layout check.** Expected: no FAIL for `brief.md`.
- [ ] **Step 4: Stage the files.**

### Task 4: The consolidation agent

**Files:**
- Create: `code-review-openedx/agents/consolidate.md`
- Modify: `code-review-openedx/SKILL.md` (remove the C1 to C4 bodies and the "Needs research" paragraph)

**Interfaces:**
- Consumes: `b1-report.md` to `b5-report.md` (Task 2), the brief (Task 3).
- Produces: `candidates.md` and `record.md` in the working directory, in the formats below. Task 5 and Task 6 rely on them.

- [ ] **Step 1: Create `agents/consolidate.md`** (`general-purpose`, Sonnet, high, budget 35). Move verbatim, addressed to this agent: C1 (the acceptance-criteria table and its rules), C2 (premise audit), C3 (invariants), C4 (verify before asserting), and the paragraph on fulfilling "Needs research" items (installed source first; a web lookup only when the item decides a `Bug` or `Gap`, which this agent now does itself with WebFetch, at most 5 fetches). Add these rules:
  - Read every B report in full and the "Consolidation" section of the extension skill's `review-additions.md` when the dispatch names one.
  - Merge two candidates only when they describe the same defect: the same cause and the same fix. Two defects at one anchor stay two candidates. A merged candidate lists every source remit.
  - Never drop a candidate and never set its final severity. Record each source's proposed severity. Mark verification as `HOLDS`, `DOES NOT HOLD` (with the fact that disproves it), or `UNVERIFIABLE` (with what was missing).
  - Quote at most 6 lines of the cited code at the head SHA for each candidate.
  - Note, per candidate, anything that bears on sorting: a precedent that does the same, a pre-existing issue, a CI-enforced rule, a ticket that claims the work.
  - Carry each "Outside this remit" pointer as a candidate unless it merges into a finding from the owning remit.
- [ ] **Step 2: Specify `candidates.md`, which the top-level session reads, so it holds only what judging needs.** Exact layout:
  ````
  # Candidates: <target>, head <sha>
  <n> candidates; <n> review questions, <n> unanswered (<Q numbers>)

  ## Acceptance criteria
  | # | Criterion (first 12 words) | Verdict | Implemented at | Tested by |

  ## Premise audit: FALSE and UNVERIFIABLE rows (<n> claims checked)
  ## Invariant gaps (<n> rows in the table)

  ## Candidates
  ### C1. <title>
  - From: <remits> | Proposed: <severity per remit> | Answers: <Q number or none>
  - Anchor: `path:line`
  - Claim: <one or two sentences: what is wrong and the mechanism>
  - Verification: <HOLDS | DOES NOT HOLD | UNVERIFIABLE>: <one sentence on what was read or run>
  - Code at head:
    ```
    <at most 6 lines>
    ```
  - Impact: <one sentence>. Fix: <one sentence>.
  - Sorting notes: <precedent, pre-existing, CI-enforced, owning ticket, or none>
  ````
  Target size: at most 8,000 tokens for a 1,000-line change.
- [ ] **Step 3: Specify `record.md`, which the writer reads.** It holds the full criteria table with quoted criteria, the full premise table, the full invariants table, the "Checked and found acceptable" lines of all reports (with Q numbers), the checks run and skipped from B3 and B4, and the path of B4's break-and-restore table.
- [ ] **Step 4: Add the hand-back**, an exact template, at most 60 words:
  ```
  Candidates: <path> (<n> candidates: <n> HOLDS, <n> DOES NOT HOLD, <n> UNVERIFIABLE)
  Record: <path>
  Unanswered review questions: <Q numbers, or none>
  Blocked: <none, or one sentence>
  ```
- [ ] **Step 5: Remove the moved text from SKILL.md** (C1 to C4 bodies and the "Needs research" paragraph after the dispatch table). Keep C5, which Task 6 rewrites for the top-level session.
- [ ] **Step 6: Run the layout check and stage the files.**

### Task 5: The writer and the cleanup agent

**Files:**
- Create: `code-review-openedx/agents/write.md`, `code-review-openedx/agents/cleanup.md`
- Modify: `code-review-openedx/SKILL.md` (remove C6, D1, D2, and Deliver bodies)

**Interfaces:**
- Consumes: `candidates.md` and `record.md` (Task 4), the brief (Task 3), and `decisions.md`, which the top-level session writes in this exact format (Task 6 puts the same block in SKILL.md):
  ```
  Verdict: Ready to merge: <yes | with fixes | no>. <one sentence why>
  C1: <Bug | Gap | Question | Suggestion | Nit>
  C2: drop: <the fact that disproved it>
  C3: declined: <owning ticket> must <what>; it can, because <reason>
  C4: <severity> | text: <replacement claim, only when the candidate's claim or impact is wrong>
  Open questions:
  - <question for the developer>
  ```
- Produces: `review-<slug>-c6.md`, `review-<slug>-d1-explanation.md` (writer); `review-<slug>-d1-explanation-cleaned.md` and `review-<slug>-d2-changelog.md` (cleanup). Task 6 relies on both hand-backs.

- [ ] **Step 1: Create `agents/write.md`** (`general-purpose`, Sonnet, medium-high, budget 15). Move verbatim: C6 parts 1 to 11 and the presentation paragraph after them ("Lead each finding with the point..."), the Phase D introduction, and D1 with its six parts and closing paragraph, addressed to the writer. Change these points:
  - The writer takes every finding's text from its candidate in `candidates.md`, takes the severity, drops, declines, verdict, and open questions from `decisions.md`, and uses a `text:` override from `decisions.md` in place of the candidate's claim where one is given. It adds no finding and changes no severity.
  - Inputs and the tables come from the brief and `record.md`; part 7 is B4's break-and-restore table copied as returned.
  - C6 part 6 refers to the severity definitions in `review-rules.md` instead of repeating them.
  - Answers to review questions go into D1 in their own section before the action list, as PR #62's Deliver paragraph says.
  - The hand-back, an exact template:
    ```
    C6: <path>  D1: <path>
    Bug: <IDs>; Gap: <IDs>; Question: <IDs>; Suggestion: <IDs>; Nit: <IDs>
    Declined: <IDs>; Dropped: <IDs>
    Review questions answered in D1: <Q numbers, or none>
    ```
- [ ] **Step 2: Create `agents/cleanup.md`** (`general-purpose`, Sonnet, medium-high, budget 25). Move verbatim: D2 (including PR #62's layout paragraph and all its bullets) and the Deliver step's opening sentence and both numbered items, addressed to the cleanup agent. Of the Deliver step's closing paragraph, the sentences about writing answers into the D1 draft move to `write.md`, and the sentence "Your response in chat is only a link to the cleaned file, nothing more." stays in SKILL.md for Task 6. Change these points:
  - The changelog goes to `review-<slug>-d2-changelog.md`; the "Needs verification" hand-back names the source, rewrite, and changelog paths and the definitions added, at most 150 words.
  - After the gate, the top-level session continues this agent with the gate's verdict and fixes. The agent applies the fixes, then performs the Deliver step (it appends the verdict sentence, the unconfirmed definitions, and the C6 file inside the collapsed blocks the Deliver list describes). Its final hand-back is the cleaned file's path and the word count of its body.
- [ ] **Step 3: Remove the moved text from SKILL.md.**
- [ ] **Step 4: Run the layout check and stage the files.** Expected: the PR #62 sentence checks pass.

### Task 6: The orchestrator SKILL.md

**Files:**
- Modify: `code-review-openedx/SKILL.md` (rewrite what remains)

**Interfaces:**
- Consumes: every file and hand-back template from Tasks 2 to 5.
- Produces: `decisions.md` format (below), which Task 5's writer consumes; the dispatch template.

- [ ] **Step 1: Rewrite SKILL.md as the top-level session's instructions, at most 2,400 words, in this order:**
  1. The opening paragraphs (the two questions, review-only, top-level only), kept.
  2. A new paragraph: this session reads `review-rules.md`, this file, the extension skill's `SKILL.md`, the hand-backs, `candidates.md`, and the gate's report, and nothing else. The files under `agents/` are for the agents they name. The diff, the brief, the B reports, and the drafts stay on disk.
  3. "Shape and timing", updated to the new phases and about 25 minutes of wall clock.
  4. "Working directory": `<scratchpad>/review-<slug>/`, named in every dispatch, with the file names from Tasks 3 to 5.
  5. The "Who does what, and when" table, updated: A brief agent (Sonnet, high, 30); step 0 for frontend (Sonnet, medium-high); B1 to B5 unchanged; C consolidation (Sonnet, high, 35); judgment (top-level, 5 tool calls); D1 writer (Sonnet, medium-high, 15); D2 cleanup (unchanged); D3 gate (unchanged).
  6. The dispatch template, exact copy:
     ```
     You are <role> in a code review of <target>. You cannot dispatch sub-agents; return a "Needs research" item for anything you cannot do yourself. Tool-call budget: <n>.
     Read, in order: <skill-dir>/review-rules.md, then <skill-dir>/agents/<file>.md, and follow it.
     Working directory: <dir>.
     <Only when it applies: the brief path; the outline path; the additions file and its section; the developer's review questions, verbatim, with their numbers.>
     Your final message is the hand-back your agents file describes, and nothing else.
     ```
     Pass `model` explicitly on every dispatch. Dispatch all five B agents in one message.
  7. Phase A: dispatch the brief agent (and, for a frontend review, step 0 in the same message). On its hand-back: for `NO TICKET`, ask the user with the existing question text from A1 and stop; for `CONFLICT` or `BLOCKED`, put the line to the user and stop; otherwise compare the quoted criteria with the request, and continue. Then A5, kept, with one change: the extension skill's questions live in its `review-additions.md`, so each B dispatch names that file and its section, and only the developer's questions are copied into dispatch prompts.
  8. Phase B: one dispatch wave. A hand-back needs action only when its `Blocked` line is not `none`; re-dispatch that agent once with the reason.
  9. Phase C: dispatch the consolidation agent. Read `candidates.md`. Judge with C5's rules, kept verbatim but addressed to the judge, plus: at most 3 tool calls to read a cited line yourself when the quoted lines do not settle a candidate. Write `decisions.md` with the Write tool, exact format:
     ```
     Verdict: Ready to merge: <yes | with fixes | no>. <one sentence why>
     C1: <Bug | Gap | Question | Suggestion | Nit>
     C2: drop: <the fact that disproved it>
     C3: declined: <owning ticket> must <what>; it can, because <reason>
     C4: <severity> | text: <replacement claim, only when the candidate's claim or impact is wrong>
     Open questions:
     - <question for the developer>
     ```
  10. Phase D: dispatch the writer; compare its hand-back IDs with `decisions.md` and re-dispatch it once with the mismatch if they differ. Dispatch the cleanup agent. Dispatch the gate (`doc-accuracy-reviewer`, Sonnet) with the source, rewrite, and changelog paths and `clean-up-text` step 6. Continue the cleanup agent with SendMessage, passing the gate's verdict, its fixes verbatim, and its unconfirmed definitions; on FAIL, dispatch the gate again after the fixes. If the cleanup agent cannot be continued, dispatch a fresh one with the same message and the paths.
  11. Delivery: the chat response is only a link to the cleaned file, as PR #62 says.
  12. Red flags: keep the rows about dispatch timing, reading source in phase A, "One more probe", the review-question row, the two Phase D rows; add: "I'll read the diff to understand the change." (The candidates carry the quoted lines; the diff map is in the brief, and reading the diff costs more than the whole judgment step.) "I'll open b5-report.md to be sure." (The consolidation agent read it; ask that agent with SendMessage when a candidate is unclear.) "I'll write the structured review myself, it's faster." (Every token you write costs five times one you read, and the writer renders it from your decisions.) "I'll log progress while I wait." (Each extra turn re-reads the whole context.)
- [ ] **Step 2: Run the layout check.** Expected: SKILL.md word count and remit-phrase checks pass.
- [ ] **Step 3: Stage the file.**

### Task 7: The extension skills

**Files:**
- Create: `backend-code-review/review-additions.md`, `frontend-code-review/review-additions.md`
- Modify: `backend-code-review/SKILL.md`, `frontend-code-review/SKILL.md`

**Interfaces:**
- Consumes: A5 and the dispatch template (Task 6).
- Produces: section names `## B2`, `## B3`, `## B4`, `## B5`, `## Consolidation`, which the dispatch names.

- [ ] **Step 1: Create `backend-code-review/review-additions.md`.** Move the twelve backend questions, keeping their numbers as `Q1` to `Q12`, into sections by their bracketed remit (`## B2`: Q3, Q4; `## B3`: Q1; `## B4`: Q7, Q12; `## B5`: Q2, Q5, Q6, Q8, Q9, Q10, Q11). Move "Additional Notes" item 1 (the schema-only migration rule) into `## Consolidation`.
- [ ] **Step 2: Create `frontend-code-review/review-additions.md`** with `## B3`: Q3, Q4 and `## B5`: Q1, Q2, Q5.
- [ ] **Step 3: Update `backend-code-review/SKILL.md`.** Keep the opening, the parent-skill section, and "Delivering the review". Replace the questions section with two sentences: the questions and the consolidation note live in `review-additions.md`, numbered Q1 to Q12; each B dispatch and the consolidation dispatch names that file and its section, and the developer's questions are numbered from Q13.
- [ ] **Step 4: Update `frontend-code-review/SKILL.md`** the same way (questions Q1 to Q5, developer's questions from Q6). Rewrite step 0: dispatch one `general-purpose` Sonnet agent (medium-high, budget 40) in the same message as the brief agent, telling it to run `pr-component-tree` steps 1 to 7 itself, since it is both that skill's top-level session and its sub-agent, to dispatch nothing, and to write into the working directory. Give the brief agent the outline path `component-tree-pr-<N>-context.txt` in the working directory. Relay the agent's summary to the developer as soon as it returns. Keep the orientation-not-evidence paragraph (item 4) and move it into `review-additions.md` as a `## All` section. State in the frontend SKILL.md that each B dispatch names both `## All` and its own `## B<n>` section.
- [ ] **Step 5: Run the layout check.** Expected: `OK`.
- [ ] **Step 6: Stage the files.**

### Task 8: Behavior checks on real artifacts

The top-level session runs this task itself, because the checks dispatch sub-agents and an implementer cannot dispatch. Fixes that the checks call for go to an implementer.

**Files:**
- Create (scratchpad only): `test-fable-cost/` under the session scratchpad, holding fixtures and results.

**Interfaces:**
- Consumes: everything above; the PR #7 run's files in `/private/tmp/claude-501/-Users-jesperhodge-openedx/716f722b-86c5-4f2c-95b5-61e6f78b506a/scratchpad/` (`brief-pr7.md`, `pr7.diff`, `review-pr7-c6.md`, `review-pr7-d1-explanation.md`) and that session's sub-agent transcripts under `~/.claude/projects/-Users-jesperhodge-openedx/716f722b-86c5-4f2c-95b5-61e6f78b506a/subagents/`.

- [ ] **Step 1: Extract the five B reports of the PR #7 run** (the final assistant text of each B1 to B5 transcript) into `b1-report.md` to `b5-report.md` in a fixture working directory, with a copy of `brief-pr7.md` and `pr7.diff`.
- [ ] **Step 1b: File-writing smoke test.** Dispatch a `general-purpose` Haiku agent and a `software-architect` agent, each told only to follow the report rule in `agents/report-format.md` with a one-line dummy report and the hand-back template. Pass: both files exist and both final messages are the filled-in template.
- [ ] **Step 2: Orchestrator paper test** (three `general-purpose` Sonnet dispatches, high effort, no tool use beyond reading the skill files). Each reads `frontend-code-review/SKILL.md` and its parent and returns the dispatch prompts it would send in phases A and B for a request with two developer questions, plus the list of files it would read in the whole review. A fourth case gives a brief hand-back with `NO TICKET`. Pass: every prompt follows the template and is at most 150 words, no file under `agents/` and no report or diff is on the read list, and the `NO TICKET` case asks the user and stops.
- [ ] **Step 3: Consolidation fixture run** (one `general-purpose` Sonnet dispatch, high, using the real dispatch template), against the fixture directory and a worktree of `/Users/jesperhodge/openedx/frontend-app-authoring` at `81a5cb32`. Pass: every finding in `review-pr7-c6.md` maps to a candidate that is not marked DOES NOT HOLD (list the mapping); `candidates.md` is at most 8,000 tokens (`wc -w` times 1.35); the hand-back follows its template.
- [ ] **Step 4: Writer fixture run.** Write a stand-in `decisions.md` from `candidates.md` by applying C5, then dispatch the writer with the template. Pass: the hand-back IDs match `decisions.md`; the new C6 has the same findings as `review-pr7-c6.md` apart from differences the decisions explain.
- [ ] **Step 5: Cleanup and gate run** on the new D1 (cleanup dispatch, gate dispatch, SendMessage continuation). Pass: the gate returns PASS or PASS WITH FIXES; the continued cleanup agent appends the delivery blocks; the cleaned file has the PR #62 layout (Review Details block, four group headings, summary sentence plus `<details>` per finding, the accuracy check, and the structured review block).
- [ ] **Step 6: Record results** in `test-fable-cost/results.md`: pass or fail per step, hand-back word counts, `candidates.md` size, and the missing-findings list. Fix the skill text for any failure and rerun the failing step.

### Task 9: Final check and handover

- [ ] **Step 1: Run the layout check.** Expected: `OK`.
- [ ] **Step 2: Run `git diff --cached --stat`** and confirm that only the files named in this plan changed.
- [ ] **Step 3: Report to the user:** the results file, the word counts of what the top-level session now reads, and the open item that only an end-to-end run on Fable can confirm the cost (measure it with the session-cost script from this session's scratchpad). Ask whether to commit and open a PR stacked on PR #62.
