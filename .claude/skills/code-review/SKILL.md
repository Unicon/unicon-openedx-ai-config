---
name: code-review
description: "Senior peer review of a diff in an Open edX repository (openedx-core, edx-platform, frontend-app-authoring). Use when asked to review a pull request, branch, commit range, or working tree, and as the parent skill that backend-code-review and frontend-code-review extend; prefer one of those two when the change is clearly backend or frontend. Review-only: findings with file:line anchors and a severity marker; never fixes, commits, or pushes. Posts to GitHub only when explicitly asked and approved."
---

# Code review

A senior peer review of a change in the Open edX ecosystem. The review answers two separate
questions and keeps their answers separate. Is this the right thing: every acceptance criterion
of the ticket is implemented correctly and covered by a test that fails when the behavior
breaks. Is it built right: the code follows the conventions, ADRs, and layering of the
repository it lands in, and sits in the right repository at all. A change can pass one question
and fail the other, and a pass on one never offsets a failure on the other.

The review surfaces what is wrong and why, with evidence, and lets the developer decide what to
act on. It never applies fixes, commits, or pushes. It posts to GitHub only when the developer
asks and approves the wording.

This skill runs in the top-level session, directly or as the final step of `spike-and-stabilize`.
Per the Delegation rule in `CLAUDE.md`, that session is the only one that dispatches the
sub-agents this skill names; a dispatched sub-agent never dispatches a further one. When a
sub-agent needs something it cannot fetch, it returns a "Needs research" item and the top-level
session fulfills it.

## What the review must establish

Every review ends with evidence for each of these points, or a finding where the evidence is
missing:

1. Every applicable acceptance criterion is implemented, and implemented correctly.
2. Every applicable acceptance criterion is covered by at least one test that fails when the
   behavior it describes breaks. One test may cover several criteria, and one criterion may
   need several tests. A criterion with no test behind it is not acceptable.
3. The new and changed tests are meaningful: each fails when the code it covers is broken, and
   it fails for the reason its name states.
4. The code follows the documented conventions of the repository it lands in, and the ADRs and
   OEPs that govern the area it touches.
5. Each piece of the change lives in the right repository and layer, and any companion change
   another repository needs either exists or is tracked.
6. The change introduces no bug, security, data-integrity, or performance regression.
7. The pull request meets the Open edX community's requirements for a PR.

## Review-wide rules

- Review only issues introduced, worsened, or exposed by the change. Report a pre-existing
  issue only when the change makes it newly relevant to the requested behavior or contract.
- Every finding carries one of three kinds of evidence: a quoted acceptance criterion; a cited
  rule, as file plus rule, from an instruction file, ADR, or OEP; or a reproduction path with a
  concrete affected input and a `file:line`. A preference with none of those is not a finding.
- A `Bug` needs a failure reachable through supported product inputs, supported API data, or a
  documented contract. A mathematically possible counterexample on data the product cannot
  create is a `Question` or a `Suggestion`, or nothing.
- Specification silence is not permission. For behavior the ticket does not mention, judge by
  what a reasonable user of the software would expect, and grade the finding by its effect on
  that user.
- Live source: for GitHub issues and pull requests, cached search results and indexed snapshots
  are never authoritative. Fetch the current issue and PR with `gh`, and record the issue's
  `updated_at` and the PR's base and head SHAs in the review. If they cannot be fetched, stop
  and report the review as blocked. Do not substitute a branch name, a PR description, or an
  older snapshot.
- A sub-agent's finding is a hypothesis. Read its citation against the actual code at the head
  SHA before it becomes a finding of this review.
- The review is read-only on the checkout under review. Anything that runs code or changes
  files, such as running tests or breaking a code path to watch a test fail, happens in a
  temporary git worktree at the head SHA that is removed afterwards.
- Do not report what CI tooling already enforces: formatting, lint, type errors, import order.
  Do run the targeted tests and checks the repository's instructions name, and report results.

## Who does what

| Work | Agent, model, effort |
| --- | --- |
| Locate instruction files, ADRs, and callers of changed code ("where is X") | `Explore`, Haiku, default |
| Fetch and condense a long issue or PR thread; read git history and prior PR comments on the touched files | `Explore` or `general-purpose`, Sonnet, medium-high |
| Break-and-restore checks on tests, and running targeted tests, in a temporary worktree | `general-purpose`, Sonnet, high |
| Architecture, ADR adherence, and cross-repository placement judgment | `software-architect`, Opus, xhigh |
| Acceptance-criteria table, severity calls, final verdict | the top-level session, inline |

