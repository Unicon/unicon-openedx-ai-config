# [Follow-up - BE] Block dominance conflicts on taxonomy re-import

GitHub: https://github.com/openedx/openedx-core/issues/902 (#902, OPEN)
Cached: 2026-10-23

## User Story
As an administrator, I want a re-import of a competency taxonomy to be rejected when it would re-arrange tags in a way that breaks the competency dominance rule, in order to keep the competency criteria already configured for courses across the platform valid and manageable in Studio.

## Description

*Competency Dominance Rule Definition*: No ancestor/descendant pair of competency tags may both hold live criteria in the same course.

Each taxonomy reports a taxonomy_type. In the event that the taxonomy_type is Competency, then when re-importing this taxonomy, it needs to fail if someone tried to re-arrange the tags in a way that violates #666, and the import should report back the error in a useful way to the end user. In order to continue following the rule that the tagging code is not allowed to know about the CBE code, we will implement this using the same principle described in ADR 0013 which suggests using openedx-platform as a proxy to handle the relationship between tagging and CBE. We will have openedx-platform pass a CBE validator function into the tagging import function when the taxonomy is a competency taxonomy. The tagging code runs it during the plan phase, after its own validations, and reports all errors together, on both the preview and the real import.

## Context
- The primary BE implementation of this for the GUI: #666
- #797 is the frontend counterpart to #666

## Acceptance Criteria

In these scenarios, an error names a tag by its value and its identifier in the file. A tag "holds live criteria in a course run" when it has at least one criterion there that is not archived, under an association with that course run that is not archived. "The preview" is the plan step of Studio's taxonomy import wizard, and "the import" is the step that applies the file. Studio's re-import replaces the taxonomy's tags with the file's, so each file below is an export of the taxonomy with only the rows named in the scenario changed.

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
  Given "Critical Thinking" holds live criteria in Course X
  And "Deduction" holds live criteria in Course X
  When a taxonomy administrator previews a re-import whose file moves "Deduction" from "Evaluation" to "Critical Thinking"
  Then the preview reports an error for the file row of "Deduction"
  And the error names "Critical Thinking" as the ancestor and "Deduction" as the descendant that both hold criteria in course-v1:OrgA+CT101+2026
  And the error says to leave "Deduction" under its current parent, or to archive or remove one of the two competencies' criteria in that course run first
  And the error is listed in the same format as the import's other errors for a file row
  And the wizard does not let the administrator continue to the import

Scenario: The import of a rejected file fails and applies none of the file
  Given "Critical Thinking" and "Deduction" both hold live criteria in Course X
  And a file moves "Deduction" from "Evaluation" to "Critical Thinking" and renames "Synthesis" to "Creative Synthesis"
  When the file is imported without a preview, for example through the REST API
  Then the import fails and reports the same conflict for the file row of "Deduction"
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

Scenario: A move is rejected when a descendant of the moved tag holds the criteria
  Given "Critical Thinking" holds live criteria in Course X
  And "Deduction" holds live criteria in Course X, and "Evaluation" holds none
  When a taxonomy administrator previews a file that moves "Evaluation", with its child "Deduction", under "Critical Thinking"
  Then the preview reports an error for the file row of "Evaluation"
  And the error names "Critical Thinking" as the ancestor and "Deduction" as the descendant, in course-v1:OrgA+CT101+2026

Scenario: A move is rejected when the conflicting ancestor sits above the new parent
  Given "Cognitive Skills" holds live criteria in Course X
  And "Deduction" holds live criteria in Course X
  And neither "Critical Thinking" nor "Inference" holds criteria in Course X
  When a taxonomy administrator previews a file that moves "Deduction" under "Inference"
  Then the preview reports an error for the file row of "Deduction"
  And the error names "Cognitive Skills" as the ancestor and "Deduction" as the descendant, in course-v1:OrgA+CT101+2026

Scenario: A tag added in the same file can link a conflicting pair
  Given "Critical Thinking" and "Deduction" both hold live criteria in Course X
  When a taxonomy administrator previews a file that adds a new tag "Argumentation" under "Critical Thinking" and moves "Deduction" under "Argumentation"
  Then the preview reports an error for the file row of "Deduction" naming "Critical Thinking" and "Deduction" in course-v1:OrgA+CT101+2026
  And the preview reports no error for the file row that adds "Argumentation"

