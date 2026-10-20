# Ground truth: findings in the real review of openedx/openedx-core PR #847 at head 2ca89b767

Source: ormsbee's CHANGES_REQUESTED review (16 inline comments drafted 2026-10-11 against 2ca89b767, submitted 2026-10-14, plus one top-level body). Second-round comments (on dd5f40ef0) concern code that did not exist at 2ca89b767 and are excluded. Weights: blocking 3, substantive non-blocking 2, nit 1. Total weight 45.

## Blocking (weight 3)

- GT1  Rule-field validation before the DB. `rule_payload_override` alone, or `rule_profile_id` plus both overrides, reach the DB and 500 on the `oel_cbe_criterion_profile_xor_override_check` IntegrityError. Validate in the API (associate_competency_criterion) or serializer, 400 keyed by the offending field. (serializers.py:80 / api.py)
- GT2  Archived `rule_profile_id` is accepted for a new association (201). ADR-0002 Decision 3 says archived profiles are hidden from new associations. Reject it. (serializers.py:80 / api.py)
- GT3  `tag_object()` raises ValueError when the taxonomy has `allow_multiple=False` and this is a second competency, or at OBJECT_MAX_TAGS, and the view 500s. Catch and raise ValidationError on `object_id`. (api.py:193)
- GT4  Group-name overflow: Tag.value is 500 chars and CourseRun.title 255, the generated root/course-level names exceed `name` max_length 255. MySQL strict mode: DataError 500; non-strict: silent truncation. SQLite tests cannot see it. Truncate. (api.py:136)
- GT5  Taxonomy-scoped rule profile is never assigned; the criterion always gets the system default. #665 AC "A taxonomy-scoped rule profile is assigned ahead of the system default" and ADR-0002 Decision 4. Implement the lookup or document deferral. (api.py:197)
- GT6  HTTP leaks into api.py: `get_object_or_404` / `Http404` in resolve_competency_tag and resolve_supplied_leaf_group. Raise DoesNotExist (or a CBE exception) and translate in the view. (api.py:111, :166)
- GT7  Archived groups vs `get_or_create()` and the unconditioned unique constraint. #857 (on main) added `archived` to both models; neither create_leaf_group's get_or_create nor resolve_supplied_leaf_group looks at it, so a new criterion can nest under an archived course-level group or land in an archived leaf; and if the lookups did filter archived=False, the (tag, course, parent) constraint without a condition leaves no room for a replacement row. Decision must be recorded (scope_code-style derived column; would also give one-root-per-tag and let the tag lock go). (criteria.py:117)
- GT8  Rebase logistics: #846 and #857 have merged; #857 took migration 0014, so 0014_criteria_group_unique_constraints collides. Rename to 0015 and depend on 0014_add_archived_to_criteria_group_and_criterion. (migrations/)

## Substantive, non-blocking (weight 2)

- GT9  The two `select_for_update()`s on ObjectTag / CompetencyCriterion in `_reject_duplicate_criterion` buy nothing: the tag row lock already serializes callers, and a locking read takes no gap lock when no row matches. Drop both and the comment. Also `.exists()` keeps FOR UPDATE, so the `list(...[:1])` idiom is unnecessary. (api.py:223)
- GT10 The comment/commit message justify locking reads with "MySQL REPEATABLE READ"; Django has defaulted MySQL to READ COMMITTED since 2.0 and the framework assumes it. Premise is wrong. (api.py:222)
- GT11 Malformed `object_id` returns 403, not the tested 400, in Studio: the view's permission check runs before parsing and the platform's `can_change_object_tag_objectid` returns False for an unparseable key; the test stub permits everything so tests cannot see it. Add `validate_object_id()` to the serializer. (serializers.py:70)
- GT12 `rules.set_perm()` in the autouse fixture mutates the global ruleset for the rest of the test session without restoring. Make it a yield fixture that restores the original predicate. (test_views.py:44)
- GT13 Leaf naming vs the AC: #665 says the leaf is "named from the course's display name"; the PR names the course-level group and leaves the leaf unnamed. Flag the discrepancy; whoever builds #672 needs to know. (api.py:136)
- GT14 The test_criteria_group.py hunk is unnecessary and its comment is wrong: there is no one-root-per-tag constraint (NULLs are distinct in a unique index). Revert it; the PR description also wrongly claims the constraint rejects two roots. (test_criteria_group.py:57)
- GT15 The two lock-pinning tests (`test_create_leaf_group_locks_the_tag_row_before_creating_groups`, `test_associate_competency_criterion_locks_the_tag_row_before_the_duplicate_check`) mock select_for_update and pin implementation, not behavior. Drop them. (test_api.py:295)
- GT16 Question: should CompetencyCriterion have a unique constraint on (object_tag, group)? (api.py:223)

## Nits (weight 1)

- GT17 `create_leaf_group` re-takes the tag lock inside a nested atomic (savepoint) when called from associate_competency_criterion. Document that the caller holds the lock, or make it private and drop the nested atomic. (api.py:132)
- GT18 Naming inconsistency: `competency_rule_profile_id` in associate_competency_criterion vs `rule_profile_id` elsewhere. Pick one. (api.py:248)
- GT19 Mark the new public api functions UNSTABLE like get_competency_rule_profiles. (api.py:242)
- GT20 `UserType` alias for the concrete User model is confusing next to openedx_tagging.rules' `UserType`; #846 dropped it. Use get_user_model() or drop the annotation. (test_views.py:9)
- GT21 Duplicated assert line in test_api.py (`assert list(get_competency_rule_profiles()) == expected` twice). (test_api.py:191)

## Scoring method

- Coverage (weighted recall): per item 1.0 = found with the correct mechanism and an actionable recommendation; 0.5 = noticed but misdiagnosed, vague, or wrong severity by two levels; 0 = missed. Sum of weight x credit / 45.
- Precision: findings outside the ground truth are classified as valid extra (a maintainer would accept it), neutral (a question or nit with no cost), or false positive (wrong, unreachable, or something CI enforces). Precision = 1 - (false positives / total findings reported).
- Communication (0-1): verdict clarity, file:line anchors, evidence quality (reproduction or cited rule), actionability, severity calibration, signal-to-noise, readability for the PR author.
- Composite = 0.70 x coverage + 0.15 x precision + 0.15 x communication.