Pass `model` explicitly on every dispatch. Give each sub-agent the context it needs in its
brief (ticket text, SHAs, file lists, the relevant rules), never this session's history. Tell it
in the brief that it cannot dispatch and must return a "Needs research" item for anything it
cannot do itself.

## 1. Pin the target and the ticket

Identify the repository and the review target: a pull request, a branch, a commit range, or
the working tree. Confirm the refs resolve (`git rev-parse`) and the diff is non-empty before
anything else. For a pull request, use its actual base and head SHAs from `gh pr view`; do not
assume the checked-out branch matches.

Then identify the ticket that defines the requested change, before inspecting the diff. Accept
ticket text already in the conversation, a ticket URL or issue number, a ticket linked in the
PR description, or a local ticket file the developer names. If none is available, stop and ask:

> Please provide the ticket or issue for this change, as a URL, an issue number, or the ticket
> linked in the pull request description. I need it to review scope and completeness, and I
> won't begin the review until I have it.

Do not infer the ticket from the branch name, PR title, commit messages, or the code.

When the ticket is a child of a larger ticket, follow the parent links to the ticket that
states the acceptance criteria, then use the child to select the subset this change is on the
hook for. Say which criteria you excluded and why. When ticket or PR discussion appears to have
superseded a criterion, flag the conflict and ask; do not assume the criterion changed.

Record for the review: repository, target, base and head SHAs, ticket number and `updated_at`.

## 2. Ground the review in the repository's rules

Read the rules before reading the diff, so the diff is judged against them rather than against
memory. The three repositories keep their rules in different places, and only one of them has
an `AGENTS.md`.

**`openedx-core`**

- Conventions: `.claude/CLAUDE.md` (symlinked into the workspace), `.claude/architecture-overview.md`,
  `.importlinter`, and the identifier conventions in `README.rst`.
- Decisions: `docs/<app>/decisions/` for each app (`openedx_content`, `openedx_tagging`,
  `openedx_learning`, `openedx_core`).
- Relationship: a published Django library installed into `edx-platform`. It is the lower layer
  and never imports from `edx-platform`. Public APIs are contracts; breaking a non-`UNSTABLE`
  API goes through DEPR.

**`edx-platform`** (also called `openedx-platform`)

- Conventions: its own `docs/decisions/`, per-app `docs/decisions/` folders, and the OEPs in
  `../openedx-proposals`.
- Relationship: consumes `openedx-core` through `openedx/core/djangoapps/content_libraries`
  (backed by `openedx_content`) and `content_tagging` (backed by `openedx_tagging`), and serves
  the CMS REST APIs the MFEs call. Models related to one feature may live in either repository.

**`frontend-app-authoring`**

- Conventions: `AGENTS.md` at the repository root is authoritative for TypeScript, imports, data
  fetching, testing, and i18n. Also `.claude/frontend-app-authoring-architecture-overview.md`
  and the frontend section of `.claude/CLAUDE.md`.
- Decisions: `docs/decisions/` and `src/editors/decisions/`.
- Relationship: talks only to `edx-platform`'s CMS REST API and has no code dependency on
  `openedx-core`. A content or tagging feature reaches an author as an `openedx-core` model or
  API change, then an `edx-platform` endpoint, then the MFE's `api.ts`, hook, and UI.

Rules for using them:

- The nearest instruction file to a changed path wins over a more general one.
- Read an ADR's `Status:` line first. A Proposed, Superseded, or Obsolete ADR is context, not a
  rule, though a status line can itself be stale; section 9 of `.claude/architecture-overview.md`
  and section 9 of the frontend overview list the known cases.
- `CLAUDE.md` and `AGENTS.md` are written as guidance for writing code, so not every line in
  them is a review rule. Cite the specific line you hold the change to.
- Dispatch `Explore` (Haiku) to list the instruction files and ADRs that govern the changed
  paths, and the callers of changed public code in this and the consuming repositories. Read
  into your own context only the few files the judgment turns on.

## 3. Obtain the complete diff

- Pull request: `gh pr diff` at the recorded base and head, and confirm which files it changes.
- Branch: three-dot diff against the intended base (`git diff <base>...<head>`), so the
  comparison is against the merge-base. Ask for the base if it is not clear.
- Working tree: repository status plus the staged and unstaged diffs. Include untracked files
  only when they are clearly part of the change.
- Read the surrounding code at the head SHA so each hunk is understood in context, and confirm
  the diff was not truncated. If the diff cannot be obtained, stop and say what is missing. Do
  not review the PR description in its place.

## 4. Acceptance criteria: implemented and tested

