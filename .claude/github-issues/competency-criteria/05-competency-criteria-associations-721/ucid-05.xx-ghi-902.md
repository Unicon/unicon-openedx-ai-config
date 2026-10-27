# [Follow-up - BE] Block dominance conflicts on taxonomy re-import

GitHub: https://github.com/openedx/openedx-core/issues/902 (#902, OPEN)
Cached: 2026-10-23

## User Story
As an administrator, I want a re-import of a competency taxonomy to be rejected when it would re-arrange tags in a way that breaks the competency dominance rule, in order to keep the competency criteria already configured for courses across the platform valid and manageable in Studio.

## Description

**Competency Dominance Rule Definition**: No ancestor/descendant of a given competency tag may hold live criteria in the same course as the given competency tag.

Each taxonomy reports a taxonomy_type. In the event that the taxonomy_type is Competency, then when re-importing this taxonomy, it needs to fail if the taxonomy the file produces violates the Competency Dominance Rule, whether the file introduced the violation or it already existed, and the import should report back the error in a useful way to the end user.

In order to continue following the rule that the tagging code is not allowed to know about the CBE code, we will implement this using the same principle described in ADR 0013 which suggests using openedx-platform as a proxy to handle the relationship between tagging and CBE. We will have openedx-platform pass a CBE validator function into the tagging import function when the taxonomy is a competency taxonomy. The tagging code runs it during the plan phase, after its own validations, and reports all errors together, on both the preview and the real import.

#666 supplies the dominance rule and the lookup of course runs where a set of tags holds live criteria. This ticket adds the pieces around it: a validator seam in tagging's import, the openedx-platform override that supplies the CBE validator for competency taxonomies, and the validator itself, which reuses #666's definition of a live criterion to look up, in one query, which tags of the taxonomy hold live criteria in which course runs, then walks the tag tree the file produces: for each tag that holds criteria, it follows the parent links up to the root and reports every ancestor that holds criteria in the same course run. That lookup is the check's only database query, whatever the size of the file; the rest is an in-memory walk of the tree.

## Context
- The primary BE implementation of this for the GUI: #666
- #797 is the frontend counterpart to #666

## Acceptance Criteria

In these scenarios, an error names a tag by its value and its identifier in the file. A tag "holds live criteria in a course run" when it has at least one criterion there that is not archived, under an association with that course run that is not archived. "The preview" is the plan step of Studio's taxonomy import wizard, and "the import" is the step that applies the file. A conflict is reported on the file row of the descendant, the lower tag of the conflicting ancestor/descendant pair. Studio's re-import replaces the taxonomy's tags with the file's, so each file below is an export of the taxonomy with only the rows named in the scenario changed.

```
Background:
  Given a competency taxonomy "Thinking Skills", enabled for organizations OrgA and OrgB, with these tags:
    | Tag               | Parent            |
    | Cognitive Skills  | (root)            |
    | Critical Thinking | Cognitive Skills  |
    | Inference         | Critical Thinking |
    | Analysis          | Critical Thinking |
    | Evaluation        | (root)            |
    | Deduction         | Evaluation        |
    | Synthesis         | (root)            |
  And Course X is the course run course-v1:OrgA+CT101+2026
  And Course Y is the course run course-v1:OrgB+CT201+2026
  And no tag holds criteria in either course run unless a scenario says so
```

### Re-imports that are rejected

