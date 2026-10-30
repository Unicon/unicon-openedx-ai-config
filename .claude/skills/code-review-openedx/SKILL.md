---
name: code-review-openedx
description: "Senior peer review of a diff in an Open edX repository (openedx-core, edx-platform, frontend-app-authoring). Use when asked to review a pull request, branch, commit range, or working tree, and as the parent skill that backend-code-review and frontend-code-review extend; prefer one of those two when the change is clearly backend or frontend. Review-only: findings with file:line anchors and a severity marker; never fixes, commits, or pushes. Posts to GitHub only when explicitly asked and approved."
---

# Code review

A senior peer review of a change in the Open edX ecosystem. The review answers two separate
questions and keeps their answers separate. Is this the right thing: every acceptance criterion
of the ticket is implemented correctly and covered by a test that fails when the behavior
breaks. Is it built right: the code follows the conventions, ADRs, and layering of the
repository it lands in, the rules its data model relies on are enforced where the code says
they are, and every claim the change makes about how its libraries behave is true. A change can
pass one question and fail the other, and a pass on one never offsets a failure on the other.

The review surfaces what is wrong and why, with evidence, and lets the developer decide what to
act on. It never applies fixes, commits, or pushes. It posts to GitHub only when the developer
asks and approves the wording.

This skill runs in the top-level session.
Per the Delegation rule in `CLAUDE.md`, it alone dispatches the sub-agents this skill names; a
dispatched sub-agent never dispatches a further one. When a
sub-agent needs something it cannot fetch, it returns a "Needs research" item, and the
consolidation agent fulfills it.

The top-level session runs on the most expensive model and re-reads everything it has read on
every call. It reads only `review-rules.md`, this file, the extension skill's `SKILL.md`,
the hand-backs, `candidates.md`, and the gate's report. The files under `agents/` are for the
agents they name. The diff, the brief, the B reports, and the drafts stay on disk.

**Shape and timing.** The review runs in four phases: the brief (A), one dispatch wave of five
parallel sub-agents (B), consolidation and judgment (C), and the explanation (D). Nothing in the wave waits on anything else in it. A review of a 1,000-line change should finish in about
25 minutes: phase A in about 4, the wave in about 8, phase C in about 6, and phase D in about 7.
A longer review has usually broken a rule: this session read the diff or source files, a
sub-agent was dispatched after the wave instead of in it, or phase C probed instead of reading
cited lines.

## Working directory

Every review works in `<scratchpad>/review-<slug>/`, where `<slug>` is `pr<N>` for a pull
request and the branch name with `/` replaced by `-` otherwise. Every dispatch names it. It
holds `pr<N>-body.md`, `ticket-<N>.json`, `pr<N>.diff` (`<slug>.diff` for another target), and
`brief-<slug>.md` from the brief agent; `b1-report.md` to `b5-report.md` from the B agents;
`candidates.md` and `record.md` from the consolidation agent; `decisions.md` from this session;
`component-tree-pr-<N>-context.txt` from step 0 of a frontend review;
`review-<slug>-c6.md` and `review-<slug>-d1-explanation.md` from the writer; and the cleaned
file and its changelog.

## Who does what, and when

| Phase | Work | Agent, model, effort | Budget |
| --- | --- | --- | --- |
| A | Pin target and ticket, quote the criteria, write the brief | brief agent, `general-purpose`, Sonnet, high | 30 |
| A, frontend | Step 0 of the extension skill: the component tree map | `general-purpose`, Sonnet, high | set by the extension skill |
| B1 | Locate instruction files, ADRs, and callers ("where is X") | `general-purpose`, Haiku, default | 25 |
| B2 | Tickets, git history, prior PR comments, comments and prose, community requirements | `general-purpose`, Sonnet, high | 35 |
| B3 | Mechanical checks: merge with `main`, linters, targeted tests, premise lookups | `general-purpose`, Sonnet, high | 35 |
| B4 | Behavior: break-and-restore of tests, error paths, lean tests | `general-purpose`, Sonnet, high | 35 |
| B5 | Architecture, ADRs, placement, invariants; writes its report with a Bash heredoc | `software-architect`, Opus, xhigh | 35 |
| C | Consolidation: tables, and every candidate verified at the head SHA | `general-purpose`, Sonnet, high | 35 |
| C | Judgment: sort the candidates, write `decisions.md` | the top-level session | 5 tool calls |
| D1 | Render the structured review and the explanation | writer, `general-purpose`, Sonnet, high | 15 |
| D2 | `clean-up-text` steps 1 to 5 and 7, the gate's fixes, delivery | `general-purpose`, Sonnet, high | 25 |
| D3 | The accuracy gate, `clean-up-text` step 6, on the cleaned explanation | `doc-accuracy-reviewer`, Sonnet, high | 15 |

The effort column is the Agent tool's `effort` parameter; where it says `default`, pass none.

## Dispatching

Every dispatch except the gate's uses this template, with the placeholders filled in.
`<skill-dir>` is the absolute path of the `code-review-openedx` skill directory, and every path
in a dispatch is absolute:

