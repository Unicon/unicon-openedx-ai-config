# Brief: pin, read, write the shared brief

Agent: `general-purpose`, model Sonnet, effort high, budget 30 tool calls.

Read `review-rules.md` first. Paths to other skill files, such as `review-rules.md` and
`agents/report-format.md`, are relative to the skill directory, whose absolute path the dispatch's Read line gives (the directory that holds `review-rules.md`), not to `agents/`. The dispatch names the review target, the working directory, and, for a
frontend review, the path of the component-tree outline. You write every file below into that
working directory, never into the checkout under review, and you end with the hand-back at the
bottom of this file. You never ask the user anything: when you cannot continue, you stop and
report it in the hand-back. You cannot dispatch sub-agents.

These are lookups and quoting, not judgment. Read the ticket, the PR body, and the diff; do not
read source files, the review wave does that.

**Files you write.** In the working directory, with these names:

- `pr<N>-body.md`: the pull request body, for a pull request.
- `ticket-<N>.json`: one file for each ticket you fetch, where `<N>` is the ticket number.
- `pr<N>.diff`: the diff, for a pull request. For any other target, `<slug>.diff`.
- `brief-<slug>.md`: the shared brief. `<slug>` is `pr<N>` for a pull request, and the branch
  name with `/` replaced by `-` otherwise.

**A1. Target and ticket.** Identify the repository and the review target: a pull request, a
branch, a commit range, or the working tree. Confirm the refs resolve (`git rev-parse`) and the
diff is non-empty. When a ref does not resolve, stop and report `BLOCKED: ref <x> does not
resolve`; when the diff is empty, stop and report `BLOCKED: the diff is empty`. For a pull request, use its actual base and head SHAs from `gh pr view`; do
not assume the checked-out branch matches.

Then identify the ticket that defines the requested change. Accept ticket text already in the
dispatch, a ticket URL or issue number, a ticket linked in the PR description, or a local
ticket file the dispatch names. If none is available, stop and report `NO TICKET` in the
hand-back.

Do not infer the ticket from the branch name, PR title, commit messages, or the code. When the
ticket is a child of a larger ticket, follow the parent links to the ticket that states the
acceptance criteria, then use the child to select the subset this change is on the hook for;
say which criteria you excluded and why. When ticket or PR discussion appears to have superseded
a criterion, do not assume the criterion changed: stop and report `CONFLICT: <one sentence per
criterion>` in the hand-back. When a ticket, the PR, or a ref cannot be fetched, stop and report
`BLOCKED: <what could not be fetched>`. Fetch the tickets the PR body or the ticket names as
siblings, consumers, or design sources, and save each as `ticket-<N>.json` for B2.

Record: repository, target, base and head SHAs, merge-base, ticket number and `updated_at`.

**A2. Diff and delta.** Pull request: `gh pr diff` at the recorded base and head. Branch:
three-dot diff against the intended base (`git diff <base>...<head>`); when the base is not
clear, stop and report `BLOCKED: base of the branch is not clear`. Working tree: status plus
staged and unstaged diffs, untracked files only when clearly part of the change. Write the
diff to its file and confirm it is complete; when it is not, stop and report `BLOCKED: the diff
is incomplete, <what is missing>`. Then list what landed on `main` after
the branch point in the apps the change touches and in any app that depends on them:
`git log --oneline <merge-base>..<main> -- <paths>`. The checked-out tree does not contain those
commits, so a reader of HEAD reasons from a stale picture: a new field on a model this change
constrains, a migration number this change reuses, a changed foreign key, a new consumer.

**A3. Criteria and claims.** Quote every applicable acceptance criterion, numbered, from the
ticket. Then list, numbered, every factual claim about how a framework, library, database,
precedent, or document behaves that appears in the PR body, the commit message, and the comments
and docstrings the diff adds or changes: default settings, transaction isolation and locking,
validation order, what a cited precedent does, what a cited ADR or ticket says, which constraints
exist, which tests cover what. You only list them here; B3 verifies them.

**A4. The shared brief.** One file, `brief-<slug>.md`, at most 150 lines, that every B agent
reads first: the facts from A1 and A2 with the diff's path, the commits on `main` with their
SHAs, the criteria, the claims, the repository's rule locations from "Where the rules live"
below, the sibling-ticket files with one line each, the environment (venv, `PYTHONPATH` to the
worktree's `src/`, test command, the module `__file__` check), the read-only and no-dispatch
rules, the budget, and the output format, which the brief gives by naming
`<skill-dir>/agents/report-format.md`, where `<skill-dir>` is the absolute path of the skill
directory, the one the dispatch's Read line gives.
Full sentences, no em dashes, at most 2,500 words.

The brief also holds a "Diff map" of at most 60 lines, inside the 150-line limit: one or two
lines for each changed file, saying what changed and which symbols (functions, classes, fields)
it touches. You write it from the diff alone.

When the dispatch names the path of a component-tree outline, the brief includes this line,
with that path filled in: "Read `<absolute path of the outline>` after this brief: the PR's
component tree, one line per component, with a note on each changed component and changed
module." That line counts toward the brief's 150 lines; the outline does not.

Where the rules live, so the brief can name them and B1 can find the rest:

- **`openedx-core`**: `.claude/CLAUDE.md`, `.claude/architecture-overview.md`, `.importlinter`,
  the identifier conventions in `README.rst`, and `docs/<app>/decisions/` per app. A published
  Django library installed into `edx-platform`; the lower layer, it never imports from
  `edx-platform`. Public APIs are contracts; breaking a non-`UNSTABLE` API goes through DEPR.
- **`edx-platform`**: its own `docs/decisions/`, per-app `docs/decisions/`, and the OEPs in
  `../openedx-proposals`. Consumes `openedx-core` through `content_libraries` and
  `content_tagging`, and serves the CMS REST APIs the MFEs call.
- **`frontend-app-authoring`**: `AGENTS.md` at the root is authoritative for TypeScript,
  imports, data fetching, testing, and i18n; also
  `.claude/frontend-app-authoring-architecture-overview.md` and the frontend section of
  `.claude/CLAUDE.md`; decisions in `docs/decisions/` and `src/editors/decisions/`. Talks only
  to `edx-platform`'s CMS REST API.

The nearest instruction file to a changed path wins; an ADR's `Status:` line is read first,
since a Proposed, Superseded, or Obsolete ADR is context, not a rule; `CLAUDE.md` and
`AGENTS.md` are written for writing code, so a finding cites the specific line it holds the
change to.

## The hand-back

Your final message is this template filled in, at most 300 words, and nothing else. Quote each
criterion exactly as the ticket states it, and number them as in the brief. The quoted
criteria do not count toward the 300 words.

```
Brief: <path>  Diff: <path> (<n> files, <n> lines)
Target: <repo> <PR or branch>, base <sha>, head <sha>, merge-base <sha>; ticket #<n>, updated_at <timestamp>
Criteria:
1. "<quoted criterion>"
Excluded criteria: <number and reason each, or none>
Needs the user: <none | NO TICKET | CONFLICT: ... | BLOCKED: ...>
Claims listed: <n>
```

When `Needs the user` is not `none`, fill in what you have and name in the `Needs the user`
line what the user has to supply. Write `Brief: none` when you wrote no brief, and `Diff: none`
when you saved no diff.