```
Scenario: Moving a tag under a tag that holds criteria in the same course run is rejected in the preview
  Given "Critical Thinking" and "Deduction" both hold live criteria in Course X
  When a taxonomy administrator previews a re-import whose file moves "Deduction" from "Evaluation" to "Critical Thinking"
  Then the preview reports an error for the file row of "Deduction"
  And the error names "Critical Thinking" as the ancestor and "Deduction" as the descendant that both hold criteria in course-v1:OrgA+CT101+2026
  And the error says to change the file so that "Critical Thinking" is not an ancestor of "Deduction", or to archive or remove one of the two competencies' criteria in that course run first
  And the error is listed in the same format as the import's other errors for a file row
  And the wizard does not let the administrator continue to the import

Scenario: The import of a rejected file fails and applies none of the file
  Given "Critical Thinking" and "Deduction" both hold live criteria in Course X
  And a file moves "Deduction" from "Evaluation" to "Critical Thinking" and renames "Synthesis" to "Creative Synthesis"
  When the file is imported without a preview, for example through the REST API
  Then the import fails and reports an error for the file row of "Deduction"
  And the error names "Critical Thinking" as the ancestor and "Deduction" as the descendant that both hold criteria in course-v1:OrgA+CT101+2026
  And "Deduction" is still a child of "Evaluation"
  And "Synthesis" keeps its name
  And the criteria of "Critical Thinking" and "Deduction" in Course X are unchanged

Scenario: A criterion added between the preview and the import is caught by the import
  Given "Deduction" holds live criteria in Course X and "Critical Thinking" holds none
  And a taxonomy administrator has previewed a file that moves "Deduction" under "Critical Thinking", with no errors
  When a course author adds a criterion for "Critical Thinking" in Course X
  And the administrator then continues to the import
  Then the import fails with an error naming "Critical Thinking", "Deduction", and course-v1:OrgA+CT101+2026
  And "Deduction" is still a child of "Evaluation"

Scenario: A move is rejected when a descendant of the moved tag holds the criteria, and the error is on that descendant's row
  Given "Critical Thinking" and "Deduction" both hold live criteria in Course X
  And "Evaluation" holds none
  When a taxonomy administrator previews a file that moves "Evaluation", with its child "Deduction", under "Critical Thinking"
  Then the preview reports an error for the file row of "Deduction" and none for the file row of "Evaluation"
  And the error names "Critical Thinking" as the ancestor and "Deduction" as the descendant, in course-v1:OrgA+CT101+2026

Scenario: A move is rejected when the tag with criteria is above the new parent, not the new parent itself
  Given "Cognitive Skills" and "Deduction" both hold live criteria in Course X
  And neither "Critical Thinking" nor "Inference" holds criteria in Course X
  When a taxonomy administrator previews a file that moves "Deduction" under "Inference"
  Then the preview reports an error for the file row of "Deduction"
  And the error names "Cognitive Skills" as the ancestor and "Deduction" as the descendant, in course-v1:OrgA+CT101+2026

Scenario: A tag added in the same file can link a conflicting pair
  Given "Critical Thinking" and "Deduction" both hold live criteria in Course X
  When a taxonomy administrator previews a file that adds a new tag "Argumentation" under "Critical Thinking" and moves "Deduction" under "Argumentation"
  Then the preview reports an error for the file row of "Deduction" naming "Critical Thinking" and "Deduction" in course-v1:OrgA+CT101+2026
  And the preview reports no error for the file row that adds "Argumentation"

Scenario: Two moves that create a conflicting pair together are rejected, although neither move alone would be
  Given "Critical Thinking" and "Synthesis" both hold live criteria in Course X
  And "Evaluation" holds no criteria
  When a taxonomy administrator previews a file that moves "Evaluation" under "Critical Thinking" and moves "Synthesis" under "Evaluation"
  Then the preview reports the conflict between "Critical Thinking" and "Synthesis" in course-v1:OrgA+CT101+2026 for the file row of "Synthesis"

Scenario: Every conflict in the file is reported, not only the first
  Given "Critical Thinking" and "Deduction" both hold live criteria in Course X and in Course Y
  And "Synthesis" holds live criteria in Course X
  When a taxonomy administrator previews a file that moves "Deduction" under "Critical Thinking" and moves "Synthesis" under "Analysis"
  Then the preview reports these three conflicts:
    | File row of | Ancestor          | Descendant | Course run                |
    | Deduction   | Critical Thinking | Deduction  | course-v1:OrgA+CT101+2026 |
    | Deduction   | Critical Thinking | Deduction  | course-v1:OrgB+CT201+2026 |
    | Synthesis   | Critical Thinking | Synthesis  | course-v1:OrgA+CT101+2026 |

Scenario: A row that changes a tag's identifier and moves it is checked like any other move
  Given "Critical Thinking" and "Deduction" both hold live criteria in Course X
  When a taxonomy administrator previews a file whose row for "Deduction" changes its identifier and moves it under "Critical Thinking"
  Then the preview reports an error for that file row naming "Critical Thinking" and "Deduction" in course-v1:OrgA+CT101+2026

Scenario: The course run is named even when the administrator has no access to it
  Given an organization administrator of OrgA, who can re-import the taxonomy but has no access to Course Y
  And "Critical Thinking" and "Deduction" both hold live criteria in Course Y
  When the administrator previews a file that moves "Deduction" under "Critical Thinking"
  Then the preview reports the conflict and names course-v1:OrgB+CT201+2026
```

