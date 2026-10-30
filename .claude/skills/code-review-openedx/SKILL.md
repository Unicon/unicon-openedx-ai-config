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
Per the Delegation rule in `CLAUDE.md`, that session is the only one that dispatches the
sub-agents this skill names; a dispatched sub-agent never dispatches a further one. When a
sub-agent needs something it cannot fetch, it returns a "Needs research" item and the top-level
session fulfills it.

**Shape and timing.** The review runs in four phases: a short inline phase in which the
orchestrator pins the target, reads the ticket and the diff, and writes one shared brief; one
dispatch wave in which five sub-agents work in parallel from that brief; an inline phase in
which the orchestrator verifies, sorts, and presents; and an explanation phase in which the
orchestrator writes the findings out for the engineer who implemented the change, has a Sonnet
sub-agent clean that text up, and gates it for accuracy. Nothing in the wave waits on anything
else in the wave. A review of a 1,000-line change should finish in 15 to 20 minutes of wall
clock: phase A in about 4 minutes, the wave bounded by its slowest agent (each has a tool-call
budget of 35), phase C in about 6 minutes, phase D in about 5 minutes. A review that runs longer has usually broken one of
three rules: the orchestrator read source files instead of the diff and the ticket in phase A,
a sub-agent was dispatched after the wave instead of in it, or phase C wrote new probes instead
of reading the cited lines.

## What the review must establish

Every review ends with evidence for each of these points, or a finding where the evidence is
missing:

1. Every applicable acceptance criterion is implemented, and implemented correctly.
2. Every applicable acceptance criterion is covered by at least one test that fails when the
   behavior it describes breaks. One test may cover several criteria, and one criterion may
   need several tests. A criterion with no test behind it is not acceptable.
3. The new and changed tests are meaningful and lean: each fails when the code it covers is
   broken, fails for the reason its name states, asserts what the code does rather than how it
   is written, and no two of them assert the same behavior.
4. Every factual claim the change makes in prose about how a framework, library, or database
   behaves, in the PR body, the commit message, and the comments and docstrings it adds, is
   true.
5. Every rule the data model relies on has a stated enforcement, and that enforcement holds
   across the lifecycle the design describes (archive, delete, replace, re-create).
6. The code follows the documented conventions of the repository it lands in, and the ADRs and
   OEPs that govern the area it touches.
7. Each piece of the change lives in the right repository and layer, and any companion change
   another repository needs either exists or is tracked.
8. The change merges: no migration-graph or file conflict against the current `main`, and the
   repository's mechanical checks pass on the merged tree.
9. The change introduces no bug, security, data-integrity, or performance regression, and no
   other changed behavior with a concrete impact goes unmentioned.
10. The pull request meets the Open edX community's requirements for a PR.

## Review-wide rules

- Review only issues introduced, worsened, or exposed by the change. Report a pre-existing
  issue only when the change makes it newly relevant to the requested behavior or contract.
- Every finding carries one of three kinds of evidence: a quoted acceptance criterion; a cited
  rule, as file plus rule, from an instruction file, ADR, or OEP; or a reproduction path with a
  concrete affected input and a `file:line`. A preference with none of those is not a finding.
- A `Bug` needs a failure reachable through supported product inputs, supported API data, or a
  documented contract. Supported input includes every option the product exposes as a
  first-class setting, however rarely it is used. A counterexample on data the product cannot
  create is a `Question` or a `Suggestion`, or nothing.
- Inference lowers confidence, not severity. When the last step of a failure cannot be executed
  locally (a database the CI matrix runs and the workstation lacks), score the consequence,
  name the step that was inferred, and keep the severity.
- A defect whose evidence holds is never dropped. A precedent that does the same thing, or a
  test run that showed no symptom, lowers its severity; it does not remove it. Drop only what is
  wrong, what nothing available can verify, or what proposes no change.
- Nits are reported, not filtered. Which nits to raise on the PR is the human reviewer's call,
  and reviewers differ on it; the skill's job is to list them under `Nit` with an anchor.
