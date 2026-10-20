# Plan: add openedx/openedx-core PR #819 as a held-out case and run code-review-openedx against it

Written 2026-10-20, before the case was frozen and before anyone on this side read the PR's review comments. The
purpose is a held-out measurement: every version of the project's review skills scored so far was benchmarked on
PR #847, and the 2026-10-20 rewrites of code-review-openedx and code-review-v2 were written with #847's answer key in
hand (see `../openedx-core-pr847/circularity_G.md`). PR #819 is a different app (`openedx_catalog`), a different
author, and a mostly different set of reviewers, so a pass here means something a pass on #847 cannot.

## Contamination rule for this case

Whoever edits a review skill between now and the run must not read PR #819's review comments, review bodies, or the
`ground_truth_source.md` the freezer writes, and must not read `ground_truth.md` once it exists. The metadata below
was collected with `gh` calls that return authors, states, timestamps, SHAs, and counts only; no comment body was
fetched. Two people, or two sessions, are the clean split: one freezes the case and writes the ground truth, the
other has edited the skill. If the same person must do both, write the ground truth after the run's report exists
and say so in the results.

## Facts gathered (metadata only)

- PR #819 "feat(pathways): implement CatalogPathway" by Agrendalath; created 2026-09-15T20:08:59Z, merged
  2026-10-20T17:55:40Z as `d7a2229fc`; current head `e27748f6f`; 9 commits, all `fixup!` of one feature commit, so the
  PR's change is `merge-base..head` and `BASE_SHA` must be passed to `setup_checkout.sh`.
- No linked ticket: `closingIssuesReferences` is empty and the body references only PR #818 (a dependency whose
  direction decision is in `https://github.com/openedx/openedx-core/pull/818#issuecomment-5735091736`). The body
  says "I used Claude for proofreading and the initial reviews before opening the PR."
- Files at the answer-key head `c0047cddf` (names only): `.importlinter`, `src/openedx_catalog/admin.py`,
  `api_impl.py`, `migrations/0002_pathways.py`, `models/__init__.py`, `models/catalog_pathway.py`,
  `models/pathway_category.py`, `models/pathway_enrollment.py`, `models_api.py`,
  `tests/openedx_catalog/test_pathway_api.py`, `test_pathway_models.py`.
- Governing ADRs present at that head: `docs/openedx_learning/decisions/0005-pathway-and-pathway-items.rst`,
  `0006-pathway-item-fulfillment.rst`, `0007-pathway-catalog-content-split.rst`.
- Review rounds (author, state, time, anchored commit; inline-comment counts by non-authors in parentheses):
  - `fa1d75b6a`: bradenmacdonald APPROVED 2026-09-22T21:11Z (3 inline).
  - `c0047cddf`: ormsbee review 2026-10-01T23:44:57Z, state DISMISSED (12 inline); kdmccormick COMMENTED
    2026-10-02 and 2026-10-08 (5 inline anchored here).
  - `73a0d542d`: kdmccormick CHANGES_REQUESTED 2026-10-08T21:41Z (7 inline), rpenido (1), cassiezamparini (1).
  - `d28832dad`: kdmccormick APPROVED 2026-10-20T13:53Z.
- `main` before the ormsbee review: `0b351b8c1` (2026-10-01T18:34:07Z, "Merge pull request #844").

## Decisions to make, with the recommended answer

