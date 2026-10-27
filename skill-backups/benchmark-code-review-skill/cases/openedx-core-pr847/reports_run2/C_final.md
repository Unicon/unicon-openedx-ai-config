Everything checks out. The temporary worktree is removed and the wt-C tree is clean. Here is the report.

## Review of PR #847 (`pr-base..pr-head`), stock `code-review` skill, effort `high`

The skill's output follows verbatim.

---

All anchors resolved; nothing further is needed. Below is the deduplicated, severity-ranked result of the eight angles. Everything in it was checked against the worktree source (not the main checkout, which the interpreter resolves to by default), and two claims were verified by running code: the pre-PR `test_criteria_group` body passes unchanged against the new constraint, and `makemigrations --check` shows no drift for `openedx_learning`.

```json
[
  {
    "file": "src/openedx_learning/applets/cbe/rest_api/v1/serializers.py",
    "line": 80,
    "summary": "The rule fields are accepted as loose scalars with no cross-field or existence validation, so several bad-but-plausible request bodies reach the database and fail with IntegrityError (a 500) instead of a 400.",
    "failure_scenario": "POST {\"object_id\": <valid key>, \"rule_profile_id\": 999999} -> CompetencyCriterion.objects.create() inserts a dangling FK; MySQL rejects it with IntegrityError and the view has no handler for it, so the client gets a 500 after the tag lock and group creation already ran. Likewise {\"rule_payload_override\": {...}} with no rule_type_override, or rule_profile_id plus both overrides, pass serializer validation and CompetencyCriterion.clean() (which only checks when rule_type_override is set) and then violate oel_cbe_criterion_profile_xor_override_check -> IntegrityError -> 500. A serializer-level validate() enforcing the profile-xor-override rule, with rule_profile_id as a PrimaryKeyRelatedField, turns all of these into 400s."
  },
  {
    "file": "src/openedx_learning/applets/cbe/api.py",
    "line": 197,
    "summary": "An explicitly supplied rule_profile_id is never checked against `archived`, so a new criterion can be bound to an archived profile even though ADR-0002 Decision 3 says archived profiles are hidden from new associations.",
    "failure_scenario": "Admin archives profile 7 (archived=True, scope_code=None). A client then POSTs {\"object_id\": ..., \"rule_profile_id\": 7}: associate_competency_criterion() skips the default-resolution branch because rule_profile_id is not None and creates the criterion pointing at the archived row with a 201. The retired rule now governs a brand-new criterion and nothing in the response or the data flags it."
  },
  {
    "file": "src/openedx_learning/applets/cbe/api.py",
    "line": 193,
    "summary": "tag_object() raises ValueError for a taxonomy with allow_multiple=False or when OBJECT_MAX_TAGS would be exceeded, and neither the API nor the view converts that into a ValidationError, so a legitimate taxonomy configuration produces a 500.",
    "failure_scenario": "A competency taxonomy created with create_competency_taxonomy(allow_multiple=False) (an argument the function explicitly offers). An author creates a criterion for tag A on subsection S (201), then one for tag B on S: existing_values becomes [A, B], tag_object() hits _get_current_tags()'s `not taxonomy.allow_multiple and len(tags) > 1` check and raises ValueError, which is not DjangoValidationError, so the view's except clause does not catch it and DRF returns 500 instead of a 400 keyed on object_id."
  },
  {
    "file": "src/openedx_learning/applets/cbe/api.py",
    "line": 136,
    "summary": "The derived group names are built from Tag.value (max_length=500) and CourseRun.title but written into CompetencyCriteriaGroup.name (max_length=255) via objects.create()/get_or_create(), which skip full_clean(), so a long tag value overflows the column.",
    "failure_scenario": "A competency tag with a 300-character value (valid: Tag.value allows 500). First POST for that tag calls get_or_create(defaults={\"name\": f\"{tag.value} (root)\"}): on MySQL in strict mode the INSERT fails with DataError 'Data too long for column name' (a 500); on a non-strict server or SQLite it is silently truncated. Truncating with name[:255] or deriving the name differently avoids both outcomes."
  },
  {
    "file": "src/openedx_learning/applets/cbe/api.py",
    "line": 160,
    "summary": "resolve_supplied_leaf_group() defines 'leaf' as 'has a parent and no course' and then reads the course from group.parent, which assumes the group sits at exactly depth 2; ADR-0002 Decision 2 allows arbitrarily nested descendant groups, and any deeper group is rejected with a misleading 'must belong to the given course' error.",
    "failure_scenario": "Tree: root -> course-level group (course=C) -> group G1 (course=None) -> group G2 (course=None), built per the ADR's nested-expression model. POST {\"object_id\": <key in C>, \"group_id\": G2.id}: G2 passes the leaf test (parent set, course null) but G2.parent.course_id is None != C.id, so the request is rejected as belonging to the wrong course although it is in course C. Walking up to the nearest ancestor with a non-null course (or restricting the leaf test to parent.course_id non-null with an accurate message) fixes it."
  },
  {
    "file": "src/openedx_learning/applets/cbe/api.py",
    "line": 34,
    "summary": "resolve_competency_tag, create_leaf_group and resolve_supplied_leaf_group are added to __all__ and therefore re-exported by openedx_learning.api as stable public API, yet they raise django.http.Http404 from a domain layer and create_leaf_group alone persists an empty group, which ADR-0002 (line 110) says backend validation must reject.",
    "failure_scenario": "A platform caller or management command calls openedx_learning.api.create_leaf_group(tag, run) to prepare a group and then fails before adding a criterion: an empty root/course-level/leaf trio is committed, exactly the state the ADR forbids, and there is no API to delete it. A non-view caller passing an unknown tag_id to resolve_competency_tag() gets Http404, an HTTP exception, from a library function. .claude/CLAUDE.md: 'Public APIs are stable. Breaking changes to non-UNSTABLE APIs go through the DEPR process' and get_competency_rule_profiles already models the alternative with an UNSTABLE docstring marker. Either keep these three private (underscore, out of __all__, tests import the applet module) or mark them UNSTABLE and raise ObjectDoesNotExist/ValidationError, mapping to 404 in the view."
  },
  {
    "file": "src/openedx_learning/applets/cbe/api.py",
    "line": 197,
    "summary": "Default rule-profile resolution is hard-wired to the all-null system default even though this entry point already knows the course run and the competency taxonomy, and ADR-0002 Decision 4's table says a course-scoped (then taxonomy/org-scoped) profile wins over the default when one exists.",
    "failure_scenario": "A course-scoped CompetencyRuleProfile for course C exists (the model, constraints and the cbe test fixtures already support creating one). POST {\"object_id\": <subsection in C>} with no rule fields: the criterion is assigned the system default rather than C's profile, so C's intended threshold is ignored, and the docstring's citation of Decision 4 misdescribes what the code does. The ADR's MVP note justifies defaulting only because the authoring screens lack course context; this endpoint derives it from the usage key, so the resolution should at least prefer a live course-scoped profile for course_run (and a taxonomy-scoped one for tag.taxonomy), or the docstring should state plainly that scoped profiles are deliberately ignored here."
  },
  {
    "file": "src/openedx_learning/applets/cbe/api.py",
    "line": 113,
    "summary": "Nothing in the public API path rejects a tag whose taxonomy is disabled, although ADR-0002 Decision 1 says CompetencyCriteriaGroup and CompetencyCriterion are only valid for competencies from enabled taxonomies; only the view's permission predicate happens to block it.",
    "failure_scenario": "Taxonomy T is disabled (enabled=False). Any direct caller of associate_competency_criterion(tag_id=<tag in T>, object_id=...) gets a 201-equivalent success: resolve_competency_tag() checks only the CompetencyTaxonomy link. Worse, get_object_tags() excludes disabled taxonomies, so existing_values is empty and tag_object() then deletes every other ObjectTag the object had in T. The REST view is shielded only because can_view_object_tag_taxonomy() returns False for disabled taxonomies; the API should enforce the invariant itself."
  },
  {
    "file": "tests/openedx_learning/applets/cbe/test_criteria_group.py",
    "line": 52,
    "summary": "The test was rewritten to use a second tag with a comment asserting that 'the one-root-per-tag constraint allows only one root group per tag', but no such constraint exists: the new UniqueConstraint covers (tag, course, parent) with NULLs distinct, and the pre-PR test body passes unchanged against the new model.",
    "failure_scenario": "Verified by running the pr-base version of the test against the worktree source: 3 passed. The edit is therefore unrelated to the change and the comment documents a guarantee the schema does not provide, so the next reader will assume two roots per tag are impossible. .claude/CLAUDE.md: 'Treat stale comments as bugs: update or delete them in the same change' and 'Surgical changes: don't refactor or reformat code your task doesn't touch. ... Every changed line should trace to the request.' Revert the hunk, or if two-roots-per-tag is meant to be impossible, say so accurately (it is only serialized by the tag row lock in create_leaf_group, not by a constraint)."
  },
  {
    "file": "src/openedx_learning/applets/cbe/rest_api/v1/views.py",
    "line": 84,
    "summary": "The view resolves the tag (Tag + taxonomy + competencytaxonomy queries) and then hands tag.id to associate_competency_criterion(), which resolves the same tag again; inside the transaction the tag row is also locked twice (associate_competency_criterion and the nested create_leaf_group).",
    "failure_scenario": "Every successful POST on the derive path runs resolve_competency_tag() twice (two get_object_or_404 lookups plus two lazy taxonomy loads and two hasattr(competencytaxonomy) queries) and issues SELECT ... FOR UPDATE on the same tag row twice in the same transaction. Letting the API accept the already-resolved Tag (or performing the has_perm check inside the API with a user argument) and dropping the inner lock in create_leaf_group when a caller already holds it removes four to five queries per request on a hot authoring path."
  }
]
```

