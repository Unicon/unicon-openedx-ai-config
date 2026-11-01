# [NTH - BE] Include Competency Criteria in Course Import

GitHub: https://github.com/openedx/openedx-core/issues/696 (#696, OPEN)
Cached: 2026-10-20

## User Story
As a course author, when I import a course, I want the import to include the competency mastery rules (competency criteria groups and competency criteria) attached to the course's content, in order to have them in the destination course without rebuilding each rule by hand.

## Description
Today, when a course is imported in Open edX, its content tags are included (as `tags.csv`), but the competency criteria groups and competency criteria associated with those tags are not. We should update the import process to also read the JSON file that contains this course's criteria groups and criteria, and reconstruct them for the destination course, which may be a new course or an existing course run that already has some of them.

At a high level, the import does this:

```
when a course is imported, right after tags.csv has been imported:
  if the criteria file is present and readable:
  for each competency in the file:
    find the competency's Tag by taxonomy export_id and tag external_id; if it is missing or archived, or its taxonomy is not a competency taxonomy, skip the competency
    if this course run's course-level group for that competency is archived, skip the competency
    for each criterion in the file:
      if the course run already has a live criterion for that competency on that subsection, leave it as it is
      if its subsection has no live tag association for that competency, skip it
      otherwise add it: in the one existing group that holds the rest of its file group's criteria, or in a new group when none does; skip it when those criteria are split across groups
      give it the destination's default rule profile when the file's threshold matches it, otherwise an override with the file's threshold
    create the course-level group, and bring back an archived root, only when a criterion was added
```

## Context
- #695 is the corresponding ticket for export

## Acceptance Criteria

Every outcome below can be checked on the destination course's Competency Management page, or through the criteria read path behind it (#681).

Terms used in the scenarios:

- A **mastery rule** is a competency criterion. A **group** is a competency criteria group. A competency's groups form a tree: one shared root, one course-level group per course, and bottom-tier groups under the course-level group that hold the mastery rules. For MVP every mastery rule evaluates a subsection.
- A **rule profile** holds a threshold, such as a grade of at least 75%. A mastery rule either uses a rule profile or carries its own override threshold. For MVP the destination has one rule profile, the default.
- The **course export** is the package the author uploads. The **criteria file** is the competency criteria file inside it, the one #695 writes.
- **How the import matches what the course already has.**
  - A mastery rule in the file is **already present** when the destination course has a live mastery rule for the same competency on the same subsection, in any group and with any threshold. The import leaves that mastery rule exactly as it is.
  - A mastery rule that is not present is **added**. To pick its group, the import looks at the other subsections listed in the same group of the file, and finds the live bottom-tier groups in the destination that already hold a live mastery rule on any of those subsections.
    - When exactly one destination group holds some of those subsections, the new mastery rule joins that group.
    - When no destination group holds any of them, the import creates a new group with the file's name and way of combining.
    - When two or more destination groups each hold some of them, the import cannot pick one, so it adds nothing from that group of the file.
  - The import never renames, reorders, or changes the way of combining of an existing group, and it never brings back an archived group or mastery rule.
  - When a competency's course-level group in the course is archived, nothing is imported for that competency.
  - The one exception to "never brings back" is an archived shared root, which becomes live again when the import adds a new course-level group beneath it.

