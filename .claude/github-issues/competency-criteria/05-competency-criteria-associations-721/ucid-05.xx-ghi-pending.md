# [Follow-up - BE] Reject a competency taxonomy import that re-arranges tags into a dominance conflict

GitHub: pending
Cached: 2026-10-23

## User Story
As a course author, I do not want my re-import of a taxonomy to ruin my competency criteria that I have configured for my course by breaking the competency dominance rule in order to avoid having confusing competency criteria or competency criteria that I would not be able to manage directly in Studio.

## Description

*Competency Dominance Rule Definition*: No ancestor/descendant pair of competency tags may both hold live criteria in the same course.

Currently, each taxonomy has the taxonomy_type field. In the event that the taxonomy_type is Competency, then when re-importing this taxonomy, it needs to fail if someone tried to re-arrange the tags in a way that violates #666, and the import should report back the error in a useful way to the end user. In order to continue following the rule that the tagging code is not allowed to know about the CBE code, we will implement this using the same pattern described in ADR 0013 which suggests using openedx-platform as a proxy to handle the relationship between tagging and CBE. Therefore, openedx-platform would call off to the tagging code to get the original import validation answer and then it would check if the taxonomy_type is Competency and if it is, then call off to the CBE code to do an additional validation for the #666 check. Add the CBE validations to the set from the plain tagging validations and report all of them back for the end user.

## Context
- The primary BE implementation of this for the GUI: #666
- #797 is the frontend counterpart to #666

## Notes for drafting

Everything below was settled in the 2026-10-23 session with the architect (mgwozdz) and is background for the BA's draft pass. It is not posted.

**Origin.** Jesper's 2026-10-21 comment on #683 reported that a competency with criteria can gain a child through a taxonomy edit or re-import, after which #666 blocks the child's associations in that course and the author can't see why. His frontend-only suggestion was declined. The frontend half (non-leaf competencies not selectable) was a bug introduced in frontend-app-authoring PR #3275, already commented on by the architect; no new frontend ticket is needed. This ticket is the backend half.

**Product rule (architect's decision).** A competency at any level of the taxonomy can carry criteria. The only limit is #666's dominance rule: no ancestor/descendant pair may both hold live criteria in the same course. Leaf-only is not a rule anywhere. Archived criteria and archived associations never block anything.

**Which hierarchy changes can violate #666.** Adding a new child tag (interactive add sub-tag, or import create-with-parent) can never violate it, because a new tag has no criteria. Only reparenting an existing tag can, which import does through its `UpdateParentTag` action (`src/openedx_tagging/import_export/actions.py`). A move changes the ancestry of the moved tag and its whole subtree, and gives the new ancestors new descendants, so the check must cover every tag whose ancestor or descendant set changes, with all moves in the file applied together, not each move alone. The Django admin's Tag form also edits `parent` directly and bypasses all of this; the architect accepts that gap.

**Chosen approach (architect's proposal, confirmed).** openedx-platform is the proxy, the same pattern ADR 0013 (`docs/openedx_tagging/decisions/0013-competency-taxonomy-detection.rst`) uses for `taxonomy_type`: `openedx_tagging` must never know CBE exists (`.importlinter` comment). Shape:
- `openedx_tagging.import_export.api.import_tags()` gains one generic, optional parameter: a list of extra validator callables run during the plan phase, after tagging's own action validation, whose errors are appended to the plan's error list. Same shape as Django's `validators=[...]` on fields. No CBE reference in tagging.
- openedx-platform's `TaxonomyOrgView` (`openedx/core/djangoapps/content_tagging/rest_api/v1/views.py`, already overrides `create_import`) passes the CBE validator when `openedx_learning.api.is_competency_taxonomy()` is true, on the plan endpoint (`tags/import/plan`) and the real import endpoints.
- A new CBE public function in `openedx_learning` takes the `TagImportPlan` and returns #666-style errors: for each affected tag, compute its proposed ancestors and descendants from the plan, then reuse `get_courses_with_relative_criteria(tag_ids, course)` from PR #875 (#666) to find conflicting courses. `get_ancestor_tags` / `get_descendant_tags` from #875 don't reuse directly because they read the stored `lineage` of each `Tag` row, and the check must run against the tree the file would produce.
- Error message should name the moved tag, the conflicting tag, and the course key, matching #666's existing message.

**Why the seam is inside `import_tags()`.** Preview and real import are separate HTTP calls, but the real import plans and executes inside one `import_tags()` call with nothing between plan and execute. A platform-side check before the call would need a plan-only pass first, re-parse for the real run, and would never show the CBE errors in the real run's task log. Validators run during the plan phase cover both calls in one place, and Studio's import wizard (`src/taxonomy/import-tags/ImportTagsWizard`) already displays the plan's error list and task log, so no frontend change is expected (inferred: wizard call order verified, error rendering not traced in detail).

**Related tickets.** #666 and PR #875 (dominance check at criterion creation, the code to reuse). #796 / #797 (proactive gray-out of ineligible content; the frontend counterpart to #666). #814 (Epic 10: import refusals for values and external ids belonging to archived tags, the other import-time guardrail in `actions.py`, and precedent for import validation errors). #780 (Epic 10: tag deletes archive instead of hard-delete when locked; covers import's `DeleteTag` in replace mode, out of scope here). ADR 0013.

**Repos.** openedx-core (tagging seam plus CBE validator) and openedx-platform (view wiring). One ticket with PRs in both repos is the team's normal practice as long as the ticket size stays appropriate; the openedx-core PR must land and be released before the platform PR can depend on it.

**Decisions from the pre-handoff check**
- Archived criteria and associations never block a reparent.
- Archived child tags: moot, since leaf-ness no longer matters.
- Django admin gap: accepted.
- Pre-existing violating data (e.g. Jesper's test env): not this ticket's problem.
- Epic placement: Epic 5 (#721), where #666 lives; Epic 10 (#723) was the alternative.
