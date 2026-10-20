# Scoring: variant D = no skill; one `software-architect` agent (model fable passed explicitly; the agent definition's effort, xhigh) with a four-sentence review instruction. Report = reports/D_final.md

Tiers (locked before any report was read): 1.0 found + correct mechanism + actionable; 0.75 one severity level soft or hedged; 0.5 vague / misdiagnosed / two levels soft / part of a multi-part item; 0 missed or argues the opposite.
Severity reading for this report: "blocking" = blocking; "should fix" = one level below, except where the Verdict paragraph names the item as a reason the PR is not mergeable (then judged blocking by content); "nit" = two below blocking, one below substantive.

| GT | w | credit | where in report | note |
|---|---|---|---|---|
| GT1 rule-field validation before DB | 3 | 1.0 | S1 (should fix; named in Verdict as "500 instead of 400") | reproduced both bad shapes; serializer validate() + PrimaryKeyRelatedField; also notes the error keys |
| GT2 archived rule_profile_id accepted | 3 | 0.75 | S2 (should fix) | reproduced; ADR Decision 3; one level soft |
| GT3 tag_object ValueError 500 | 3 | 0.75 | S11 (should fix, "low") | allow_multiple=False reproduced; OBJECT_MAX_TAGS not mentioned; same fix; one level soft |
| GT4 group-name overflow 255 | 3 | 0.75 | S3 (should fix) | reproduced 507 to 512 chars; MySQL strict DataError; truncate or stop embedding tag.value; one level soft |
| GT5 taxonomy-scoped profile never assigned | 3 | 1.0 | B5 (blocking) | probed; AC vs ADR MVP note vs #672; implement or amend |
| GT6 Http404 in api.py | 3 | 0.75 | S8 (should fix) | raise DoesNotExist, map to NotFound in the view; grep shows no other api.py does this; one level soft |
| GT7 archived groups vs get_or_create + constraint | 3 | 0.5 | B1 fix paragraph | noticed that the three lookups ignore `archived`, deferred to #717; no mention of the unconditioned constraint |
| GT8 migration 0014 collision | 3 | 1.0 | B1 + B2 (blocking) | rebase with the nine conflicting files enumerated; collision reproduced; rename to 0015 depending on 0014_add_archived |
| GT9 duplicate-check locking reads buy nothing | 2 | 0.5 | S7 (should fix) | right target and option (a) is the maintainer's fix (plain read, unique_together as backstop), but the mechanism is a gap-lock deadlock, which the maintainer rejected ("a locking read takes no gap lock when no row matches"); misdiagnosed |
| GT10 REPEATABLE READ premise wrong | 2 | 0 | B4, S7 | adopts the premise and builds two findings on it |
| GT11 malformed object_id -> 403 in Studio | 2 | 1.0 | S5 (should fix) | verified against the platform predicate in a local edx-platform checkout; validate_object_id on the serializer |
| GT12 set_perm fixture leaks | 2 | 0.75 | N4 (nit) | exact content and fix; one level soft |
| GT13 leaf naming vs AC | 2 | 1.0 | S3 second half | AC quoted, probe shows '' ; set name=course_run.title or amend; mentions #672 |
| GT14 test_criteria_group hunk + wrong comment | 2 | 1.0 | S9 (should fix) | revert the hunk, comment false, PR body describes the old design |
| GT15 drop lock-pinning tests | 2 | 0 | B4 fix | recommends adding another lock-pinning test on the same pattern: argues the opposite |
| GT16 unique (object_tag, group)? | 2 | 0 | | not mentioned |
| GT17 create_leaf_group re-takes the lock | 1 | 0 | B4 mechanism | notes the lock is taken at api.py:285 "and again api.py:132" but does not flag it |
| GT18 competency_rule_profile_id naming | 1 | 0 | | not mentioned (S6 and S9 are about response and PR-body names) |
| GT19 mark new api functions UNSTABLE | 1 | 1.0 | S8 | "underscore-prefix the helpers, or at minimum mark them UNSTABLE as get_competency_rule_profiles already is" |
| GT20 UserType alias | 1 | 0 | | not mentioned |
| GT21 duplicated assert | 1 | 1.0 | N1 | |

Weighted: blocking 6.5x3 = 19.5 ; substantive 4.25x2 = 8.5 ; nits 2x1 = 2 => 30/45 = 66.7%. Blocking items found: 6.5 of 8.

Findings reported: 5 blocking + 11 should-fix + 6 nits = 22.
- False positives: B4 (root-group race under ATOMIC_REQUESTS: rests on InnoDB REPEATABLE READ snapshots; Django runs MySQL at READ COMMITTED, the premise the maintainer rejected, under which the post-lock get_or_create read sees the committed root) and S7 (gap-lock deadlock on the missing ObjectTag row: same premise; under READ COMMITTED a non-matching locking read takes no gap lock, which is what the maintainer said). Both are labeled "reasoned, not reproduced", which is honest, but the recommended locking reads in B4 are the ones the maintainer asked to remove.
- Valid extras: B3 (isolated_apps import-linter contract broken after rebase, reproduced); S4 (library usage key -> AssertionError 500, reproduced); S6 (response field names vs AC and #672; PR body claims source= mappings); S10 (untested AC scenarios); N3 (docstring claim false at pr-base); N6 (system-default lookup should reuse get_competency_rule_profiles).
- Neutral: N2 (__all__ order), N5 (tag resolved twice), S4's block-type check, S8's note that create_competency_criterion bypasses the lock, the "Notes for the ticket owners".
Precision = 1 - 2/22 = 0.91

Communication: 0.85. Verdict first with the reasons grouped (mechanical vs substantive); a summary table with severity and anchor per finding before the detail; each finding states mechanism then fix; reproduced and reasoned claims are labeled as such, and the MySQL gap is declared; cross-ticket notes are separated from defects. Against it: the longest report of the six variants; two blocking-rated items are wrong; several items the maintainer blocked on are filed as should-fix.

Composite = 0.70 x 0.667 + 0.15 x 0.91 + 0.15 x 0.85 = 0.73

Cost: one agent, about 269k tokens, 37 tool uses (20 Read, 52 Bash), 18.2 min wall clock (harness), no sub-agents. Read the local edx-platform and tutor checkouts (not forbidden by the brief) to settle ATOMIC_REQUESTS and the platform's object-id predicate.