Scenario: Moves in one file are checked against the tree the whole file produces
  Given "Critical Thinking" and "Synthesis" both hold live criteria in Course X
  And "Evaluation" holds no criteria
  When a taxonomy administrator previews a file that moves "Evaluation" under "Critical Thinking" and moves "Synthesis" under "Evaluation"
  Then the preview reports the conflict between "Critical Thinking" and "Synthesis" in course-v1:OrgA+CT101+2026 for the file row of "Evaluation"
  And the preview reports the same conflict for the file row of "Synthesis"

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
Scenario Outline: Archived criteria and archived associations don't block a move
  Given "Deduction" holds live criteria in Course X
  And <archived state>
  When a taxonomy administrator previews and then imports a file that moves "Deduction" under "Critical Thinking"
  Then the preview reports no errors
  And after the import "Deduction" is a child of "Critical Thinking"

  Examples:
    | archived state                                                   |
    | every criterion "Critical Thinking" has in Course X is archived  |
    | the association of "Critical Thinking" with Course X is archived |

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

Scenario: Moving a tag to the root never blocks
  Given "Inference" and its parent "Critical Thinking" both hold live criteria in Course X, an existing conflict made outside Studio
  When a taxonomy administrator previews and then imports a file that moves "Inference" to the root
  Then the preview reports no errors and the import succeeds
  And "Inference" is a root tag

Scenario: An existing conflict doesn't block an import that leaves it alone
  Given "Inference" and its parent "Critical Thinking" both hold live criteria in Course X, an existing conflict made outside Studio
  When a taxonomy administrator previews and then imports a file that only renames "Synthesis" to "Creative Synthesis"
  Then the preview reports no errors and the import succeeds

Scenario: An existing conflict doesn't block a move that keeps the same pair
  Given "Inference" and its parent "Critical Thinking" both hold live criteria in Course X, an existing conflict made outside Studio
  And "Analysis" holds no criteria
  When a taxonomy administrator previews and then imports a file that moves "Inference" under "Analysis", so that "Critical Thinking" is still its ancestor
  Then the preview reports no errors and the import succeeds

Scenario: Changing a parent's identifier is not a move
  Given "Inference" and its parent "Critical Thinking" both hold live criteria in Course X, an existing conflict made outside Studio
  When a taxonomy administrator previews and then imports a file that changes the identifier of "Critical Thinking" and gives the new identifier as the parent of "Inference" and "Analysis"
  Then the preview reports no errors and the import succeeds
  And "Inference" is still a child of "Critical Thinking"

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

`openedx_tagging` gains a generic seam: `import_tags()` accepts optional validator callables that run during the plan phase and add their errors to the plan, and `TaxonomyView` gains a hook that supplies them, empty by default. openedx-platform's `TaxonomyOrgView` overrides the hook to supply a new CBE validator for competency taxonomies, so tagging never references CBE, following the proxy pattern in ADR 0013. The validator reads the before and after tag trees that PR #877 already computes, finds the ancestor/descendant pairs the file creates, and uses PR #875's `get_courses_with_relative_criteria()` to find the course runs where both tags of a pair hold live criteria.

**Approach**

openedx-core, tagging (no CBE reference):

1. In `src/openedx_tagging/import_export/import_plan.py`, `TagImportPlan.generate_actions()` already computes, for PR #877's hierarchy checks, the pre-import tags from `_existing_tags()` and the `parent_of`, `pk_of`, and `row_of` dicts from `_end_state()`. Keep them on the plan and expose them read-only, for example as `plan.end_state`, documented as the input for import validators. `row_of` is 0-based, while `ImportAction.row` is 1-based.
2. In `src/openedx_tagging/import_export/api.py`, `import_tags()` gains a trailing `validators=None` keyword that takes a list of `Callable[[TagImportPlan], list[ImportActionError]]`. Run each validator after `generate_actions()` and before `task.log_plan()`, and add its results to `plan.errors` even when tagging has already found errors. The placement matters because `log_plan()` copies the errors into the task log that the Studio import wizard shows: a validator that ran after it would still block the import, but its message would never reach the wizard. Parse errors still end the import before planning. The docstring states the validator contract:
   - A validator is read-only.
   - A validator returns errors and never raises. A raised exception lands in the broad `except` and drops the plan from the preview.
   - A validator tolerates a tree in which tagging has already found errors.