```
# Importing into a new course

Scenario: Importing into a new course recreates the file's groups and mastery rules
  Given a course export whose criteria file holds a course-level group for a competency with two bottom-tier groups of mastery rules
  And the destination instance has a competency taxonomy and a competency matching the file's identifiers
  When a course author imports the course export into a new course and the import finishes
  Then the destination course has a course-level group for that competency holding two bottom-tier groups
  And each bottom-tier group has the name and the way of combining its children that the file records
  And the course-level group is named the way the destination names a course-level group an author creates by hand
  And the course-level group combines its bottom-tier groups the way the file records
  And each mastery rule evaluates the destination course's own copy of the subsection the file names
  And the import reports success to the author as usual

Scenario: Imported groups and mastery rules can be edited like any others
  Given a course whose groups and mastery rules were created by an import
  When the author adds a mastery rule to an imported group, and edits and removes an imported mastery rule, on the Competency Management page
  Then each change succeeds the same way it does for groups and mastery rules the author created by hand

Scenario: Imported mastery rules become one more alternative under the competency's existing shared root
  Given the destination instance already has a live shared root for the competency, holding another course's groups
  When a course export with mastery rules for that competency is imported into a new course
  Then the new course's course-level group sits under that shared root as one more alternative way to demonstrate the competency
  And the other course's groups and mastery rules are unchanged
  And no second shared root exists for the competency

Scenario: An archived shared root is brought back into use rather than duplicated
  Given the competency's only shared root on the destination is archived, because every course-level group under it was archived
  When a course export with mastery rules for that competency is imported into a new course
  Then the shared root is live again and holds the new course-level group
  And no second shared root exists for the competency
  And the archived course-level groups under it stay archived

Scenario: Importing beside a live source course on the same instance leaves the source unchanged
  Given a course export taken from a course on this same instance, whose mastery rules are still live
  When the course export is imported into a different, new course on that instance
  Then the new course has its own course-level group under the competency's shared root, beside the source course's group
  And the source course's groups, mastery rules, and learner statuses are unchanged
  And changing the new course's mastery rules leaves the source course's mastery rules unchanged

# How each mastery rule's threshold is chosen

Scenario Outline: Each recreated mastery rule keeps the threshold the file records
  Given the file records a mastery rule <as recorded>
  And the destination's default rule profile requires <destination threshold>
  When the course export is imported
  Then the destination has <result>

  Examples:
    | as recorded | destination default threshold | result |
    | as using a rule profile, with a grade of at least 75% | a grade of at least 75% | a mastery rule that uses the destination's default rule profile |
    | as using a rule profile, with a grade of at least 75% | a grade of at least 80% | a mastery rule with its own override requiring a grade of at least 75% |
    | as its own override, requiring a grade of at least 85% | a grade of at least 75% | a mastery rule with its own override requiring a grade of at least 85% |
    | as its own override, requiring a grade of at least 75% | a grade of at least 75% | a mastery rule that uses the destination's default rule profile |

# What is skipped

Scenario Outline: A competency the destination cannot take is skipped as a whole
  Given the file names a competency where <condition>
  When a course author imports the course export
  Then the destination gets no groups or mastery rules for that competency from the file
  And no taxonomy, competency, or tag association is created beyond what the content tags import creates
  And the other competencies in the file import normally
  And the import reports success to the author as usual

  Examples:
    | condition |
    | no taxonomy on the destination has the file's taxonomy identifier |
    | the taxonomy exists on the destination but is not a competency taxonomy |
    | the competency taxonomy has no competency with the file's competency identifier |
    | the competency or its taxonomy is archived on the destination |
    | a competency above or below it in the destination's taxonomy already has a live mastery rule in the destination course |

Scenario Outline: A mastery rule is skipped when the content tags import could not tag its subsection with the competency
  Given the file records a mastery rule for a competency on a subsection
  And the content tags import finds a competency by its value, while the criteria file finds it by its identifier
  And after the export, on the destination, <change>
  When the course export is imported
  Then the destination has no equivalent of that mastery rule
  And the mastery rules beside it in the file are created

  Examples:
    | change |
    | the competency's value was changed, so the content tags import finds no competency with the value the export carries and leaves the subsection with no usable tag for that competency |
    | the competency's value was given to a different competency in the same taxonomy, so the content tags import tags the subsection with that other competency instead |

Scenario: A group left with no mastery rules is left out, and nothing is created above it
  Given every mastery rule the file records in one bottom-tier group is on a subsection that is not tagged with the competency on the destination
  When the course export is imported
  Then the destination has no equivalent of that group
  And when every group for the competency is left out, the destination gets no course-level group and no new shared root for that competency

# Importing into a course run that already has mastery rules

Scenario: Importing the same course export again changes nothing further
  Given a course export was imported into a course run
  When the same course export is imported into that course run again
  Then the course run has the same groups and mastery rules as after the first import, each exactly once

Scenario: A mastery rule the course run is missing is added to the group that holds its siblings
  Given a course run whose bottom-tier group for a competency holds three mastery rules
  And a course export of that run taken when the group also held a fourth mastery rule, which the author has since removed
  When the course export is imported into that course run
  Then the fourth mastery rule is added to that same group
  And the three mastery rules already there are unchanged, with their learner statuses

Scenario: A file group the course run no longer has is recreated beside the existing groups
  Given a course run with two bottom-tier groups for a competency
  And a course export of that run taken when it also had a third bottom-tier group, which the author has since removed with all of its mastery rules
  When the course export is imported into that course run
  Then the course run has that third group again, with the name, way of combining, and mastery rules the file records
  And the two existing groups are unchanged

Scenario: A mastery rule the course run holds in a different group than the file records stays where it is
  Given the author removed a mastery rule from one bottom-tier group and created the same mastery rule again in another bottom-tier group for the same competency
  And the file records that mastery rule in the first group
  When the course export is imported into that course run
  Then the mastery rule exists once, live, in the group the author moved it to
  And no copy of it is created in the first group

Scenario: Two file groups whose mastery rules the author merged into one group both add to that group
  Given the file records two bottom-tier groups for a competency, one with mastery rules on subsections A and B, the other with mastery rules on subsections C and D
  And in the course run the author merged them, so one live bottom-tier group holds the mastery rules on A and C, and no mastery rule exists for B or D
  When the course export is imported into that course run
  Then the mastery rules on B and D are added to that one group, which then holds A, B, C, and D
  And no new group is created

Scenario: A mastery rule the course run already has keeps its own threshold
  Given a mastery rule in the course run that learners have been evaluated against requires a grade of at least 80%
  And the file records that mastery rule with a grade of at least 75%
  When the course export is imported
  Then the mastery rule still requires a grade of at least 80%, and its learner statuses are unchanged

Scenario: Groups that receive a mastery rule keep their own names and ways of combining
  Given the group in the course run that holds the file group's other mastery rules has a different name and a different logic operator from the ones the file records
  And the course-level group above it has a different logic operator from the one the file records
  When the course export is imported into that course run
  Then the missing mastery rule is added to that group
  And both groups' names and logic operators are unchanged

Scenario: A file group whose mastery rules are split across two groups in the course run adds nothing
  Given the file records a bottom-tier group with three mastery rules
  And the course run holds two of them in two different live bottom-tier groups and has no mastery rule for the third
  When the course export is imported into that course run
  Then the third mastery rule is not added anywhere
  And both groups in the course run are unchanged

Scenario: Groups and mastery rules the course export does not describe are left alone
  Given the course run has a group holding a mastery rule that the course export does not describe
  When the course export is imported
  Then that group and mastery rule are unchanged, and so are their learner statuses

Scenario: An archived course-level group skips the competency
  Given the course run's course-level group for a competency is archived, together with every group and mastery rule under it
  And the course export records mastery rules for that competency
  When the course export is imported into that course run
  Then nothing is created for that competency in the course run
  And the course-level group and everything under it stay archived
  And the other competencies in the file import normally

Scenario: A mastery rule whose earlier counterpart is archived is created fresh
  Given the course run's course-level group for a competency is live
  And the course run has an archived mastery rule for that competency on a subsection, archived when the author removed it after learners were evaluated against it
  And the file records a mastery rule for that competency on that subsection
  When the course export is imported into that course run
  Then a new live mastery rule exists for that competency on that subsection, in the group that holds its file siblings or in a new group when none does
  And the archived mastery rule stays archived, with its learner statuses unchanged

# Learner status

Scenario: The import never touches learner status
  Given learners have mastery statuses in the destination course run
  When a course export is imported into it
  Then every existing learner status is unchanged, and the import creates no learner status
  And each mastery rule the import created has no learner status until the next grade for its subsection is recorded

# File problems and permission

Scenario: A course export without a criteria file imports as it does today
  Given a course export with no criteria file, such as one taken from an instance that does not write it
  When the course export is imported
  Then the import succeeds as it does today

Scenario Outline: A criteria file the destination cannot read is skipped whole
  Given a course export whose criteria file <problem>
  When the course export is imported
  Then the import succeeds and the author sees no new message
  And the destination gets no groups or mastery rules from the file

  Examples:
    | problem |
    | cannot be read |
    | is in a newer format version than this instance supports |

Scenario: One entry that does not follow the format skips only itself
  Given a course export whose criteria file is readable but holds one mastery rule entry that does not follow its format version, such as one with no subsection
  When the course export is imported
  Then the destination has no equivalent of that mastery rule
  And every other group and mastery rule in the file is imported

Scenario: A course author who can import the course can import its mastery rules
  Given a course author permitted to import the course but holding no permission to author competency criteria
  When the author imports the course export
  Then the file's mastery rules are created in full, and none are dropped for lack of permission
```

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done.