### Re-imports that are allowed

```
Scenario: Archived criteria don't block a move
  Given "Deduction" holds live criteria in Course X
  And every criterion "Critical Thinking" has in Course X is archived
  When a taxonomy administrator previews and then imports a file that moves "Deduction" under "Critical Thinking"
  Then the preview reports no errors
  And after the import "Deduction" is a child of "Critical Thinking"

Scenario: Archived associations don't block a move
  Given "Deduction" holds live criteria in Course X
  And the association of "Critical Thinking" with Course X is archived
  When a taxonomy administrator previews and then imports a file that moves "Deduction" under "Critical Thinking"
  Then the preview reports no errors
  And after the import "Deduction" is a child of "Critical Thinking"

Scenario: Related tags whose criteria are in different course runs don't block a move
  Given "Critical Thinking" holds live criteria in Course X only
  And "Deduction" holds live criteria in Course Y only
  When a taxonomy administrator previews and then imports a file that moves "Deduction" under "Critical Thinking"
  Then the preview reports no errors and the import succeeds

Scenario: Tags that end up as siblings don't block a move
  Given "Analysis" and "Deduction" both hold live criteria in Course X
  And neither "Cognitive Skills" nor "Critical Thinking" holds criteria in Course X
  When a taxonomy administrator previews and then imports a file that moves "Deduction" under "Critical Thinking"
  Then the preview reports no errors and the import succeeds
  And "Deduction" and "Analysis" are siblings under "Critical Thinking"

Scenario: Adding a new tag under a tag with criteria never blocks
  Given "Critical Thinking" holds live criteria in Course X
  When a taxonomy administrator previews and then imports a file that adds a new tag "Argumentation" under "Critical Thinking"
  Then the preview reports no errors and the import succeeds
  And "Argumentation" is a child of "Critical Thinking"

Scenario: A file that moves no tag with criteria imports as it does today
  Given "Critical Thinking" and "Deduction" both hold live criteria in Course X
  When a taxonomy administrator previews and then imports a file that renames "Synthesis", adds a new tag "Induction" under "Evaluation", and moves "Analysis" under "Evaluation"
  Then the preview reports no errors and the import succeeds
  And the taxonomy matches the file

Scenario: Criteria stay valid after an allowed move
  Given "Deduction" holds live criteria in Course X, and no other tag holds criteria in Course X
  When a taxonomy administrator imports a file that moves "Deduction" under "Inference"
  Then "Deduction" is a child of "Inference"
  And the criteria of "Deduction" in Course X are unchanged
  And a course author can still add another criterion for "Deduction" in Course X
```

### Other taxonomies and entry points

```
Scenario: Re-importing a taxonomy that is not a competency taxonomy is unaffected
  Given a second taxonomy, which is not a competency taxonomy, with the same tags as "Thinking Skills"
  When a taxonomy administrator previews and then imports a file that moves "Deduction" under "Critical Thinking" in that taxonomy
  Then the preview and the import behave as they do today, and the import succeeds

Scenario: Creating a competency taxonomy by import is unaffected
  When a taxonomy administrator creates a new competency taxonomy in Studio by importing a file with the tags above
  Then the taxonomy is created with those tags, as it is today
```

