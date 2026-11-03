# [Follow-up BE] Remove the ENABLE_COMPETENCY_MASTERY_TRACKING setting

GitHub: pending (openedx/openedx-core, sub-issue of #725; the code change is in openedx/openedx-platform)
Cached: 2026-11-02

## User Story

As a platform operator, I want a learner's competency criterion status recorded on every subsection grade write without a setting to switch on, in order to have mastery tracked as soon as criteria are attached to content, with no configuration step to miss.

## Description

openedx/openedx-platform#39179 gated the competency status write on the subsection grade path behind the Django setting `ENABLE_COMPETENCY_MASTERY_TRACKING`, default `False`, but upon further inspection, this isn't necessary per the PR comment discussion. Essentially, with no competency criteria in a deployment, `record_graded_object_statuses` in `openedx-core` runs one indexed query that returns no rows and queues no roll-up task, so a deployment that does not use competencies pays one SELECT per subsection grade write and nothing else, so there is no reason to have an extra flag to prohibit this call for non-CBE instances.

Remove the setting and run the competency call unconditionally. The change is in `openedx-platform`.

## Context
- #701's acceptance scenario "An operator can decline competency tracking entirely" no longer holds once this ticket is done.

## Acceptance Criteria

- [ ] `ENABLE_COMPETENCY_MASTERY_TRACKING` and its toggle annotation block are gone from `lms/envs/common.py`.
- [ ] `_record_competency_status` in `lms/djangoapps/grades/subsection_grade.py` calls `record_graded_object_statuses` without consulting any setting, and its docstring no longer describes a tracking-off case.
- [ ] No test in `lms/djangoapps/grades` overrides the setting, the tests that asserted setting-off behavior are removed, and the rest of the grades test suite passes.

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done.

**Approach**

1. Delete the `ENABLE_COMPETENCY_MASTERY_TRACKING` assignment and the `.. toggle_name:` annotation block above it from `lms/envs/common.py`.
2. In `lms/djangoapps/grades/subsection_grade.py`, remove the `if not settings.ENABLE_COMPETENCY_MASTERY_TRACKING: return []` guard at the top of `_record_competency_status` and update its docstring. Leave the `transaction.atomic()` blocks, the `on_commit` enqueue, and the event emission as they are; the setting never gated them.
3. Remove `test_setting_off_saves_grades_without_calling_core` and `test_setting_off_does_not_enqueue` from `lms/djangoapps/grades/tests/test_subsection_grade.py`, and remove every `@override_settings(ENABLE_COMPETENCY_MASTERY_TRACKING=True)` decorator from `test_subsection_grade.py`, `tests/test_api.py`, and `rest_api/v1/tests/test_gradebook_views.py`. The tests under those decorators keep running, now against the unconditional path.

**Files to create and modify**

| File | Change |
| --- | --- |
| lms/envs/common.py | modified: remove the setting and its annotation block |
| lms/djangoapps/grades/subsection_grade.py | modified: drop the setting guard in `_record_competency_status` |
| lms/djangoapps/grades/tests/test_subsection_grade.py | modified: remove the two setting-off tests and the override decorators |
| lms/djangoapps/grades/tests/test_api.py | modified: remove the override decorator |
| lms/djangoapps/grades/rest_api/v1/tests/test_gradebook_views.py | modified: remove the override decorator |

</details>
