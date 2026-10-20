# PR Review Summary

**Review record**
- Pull request: openedx/openedx-core #847, "feat: add endpoint for creating competency criteria". It implements ticket #665.
- Snapshot reviewed:
  - base = `6162f21` (`pr-base`, the head of #846)
  - head = `2ca89b767e4706056ea678d7c589f2b8db318106` (authored 2026-10-09)
  - merge target main = `fd4300e99b69d83328190ca8c131791a28846320` (upstream main as of 2026-10-14T04:44Z)
  - merge-base of head and main = `b6a58bf88`
- Context as of review time:
  - The PR was created 2026-10-02. Its body was not edited after that.
  - Ticket #665 updated_at is 2026-09-15T14:29:52Z.
  - CI was green for this head, including the MySQL matrix.
  - There were no prior reviews.
- Scope: the PR's own change, `git diff pr-base pr-head`, which touches 9 files with 1135 lines added and 14 removed. It was reviewed against main as it is now, because main has moved: #716, #846 and #861 have landed there.
- Procedure: `pr-review-toolkit` `review-pr` with the aspects `all parallel`. All five review agents ran concurrently. `code-simplifier` was not run (see the Process log).

Agent names in brackets are the agents that raised each item. "Verified" means at least one agent reproduced the behavior by running code. Each item says when it rests on inference instead.

## Critical Issues (2 found)

- **[code-reviewer, pr-test-analyzer, type-design-analyzer, silent-failure-hunter, comment-analyzer] The PR's migration number collides with a migration already on main, so `migrate` refuses to run after merge.** `src/openedx_learning/migrations/0014_criteria_group_unique_constraints.py:11-12`
  - **Mechanism:** main now carries `0014_add_archived_to_criteria_group_and_criterion` from #716. Both that migration and this PR's `0014` depend on `0013`.
  - **Verified:** on main plus this commit, `makemigrations --check` reports "Conflicting migrations detected; multiple leaf nodes", and pytest errors while creating the test database. CI was green only because it ran against the pre-#716 base.
  - **Fix:** rebase onto main, rename the migration to `0015_...`, and make it depend on main's `0014`. pr-test-analyzer renumbered it locally that way, and all 212 CBE tests passed.
  - **The rebase is needed regardless:** code-reviewer reports that `git merge main` produces add/add conflicts in 8 files. The cause is that #846 was squash-merged in a different form from the `pr-base` snapshot this branch carries.

- **[code-reviewer] `from openedx_catalog.models import CourseRun` breaks the `isolated_apps` import-linter contract that #861 added to main.** `src/openedx_learning/applets/cbe/api.py:16`
  - **Mechanism:** main's `.importlinter` lets code outside `openedx_catalog` import only that app's `api`, `models_api`, `data` and `tests` modules.
  - **Verified:** code-reviewer ran `lint-imports` with main's configuration and got BROKEN. I confirmed it separately by reading main's `.importlinter` and `api.py:16`.
  - **Rule:** the project CLAUDE.md says "Respect the layering in `.importlinter`... Don't loosen a rule to fix the build."
  - **Fix:** `from openedx_catalog.models_api import CourseRun`, which is what `models/criteria.py:18` already does.

## Important Issues (14 found)

- **[all five agents] Invalid combinations of the rule fields return an HTML 500 instead of a 400.** `api.py:196-212`, `serializers.py:80-88`, `views.py:98-99`
  - **Mechanism:**
    - `CompetencyCriterion.save()` calls `full_clean(validate_constraints=False)`, so only the database enforces `oel_cbe_criterion_profile_xor_override_check`.
    - The database rejection is an `IntegrityError`.
    - The view converts only Django's `ValidationError`, so the `IntegrityError` becomes a 500.
  - **Verified:** `rule_profile_id` sent together with both override fields returns 500, and `rule_payload_override` sent alone returns 500.
  - **Effect on #665:** the acceptance criterion "A criterion is never created without a rule source" holds only because the database refuses the row.
  - **Fix:** validate the combination before the transaction opens, either in a serializer `validate()` or in `associate_competency_criterion()`, keyed to the request's field names. Add a parametrized test over the combinations.

- **[all five agents] #665's acceptance criterion "A taxonomy-scoped rule profile is assigned ahead of the system default" is not implemented, not tested, and not listed among the commit's deviations.** `api.py:197-202`
  - **Verified:** a probe created a live taxonomy-scoped profile and got the system default's id back.
  - **The ADR and the ticket disagree:** the scenario is at `issue_665.md:127-133`, but ADR 0002 Decision 4's MVP note (`0002-competency-criteria-model.rst:237`) says only the system default exists in this phase. I confirmed both texts.
  - **Why it matters:** ADR 0002 never re-resolves the assignment later, so a wrong pick is permanent.
  - **Fix:** either implement the rule (use a live taxonomy-scoped profile if one exists, otherwise the system default) and add the test, or record the deferral as a deviation in the commit message and the PR body. In both cases, correct the docstring at `api.py:183-185`, which presents the hard-coded default as what Decision 4 prescribes.

- **[code-reviewer, pr-test-analyzer, silent-failure-hunter] A v2 library usage key returns a 500 instead of the 400 that #665 requires.** `api.py:271-279`
  - **Mechanism:** `lb:Org:lib:problem:p1` parses as a valid key, but its `course_key` is a `LibraryLocatorV2`. `CourseKeyField` then raises `AssertionError`, and the `except CourseRun.DoesNotExist` clause does not catch it.
  - **Verified.**
  - **Fix:** check `isinstance(usage_key.context_key, CourseKey)` and raise the same `object_id` `ValidationError`. Add an `lb:` test.

- **[code-reviewer, silent-failure-hunter] In openedx-platform, a malformed `object_id` gets a 403, not a 400.** `views.py:82-87`
  - **Mechanism:**
    - The view calls `has_perm("oel_tagging.can_tag_object", ...)` with the raw string before anything parses it.
    - The platform's `can_change_object_tag_objectid` returns False for keys it cannot parse (`edx-platform/openedx/core/djangoapps/content_tagging/rules.py:213-232`), so the request is refused.
  - **Why the tests pass anyway:** the autouse fixture at `test_views.py:38-44` grants permission for every string, which hides the problem from `test_malformed_object_id_is_400` (`test_views.py:608`).
  - **Verified:** reproduced with a predicate that parses keys the way the platform's does.
  - **Ordering in #665:** the ticket's Logic section parses the key and resolves the course run before checking permission.
  - **Fix:** validate `object_id` before the permission check, for example with a serializer `validate_object_id()`. Make the test predicate refuse unparseable keys.

- **[silent-failure-hunter, comment-analyzer] Associating a second competency with a subsection can silently delete another competency's `ObjectTag` and, through `CASCADE`, its `CompetencyCriterion`.** `api.py:190-193`
  - **Mechanism:** the code reads existing tags with `get_object_tags()`, which hides rows on a disabled taxonomy and deleted tags. It then passes the merged list to `tag_object()`, which replaces every raw row for that taxonomy and object. Any row the read hid is deleted.
  - **Verified for a disabled taxonomy:**
    - Through REST, only a superuser can reach this.
    - Through the public Python API, any caller can.
    - When the sibling criterion has a learner-status row (`PROTECT`), the same request returns a 500 instead.
  - **Concurrent variant (simulated only, not run on MySQL):**
    - Requests for different tags lock different `Tag` rows, so they are not serialized against each other.
    - Django's MySQL backend defaults to READ COMMITTED. Two agents verified this in `django/db/backends/mysql/base.py:238`.
    - If another request commits between this request's two reads, its row is deleted.
  - **Severity:** silent-failure-hunter rated this CRITICAL. I placed it under Important because the deterministic trigger needs a disabled taxonomy plus a superuser or a direct API caller, and nobody has measured the concurrent trigger on MySQL.
  - **Fix:** reject disabled taxonomies in `resolve_competency_tag()`, and make the write add-only so it cannot remove sibling rows.

- **[code-reviewer, pr-test-analyzer, type-design-analyzer, silent-failure-hunter] An archived `CompetencyRuleProfile` is accepted as `rule_profile_id`.** `serializers.py:80`, `api.py:206-212`
  - **Verified:** the request returned 201.
  - **Why it matters:** ADR 0002 Decision 3 and the model's help text both say archived profiles are hidden from new associations. Ticket #717 covers archived groups and criteria, not profiles, so it does not cover this case.
  - **Fix:** use a `PrimaryKeyRelatedField` over `get_competency_rule_profiles()`, or add an explicit check keyed to `rule_profile_id`. That also fixes the error key that is currently `rule_profile`.

- **[silent-failure-hunter, pr-test-analyzer] `tag_object()` failures that it documents become 500s.** `api.py:193-194`
  - **Verified cases:**
    - On a competency taxonomy with `allow_multiple=False`, adding a second competency to the same subsection raises `ValueError`.
    - On a free-text competency taxonomy, the re-fetch at `api.py:194` raises `ObjectTag.DoesNotExist`.
  - **Precedent:** the tagging app's own view converts these errors to 400s (`openedx_tagging/rest_api/v1/views.py:591-595`).
  - **Fix:** convert them to a field-keyed `ValidationError`, or reject such taxonomies up front.

- **[type-design-analyzer, comment-analyzer] Leaf groups are created with `course_id` null, which contradicts ADR 0002 Decision 2, and the new unique constraint depends on that.** `api.py:144-149`, `models/criteria.py:113-124`
  - **The conflict:** ADR 0002 line 86 says "Within a course-scoped subtree, every group carries the same `course_id`." #665 itself specifies leaves with `course_id` null (`issue_665.md:237`, `:261`). I confirmed both texts. The PR follows the ticket, and the ticket contradicts the ADR.
  - **Why the constraint depends on it:** if leaves carried `course_id`, sibling leaves would collide on the `(tag, course, parent)` constraint.
  - **Possible effect on #681 (inference):** the ADR's retrieval rule (`0002...rst:112`) would read leaves with a null course as root-scope nodes.
  - **Fix:** the maintainers need to choose. Either amend the ADR, or change the leaf shape together with the constraint. type-design-analyzer suggests a derived `level` column, following the `scope_code` precedent. At a minimum, say in `criteria.py:114-116` and in the `resolve_supplied_leaf_group()` docstring that this convention comes from #665 and departs from the ADR.

- **[type-design-analyzer, comment-analyzer] `__all__` makes public some functions that can persist states the API is meant to forbid.** `api.py:27-38`
  - **The functions:** `create_leaf_group`, `resolve_supplied_leaf_group` and `create_competency_criterion`.
  - **What they allow:**
    - `create_leaf_group` leaves a committed leaf with no criterion, which is an empty group.
    - `create_competency_criterion` attaches a criterion to a non-leaf group, or to another tag's group, without checking.
  - **Why now:** CLAUDE.md treats public APIs as stable, and changing them later goes through DEPR. Narrowing them now costs nothing.
  - **Fix:** export only `associate_competency_criterion`, plus `resolve_competency_tag`, which the view needs. Alternatively, document each function's preconditions and mark them "UNSTABLE:" the way `get_competency_rule_profiles()` is marked.

- **[pr-test-analyzer] Two break-and-restore checks show test gaps.**
  - **The competency-taxonomy check is untested:** with `or not is_competency_taxonomy(tag.taxonomy)` removed from `api.py:113`, all 68 API and view tests still pass. That leaves the #665 case "tag exists but is not on a Competency Taxonomy" untested.
  - **The lock tests pass without a lock:** with both `select_for_update().get(...)` calls (`api.py:132`, `:285`) replaced by querysets that are never evaluated, so no lock is taken, all three lock tests still pass (`test_api.py:295`, `:438-465`).
  - **The commit message overclaims:** it says the tests cover "the concurrent-request race case". They do not.
  - **Fix:**
    - Add the 404 test.
    - Add a MySQL-only threaded test, or a `CaptureQueriesContext` assertion that a `SELECT ... FOR UPDATE` is sent.
    - Rename `test_api.py:262` and `:280` to describe what they actually test.

- **[comment-analyzer, pr-test-analyzer, type-design-analyzer, silent-failure-hunter] Several new comments state things that are false.** CLAUDE.md treats stale comments as bugs.
  - **`views.py:66-72`, repeated in the commit message:** the claim that every existing `DjangoObjectPermissions` class contributes only the authentication gate is false. Verified: `view_competencyruleprofile`, `add_taxonomy`, `change_taxonomy` and `delete_taxonomy` all return False for a plain user when no object is given. This claim is the commit's stated reason for not adding a permission class.
  - **`test_criteria_group.py:52-53`:** the comment cites a "one-root-per-tag constraint" that does not exist. The pre-PR test body passes against the PR's code, so lines 52-57 should be reverted.
  - **`api.py:222`, repeated in the commit message:** the comment reasons about REPEATABLE READ. Django's MySQL backend runs READ COMMITTED, and I confirmed by grep that neither edx-platform's envs nor Tutor's templates override the isolation level. This rationale is also in tension with `api.py:126` and `:130-131`.
  - **`views.py:60-64`:** the docstring credits the API function with the permission check, but the view performs it.

- **[code-reviewer, comment-analyzer, pr-test-analyzer, type-design-analyzer] The PR body and the commit message describe an earlier draft of this PR.**
  - **The PR body still describes:**
    - migration `0004` with two partial constraints
    - a `source=` mapping to the ticket's field names
    - a test file named `test_criteria_models.py`
    - "147 passed", and "all 20" acceptance scenarios tested, when #665 has 22
  - **The commit message:**
    - names `resolve_or_create_leaf_group()`, but the function is `create_leaf_group()`. #717 also uses the old name.
    - calls `associate_competency_criterion()` the "single public entry point", which contradicts `__all__`.
    - says every acceptance scenario is tested.
  - **Fix:** rewrite the PR body against the actual diff, and amend the commit message.

- **[code-reviewer, pr-test-analyzer, type-design-analyzer, comment-analyzer] The response uses a field name that differs from #665's acceptance criteria, and this is not declared.**
  - **The mismatch:** the first scenario names the field `oel_tagging_objecttag_id`, but the serializer emits `object_tag_id` (`serializers.py:81`). The tests assert the new name (`test_views.py:320`, `:508`).
  - **The comment on #665 does not cover it:** according to pr-test-analyzer, the rename agreed in the 2026-09-14 comment covered only `group_id` and `rule_profile_id`.
  - **Fix:** confirm the name with the ticket owner, list it as a deviation, and add an assertion on the exact set of response keys.

- **[code-reviewer, pr-test-analyzer] The leaf group is created with an empty `name`.** `api.py:144-149`
  - **The deviation:** #665's first scenario says the leaf is "named from the course's display name".
  - **Verified.**
  - **Impact:** low in practice, because #672 does not read group names.
  - **Fix:** set `name=course_run.title` and assert it in the hierarchy test, or declare the deviation.

## Suggestions (10 found)

- **[code-reviewer, pr-test-analyzer, type-design-analyzer, comment-analyzer] After the rebase, the lookups do not consider `archived`.** `api.py:133-143`, `:152-166`, `:215-240`
  - **The gap:** after the rebase onto #716's `archived` fields, the lookups reuse archived root and course-level groups, accept an archived leaf as `group_id` (pr-test-analyzer verified this on main plus the PR), and count archived criteria as duplicates.
  - **#717 owns this work:** I checked, and #717 explicitly owns exactly these changes inside #665's flow and is blocked by #665. It also accepts as permanent for the MVP that an archived course-level group blocks new criteria for that course, and it assumes #665's unique constraints stand as defined.
  - **Recommendation:** this is a sequencing item, not a blocker for this PR. silent-failure-hunter reached the same conclusion. Schedule #717 promptly after this merges.
- **[silent-failure-hunter, type-design-analyzer] Nothing in the database enforces one root group per tag.**
  - **Verified:** with two roots present, `get_or_create(tag, parent=None)` raises `MultipleObjectsReturned`, and every later derive-path request for that competency returns a 500 (`api.py:133-137`).
  - **Fix:** document that every writer of root groups must hold the `Tag` row lock, or log a clear error. type-design-analyzer's derived `level` column would also give the database a backstop.
- **[silent-failure-hunter, pr-test-analyzer, type-design-analyzer] Error keys do not match the request's field names.** An invalid payload is keyed `__all__`, and a nonexistent profile is keyed `rule_profile` instead of `rule_profile_id` (`views.py:98-99`).
- **[silent-failure-hunter] Unhandled errors reach the JSON client as Django's HTML 500 page, and the CBE code logs nothing.** `views.py:56-100`
  - **Precedent:** `TaggingExceptionHandlerMixin`.
  - This is a team decision.
- **[silent-failure-hunter] A missing or archived system-default profile becomes an anonymous `DoesNotExist` 500.** `api.py:197-202`. Log what is wrong, or raise `ImproperlyConfigured`.
- **[type-design-analyzer] Type and naming points:**
  - The domain API raises `Http404` (`api.py:108`, `:114`, `:156`, `:159`), which is a first for this repository's API modules.
  - `logic_operator` is typed `str | None`, and `logic_operator or LogicOperator.OR` turns `""` into `OR` (`api.py:148`).
  - The rule profile is spelled `competency_rule_profile_id` in one place and `rule_profile_id` in another along the same call chain.
- **[type-design-analyzer, comment-analyzer] The leaf check is a shape heuristic.** A group placed under a leaf is rejected with the wrong message, "must belong to the given course" (`api.py:160-164`). #665's open questions already flag this.
- **[pr-test-analyzer] Test hardening:**
  - The rollback test should also assert that the `ObjectTag` was rolled back (`test_api.py:518-538`).
  - A pre-existing `ObjectTag` without a criterion is untested.
  - The permission test covers only one of the two cases the scenario names. The 401 and the "no rows written on 403" checks are also untested.
  - The "no rows created" clauses are unchecked at `test_views.py:351`, `:410` and `:468`.
  - `test_api.py:191` duplicates the assertion on line 190.
  - The global `rules.set_perm()` fixture is never restored (`test_views.py:38-44`).
  - The `group_id` rejection tests could assert the message text.
- **[comment-analyzer] Smaller comment fixes:**
  - The constraint's name and violation message overstate what it enforces (`criteria.py:119-122`).
  - "one per criterion" is inaccurate (`api.py:127`).
  - The rationale at `criteria.py:110-112` is wrong.
  - The #666 placeholder at `api.py:204` sits after the `tag_object()` write and lacks the parsed key.
  - The view docstring does not state the endpoint contract (`views.py:57-73`).
  - The comment at `api.py:235-236` sits in the wrong branch.
  - "already associated" is ambiguous (`api.py:217`), and "its course" is imprecise (`api.py:157`).
  - `test_views.py:561` refers to a planning document that is not in the repository.
  - The assert at `api.py:267-268` is redundant.
  - `views.py:63` and `serializers.py:75` use "--" as an em dash.
  - The migration file name is plural for a single constraint.
- **[code-reviewer, below its 80-confidence reporting bar]**
  - Because the tag is resolved before the permission check, a caller can tell 404 from 403 for tag ids.
  - The tag is resolved twice per request.
  - `__all__` is not alphabetical.
  - The migration's "Generated by Django" header was written by hand.

## Strengths

- **Locking design (code-reviewer, type-design-analyzer):** the code locks the `Tag` row, does locking reads for the duplicate check, then creates groups and the criterion inside one `transaction.atomic()`. This is a sound way to get race safety without partial indexes on MySQL, and the commit message explains it honestly.
- **Tag preservation (pr-test-analyzer):** the read-merge-write around `tag_object()` keeps sibling competency tags in the normal case. Its test deliberately uses two tags from the same taxonomy, which is the only case that exercises the replace behavior. A break-and-restore check that replaced the merge with `[tag.value]` was caught.
- **Rollback (pr-test-analyzer):** the rollback test proves ADR 0002's rule against persisting empty groups. Removing the outer `atomic()` fails it.
- **Error handling (silent-failure-hunter):** the `except` clauses are specific and chained with `from exc`, the two 404s have distinguishable messages, and the Django-to-DRF `ValidationError` conversion keeps the field dictionary.
- **Constraint test (pr-test-analyzer):** the database constraint is tested directly, bypassing `get_or_create()` (`test_api.py:308`).
- **Comment quality (comment-analyzer):** most comments explain why, not what, for example `api.py:130-131`, `serializers.py:72-76` and `criteria.py:114-116`.
- **Reuse and API shape (type-design-analyzer, code-reviewer):** the view reuses `oel_tagging.can_tag_object` and `ObjectTagPermissionItem` instead of inventing a new authorization path. The serializer never owns persistence, and the public entry point takes keyword-only arguments.
- **Coverage (pr-test-analyzer):** 17 of #665's 22 scenarios have a direct REST-level test, and most tests assert database state rather than mocks.

## Recommended Action

1. **Fix the critical issues first.**
   - Rebase onto main, resolving the add/add conflicts left by the squash-merge of #846.
   - Renumber the migration to `0015` so it depends on main's `0014`.
   - Import `CourseRun` from `openedx_catalog.models_api`.
   - Re-run `lint-imports`, `makemigrations --check`, the CBE suite and the MySQL CI on the rebased branch.
2. **Address the important issues.**
   - Turn each invalid-input class into a field-keyed 400: rule-field combinations, `lb:` keys, `tag_object()` errors and archived profiles.
   - Validate `object_id` before the permission check.
   - Decide the taxonomy-scoped profile question: implement it, or declare the deviation and reconcile it with ADR 0002's MVP note.
   - Close the sibling-deletion path: reject disabled taxonomies and make the tag write add-only.
   - Take the leaf `course_id` conflict between the ADR and the ticket to the maintainers.
   - Narrow `__all__`.
   - Fix the false comments.
   - Rewrite the PR body and amend the commit message.
   - Settle the `object_tag_id` name and the leaf's `name`.
   - Add the tests that the two break-and-restore checks showed are missing.
3. **Consider the suggestions,** and sequence #717 right after this merges for the `archived` handling.
4. **Re-run the review after the fixes,** on the rebased branch.

## Agent reports

### code-reviewer (dispatched 1st)

# Code review: openedx-core PR #847 (code-reviewer agent)

## What I reviewed

- Commit range `pr-base..pr-head`: `6162f215fc0a64f0f2400e9cf8feab4543f484c0` (head of #846, the stacked base) to `2ca89b767e4706056ea678d7c589f2b8db318106` (the PR's single commit, "feat: add endpoint for creating competency criteria"). All anchors below are `file:line` at pr-head.
- Merge context: `main` at `fd4300e99b69d83328190ca8c131791a28846320`, which now contains #846 (squash-merged as `a58d833`), #716 (`afce3e7`, the `archived` fields and migration `0014_add_archived_to_criteria_group_and_criterion`), and #861 (`cd2b2a0`, the `isolated_apps` import-linter contract).
- Ticket #665's acceptance criteria (the 22 Gherkin scenarios), the PR body, the commit message, ADR 0002, the tagging and catalog API functions the new code composes, and the platform-side `oel_tagging.can_tag_object` implementation in `edx-platform` (read only).

How I verified: I ran Django's migration check and `lint-imports` against pr-head combined with main's files in a temporary worktree, and I ran a scratch pytest file against pr-head exercising request shapes the PR's tests do not cover. Each finding says whether it was confirmed by running code or is inference from reading.

One procedural note before the findings: `git merge main` from pr-head produces add/add conflicts in `rules.py`, `urls.py`, `views.py`, `serializers.py`, `conftest.py`, `test_api.py`, `test_rules.py`, and `test_views.py`, because the version of #846 that was squash-merged to main differs from the `pr-base` snapshot this branch carries. The PR needs a rebase onto main regardless of the findings below. Findings 1 and 2 survive that rebase unless they are fixed deliberately.

## Critical (90-100)

### 1. Migration `0014` collides with main's `0014`; `migrate` refuses to run after merge (confidence 98, confirmed by running)

- `src/openedx_learning/migrations/0014_criteria_group_unique_constraints.py:11-12`
- Main already has `0014_add_archived_to_criteria_group_and_criterion`, and both files depend on `0013_alter_historicalcompetencycriteriagroup_history_date_and_more`. With both present, Django reports: `CommandError: Conflicting migrations detected; multiple leaf nodes in the migration graph: (0014_add_archived_to_criteria_group_and_criterion, 0014_criteria_group_unique_constraints in openedx_learning)`. I reproduced this with `python manage.py makemigrations --check --dry-run` and `migrate --plan` on pr-head plus main's `0014` file. CI was green only because it ran against the pre-#716 base.
- Fix: rename the PR's migration to `0015_criteria_group_unique_constraints.py` and point its dependency at `0014_add_archived_to_criteria_group_and_criterion`. A `makemigrations --merge` migration would also resolve the graph, but renumbering keeps the history linear, which is what every other migration in this app does.

### 2. `from openedx_catalog.models import CourseRun` breaks the `isolated_apps` import-linter contract that is now on main (confidence 97, confirmed by running)

- `src/openedx_learning/applets/cbe/api.py:16`
- Main's `.importlinter` (from #861) allows code outside `openedx_catalog` to import only `openedx_catalog.{api,models_api,data,tests}`. Running `lint-imports` on pr-head with main's `.importlinter` and `test_utils/isolated_apps_contract.py` gives: `"code outside an isolated app only reaches its public API" BROKEN ... openedx_learning.applets.cbe.api:16: imported from non-public API of openedx_catalog: from openedx_catalog.models import CourseRun`. CLAUDE.md: "Respect the layering in `.importlinter`; `lint-imports` enforces it. Don't loosen a rule to fix the build."
- Fix: `from openedx_catalog.models_api import CourseRun`, which is exactly what `models/criteria.py:18` already does in this applet. `get_course_run` from `openedx_catalog.api` (line 15) is fine.

## Important (80-89)

### 3. The acceptance criterion "A taxonomy-scoped rule profile is assigned ahead of the system default" is not implemented, not tested, and not listed as a deviation (confidence 88, confirmed by running)

- `src/openedx_learning/applets/cbe/api.py:197-202`
- When all three rule fields are omitted, the code unconditionally fetches the all-null-scope profile. #665's AC has a dedicated scenario requiring that, when the competency's taxonomy has its own `CompetencyRuleProfile`, the criterion's `rule_profile_id` is that taxonomy's profile. ADR 0002 Decision 4's resolution table agrees ("Course: No, Org: No, Taxonomy: Yes → Taxonomy"), and its item 1 says the creating screen supplies the taxonomy context, which this endpoint has in `tag.taxonomy`. My probe created a taxonomy-scoped profile and posted with no rule fields: the response carried the system default's id, not the taxonomy profile's id. No test in `test_views.py` or `test_api.py` covers this scenario, and the commit message's "Deviations from the ticket's literal text" lists only the all-null and duplicate-check deviations. The PR body claims "all 20" AC scenarios are tested; the AC has 22, and this is one of the two missing (the other, "never created without a rule source", is covered indirectly by the DB constraint).
- Fix: resolve the profile as `CompetencyRuleProfile.objects.filter(archived=False, competency_taxonomy_id=tag.taxonomy_id).first()` falling back to the system default (organization and course scoped profiles have no source at this endpoint, so the only candidates are the taxonomy row and the system default), and add the AC test. If the developer-approved decision is to defer this to a later ticket, say so in the commit message and the PR body alongside the other deviations.

### 4. A library-block usage key produces an unhandled `AssertionError` (HTTP 500) instead of the ticket's 400 (confidence 88, confirmed by running)

- `src/openedx_learning/applets/cbe/api.py:271-279`
- `UsageKey.from_string("lb:Org:lib:problem:p1")` parses, so the `InvalidKeyError` branch does not fire; `usage_key.course_key` is then a `LibraryLocatorV2`, and `get_course_run()` runs `CourseRun.objects.get(course_key__exact=...)`, whose `CourseKeyField` asserts the value is a `CourseKey`. Only `CourseRun.DoesNotExist` is caught, so the request fails with `AssertionError: lib:Org:lib is not an instance of <class 'opaque_keys.edx.keys.CourseKey'>`. The ticket's AC says a usage key whose course does not resolve to a `CourseRun` is a 400 keyed on `object_id`.
- Fix: after parsing, check `isinstance(usage_key.context_key, CourseKey)` (or guard `usage_key.course_key`) and raise the same `ValidationError({"object_id": ...})` when it is not a course key; add a test with a `lb:` key.

### 5. Invalid rule-field combinations surface as `IntegrityError` (HTTP 500) rather than 400 (confidence 88, confirmed by running)

- `src/openedx_learning/applets/cbe/rest_api/v1/serializers.py:80-88`, `src/openedx_learning/applets/cbe/api.py:206-212`
- The serializer accepts `rule_profile_id`, `rule_type_override`, and `rule_payload_override` independently, and `CompetencyCriterion.save()` calls `full_clean(validate_constraints=False)`, so the `oel_cbe_criterion_profile_xor_override_check` constraint is only enforced by the database. Two probes: `rule_profile_id` plus both overrides, and `rule_payload_override` alone, both raised `IntegrityError: CHECK constraint failed: oel_cbe_criterion_profile_xor_override_check`. MySQL 8.0.16+ enforces CHECK constraints, so production behaves the same. (By contrast, `rule_type_override` alone and an unknown `rule_profile_id` do come back as 400 via `full_clean`, although the latter is keyed `rule_profile`, not the request's `rule_profile_id`.)
- Fix: a `validate()` on `CompetencyCriterionSerializer` that enforces "either `rule_profile_id` alone, or both overrides together, or none" (that is what a DRF serializer is for), and tests for the two rejected shapes.

### 6. An archived `CompetencyRuleProfile` is accepted as `rule_profile_id` for a new criterion (confidence 85, confirmed by running)

- `src/openedx_learning/applets/cbe/rest_api/v1/serializers.py:80`
- `rule_profile_id` is a plain `IntegerField`, so any existing profile id passes. My probe created a taxonomy-scoped profile with `archived=True`, posted it as `rule_profile_id`, and got 201 with `criterion.rule_profile.archived == True`. ADR 0002 Decision 3 item 8 says archived profiles "are hidden from authoring and new associations", and the model's own help text at `models/criteria.py:188-194` says the same. The applet already exposes the live set as `get_competency_rule_profiles()` (`api.py:67`).
- Fix: declare the field as `PrimaryKeyRelatedField(source="rule_profile", queryset=get_competency_rule_profiles(), required=False, allow_null=True)` (or validate in `create_competency_criterion`), so an archived id is a 400.

### 7. The new unique constraint and the group lookups do not account for the `archived` lifecycle that is now on main (confidence 82, inference from code on main and ADR 0002)

- `src/openedx_learning/applets/cbe/models/criteria.py:113-124`, `src/openedx_learning/applets/cbe/api.py:133-141`, `api.py:152-165`, `api.py:215-240`
- Main's `CompetencyCriteriaGroup.archived` (from #716) is documented in its help text as hiding a group "from authoring and new associations", matching ADR 0002 Decision 2 item 8 and Decision 7. After the rebase this PR will compile against that model, and: (a) `get_or_create(tag, parent=None)` and `get_or_create(tag, course, parent=root)` will return an archived root or course-level group and attach a new leaf beneath it; (b) `resolve_supplied_leaf_group` will accept an archived leaf; (c) `_reject_duplicate_criterion` will count an archived criterion as a live duplicate. More fundamentally, `UniqueConstraint(fields=["tag", "course", "parent"])` makes an archived course-level group permanently occupy the only `(tag, course, root)` slot, so once a course-level group is archived (#674's planned archive cascade does exactly that when all of a group's children are archived; that part is a ticket, not code yet), no live replacement can ever be created for that competency in that course. This is the same problem `CompetencyRuleProfile` solved with the derived `scope_code` column that goes null on archive (`criteria.py:169-180`, ADR 0002 Rejected Alternative 6), rather than a unique constraint over raw columns.
- Fix: decide the archive semantics before merging the constraint. Options: scope the constraint through a derived column that is null while archived, as the rule profile does; or drop the constraint and rely on the tag-row lock alone (the commit message already treats the lock as the primary mechanism and the constraint as a backstop). In either case, filter `archived=False` in the three lookups above.

### 8. A malformed `object_id` returns 403 in production, not the ticket's 400, because the permission check runs before the key is parsed (confidence 82, confirmed by simulation plus reading platform code)

- `src/openedx_learning/applets/cbe/rest_api/v1/views.py:82-87`, `src/openedx_learning/applets/cbe/api.py:271-273`
- `object_id` is a bare `CharField`, so `"not-a-usage-key"` passes `is_valid()`; the view then calls `has_perm("oel_tagging.can_tag_object", ...)` with that string. In `edx-platform`'s `content_tagging/rules.py:213-232`, `can_change_object_tag_objectid` calls `get_context_key_from_key_string`, which raises `ValueError` for an unparseable string, and the predicate returns `False`, so the view raises `PermissionDenied`. The AC scenario "Reject creation with a missing or malformed object_id" requires 400 with the field identified, and the ticket's Logic section orders parsing (step 2) and course resolution (step 3) before the permission check (step 4). `test_views.py:608` passes only because the test override at `test_views.py:39` allows every object_id that does not contain the marker. I reproduced the 403 with a predicate that mirrors the platform's parse-and-refuse behavior.
- Fix: add `validate_object_id` to the serializer that parses the usage key (and, per finding 4, requires a course context key), so the permission check receives a well-formed key. Resolving the `CourseRun` before the permission check would also match the ticket's step order, though 403 for a nonexistent course is a defensible choice if stated.

### 9. The leaf group is created with an empty `name`; the AC says it is named from the course's display name (confidence 80, confirmed by running)

- `src/openedx_learning/applets/cbe/api.py:144-149`
- The root and course-level groups get the ticket's recommended placeholder names, but `CompetencyCriteriaGroup.objects.create(...)` for the leaf passes no `name`, so it is stored as `""`. The first AC scenario states "a new leaf CompetencyCriteriaGroup is created, parented under the course-level group, named from the course's display name". No test asserts the leaf's name. The frontend ticket #672 derives its section headers from a content-search display-name map rather than from group names, so the practical impact is low, but it is an undeclared deviation.
- Fix: set `name=course_run.title` (or whatever naming the team settles on) on the leaf, and assert it in `test_create_leaf_group_builds_the_full_hierarchy_on_first_use`; or add it to the declared deviations.

### 10. The PR body and commit message describe code that is not what pr-head contains (confidence 85, confirmed by diffing text against code)

- PR body (`pr_847_body.md`) and `git log -1 pr-head`.
- The PR body says the migration is `0004_criteria_group_unique_constraints.py` adding "two partial `UniqueConstraint`s" (one root per tag with `condition=Q(parent__isnull=True)`); the code has one unconditional constraint in `0014`, and the model comment at `criteria.py:114-116` explains why there is no partial one. The body says the response names are the ticket's `competency_rule_profile_id`, `competency_criteria_group_id`, and `oel_tagging_objecttag_id` "mapped via explicit `source=`"; the serializer at `serializers.py:71-88` emits `rule_profile_id`, `group_id`, and `object_tag_id` with no `source=`, and its docstring says so. The body names `test_criteria_models.py`; the changed file is `test_criteria_group.py`. Both the body and the commit message name `resolve_or_create_leaf_group()`; the function is `create_leaf_group()` (`api.py:118`, `__all__` at `api.py:35`). The AC's response field `oel_tagging_objecttag_id` versus the emitted `object_tag_id` is a related contract question that should be settled explicitly, since #671/#672 do not read that field and so will not catch a rename later.
- CLAUDE.md: "Write the current state, not its history" and "Treat stale comments as bugs". Fix: rewrite the PR body against the actual diff and amend the commit message's function name before merge.

## Not reported (below the confidence bar, for the orchestrator's awareness only)

The view resolves the tag before checking permission, so an unpermitted caller can distinguish 404 from 403 for tag ids; `resolve_competency_tag` runs twice per request (view and API); `__all__` at `api.py:33-37` is no longer alphabetical; the migration header's "Generated by Django 5.2.16 on 2026-09-11" is hand-written. None of these is worth a round-trip on its own.

## Positive notes

The tag-row `select_for_update` plus locking reads in `_reject_duplicate_criterion` is a sound answer to MySQL's lack of partial unique indexes, and the ordering test at `test_api.py` for lock-before-duplicate-check is a reasonable stand-in for a concurrency test. The read-merge-write around `tag_object()` correctly avoids dropping a sibling competency's tag, and the rollback test proves ADR 0002's no-empty-groups rule holds on failure. The 209 existing CBE tests pass at pr-head.

Needs research: none

### type-design-analyzer (dispatched 2nd)

# Type design review of openedx-core PR #847 (type-design-analyzer)

## What I reviewed

- Commit range `pr-base..pr-head`: `6162f215fc0a64f0f2400e9cf8feab4543f484c0` (PR #846's head) to `2ca89b767e4706056ea678d7c589f2b8db318106` (PR head, authored 2026-10-09). The PR's own change is `git show pr-head`; code inherited from #846 was read only as context.
- Merge context: `main` at `fd4300e99b69d83328190ca8c131791a28846320`, in particular #716 (`afce3e7`), which added `archived` to `CompetencyCriteriaGroup` and `CompetencyCriterion` and its own `0014_*` migration.
- Context files: `pr_847_body.md`, `issue_665.md`, and ADR 0002 (`docs/openedx_learning/decisions/0002-competency-criteria-model.rst`).
- Verification: I ran a read-only probe (nine pytest cases under my working directory, reusing the cbe `conftest.py` fixtures, against `wt-E/src`; import path confirmed as `wt-E/src/openedx_learning/__init__.py`). I did not modify `wt-E`; `git status --short` there is empty. Findings marked **verified** below come from that probe or from reading the exact code; findings marked **inference** are reasoned from the code and the main-branch diff without executing a merged tree.

The types this PR introduces or changes are: `CompetencyCriteriaGroup` (new `Meta.constraints`), the criterion-creation API surface in `applets/cbe/api.py` (five new public functions that together act as the aggregate for the criteria tree), `CompetencyCriterionSerializer`, and `CompetencyCriterionCreateView`. Nearly all of the domain invariants live in `api.py` rather than on the models, so that is where most of the analysis lands.

---

## Type: CompetencyCriteriaGroup (`src/openedx_learning/applets/cbe/models/criteria.py:40-124`)

### Invariants identified
- I1. At most one root group (`parent IS NULL`) per `tag`. Required by the PR's `get_or_create` at `api.py:133-137`; **not backed by any constraint**.
- I2. At most one course-level group per `(tag, course, parent)`. Backed by the new `UniqueConstraint` at `criteria.py:117-123` and migration `0014_criteria_group_unique_constraints.py`.
- I3. Tree shape: root has `parent IS NULL, course IS NULL`; course-level has `parent = root, course NOT NULL`; leaf has `parent = course-level, course IS NULL`. Encoded only in `api.py` (`create_leaf_group` at `api.py:144-148`, the shape test at `api.py:160`) and in a `Meta` comment at `criteria.py:114-116`.
- I4. `logic_operator` is `AND`, `OR`, or null, with null meaning "single child" per ADR 0002 (`criteria.py:89-98`). Not enforced; acknowledged in the comment at `criteria.py:110-112`.
- I5. (Post-merge, from #716) an `archived` group is "hidden from authoring and new associations".

### Ratings
- **Encapsulation: 4/10.** The model exposes every column as plain writable fields and has no behavior; all shape rules depend on callers going through `api.py`. The PR's own tests bypass that path (`CompetencyCriteriaGroup.objects.create(tag=tag, course=course_run, parent=root)` at `tests/openedx_learning/applets/cbe/test_api.py`) and nothing prevents production code from doing the same.
- **Invariant expression: 3/10.** The one constraint added is named for an invariant it only partly expresses (`one_course_group_per_tag_course`), the comment at `criteria.py:114-116` states "`course` is NULL for roots and leaves" as if it were the type's contract, and I1 and I3 are nowhere visible from the model definition itself.
- **Invariant usefulness: 7/10.** I1 through I3 are the right invariants for the 3-level hierarchy #665 asks for, and I2 does prevent a real race on course-level creation.
- **Invariant enforcement: 3/10.** I2 is enforced by the database. I1 is enforced only by the `select_for_update()` lock inside `create_leaf_group` (`api.py:132`), so any code path that is not that function can create a second root. I3 and I5 are not enforced anywhere.

### Strengths
- The `(tag, course, parent)` constraint is correctly reasoned for MySQL: because leaves and roots carry `course IS NULL`, repeated NULLs never collide, so it is safe without a `condition`. The migration matches the model (`makemigrations --check` was reported clean by the orchestrator and my probe ran the migrations without complaint).
- The `Meta` comment at `criteria.py:110-112` is honest about which invariants are deliberately unconstrained and why.

### Concerns
1. **Leaf `course IS NULL` contradicts ADR 0002 Decision 2, and the new constraint now depends on that contradiction.** ADR 0002 column 4 (`0002-competency-criteria-model.rst:86`) says: "Within a course-scoped subtree, every group carries the same `course_id`, not only its topmost group." The PR creates leaves with `course=None` (`api.py:146`), tests assert it (`test_api.py:217`, `assert leaf.course_id is None`), and the model comment codifies it (`criteria.py:116`). If leaves were later given the ADR's `course_id`, every sibling leaf under one course-level group would share `(tag, course, parent)` and violate the new `UniqueConstraint`, so this constraint makes the ADR rule unimplementable without a schema change. ADR 0002 also defines retrieval scope as "all nodes where `course_id is null`" being the root scope (`0002:112`), so leaves with null `course_id` would be read as root-scope nodes by the #681 read endpoint. **Verified** by reading the ADR, the code, and the test; the consequence for #681 is inference.
2. **Root uniqueness (I1) is a documented-only invariant, and the PR's own test comment asserts a constraint that does not exist.** `tests/openedx_learning/applets/cbe/test_criteria_group.py:52` says "the one-root-per-tag constraint allows only one root group per tag", but no such constraint exists at pr-head; the PR body also still describes two partial constraints that the final commit dropped. My probe created two root groups for one tag with plain `objects.create()` and got no error. **Verified.** The comment is a stale claim about the type's contract and should be corrected or the invariant actually enforced.
3. **Post-merge, `archived` groups are reusable as parents and targetable as leaves.** On `main`, `CompetencyCriteriaGroup.archived` says it "hides the group from authoring and new associations". `create_leaf_group`'s `get_or_create` (`api.py:133-143`) and `resolve_supplied_leaf_group`'s `get_object_or_404` (`api.py:159`) do not filter on `archived`, so after the merge an archived course-level group would be returned by `get_or_create` (the `(tag, course, parent)` key still matches it) and new leaves would be hung under it, and an archived leaf would be accepted as `group_id`. **Inference** from `git diff pr-head main -- criteria.py`; I did not execute a merged tree.
4. **Migration collision at merge.** Both `pr-head`'s `0014_criteria_group_unique_constraints.py:12-14` and `main`'s `0014_add_archived_to_criteria_group_and_criterion.py` depend on `0013_...`, so Django will see two leaf nodes and require a merge migration (or a renumber) before `migrate` or `makemigrations --check` passes. **Verified** by reading both files' `dependencies`.

### Recommended improvements
- Decide the leaf `course_id` question explicitly before merging: either amend ADR 0002 Decision 2 column 4 (and line 112's retrieval-scope rule) to say leaves carry `course_id` null, or give leaves the ADR's `course_id` and replace the `(tag, course, parent)` constraint with one that only covers course-level groups. Because MySQL lacks partial indexes, the second option needs the same technique `CompetencyRuleProfile.scope_code` already uses in this file (`criteria.py:172-180`): a small derived, non-null discriminator column recomputed in `save()` (for example `level` in `{root, course, leaf}`) with `UniqueConstraint(fields=["tag", "level"])` for roots and `UniqueConstraint(fields=["tag", "course", "level"])` for course-level groups. That also gives I1 a database backstop and gives `resolve_supplied_leaf_group` a real leaf test instead of a shape heuristic.
- If a derived column is out of scope for this PR, at minimum fix the stale comment at `test_criteria_group.py:52-53` and make the model docstring or `Meta` comment say plainly that root uniqueness is enforced only by `create_leaf_group`'s row lock.
- Add `archived=False` to the `get_or_create` lookup kwargs (keeping it out of `defaults`) and to the `get_object_or_404` lookup once rebased on `main`, and renumber the migration to `0015` depending on main's `0014`.

---

## Type: criterion-creation API surface (`src/openedx_learning/applets/cbe/api.py:104-297`)

This is the de-facto aggregate for the criteria tree: `resolve_competency_tag`, `create_leaf_group`, `resolve_supplied_leaf_group`, `create_competency_criterion`, `_reject_duplicate_criterion`, and `associate_competency_criterion`. All but the underscore-prefixed one are exported in `__all__` (`api.py:27-36`) and re-exported at the top-level `openedx_learning.api` via a wildcard import, so they are public, stable API under this repo's CLAUDE.md.

### Invariants identified
- A1. A `tag_id` must name a `Tag` on a `CompetencyTaxonomy` (`api.py:111-114`).
- A2. `object_id` must parse as a `UsageKey` whose course key resolves to a `CourseRun` (`api.py:270-278`).
- A3. `group_id` and `logic_operator` are mutually exclusive (`api.py:280-281`).
- A4. A supplied `group_id` must be a leaf of `tag`'s tree whose course-level parent matches the resolved `CourseRun` (`api.py:159-166`).
- A5. No second `CompetencyCriterion` for the same `(tag, object_id)` in the same group, and none at all via the derive path (`api.py:215-239`).
- A6. The `ObjectTag` for `(object_id, taxonomy, tag)` exists and other tags on the object in that taxonomy are preserved (`api.py:190-194`).
- A7. A criterion always has a rule source: either a profile or both overrides (`api.py:196-202`, backed by the model's `CheckConstraint`).
- A8. Groups are never persisted empty (ADR 0002:110), achieved by one `transaction.atomic()` around group creation and criterion creation (`api.py:283-297`).
- A9. No empty-group side effects on rejection; the duplicate check runs before group creation (`api.py:286`).

### Ratings
- **Encapsulation: 4/10.** Making `create_leaf_group` and `create_competency_criterion` public lets any caller persist exactly the states the aggregate is meant to forbid: `create_leaf_group(tag, course_run)` returns a committed, criterion-less leaf (an empty group, which ADR 0002 says backend validation must reject), and `create_competency_criterion(group=any_group, ...)` accepts a root or course-level group, or a group from another tag, with no check. The tests use both bypasses freely, which shows how easy they are to reach.
- **Invariant expression: 5/10.** The docstrings are good and name every invariant. The signatures do not: `logic_operator: str | None` rather than `LogicOperator | None` (`api.py:121`, `247`), so `"and"` or `""` type-check fine and `"" or LogicOperator.OR` at `api.py:148` silently turns an empty string into `OR`; `competency_rule_profile_id` on the public entry point versus `rule_profile_id` on the inner function and serializer (`api.py:248` vs `172`) is three spellings for one concept across one call chain. Two domain functions raise `django.http.Http404` (`api.py:108`, `114`, `156`, `159`); no other `api.py` or `api_impl.py` in this repository imports `Http404` or `get_object_or_404` (verified by grep), so this is the first place the domain layer takes a dependency on the HTTP layer's exception type.
- **Invariant usefulness: 8/10.** A1 through A9 are the right rules for #665 and each one blocks a real bug (orphan groups, cross-course leaves, duplicate criteria, dropped sibling tags). The transaction and lock design is sound.
- **Invariant enforcement: 5/10.** A1 through A6, A8 and A9 are enforced on the `associate_competency_criterion` path (verified by the PR's tests and my probe). A7 is enforced only by the database, and the API boundary does not translate that failure: supplying `rule_profile_id` together with both overrides escapes `CompetencyCriterion.save()` (which calls `full_clean(validate_constraints=False)`, `criteria.py:361`) and reaches the view as an unhandled `IntegrityError: CHECK constraint failed: oel_cbe_criterion_profile_xor_override_check`, a 500. **Verified** (probe D). An archived `CompetencyRuleProfile` supplied as `rule_profile_id` is accepted and the criterion is created on it, although the profile's own help text (`criteria.py:188-194`) says archived profiles are hidden "from new associations". **Verified** (probe C, 201 returned). By contrast, a nonexistent `rule_profile_id` is correctly rejected with 400 by Django's FK validation inside `full_clean` (probe B), and a `rule_type_override` with no payload is rejected with 400 by `validate_rule_payload` (probe A), so the gap is specific to the xor rule and the archived rule.

### Strengths
- Locking the `Tag` row, then doing locking reads for the duplicate check, then creating groups and the criterion inside one `atomic()` block is a clean, correct way to get both race safety and ADR 0002's no-empty-groups rule on MySQL without partial indexes. The rollback test (`test_api.py:518+`) proves A8 for the derive path.
- The read-merge-write around `tag_object()` (`api.py:190-193`) correctly preserves sibling competency tags; `ObjectTag`'s `unique_together` on `(object_id, taxonomy, tag_id)` makes the follow-up `.get()` at `api.py:194` safe from `MultipleObjectsReturned`.
- `associate_competency_criterion` uses keyword-only arguments for the optional fields (`api.py:245`), which is the right shape for a public entry point with seven parameters.

### Concerns
1. **Public API exposes invariant-breaking constructors.** `create_leaf_group` and `create_competency_criterion` in `__all__` (`api.py:29`, `33`) let callers persist empty groups and attach criteria to non-leaf or wrong-tag groups. Once published, narrowing them is a DEPR-process change under this repo's rules, so the time to make them private is now.
2. **The xor invariant (A7) is reachable from HTTP as a 500.** The view maps only `DjangoValidationError` (`views.py:98-99`); the constraint failure is an `IntegrityError`. **Verified** (probe D).
3. **Archived profiles are accepted as `rule_profile_id`.** **Verified** (probe C). This is the same class of gap as concern 3 on the model above (archived groups post-merge) and would be fixed by the same habit: every lookup that performs a "new association" filters `archived=False`.
4. **The leaf test is a shape heuristic, and its error message can be wrong.** `api.py:160` treats any `(parent set, course null)` row as a leaf. A group hung under a leaf has that same shape; it is rejected today, but only because `group.parent.course_id` at `api.py:164` compares the leaf's null course to the run's id and fires the "must belong to the given course" message, which misdescribes the problem. **Verified** (probe I). The ticket's open questions already flag this (`issue_665.md:221`); the derived `level` column recommended above would resolve it.
5. **Default-profile resolution ignores taxonomy scope.** `api.py:197-202` always selects the system default. With a live taxonomy-scoped profile present and all three rule fields omitted, the criterion was assigned the system default. **Verified** (probe H). This fails #665's AC "A taxonomy-scoped rule profile is assigned ahead of the system default" (`issue_665.md:127-133`) and the resolution table in ADR 0002 Decision 4. I flag it here because it is the invariant `create_competency_criterion`'s docstring claims to uphold ("resolves to a concrete profile per Decision 4"); the correctness and requirements reviewers should own the severity call.
6. **`Http404` in the domain API** couples `openedx_learning.api` to Django's HTTP layer and is a first in this codebase (verified by grep). A caller that is not a view (a management command, a Celery task, #666's containment check) gets an HTTP exception for a domain "not found".

### Recommended improvements
- Reduce `__all__` to `associate_competency_criterion` and `resolve_competency_tag` (the view needs the latter for its permission object), and rename the rest with a leading underscore. The tests that call `create_leaf_group` directly can import it by its private name from `openedx_learning.applets.cbe.api`; the test module already imports `cbe_api` that way for monkeypatching.
- In `associate_competency_criterion`, validate the rule-source triple before entering the transaction: raise `ValidationError` when a profile and any override are both supplied, when exactly one override is supplied, or when the profile is archived. Three `if` statements, no new abstraction, and every rule-shape error becomes a 400 keyed to a field.
- Type `logic_operator` as `LogicOperator | None` in both signatures and replace `logic_operator or LogicOperator.OR` with `LogicOperator.OR if logic_operator is None else logic_operator`, so an empty string cannot masquerade as "omitted".
- Rename `competency_rule_profile_id` on the public entry point to `rule_profile_id` to match the serializer field, the inner function, and the model attribute.
- Define a small domain exception (for example `CompetencyTagNotFound(ObjectDoesNotExist)` next to the API) and have the view translate it to 404. If the team prefers to keep `Http404` for parity with the ticket's text, record that choice in the module docstring so the next reader knows it is deliberate.

---

## Type: CompetencyCriterionSerializer (`src/openedx_learning/applets/cbe/rest_api/v1/serializers.py:59-89`)

### Invariants identified
- S1. `object_id` is required on input and never echoed on output (`serializers.py:70`).
- S2. `logic_operator`, when present, is one of `LogicOperator.choices` and is input-only (`serializers.py:77-79`).
- S3. `rule_type_override` and `rule_payload_override` are validated by the model-derived fields (`choices=RuleType`, JSON).
- S4. `id` and `object_tag_id` are output-only (`serializers.py:81`, `89`).

### Ratings
- **Encapsulation: 7/10.** The serializer does not construct the instance; the view hands validated data to the API, so DRF's `ModelSerializer.create()` cannot be reached and the serializer cannot persist anything on its own. That is the right division.
- **Invariant expression: 6/10.** Field-level constraints are expressed in the declarations, and the docstring explains why `object_id`/`logic_operator` are detached from the model. Cross-field rules (A3, the rule-source triple) are not expressed here, even though a `validate()` method is the idiomatic place for them and would turn probe D's 500 into a 400 without touching the API layer.
- **Invariant usefulness: 7/10.** S1 through S4 are exactly what a request/response contract needs.
- **Invariant enforcement: 6/10.** Everything declared is enforced by DRF. The cross-field rules are left to the API, which (see above) enforces A3 but not the rule-source triple.

### Strengths
- Reusing one serializer for request and response, with `write_only` and `read_only` discriminating the two directions, keeps the contract in one place.
- The docstring at `serializers.py:63-67` is a clear explanation of a non-obvious design choice.

### Concerns
1. **Contract names drift from the ticket and the PR body.** The AC in `issue_665.md:32` names the response field `"oel_tagging_objecttag_id"`, and the PR body (`pr_847_body.md:31-34`) says `competency_rule_profile_id`, `competency_criteria_group_id`, and `oel_tagging_objecttag_id` are "the ticket's contracted JSON names, mapped via explicit `source=`". The committed serializer uses `object_tag_id`, `rule_profile_id`, `group_id` with no `source=` (`serializers.py:85-88`). The code is internally consistent and arguably cleaner, but the PR description and the frontend tickets (#671, #672) describe a different contract. This is a contract-expression concern rather than a type-design flaw; the requirements reviewer should decide which names are canonical, and the PR body needs updating either way.
2. **`rule_profile_id` has no archived or existence check at the serializer.** A `PrimaryKeyRelatedField(source="rule_profile", queryset=CompetencyRuleProfile.objects.filter(archived=False), required=False, allow_null=True)` would express and enforce "live profile only" at the boundary with one line and give a field-keyed 400; today the 400 for a bad id comes from `full_clean` and is keyed `rule_profile`, not `rule_profile_id` (verified, probe B).

### Recommended improvements
- Add a `validate(self, attrs)` that rejects `group_id` with `logic_operator`, a profile with any override, and exactly one override; the API can keep its own checks for non-HTTP callers.
- Consider `PrimaryKeyRelatedField` with an `archived=False` queryset for `rule_profile_id`, as above.
- Reconcile the field names with #665's AC and update the PR body to match the committed contract.

---

## Type: CompetencyCriterionCreateView (`src/openedx_learning/applets/cbe/rest_api/v1/views.py:56-100`)

### Invariants identified
- V1. The caller is authenticated (`views.py:77`).
- V2. The caller holds `oel_tagging.can_tag_object` for `(tag.taxonomy, object_id)` (`views.py:85-87`).
- V3. Every `django.core.exceptions.ValidationError` from the API becomes a DRF 400 (`views.py:98-99`).

### Ratings
- **Encapsulation: 7/10.** The view owns only HTTP concerns and delegates construction to the API. Resolving the tag twice (`views.py:84` and again inside `associate_competency_criterion` at `api.py:266`) is a small leak of the API's internals into the view, but it exists because the permission object needs the taxonomy before the API runs.
- **Invariant expression: 7/10.** The class docstring explains the permission design clearly and the `IsAuthenticated` plus manual `has_perm()` split is honest about what each layer checks.
- **Invariant usefulness: 8/10.** V1 through V3 are the right boundary rules.
- **Invariant enforcement: 6/10.** V1 and V2 are enforced. V3 only covers `ValidationError`; `IntegrityError` escapes as a 500 (verified, probe D). The `hasattr(exc, "message_dict")` branch at `views.py:99` is correct for both dict-keyed and list errors.

### Strengths
- Overriding `create()` instead of `perform_create()` is the right call here, since the serializer must not own persistence.
- Using `ObjectTagPermissionItem` and the existing `oel_tagging.can_tag_object` permission reuses the established tagging authorization chain rather than inventing a new one.

### Concerns
1. Only `ValidationError` is translated; see the API section's concern 2 for the `IntegrityError` path. Fixing it at the serializer or API layer is preferable to catching `IntegrityError` here, because a 500 on an integrity failure is the right outcome once the application-level checks exist and something still slips through.

### Recommended improvements
- None specific to the view beyond the upstream fixes already recommended. Optionally, pass the already-resolved `tag` into the API to avoid the second lookup, if `associate_competency_criterion`'s signature is being revisited anyway.

---

## Summary for the maintainers

The transactional core of `associate_competency_criterion` is well designed and the tests for the happy paths and the race scenarios are thorough. The type-design problems are at the edges: the new `UniqueConstraint` bakes in a leaf shape that contradicts ADR 0002 Decision 2 and would make the ADR's rule unimplementable; root uniqueness is asserted in a comment but enforced only by a lock inside one function; two public API functions let callers persist states the aggregate forbids; and the rule-source and archived invariants are not checked at the boundary, so one input shape reaches HTTP clients as a 500 and another silently attaches a criterion to an archived profile. Rebasing on `main` also needs a migration renumber and `archived=False` filters on every group lookup.

Verified by running code: probes A through I as described above, and the migration-dependency collision by reading both files. Inference: the behavior of archived groups after the merge, and the effect of null-course leaves on the #681 read scope.

Needs research: none

### pr-test-analyzer (dispatched 3rd)

# Test coverage review: openedx-core PR #847 (pr-test-analyzer)

## What I reviewed

- **Commit range:** `pr-base..pr-head`, which is `6162f215fc0a64f0f2400e9cf8feab4543f484c0..2ca89b767e4706056ea678d7c589f2b8db318106`. That is the single commit 2ca89b7, "feat: add endpoint for creating competency criteria".
- **Files:** the test diffs in `test_api.py`, `test_views.py` and `test_criteria_group.py`, and the source they cover: `api.py`, `rest_api/v1/views.py`, `serializers.py`, `urls.py`, `models/criteria.py` and migration 0014.
- **Measured against:** the 22 acceptance-criteria scenarios in #665 (ticket body as of 2026-09-15) and against `main` at fd4300e.
- **How I verified (all on SQLite, nothing on MySQL):**
  - In a temporary worktree at pr-head, I ran scratch probe tests and four break-and-restore mutations.
  - On `main` with pr-head cherry-picked onto it (it applies cleanly), I ran the migration check and the CBE suite.
  - Probe files are saved at `/private/tmp/claude-501/-Users-jesperhodge-openedx-openedx-core/776858b1-b3da-4e00-8cac-aea3a17b817b/scratchpad/eval/agent-E/run-2/pr-test-analyzer/probes/test_zz_probe.py` and `/private/tmp/claude-501/-Users-jesperhodge-openedx-openedx-core/776858b1-b3da-4e00-8cac-aea3a17b817b/scratchpad/eval/agent-E/run-2/pr-test-analyzer/probes/test_zz_archived_probe.py`. To re-run them, drop them into `tests/openedx_learning/applets/cbe/`.
- Both temporary worktrees are removed, and `git status --short` in `wt-E` is empty.

## 1. Summary

The group-hierarchy logic and the happy paths are well tested:
- 17 of the 22 acceptance scenarios in #665 have a direct REST-level test.
- The two mutations I made against the rollback and tag-merge behavior were both caught.

The gaps fall in four places:
1. **Rule-source fields.** For `rule_profile_id` and the two override fields, only the case where all three are omitted is tested. Two acceptance scenarios about rule sources have no test, and both fail when tested.
2. **The competency-taxonomy gate.** No test notices if the check in `resolve_competency_tag()` is removed.
3. **Concurrency.** The locking is tested only through mocks, and those mocks still pass when no lock query is ever sent.
4. **The green CI result.** It reflects the stale base. On current `main`, the PR's migration number collides with one already there, and every database test errors while the test database is being created.

**The PR's own descriptions of its tests are inaccurate:**
- The PR body claims "one test per scenario ... (all 20)", but the ticket has 22 scenarios.
- The PR body also describes migration `0004` with two partial constraints, a file named `test_criteria_models.py`, and a count of 147 tests. None of these match the commit.
- The commit message says the tests cover "the concurrent-request race case". That is not accurate: the tests named for concurrency are sequential (see the Test Quality Issues section).

## 2. Critical Gaps (rated 8 to 10)

### 2.1 [9] The PR's tests cannot run on `main` as it is now (verified)

**Mechanism:**
- `main` gained `0014_add_archived_to_criteria_group_and_criterion` from #716 (afce3e7).
- This PR adds `0014_criteria_group_unique_constraints`.
- Both depend on `0013` (`src/openedx_learning/migrations/0014_criteria_group_unique_constraints.py:12`).

**What I ran:** On `main` plus the cherry-picked PR commit:
- `makemigrations --check` fails with "Conflicting migrations detected; multiple leaf nodes in the migration graph".
- pytest errors on the first database test while creating the test database.

CI was green because it ran against the PR's own base, not against `main`. After I renumbered the PR migration locally to `0015`, depending on main's `0014`, all 212 CBE tests passed.

**What to do:** Rebase, renumber the migration, and re-run CI, so the coverage signal describes the code that will actually merge. See 3.2 for the tests that rebase also needs.

### 2.2 [9] Taxonomy-scoped rule profile scenario: no test, and the behavior is wrong (verified)

The scenario is "A taxonomy-scoped rule profile is assigned ahead of the system default".

**Mechanism:** `src/openedx_learning/applets/cbe/api.py:197-202` always resolves the profile using organization, course and competency_taxonomy all null, so it always picks the system default.

**What I ran:** I created a profile scoped to the tag's competency taxonomy and POSTed with no rule fields. The response had `rule_profile_id` 1 (the system default), not 2 (the taxonomy-scoped profile).

**Why it matters:**
- ADR 0002 Decision 4 resolves the profile once, at creation time, and stores it.
- So every criterion created under a taxonomy that has its own profile is stored with the wrong grading rule, and it never corrects itself.
- The developer-approved deviation in the commit message only covers resolving to a concrete profile instead of storing null. It says nothing about skipping taxonomy scope.

**Test to add:** In `test_views.py`, create a taxonomy-scoped profile, POST with no rule fields, and assert that `rule_profile_id` equals the scoped profile's id. This test will fail until the code is fixed.

### 2.3 [8] "Never created without a rule source" scenario: only one input combination is tested, and two return HTTP 500 (verified)

The scenario is "A criterion is never created without a rule source", which the ticket applies to "any combination of supplied fields". Probe results:

| Request body (besides `object_id`) | Status |
| --- | --- |
| `rule_profile_id` plus both override fields | 500: unhandled `IntegrityError` from the `oel_cbe_criterion_profile_xor_override_check` constraint |
| `rule_payload_override` alone | 500, from the same constraint |
| `rule_type_override` alone | 400, keyed `__all__` |
| An invalid override payload | 400, keyed `__all__` |
| Both override fields valid, no profile | 201, with `rule_profile_id` null |

**Mechanism:**
- `CompetencyCriterion.save()` calls `full_clean(validate_constraints=False)`, so only the database enforces the xor constraint.
- The view only converts Django's `ValidationError` into a 400 (`src/openedx_learning/applets/cbe/rest_api/v1/views.py:98-99`). The `IntegrityError` escapes as a 500.

**Coverage gap:** No test exercises supplied rule fields at all. That includes the supported happy path where both override fields are set.

**Test to add:** A parametrized REST test over these combinations that asserts 201 or 400 for each one, and asserts that no criterion is left behind after a rejection.

### 2.4 [8] A tag that is not on a CompetencyTaxonomy: the 404 half of the scenario is untested (verified by mutation)

This is the second half of the scenario "Reject creation for a competency that does not exist".

**What I ran:** I dropped `or not is_competency_taxonomy(tag.taxonomy)` from `src/openedx_learning/applets/cbe/api.py:113`. All 68 tests in `test_api.py` and `test_views.py` still passed. A probe confirms the current code does return 404.

**Why it matters:** Without a test, a refactor could let a tag from any taxonomy, such as a plain content taxonomy, be used to build competency criteria trees, and nothing would fail.

**Test to add:** Create a plain `Taxonomy` with a `Tag`, POST to that tag's endpoint, and assert 404 with no group, criterion or ObjectTag rows created. Add it next to `test_competency_not_found_404s` (`tests/openedx_learning/applets/cbe/test_views.py:580`) and `test_associate_competency_criterion_404s_for_an_unknown_tag_id` (`tests/openedx_learning/applets/cbe/test_api.py:498`).

## 3. Important Improvements (rated 5 to 7)

### 3.1 [7] The concurrency guarantee is tested only by mocks that pass without a lock (verified by mutation)

**What I ran:** I replaced both `Tag.objects.select_for_update().get(pk=tag.pk)` calls (`api.py:132` and `api.py:285`) with the bare `Tag.objects.select_for_update()`. A queryset that is never evaluated sends no SQL, so no row lock is taken. All three lock tests still passed:
- `test_api.py:295` only asserts that `select_for_update` was called.
- `test_api.py:438-465` only records the order of calls.

**Why it matters:**
- The tag-row lock is the only thing that prevents duplicate root groups. The root group has no database backstop by design, because MySQL has no partial indexes (`models/criteria.py:113-124`).
- The duplicate-association check also has no database constraint behind it.
- SQLite treats `select_for_update` as a no-op, so no SQLite test can prove that requests are serialized.

**Test to add:**
- **Preferred:** A MySQL-only test (skipped unless `connection.vendor == "mysql"`; CI already has a MySQL matrix), using `django_db(transaction=True)`. It should run two threads that race `associate_competency_criterion()` for the same tag and course, then assert exactly one root group and one course-level group, and that the second identical derive-path call raises the duplicate error.
- **Cheaper alternative:** On MySQL, use `CaptureQueriesContext` to assert that a `SELECT ... FOR UPDATE` on the tag table is sent before the first group INSERT.

**Production context:**
- Verified: the platform sets `ATOMIC_REQUESTS: True` (`edx-platform/openedx/envs/common.py:405`). A threaded test that goes through the view would therefore cover the outer request transaction as well.
- Inference, not checked on MySQL: I believe Django's MySQL backend defaults to READ COMMITTED, which would make the lock-then-read design sound. The commit message reasons about REPEATABLE READ instead.

### 3.2 [7] After rebasing onto `main`, the PR's code ignores the new `archived` flags, and nothing tests that (verified on `main` plus the PR)

Three behaviors:
- `create_leaf_group()` reuses an archived root group and an archived course-level group. Its two `get_or_create()` calls (`api.py:133` and `api.py:138`) do not filter on `archived`.
- `resolve_supplied_leaf_group()` (`api.py:152-166`) accepts an archived leaf as `group_id`. The probe created a criterion inside the archived leaf.
- An archived criterion still blocks re-associating the same object through the derive path (`_reject_duplicate_criterion()`, from `api.py:223`).

On `main`, the help text for both `archived` fields says that archiving "hides the group from authoring and new associations". The second behavior contradicts that documented contract. The first and third are product decisions. Tests for these behaviors should land with the rebase, at least one that rejects an archived leaf.

### 3.3 [6] A usage key with no course returns 500 instead of the scenario's 400 (verified)

**What I ran:** `object_id` `"lb:Org1:lib1:problem:p1"` parses as a valid usage key. Then `get_course_run(usage_key.course_key)` at `api.py:276` raises `AssertionError` ("lib:Org1:lib1 is not an instance of CourseKey"), which surfaces as a 500.

**Expected:** The scenario "Reject creation with a missing or malformed object_id" calls for a 400.

**Coverage gap:** The only malformed-input tests use `"not-a-usage-key"` (`test_views.py:608` and `test_api.py:505`). The ticket also expects library subsection support later, so library keys are likely to be sent.

### 3.4 [6] The permission tests cover only one of the two cases the scenario names

The scenario lists two ways to lack permission: no studio write access to the course, or no view access to the taxonomy.

**Coverage gap:** `test_no_permission_is_403` (`test_views.py:626`) exercises only the object-id predicate.

**Probe results for the untested cases:**
- A disabled competency taxonomy returns 403.
- An unauthenticated caller gets 401.
- A refused request writes no group or ObjectTag rows.

None of these is tested. The permission check runs at `views.py:84-87`, before any write happens. Asserting "no rows created" on a 403 would catch a refactor that moves the check after the writes.

### 3.5 [6] The tests pin a response field name that differs from the acceptance criteria

**The mismatch:**
- The first scenario lists `oel_tagging_objecttag_id` in the response body.
- The serializer emits `object_tag_id` (`serializers.py:81`), and the tests assert that name (`test_views.py:320` and `test_views.py:508`).
- The rename agreed in the 2026-09-14 comment on #665 covered only `group_id` and `rule_profile_id`.
- The PR body says the opposite of the serializer docstring (`serializers.py:66`) about how fields are mapped with `source=`.

**What to do:** Confirm the intended name with the ticket owner. Then add one assertion on the exact response key set, which also proves that the write-only fields `object_id` and `logic_operator` do not leak into the response.

### 3.6 [5] The rollback test does not check that the ObjectTag is rolled back

**Mechanism:** `test_api.py:518-538` only asserts that no groups remain. But `tag_object()` (`api.py:193`) runs before the failing create. A regression that moved tagging outside the transaction would leave the subsection tagged with no criterion behind it, and this test would still pass.

**Current behavior:** The probe confirms the current code does roll the ObjectTag back.

**Test to add:** `assert not ObjectTag.objects.filter(object_id=object_id, tag=tag).exists()`.

### 3.7 [5] A pre-existing ObjectTag without a criterion is untested

**The case:** An author tags the subsection through the normal tagging UI first. An ObjectTag exists, but no criterion does.

**Current behavior:** The probe got 201, reusing the existing ObjectTag.

**Why it matters:** No test pins this. A regression that treated any existing ObjectTag as a duplicate would block this common path silently.

### 3.8 [5] An archived `rule_profile_id` is accepted, and some error keys are not tested (verified)

- **Archived profile:** Supplying an archived profile's id returns 201. `get_competency_rule_profiles()` hides archived profiles, but a stale client can still send one. The ticket is silent on this, so it needs a product decision, and a test if it should be rejected.
- **Nonexistent profile:** A nonexistent `rule_profile_id` returns a 400 keyed `rule_profile` (the model field name), not the request field `rule_profile_id`. A test asserting the error key would catch this.

### 3.9 [4] A single-tag competency taxonomy returns 500 (verified)

**The case:** `create_competency_taxonomy()` lets a caller set `allow_multiple=False`. On such a taxonomy, adding a second competency to the same subsection makes `tag_object()` raise `ValueError`, which surfaces as a 500.

**What to do:** Add a test, or document that competency taxonomies always allow multiple tags.

## 4. Test Quality Issues

- **Concurrency names that overclaim.** `test_api.py:262` and `test_api.py:280` are named and documented as concurrency tests. Each one pre-creates a row in the same transaction and calls `create_leaf_group()` once. That is the same path as `test_create_leaf_group_reuses_the_root_and_course_level_group_on_a_second_call` (`test_api.py:229`). Rename them to describe what they actually test.
- **A lock-ordering name the test doesn't check.** `test_api.py:295` is named "locks the tag row before creating groups", but it checks neither the ordering nor that the lock query was actually evaluated (see 3.1).
- **A stale comment and an unneeded edit.** The comment at `test_criteria_group.py:52` cites a "one-root-per-tag constraint" that this PR deliberately does not add. I ran the pre-PR version of that test against the PR code and it passes, so the edit is not needed. Revert it, or fix the comment; the project's CLAUDE.md treats stale comments as bugs.
- **A duplicated assertion.** `test_api.py:191` repeats line 190 word for word.
- **A permission override that leaks.** The autouse fixture at `test_views.py:38-44` calls `rules.set_perm()` on the global registry and never restores it. The override leaks into later test modules in the same process. The tagging tests do the same thing, so this matches precedent, but a yield fixture that restores the original predicate is cheap.
- **Unchecked "no rows created" clauses.** Several rejection tests do not check the acceptance criteria's "no rows created" clauses: lines 351, 410 and 468 of `test_views.py`. The risk is low because each of these rejections raises before any write. `test_views.py:514` already shows the pattern to follow.
- **Rejections that don't identify which check fired.** The three supplied-group rejection tests assert only that `group_id` appears in the response. Each fixture breaks exactly one condition, so each test does isolate its own check; I reasoned this through but did not mutate it. The scenarios say the response body "identifies" the specific failure, so asserting the message text would also catch swapped messages.
- **Leaf naming.** The first scenario says the leaf is "named from the course's display name". The code names the course-level group from the course title and leaves the leaf unnamed (`api.py:144-149`), and no test checks the leaf name. Confirm which behavior is intended.

## 5. Positive Observations

- 17 of the 22 scenarios have a direct REST-level test. `create_leaf_group()` and `resolve_supplied_leaf_group()` also have unit tests, including both shapes of non-leaf group (root and course-level).
- Two mutations were caught, confirming real protection:
  - Removing the outer `transaction.atomic()` (`api.py:283`) fails the rollback test.
  - Replacing the tag-merge with `[tag.value]` (`api.py:193`) fails `test_reusing_a_subsection_already_tagged_with_a_different_competency_preserves_both_tags`.
- The tag-preservation test deliberately uses two tags from the same taxonomy, and its docstring explains why that is the only case that exercises `tag_object()`'s replace-the-whole-list behavior.
- `test_duplicate_association_supplying_a_different_existing_leaf_creates_a_second_criterion` (`test_views.py:484`) asserts that both criteria exist with the right group ids and that no groups were created. That would also catch `tag_object()` recreating the ObjectTag and cascading away the first criterion.
- `test_course_level_group_unique_constraint_rejects_a_second_group_for_the_same_tag_and_course` (`test_api.py:308`) proves the database constraint directly, bypassing `get_or_create()`.
- Most tests assert on database state rather than on mocks, and their names describe the behavior under test.

## Verified versus inferred

| Status | Findings |
| --- | --- |
| Verified by running code | 2.1, 2.2, 2.3, 2.4; 3.1 (the mutation), 3.2, 3.3, 3.4, 3.6, 3.7, 3.8, 3.9; the `test_criteria_group.py` revert check |
| Inference | The MySQL isolation-level remark in 3.1 |
| Reasoning, not run | The "each supplied-group test isolates its own check" point in section 4 |

Needs research: none

### silent-failure-hunter (dispatched 4th)

# Silent-failure review of openedx-core PR #847

## What I reviewed

- **Range:** `pr-base..pr-head`, from `6162f215fc0a64f0f2400e9cf8feab4543f484c0` to `2ca89b767e4706056ea678d7c589f2b8db318106`. That is the single commit "feat: add endpoint for creating competency criteria". The code from #846 was used only as context.
- **Files read closely:** `src/openedx_learning/applets/cbe/api.py`, `rest_api/v1/views.py`, `rest_api/v1/serializers.py`, `models/criteria.py`, and the new tests.
- **Code the PR calls, read as context:** `openedx_tagging.api.get_object_tags` and `tag_object`, `openedx_tagging.rules`, `openedx_catalog.api_impl.get_course_run`, and `openedx_tagging/rest_api/v1/exception_handlers.py`.
- **Platform code, read only:** `edx-platform/openedx/core/djangoapps/content_tagging/rules.py`.
- **Requirements and design:** ticket #665 and its comments, #717, and ADR 0002.
- **What landed on main:** I diffed main against pr-head (#716 archived fields, #846).
- **How I verified:** I wrote probe tests in a temporary worktree at pr-head under my working directory, using SQLite test settings. The import path was confirmed under that worktree's `src`. Every finding marked "Verified" below was reproduced by running code. Findings marked "Inference" were not. The worktree has been removed and `wt-E` is clean.

**Project conventions:** The role brief mentions `logError`, `logForDebugging`, `constants/errorIds.ts` and Sentry IDs. None of these exist in this repository. The repository uses stdlib `logging`, and the CBE applet does no logging at all. The closest established precedent is `openedx_tagging/rest_api/v1/exception_handlers.py`. It logs unexpected exceptions with `log.exception` and returns a JSON 500. I judged the PR against that precedent, the project CLAUDE.md, ADR 0002 and ticket #665.

**What is done well:**
- `InvalidKeyError` (api.py:272) and `CourseRun.DoesNotExist` (api.py:277) are caught specifically and chained with `from exc`.
- The 404 for an unknown tag and the 404 for an unknown `group_id` have distinguishable messages.
- The Django-to-DRF `ValidationError` conversion keeps the field dict.
- The rollback-on-failure test exists.

The problems are the failure modes that are not caught, and one write that silently destroys data.

---

## 1. Associating a second competency can silently delete another competency's criterion

- **Location:** `src/openedx_learning/applets/cbe/api.py:190-193` (`create_competency_criterion`)
- **Severity:** CRITICAL
- **Status:** Verified for the disabled-taxonomy case and the learner-status case. The concurrent case was reproduced by simulation only.

**How the write works.** The function reads the object's existing tags with `get_object_tags()`. It unions in the new tag and hands the list to `tag_object()`. But the two calls look at different sets of rows:
- `get_object_tags()` is a display-filtered read. It always excludes ObjectTags whose taxonomy is disabled (`.exclude(taxonomy__enabled=False)`, applied even with `include_deleted=True`). It also excludes deleted tags.
- `tag_object()` replaces the raw row set. Its `_get_current_tags()` reads every `ObjectTag` for `(taxonomy, object_id)` with no filters, then deletes every row that is not in the list it was given.
- `CompetencyCriterion.object_tag` is `on_delete=CASCADE`.

So any row that the read hides but the write sees is deleted, along with every criterion that points at it.

**What I reproduced:**
- **Disabled taxonomy (deterministic).**
  1. Associate competency A with subsection X. This returns 201.
  2. Disable the CompetencyTaxonomy.
  3. Associate competency B, from the same taxonomy, with X, as a superuser. This also returns 201.
  4. Afterward, A's ObjectTag is gone and A's `CompetencyCriterion` is gone. The object's tags are `['Other']` only. A's leaf group is left behind empty, which ADR 0002 forbids.
  5. Nothing is logged and nothing is reported to the caller.
  6. Who can reach this: in openedx-platform, `can_view_object_tag_taxonomy` refuses non-superusers on a disabled taxonomy. However, Django's `has_perm` always returns True for an active superuser. Any direct caller of the public `associate_competency_criterion()` also bypasses the check, because its docstring leaves permission checks to the caller.
- **Learner status exists.** If A's criterion already has a `StudentCompetencyCriterionStatus` row (FK `PROTECT`), the same request raises `ProtectedError`, which becomes an HTML 500. In that case the author cannot associate B with that subsection at all, and the message gives no hint why.
- **Concurrent requests (simulated by patching `get_object_tags` to return the pre-commit result).**
  - Mechanism: Django's MySQL backend defaults to READ COMMITTED (`django/db/backends/mysql/base.py:238`), and neither edx-platform nor tutor overrides it. Requests for different competency tags lock different `Tag` rows, so they are not serialized against each other. Suppose request A commits after B's `get_object_tags()` read but before B's `_get_current_tags()` read. Then B deletes A's freshly committed ObjectTag, and A's criterion cascades away. Both callers received 201.
  - Verification: I verified the deletion mechanism with the simulation. The timing window itself is inference; see "Needs research".
  - Related comment: api.py:222 and the commit message reason about "MySQL REPEATABLE READ". That is not the isolation level these deployments run at.

**Hidden errors:** None of the cases above raises an exception except the learner-status case. The data loss is entirely silent.

**User impact:** A course author's earlier competency association disappears with no error. The author only finds out later when mastery evaluation is wrong. Recovering it requires reading simple-history tables.

**Recommendation:**
- Reject disabled taxonomies up front in `resolve_competency_tag()`. This closes the deterministic case.
- Make the write add-only, so it structurally cannot remove siblings. This closes the concurrent case. The endpoint only ever adds one ObjectTag, so it does not need `tag_object()`'s replace semantics.
- If `tag_object()` must stay, pass it exactly the raw row set it will replace, and serialize on something per-object rather than per-tag.
- Add a test for the disabled-taxonomy case and for the sibling-with-learner-status case.

**Example:**
```python
# resolve_competency_tag()
if tag.taxonomy is None or not is_competency_taxonomy(tag.taxonomy) or not tag.taxonomy.enabled:
    raise Http404("Tag is not on an enabled CompetencyTaxonomy.")

# create_competency_criterion(): add-only; never deletes sibling ObjectTags
object_tag = ObjectTag.objects.filter(object_id=object_id, taxonomy_id=tag.taxonomy_id, tag_id=tag.id).first()
if object_tag is None:
    object_tag = ObjectTag(object_id=object_id, taxonomy=tag.taxonomy, tag=tag)
    object_tag.full_clean()
    object_tag.save()
```
An add-only write would have to re-implement the `allow_multiple` and `OBJECT_MAX_TAGS` checks that `tag_object()` performs. Finding 3 explains why those checks need handling anyway.

---

## 2. Invalid combinations of rule fields return an HTML 500 instead of a 400

- **Location:** `src/openedx_learning/applets/cbe/api.py:196-212`, and `rest_api/v1/serializers.py`, which has no `validate()`
- **Severity:** HIGH
- **Status:** Verified

**Mechanism:**
- Neither the serializer nor `associate_competency_criterion()` checks the profile/override exclusivity rule.
- `CompetencyCriterion.save()` calls `full_clean(validate_constraints=False)`. That means the model's well-written `violation_error_message` for `oel_cbe_criterion_profile_xor_override_check` never runs.
- The invalid row therefore reaches the database, which raises `IntegrityError`. Only `DjangoValidationError` is caught at views.py:98, so the `IntegrityError` propagates.

**Reproduced cases:**
- POST with `rule_payload_override` but no `rule_type_override` returns 500 (`IntegrityError: CHECK constraint failed: oel_cbe_criterion_profile_xor_override_check`).
- POST with `rule_profile_id` together with both override fields returns the same 500.
- In both cases the response is `Content-Type: text/html`, Django's "Server Error (500)" page, sent to a JSON API client.

**Hidden errors:** Any `IntegrityError` from the criterion insert. On MySQL 8.0.16 and later the CHECK is also enforced (error 3819), so I expect the same 500 there. That part is inference.

**User impact:** The frontend in #672 gets an unparseable HTML 500 for a client mistake that has a clear fix. Ticket #665's acceptance criterion "A criterion is never created without a rule source" holds only because the database refuses the row, not because the API rejects the request cleanly.

**Recommendation:** Validate the combination before opening the transaction, keyed by the request field names. Add tests for both combinations.

**Example:**
```python
has_type, has_payload = rule_type_override is not None, rule_payload_override is not None
if has_type != has_payload:
    missing = "rule_payload_override" if has_type else "rule_type_override"
    raise ValidationError({missing: _("rule_type_override and rule_payload_override must be supplied together.")})
if competency_rule_profile_id is not None and has_type:
    raise ValidationError({"rule_profile_id": _("Supply rule_profile_id or the override fields, not both.")})
```

---

## 3. Expected tagging failures become 500s

- **Location:** `src/openedx_learning/applets/cbe/api.py:193` (`tag_object`) and `api.py:194` (`ObjectTag.objects.get`)
- **Severity:** HIGH
- **Status:** Verified

**Mechanism:** `tag_object()` documents that it raises `ValueError` and `Tag.DoesNotExist`. The PR catches neither, and the view only converts `DjangoValidationError`. The tagging app's own REST view converts these same two exceptions to 400s at `src/openedx_tagging/rest_api/v1/views.py:591-595`. That is the established precedent this call skipped.

**Reproduced cases:**
- **Taxonomy with `allow_multiple=False`.** The first competency on a subsection returns 201. A second competency from the same taxonomy on the same subsection raises `ValueError: Taxonomy (Nursing) only allows one tag per object.`, which becomes an HTML 500.
- **Competency taxonomy with `allow_free_text=True`.** `create_competency_taxonomy()` accepts this parameter. `tag_object()` takes its free-text branch and writes `_value` with no `tag_id`. The lookup at api.py:194 then raises `ObjectTag.DoesNotExist`, which becomes an HTML 500.

**Hidden errors (inference, from reading the code):**
- `ValueError("Cannot add more than {limit} tags…")` from `_check_new_tag_count()`.
- `Tag.DoesNotExist` from `taxonomy.tag_for_value()`.
- `ObjectTag.DoesNotExist` from the re-fetch on any path where `tag_object()` did not write a `tag_id`-linked row.

**User impact:** An author gets a generic 500 for a rule the system knows how to explain, for example "this taxonomy allows one tag per object".

**Recommendation:** Convert the documented `tag_object()` errors into a field-keyed `ValidationError`, as the tagging view does. Either reject free-text competency taxonomies up front, or stop re-fetching by `tag_id`. Add tests for both cases.

**Example:**
```python
try:
    tag_object(object_id, tag.taxonomy, existing_values)
except (ValueError, Tag.DoesNotExist) as exc:
    raise ValidationError({"object_id": str(exc)}) from exc
```

---

## 4. The `except CourseRun.DoesNotExist` clause misses library usage keys, so they return a 500

- **Location:** `src/openedx_learning/applets/cbe/api.py:275-278`
- **Severity:** HIGH
- **Status:** Verified

**Mechanism:**
- `UsageKey.from_string("lb:Org1:lib1:problem:p1")` succeeds and returns a `LibraryUsageLocatorV2`.
- Its `.course_key` is a `LibraryLocatorV2`, which is not a `CourseKey`.
- `get_course_run()` passes that key to `CourseKeyField.get_prep_value()`. That method asserts the key type (`opaque_keys/edx/django/models.py:138`) and raises `AssertionError: lib:Org1:lib1 is not an instance of <class 'opaque_keys.edx.keys.CourseKey'>`.
- The narrow except clause does not catch it, so the response is an HTML 500.
- For comparison, a legacy `lib-block-v1:` key correctly returns a 400.
- Under `python -O` the assert is stripped, and the same input would presumably fall through to `DoesNotExist` and a 400. The behavior therefore also depends on interpreter flags. That last part is inference.

**Who can reach this:** The platform's `can_change_object_tag_objectid` explicitly admits v2 library keys for users with library tagging permission.

**User impact:** Ticket #665 says `object_id` "must resolve to a CourseRun (400 otherwise)". A library author instead gets a 500 with no explanation.

**Recommendation:** Check the key's context type explicitly before the lookup. Add a test for an `lb:` key.

**Example:**
```python
if not isinstance(usage_key.context_key, CourseKey):
    raise ValidationError({"object_id": _("object_id must be a usage key inside a course run.")})
```

---

## 5. The permission check runs before `object_id` is validated, so in the platform a malformed key returns 403 instead of 400

- **Location:** `src/openedx_learning/applets/cbe/rest_api/v1/views.py:84-87`, with the test at `tests/openedx_learning/applets/cbe/test_views.py:39` and `:608`
- **Severity:** HIGH
- **Status:** Verified with a rule that mimics the platform. Behavior in the real platform is inference.

**Mechanism:**
- The view calls `has_perm("oel_tagging.can_tag_object", ...)` with the raw `object_id` before `associate_competency_criterion()` parses it.
- openedx-platform's `can_change_object_tag_objectid` catches `ValueError`/`AssertionError` from key parsing and returns `False` (`edx-platform/openedx/core/djangoapps/content_tagging/rules.py:228-232`).
- So `"not-a-usage-key"` gets `403 "You do not have permission to perform this action."`.
- I reproduced this with a predicate that parses the key the way the platform's does: 403.

**Why the tests pass anyway:** The test suite's autouse fixture `_allow_object_level_tagging` (test_views.py:39) grants permission for every string. That is why `test_malformed_object_id_is_400` (test_views.py:608) passes here, but it could not pass against the platform.

**A second likely effect (inference):** A well-formed key for a course with no CourseRun would also get a 403 for ordinary authors, because `has_studio_write_access` fails on a nonexistent course. It would not get #665's 400 "course unresolvable".

**Note:** #665's Logic section orders the steps as parse, resolve CourseRun, then check permission.

**User impact:** A typo in `object_id` looks like a permissions problem. Authors and support staff will chase role assignments instead of fixing the key.

**Recommendation:** Parse the usage key and resolve the CourseRun before the permission check. One way is a serializer `validate_object_id()`. Another is a small API helper the view calls first. Make the test's permission predicate reject unparseable keys, as the platform's does.

---

## 6. A taxonomy-scoped rule profile is silently ignored in favor of the system default

- **Location:** `src/openedx_learning/applets/cbe/api.py:196-202`
- **Severity:** HIGH
- **Status:** Verified

**Mechanism:** When no rule fields are supplied, the code always selects the system default. It never considers a profile scoped to the competency's taxonomy.

**Reproduction:** I created a live taxonomy-scoped profile (id 2) and posted with no rule fields. The response was 201 with `rule_profile_id: 1`, the system default. No error was raised and nothing was logged.

**Conflict with the ticket:** #665 (as edited 2026-09-15) has the acceptance criterion "A taxonomy-scoped rule profile is assigned ahead of the system default". The commit message lists its approved deviations, and this is not one of them. The PR body says every acceptance-criteria scenario is tested, but there is no test for this one.

**Context:** ADR 0002 line 237 has an MVP note saying only the system default exists in this phase. However, the model already allows taxonomy-scoped rows, and ADR 0002 line 184 says the assignment is never re-resolved at evaluation time. A wrong pick is therefore permanent until some later write event reassigns it.

**User impact:** Learners are evaluated against the wrong threshold, with nothing to show that a fallback happened.

**Recommendation:** Either implement the resolution precedence, or get the acceptance criterion formally dropped and list it among the commit's deviations. In either case, add a test that pins the chosen behavior.

---

## 7. An archived rule profile is accepted for a new association

- **Location:** `src/openedx_learning/applets/cbe/api.py:206-212` (`rule_profile_id` is passed through unchecked), and `serializers.py:80`
- **Severity:** HIGH
- **Status:** Verified

**Mechanism:** Nothing checks the supplied profile's `archived` flag. ADR 0002 line 139 and the model's `help_text` both say archived profiles are "hidden from authoring and new associations".

**Reproduction:** POST with the id of an archived profile returned 201 and stored the criterion against it.

**User impact:** Suppose a profile is archived while an author's page is open. The author's next association silently binds to the retired rule.

**Recommendation:** Reject archived and nonexistent profiles together, keyed `rule_profile_id`. The same check also fixes the key mismatch described in finding 10. Add a test.

**Example:**
```python
if competency_rule_profile_id is not None and not CompetencyRuleProfile.objects.filter(
    pk=competency_rule_profile_id, archived=False,
).exists():
    raise ValidationError({"rule_profile_id": _("rule_profile_id must reference a live CompetencyRuleProfile.")})
```

---

## 8. A missing or archived system-default profile becomes an anonymous 500

- **Location:** `src/openedx_learning/applets/cbe/api.py:197-202`
- **Severity:** MEDIUM
- **Status:** Verified

**Mechanism:** If migration 0005's seed row is missing or archived, `.get()` raises `CompetencyRuleProfile.DoesNotExist`. The client gets an HTML 500, and the server log has only a generic traceback, with no statement that the seed row is the problem. `MultipleObjectsReturned` cannot happen here, because `oel_cbe_ruleprofile_scope_code_uniq` prevents a second live default.

**Recommendation:** A 500 is the right status for a server misconfiguration. It should still say what is wrong.

**Example:**
```python
except CompetencyRuleProfile.DoesNotExist as exc:
    log.error("No live system-default CompetencyRuleProfile (migration 0005's seed row is missing or archived).")
    raise ImproperlyConfigured("No live system-default CompetencyRuleProfile.") from exc
```

---

## 9. The root `get_or_create()` relies on a uniqueness rule that nothing enforces

- **Location:** `src/openedx_learning/applets/cbe/api.py:133-137`, with the comment at `tests/openedx_learning/applets/cbe/test_criteria_group.py:52`
- **Severity:** MEDIUM
- **Status:** Verified

**Mechanism:**
- The new constraint on `(tag, course, parent)` cannot stop two roots for the same tag, because NULLs never collide in a unique index.
- If two roots exist, `get_or_create(tag=tag, parent=None)` raises `MultipleObjectsReturned`, and every later derive-path request for that competency returns an HTML 500.
- Two roots can come from any writer that does not take the Tag row lock: direct ORM code, future endpoints, or data fixes.

**Reproduction:** With two roots present, the derive-path POST returned a 500.

**Stale comment:** The PR's own test comment at test_criteria_group.py:52 says "the one-root-per-tag constraint allows only one root group per tag". No such constraint exists. #717 also assumes one ("#665's own partial UniqueConstraints (one root per competency…)").

**Recommendation:** Correct the stale comment. Either document that every root writer must hold the Tag row lock, or turn `MultipleObjectsReturned` into a logged error that names the tag id, so the corrupt state can be diagnosed. Do not silently pick one of the roots.

---

## 10. Error keys do not match the request's field names

- **Location:** `src/openedx_learning/applets/cbe/rest_api/v1/views.py:98-99`
- **Severity:** MEDIUM
- **Status:** Verified

**Mechanism:** The errors raised by `CompetencyCriterion.full_clean()` are passed through with model-level keys rather than the request's field names.

**Reproduced cases:**
- An invalid `rule_payload_override` returns `{"__all__": ["A 'Grade' rule_payload has the wrong keys: …"]}`. The key `__all__` is neither the request field nor DRF's `non_field_errors` convention.
- A nonexistent `rule_profile_id` returns `{"rule_profile": ["competency rule profile instance with id 999999 is not a valid choice."]}`. The client sent `rule_profile_id`.

**User impact:** The frontend cannot attach these errors to the input that caused them.

**Recommendation:** Validate before `create()`, re-keyed to the request names. Findings 2 and 7 cover the profile cases. For the payload, call `validate_rule_payload()` up front and re-raise keyed `rule_payload_override`.

---

## 11. Unexpected errors render as Django's HTML 500 page, and nothing in the CBE path logs

- **Location:** `src/openedx_learning/applets/cbe/rest_api/v1/views.py:56-100` (the whole view)
- **Severity:** MEDIUM
- **Status:** Verified that the content type is `text/html`

**Mechanism:** The view uses DRF's default handler. That handler returns `None` for any non-APIException, so every uncaught case in findings 1 through 9 reaches the JSON client as an HTML page. In the platform, the server side still gets Django's `django.request` error log and Sentry. The CBE code itself logs nothing about the operation that failed: which tag, which object_id, which group.

**Precedent:** `openedx_tagging/rest_api/v1/exception_handlers.py` (`TaggingExceptionHandlerMixin`) logs with `log.exception` and returns a JSON 500.

**Recommendation:** Fix the expected failures as 400s first, in findings 2 through 4. Then consider adopting a JSON 500 handler like the tagging one for this view. That is a team decision, because the existing `CompetencyRuleProfileView` does not use one either.

---

## Outside my specialty, for the other reviewers

- **Migration conflict on merge (confirmed by reading `git ls-tree main`, not run):** main already has `0014_add_archived_to_criteria_group_and_criterion.py`, and this PR adds `0014_criteria_group_unique_constraints.py`. Both depend on `0013`. Django will refuse to migrate after merge, reporting conflicting leaf nodes. This failure is loud, not silent.
- **Archived groups and criteria after merge:** Once #716's `archived` fields are present, the create path does not check them. I did not file this as a finding because ticket #717 explicitly owns that work and is blocked by #665.

## Needs research

- **Concurrent-request data loss on real MySQL:** Run two concurrent POSTs for *different* competency tags from the same taxonomy on the same `object_id`, using a MySQL-backed setup such as `mysql_test_settings.py` or a devstack. The goal is to measure how often request B deletes request A's just-committed ObjectTag and criterion under READ COMMITTED (finding 1). I could only simulate the interleaving here, with SQLite and a mock. A real MySQL run would show how likely it is in practice, which would settle whether finding 1 should stay CRITICAL for the concurrent trigger on its own merits. The disabled-taxonomy trigger is deterministic regardless.

### comment-analyzer (dispatched 5th)

## Comment analysis: openedx-core PR #847 (comment-analyzer)

**What I reviewed.** I reviewed the commit range `pr-base..pr-head`, that is `6162f215fc0a64f0f2400e9cf8feab4543f484c0..2ca89b767e4706056ea678d7c589f2b8db318106`, a single commit. That covers every comment, docstring, and help/violation string the commit adds to the 9 changed files, and the commit message too, since git keeps it permanently. I checked the claims against the code at pr-head, ADR-0002, ADR-0006 (public API conventions), tickets #665, #666 and #613, main at `fd4300e` (which now carries #846 and #716), and the openedx-platform and Tutor settings. Every claim marked "verified" below was confirmed by running code: scratch tests or mypy in a temporary worktree at pr-head, since removed. Every claim marked "inference" was established by reading source only.

### Summary

Most of the new comments explain why the code does something, which is the right habit. However, nine comments or docstrings state something the code or the repository contradicts. Two of them are flatly false: the view docstring's claim about how every existing `DjangoObjectPermissions` class behaves, and a test comment about a "one-root-per-tag constraint" that does not exist. Several others look like leftovers from an earlier draft of this PR that used partial unique constraints, a function named `resolve_or_create_leaf_group()`, and `source=` field mappings. The commit message and the PR body still describe that earlier draft.

### Critical Issues

**1. False claim about the existing permission classes**
- Location: `src/openedx_learning/applets/cbe/rest_api/v1/views.py:66-72`. The commit message repeats the same claim.
- Issue: The docstring says every existing `DjangoObjectPermissions` class "only ever contributes the authentication gate, since the `rules` predicate behind it returns True whenever called with no object". That is false.
  - At pr-head, `openedx_learning.view_competencyruleprofile` (used by `CompetencyRuleProfilePermissions` in this same module) is `is_taxonomy_admin(user)`.
  - `oel_tagging.add_taxonomy`, `change_taxonomy` and `delete_taxonomy` (used by `TaxonomyObjectPermissions`) are `is_taxonomy_admin(user)` regardless of the object.
  - Verified: `rules.has_perm(...)` with no object returns False for a plain user on all three of those permissions. The pr-head test `test_only_a_competency_administrator_may_read_the_collection` also expects 403 for a plain user.
  - On main, the CBE predicate now returns True for a listing, but the tagging classes still refuse with no object, so the claim is false on main too.
- Suggestion: State the real reason directly: "Authorization depends on the object_id in the request body, which DRF's class-level `has_permission()` cannot see, so it is checked with `has_perm('oel_tagging.can_tag_object', ...)` in `create()`." Fix the commit message the same way.

**2. The test comment cites a constraint that does not exist**
- Location: `tests/openedx_learning/applets/cbe/test_criteria_group.py:52-53`.
- Issue: The comment says "the one-root-per-tag constraint allows only one root group per tag". No such constraint exists, and the commit message itself says the root group "cannot be backed by a constraint". Verified twice:
  - I ran the pre-PR body of this test against the pr-head schema, and all 3 parametrizations pass.
  - A probe created two roots for one tag without error.
- Suggestion: Revert lines 52-57 to the original test body. The comment and the `other_tag` workaround are leftovers from the partial-constraint draft.

**3. The concurrency comments assume REPEATABLE READ, which Django does not use by default**
- Location: `src/openedx_learning/applets/cbe/api.py:222`. The commit message makes the same claim. The comments at `api.py:126` and `api.py:130-131` and the test docstring at `tests/openedx_learning/applets/cbe/test_api.py:268-269` are in tension with it.
- Issue: The comment says the locking reads are what make a concurrent duplicate visible "under MySQL REPEATABLE READ". That premise does not match the deployment:
  - Django 5.2's MySQL backend sets READ COMMITTED unless `OPTIONS["isolation_level"]` overrides it (verified in `django/db/backends/mysql/base.py:238`).
  - Neither openedx-platform's `openedx/envs/common.py` nor Tutor's templates set an override.
  - Both of them set `ATOMIC_REQUESTS: True`.
- Consequences (inference, not run on MySQL):
  - Under READ COMMITTED, any read issued after the tag lock already sees the previous lock holder's commit, so the locking reads do not do what the comment says they do.
  - Under REPEATABLE READ, the reads in the view before the lock would fix the snapshot, because `ATOMIC_REQUESTS` puts the whole request in one transaction. Then the plain reads in `create_leaf_group()`'s `get_or_create()` would miss a root committed by the earlier lock holder.
  - So the claims at lines 126 and 130-131 ("race-safe", "serialized on the tag row") hold only under READ COMMITTED.
  - Either way, the two comments describe different threat models.
- Suggestion: State the actual assumption once: "Django's MySQL backend runs READ COMMITTED, which openedx-platform does not override, so reads after the tag lock see rows committed by the previous holder." Then remove the REPEATABLE READ rationale from the code and from the commit message. If REPEATABLE READ support is intended, the comment has to say that every read after the lock must be a locking read, and the `get_or_create()` calls are not.

**4. The view docstring credits the API with a check the view performs**
- Location: `src/openedx_learning/applets/cbe/rest_api/v1/views.py:60-64`.
- Issue: The docstring lists "permission check" among the steps that `associate_competency_criterion` "already owns end-to-end". It does not own that step:
  - The view performs the check itself at `views.py:85-87`.
  - The function's own docstring at `api.py:255-256` says "the caller is expected to have already checked `oel_tagging.can_tag_object`".
- Verified by reading the code.
- Suggestion: Drop "permission check" from that list, and say that the view checks permission before delegating.

**5. The merge guarantee in the `create_competency_criterion()` docstring fails for a disabled taxonomy**
- Location: `src/openedx_learning/applets/cbe/api.py:179-181`.
- Issue: The docstring promises the read-merge-write avoids "silently dropping a sibling competency's tag". That holds only when `get_object_tags()` returns every row that `tag_object()` will replace. `get_object_tags()` excludes rows on a disabled taxonomy.
- Verified: on a disabled competency taxonomy, a second `associate_competency_criterion()` call for a different competency deleted the sibling `ObjectTag`. Through `CASCADE`, it also deleted the first `CompetencyCriterion`.
- Reachability:
  - Through the REST view, only a superuser reaches this, because `can_tag_object` refuses disabled taxonomies for everyone else.
  - Through the public Python API, any caller reaches it.
- Suggestion: Either guard against this case, or state the limitation in the docstring. The behavior itself is a correctness concern for the other reviewers.

**6. Wrong reason, and an unsupporting citation, for the missing `(parent, ordering)` constraint**
- Location: `src/openedx_learning/applets/cbe/models/criteria.py:110-112`.
- Issue: The comment says neither omitted constraint "has a single-row state to check at save time" because "a child group cannot be saved until its parent's primary key exists".
  - That reasoning fits a child-count rule.
  - It does not fit a `UniqueConstraint` on `(parent, ordering)`. The database checks that constraint across rows when the child is inserted, and the parent's primary key already exists by then.
  - ADR-0002 Decision 2, which the comment cites, says nothing about either omission.
  - The real reason is in the class docstring at `criteria.py:46-50` and in #613's acceptance criterion: `ordering` covers only child groups, not leaf criteria.
- Suggestion: Delete lines 110-112, which this PR's feature does not need. If a pointer is wanted, refer to the class docstring.

**7. "One per criterion" is inaccurate**
- Location: `src/openedx_learning/applets/cbe/api.py:127`.
- Issue: The docstring says "a tag/course pair can hold more than one leaf, one per criterion". A leaf can hold several criteria through an explicit `group_id`. Verified: two `associate_competency_criterion(..., group_id=leaf.id)` calls put 2 criteria in one leaf.
- Suggestion: Give the real reason a new leaf is always created: "Always creates a new leaf, so a `logic_operator` supplied for this request never changes a leaf that other criteria already use" (this matches #665's Description).

**8. The constraint's name and violation message overstate what it enforces**
- Location: `src/openedx_learning/applets/cbe/models/criteria.py:119-122`, repeated in the migration.
- Issue: The name `...one_course_group_per_tag_course` and the message "at most one course-level CompetencyCriteriaGroup per course" describe uniqueness per (tag, course). The constraint actually enforces uniqueness per (tag, course, parent). Verified: two course-level groups for the same tag and course, under two different roots, save successfully.
- Suggestion: Say "per course under a given parent", as #665's own Technical Details phrase it. Alternatively, say that it relies on the application keeping one root per tag.

**9. The "Raises" contract in the `associate_competency_criterion()` docstring is incomplete**
- Location: `src/openedx_learning/applets/cbe/api.py:263-264`.
- Issue: The docstring promises a `ValidationError` "on rejected input". Some rejected input raises `IntegrityError` instead (from `oel_cbe_criterion_profile_xor_override_check`), which the view does not catch and would return as a 500. Verified:
  - `competency_rule_profile_id` plus both overrides raises `IntegrityError`.
  - `rule_payload_override` without a `rule_type_override` raises `IntegrityError`.
- Suggestion: Either validate the rule-field combinations up front, or document the `IntegrityError` cases. The 500 response is a correctness issue for the other reviewers.

### Improvement Opportunities

- **The docstring cites ADR-0002 Decision 4 for a hard-coded default.**
  - Location: `api.py:183-185`.
  - Current state: The docstring presents "resolves to the seeded system-default" as what ADR-0002 Decision 4 prescribes. Decision 4 actually prescribes a precedence table (course, then organization or taxonomy, then system default), and only its MVP note narrows that to the system default. #665 has an acceptance criterion, "A taxonomy-scoped rule profile is assigned ahead of the system default", which is neither implemented nor tested. The commit message's deviations list does not mention this.
  - Suggestion: Say "Always assigns the system default (ADR-0002 Decision 4 MVP note); taxonomy-scoped profiles are not consulted yet." Then either implement the acceptance criterion or list it as a deviation.

- **The leaf shape conflicts with ADR-0002 without saying so.**
  - Location: `criteria.py:114-116` and `api.py:152-158`.
  - Current state: The comment states "`course` is NULL for roots and leaves" as fact. ADR-0002 Decision 2, amended on 2026-09-04 for #676, says "Within a course-scoped subtree, every group carries the same `course_id`". The code follows #665's text, which contradicts the ADR. This comment is load-bearing: if leaves ever carry `course_id` as the ADR requires, this constraint allows only one leaf per course-level group, and `resolve_supplied_leaf_group()` rejects a correctly formed leaf as "not a leaf".
  - Suggestion: Say in both places that this leaf convention comes from #665 and departs from ADR-0002 Decision 2. Define "leaf" in the `resolve_supplied_leaf_group()` docstring as "parent set, course null". Raise the conflict between the ADR and the ticket with the maintainers.

- **The placeholder for #666 cannot meet #666's own contract.**
  - Location: `api.py:204`.
  - Current state: The comment marks where #666's check goes. That spot runs after `tag_object()` has already written to the database. `create_competency_criterion()` is a public function that opens no transaction, so a rejection at this spot leaves the `ObjectTag` behind unless the caller wrapped the call in a transaction. #666 also plans to call `_validate_containment(group, parsed_key)` with the already-parsed `UsageKey` and "no signature change to `create_competency_criterion()`". At this spot, only the raw `object_id` string is available.
  - Suggestion: Add the `_validate_containment` stub that both tickets name, and call it where the parsed key exists. Otherwise, state both constraints in the comment.

- **The public API surface and its preconditions are undocumented.**
  - Location: `api.py:28-38`, `api.py:176-189`, `api.py:255`.
  - Current state: Under ADR-0006, `__all__` lists the functions a module is willing to support publicly. `__all__` here exports `create_leaf_group`, `resolve_supplied_leaf_group`, `create_competency_criterion` and `resolve_competency_tag`, yet `associate_competency_criterion` is called "the public entry point". The `create_competency_criterion()` docstring leaves out several preconditions: it does no duplicate check, takes no lock, does no leaf validation, and requires a tag on a competency taxonomy. Its assert comment says only "already guaranteed set by the caller". None of these functions carries the "UNSTABLE:" notice that `get_competency_rule_profiles()` uses, although #666 and #675 will change them.
  - Suggestion: Either keep the helpers out of `__all__`, or document their preconditions and mark them UNSTABLE, consistent with the neighboring functions.

- **The view docstring describes implementation, not the endpoint contract.**
  - Location: `views.py:57-73`.
  - Current state: The docstring explains design rationale but never states the endpoint's contract. By comparison, `CompetencyRuleProfileView` names `GET api/cbe/v1/rule_profiles/`. CLAUDE.md asks public class docstrings to describe the contract.
  - Suggestion: Add `POST api/cbe/v1/competencies/<tag_id>/criteria/`, the body fields, and the 201, 400, 403 and 404 responses.

- **A comment sits in the branch it does not describe.**
  - Location: `api.py:235-236`.
  - Current state: The comment inside the `elif` describes the case that does not raise (a different group), but it sits in the branch that raises for the same group.
  - Suggestion: Move it above the `elif`, or reword it: "Only the same explicit group is a duplicate."

- **"Already associated" is ambiguous.**
  - Location: `api.py:217`.
  - Current state: The phrase can be read as "an ObjectTag exists". An object tagged in Studio with no criterion is not rejected.
  - Suggestion: Write "already has a CompetencyCriterion for `tag`".

- **"Its course" is imprecise.**
  - Location: `api.py:157`.
  - Current state: The check compares the parent's course, not the leaf's.
  - Suggestion: Write "its course-level parent's course".

- **Archived rows after rebasing onto main.**
  - Location: `api.py:124-127`, `api.py:154`, `api.py:215-217`.
  - Current state: Main's #716 adds `archived` fields to groups and criteria, and their help text says these rows are "hidden from authoring and new associations". After the rebase, "validated as a usable leaf" and "Gets or creates the root and course-level groups" will overclaim, because archived rows are neither rejected nor skipped. The duplicate check also counts archived criteria.
  - Suggestion: Once the PR is rebased, say how each function treats archived rows.

- **A test docstring references a document outside the repository.**
  - Location: `tests/openedx_learning/applets/cbe/test_views.py:561`.
  - Current state: "per the plan's explicit note" refers to a planning document that is not in the repository.
  - Suggestion: Remove the phrase. The rest of that sentence explains itself.

- **The commit message and the PR body are stale.** Both will outlive the code review, so they should match the code.
  - Commit message:
    - It names `resolve_or_create_leaf_group()`, but the function is `create_leaf_group()`. `__all__`'s ordering at `api.py:35` still reflects the old name.
    - It says "single public entry point", which contradicts `__all__`.
    - It says "every acceptance-criteria scenario in #665" is tested. #665 has 22 scenarios; the taxonomy-scoped-profile scenario and the "tag exists but is not in a Competency Taxonomy" 404 scenario have no tests.
    - It says the "concurrent-request race case" is tested. The tests only assert the order of the lock calls; their own docstring at `test_api.py:444` admits this.
    - Its deviations list omits the response field `object_tag_id`, where the acceptance criterion says `oel_tagging_objecttag_id`.
  - PR body: It still describes migration 0004 with two partial constraints, a `source=` mapping to the ticket's field names, `test_criteria_models.py`, and "147 passed".

- **The migration name and number.**
  - Location: `src/openedx_learning/migrations/0014_criteria_group_unique_constraints.py:1-3`.
  - Current state: The file name says "constraints" (plural) for a single constraint, and 0014 collides with main's `0014_add_archived_to_criteria_group_and_criterion`.
  - Suggestion: When renumbering, make the name singular so it matches the docstring.

- **Writing style.** `views.py:63` and `serializers.py:75` use "--" as an em dash, which the CLAUDE.md writing-style rule asks to avoid. This is low priority.

### Recommended Removals

- **`api.py:267-268`, the assert and its comment ("re-asserted since that doesn't cross function boundaries for mypy").** Nothing in `associate_competency_criterion()` reads `taxonomy_id`, and each callee asserts it again itself. Verified: with both lines removed, mypy still passes on the file, and mypy does type `taxonomy_id` as `int | None` there (I confirmed this with a probe assignment).
- **`test_criteria_group.py:52-57`, the comment and the `other_tag` workaround.** They exist only because of the nonexistent constraint described in Critical Issue 2. Verified by running the original test body.
- **`criteria.py:110-112`.** This rationale is wrong and not needed by the PR's feature (see Critical Issue 6).

### Positive Findings

- `api.py:130-131` says plainly why a lock is used instead of a constraint: MySQL has no partial indexes.
- `api.py:179-181` gives a clear reason for the read-merge-write that a maintainer would otherwise "simplify" away. Only the scope of its guarantee needs tightening (Critical Issue 5).
- `serializers.py:72-76` explains why `logic_operator` is rejected alongside an explicit `group_id`.
- `criteria.py:114-116` explains why the constraint has no `condition` and why repeated NULLs make the unconditional version equivalent. This is a good comment once it acknowledges the ADR.
- `test_api.py:521-527` ties the rollback test to ADR-0002's rule against persisting empty groups.
- `test_views.py:28-34` explains the permission override and names its precedent accurately.

Needs research: one item. I need to know whether any production Open edX deployment overrides Django's MySQL `isolation_level` (for example, to REPEATABLE READ). The openedx-platform and Tutor checkouts I could read do not set it. This decides which of the two conflicting concurrency comments in Critical Issue 3 should survive. I verified none of those concurrency claims against a real MySQL server.

## Process log

**Sub-agents dispatched.** All five were sent in one message with `run_in_background: false` and ran concurrently. All were `general-purpose`. None dispatched further. Each delivered its report through SubagentHandback, and I pasted the reports above verbatim, with only the harness's two-space indent removed.

| # | Agent definition carried | Model | Effort | Purpose | Agent id | Tokens | Tool uses | Duration |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `agents/code-reviewer.md` | fable | xhigh | CLAUDE.md compliance, bugs, general quality | a4491113fdc5d4b9e | 192,406 | 37 | 723 s |
| 2 | `agents/type-design-analyzer.md` | fable | xhigh | Invariants and encapsulation of the new and changed types | aa3f0b903179ade03 | 152,615 | 25 | 670 s |
| 3 | `agents/pr-test-analyzer.md` | opus | not passed | Behavioral test coverage and test quality | ad234fca41e091f2e | 171,012 | 45 | 638 s |
| 4 | `agents/silent-failure-hunter.md` | opus | not passed | Error handling, silent failures, fallbacks | a7129c9874b22bafe | 197,350 | 49 | 679 s |
| 5 | `agents/comment-analyzer.md` | opus | not passed | Accuracy of comments, docstrings and commit text | a9c1ad3dd1eee4c11 | 220,466 | 56 | 769 s |

The five sub-agents used 933,849 tokens in total.

**How the prompts were built.**
- Each prompt is the agent file's body, everything after the frontmatter, copied verbatim. I checked each body byte for byte with `cmp` against the source file.
- After the body comes a shared task section: the review target and range, the main context, the context directory with a description of each file, the guideline files, read limits, environment rules, a working directory per agent, and the rule against further dispatch.
- The `model:` lines in the frontmatter were overridden per the brief's table.
- The assembled prompts are saved at `/private/tmp/claude-501/-Users-jesperhodge-openedx-openedx-core/776858b1-b3da-4e00-8cac-aea3a17b817b/scratchpad/eval/agent-E/run-2/briefs/<agent>.prompt.md`.

**How the command's steps were adapted to the frozen snapshot.**
- Step 1 and step 3: I ran `git status --short` (it was clean) and `git diff --name-only pr-base pr-head` instead of looking at the working tree. There was no `gh pr view`; the PR body came from `context/pr_847_body.md`.
- Step 4: with the aspect `all`, all five agents ran. I confirmed each one applies as follows:
  - **code-reviewer:** always applicable.
  - **pr-test-analyzer:** three test files changed.
  - **comment-analyzer:** grep counted 41 added comment or docstring lines under `src`, plus new model help and violation strings.
  - **silent-failure-hunter:** the diff adds `try`/`except` blocks for `InvalidKeyError` and `CourseRun.DoesNotExist`, a Django-to-DRF `ValidationError` conversion, and `Http404`/`PermissionDenied` raises.
  - **type-design-analyzer:** the diff adds the classes `CompetencyCriterionSerializer`, `CompetencyCriterionCreateView` and a `Migration`, and new `Meta.constraints` on `CompetencyCriteriaGroup`.
- Step 5: I used the parallel approach, as the aspect `parallel` asks.
- `code-simplifier` was not run. It edits code, and this review is read-only. Its agent file was also not among the files provided.

**Commands and tests I ran myself.** Everything ran in `wt-E` with the venv, with `PYTHONPATH` set to `wt-E/src`. Nothing was modified.
- I read the seven skill files with `cat`.
- I ran `git status`, `git rev-parse`, `git diff --name-only/--stat pr-base pr-head`, `git log -1 pr-head`, `git log --oneline pr-head..main`, `git merge-base`, `git ls-tree` of the migrations on main and on pr-head, and `git diff --stat b6a58bf88 main`.
- I grepped the diff for error-handling lines, class definitions and comment lines (for step 4).
- I read the database settings in `test_settings.py`, which showed an in-memory SQLite database, so concurrent pytest runs were safe.
- I confirmed the import path once: `python -c "import openedx_learning; print(openedx_learning.__file__)"` printed a path under `wt-E/src`.
- Cross-checks after the agents returned:
  - read `api.py:12-20` at pr-head and main's `.importlinter`
  - grepped `issue_717.md`, `issue_665.md` and `issue_665_comments.md`
  - read ADR 0002 lines 61, 84-88, 110-113, 145 and 237
  - grepped edx-platform envs and Tutor templates for `isolation_level` (no matches) and `ATOMIC_REQUESTS` (true in both)
  - ran `which mysql mysqld docker`
- Final checks:
  - `pytest tests/openedx_learning/applets/cbe/ --no-cov -p no:cacheprovider -q`: 209 passed.
  - `python manage.py makemigrations --check --dry-run`: no changes detected.
  - `git status --short`: empty.
  - No `agent-E` worktrees remain.

**How the cross-checks changed the summary.**
- **Archived groups and criteria:** this is #717's scope, so I moved it from Important to Suggestions. #717 owns it explicitly, accepts as permanent for the MVP that an archived course-level group blocks new criteria for that course, and assumes #665's constraints stand.
- **Sibling-deletion finding:** silent-failure-hunter rated it CRITICAL. I placed it under Important, for the reachability reasons given in that item.
- **Taxonomy-scoped profile:** I noted that #665's acceptance criterion and ADR 0002's MVP note conflict.
- **Leaf `course_id`:** I confirmed that the conflict is between the ADR and the ticket, not something the PR introduced.
- **Import-linter break:** I confirmed it by reading main's configuration.

**"Needs research" items.**
- **silent-failure-hunter, measuring concurrent data loss on real MySQL:** I did not fulfill this. No MySQL server is available. Docker is installed, but starting MySQL would mean pulling an image and writing outside the allowed paths. The item stays open, and the concurrent trigger stays unmeasured.
- **comment-analyzer, whether any deployment overrides the MySQL `isolation_level`:** I answered this as far as possible offline. The readable edx-platform envs and Tutor templates set no override, and both set `ATOMIC_REQUESTS`. Real production deployments cannot be checked from here. I did not continue the agent with SendMessage, because the answer matches the assumption it already stated and would not change its findings. That departs from CLAUDE.md's continue-the-agent loop.

**Which checkout and range the findings refer to.**
- All `file:line` anchors are in `wt-E` at pr-head `2ca89b767`, for the range `pr-base` (`6162f21`) to `pr-head`.
- Findings about the merge refer to main `fd4300e99`. The agents tested them in temporary worktrees: pr-head plus main's migration file or `.importlinter`, and main with pr-head cherry-picked onto it.
- Everything ran on SQLite. Nothing ran on MySQL.

**Other notes.**
- `agent-E/` already held `BRIEF_E.md` and `killed-run-1/` before this run. I did not read or modify either, and this run's files are in `agent-E/run-2/`.
- `git worktree list` in `wt-E` shows worktrees registered by another session that share the same repository: `.../bc59e103-.../scratchpad/eval/repo` and `wt-A` through `wt-D`. I did not read or touch them.
- The Agent tool's results contained only a pointer to each SubagentHandback message, not the report text. The reports arrived as agent messages.

**Wall-clock time.** About 22 minutes: from 09:40:35 EDT (reading the skill) to about 10:02 EDT (final checks). The agents ran concurrently from about 09:43 to about 09:56.

All steps of the skill were performed as written, with these exceptions: the adaptations above that the brief asked for, the omission of `code-simplifier`, and the two "Needs research" items described above.