```
You are <role> in a code review of <target>. You cannot dispatch sub-agents; return a "Needs research" item for anything you cannot do yourself. Tool-call budget: <n>.
Read, in order: <skill-dir>/review-rules.md, then <skill-dir>/agents/<file>.md, and follow it.
Working directory: <dir>.
<Only when it applies: the brief path; the outline path; the additions file and its section; the developer's review questions, verbatim, with their numbers.>
Your final message is the hand-back your agents file describes, and nothing else.
```

Pass `model` explicitly on every dispatch. Dispatch all five B agents in one message with
`run_in_background: false`: they run concurrently and this session waits for all of them.
For the B agents and the consolidation agent, this session acts on the `Blocked` line only, and
reads a `Note` line without acting on it. When the `Blocked` line is not `none`, re-dispatch that
agent once with the reason, and when it is still blocked, tell the user why and stop. The brief,
writer, cleanup, and gate hand-backs have their own lines, described in their phases. When the
writer's `Blocked` line names a candidate missing from `decisions.md`, add that candidate's line
and re-dispatch it; on a second ID mismatch, stop and tell the user.

## Phase A: brief, then check the scope

Read `review-rules.md` first, before dispatching anything, because it holds the judging rules.
Then dispatch the brief agent (`agents/brief.md`) with the review target, the working directory,
and any ticket reference or text from the user's request. For a frontend review, send the
step 0 dispatch in the same message (the extension skill's `SKILL.md` describes it), and pass the brief agent the outline path `<dir>/component-tree-pr-<N>-context.txt`, the file that
`pr-component-tree` writes. Give step 0's Markdown path and summary to the user in their own message before the wave starts. When step 0 fails or its outline file does not exist, leave the
outline path out of the B dispatches, tell the B agents to skip the brief's outline line, and say
so in that message instead.

The `Needs the user` line of the brief agent's hand-back decides what happens next:

- `NO TICKET`: ask the user the question below, and stop. When the user gives the ticket,
  dispatch the brief agent again with it.

  > Please provide the ticket or issue for this change, as a URL, an issue number, or the ticket
  > linked in the pull request description. I need it to review scope and completeness, and I
  > won't begin the review until I have it.

- `CONFLICT: ...` or `BLOCKED: ...`: put that line to the user, and stop. When the user resolves
  it, dispatch the brief agent again with the user's answer.
- `none`: compare the quoted criteria with the request, and continue.

**A5. Review questions.** A review question is one the review must answer on top of the remits below. Review questions come from two places: the extension skill (`backend-code-review`
and `frontend-code-review` each keep theirs in a `review-additions.md`, under the remit that
answers each one), and the developer's request (for example, "also check whether the new view
logs the learner's email"). Number them `Q1`, `Q2`, and so on, the extension skill's questions
first; its `SKILL.md` states how many there are. Each B dispatch names `review-additions.md` and, when the file has a `## B<n>` section for that
remit, that section, so the extension skill's questions are not copied into prompts. Only the
developer's questions are copied, verbatim, with their numbers, under the
heading "Review questions", each into exactly one remit, the one for what it asks about:

| The question asks about | Remit |
| --- | --- |
| Only where something lives, or what calls or imports it, with no judgment about it | B1 |
| The tickets, the history of the touched code, comments, docstrings, names, or the PR description | B2 |
| Whether a claim about a framework, library, or tool is true, or what a test run, linter, or merge reports | B3 |
| Runtime behavior: tests, error paths, and input handling | B4 |
| Design, accessibility, the data model, security, conventions and ADRs, whether new code duplicates existing code, or anything the rows above do not cover | B5 |

## Phase B: one dispatch wave

The remits are `agents/b1-locate.md`, `agents/b2-context.md`, `agents/b3-mechanical.md`,
`agents/b4-behavior.md`, and `agents/b5-architecture.md`. Each B dispatch carries the brief path, the outline path for a frontend review, the additions file
with the section for that remit when it has one (and `## All` for a frontend review), and the
review questions routed to that remit, never this session's history.

## Phase C: consolidate, then judge

Dispatch the consolidation agent (`agents/consolidate.md`) with the brief path, the extension
skill's whole `review-additions.md`, and the developer's review questions with their numbers and
remits. Read `candidates.md` from its hand-back, and nothing else it names.

**C5. Sort.** Two questions per candidate: did the evidence hold, and does it propose a change?

- Evidence held and it proposes a change: a finding, at the severity the evidence supports. A
  precedent that does the same, or a run that showed no symptom, lowers it to `Suggestion` or
  `Nit`; it does not remove it. Nits stay in the report under `Nit`.
- Evidence did not hold, or nothing available can verify it, or it proposes no change: dropped,
  with one line saying what disproved it, under "Dropped".
- Reachability or contract unconfirmed: a `Question`.

When another ticket explicitly owns the work a candidate asks for, write down what that ticket
will have to do, then check whether it can do it without undoing something this change adds: a
constraint, a field name, a response shape, a lookup. If it can, the candidate is a line under
"Declined to judge" with that reasoning. If it cannot, it is a finding on this change, whatever
the ticket says.

Drop, rather than downgrade: pre-existing issues the change does not touch; anything CI tooling
catches; issues on lines the change did not modify, unless the change exposes them.

`candidates.md` quotes every cited line. Use at most 3 tool calls to read a cited line yourself, and only when the quoted lines do not
settle a candidate. To ask what a B agent found, continue
the consolidation agent with SendMessage.

A `Bug` or a `Gap` means the verdict is not "yes". Keep the two axes separate: a clean
convention pass does not soften a criterion `Gap`, and full criteria coverage does not excuse a
layering violation.

For an unanswered developer question on the hand-back's "Unanswered review questions" line,
continue the consolidation agent with SendMessage to answer it from the reports, and when it
cannot, put it under "Open questions" in `decisions.md`. An unanswered extension-skill question
is listed under "Checks run and skipped", as C4 says.

Write `decisions.md` in the working directory with the Write tool, in exactly this format. It
has one line per candidate, keyed by its `C<n>` ID, each in one of the four forms shown, because
the writer treats a candidate it does not find there as a blocker:

```
Verdict: Ready to merge: <yes | with fixes | no>. <one sentence why>
C1: <Bug | Gap | Question | Suggestion | Nit>
C2: drop: <the fact that disproved it>
C3: declined: <owning ticket> must <what>; it can, because <reason>
C4: <severity> | text: <replacement claim, only when the candidate's claim or impact is wrong>
Open questions:
- <question for the developer>
```

## Phase D: write, clean up, gate, deliver

**D1. Writer.** Dispatch the writer (`agents/write.md`) with the working directory, the `<slug>`,
and, under a "Review questions" heading, the developer's review questions verbatim, with their
numbers. The writer answers every question listed there in D1. When the finding IDs in its hand-back
differ from `decisions.md`, re-dispatch it once with the mismatch.

**D2. Cleanup.** Dispatch the cleanup agent (`agents/cleanup.md`) with the working directory, the
`<slug>`, the D1 file as the source path, the C6 file path, and the intended reader: the engineer
who implemented the change. Its round-one hand-back is a "Needs verification" item with the
source, rewrite, and changelog paths.

**D3. Gate (`doc-accuracy-reviewer`, Sonnet, high, budget 15).** Dispatch the gate with this
prompt. The agent type is `doc-accuracy-reviewer`; when that type does not resolve, use a
`general-purpose` agent told to read the `doc-accuracy-reviewer` agent definition in
`.claude/agents/`.

```
Read <absolute path of clean-up-text's SKILL.md> and run its step 6. Source: <path>. Rewrite: <path>. Changelog: <path>. Each summary sentence in the changelog is added text: check it against its finding in the source. Your final message is the verdict, then a numbered list of fixes, each written as the exact old text and the exact new text, then the definitions you cannot confirm, and nothing else.
```

Then continue the cleanup agent with SendMessage, passing the gate's verdict, its fixes verbatim, and its
unconfirmed definitions. Leave out any gate fix that would undo the cleaned file's layout, for
example restoring the removed lead paragraph; pass every other fix verbatim. Nothing ships
past a FAIL:

- On FAIL, the cleanup agent corrects the text only and hands back
  `Corrected: <path>  Fixes applied: <n>`. Dispatch the gate again, and continue the cleanup
  agent again with the new verdict. After a second FAIL, stop and tell the user that the accuracy
  gate failed twice, with the path of the cleaned file and the gate's last report.
- On PASS or PASS WITH FIXES, the cleanup agent applies any fixes, delivers, and hands back
  `Cleaned: <path>  Body words: <n>`.

If the cleanup agent cannot be continued, dispatch a fresh one. Its dispatch carries the gate
verdict, the fixes, the definitions, and the source, rewrite, changelog, and C6 paths.

**Deliver.** The cleaned file is the review the user receives. The cleanup agent appends the
delivery blocks to it. Your response in chat is only a link to the cleaned file, nothing more.

## Red flags

| Thought | Reality |
| --- | --- |
| "I'll dispatch the architect once the criteria table is done." | The architect needs the criteria, not the table. The wave goes out in one message. |
| "Let me read the model file before writing the brief." | The brief agent reads the ticket, the PR, and the diff. Source files are the wave's. |
| "One more probe to be sure." | The consolidation agent reads cited lines and re-runs stated commands, and probes only a `Bug` with no reproduction. |
| "This review question is quick; I will answer it myself." | Every review question goes to one B agent in the wave (A5). This session holds the largest context, so answering there costs the most. |
| "The structured review is clear enough; the explanation would only repeat it." | It is clear to someone who read the ticket and the diff, not to the implementer. Phase D is part of the deliverable. |
| "I will clean the explanation up myself instead of dispatching." | The cleanup and the gate are two more pairs of eyes, by design. The drafter cannot audit their own rewrite. |
| "I'll read the diff to understand the change." | The candidates carry the quoted lines, and the brief holds the diff map. Reading the diff costs more than the whole judgment. |
| "I'll open b5-report.md to be sure." | Ask the consolidation agent with SendMessage. It read the report. |
| "I'll write the structured review myself, it's faster." | A token you write costs five times one you read, and the writer renders it from your decisions. |
| "I'll log progress while I wait." | Each extra turn re-reads all context. |