3. In `src/openedx_tagging/rest_api/v1/views.py`, `TaxonomyView` gains `_get_import_validators(self, taxonomy)`, which returns `[]`, next to `_create_taxonomy_for_import()`. `update_import` and `plan_update_import` pass its result to `import_tags()`. `create_import` does not call it, because a new taxonomy has no criteria. The docstring says that openedx-platform overrides this hook, since a rename in core would silently turn platform's override into dead code.

openedx-core, CBE, in `src/openedx_learning/applets/cbe/api.py`:

4. Add `validate_tag_import_dominance(plan) -> list[ImportActionError]` to `__all__`, marked UNSTABLE like the other criteria-authoring functions. It compares pks, so a renamed identifier never counts as a move. A `parent_of` value that is not a key of `pk_of` is an unknown or deleted parent, which tagging reports itself; the validator treats that value as the root.
   - A moved tag is an existing tag (`pk_of` is not `NEW_TAG`) whose final parent is a different tag from its stored parent and is not the root. A move to the root only removes ancestors. Moves are read from the two trees rather than from `update_parent` actions, because tagging plans an `update_parent` for every child of a parent whose identifier is renamed, and plans none for a row that renames and moves a tag together.
   - For each moved tag, the new ancestors are its final ancestors minus its stored ancestors, and its subtree is the tag plus all of its final descendants. Both sets hold existing pks only. Because both sets come from the final tree, every move in the file is applied together, a chain through a tag the same file creates is followed, and a pair that two moves create together is reported on both rows.
   - Every walk up the final tree keeps a visited set. A moved tag whose walk revisits a tag is skipped, because it is on or below a parent cycle that tagging has already reported as a `ParentCycleError`. Validators run after that report, and an unguarded walk would never end.
   - Call `get_courses_with_relative_criteria()` with the new ancestors. Only if that finds a course run, call it again with the subtree, so there are at most two queries per moved tag. Each course run in both results holds a conflicting pair: the ancestor from the first result and the descendant from the second. Report one error per moved tag per course run.
   - Each error is an `ImportActionError(action=..., message=...)`. The action is the parent-setting action that the row produced, found by matching `ImportAction.row` to `row_of` (if no parent-setting action has that row, attach the error to any action with that row): `UpdateParentTag`, or `RenameTagExternalId` for a row that renames and moves a tag together.
   - The message starts with `Row N:`, as PR #877's parent errors do, because the `#N` in "Action error in 'update_parent' (#N)" is the plan's action number rather than the file row. It then names both tags with `Tag.display_str()`, then the course key, then the remedy: leave the tag under its current parent, or archive or remove one competency's criteria in that course run first. The course key appears even when the importing admin cannot access that course run.
   - Known limit: when the stored data already violates #666, and a file moves another tag between the two tags of that pair and moves the lower tag under it, that import is blocked and the error names the pair that already existed.

openedx-platform:

5. In `openedx/core/djangoapps/content_tagging/rest_api/v1/views.py`, `TaxonomyOrgView` overrides `_get_import_validators()` to add `validate_tag_import_dominance` when `is_competency_taxonomy(taxonomy)` is true. The re-import request carries no `taxonomy_type`, so the stored taxonomy decides. `get_queryset()` already joins the `CompetencyTaxonomy` row, so the check costs no query.

Beyond the Acceptance Criteria, the tests must cover:
- In openedx-platform, the same file is rejected for a competency taxonomy and accepted for a plain one, on both the plan endpoint and the import endpoint.
- The validator's query count: at most two lookups per moved tag, and none when no tag moves under a new parent.