### Errors reported together

```
Scenario: The import's own errors and dominance conflicts appear in one preview
  Given "Critical Thinking" and "Deduction" both hold live criteria in Course X
  When a taxonomy administrator previews a file that moves "Deduction" under "Critical Thinking" and gives "Synthesis" the parent "Metacognition", which no row or tag defines
  Then the preview reports the unknown parent "Metacognition" named by the row for "Synthesis"
  And the preview reports the conflict for the file row of "Deduction"

Scenario: A file with a parent cycle still gets a complete preview
  Given "Critical Thinking" and "Synthesis" both hold live criteria in Course X
  When a taxonomy administrator previews a file that makes "Evaluation" a child of "Deduction" while "Deduction" stays a child of "Evaluation", and moves "Synthesis" under "Analysis"
  Then the preview finishes and reports the parent cycle
  And the preview reports the conflict between "Critical Thinking" and "Synthesis" in course-v1:OrgA+CT101+2026 for the file row of "Synthesis"
```

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done.

**Summary**

`openedx_tagging` gains a generic seam: `import_tags()` accepts optional validator callables that run during the plan phase and add their errors to the plan, and `TaxonomyView` gains a hook that supplies them, empty by default. openedx-platform's `TaxonomyOrgView` overrides the hook to supply a new CBE validator for competency taxonomies, so tagging never references CBE, following the proxy pattern in ADR 0013. The validator reads the final tag tree that PR #877 already computes, finds in one query which tags of the taxonomy hold live criteria in which course runs, and reports every ancestor/descendant pair in the final tree whose two tags hold live criteria in the same course run, whether the file creates the pair or the stored taxonomy already has it.

**Approach**

openedx-core, tagging (no CBE reference):

1. In `src/openedx_tagging/import_export/import_plan.py`, `TagImportPlan.generate_actions()` already computes the final tree for PR #877's hierarchy checks, as the `parent_of`, `pk_of`, and `row_of` dicts that `_end_state()` returns, but keeps them in local variables. Right after `_end_state()`, store the final tree on the plan as a public attribute, for example `final_tree: dict[str, FinalTag]`, keyed by casefolded final id like those dicts. `FinalTag` is a small record next to `ExistingTag`. It holds the tag's final `external_id` and `value` (from its file row, or from `_existing_tags()` for a stored tag the file omits), its `pk` (None for a tag the import creates), its `parent` (the parent's final id, or None for a root), and its `row` (1-based, as "Row N" appears in errors, or None when the tag has no row). With this record, validators never deal with `NEW_TAG`, the 0-based positions, or the split between file rows and stored tags. The attribute's docstring calls it read-only input for import validators.
2. In `src/openedx_tagging/import_export/api.py`, `import_tags()` gains a trailing `validators=None` keyword that takes a list of `Callable[[TagImportPlan], list[TagImportError]]`. Run each validator after `generate_actions()` and before `task.log_plan()`, and add its results to `plan.errors` even when tagging has already found errors. The placement matters because `log_plan()` copies the errors into the task log that the Studio import wizard shows. A validator that ran after `log_plan()` would still block the import, but its message would never reach the wizard. Parse errors still end the import before planning. The docstring states the validator contract:
   - A validator is read-only.
   - A validator returns errors and never raises. A raised exception lands in the broad `except` and drops the plan from the preview.
   - A validator tolerates a final tree in which tagging has already found errors, such as a parent that is not a tag of the tree, or a parent cycle.
3. In `src/openedx_tagging/rest_api/v1/views.py`, `TaxonomyView` gains `_get_import_validators(self, taxonomy)`, which returns `[]`, next to `_create_taxonomy_for_import()`. `update_import` and `plan_update_import` pass its result to `import_tags()`. `create_import` does not call it. The docstring says that openedx-platform overrides this hook, because a rename in core would silently turn platform's override into dead code.

