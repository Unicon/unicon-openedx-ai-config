# Report format for the B agents

Every B agent (B1 to B5) writes its report in this format and ends with the hand-back below.
The shared brief names the working directory; the remit file names the required table.

Paths to other skill files, such as `review-rules.md` and `agents/report-format.md`, are relative to
the skill directory, whose absolute path the dispatch's Read line gives (the directory that holds `review-rules.md`), not to `agents/`.

## Rules that apply to every B agent

- The checkout under review is read-only. Anything that runs code or changes files, such as
  running tests, merging with `main`, or breaking a code path to watch a test fail, happens in a
  temporary git worktree that you remove afterwards.
- You cannot dispatch sub-agents. When you need something you cannot fetch or run yourself, put
  it under "Needs research" and keep going; the consolidation agent fulfills it.
- Your remit file states a tool-call budget. Stay within it. Work left undone for lack of budget
  goes on the `Note` line of the hand-back. `Blocked` is only for something that stopped the
  work, because a `Blocked` line triggers a re-dispatch with the same budget.

## Where the report goes

Write the report to `b<n>-report.md` in the working directory the dispatch names: `b1-report.md`
for B1, `b2-report.md` for B2, and so on. Write it with the Write tool. When you have no Write tool, or
the Write tool refuses the path, write it with a Bash heredoc. The report never goes into your
final message.

## Report contents

In this order:

1. **Findings.** Each finding has:
   - **Title.** One line.
   - **Severity.** One of `Bug`, `Gap`, `Question`, `Suggestion`, `Nit`, as `review-rules.md`
     defines them.
   - **Anchor.** `path:line`.
   - **Evidence.** Marked CONFIRMED or INFERRED. For INFERRED, name the step that was inferred.
   - **Why it matters.** One sentence.
   - **Suggested change.**
2. **The remit's required table.** The remit file names it.
3. **Checked and found acceptable.** Anything you checked and propose no change for.
4. **Outside this remit.** When you notice something another remit owns, write one line: its
   title, its `path:line`, and the owning remit. Do not investigate it further.
5. **Needs research.** Each item says what you need and why.

Write full sentences and no em dashes. The report has at most 2,500 words.

## Review questions

Answer every question under a "Review questions" heading in the dispatch, and every question in
a `review-additions.md` section the dispatch names, each with its number. An answer that proposes a change is a finding whose title starts with the number
(`Q3: ...`). Every other answer is a line in "Checked and found acceptable" that starts with the
number. You may also raise any further concern in the same area.

## The hand-back

Your final message is this template filled in, at most 80 words, and nothing else:

```
Report: <path>
Candidates: <n> (Bug <n>, Gap <n>, Question <n>, Suggestion <n>, Nit <n>); outside-remit pointers: <n>
Review questions answered: <Q numbers, or none>; unanswered: <Q numbers, or none>
Needs research: <n>
Blocked: <none, or one sentence>
Note: <optional, one sentence>
```

`Blocked` is exactly `none` when the work finished. Write a reason on it only when something
blocked you. Any other remark goes on the optional `Note` line.
