# [BE] Copy competency criteria and content tags to a new course run

GitHub: https://github.com/openedx/openedx-core/issues/694 (#694, OPEN)
Cached: 2026-09-21

## User Story

As a course author, I want the content tags and competency mastery rules attached to my course's content to be recreated on each new run of that course, in order to track learner mastery from the first day of the new run without re-tagging content and rebuilding every rule by hand.

## Acceptance Criteria

Every outcome below is observable by a course author reading the new run. A failure is additionally observable by an operator, and by the author through Studio's existing rerun-failure notification.

```
# What carries over

Scenario: Content tags carry over to the new run
  Given content in the source run is tagged with a competency
  When a course author creates a new run of that course and the run finishes being created
  Then the corresponding content in the new run carries the same tags the author sees on the
    source run's content, both on the Course Outline page and on the Competency Management page
  And the source run's tags are unchanged

Scenario: Tags from a regular, non-competency taxonomy also carry over
  Given content in the source run is tagged with a tag from a taxonomy that is not competency-enabled
  When a course author creates a new run of that course and the run finishes being created
  Then the corresponding content in the new run carries the same tag
  And the source run's tag is unchanged

Scenario: The Competency Management page shows a new course-level group matching the source run
  Given content in the source run is tagged with a competency and governed by a criteria group of
    mastery rules
  When a course author creates a new run of that course and the run finishes being created
  Then opening the Competency Management page for that competency shows a new course-level group
    for the new run
  And that group contains the same corresponding bottom-tier criteria boxes, rule boxes, and
    subsection chips as the source run's group

Scenario: The author can modify the new run without affecting the source run
  Given content in the source run is tagged with a competency and governed by mastery rules
  When a course author creates a new run of that course and the run finishes being created
  Then the author can remove a tag, edit or archive a mastery rule, or edit or archive a criteria
    group on the new run via the Competency Management page
  And doing so leaves the source run's tags, rules, and groups unchanged

Scenario: The author can modify the source run without affecting the new run
  Given content in the source run is tagged with a competency and governed by mastery rules
  When a course author creates a new run of that course and the run finishes being created
  Then the author can remove a tag, edit or archive a mastery rule, or edit or archive a criteria
    group on the source run via the Competency Management page
  And doing so leaves the new run's tags, rules, and groups unchanged

Scenario: A mastery rule using the system default rule profile carries over to the new run
  Given the source run has a mastery rule using the system default rule profile, requiring a grade
    threshold on one of its graded subsections
  When a course author creates a new run of that course and the run finishes being created
  Then the new run has an equivalent mastery rule using the same system default rule profile and
    the same grade threshold
  And that rule targets the new run's own copy of the subsection
  And the source run's rule still targets the source run's subsection

Scenario: A mastery rule with a custom override carries over to the new run
  Given the source run has a mastery rule with a custom override of the rule type or threshold,
    requiring a grade threshold on one of its graded subsections
  When a course author creates a new run of that course and the run finishes being created
  Then the new run has an equivalent mastery rule with the same custom override
  And that rule targets the new run's own copy of the subsection
  And the source run's rule still targets the source run's subsection

Scenario: The new run's rules are an alternative way to demonstrate the competency, not an
    additional requirement
  Given the source run has a criteria group of mastery rules for a competency
  When a course author creates a new run of that course and the run finishes being created
  Then the competency shows the source run's criteria group and the new run's criteria group as
    alternative ways to demonstrate it
  And demonstrating the competency does not require satisfying both runs' rules

Scenario: Competencies within a taxonomy are shared, not duplicated
  Given the source run's content is tagged with a competency from a competency taxonomy
  When a course author creates a new run of that course and the run finishes being created
  Then the competency taxonomy still lists that competency exactly once, with no duplicate entry
    created for the new run
  And renaming that competency afterwards changes the label seen on both runs

Scenario: The competency taxonomy itself is not duplicated
  Given the source run's content is tagged with a competency from a competency taxonomy
  When a course author creates a new run of that course and the run finishes being created
  Then the platform's list of taxonomies still shows that taxonomy exactly once, with no duplicate
    taxonomy created for the new run
  And both the source run's and the new run's tags reference the same taxonomy

# What does not carry over

Scenario: Archived rules are not carried to the new run
  Given the source run has a mastery rule that was archived after learners had already been
    evaluated against it
  When a course author creates a new run of that course and the run finishes being created
  Then the new run has no equivalent of the archived rule
  And the new run's criteria group contains only the rules still in force on the source run
  And the source run still shows the archived rule and its learner history unchanged

Scenario: An archived criteria group and everything under it are not carried to the new run
  Given the source run has a criteria group that was archived
  And rules and child groups are still recorded under that archived group
  When a course author creates a new run of that course and the run finishes being created
  Then the new run has no equivalent of the archived group
  And the new run has no equivalent of any rule or child group recorded under the archived group

Scenario: A group left with a single rule in force is still carried over as a group
  Given a criteria group in the source run has two mastery rules
  And one of those two rules has been archived
  When a course author creates a new run of that course and the run finishes being created
  Then the new run has an equivalent criteria group
  And that group combines its children the same way the source run's group does
  And it contains only the rule still in force

# Empty, failing, and permission cases

Scenario: A new run of a course with no tags and no rules succeeds with nothing to carry over
  Given the source run has no tagged content and no mastery rules
  When a course author creates a new run of that course and the run finishes being created
  Then the new run is created successfully
  And the new run reports no content tags and no mastery rules, without reporting an error

Scenario: A failure part way through leaves no partly built rules on the new run
  Given the source run has content tags and mastery rules
  And carrying the mastery rules over fails part way through
  When a course author creates a new run of that course
  Then the new run has no partly built criteria groups and no partly built mastery rules
  And no content tags are left copied onto the new run
  And the new run's rerun is marked failed the same way the platform already marks any other
    rerun failure
  And the author sees Studio's existing rerun-failed notification, and an operator can see the
    underlying error

Scenario: A retried copy never duplicates rows from a failed attempt
  Given a prior attempt to carry the tags and mastery rules over to a new run failed part way
    through
  When a course author creates a new run of that course again and the copy runs again
  Then the resulting new run ends up with exactly one full copy of the source run's content tags
    and in-force mastery rules
  And no row is duplicated from the earlier failed attempt

Scenario: Carrying tags and rules over needs no permission beyond creating the run
  Given a course author is permitted to create a new run of the course
  And that author holds no separate permission to author competency criteria
  When the author creates a new run of that course and the run finishes being created
  Then the source run's content tags and in-force mastery rules are carried over in full
  And none are dropped for lack of permission
```

