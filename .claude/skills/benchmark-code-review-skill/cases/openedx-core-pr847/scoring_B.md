# Scoring: variant B = superpowers 7.0.0 `requesting-code-review` (one `general-purpose` reviewer, model fable, from the skill's template). Report = reports/B_final.md

Tiers (locked before any report was read): 1.0 found + correct mechanism + actionable; 0.75 one severity level soft or hedged; 0.5 vague / misdiagnosed / two levels soft / part of a multi-part item; 0 missed or argues the opposite.
Severity reading for this template: Critical = blocking; Important = one level below, except where the Assessment names the item as a reason the PR is not ready to merge (then judged blocking by content); Minor = two below blocking, one below substantive.

| GT | w | credit | where in report | note |
|---|---|---|---|---|
| GT1 rule-field validation before DB | 3 | 1.0 | issue 4 (Important; named in Assessment) | probed both bad shapes; serializer validate(); correctly notes nonexistent id already 400s |
| GT2 archived rule_profile_id accepted | 3 | 1.0 | issue 5 (Important; named in Assessment) | probed; ADR Decision 3 and help text |
| GT3 tag_object ValueError 500 | 3 | 1.0 | issue 8 (Important; named in Assessment) | probed allow_multiple=False; cites ObjectTagView precedent; catch -> ValidationError |
| GT4 group-name overflow 255 | 3 | 0 | | not mentioned |
| GT5 taxonomy-scoped profile never assigned | 3 | 1.0 | issue 2 (Important; named in Assessment) | probed; AC vs ADR MVP note; implement or amend the AC |
| GT6 Http404 in api.py | 3 | 0 | | not mentioned |
| GT7 archived groups vs get_or_create + constraint | 3 | 0.5 | Recommendations, last bullet; Declined to judge | noticed that get_or_create will reuse archived groups after the rebase, deferred to #717, no mention of the unconditioned constraint leaving no room for a replacement row |
| GT8 migration 0014 collision | 3 | 1.0 | issue 1 (Critical) | reproduced by cherry-pick onto main (190 errors); rename to 0015, depend on 0014_add_archived |
| GT9 duplicate-check locking reads buy nothing | 2 | 0 | Strengths bullet 2; issue 17 | Strengths praise the locking reads as "careful"; issue 17 only hedges the list(...[:1]) idiom as "use .exists() unless select_for_update needs it". Main claim argued the opposite. |
| GT10 REPEATABLE READ premise wrong | 2 | 0 | Strengths bullet 2; issue 3 | adopts the premise ("visible under MySQL REPEATABLE READ") and builds issue 3 on it |
| GT11 malformed object_id -> 403 in Studio | 2 | 1.0 | issue 7 (Important) | same mechanism and same fix (validate_object_id on the serializer); flagged as needing platform confirmation |
| GT12 set_perm fixture leaks | 2 | 0.75 | issue 18 (Minor) | exact content and fix (yield fixture); one level soft |
| GT13 leaf naming vs AC | 2 | 0.75 | issue 11 (Minor) | AC quoted, probe shows leaf name ''; "undeclared deviation", mentions #672; one level soft |
| GT14 test_criteria_group hunk + wrong comment | 2 | 0.75 | issue 13 (Minor) + issue 9 (PR body claims a root constraint) | content complete across the two; one level soft |
| GT15 drop lock-pinning tests | 2 | 0 | Strengths bullet 2; Recommendations | praises the pinning test and recommends adding another: argues the opposite |
| GT16 unique (object_tag, group)? | 2 | 0 | | not mentioned |
| GT17 create_leaf_group re-takes the lock | 1 | 0 | | issue 16 is the double tag resolution, not the nested lock |
| GT18 competency_rule_profile_id naming | 1 | 1.0 | issue 15 (Minor) | |
| GT19 mark new api functions UNSTABLE | 1 | 0 | Strengths bullet 1 | praised as "declared in __all__ and re-exported" |
| GT20 UserType alias | 1 | 0 | | not mentioned |
| GT21 duplicated assert | 1 | 1.0 | issue 14 (Minor) | |

Weighted: blocking 5.5x3 = 16.5 ; substantive 3.25x2 = 6.5 ; nits 2x1 = 2 => 25/45 = 55.6%. Blocking items found: 5.5 of 8.

Findings reported: 18 issues.
- False positives: issue 3 (root-group creation race under ATOMIC_REQUESTS). It rests on MySQL REPEATABLE READ snapshots taken before the tag lock; Django runs MySQL at READ COMMITTED, the premise the maintainer rejected (GT10), under which the post-lock get_or_create read sees the winner's committed root. The recommended locking reads are the ones the maintainer asked to remove.
- Valid extras: issue 6 (disabled taxonomy: read-merge-write deletes another competency's criterion, probed); issue 9 (PR body describes a different implementation; stale); issue 10 (response field object_tag_id vs AC's oel_tagging_objecttag_id).
- Neutral: issue 12 (block type not checked), issue 16 (tag resolved twice), issue 17 (idiom), __all__ ordering and create_leaf_group naming inside issue 15.
Precision = 1 - 1/18 = 0.94

Communication: 0.80. Clear verdict with reasons (at the end, after Strengths, as the template dictates); file:line anchors throughout; strongest evidence of any variant (probe script for seven request shapes, cherry-pick reproduction of the migration collision, lint-imports/mypy/pycodestyle/isort/pylint/pydocstyle, cross-module test run); actionable fixes; honest "Needs research" items instead of asserted platform behavior; a "Declined to judge" list that makes scope decisions visible. Against it: very long; two Strengths bullets praise exactly what the maintainer asked to remove (the locking reads and the lock-pinning test), which steers the author wrong; three substantive items filed as Minor.

Composite = 0.70 x 0.556 + 0.15 x 0.94 + 0.15 x 0.80 = 0.65

Cost: orchestrator about 111k tokens, 12 tool uses; one general-purpose reviewer on fable, about 234k tokens, 41 tool uses, 17.8 min; about 24 min wall clock end to end.