Out of scope:
- `create_import`, because a new taxonomy has no criteria.
- Edits to a tag's `parent` through the Django admin, which bypass import. This gap is accepted.
- Restoring an archived criterion or group. No restore path exists, and adding one would need its own dominance check.
- Whether replace-mode deletes archive or hard-delete tags (#780), and refusing the values and identifiers of archived tags on import (#814).

**Files to create and modify**

| File | Change |
| --- | --- |
| src/openedx_tagging/import_export/import_plan.py | modified: `plan.end_state` accessor |
| src/openedx_tagging/import_export/api.py | modified: `validators` keyword on `import_tags()` |
| src/openedx_tagging/rest_api/v1/views.py | modified: `TaxonomyView._get_import_validators()` |
| src/openedx_learning/applets/cbe/api.py | modified: `validate_tag_import_dominance()` |
| tests/openedx_tagging/import_export/test_import_plan.py | modified |
| tests/openedx_tagging/import_export/test_api.py | modified |
| tests/openedx_tagging/test_views.py | modified |
| tests/openedx_learning/applets/cbe/test_api.py | modified |
| openedx-platform: openedx/core/djangoapps/content_tagging/rest_api/v1/views.py | modified: `TaxonomyOrgView._get_import_validators()` |
| openedx-platform: openedx/core/djangoapps/content_tagging/rest_api/v1/tests/test_views.py | modified |

**Additional context**

- PR #875 (#666) and PR #877 must merge first. The release order is: PR #875 and PR #877 merge, then this openedx-core PR, then an openedx-core release, then the openedx-platform PR.
  - PR #875 supplies `get_courses_with_relative_criteria(tag_ids, course=None)`, which maps each conflicting `CourseRun` to the lowest-id tag that has a live criterion there and already skips archived criteria and groups. It also supplies the `make_tag` and `make_criterion` test helpers.
  - PR #877 supplies `_existing_tags()`, `_end_state()`, `NEW_TAG`, `ImportAction.row`, and `ParentCycleError`. The `_end_state()` result is a local variable inside `generate_actions()` today, so step 1 is new work inside that function. PR #877's follow-ups #892 and #893 also edit `generate_actions()`, so coordinate with their author. Both follow-ups leave this design intact.
- #666 lists "taxonomy parent/child structure changes after criteria already exist" as out of scope. This ticket closes that gap for import, which is the only way to reparent a tag outside the Django admin. #796 shares #666's course lookup.
- ADR 0013 (`docs/openedx_tagging/decisions/0013-competency-taxonomy-detection.rst`) is the proxy pattern followed here. `TaxonomyOrgView._create_taxonomy_for_import()` is the existing precedent for platform overriding a `TaxonomyView` hook.
- openedx-platform's router registers `TaxonomyOrgView` for the `taxonomies` routes and does not mount core's bare `TaxonomyView`, so every Studio re-import goes through the override.
- The real import plans again and reruns the validators, so a criterion created between the preview and the import is caught. A criterion created inside one `import_tags()` call, between the validator's reads and the commit of `execute()`, is not caught. This race is accepted; PR #875's `_validate_containment()` has the mirror-image race.
- No frontend change is needed for the errors to reach the admin: Studio's import wizard already shows the task log on the preview's 400 and on the import's 400. It renders the log as one paragraph, without preserving line breaks, so each message must read on its own without relying on layout.

</details>

## Open Questions

- (architect, final review) Should the check be made exact for nested moves? With the subtree walk as drafted (the moved tag plus all of its final descendants), a file that moves one tag in between the two tags of a pair that already violates #666, and moves the lower tag under it, is blocked, and the error names the pre-existing pair. That is the one case where a pre-existing violation blocks an import. The alternative is to stop each moved tag's subtree walk at another moved tag and subtract that tag's stored ancestors, which makes the check exact but reports a pair created by two moves on one row instead of both. Recommended: accept the limit and state it, as drafted.
- (architect, final review) Should the generic seam's validator type be `Callable[[TagImportPlan], list[TagImportError]]`, the element type of `plan.errors`, rather than `list[ImportActionError]`? The CBE function would still return `ImportActionError`s. A future validator (for example one vetoing a replace-mode delete in the spirit of #780) has no row action to attach an error to. Recommended: widen to `TagImportError`.
- (architect, final review) Should `validate_tag_import_dominance` be marked UNSTABLE? Its only caller is openedx-platform's override, and its input is a plan accessor that is new in this ticket. Recommended: yes, matching the rest of the criteria-authoring family.
- (implementer) The names `plan.end_state` (and whether it is a NamedTuple or an attrs class), `validate_tag_import_dominance`, and `_get_import_validators` are suggestions.