openedx-core, CBE, in `src/openedx_learning/applets/cbe/api.py`:

4. Move the live-criteria filter out of PR #875's `get_courses_with_relative_criteria()` into a private `_live_criteria_groups()`, which returns the `CompetencyCriteriaGroup` queryset with the archived and course conditions. `get_courses_with_relative_criteria()` then filters that queryset by `tag_id__in`, and its signature and behavior stay the same. The criterion-creation check and the import check then share one definition of "holds live criteria in a course run", so Studio and the import can't disagree about what conflicts.
5. Add `validate_tag_import_dominance(plan) -> list[TagImportError]` to `__all__`. It must be in `__all__` because openedx-platform imports it from `openedx_learning.api`, which re-exports this module's `__all__`.
   1. Run one query: `_live_criteria_groups()` filtered by `tag__taxonomy=plan.taxonomy`, read as `values_list("tag_id", "parent__course__course_key")`, and collect the course keys of each tag pk into a set.
   2. Keep only the tags of `plan.final_tree` whose `pk` has course keys. Tags that the import deletes are not in the final tree, so they drop out here. Tags that the file creates have no pk, so they drop out too.
   3. For each kept tag, in file row order, walk up its `parent` links with a visited set. Stop at a root, or at a parent that is not a key of the final tree: that parent is unknown or deleted, tagging reports it itself, and the validator treats it as the root. If the walk revisits a tag, the starting tag is on or below a parent cycle that tagging has already reported as a `ParentCycleError`, so skip the starting tag. Validators run after that report, and without the visited set the walk would never end.
   4. For each kept tag that the walk reaches as an ancestor, add one error per course key that the two tags share.

   The validator costs one query per import whatever the file size, because it filters by taxonomy rather than by a list of tag ids. The in-memory walk is bounded by the number of tags that hold criteria times the tree depth.

   Each error is a plain `TagImportError(message)`, attached to no action. The message names the descendant, then the ancestor, by the final value and identifier in `plan.final_tree`. It then names the course key, and then the remedy: change the file so that the ancestor is not an ancestor of the descendant, or archive or remove one of the two competencies' criteria in that course run first. `Tag.display_str()` doesn't fit here, because it shows the stored value and identifier, which the file may change. The course key appears even when the importing admin cannot access that course run. The message starts with `Row N: `, using the descendant's `row`, which is the same prefix that `ImportAction._validate_parent()` puts on parent errors. When the descendant has no row, the message has no prefix. That only happens for a direct `import_tags(replace=False)` caller, because both re-import endpoints import with `replace=True`, which deletes every stored tag the file omits.

openedx-platform:

6. In `openedx/core/djangoapps/content_tagging/rest_api/v1/views.py`, `TaxonomyOrgView` overrides `_get_import_validators()` to add `validate_tag_import_dominance` when `is_competency_taxonomy(taxonomy)` is true. The re-import request carries no `taxonomy_type`, so the stored taxonomy decides.

Beyond the Acceptance Criteria, unit tests must cover the following cases. In this list, a conflicting pair is an ancestor tag and a descendant tag that both hold live criteria in the same course run. QA cannot create one in Studio, because #666 blocks it, so these cases are unit tests only.
- A rename-only file is rejected when the stored taxonomy already holds a conflicting pair, and the error is on the descendant's row.
- A file that moves the descendant of an existing conflicting pair under a sibling below the same ancestor, so that the ancestor still sits above the descendant, is rejected.
- A file that changes the identifier of the ancestor of an existing conflicting pair, and leaves the descendant under it, is rejected.
- A file that moves the descendant of an existing conflicting pair to the root clears the conflict, and the import succeeds.
- With `import_tags(replace=False)` and a file that omits the descendant of an existing conflicting pair, the error names both tags and has no row prefix.
- The validator makes exactly one query, both when no tag holds criteria and when several pairs conflict.