## Description

Creating a new run of a course in Studio clones the course content only. Neither the content tags nor the competency mastery rules attached to that content are recreated on the new run.

A course that has been running for a while also holds retired rules. Once any learner has been evaluated against a mastery rule, removing that rule retires it instead of deleting it, so the learner's history stays traceable to the rule that produced it. Retirement is a decision about the rule, not about one run, and a new run has no learner history for a retired rule to explain. The new run therefore carries exactly the rules the author currently sees in force on the source run, and nothing that is retired or that sits beneath something retired.

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the source of truth. The User Story and Acceptance Criteria define what must be true when the work is done; what follows exists to save the implementer some thinking.

### In short

**Where the copy is triggered from.** openedx-platform's rerun task clones the course structure with `modulestore().clone_course(...)` and then emits `COURSE_RERUN_COMPLETED`. That event's payload carries only the destination course key, so the source course key has to be recovered from the `CourseRerunState` row, which records both the destination `course_key` and the `source_course_key` and is written before the event fires. Two receivers already listen for the event, one maintaining upstream links and one reindexing for search, and neither touches tags or competency criteria. A rerun also never fires the per-block duplication event that the existing tag-duplication path keys on, so nothing copies anything today. This ticket adds a third receiver alongside the existing two, in openedx-platform's own signal handlers rather than in the tagging app, and that receiver hands the work to a Celery task rather than doing it inline. Putting the orchestration in openedx-platform keeps the tagging app unaware of competencies: the copy composes two lower-level capabilities, tag copying and criteria copying, and the composition belongs in the caller that already depends on both.