**Summary**

openedx-core gets one public function that reads the competency criteria file #695 writes and adds the criteria it describes to the destination course run, in one transaction and without row locks. The import only adds, and it matches criteria by subsection. When the run already has a live criterion for the same competency and subsection, the import leaves it as it is. When a criterion is missing, the import adds it to the one existing group that holds the rest of its file group's criteria, or to a new group when no group does. Nothing that already exists is renamed, reordered, given a different operator, or reactivated. The one exception is an archived root, which is reactivated when a course-level group is added beneath it, as #717 does for authoring. openedx-platform calls the function from the course importer right after `tags.csv` has been imported.

**Approach**

1. **openedx-platform call site.** Add `import_competency_criteria(data_path, dest_id)` to `ImportManager` in `xmodule/modulestore/xml_importer.py` as a method that does nothing, and implement it on `CourseImportManager`.
   - Call it in `run_imports` after the `bulk_operations` block that runs `import_tags`, and before `post_course_import`. Keep the call outside that block's `try/except`, because that handler logs `FileNotFoundError` and `ValueError` at info level and would hide an unexpected error. A `COURSE_IMPORT_COMPLETED` receiver cannot do this work, because the event carries the course key but not the path to the course export.
   - When `COMPETENCY_CRITERIA_FILE_NAME` is absent from the course export, the method returns without logging. Otherwise it passes the file's raw bytes to `openedx_learning.api.import_competency_criteria_for_course(dest_id, contents)`.
