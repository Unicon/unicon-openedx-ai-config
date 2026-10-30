# B1: Locate

Agent: `general-purpose`, model Haiku, effort default, budget 25 tool calls.

Read `review-rules.md`, the shared brief, and `agents/report-format.md` first, in that order.
When the dispatch names a section of the extension skill's `review-additions.md`, read that
section too. Write your report as `agents/report-format.md` says, and end with the hand-back
it defines. Paths to other skill files, such as `review-rules.md` and `agents/report-format.md`,
are relative to the skill directory, whose absolute path the dispatch's Read line gives (the directory that holds `review-rules.md`), not to `agents/`.

List the instruction files and ADRs that govern the changed
paths, with their `Status:` lines; the callers of each changed or new public symbol in this
repository and in the consuming repositories named in the brief; and the tests that import the
changed modules. Paths and line numbers only, no judgment.

## Red flags

| Thought | Reality |
| --- | --- |
| "There is no `AGENTS.md`, so there are no conventions to check." | `openedx-core` and `edx-platform` keep theirs in `CLAUDE.md`, ADRs, OEPs, and `.importlinter`. |
