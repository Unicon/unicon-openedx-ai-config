Every agent in the review, and the top-level session, reads this file first.

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
  files, such as running tests, merging with `main`, or breaking a code path to watch a test
  fail, happens in a temporary git worktree that is removed afterwards.
- Do not report what CI tooling already enforces: formatting, lint, type errors, import order.
  Do run the targeted tests and checks the repository's instructions name, and report results.

## Severities

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

## Red flags

| Thought | Reality |
| --- | --- |
| "The comment is wrong but the code works." | The comment is what the next maintainer reads, and the correctness argument built on it is unsound. A false claim is a finding. |
| "I could not run it on the CI database, so it is a Question." | The consequence is the same whether you ran it or reasoned it. Keep the severity, name the inferred step. |
| "The other ticket owns this." | Write down what that ticket must do. If it cannot do it against the constraint or name this change adds, the finding is on this change. |
| "The neighboring tests do the same." | Precedent lowers severity. It does not make a defect absent. |
| "A senior engineer would not raise this nit." | Some would. List it under `Nit`; the human decides. |
| "The ticket does not mention it, so it is fine." | Specification silence is not permission. A reasonable user's expectation is a requirement. |
| "The sub-agent found it, so it is a finding." | It is a hypothesis until you have read its citation at the head SHA. |
| "That configuration is exotic." | If the product exposes it as a setting, it is supported input, and the failure is a `Bug`. |
