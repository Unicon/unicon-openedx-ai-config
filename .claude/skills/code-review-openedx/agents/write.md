# Write: render the structured review (C6) and the explanation draft (D1)

Agent: `general-purpose`, model Sonnet, effort high, budget 15 tool calls.

Read `review-rules.md` first. Paths to other skill files, such as `review-rules.md`, are
relative to the skill directory, whose absolute path the dispatch's Read line gives (the directory that holds `review-rules.md`), not to `agents/`. The
dispatch names the working directory and the review's `<slug>`: `pr<N>` for a pull request, and
the branch name with `/` replaced by `-` otherwise. In that working directory, never in the
checkout under review, you read:

- `brief-<slug>.md`, the shared brief, for the inputs.
- `candidates.md`, the consolidation agent's candidate list. Every finding's text comes from its
  candidate here.
- `record.md`, the consolidation agent's record, for the tables and the lists of checks.
- `decisions.md`, the top-level session's decisions on the candidates, in exactly this format:

  ```
  Verdict: Ready to merge: <yes | with fixes | no>. <one sentence why>
  C1: <Bug | Gap | Question | Suggestion | Nit>
  C2: drop: <the fact that disproved it>
  C3: declined: <owning ticket> must <what>; it can, because <reason>
  C4: <severity> | text: <replacement claim, only when the candidate's claim or impact is wrong>
  Open questions:
  - <question for the developer>
  ```

You write two files into the working directory: `review-<slug>-c6.md` (the structured review)
and `review-<slug>-d1-explanation.md` (the explanation draft), and you end with the hand-back
at the bottom of this file. You never ask the user anything, and you cannot dispatch
sub-agents. Everything you cannot do yourself goes in the hand-back as a blocker.

**Whose word goes where.** You render; you do not judge.

- Every finding's text (title, anchor, claim, evidence, impact, fix) comes from its candidate in
  `candidates.md`. When `decisions.md` gives a `text:` for a candidate, use that text in place
  of the candidate's claim and impact.
- A candidate's severity comes from its line in `decisions.md`, never from the candidate's
  proposed severity. A candidate marked `drop:` goes under "Dropped" and nowhere else. A
  candidate marked `declined:` goes under "Declined to judge" and nowhere else.
- The verdict, the drops, the declines, and the open questions come from `decisions.md`.
- You add no finding and change no severity. A candidate that `decisions.md` does not mention
  is a blocker: name it in the hand-back and leave it out.

## C6. The structured review

The review output has these parts, in this order:

1. **Verdict.** `Ready to merge: yes | with fixes | no`, and one sentence why. Copy it from
   `decisions.md`.
2. **Inputs.** Repository, target, base and head SHAs, merge-base, ticket number and
   `updated_at`, the commits on `main` that changed the picture, and the repositories checked
   for companion changes. Copy all of them from the brief except the repositories checked for
   companion changes: take those from the "Repositories checked for companion changes" item
   of `record.md`.
3. **Acceptance criteria.** The table from `record.md`.
4. **Premise audit.** The FALSE and UNVERIFIABLE rows from `record.md`, and one line saying how
   many claims were checked in total.
5. **Invariants.** The gap rows from `record.md` and one line saying how many rows the table
   had, when the diff touches a model, constraint, index, or lock; otherwise one line saying it
   does not.
6. **Findings**, grouped by severity as `review-rules.md` defines them (its "Severities"
   section), each with a `file:line` anchor and its evidence.
7. **Tests checked.** B4's break-and-restore table as returned. `record.md` gives the path of
   `b4-report.md`; copy the table from there without rewording it.
8. **Checks run and skipped**, with the reason for each skip, including the merge with `main`
   and every review question its agent left unanswered. Copy them from `record.md`.
9. **Declined to judge.** One line per behavior considered and set aside as outside the ticket,
   with what the owning ticket must do and why it can do so against this change.
10. **Dropped.** One line per candidate whose evidence did not hold, with the fact that
    disproved it.