- A fact used to settle a disagreement is reported. When two sources conflict (a code comment
  and the library's source, two sub-agents) and you resolve it by reading the code, every
  passage in the change that stated the losing version is a finding.
- A ticket's User Story and Acceptance Criteria are the review's instructions, and they are the
  only parts of any ticket the review reads: the ticket under review, its parent, and its
  siblings alike. The brief quotes those two sections. The Description, Context, UX Design,
  Technical Details, and Open Questions sections, and any design discussion they link, stay
  unread, because they record one author's guess at an implementation and the review judges the
  code on its own merits against the behavior the criteria describe and the repository's rules.
  When a criterion itself names a mechanism (a hook, a parameter, a query option) and the code
  delivers the behavior the criterion describes another way, that is a `Question` addressed to
  the ticket's author, not a `Gap`.
- Specification silence is not permission. For behavior the criteria do not mention, judge by
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
  files, such as running tests, merging with `main`, or breaking a code path to watch a test
  fail, happens in a temporary git worktree that is removed afterwards.
- Do not report what CI tooling already enforces: formatting, lint, type errors, import order.
  Do run the targeted tests and checks the repository's instructions name, and report results.

## Who does what, and when

| Phase | Work | Agent, model, effort | Budget |
| --- | --- | --- | --- |
| A | Pin the target and ticket, obtain the diff and the delta on `main`, quote the criteria, list the claims to verify, write the shared brief | the top-level session, inline | 10 tool calls |
| B1 | Locate instruction files, ADRs, and callers of changed code in this and the consuming repositories ("where is X") | `Explore`, Haiku, default | 25 |
| B2 | Condense the sibling tickets' user stories and acceptance criteria into expectations of this change; read git history and prior PR comments on the touched files; check comment necessity and conciseness and the PR's community requirements | `general-purpose`, Sonnet, medium-high | 35 |
| B3 | Mechanical checks in a temporary worktree: the merge with `main` and its migration graph and import linter, targeted tests and linters, the premise lookups | `general-purpose`, Sonnet, high | 35 |
| B4 | Behavior in a temporary worktree: map tests to criteria and break-and-restore each load-bearing test, enumerate and probe error paths and bounded writes, rerun the pre-existing form of edited tests, the lean-test checks | `general-purpose`, Sonnet, high | 35 |
| B5 | Architecture, ADR adherence, framework-boundary leaks, cross-repository placement, callers, the data-model invariants table | `software-architect`, Opus, xhigh | 35 |
| C | Build the tables from B's results, verify every candidate at the head SHA, sort, present | the top-level session, inline | 12 tool calls |
| D1 | Write the explanation of the findings for the engineer who implemented the change, from the C6 output | the top-level session, inline | 1 tool call |
| D2 | Run `clean-up-text` steps 1 to 5 and 7 on that explanation | `general-purpose`, Sonnet, medium-high | 25 |
| D3 | The accuracy gate, `clean-up-text` step 6, on the cleaned explanation | `doc-accuracy-reviewer`, Sonnet, high | 15 |

Pass `model` explicitly on every dispatch, and dispatch all five B agents in one message with
`run_in_background: false`, so the wave runs concurrently and the orchestrator waits for all of
them. Give each sub-agent the shared brief and its remit, never this session's history. Tell it
in the brief that it cannot dispatch, that it has a tool-call budget, and that it must return a
"Needs research" item for anything it cannot do itself. Fulfill "Needs research" items yourself
in phase C: by reading the installed source in the venv first, and by a web lookup in a
`general-purpose` Sonnet sub-agent with a budget of 5 only when the venv cannot answer and the
item decides a `Bug` or `Gap`.

## Phase A: pin, read, brief (orchestrator, inline, at most 10 tool calls)

Lookups and quoting, not judgment. Read the ticket, the PR body, and the diff; do not read
source files in this phase, the wave does that.

**A1. Target and ticket.** Identify the repository and the review target: a pull request, a
branch, a commit range, or the working tree. Confirm the refs resolve (`git rev-parse`) and the
diff is non-empty. For a pull request, use its actual base and head SHAs from `gh pr view`; do
not assume the checked-out branch matches.

Then identify the ticket that defines the requested change. Accept ticket text already in the
conversation, a ticket URL or issue number, a ticket linked in the PR description, or a local
ticket file the developer names. If none is available, stop and ask:

> Please provide the ticket or issue for this change, as a URL, an issue number, or the ticket
> linked in the pull request description. I need it to review scope and completeness, and I
> won't begin the review until I have it.

Do not infer the ticket from the branch name, PR title, commit messages, or the code. When the
ticket is a child of a larger ticket, follow the parent links to the ticket that states the
acceptance criteria, then use the child to select the subset this change is on the hook for;
say which criteria you excluded and why. When ticket or PR discussion appears to have superseded
a criterion, flag the conflict and ask; do not assume the criterion changed. Fetch the tickets
the PR body or the ticket names as siblings or consumers, extract the User Story and Acceptance
Criteria sections of each, and save those extracts for B2.

Record: repository, target, base and head SHAs, merge-base, ticket number and `updated_at`.

**A2. Diff and delta.** Pull request: `gh pr diff` at the recorded base and head. Branch:
three-dot diff against the intended base (`git diff <base>...<head>`); ask for the base if it
is not clear. Working tree: status plus staged and unstaged diffs, untracked files only when
clearly part of the change. Confirm the diff is complete. Then list what landed on `main` after
the branch point in the apps the change touches and in any app that depends on them:
`git log --oneline <merge-base>..<main> -- <paths>`. The checked-out tree does not contain those
commits, so a reader of HEAD reasons from a stale picture: a new field on a model this change
constrains, a migration number this change reuses, a changed foreign key, a new consumer.

**A3. Criteria and claims.** Quote the ticket's user story, then every applicable acceptance
criterion, numbered. Then list, numbered, every factual claim about how a framework, library,
database, precedent, or document behaves that appears in the PR body, the commit message, and
the comments and docstrings the diff adds or changes: default settings, transaction isolation
and locking, validation order, what a cited precedent does, what a cited ADR or ticket says,
which constraints exist, which tests cover what. You only list them here; B3 verifies them.

**A4. The shared brief.** One file, at most 150 lines, that every B agent reads first: the facts
from A1 and A2 with the diff's path, the commits on `main` with their SHAs, the user story and
the criteria, the claims, the repository's rule locations from the table below, the
sibling-ticket extracts with one line each, the environment (venv, `PYTHONPATH` to the
worktree's `src/`, test command, the module `__file__` check), the read-only and no-dispatch
rules, the budget, and the output format:
findings with Title, Severity (`Bug`, `Gap`, `Question`, `Suggestion`, `Nit`), Anchor
`path:line`, Evidence marked CONFIRMED or INFERRED with the inferred step named, Why it matters
in one sentence, Suggested change; then the remit's required table; then "Checked and found
acceptable" (nothing a change is proposed for); then "Needs research". Full sentences, no em
dashes, at most 2,500 words.

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

## Phase B: one dispatch wave

Each remit below is the body of one dispatch. Every agent reads the shared brief first and
returns the output format it specifies.

**B1. Locate (`Explore`, Haiku).** List the instruction files and ADRs that govern the changed
paths, with their `Status:` lines; the callers of each changed or new public symbol in this
repository and in the consuming repositories named in the brief; and the tests that import the
changed modules. Paths and line numbers only, no judgment.

**B2. Context and prose (`general-purpose`, Sonnet, medium-high).** From the sibling tickets'
user stories and acceptance criteria: every behavior they expect of this change, including the
names and shapes a consumer's criteria rely on, with the ticket and line; the lifecycle they
describe (archive, delete, replace, re-create) for the rows this change creates; and any
contradiction between them, the ticket, and the ADRs. From git: the blame and log of the
changed code and prior PR review comments on the same files, for a constraint the change may
have missed. From the diff: for each comment the change adds, whether the code would be clear without it and
whether it is as short as it can be; most comments should be one or two lines unless the file
already follows a pattern of longer ones; a comment says why, not what, and a comment the change
made stale is a bug. From the PR: the description states which AI agent was used or that none
was; it gives manual testing steps or states that the change has no manual QA path; its
description matches the diff (file names, counts, claims about tests).

**B3. Mechanical checks (`general-purpose`, Sonnet, high).** In a temporary worktree, with
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

**B4. Behavior and tests (`general-purpose`, Sonnet, high).** In a temporary worktree:

1. **Map and break.** For each criterion in the brief, name the test that fails when the
   behavior it describes is broken, and the assertion that fails; then break the code path,
   run the test, confirm it fails on the asserted behavior rather than on an import error,
   restore. Do this for every test so named and for any test guarding a security or
   data-integrity path. Return the mapping and a table: test | how the code was broken | failed?
   | failed for the stated reason? A test that also passes against broken code is reported.
2. **Error paths, enumerated.** For each new endpoint or public function, read the source of
   every callee it invokes and list each exception the callee can raise; check that each one is
   handled or mapped to a client response. Put every unmapped path, every criterion's negative
   case, each first-class configuration option of the input types, a value at the maximum
   length of every input that is concatenated into a stored field, and malformed input through
   any permission check that runs before validation into one probe file, and run it once. Report
   each unhandled error as a reproduction with the input and the exception.
3. **Bounded writes and check order.** Every generated value stored in a column with a length
   limit, checked against the maximum lengths of its inputs; when a permission predicate
   receives raw client input, what the production predicate (not the test stub) returns for
   malformed input, read in the consuming repository if it lives there.
4. **Edited tests.** For every pre-existing test the diff edits, run the pre-existing form
   against the new code. If it passes, the edit was unnecessary and its comment is suspect.
5. **Lean tests.** For the new and changed tests: two tests that assert the same behavior;
   tests of boilerplate or of the obvious (a default value, a field's presence) that the
   surrounding module does not test at that granularity; tests that run the same code with
   different inputs as copies rather than one parameterized test, using what the repository
   already uses (`ddt` or `pytest.mark.parametrize` in Python, `it.each` or `test.each` in
   Jest); a docstring on a test whose name and body already say what it checks; assertions that
   cannot fail; expected values recomputed the way the code computes them rather than taken from
   an independent source; tests that assert how the code is written (a mocked collaborator was
   called, a call order, a query count, a lock or manager method invoked) rather than what it
   does; fixtures or setup that change global state (a settings value, a permission registry, a
   module attribute) without restoring it; values that can go stale (dates) not held in
   constants or fixtures. Name each, with the fix.

**B5. Architecture (`software-architect`, Opus, xhigh).** With the criteria, the diff, the
commits on `main`, and the rule locations, findings each with a `file:line` and the cited rule
or ADR on:

- layering and contracts: `.importlinter` boundaries, public API stability and DEPR, which names
  a module exports as supported API and whether each one upholds the module's invariants on its
  own, `UNSTABLE` markers where the module's neighbors carry them, the identifier conventions
  (`id`, `uuid`, `key`, `num`), and PII annotations on new models;
- framework-boundary leaks: HTTP-layer types (`Http404`, `get_object_or_404`, a DRF exception)
  raised from a module that is not a view or serializer are a `Gap`, because every non-HTTP
  caller of a library API inherits HTTP semantics; the fix is a domain exception translated in
  the view;
- the ADRs that govern the touched area, whether the change follows them, whether the ticket
  and an ADR disagree (name the conflict rather than following either), and whether a decision
  the change makes should itself become a proposed ADR or an ADR amendment;
- the **invariants table**, whenever the diff adds or changes a model, a constraint, an index,
  or a lock: one row per rule the data model relies on, stated in code or comments or implied by
  the tickets and ADRs, including the rules existing constraints, `on_delete` behaviors, and
  signals already encode and the change interacts with: invariant | enforcement (database
  constraint, application check, lock, nothing) | when a row is archived or soft-deleted | when
  deleted | when a replacement row is created | gap. Each gap is a finding: a rule only
  application code or a lock enforces, where a race, an out-of-band writer (the ORM, a fixture,
  an admin, a future endpoint), or a second code path can violate it, is a `Gap` when violation
  breaks a read path or corrupts data, otherwise a `Question` asking for a constraint; a
  constraint without a condition, in a design whose tickets or ADRs describe archiving or soft
  deletion, leaves an archived row occupying the slot so that no replacement row can exist, a
  `Gap` on this change because the constraint is what makes the later ticket impossible without
  a schema change; a lock or locking read whose work an outer lock or a database constraint
  already does is a `Suggestion` to remove it, with the reason; a lookup that will have to
  filter on a lifecycle field that already exists on `main` and does not is a `Question`;
- security of the new surface: authentication and permission checks on new or changed
  endpoints, object-level access, references to another tenant's rows by id, read-merge-write
  sequences that can delete or overwrite rows the change does not own, injection, secrets, new
  dependencies;
- placement: whether each piece lives in the right repository and layer, what companion change
  `edx-platform` or the MFE needs for the feature to reach its users, and whether that companion
  exists or is linked;
- callers: what in this repository, in `edx-platform`, or in community plugins the change can
  break; whether the test strategy fits the layer;
- naming: public functions have clear names and RST docstrings that state the contract, and the
  same concept has one name across the function signatures, the serializer, and the ticket;
- anything else with a concrete impact that the remits above do not name. The listed dimensions
  are where defects usually are, not the complete set.

## Phase C: verify, sort, present (orchestrator, inline, at most 12 tool calls)

**C1. Acceptance criteria.** Build the required table from B4's mapping and your own reading of
the diff. One row per applicable criterion, quoting the criterion:

| Criterion (quoted) | In scope | Implemented at | Tested by | Verdict |
| --- | --- | --- | --- | --- |
| "..." | yes, or no and why | `file:line` | `test_file::test_name`, and the assertion that failed under B4's break | Covered / Implemented, untested / Not implemented / Implemented wrong |

"Implemented at" points at the code that makes the criterion true, read at the head SHA, not at
the PR description's claim. "Tested by" names a test B4 showed to fail when the behavior breaks;
a test that exercises the path without asserting the outcome does not count. A criterion written
as an artifact checklist item (a column exists, a migration is additive) is confirmed by
inspection plus the repository's standard check for that artifact, and counts as covered when a
behavior test exercises the artifact; the migration file itself needs no dedicated test. Also
record the two things a criterion-by-criterion pass misses: behavior the change adds that no
criterion asked for (name it, and let the developer decide whether it belongs), and a criterion
that looks implemented but whose implementation is wrong on an input the criterion covers,
including names and shapes (fields, response keys, function names) that differ from what the
criteria and the consumer tickets expect. A criterion not implemented, implemented wrong, or
without a test behind it is a `Gap`, or a `Bug` when the wrong implementation has a reachable
failure; a deliberate, documented deviation caused by a framework or library limitation is a
`Question` when the documented behavior has no concrete failure.

**C2. Premise audit.** Take B3's table and re-read the citation of every FALSE row yourself.
Each FALSE row is a finding, whether or not the code behaves correctly despite the claim: the
wrong rationale is what the next maintainer reads, and a correctness argument built on it is
unsound. A false claim in committed text (a comment, a docstring, the commit message) is a
`Gap`. A false claim in the PR body is a `Nit`, or a `Gap` when a reviewer would rely on it for
the merge decision, such as a claim about test coverage or about which constraints exist.

**C3. Invariants.** Take B5's table, read each gap row's enforcement claim at the head SHA, and
apply the rules in B5's remit to turn the gaps into findings.

**C4. Verify before asserting.** For every candidate from B1 to B5, confirm: it is introduced,
worsened, or exposed by the change; it has an evidence source read at the head SHA, not from
memory; it names a concrete impact; and its severity matches the evidence. For a `Bug`, also
confirm the reproduction path, the affected input or state, and that the path is reachable in
supported usage. Verify by reading the cited line or re-running the agent's stated command;
write a new probe only when a candidate `Bug` has no reproduction at all.

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

**C6. Present.** The review output has these parts, in this order:

1. **Verdict.** `Ready to merge: yes | with fixes | no`, and one sentence why.
2. **Inputs.** Repository, target, base and head SHAs, merge-base, ticket number and
   `updated_at`, the commits on `main` that changed the picture, and the repositories checked
   for companion changes.
3. **Acceptance criteria.** The table from C1.
4. **Premise audit.** The FALSE and UNVERIFIABLE rows from C2, and one line saying how many
   claims were checked in total.
5. **Invariants.** The gap rows from C3 and one line saying how many rows the table had, when
   the diff touches a model, constraint, index, or lock; otherwise one line saying it does not.
6. **Findings**, grouped by severity, each with a `file:line` anchor and its evidence:
   - `Bug.` A supported, reproducible failure or documented contract violation with meaningful
     impact, including an unhandled error reachable from client input and a branch that cannot
     merge.
   - `Gap.` A required element is missing or a stated one is false: a criterion not implemented
     or without a test that fails when it breaks, a companion change that does not exist, a PR
     requirement not met, a false claim in committed text, an invariant with no enforcement
     that a write can violate, a leaked framework boundary.
   - `Question.` A plausible concern whose reachability, contract, or impact is unconfirmed, or
     a decision the change should record now.
   - `Suggestion.` Optional hardening, broader coverage, or a test, comment, or lock to remove,
     without demonstrated user impact.
   - `Nit.` Style or wording only. All of them; the human decides which to raise.
7. **Tests checked.** B4's break-and-restore table as returned.
8. **Checks run and skipped**, with the reason for each skip, including the merge with `main`.
9. **Declined to judge.** One line per behavior considered and set aside as outside the ticket,
   with what the owning ticket must do and why it can do so against this change.
10. **Dropped.** One line per candidate whose evidence did not hold, with the fact that
    disproved it.
11. **Open questions** for the developer.

Lead each finding with the point, then the mechanism, in one to three sentences. Keep the tone
of one engineer to another: direct, specific, no praise padding and no "strengths" section. A
`Bug` or a `Gap` means the verdict is not "yes". Keep the two axes separate: a clean convention
pass does not soften a criterion `Gap`, and full criteria coverage does not excuse a layering
violation. If nothing is wrong, say so plainly, with the tables that show it.

## Phase D: explain (orchestrator inline, then two dispatches)

The C6 output is written for a reviewer who has read the ticket, the diff, and this skill. It
uses the severity vocabulary, `path:line` anchors, and names coined in the conversation that
produced it, such as "the opt-out" or "the moved base". The engineer who implemented the
change, and anyone else who did not sit in the review, cannot follow it without that context.
Phase D produces the text they can follow. It is part of the deliverable, not an optional
summary: a review without it is not finished.

**D1. Draft (orchestrator, inline, one file in the scratchpad).** Write the findings out for one
reader: the engineer who implemented the change, who knows the framework but not this
codebase's history, the ticket thread, or the sibling tickets. The draft has these parts, in
this order:

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
are not needed in the text; the grouping carries them.

**D2. Clean up (`general-purpose`, Sonnet, medium-high, budget 25).** Dispatch one sub-agent to
run the `clean-up-text` skill on the D1 file. Tell it: the path of that skill file, to read
first; the source path; the intended reader; that it cannot dispatch, so it runs steps 1 to 5
and 7 and returns step 6 as a "Needs verification" item carrying the source path, the rewrite
path, its changelog, and the definitions it added; that the repository is read-only and it may
grep to confirm that the names in the text exist; and that it writes the rewrite to a new file
next to the source. The skill's own length check applies: the body of the rewrite does not grow
past the source.

Also give it the layout of the rewrite. The layout lets a reader see every finding at a glance
and open only the detail they need. It uses HTML `<details>` blocks, which GitHub and Markdown
previews render collapsed, with a blank line after `<details>` and before `</details>` so the
Markdown inside them still renders:

- The title names the pull request and what it changes.
- The D1 lead paragraph is removed, including its statement of whether the change is ready to
  merge, which the "Must fix before merge" group already conveys. A sentence of the lead stays,
  as a short paragraph under the title, only when it carries information the implementer
  critically needs and no other part of the review states.
- The first section is "Review Details". Its heading sits outside, and one `<details>` block
  holds the rest of it: the prerequisites section, "Things the review looked at and is leaving
  to other tickets", "What passed", and the action list, in that order, each under its own
  subheading, followed by any other section a reader can skip and still act on the review.
- The four group headings of the findings follow, outside any `<details>` block.
- Each finding is one sentence followed by a `<details>` block that holds the whole finding. The
  sentence says what the finding is, in plain words a reader new to the codebase understands,
  and leaves out every detail: file and function names, the mechanism, the evidence, and the
  fix. A reader who reads only these sentences knows what every finding is about.
- Before it returns, it checks each sentence against the finding in the source: the sentence
  says only what the finding establishes, is exactly as certain and as severe as the finding,
  and names the finding's problem rather than a symptom of it or its fix. Its changelog lists
  the sentences as added text, so the D3 gate checks each one against its finding as well.
- The length check counts the summary sentences as allowed growth, like the prerequisites
  section: the rewrite minus the prerequisites section and the summary sentences comes in at or
  under the source.

**D3. Gate (`doc-accuracy-reviewer`, Sonnet, high, budget 15).** Dispatch the gate yourself, as
`clean-up-text` step 6 describes, with the source path, the rewrite path, and D2's changelog.
Nothing ships past a FAIL: correct the text and dispatch the gate again. On PASS WITH FIXES,
apply the fixes. The gate flags the definitions the rewrite added and cannot confirm them, so
that list travels with the delivery and the reader is told nobody has confirmed it.

**Deliver.** The cleaned file is the review the user receives, and it holds everything the user
needs from the review. Append to it, at the end of the file:

1. One sentence with the gate's verdict and the number of definitions the cleanup added that
   nobody has confirmed, followed by a `<details>` block that lists those definitions.
2. A heading that names the reviewer as its reader, followed by a `<details>` block that holds
   the C6 output.

When the user asked questions that are an integral part of the review, the answers are part of
the review in that file: write them into the D1 draft, in their own section before the action
list, so the cleanup and the gate cover them. Your response in chat is only a link to the cleaned
file, nothing more.

## Red flags

| Thought | Reality |
| --- | --- |
| "I'll dispatch the architect once the criteria table is done." | The architect needs the criteria, not the table. Everything in the wave goes out in one message. |
| "Let me read the model file before writing the brief." | Phase A reads the ticket, the PR, and the diff. Source files are the wave's job. |
| "One more probe to be sure." | Phase C reads cited lines and re-runs stated commands. A new probe is for a `Bug` with no reproduction. |
| "The migration check covers this criterion." | A migration check proves the schema applies. It proves nothing about the behavior the criterion describes. Name the test or report a `Gap`. |
| "Existing tests cover this." | Name the test and the assertion that would fail. If you cannot, it is not covered. |
| "The tests pass, so the behavior works." | A test that also passes against broken code proves nothing. Break the code and look. |
| "The test mocks the lock call, so the lock is tested." | It tests that a method was called. Replace the call with one that does nothing and the test still passes. |
| "More tests is safer." | Every test is something a reviewer reads. Two tests of one behavior, or five copies instead of one parameterized test, are findings. |
| "The comment is wrong but the code works." | The comment is what the next maintainer reads, and the correctness argument built on it is unsound. A false claim is a finding. |
| "I could not run it on the CI database, so it is a Question." | The consequence is the same whether you ran it or reasoned it. Keep the severity, name the inferred step. |
| "The other ticket owns this." | Write down what that ticket must do. If it cannot do it against the constraint or name this change adds, the finding is on this change. |
| "The neighboring tests do the same." | Precedent lowers severity. It does not make a defect absent. |
| "A senior engineer would not raise this nit." | Some would. List it under `Nit`; the human decides. |
| "There is no `AGENTS.md`, so there are no conventions to check." | `openedx-core` and `edx-platform` keep theirs in `CLAUDE.md`, ADRs, OEPs, and `.importlinter`. |
| "The ticket does not mention it, so it is fine." | Specification silence is not permission. A reasonable user's expectation is a requirement. |
| "The ticket's Technical Details say to build it this way." | The review reads the user story and the criteria, and nothing else from a ticket. Technical Details are one author's guess; the code is judged against the behavior the criteria describe and the repository's rules. |
| "This is a library change; the platform and the frontend are someone else's problem." | Trace the chain. A missing or unlinked companion change is a `Gap`. |
| "The sub-agent found it, so it is a finding." | It is a hypothesis until you have read its citation at the head SHA. |
| "That configuration is exotic." | If the product exposes it as a setting, it is supported input, and the failure is a `Bug`. |
| "The structured review is clear enough; the explanation would only repeat it." | It is clear to someone who read the ticket and the diff. The implementer did not sit in this review. Phase D is part of the deliverable. |
| "I will clean the explanation up myself instead of dispatching." | The cleanup and the gate are two more pairs of eyes on the text, by design of `clean-up-text`. The drafter cannot audit their own rewrite. |