| Decision | Recommendation | Why |
| --- | --- | --- |
| Cutoff and frozen head | Cutoff `2026-10-01T23:44:57Z` (ormsbee's review), head `c0047cddf`, passed with `--cutoff`. | The freezer's default rule (earliest non-author review with inline comments) would pick bradenmacdonald's approval at `fa1d75b6a` with 3 comments, too thin for an answer key. The `c0047cddf` round has 17 non-author inline comments from two maintainers. |
| Answer key | All non-author inline comments anchored to `c0047cddf` (ormsbee's 12, kdmccormick's 5) plus the review bodies submitted against that head, split into one item each with weights 3/2/1 per `templates/scoring.md`. | These comment on the frozen code. The `73a0d542d` round comments on code the fixes introduced and is excluded, as the 847 case excluded its second round. Record ormsbee's DISMISSED state in the ground truth and say what the dismissal means after reading the timeline. |
| Earlier round | Exclude `fa1d75b6a`'s 3 comments; note them in the ground truth as "earlier head, out of scope". | A different head; a reviewer at `c0047cddf` saw the code after those were addressed. |
| `pr-base` | `BASE_SHA` = `git merge-base c0047cddf <main at cutoff>`; the freezer's `merge_base` field gives it. | Nine fixup commits; the head's parent is not the branch point. |
| `main` at cutoff | `0b351b8c1`. | Last `main` commit before the cutoff. |
| `ABSENT_SHAS` | `73a0d542d d28832dad e27748f6f d7a2229fc`. | Later heads and the merge commit. `fa1d75b6a` predates the cutoff and may stay. |
| The ticket | There is none. Assemble `context/requirements_819.md` from the PR body as of the cutoff (the three models it introduces and the stated scope), the Decisions sections of ADRs 0005 and 0007, and the #818 decision comment, each quoted with its source. Name it in the brief as "a local ticket file, explicitly provided", which the skill accepts. | code-review-openedx stops without a ticket by design. The acceptance-criteria table will quote ADR decisions and body statements instead of Gherkin scenarios; say so in the results. Assemble this file before reading any review comment. |
| Freezer change | Make `--ticket` optional in `scripts/freeze_pr.py` (skip `context/issue_<t>.md` and the comments file when absent) and add `--pr-context 818` to freeze another PR's body and comments up to the cutoff as `context/pr_818_body.md` and `pr_818_comments.md`. About 30 lines. | The script requires a ticket today, and #818's discussion is this PR's design source. |
| Variants | V1: the current code-review-openedx (the three-phase version committed to PR 49 of the config repo), orchestrator on fable, sub-agents as its table states. V2: the no-skill control from run 2 (one `software-architect` on fable at the definition's xhigh with the four-sentence instruction in `../openedx-core-pr847/reports_run2/BRIEF_D.md`). | The skill's score needs the model's unaided score beside it on a case with no prior rows. Add code-review-v2 only if budget allows; it is not the question this case asks. |
| Budget | About 1.0M tokens for V1 (run 5 measured 1.04M for the sequential shape; the three-phase shape is designed to hold that) and about 0.3M for V2; 15 to 25 minutes wall clock for V1 if the parallel shape works, which this run also measures. | From run 5's process logs. |

## Procedure (the numbered steps are `SKILL.md`'s; only what is specific to this case is written out)

1. **Freeze.** After the freezer change:
   `python3 scripts/freeze_pr.py --repo openedx/openedx-core --pr 819 --cutoff 2026-10-01T23:44:57Z --pr-context 818 --out <scratch>/case819`.
   Confirm in `case.json`: head `c0047cddf`, `main_sha_at_cutoff` `0b351b8c1`, the merge-base, the PR body's last edit
   before the cutoff. Keep `ground_truth_source.md` out of every directory an agent reads.
2. **Ground truth.** Written by the person who has not edited the skill, from the `c0047cddf` comments only, before any
   report exists, with the tiers copied from `templates/scoring.md` and the pass/fail gate. Then the overlap audit:
   for each item, note whether a passage of the current code-review-openedx names its failure class, so the results
   can report mapped and unmapped scores separately as run 5 did. Expect fewer mapped items than on #847; that is the
   point of the case.
3. **Checkout.** `CLAUDE_DIR=<config>/.claude BASE_SHA=<merge-base> CUTOFF=2026-10-01T23:44:57Z ABSENT_SHAS="73a0d542d... d28832dad... e27748f6f... d7a2229fc..." bash scripts/setup_checkout.sh <seed> https://github.com/openedx/openedx-core.git c0047cddf... 0b351b8c1... <scratch>/eval V1 V2`
   with full SHAs. Seed from the developer checkout or the 847 clone. Smoke test `tests/openedx_catalog/` with
   `PYTHONPATH=<wt>/src` and confirm `openedx_catalog.__file__` resolves under the worktree. The head is from
   September; if an import fails because the venv's dependencies moved on, build a venv from the head's
   `requirements/` and name it in the brief instead of the developer venv.
4. **Serve the skill as files.** `skills/V1/code-review-openedx/SKILL.md` and `skills/V1/backend-code-review/SKILL.md`
   from the commit under test, side by side so `../code-review-openedx/SKILL.md` resolves. Record the commit SHA and
   the md5 of both files in the results.
5. **Nested dispatch check**, as in `SKILL.md` step 5.
6. **Briefs** from `templates/BRIEF.md`, skill section shape (a) for V1 and (c) for V2. The V1 skill section is
   `../openedx-core-pr847/reports_run2/BRIEF_G.md`'s with the new paths. Both briefs name `requirements_819.md` as the
   ticket, `pr_818_body.md` and `pr_818_comments.md` as the design discussion, the three ADRs as governing documents,
   and the same sibling-repo rule as run 5 (edx-platform and tutor readable, read-only). State the stacking: the
   change is `git diff pr-base pr-head` with `pr-base` the merge-base.
7. **Dispatch** both in one message on `model: fable`, in the background. Record the wall clock from dispatch to
   hand-back; V1's is the measurement of the three-phase shape.
8. **Collect and audit** with `scripts/extract_handback.py`, needles: the case directory, the config repo, every
   earlier session's scratchpad, the other variant's directories, `gh pr`, `gh api`, `gh issue`.
9. **Score** with the locked tiers, the pass/fail gate, and the composite. Communication is graded last. Report the
   mapped and unmapped split from step 2's audit.
10. **Save** under `cases/openedx-core-pr819/`: `case.json`, `frozen/` (PR body, requirements file, #818 body and
    comments), `ground_truth.md`, the briefs, reports, per-item sheets, and `results.md`. Add the case to
    `SKILL.md`'s saved-cases list. Remind the user of decision 0002's evaluations-log line.

## What the results must say

- The pass/fail verdict for V1 and V2, and the blocking items below the bar.
- The composite beside run 5's #847 numbers for the same skill, with the sentence that #819 is the first held-out
  measurement and #847's are not.
- The mapped and unmapped split: how much of the skill's content the #819 answer key exercises.
- V1's wall clock and tokens against run 5's 117 minutes and 1.04M, as the test of the three-phase rewrite.
- The ticket substitution and what it did to the acceptance-criteria table.
- Anything the smoke test forced (a separate venv) and anything the review rounds made ambiguous (the DISMISSED
  review, comments on `c0047cddf` posted after the cutoff).

## Risks

- Dependency drift at a September head against the developer venv; the smoke test decides.
- Review-round ambiguity: kdmccormick's `c0047cddf` comments were posted after ormsbee's review; they anchor to the
  frozen code and belong in the answer key, but the context files are frozen at ormsbee's time, so a kdmccormick
  comment that reacts to something said after the cutoff should be marked.
- Reviewer overlap: ormsbee reviewed both #847 and #819, so some failure classes may recur; the mapped/unmapped split
  is how the results stay honest about it.
- The PR body was edited after the cutoff (it now contains a struck-through dependency note); the freezer takes the
  last edit before the cutoff, so check that the body it saved still states the scope.