2. **openedx-core public function.** Add `import_competency_criteria_for_course(course_key: CourseKey, contents: bytes) -> None` to `cbe/api.py` and its `__all__`. Leave it without an UNSTABLE marker unless the implementer sees a reason for one; the durable contract is the file format. The function looks up the run with `openedx_catalog.api.get_course_run()`. On `CourseRun.DoesNotExist` it logs a warning naming the course and returns. The import never creates a `CourseRun` row: the publish receiver creates it, nothing else in the import path does, and the import matches that.
3. **Parse before writing anything.** Add the parser to `cbe/criteria_file.py`, beside #695's serializer. Make it recursive, like the format.
   - An unreadable file skips the whole file with a warning. Catch `ValueError`, which covers JSON and Unicode decode errors. A `version` newer than this instance supports is handled the same way.
   - A structurally invalid entry skips only itself, and its siblings still import. A criterion skips itself when it has a missing key, an unknown `source`, or a `block_id` for which `course_key.make_usage_key(block_type, block_id)` raises `InvalidKeyError`. Any other problem inside a competency's entry skips that whole competency, for example an unknown `logic_operator` on one of its groups. A competency the file lists twice is skipped, because the import cannot tell which entry is right.
4. **Look up each competency.** Find the taxonomy with `openedx_tagging.api.get_taxonomy_by_export_id()`, check it with `is_competency_taxonomy()`, and find the Tag with the taxonomy's `tag_for_external_id()`. Skip the competency when the taxonomy or the Tag is missing or archived, or when the taxonomy is not a competency taxonomy.
5. **Load the run's existing groups and criteria once.**
   - Load the run's groups, archived ones included, with one filter on the subtree-course column that #919 adds to every group in a course-scoped subtree. That gives the course-level group and every group below it. Reach each shared root through the course-level group's `parent`.
   - Load every criterion in those groups, archived ones included, with `select_related` on `object_tag` and `rule_profile`. Index the criteria by Tag and `object_tag.object_id`.
   - A criterion counts as live only when the criterion, its group, and every group above it are all live.
