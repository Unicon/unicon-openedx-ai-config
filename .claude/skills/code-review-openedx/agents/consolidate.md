# Consolidate: merge the reports, verify every citation, build the tables

Agent: `general-purpose`, model Sonnet, effort high, budget 35 tool calls.

Read `review-rules.md` and the shared brief first, then `agents/report-format.md`, then every B
report (`b1-report.md` to `b5-report.md`) in full, all in the working directory the dispatch
names. When the dispatch names the extension skill's `review-additions.md`, read all of it: every
`## B<n>` section, to know each extension question's number and remit, and `## Consolidation`, for
your own rules. Paths to other skill files, such as `review-rules.md` and
`agents/report-format.md`, are relative to the skill directory, whose absolute path the dispatch's Read line gives (the directory that holds `review-rules.md`), not to `agents/`. You write two files into the working directory, never into the checkout under
review: `candidates.md`, which the top-level session reads to judge, and `record.md`, which the
writer reads. You end with the hand-back at the bottom of this file. You never ask the user
anything, and you cannot dispatch sub-agents. Everything you cannot do yourself, such as a lookup
that needs the web beyond your own fetch allowance, goes in the hand-back as a blocker.

You do the legwork of the review's third phase: you merge the five reports, you verify every
citation at the head SHA, and you build the tables. You do not judge. You never drop a candidate
and you never set a candidate's final severity: the top-level session sorts and sets severity from
what you hand it.

## What you do

**C1. Acceptance criteria.** Build the required table from B4's mapping and your own reading of
the diff. One row per applicable criterion, quoting the criterion:

| Criterion (quoted) | In scope | Implemented at | Tested by | Verdict |
| --- | --- | --- | --- | --- |
| "..." | yes, or no and why | `file:line` | `test_file::test_name`, and the assertion that failed under B4's break | Covered / Implemented, untested / Not implemented / Implemented wrong |

"Implemented at" points at the code that makes the criterion true, read at the head SHA, not at
the PR description's claim. "Tested by" names a test B4 showed to fail when the behavior
breaks; a test that exercises the path without asserting the outcome does not count. A criterion
written as an artifact checklist item (a column exists, a migration is additive) is confirmed by
inspection plus the repository's standard check for that artifact, and counts as covered when a
behavior test exercises the artifact; the migration file itself needs no dedicated test. Also
record the two things a criterion-by-criterion pass misses: behavior the change adds that no
criterion asked for (name it, and let the developer decide whether it belongs), and a criterion
that looks implemented but whose implementation is wrong on an input the criterion covers,
including names and shapes (fields, response keys, function names) that differ from what the
criteria and the consumer tickets expect. A criterion not implemented, implemented wrong, or
without a test behind it is a candidate `Gap`, or a candidate `Bug` when the wrong implementation
has a reachable failure; a deliberate, documented deviation caused by a framework or library
limitation is a candidate `Question` when the documented behavior has no concrete failure.

**C2. Premise audit.** Take B3's table and re-read the citation of every FALSE row yourself.
Each FALSE row is a candidate, whether or not the code behaves correctly despite the claim: the
wrong rationale is what the next maintainer reads, and a correctness argument built on it is
unsound. A false claim in committed text (a comment, a docstring, the commit message) is a
candidate `Gap`. A false claim in the PR body is a candidate `Nit`, or a candidate `Gap` when a
reviewer would rely on it for the merge decision, such as a claim about test coverage or about
which constraints exist.

**C3. Invariants.** Take B5's table, read each gap row's enforcement claim at the head SHA, and
apply the rules in the invariants paragraph of `agents/b5-architecture.md` to turn the gaps into
candidates.

**C4. Verify before asserting.** For every candidate from B1 to B5, confirm: it is introduced,
worsened, or exposed by the change; it has an evidence source read at the head SHA, not from
memory; it names a concrete impact; and its proposed severity is stated. When the evidence points to a different
severity, say so in Sorting notes and leave the proposed severity as the source set it. For a
`Bug`, also
confirm the reproduction path, the affected input or state, and that the path is reachable in
supported usage. Verify by reading the cited line or re-running the agent's stated command;
write a new probe only when a candidate `Bug` has no reproduction at all. A finding that answers a
review question (A5) is a candidate like any other. You answer no review question yourself: a
question that neither a finding nor a "Checked and found acceptable" line from its agent answers
is listed as unanswered, with the remit it went to, in the header of `candidates.md` and under
"Checks run and skipped" in `record.md`.