Two lower-ranked candidates were cut by the cap and are worth a glance if you have time: `tests/openedx_learning/applets/cbe/test_api.py` gains a duplicated `assert list(get_competency_rule_profiles()) == expected` line at the end of `test_get_competency_rule_profiles_is_ordered_by_id`, and `create_leaf_group` rebinds the module-level `_` (gettext_lazy) via `root, _ = ...` and `course_level_group, _ = ...`, which is harmless at runtime but shadows the translation helper inside that function.

---

## Process log

**Which checkout and range the findings refer to.** All findings refer to the isolated checkout at `/private/tmp/claude-501/-Users-jesperhodge-openedx-openedx-core/bc59e103-2d05-4b61-9b05-8c383fd655c6/scratchpad/eval/wt-C` and the range `pr-base..pr-head`. Line numbers are line numbers in the pr-head tree.

| Record item | Value |
| --- | --- |
| base (`pr-base`, head of #846) | 6162f215fc0a64f0f2400e9cf8feab4543f484c0 |
| head (`pr-head`, PR #847 head, also HEAD) | 2ca89b767e4706056ea678d7c589f2b8db318106 |
| merge target `main` | fd4300e99b69d83328190ca8c131791a28846320 |
| ticket #665 updated_at | 2026-09-15T14:29:52Z |
| PR body | created 2026-10-02, unedited since |
| CI for head | all checks green, including the MySQL matrix |

The stock skill does not consult PR bodies or tickets, so it never asked for those values and I did not read the context directory. The record values above come from the task brief.

**Anchor check against `git diff pr-base pr-head`.** Nine files changed. Every cited file is in the diff and every cited line sits inside an added hunk. I read each anchor line in the pr-head tree:

- `serializers.py:80` is the `rule_profile_id = serializers.IntegerField(...)` declaration (added hunk lines 57 to 89).
- `api.py:34` is `"resolve_competency_tag"` in the `__all__` additions (hunk lines 34 to 36).
- `api.py:113` is the `tag.taxonomy is None or not is_competency_taxonomy(...)` check in `resolve_competency_tag`.
- `api.py:136` is the `defaults={"name": f"{tag.value} (root)"}` line in `create_leaf_group`.
- `api.py:160` is the leaf test `group.parent_id is None or group.course_id is not None` in `resolve_supplied_leaf_group`.
- `api.py:193` is the `tag_object(object_id, tag.taxonomy, existing_values)` call.
- `api.py:197` (cited twice) is the `CompetencyRuleProfile.objects.get(...)` system-default lookup. All `api.py` anchors from 113 up fall in the single added hunk at lines 102 to 297.
- `test_criteria_group.py:52` is the "one-root-per-tag constraint" comment (hunk lines 52 to 57).
- `views.py:84` is `tag = resolve_competency_tag(self.kwargs["tag_id"])` in `create` (hunk lines 54 to 100).
- Both cut candidates also check out: the duplicated assert is an added line in the `test_api.py` diff, and `_` is rebound at `api.py:133` and `api.py:138` while line 11 imports `gettext_lazy as _`.

**Sub-agents dispatched by me with the Agent tool: none.** The `code-review` skill runs as a forked execution through the Skill tool and returned a finished result. Its report says it ran "eight angles", but that fan-out happened inside the fork, and the agent types, models, and effort levels it used are not visible to the invoking session. The task instruction to dispatch the skill's sub-agents myself with explicit models could therefore not be performed as written. I did not work around it by re-reviewing or by dispatching agents of my own.

**Commands and tests I ran.**

1. `git rev-parse pr-base pr-head`: both SHAs matched the expected values. `git status --short` was empty.
2. `Skill code-review` with args `high pr-base..pr-head`, invoked once.
3. `git diff --stat pr-base pr-head` and a `-U0` hunk listing for the four cited source files, plus reads of each anchor line.
4. Interpreter check in wt-C with the venv activated and `PYTHONPATH` set to the wt-C `src`: `openedx_learning.__file__` resolved to `/private/tmp/claude-501/-Users-jesperhodge-openedx-openedx-core/bc59e103-2d05-4b61-9b05-8c383fd655c6/scratchpad/eval/wt-C/src/openedx_learning/__init__.py`.
5. `python manage.py makemigrations --check --dry-run`: "No changes detected". This confirms the skill's migration claim.
6. `pytest tests/openedx_learning/applets/cbe/test_criteria_group.py --no-cov -p no:cacheprovider` at pr-head: 6 passed.
7. A temporary worktree at pr-head under `/private/tmp/claude-501/-Users-jesperhodge-openedx-openedx-core/bc59e103-2d05-4b61-9b05-8c383fd655c6/scratchpad/eval/agent-C/wt-basecheck`, with the pr-base version of `test_criteria_group.py` copied over it and `PYTHONPATH` pointed at that worktree's `src` (import path confirmed). The same pytest command: 6 passed. This confirms the skill's claim behind the ninth finding that the old test body passes unchanged against the new constraint. The skill reported "3 passed" for the same check. My run of the full module reports 6, so the skill likely ran a subset. The conclusion is unaffected.
8. Removed the temporary worktree. `git worktree list` no longer lists it and `git status --short` in wt-C is empty.

**Not performed.** No network access, no `gh`, no remotes added, no linters run beyond what the skill did internally, no code edited, nothing posted.

**Wall-clock time.** Approximately 10 to 15 minutes end to end, most of it inside the forked skill run. This is an estimate; the harness gives me no timestamps.