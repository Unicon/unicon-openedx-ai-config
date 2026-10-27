# Scoring: variant A = Claude Code built-in `code-review`, effort high, invoked through the Skill tool from a dispatched general-purpose orchestrator (model fable) whose brief named the frozen worktree. Report = reports/A_final.md

Not scoreable. Both permitted invocations of the skill reviewed the developer checkout (/Users/jesperhodge/openedx/openedx-core, branch tbain/776_archived_deletion_locked, range 24b3f71..HEAD by the fork's own statement) instead of wt-A. The fork resolves `pr-base..pr-head` against the process's primary working directory and did not pick up the absolute checkout path or the SHAs the orchestrator stated in the conversation immediately before the second call. None of the 16 findings across the two runs touches a file in `git diff pr-base pr-head`; the identifier most of them concern (deletion_locked) does not occur anywhere at pr-head.

Coverage 0/45 by construction; excluded from the comparison table. Kept as the evidence behind the procedure change: a built-in forked skill has to run as a separate process whose working directory is the worktree (variant C).

Cost: orchestrator about 224k tokens, 17 tool uses, 11.7 min wall clock, two forked skill runs of about 4 min each whose internal fan-out is not visible.