This table is required in every review and is built before any other finding is written. One
row per applicable criterion, quoting the criterion:

| Criterion (quoted) | In scope | Implemented at | Tested by | Verdict |
| --- | --- | --- | --- | --- |
| "..." | yes, or no and why | `file:line` | `test_file::test_name`, and the assertion that would fail | Covered / Implemented, untested / Not implemented / Implemented wrong |

How to fill it:

- "Implemented at" points at the code that makes the criterion true, read at the head SHA, not
  at the PR description's claim that it does.
- "Tested by" names a test that fails when the behavior the criterion describes is broken. A
  test may appear in several rows and a row may name several tests. A test that exercises the
  code path without asserting the criterion's outcome does not count.
- A criterion written as an artifact checklist item (a column exists, a migration is additive,
  a file is present) is confirmed by inspection at `file:line`, plus the repository's standard
  check for that artifact when it has one, and counts as covered when a behavior test exercises
  the artifact, such as a test that sets and reads the new column. The migration file itself
  needs no dedicated test.
- Also look for the two things a criterion-by-criterion pass misses: behavior the change adds
  that no criterion asked for (name it, and let the developer decide whether it belongs), and a
  criterion that looks implemented but whose implementation is wrong on an input the criterion
  covers.

Severity, using the markers defined in step 9: a criterion that is not implemented, implemented
wrong, or has no test behind it is a `Gap`, or a `Bug` when the wrong implementation has a
reachable failure. A deliberate, documented deviation from a criterion's literal wording, caused
by a framework or library limitation, is a `Question` rather than a `Gap` when the documented
behavior has no concrete failure.

## 5. Tests: meaningful, and failing for the right reason

For each new or changed test, check by reading:

- The assertion checks the behavior the test name claims, through the public interface, not
  through an internal collaborator or a side channel.
- Expected values come from an independent source (a known literal, a worked example, the
  ticket), not recomputed the way the code computes them.
- The test is not coupled to the implementation: it does not mock internal collaborators,
  assert call counts or order, or inspect private state, unless the repository's own tests do
  so for this kind of code.
- The unhappy paths the changed behavior introduces (empty, error, permission, boundary) have a
  negative test.
- Values that can go stale, such as dates, use constants or fixtures, and the test matches the
  granularity of the surrounding test module rather than testing the obvious.

Then check by running a break-and-restore check on each load-bearing test: every test named in
a "Tested by" cell, and any test guarding a security or data-integrity path. In a temporary
worktree at the head SHA, break the code path the test covers, run the test, confirm it fails,
and confirm it fails on the asserted behavior rather than on an import error or an unrelated
assertion. Restore the code, and remove the worktree when done. Make the worktree runnable
without a fresh install, and confirm the run uses the worktree's code rather than the main
checkout's: in a Python repository set `PYTHONPATH` to the worktree's `src/` (the editable
install points at the main checkout) and check the module's `__file__`; in a JavaScript
repository symlink the main checkout's `node_modules` into the worktree. This work is mechanical
and heavy on context, so dispatch it to a Sonnet `general-purpose` sub-agent with the table
rows, the worktree instructions, and the test command. Read its output as claims, and spot
check one. A test that also passes against broken code is reported as a `Gap` in the row it
backs.

Run the targeted tests and checks that the repository's instructions name for this kind of
change: in `openedx-core`, pytest without coverage on the related tests and the linters named in
`CLAUDE.md`; in `frontend-app-authoring`, that repository's own tools as named in its
`AGENTS.md`. Report what ran and what was skipped and why. A skipped check is not a pass.

## 6. Architecture, conventions, and cross-repository placement

Dispatch `software-architect` (Opus, `xhigh`) once, with a narrow brief: the ticket, the diff
or its path, the acceptance-criteria table, and the instruction files and ADRs located in step
2. Ask it for findings, each with a `file:line` and the cited rule or ADR, on:

- layering and contracts: `.importlinter` boundaries, public API stability and DEPR, the
  identifier conventions (`id`, `uuid`, `key`, `num`), and PII annotations on new models;
- the ADRs that govern the touched area, whether the change follows them, and whether a
  decision the change makes should itself become a proposed ADR;
- placement: whether each piece lives in the right repository and layer, what companion change
  `edx-platform` or the MFE needs for the feature to reach its users, and whether that companion
  exists or is linked;
- callers: what in this repository, in `edx-platform`, or in community plugins the change can
  break;
- whether the test strategy fits the layer: a library API tested at the API, an endpoint tested
  through the endpoint, UI tested through what the user sees.

