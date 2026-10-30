# B2: Context and prose

Agent: `general-purpose`, model Sonnet, effort high, budget 35 tool calls.

Read `review-rules.md`, the shared brief, and `agents/report-format.md` first, in that order.
When the dispatch names a section of the extension skill's `review-additions.md`, read that
section too. Write your report as `agents/report-format.md` says, and end with the hand-back
it defines. Paths to other skill files, such as `review-rules.md` and `agents/report-format.md`,
are relative to the skill directory, whose absolute path the dispatch's Read line gives (the directory that holds `review-rules.md`), not to `agents/`.

From the sibling tickets and
the design discussion: every expectation they state about this change's names, shapes,
functions, and order of operations, with the ticket and line; the lifecycle they describe
(archive, delete, replace, re-create) for the rows this change creates; and any contradiction
between them, the ticket, and the ADRs. From git: the blame and log of the changed code and
prior PR review comments on the same files, for a constraint the change may have missed. From
the diff: for each comment the change adds, whether the code would be clear without it and
whether it is as short as it can be; most comments should be one or two lines unless the file
already follows a pattern of longer ones; a comment says why, not what, and a comment the change
made stale is a bug. From the commits: the subjects and messages the change adds, for wording
errors and typos (a `Nit`). From the PR: the description states which AI agent was used or that none
was; it gives manual testing steps or states that the change has no manual QA path; its
description matches the diff (file names, counts, claims about tests).
