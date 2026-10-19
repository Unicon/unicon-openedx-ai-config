# Results on openedx/openedx-core PR #847 (head 2ca89b767), run 2026-10-16 to 2026-10-19

Reviewer model: Fable (`model: fable` on the Agent dispatch), one run per variant, sub-agents as each skill prescribes.
Ground truth: ground_truth.md (21 items, weight 45). Scoring per templates/scoring.md.

| Variant | Coverage | Blocking found (of 8) | Precision | Communication | Composite |
|---|---|---|---|---|---|
| backend-code-review + code-review, config repo `main` at c184c5f (before PR 49) | 65.6% | 6.0 | 0.96 | 0.80 | 72% |
| backend-code-review + code-review at 22d5a35 (PR 49) | 79.4% | 6.75 | 1.00 | 0.85 | 83% |
| code-review-v2 (SKILL.md + scopes.md, 2026-10-16 working tree) | 77.8% | 7.0 | 1.00 | 0.85 | 82% |

Missed by all three: GT16 (unique constraint on (object_tag, group)?), GT20 (UserType alias).
Weak for all three: GT7 (archived groups versus the unconditioned constraint; all three deferred it to ticket #717),
GT9 (the two locking reads buy nothing), GT15 (drop the lock-pinning tests).

Differentiators: the pre-PR-49 skill missed the archived-groups question, argued from the REPEATABLE READ premise the
maintainer rejected (its one false positive), and graded two blocking items as Suggestion/Question. The PR 49 skill's
break-and-restore step found a test that passes against broken code and kept the set_perm leak and the wrong
isolation-level comment that v2 dropped as noise. V2 found the most blocking items (it caught the allow_multiple
ValueError 500 the PR 49 skill only half-found) and resolved a reviewer conflict about MySQL isolation by inspecting
Django's backend default.

Valid findings outside the ground truth, raised by two or more variants: the isolated_apps import-linter break after
rebase; the companion mount path in the PR body that would serve /api/cbe/cbe/v1/; leaves stored with null course_id
against ADR 0002 Decision 2; parent groups keeping a null logic_operator with two children; a read-merge-write race in
tag_object that can cascade-delete another competency's criterion; response field object_tag_id versus the AC's
oel_tagging_objecttag_id.

Cost: old skill about 300k orchestrator tokens plus four Sonnet sub-agents; PR 49 skill about 370k plus one Haiku,
two Sonnet, and two Opus xhigh sub-agents (the second architect only because of an interruption); v2 about 410k plus
six reviewers totaling 1.37M tokens, about 20 minutes wall clock in parallel.

Caveats: a session rate limit killed all three runs mid-way on 2026-10-16; they were resumed on 2026-10-19 (the PR 49
run delivered an interim report before its sub-agents returned and re-dispatched its architect). Single run per
variant. No MySQL locally. GitHub access was frozen to the files in frozen/.

Circularity: the PR 49 skill (commit 22d5a35, 2026-10-16) and the config repo's #665 AC alignment (d8ef489) were
written after PR 847's review (2026-10-11 to 2026-10-15), and PR 49's commit message says reviews had "accepted
untested criteria". GT5 (the untested taxonomy-profile criterion) is the item most likely to have shaped that change.
All three variants found GT5, so it did not move the ranking, but treat this case as "seen" by the PR 49 skill and
prefer a held-out PR for the next comparison of that skill.