It cannot dispatch. Fulfill its "Needs research" items with `Explore` or a Sonnet sub-agent and
continue it with `SendMessage`. Verify each of its citations before adopting the finding.

## 7. Correctness, security, and history

Check the dimensions the diff touches, and say which you skipped:

- Correctness: logic, edge cases, error paths, off-by-one, `None` and empty handling,
  concurrency.
- Security: authentication and permission checks on new or changed endpoints, input validation,
  object-level access, injection through raw SQL or unescaped output, secrets in code or logs,
  new dependencies.
- Data integrity and migrations: backward compatibility, table locks, data loss, and ordering
  against merged migrations.
- Performance: new queries (N+1 patterns, missing `select_related`, indexes the access pattern
  needs).
- Naming, comments, and docstrings: public functions have clear names and RST docstrings that
  state the contract; comments say why, not what; a comment the change made stale is a bug.
- Surgical scope: every changed line traces to the ticket.
- History: the git blame and log of the changed code, and prior PR review comments on the same
  files, for a constraint the change may have missed. Delegate this to a Sonnet sub-agent when
  the diff is large.
- Community requirements for the PR: the description states which AI agent was used, or that
  none was; it gives manual testing steps, or states explicitly that the change has no manual
  QA path.

## 8. Verify before asserting

Before a finding is written, confirm: it is introduced, worsened, or exposed by the change; it
has an evidence source read at the head SHA, not from memory; it names a concrete impact; and
its severity matches the evidence. For a `Bug`, also confirm the reproduction path, the
affected input or state, and that the path is reachable in supported usage.

Drop, rather than downgrade, these: pre-existing issues the change does not touch; anything CI
tooling catches; nits a senior engineer would not raise on a PR; changes in behavior that are
clearly part of the requested change; issues on lines the change did not modify, unless the
change exposes them. Downgrade to a `Question` anything whose reachability or contract you could
not confirm. Checking a library's documented behavior is a web lookup; run it in a sub-agent.

## 9. Present

The review output has these parts, in this order:

1. **Verdict.** `Ready to merge: yes | with fixes | no`, and one sentence why.
2. **Inputs.** Repository, target, base and head SHAs, ticket number and `updated_at`, and the
   repositories checked for companion changes.
3. **Acceptance criteria.** The table from step 4.
4. **Findings**, grouped by severity, each with a `file:line` anchor and its evidence:
   - `Bug.` A supported, reproducible failure or documented contract violation with meaningful
     impact.
   - `Gap.` A required element is missing: a criterion not implemented or without a test that
     fails when it breaks, a companion change that does not exist, or a PR requirement not met.
   - `Question.` A plausible concern whose reachability, contract, or impact is unconfirmed.
   - `Suggestion.` Optional hardening or broader coverage without demonstrated impact.
   - `Nit.` Style or wording only.
5. **Tests checked.** For each break-and-restore check: the test, how the code was broken,
   whether the test failed, and whether it failed for the stated reason.
6. **Checks run and skipped**, with the reason for each skip.
7. **Declined to judge.** One line per behavior considered and set aside as outside the ticket,
   with the reason, so nothing is dropped silently. An empty list says so.
8. **Open questions** for the developer.

Lead each finding with the point, then the mechanism. Keep the tone of one engineer to another:
direct, specific, no praise padding. A `Bug` or a `Gap` means the verdict is not "yes". Keep the
two axes separate: a clean convention pass does not soften a criterion `Gap`, and full criteria
coverage does not excuse a layering violation. If nothing is wrong, say so plainly, with the
table that shows it.

## Red flags

| Thought | Reality |
| --- | --- |
| "The migration check covers this criterion." | A migration check proves the schema applies. It proves nothing about the behavior the criterion describes. Name the test or report a `Gap`. |
| "Existing tests cover this." | Name the test and the assertion that would fail. If you cannot, it is not covered. |
| "The tests pass, so the behavior works." | A test that also passes against broken code proves nothing. Break the code and look. |
| "There is no `AGENTS.md`, so there are no conventions to check." | `openedx-core` and `edx-platform` keep theirs in `CLAUDE.md`, ADRs, OEPs, and `.importlinter`. |
| "The ticket does not mention it, so it is fine." | Specification silence is not permission. A reasonable user's expectation is a requirement. |
| "This is a library change; the platform and the frontend are someone else's problem." | Trace the chain. A missing or unlinked companion change is a `Gap`. |
| "The sub-agent found it, so it is a finding." | It is a hypothesis until you have read its citation at the head SHA. |
| "It is only a schema change, so there is nothing to test." | The column is covered when a test sets and reads it. A column no test touches is a `Gap`. |