openedx-platform needs its own tests for the override, because openedx-core's tests cannot exercise it: the same file is rejected for a competency taxonomy and accepted for a plain one, on both the plan endpoint and the import endpoint.

Out of scope:
- `create_import`, because a new taxonomy has no criteria.
- Changes to a tag's parent that bypass the two re-import endpoints: edits through the Django admin, and a direct call to `import_tags()` that passes no validators. `import_tags_task` is such a caller: it runs tagging's own checks but not the pluggable validators, and nothing in openedx-core or openedx-platform calls it today. This gap is accepted.
- Restoring an archived criterion or group. No restore path exists, and adding one would need its own dominance check.
- Whether replace-mode deletes archive or hard-delete tags (#780), and refusing the values and identifiers of archived tags on import (#814).

**Files to create and modify**

| File | Change |
| --- | --- |
| src/openedx_tagging/import_export/import_plan.py | modified: `FinalTag` and `TagImportPlan.final_tree` |
| src/openedx_tagging/import_export/api.py | modified: `validators` keyword on `import_tags()` |
| src/openedx_tagging/rest_api/v1/views.py | modified: `TaxonomyView._get_import_validators()` |
| src/openedx_learning/applets/cbe/api.py | modified: `_live_criteria_groups()` and `validate_tag_import_dominance()` |
| tests/openedx_tagging/import_export/test_import_plan.py | modified |
| tests/openedx_tagging/import_export/test_api.py | modified |
| tests/openedx_tagging/test_views.py | modified |
| tests/openedx_learning/applets/cbe/test_api.py | modified |
| openedx-platform: openedx/core/djangoapps/content_tagging/rest_api/v1/views.py | modified: `TaxonomyOrgView._get_import_validators()` |
| openedx-platform: openedx/core/djangoapps/content_tagging/rest_api/v1/tests/test_views.py | modified |

**Additional context**

- PR #877 is merged and supplies `_existing_tags()`, `_end_state()`, `NEW_TAG`, and `ParentCycleError`. PR #875 (#666) is still open and must merge first. It supplies `get_courses_with_relative_criteria()` and the `make_tag` and `make_leaf_criterion` test helpers in `tests/openedx_learning/applets/cbe/test_api.py`. The release order is: PR #875 merges, then this openedx-core PR, then an openedx-core release, then the openedx-platform PR.
- PR #877's follow-ups #892 and #893 also edit `generate_actions()`, so coordinate with their author.
- #666 lists "taxonomy parent/child structure changes after criteria already exist" as out of scope. This ticket closes that gap for import, which is the only way to reparent a tag outside the Django admin. #796 shares #666's course lookup.
- ADR 0013 (`docs/openedx_tagging/decisions/0013-competency-taxonomy-detection.rst`) is the proxy pattern followed here. `TaxonomyOrgView._create_taxonomy_for_import()` is the existing precedent for platform overriding a `TaxonomyView` hook.
- openedx-platform's router registers `TaxonomyOrgView` for the `taxonomies` routes and does not mount core's bare `TaxonomyView`, so every Studio re-import goes through the override.
- The real import plans again and reruns the validators, so a criterion created between the preview and the import is caught. A criterion created inside one `import_tags()` call, between the validator's query and the commit of `execute()`, is not caught. This race is accepted. PR #875's `_validate_containment()` has the mirror-image race.
- Errors reach the admin with no frontend change: Studio's import wizard already shows the task log on the 400 response from both the preview and the import. The wizard renders the log as one paragraph without line breaks, so each message must read on its own without relying on layout.

</details>

## Open Questions

- (implementer) The names `final_tree`, `FinalTag`, `_get_import_validators`, `_live_criteria_groups`, and `validate_tag_import_dominance` are suggestions. Whether `FinalTag` is a NamedTuple, like `ExistingTag`, or an attrs class, like `TagItem`, is also the implementer's choice.
