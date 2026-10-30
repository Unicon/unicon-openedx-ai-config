# B3: Mechanical checks

Agent: `general-purpose`, model Sonnet, effort high, budget 35 tool calls.

Read `review-rules.md`, the shared brief, and `agents/report-format.md` first, in that order.
When the dispatch names a section of the extension skill's `review-additions.md`, read that
section too. Write your report as `agents/report-format.md` says, and end with the hand-back
it defines. Paths to other skill files, such as `review-rules.md` and `agents/report-format.md`,
are relative to the skill directory, whose absolute path the dispatch's Read line gives (the directory that holds `review-rules.md`), not to `agents/`.

In a temporary worktree, with
`PYTHONPATH` to its `src/` and the module `__file__` confirmed:

1. **Merge with `main`.** From a worktree at `main`, `git merge --no-commit --no-ff <head>`;
   list the conflicting files; on the merged tree (or on `main` plus the change's migration
   files when the merge conflicts in files the change did not touch) run the repository's
   migration graph check (in Django, `makemigrations --check --dry-run` and `migrate --check`)
   and its import linter; abort the merge. A migration-number collision, a conflicting leaf
   node, or a linter contract broken by the merge is a `Bug`: the branch cannot merge as it
   stands.
2. **Targeted tests and checks** the repository's instructions name for this kind of change:
   in `openedx-core`, pytest without coverage on the related tests and the linters named in
   `CLAUDE.md`; in `frontend-app-authoring`, that repository's own tools from its `AGENTS.md`.
   Report what ran and what was skipped and why. A skipped check is not a pass.
3. **The premise lookups.** For each numbered claim in the brief, verify it against the
   installed source (find the file with `python -c "import <pkg>; print(<pkg>.__file__)"` and
   read the line) or against this repository's own code and documents, never against memory.
   When a claim concerns a database default (isolation level, strict mode, locking), read the
   framework's backend source for that setting before any database manual: the framework may
   override the database's own default. Return the table: claim | where it appears | checked
   against (`file:line` or the command run) | TRUE, FALSE, or UNVERIFIABLE | consequence if
   false.