**The new run's catalog record.** A recreated criteria group points at the destination course's catalog record. Every other course-creation path produces one immediately, because `create_course` auto-publishes the course's root block by default, which is what creates the catalog record, but a rerun's `clone_course` call opts out of that auto-publish (`skip_auto_publish=True`) so the author gets a review window before the new run goes live. A rerun is therefore the one course-creation path that reaches this event with no catalog record yet. The copy task ensures the record exists before it recreates any rules, creating it from the destination course's own title if it is missing, inside the same transaction as the rest of the copy so a failure rolls that creation back too. This makes the copy task a second creator of catalog records alongside the publish path, which is harmless: `_listen_for_course_publish` (the publish path's own receiver) already does the identical get-or-create before syncing title and language, so a real publish later simply finds the record this task created.

**How old content ids map to new ones.** A split-mongo rerun points a new course locator at the same structure versions as the source, so each XBlock's local name is identical between the two runs; only the course key differs. A tag's `object_id` is the block's full key, course key included, so it is still a new, distinct id on the new run even though the local name matches. The old-to-new id map is therefore a computed transform, `old_key.map_into_course(destination_course_key)`, applied to each object id found under the source course. Only a plain `dict[str, str]` of old object id to new object id crosses from `openedx-platform` into `openedx-core`; no model instance and no modulestore concept does.

**Tags are copied first, then the rules are pointed at the results.** Neither available tag-copy function returns an old-to-new tag-association map, and a mastery rule holds a hard foreign key to exactly one association row. Rather than change either tag-copy function, which are both used elsewhere, the task copies the tags first, and the criteria step then finds each recreated rule's destination association by its natural key of object id, taxonomy, and tag. Because a rerun is always same-instance, the source and destination share the identical taxonomy and tag rows, so nothing resolves taxonomy identity and no taxonomy or tag row is ever duplicated here.

**What the criteria copy recreates, and where it attaches.** For MVP, a competency's criteria tree has exactly three levels: a shared root, a course-level group per course, and that course-level group's bottom-tier groups, which hold the mastery rules themselves. Nothing nests deeper. For each live course-level group of the source course, the copy recreates that group and its live bottom-tier children on the destination course, carrying names, ordering, logic operators, and the competency tag across unchanged. The recreated course-level group keeps the same parent (the shared root) as its source group rather than getting a new parent, which is how the two runs' course-level groups end up combined under the root's `OR`. Each recreated bottom-tier group points at the newly created copy of its course-level parent, not at the source's row. Groups with no course scope are not recreated at all. Each recreated rule keeps whatever rule-profile assignment or per-rule override its source had, so the new run evaluates exactly the way the source run does.

**Archived rules do not travel.** A long-running source course accumulates archived groups and archived rules, because removing either is archive-only once learner status references it. The copy recreates what the source course currently evaluates, not its history, so archived rows are excluded: a course-level group is skipped along with its bottom-tier children if it was archived directly, and a bottom-tier group or an individual rule is skipped on its own if that's what was archived. Every row the copy creates is live.

**The whole per-course copy is one transaction.** The catalog record check, the tag copy, and the criteria copy run inside a single `transaction.atomic()`, so a failure anywhere leaves the new run with neither copied tags nor partial rules, and never a group tree missing some of its leaves. The underlying course structure clone has already committed by the time the event fires and is unaffected either way. Because this runs in a Celery task, the transaction is off the request path.

**Reporting a failure.** On failure, the task calls the same `CourseRerunState.objects.failed(destination_course_key)` that `rerun_course` itself already calls when the course clone fails, rather than introducing a separate, copy-specific failure state. This is a deliberate simplification: a tag/rule-copy failure becomes indistinguishable, to the author, from any other rerun failure, surfaced through Studio's existing generic rerun-failed notification and its existing dismiss flow. That flow's normal behavior for a failed rerun applies here too, including removing the destination course along with it, even though the course clone itself succeeded; this ticket accepts that consequence rather than adding a distinct partial-failure state.

### Implementation specifics