6. **Plan each competency in memory first.** The plan reads only the state that step 5 loaded. This matters when the file lists one subsection in two groups, a second association that authoring allows, since `_reject_duplicate_criterion()` rejects a duplicate only inside the same group. On a fresh import, the subsection is then created in both groups instead of being counted as already present the second time.
   - **Archived course-level group.** When the run's course-level group for the Tag is archived, skip the competency. The import never reactivates a course-level group.
   - **Dominance.** When a taxonomy ancestor or descendant of the Tag has a live criterion in the run, skip the competency. Reuse the check that `_validate_containment()` makes through `get_courses_with_relative_criteria()`. Step 7 writes competencies one at a time, so this check also finds a relative that the same file added earlier.
   - **Criteria.** A file criterion is the same as a destination criterion when both have the same Tag and the same object id. Build the object id with `course_key.make_usage_key()`.
     - When a live destination criterion exists anywhere in the run, leave it as it is, in whatever group it sits. Log when its `_effective_rule()` differs from the file's values.
     - Otherwise the criterion is missing, including when only an archived destination criterion exists. The import then creates a fresh criterion and leaves the archived one archived, the same way #717 lets authoring add a fresh criterion for content whose earlier criterion was archived.
     - For a missing criterion, find the live ObjectTag for that object id and Tag, and skip the criterion when that ObjectTag is missing or archived. Do not fall back to matching by tag value. An ObjectTag that the tag import could not match has no Tag, and a renamed value can point at a different Tag.
   - **Group for the missing criteria.** For each bottom-tier group in the file, collect the live bottom-tier groups under the run's course-level group that hold a live criterion for any subsection that file group lists.
     - With exactly one such group, add the file group's missing criteria to it. Log when its name or operator differs from the file's.
     - With two or more, the import cannot tell which destination group the file group corresponds to, so skip the file group's missing criteria and log. This rule only decides which existing group a criterion joins; creating several new groups in one import is fine.
     - With none, plan a new bottom-tier group with the file's name, `ordering`, and `logic_operator`, and with `course=None`, the way authoring creates one.
     - `ordering` plays no part in matching, because every group has `ordering` 0 today and the field may be removed later.
     - A group the file nests below a bottom-tier group goes through the same matching one level down, inside its parent's destination group. No API creates such a group, so only a unit test covers this case.
   - **Rule profile or override.** Compare the file's `rule_type` and `rule_payload` with the values of the rule profile that `_get_applicable_rule_profile()` returns, which for MVP is the system default. When they are equal, the new criterion uses that rule profile. Otherwise it carries an override with the file's values. The file's `source` does not change the outcome. Validate each planned override with `validate_rule_payload()` and skip any override it rejects, so the next bullet works from the final set.
   - **Nothing empty.** ADR 0002 forbids persisting an empty group. Plan a new group only when a criterion is added in or beneath it. Create the course-level group, or reactivate an archived root, only when the competency adds at least one criterion.
7. **Write each competency's plan.** All writes for the whole file happen inside one `transaction.atomic()`, and the import takes no row locks. The transaction only makes the writes commit or roll back together; it does not lock the rows the import reads.
   - Do not use `select_for_update()`, which would lock the rows the import reads so that a concurrent author has to wait. `AGENTS.md` in openedx-core reserves it as a last resort that needs a comment explaining why a constraint cannot do the job, and here the unique constraints already handle the root and the course-level group. Factor `_create_leaf_group()`'s two `get_or_create()` calls into a helper that both callers use. `get_or_create()` already recovers from the `IntegrityError` a concurrent insert raises, and the helper keeps the derived names in one place. Pass the file's `root_logic_operator` and the course-level group's `logic_operator` as `defaults`, so only a newly created row takes them. Log when an existing row's operator differs from the file's, counting a null operator as OR. The file's root and course-level group names are the source course's, and the import does not use them.
   - Because nothing is locked, the duplicate check in step 6 and the dominance check are plain reads. Authoring serializes the same checks by locking the Tag row in `associate_competency_criterion()`. So when an author adds a criterion for the same competency in the same run while the import runs, the author's criterion can get past the import's checks as a duplicate. Accept that race and explain it in a code comment.
   - Reactivate an archived root with `save()`, so that simple-history records the change. Call `get_or_create()` for the run's `CompetencyCourseRun` row, which is meant to exist for every run that has criteria, and do not lock it.
   - Create new groups parent-first, then the criteria, each with `objects.create()`, so that `save()` runs `full_clean()` and simple-history records every row. Do not call `create_competency_criterion()`, because it rewrites the object's tags through `tag_object()`. The import never changes Tags, ObjectTags, or learner status.
   - Any exception rolls back the whole file and propagates, so the course import fails.