11. **Open questions** for the developer.

Render each finding in this shape: the title, the severity, the `path:line` anchor, the point and
then the mechanism in one to three sentences (from the candidate's Claim and Impact, or the
`text:` override), the evidence in one sentence (from Verification), and the fix in one sentence.
You never copy a candidate's field labels ("Claim:", "Evidence:", "Code at head:"), its quoted
code, or its sorting notes into C6 or D1. Keep the tone
of one engineer to another: direct, specific, no praise padding and no "strengths" section. A
`Bug` or a `Gap` means the verdict is not "yes". Keep the two axes separate: a clean convention
pass does not soften a criterion `Gap`, and full criteria coverage does not excuse a layering
violation. If nothing is wrong, say so plainly, with the tables that show it.

## Phase D: explain

The C6 output is written for a reviewer who has read the ticket, the diff, and this skill. It
uses the severity vocabulary, `path:line` anchors, and names coined in the conversation that
produced it, such as "the opt-out" or "the moved base". The engineer who implemented the
change, and anyone else who did not sit in the review, cannot follow it without that context.
Phase D produces the text they can follow. It is part of the deliverable, not an optional
summary: a review without it is not finished.

**D1. Draft.** Write the findings out for one reader: the engineer who implemented the change,
who knows the framework but not this codebase's history, the ticket thread, or the sibling
tickets. The draft has these parts, in this order:

1. A one-paragraph lead: the verdict and what the reader has to do.
2. A prerequisites section, marked skippable, that defines every term and relationship the
   findings lean on: the models and fields involved and what each is for, the mechanism the
   change adds, every name the ticket or the PR coined (an "opt-out", an "escape hatch"), the
   sibling tickets and what each one owns, the consuming repository and how it reaches this
   code, and the method the review used to test the tests (break the line, run the suite).
   Each definition comes from the code or the tickets, and the draft says where.
3. The findings, grouped in this order: "Must fix before merge" (every `Bug` and `Gap`),
   "Decisions to make or write down" (every `Question`), "Improvements worth doing" (every
   `Suggestion`), and "Small things" (every `Nit`). Each finding says, in full sentences and in
   this order: what is wrong, where (file and function, no line numbers), what the review
   observed or ran to establish it, why it matters to a user or to a later ticket, and what to
   do. A finding restates the context it needs rather than pointing at an earlier finding.
4. "Things the review looked at and is leaving to other tickets": the Declined to judge items,
   each with the ticket that owns it.
5. "What passed": the checks and the test counts, in one paragraph.
6. An action list, numbered, one line per action.

Every finding in C6 appears in D1, and D1 adds nothing C6 did not establish. The severity words
are not needed in the text; the grouping carries them. Each D1 finding is as concise as a C6
finding: say each of the five things in full sentences, and add no quoted code and no restated
candidate fields.

**Answers to review questions.** Every review question the dispatch lists under "Review questions"
gets its answer in D1, in its own section placed after
"What passed" and before the action list. Each answer carries its Q number and comes from
`record.md` (a "Checked and found acceptable" line that starts with that number) or from the
finding whose title starts with it. A question that no agent answered is listed there as
unanswered, with the remit it went to. Writing the answers into the D1 draft is what lets the
cleanup and the accuracy gate cover them.

## The hand-back

Your final message is this template filled in, at most 80 words, and nothing else. List finding
IDs as the `C<n>` numbers from `candidates.md`, and write `none` for an empty group:

```
C6: <path>  D1: <path>
Bug: <IDs>; Gap: <IDs>; Question: <IDs>; Suggestion: <IDs>; Nit: <IDs>
Declined: <IDs>; Dropped: <IDs>
Review questions answered in D1: <Q numbers, or none>
```

End the template with `Blocked: none` when the work finished. Write a reason on that line only
when something blocked you: `Blocked: <one sentence>`. Any other remark goes on an optional last
line, `Note: <one sentence>`.