- **Receiver.** Add a new `@receiver(COURSE_RERUN_COMPLETED)` to `cms/djangoapps/contentstore/signals/handlers.py`, guarding the payload with the same `isinstance(course_data, CourseData)` check the existing receivers there use. It reads `CourseRerunState.objects.get(course_key=course_data.course_key).source_course_key` and calls `.delay()` on the new task. Do not add this event to the existing `@receiver([COURSE_IMPORT_COMPLETED, COURSE_RERUN_COMPLETED])`: that receiver serves a different concern with a different task, and the import case belongs to \#696, which is cross-instance and needs different behavior.  
- **Task.** Add `copy_course_tags_and_criteria(source_course_key_str, destination_course_key_str)` to `cms/djangoapps/contentstore/tasks.py`, alongside the tag-touching tasks already there. `openedx/core/djangoapps/content_tagging/` has no Celery surface at all, which is why the task does not go there.  
- **Building the object id map.** `content_tagging.api.get_all_object_tags(content_key, prefetch_orgs=False)` returns a tuple whose first element is keyed by object id and covers the course itself plus every descendant usage key in one query, matching on a `block-v1:` prefix derived from the course key alongside the course key itself. Take its keys as the source object ids and map each through `UsageKey.map_into_course(destination_course_key)`, using the destination course key itself for the course-level entry.  
- **Tag-copy primitive.** Use `content_tagging.api.copy_object_tags(source_content_key, dest_content_key)`, one call per mapped pair. It enumerates the source with `get_all_object_tags` and writes the destination with `tag_object` per taxonomy, so the rows it creates take the `is_copied` default of `False` and are ordinary, author-editable tags. This call is taxonomy-agnostic: it copies every tag on the source object regardless of which taxonomy it belongs to, so a tag from a regular, non-competency taxonomy is carried over the same way a competency tag is.  
- **Why the tag-copy primitive must not be swapped.** Do not use `openedx_tagging.api.copy_tags`, which `content_tagging` re-exports under the telling name `copy_tags_as_read_only`. It sets `is_copied=True`, and `ObjectTagCopiedMinimalSerializer` in `content_tagging/rest_api/v1/serializers.py` overrides `can_delete_object_tag` to return `False` for such rows, so the authoring API would refuse to let an author delete the tags on their own new run. A new run's tags are the author's own content, not a synced mirror of an upstream, which is the case the read-only variant exists for. Consequently `make_copied_tags_editable` (the `unmark_copied_tags` alias, called only on upstream unlink) is not needed here, because the flag is never set.  
- **One `copy_object_tags` behavior to know.** It swallows `InvalidOrgException` and silently skips a taxonomy unavailable to the destination organization. The organization never changes on a rerun, so this is a no-op here, but it means \#695 and \#696 cannot reuse the function as-is without first deciding what a silent skip should mean across instances.  
- **Destination catalog record.** Before the criteria step and inside the same transaction, call `openedx_catalog.api.get_course_run(destination_course_key)` and, on `CourseRun.DoesNotExist`, call `openedx_catalog.api.create_course_run_for_modulestore_course_with(destination_course_key, title=...)`, taking the title from `modulestore().get_course(destination_course_key).display_name` and optionally passing the course's language as `language_short`. That function logs a warning rather than raising if the row already exists, checks no permissions, and emits no course lifecycle events. Do not read the title from `CourseOverview`, which is publish-triggered too and is the same trap one layer over.  
- **Evidence that no catalog record exists when the event fires.** `CourseRun` rows are otherwise created only by the publish-triggered `_listen_for_course_publish` receiver in `openedx/core/djangoapps/content/course_overviews/signals.py`. A rerun does not publish: `clone_course` calls `create_course(..., skip_auto_publish=True, ...)`, which gates out the `_auto_publish_no_children` call, and the only other pre-event modulestore write updates `vertical` blocks, which are not in `DIRECT_ONLY_CATEGORIES`.  
- **Source catalog record.** A missing **source** record means the source course can hold no course-scoped rules at all, so the criteria step returns a zero-count result while the tag step still commits. Only a missing destination record is created; a missing source record is not.  
- **New public function.** `copy_competency_criteria_for_course_rerun(source_course_key: CourseKey, destination_course_key: CourseKey, object_id_map: dict[str, str])` in `src/openedx_learning/applets/cbe/api.py`, re-exported from `src/openedx_learning/api.py`, which is the only module `openedx-platform` imports. Return a small result object carrying the created group and rule counts, matching the result-object shape the removal endpoints use (\#674, \#675).  
- **Course run resolution inside `openedx-core`.** Resolve both runs with `openedx_catalog.api.get_course_run(course_key)`; never query `CourseRun` directly and never accept or return its integer primary key across the API boundary.  
- **Course-level group selection, source side.** `CompetencyCriteriaGroup.objects.filter(course=source_run, archived=False)`. For MVP, a competency's criteria tree has exactly three fixed levels, a shared root, a course-level group, and that group's bottom-tier children, so this one query is the whole "which groups does this source course have" step; no parent-chain check and no recursion are needed, because \#674 and \#675 already guarantee a live group never has an archived ancestor and never has zero live content beneath it.  
- **Bottom-tier group selection.** One more query, not a walk: `CompetencyCriteriaGroup.objects.filter(parent_id__in=<course-level group ids>, archived=False)`, since bottom-tier groups are the deepest group level for MVP and hold the rules directly.  
- **Rule selection.** `CompetencyCriterion.objects.filter(competency_criteria_group_id__in=<bottom-tier group ids>, archived=False)`, loading each rule's tag-association foreign key with `select_related` in the same query, and index the results by group id.  
- **Creation order.** Create the course-level groups first, then their bottom-tier children, so each child's parent row exists first, and bulk-create the rules last. Every rule found by the rule-selection query belongs to a copied bottom-tier group by construction, so it needs no further filtering.  
- **Field-by-field copy rules.** Groups carry `oel_tagging_tag_id`, `name`, `ordering`, and `logic_operator` verbatim; `course` is remapped to the destination run where the source had the source run and left null where the source was null; `parent_id` is the source's own value (the shared root) for a copied course-level group, and the new course-level row's id for its copied bottom-tier children. Rules carry `competency_rule_profile_id`, `rule_type_override`, and `rule_payload_override` verbatim, whether a rule is using the system default rule profile or has a custom override of its own. `archived` is never carried on either model; every new row takes the field default of `False`, which is immune to any future change in what gets copied.  
- **Resolving the destination tag association.** `ObjectTag.objects.get(object_id=object_id_map[old_object_id], taxonomy_id=..., tag_id=...)`. This is a genuine natural key: `ObjectTag.Meta.unique_together` includes `("object_id", "taxonomy", "tag_id")`, so the lookup cannot return more than one row. It assumes a non-free-text taxonomy, which holds because rules only reference competency-enabled taxonomies and those have real tag rows. Let `ObjectTag.DoesNotExist` propagate rather than skipping the rule: after the tag step has run, an unresolvable association means the two steps disagree, which is a bug, and the surrounding transaction rolls the whole copy back.  
- **Rules pointing outside the source course.** If a source rule's `object_id` is absent from `object_id_map`, its tagged content is not part of the copied course, so keep its association foreign key unchanged. Remap what moved; reference what did not.  
- **History rows.** Both models carry `django-simple-history`. `bulk_create` does not write history rows, so use `simple_history.utils.bulk_create_with_history` (or create rows individually) so the copied rows have an initial historical record.  
- **Not routed through the create path.** The copy constructs rows directly instead of calling the criteria-group and rule create APIs, for three reasons unrelated to archiving. The create path re-runs ADR 0002 Decision 4's rule-profile assignment computation, and a copy is not one of Decision 4's four listed write events, so going through create would overwrite the copied profile assignment. The create path also revalidates a tree that is already valid by construction, which would make a rerun fail on data predating a newer validation rule. And creation is per-row while this is a bulk tree operation. The consequence to accept deliberately: the copy does not inherit the creation-time `archived` enforcement added by \#717, so the archived filters above are the copy's own responsibility and must be tested here.  
- **Transaction nesting.** The `openedx-core` function wraps its own work in `transaction.atomic()`; the platform task wraps the catalog check, the tag copy, and the call to that function in one outer `transaction.atomic()`. The atomic blocks inside the tagging calls become savepoints under it.  
- **Cross-run coupling to be aware of when writing tests.** A recreated group is an ordinary row under the shared parent, so once the new run accumulates learner status the shared parent is no longer hard-deletable for any run, and archiving that shared parent through \#675 archives every run's group beneath it in one action. That follows from the shared-parent rule and is not special-cased here.  
- **No new schema.** No model, field, or migration in this ticket. The `archived` field on both models arrives with \#716, which this ticket depends on.  
- **Layering.** The new function is the higher layer calling the lower: `openedx_learning` imports `openedx_tagging` and `openedx_catalog`, and `openedx-platform` calls `openedx_learning.api`. `.importlinter` currently names neither `openedx_catalog` nor `openedx_learning` in `root_packages`; if \#613 adds `openedx_learning` there, `openedx_learning` must sit above `openedx_tagging` in the `src_layering` contract.  
- **Out of scope, handled by companion tickets.** Course export (\#695) and course import (\#696) are the cross-instance pair that needs taxonomy identity resolution, which a same-instance rerun never does. Library copy is \#697 and \#698. Documentation across all the copy mechanisms is \#652. `ObjectTag` has no `archived` field today, so the tag step cannot filter on one; when it gains one, every copy mechanism's tag step needs the same filter the criteria step has here.  
- **Test cases, `openedx-core` side.**  
  - A rerun with tagged content and course-scoped rules.  
  - A rerun of a course with neither, which must succeed with nothing copied.  
  - A group with no course scope, which must not be recreated.  
  - A course-level group with bottom-tier children, verifying the children point at the new course-level group while the course-level group itself keeps the shared root as its parent.  
  - An archived course-level group with bottom-tier children still on record, verifying the whole branch is skipped.  
  - An archived bottom-tier group under a live course-level group, verifying only that branch is skipped and its siblings are copied.  
  - An archived rule under a live bottom-tier group, verifying only that leaf is skipped and its siblings are copied.  
  - A group left with exactly one live rule, which must still be recreated as a group.  
  - A rule using the system default rule profile alongside a sibling rule with a custom override, verifying both carry their respective assignment verbatim.  
  - A rule whose tagged content lies outside the source course, verifying its association reference is unchanged.  
  - A forced failure inside the copy, verifying no partial rows and no copied tags remain.  
- **Test cases, `openedx-platform` side.**  
  - The receiver enqueues the task, and ignores a payload that is not course data.  
  - The object id map is built correctly for both course-level and block-level tags.  
  - A rerun whose destination has no catalog record creates one and proceeds.  
  - A rerun whose source course has no catalog record copies the tags and creates no rules.  
  - An end-to-end rerun producing both tags and rules on the destination.  
  - A rerun where content also carries a tag from a taxonomy that is not competency-enabled, verifying that tag is copied too, not only competency tags.  
  - A rerun verifying that no new taxonomy and no new tag row are created, only new object-tag associations pointing at the existing taxonomy and tag rows.  
  - Retrying the copy task after a forced failure, verifying the second attempt produces exactly one full copy with nothing duplicated from the failed first attempt.  
  - No existing test in `cms/djangoapps/contentstore/` references `COURSE_RERUN_COMPLETED`, so the receiver has no current coverage to extend; this is new test surface.

Files to create and modify No new files: this ticket adds no model, no migration, and no new module.

**Modified files**

| File | Nature of modification |
| :---- | :---- |
| `cms/djangoapps/contentstore/signals/handlers.py` (openedx-platform) | Add the `COURSE_RERUN_COMPLETED` receiver that enqueues the copy task |
| `cms/djangoapps/contentstore/tasks.py` (openedx-platform) | Add the `copy_course_tags_and_criteria` Celery task |
| `cms/djangoapps/contentstore/signals/tests/test_handlers.py` (openedx-platform) | Add receiver tests |
| `cms/djangoapps/contentstore/tests/test_tasks.py` (openedx-platform) | Add task tests |
| `src/openedx_learning/applets/cbe/api.py` (openedx-core) | Add `copy_competency_criteria_for_course_rerun` |
| `src/openedx_learning/api.py` (openedx-core) | Re-export the new function from the umbrella public API facade |
| `tests/openedx_learning/applets/cbe/test_api.py` (openedx-core) | Add the copy tests |
| `.importlinter` (openedx-core) | Only if \#613 has not already done so: add `openedx_learning` to `root_packages` and place it above `openedx_tagging` in `src_layering` |

Nothing in `openedx/core/djangoapps/content_tagging/` is modified; this ticket only calls its existing public API.

Context **Dependencies and siblings**

- Depends on \#613, which creates the CBE models and the applet's `api.py` this ticket adds a function to; on \#716, which adds the `archived` field the copy filters on; and on \#681, which provides the read endpoint the Competency Management page uses to render a run's criteria group.  
- Sibling copy mechanisms, each out of scope here: course export \#695, course import \#696, copy to a library \#697, copy from a library \#698, documentation \#652.  
- Archiving behavior this ticket must respect: \#674 archives a single rule, leaving its group live only if another live rule remains, and otherwise cascades the archive upward through any ancestor left with nothing live under it; \#675 archives a group's whole subtree all-or-nothing, flagging every row in it, then applies \#674's same upward cascade above it; \#717 enforces `archived` at creation time, which this copy deliberately does not go through.  
- Edit endpoints the source-run/new-run isolation scenarios exercise: \#759 edits a mastery rule; \#760 edits a criteria group. Neither is expected to need changes for this ticket; the isolation follows from each run's course-scoped groups and rules being separate rows, per the field-by-field copy rules above.

**ADRs**

- `docs/openedx_tagging/decisions/0011-cross-instance-taxonomy-identity.rst` (ADR 0011, Status: Proposed): copy semantics, same-instance versus cross-instance, and copy-by-reference for taxonomies and tags.  
- `docs/openedx_learning/decisions/0002-competency-criteria-model.rst` (ADR 0002): group and rule field definitions (Decisions 2 and 4), the prohibition on persisting empty groups (Decision 2), rule-profile scoping and archiving (Decision 3), and delete protection and archive-only archiving (Decision 7).  
- `docs/openedx_learning/decisions/0003-competency-criteria-versioning.rst` (ADR 0003): `django-simple-history` on both models (Decision 1), and the post-use archive rule for tag associations (Decision 3).  
- `docs/openedx_learning/decisions/0001-competency-criteria-location.rst` (ADR 0001): places CBE at `src/openedx_learning/applets/cbe/` under an umbrella app with a single aggregated public API.

**Prior art in `openedx-core`**

- `src/openedx_catalog/api_impl.py`: `get_course_run` and `create_course_run_for_modulestore_course_with`.  
- `src/openedx_tagging/models/base.py`: `ObjectTag`, its `unique_together` natural key, and `is_copied`.  
- `src/openedx_content/api.py`: the facade re-export pattern to follow.

**Prior art in `openedx-platform`**

- `cms/djangoapps/contentstore/tasks.py`: `rerun_course`, its `clone_course` call, and the `COURSE_RERUN_COMPLETED` emit.  
- `common/djangoapps/course_action_state/models.py`: `CourseRerunState.course_key` and `.source_course_key`.  
- `common/djangoapps/course_action_state/managers.py`: `CourseRerunStateManager.failed`, which `rerun_course` already calls on a course-clone failure and which this ticket's failure path reuses.  
- `xmodule/modulestore/split_mongo/split.py` and `split_draft.py`: `clone_course`, which preserves block ids and passes `skip_auto_publish`; `xmodule/modulestore/draft_and_published.py` for `DIRECT_ONLY_CATEGORIES`.  
- `openedx/core/djangoapps/content_tagging/handlers.py`: `duplicate_tags`, prior art for a tag-copy receiver.  
- `cms/djangoapps/contentstore/views/course.py`: `course_rerun_handler`, the entry point for manual verification.

</details>