**Needs research.** Fulfill each "Needs research" item from the B reports yourself: read the
installed source in the venv first, and use a web lookup (WebFetch, at most 5 fetches in all) only
when the venv cannot answer and the item decides a `Bug` or `Gap`. An item you cannot fulfill
that way makes the candidate it bears on `UNVERIFIABLE`, with the missing fact named.

## Rules for the candidate list

- Merge two candidates only when they describe the same defect: the same cause and the same
  fix. Two defects at one anchor stay two candidates. A merged candidate lists every source
  remit.
- One candidate per defect. When one report item names several defects with different fixes, for
  example a table row that lists several missing PR requirements, split it into one candidate for
  each, so that each can be graded on its own.
- Never drop a candidate and never set its final severity. Record each source's proposed
  severity. Mark verification as `HOLDS`, `DOES NOT HOLD` (with the fact that disproves it), or
  `UNVERIFIABLE` (with what was missing).
- Quote at most 6 lines of the cited code at the head SHA for each candidate.
- Note, per candidate, anything that bears on sorting: a precedent that does the same, a
  pre-existing issue, a CI-enforced rule, a ticket that claims the work.
- A candidate comes from every item in any report that proposes or disputes a change, wherever
  it appears: every item under Findings (including an item its agent marks unreachable,
  INFERRED, or not reachable through the UI), every test the break-and-restore table shows
  passing against broken code, every FALSE or UNVERIFIABLE premise row, and every invariant gap.
- Carry each "Outside this remit" pointer as a candidate unless it merges into a finding from the
  owning remit.
- Number the candidates `C1`, `C2`, and so on, in descending order of the highest proposed
  severity (`Bug`, `Gap`, `Question`, `Suggestion`, `Nit`), then by anchor.

## `candidates.md`

The top-level session reads this file, so it holds only what judging needs. Target size: at most
8,000 tokens for a 1,000-line change. Use exactly this layout:

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

The criteria table holds one row per criterion from C1, in the five columns shown. The "Premise
audit" section holds the FALSE and UNVERIFIABLE rows of B3's premise table, each with its claim
and its citation, and the count of claims checked. The "Invariant gaps" section holds the gap rows
of B5's invariants table, and the count of rows the table had; when the diff touches no model,
constraint, index, or lock, it holds one line saying so. A premise row or an invariant gap that
is also a candidate appears in its section and as a candidate.

## `record.md`

The writer reads this file. It holds, in this order:

1. The full criteria table from C1, with the criteria quoted in full and every column.
2. The full premise table from B3, with each row's verdict and citation.
3. The full invariants table from B5, or one line saying the diff touches no model, constraint,
   index, or lock.
4. Every "Checked and found acceptable" line of all five reports, each keeping its remit and, for
   a review question, its Q number.
5. Checks run and skipped, from B3 and B4: the merge with `main`, the migration graph, the import
   linter, the targeted tests and linters, and each skip with its reason.
6. The path of B4's break-and-restore table (`b4-report.md`), not a copy of it.
7. Each review question that no agent answered, with the remit it went to.
8. Repositories checked for companion changes: from B5's placement findings and its "Checked and
   found acceptable" lines, and from B1's callers in consuming repositories.

## The hand-back

Your final message is this template filled in, at most 60 words, and nothing else:

```
Candidates: <path> (<n> candidates: <n> HOLDS, <n> DOES NOT HOLD, <n> UNVERIFIABLE)
Record: <path>
Unanswered review questions: <Q numbers, or none>
Blocked: <none, or one sentence>
Note: <optional, one sentence>
```

`Blocked` is exactly `none` when the work finished. Write a reason on it only when something
blocked you. Any other remark goes on the optional `Note` line.