8. **Logging.** Log every skip and every difference at info level, or at debug level if the implementer prefers. Each line names the competency, and for a criterion, its block. Only the whole-file skip and the missing `CourseRun` are logged as warnings. End with one info line that counts the groups and criteria created and the entries skipped. Nothing is shown to the author; that is out of scope.
9. **Docs.** Add these import semantics to #695's format page, `docs/openedx_learning/competency_criteria_file.rst`.

Tests must cover, beyond the Acceptance Criteria:

Entries the import skips, or failures:

- each structurally invalid entry, where only that criterion or competency is skipped
- a criterion whose subsection is not in the destination course, whose ObjectTag is archived, or whose ObjectTag has no Tag
- an override that `validate_rule_payload()` rejects
- the dominance skip, including a relative added earlier from the same file
- a missing `CourseRun`, and a failure partway through that rolls everything back
- openedx-platform: a missing file does nothing, and an unexpected error fails the import

Shapes that import cleanly:

- a group nested below a bottom-tier group, created through the model, and a criterion the file lists directly on the course-level group
- a subsection listed in two file groups, created in both groups on a fresh import. Authoring allows this: `_reject_duplicate_criterion()` rejects a second criterion for the same competency and subsection only inside the same group
- a new root created with the file's operator, and an existing root or course-level group whose operator differs from the file's, which is kept and logged, with a null operator treated as OR
- a live bottom-tier group with no criteria, which is never matched

Out of scope:

- showing the author, on the import page, which entries were skipped or differ. The import page shows success or one failure message, and a `tags.csv` error is only logged today, so skips here are logged the same way. Layering does not forbid an author-facing message; a warning channel on the import page would be new work.
- course-final-grade criteria, taxonomy-scoped rule profiles, and creating groups nested below a bottom-tier group through the API
- the tag import's difference logic, and the cleanup of criteria whose subsection tag the course export dropped (#895, #779)
- library copy (#697, #698)
- user-facing docs (#652)

**Files to create and modify**

| File | Change |
| --- | --- |
| src/openedx_learning/applets/cbe/api.py | modified: `import_competency_criteria_for_course`, plus the root and course-level group helper factored out of `_create_leaf_group()` |
| src/openedx_learning/applets/cbe/criteria_file.py | modified: parser |
| tests/openedx_learning/applets/cbe/test_criteria_file_import.py | new |
| docs/openedx_learning/competency_criteria_file.rst | modified: import semantics |
| openedx-platform: xmodule/modulestore/xml_importer.py | modified: `import_competency_criteria` hook and call |
| openedx-platform: xmodule/modulestore/tests/test_xml_importer.py | modified |

**Additional context**

- The work is two PRs. The openedx-core PR goes first and needs #695's `criteria_file.py`. The openedx-platform PR then raises the openedx-core requirement. It can land independently of #695's openedx-platform PR: a criteria file that no importer reads yet is ignored, and an importer that finds no file does nothing.
- #919 lands first. Step 5 loads a run's groups with the subtree-course column #919 adds; without it, the only way to find a run's bottom-tier groups is to walk down through `parent` one level at a time.
- #895 ships with this ticket and #695. It changes a tag re-import to apply only the differences between the course export's tags and the course's tags. As a result, an unchanged re-import removes no criterion, and a criterion is missing at this step only when the author removed it, or when the course export dropped its subsection's tag.
- The lookups use the `archived` fields that #776 adds, so #776 is needed even for a fresh import.
- #717 also changes `_create_leaf_group()`, to reactivate an archived root and to reject an archived course-level group, and makes the duplicate check count only live criteria. The import follows the same three rules, so whichever of the two tickets lands second reuses the other's helper.
- The `CourseRun` row normally exists by this step. `course_published` is sent when the first `bulk_operations` block of the import closes, and `_listen_for_course_publish` in `openedx/core/djangoapps/content/course_overviews/signals.py` creates the row.

</details>
