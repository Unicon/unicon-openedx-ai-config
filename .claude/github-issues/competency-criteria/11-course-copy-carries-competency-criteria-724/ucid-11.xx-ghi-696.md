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
  if the criteria file is missing, stop. If it is malformed, log a warning and stop
  for each competency in the file:
    find the competency's Tag on this instance by taxonomy export_id and tag external_id; if it is missing or its taxonomy is not competency-enabled, skip the competency and log it
    find the live root group for that competency, or create it with the file's logic operator
    find this course run's course-level group under that root, or create it
    for each nested group in the file, find the existing group with the same ordering, or create it
    for each criterion in the file:
      find the block's association (ObjectTag) for that Tag; if it is missing, has no Tag, or is archived, skip the criterion and log it
      if the group already has a live criterion on that association, skip it; otherwise create it with its rule (the target's default when the exported values match it, otherwise an override with the exported values)
    leave out any group that ends up with no criteria
```

## Context
- #695 is the corresponding ticket for export

## Acceptance Criteria

Every outcome below can be checked on the destination course's Competency Management page, or through the criteria read path behind it (#681). Anything skipped can also be checked in the operator log. The author sees no new message on the import page, and a skip never fails the import.

The competency criteria file is the one #695 writes, and both tickets describe it in the same words.

```
# Importing into a new course

Scenario: Importing into a new course recreates the file's groups and rules
  Given an archive whose competency criteria file holds a course-level group for a competency with two bottom-tier groups of rules
  And the destination instance has a competency taxonomy and a competency matching the file's identifiers
  When a course author imports the archive into a new course and the import finishes
  Then the destination course has a course-level group for that competency holding two bottom-tier groups
  And each bottom-tier group has the name, position among its siblings, and way of combining its children that the file records
  And the course-level group is named the way the destination names a course-level group an author creates by hand
  And each rule evaluates the destination course's own copy of the content the file names, with a rule on the course itself evaluating the destination course's final grade
  And the import reports success to the author as usual

Scenario: A group nested below a bottom-tier group is recreated at the same depth
  Given the file records a group nested inside a bottom-tier group, with rules of its own
  When the archive is imported into a new course
  Then the destination has an equivalent group nested at the same place, with its own rules and its own way of combining them

Scenario: Imported groups and rules can be edited like any others
  Given a course whose groups and rules were created by an import
  When the author adds a rule to an imported group, and edits and removes an imported rule, on the Competency Management page
  Then each change succeeds the same way it does for groups and rules the author created by hand

Scenario: Imported rules become one more alternative under the competency's existing shared root
  Given the destination instance already has a live shared root for the competency, holding another course's groups
  When an archive with rules for that competency is imported into a new course
  Then the new course's course-level group sits under that shared root as one more alternative way to demonstrate the competency
  And the other course's groups and rules are unchanged
  And no second shared root exists for the competency

Scenario: A missing shared root is created the way the file records
  Given the destination instance has the competency but no criteria groups for it in any course
  When an archive with rules for that competency is imported
  Then the competency has a shared root that combines its alternatives the way the file records

Scenario: A shared root that combines its alternatives differently keeps the destination's way
  Given the destination's live shared root for the competency combines its alternatives differently from the file
  When an archive with rules for that competency is imported into a new course
  Then the shared root keeps the destination's way of combining, and the new course-level group is attached under it
  And the operator log notes the difference

Scenario: An unset way of combining counts as OR
  Given a shared root or group on the destination has no recorded way of combining its children
  And the file records its counterpart as combining them with OR
  When the archive is imported
  Then the import treats the two as combining the same way
  And no difference is logged for them

Scenario: An archived shared root is brought back into use rather than duplicated
  Given the competency's only shared root on the destination is archived, because every course-level group under it was archived
  When an archive with rules for that competency is imported into a new course
  Then the shared root is live again and holds the new course-level group
  And no second shared root exists for the competency
  And the archived course-level groups under it stay archived

Scenario: More than one live shared root skips the competency
  Given the destination has more than one live shared root for the competency
  When an archive with rules for that competency is imported
  Then the destination gets no groups or rules for that competency from the file
  And the operator log names the competency and the reason
  And the other competencies in the file import normally

# How each rule's profile is chosen

Scenario Outline: Each recreated rule keeps the threshold the file records
  Given the file records a rule <as recorded>
  And the rule profile the destination assigns to a new rule for that competency is <destination profile>
  When the archive is imported
  Then the destination has <result>

  Examples:
    | as recorded | destination profile | result |
    | as using a rule profile, with a grade of at least 75% | the default rule profile, requiring a grade of at least 75% | a rule that uses the destination's default rule profile |
    | as using a rule profile, with a grade of at least 75% | the competency taxonomy's own rule profile, requiring a grade of at least 75% | a rule that uses the competency taxonomy's own rule profile |
    | as using a rule profile, with a grade of at least 75% | the default rule profile, requiring a grade of at least 80% | a rule with its own override requiring a grade of at least 75% |
    | as its own override, requiring a grade of at least 85% | the default rule profile, requiring a grade of at least 75% | a rule with its own override requiring a grade of at least 85% |

Scenario: An override the destination cannot accept is skipped and logged
  Given the file records a rule whose own override the destination's rule validation rejects
  When the archive is imported
  Then the destination has no equivalent of that rule
  And its sibling rules are created
  And the operator log names the rule's content, its competency, and the reason

# What is skipped

Scenario Outline: A competency the destination cannot resolve is skipped as a whole
  Given the file names a competency where <condition>
  When a course author imports the archive
  Then the destination gets no groups or rules for that competency from the file
  And no taxonomy, competency, or tag association is created beyond what the content tags import creates
  And the operator log names the competency and the reason
  And the other competencies in the file import normally
  And the import reports success to the author as usual

  Examples:
    | condition |
    | no taxonomy on the destination has the file's taxonomy identifier |
    | the taxonomy exists on the destination but is not a competency taxonomy |
    | the competency taxonomy has no competency with the file's competency identifier |
    | the competency or its taxonomy is archived on the destination |

Scenario Outline: A rule the destination cannot attach is skipped
  Given the file records a rule whose <condition>
  When the archive is imported
  Then the destination has no equivalent of that rule
  And its sibling rules are created
  And the operator log names the rule's content, its competency, and the reason

  Examples:
    | condition |
    | content is not in the destination course |
    | content is not tagged with that competency after the content tags are imported |
    | content is tagged with a value the destination's competency taxonomy does not have, so the tag is not linked to any competency |
    | content's tag association for that competency is archived |
    | content is tagged with a competency of the same value but a different identifier, such as after a rename |

Scenario: A group left with no rules is left out, and nothing is created above it
  Given every rule the file records in one bottom-tier group is skipped
  When the archive is imported
  Then the destination has no equivalent of that group
  And when every group for the competency is left out, the destination gets no course-level group and no new shared root for that competency

# Re-importing into a course run that already has rules

Scenario: Re-importing refills the rules the content tag import removed
  Given a course run was exported
  And learners have since been evaluated against one of its rules and against none of the others
  When the same archive is imported back into that course run and the import finishes
  Then the course run has the groups and rules the archive describes, each exactly once
  And the rule learners were evaluated against is the same rule as before, with its learner statuses unchanged
  And the other rules are present again, each in the group the archive puts it in, with no learner status

Scenario: Rules from different groups are never combined into one group
  Given a course run with two bottom-tier groups for a competency, both created the usual way on the Competency Management page
  And learners have been evaluated against a rule in only one of those groups
  When an archive of that course run is imported back into it
  Then the group holding the evaluated rule gets back only the rules the archive records for that group
  And the other group is recreated as a separate group with its own rules and its own way of combining them

Scenario Outline: A file group with no single clear counterpart in the course run is skipped and logged
  Given the file records a group below the course-level group for a competency
  And the course run <situation>
  When the archive is imported into that course run
  Then no group is created for the file's group, and no rule from it is added to any group in the course run
  And the operator log names the file's group and the reason

  Examples:
    | situation |
    | has a group holding a live rule on some of that group's content and also a live rule on content the file does not record for that group |
    | has more than one live group holding only rules on content the file records for that group |

Scenario: A course run group that is the counterpart of more than one file group receives nothing
  Given the file records two groups below the course-level group for a competency
  And the course run has one live group holding only rules on content that the file records in both of those groups, such as a single rule on content that appears in each
  When the archive is imported into that course run
  Then no group is created for either of the file's groups
  And the course run's group receives no rule from either of them and is otherwise unchanged
  And the operator log names each of the file's groups and the reason

Scenario: An empty group in the course run is never treated as the file's group
  Given the course run has a live group below the course-level group that holds no rules
  When the archive is imported into that course run
  Then the empty group is unchanged and receives no rules from the file
  And each of the file's groups is matched or created as if the empty group were not there

Scenario: A matched group whose name differs is still refilled
  Given a group in the course run is the counterpart of the file's group and combines its rules the same way, but has a different name
  When the archive is imported into that course run
  Then the group's missing rules are added to it, and its name is unchanged
  And no difference is logged for the name

Scenario: A matched group that combines its children differently is left as it is
  Given a group in the course run, at any level, is the counterpart of the file's group but combines its children differently from the file
  When the archive is imported into that course run
  Then the group still combines its children the destination's way
  And nothing the file records in or under that group is added
  And the operator log notes the difference

Scenario: A surviving rule with a different threshold keeps the destination's threshold
  Given a rule in the course run that learners have been evaluated against requires a grade of at least 80%
  And the file records that rule with a grade of at least 75%
  When the archive is imported
  Then the rule still requires a grade of at least 80%, and its learner statuses are unchanged
  And the operator log notes the difference

Scenario: An archived course-level group is reactivated when the file adds a live rule beneath it
  Given the course run's course-level group for a competency is archived
  And it holds an archived bottom-tier group, archived earlier together with its rules, and nothing live
  And the archive's file records a bottom-tier group for that competency whose content matches no archived group in the course run, so that group has no counterpart there
  When the archive is imported into that course run
  Then the course-level group is live again
  And it holds a new bottom-tier group with the rules the file records for that group
  And no second course-level group exists for that competency in the course run
  And the earlier archived bottom-tier group and its rules stay archived
  And the operator log notes that the course-level group was reactivated

Scenario: A course-level group archived together with all its rules stays archived when the file's groups match those archived rules
  Given the course run's course-level group for a competency was archived through #675, together with every group and rule under it
  And every bottom-tier group under it holds a rule that learners were evaluated against
  And an archive of the course run was taken before that archiving
  When that archive is imported into the course run
  Then nothing new is created for that competency in the course run
  And the course-level group and everything under it stay archived
  And the operator log names each skipped group and the reason

Scenario Outline: The import never brings back an archived rule or group
  Given the course run has <archived item>
  When the archive is imported into that course run
  Then <outcome>
  And the archived item is unchanged
  And the operator log names the skipped item and the reason

  Examples:
    | archived item | outcome |
    | a group that is the counterpart of the file's group and holds an archived rule on content the file records as a live rule in that group | the group gets no new live rule on that content, and its other missing rules are added |
    | an archived bottom-tier group holding rules only on content the file records for one of the file's groups | no group is created for that file group, and no rule from it is added anywhere |

Scenario: Graded groups and rules the archive does not describe are left alone
  Given the course run has a group holding a rule learners were evaluated against, and the archive does not describe that group
  When the archive is imported
  Then that group and rule are unchanged, and so are their learner statuses

Scenario: Importing the same archive again changes nothing further
  Given an archive was imported into a course run
  When the same archive is imported into that course run again
  Then the course run has the same groups and rules as after the first import, each exactly once

Scenario: Importing beside a live source course on the same instance leaves the source unchanged
  Given an archive exported from a course on this same instance, whose rules are still live
  When the archive is imported into a different, new course on that instance
  Then the new course has its own course-level group under the competency's shared root, as an alternative to the source course's group
  And the source course's groups, rules, and learner statuses are unchanged
  And changing the new course's rules leaves the source course's rules unchanged

# Learner status

Scenario: The import never touches learner status
  Given learners have mastery statuses in the destination course run
  When an archive is imported into it
  Then every existing learner status is unchanged, and the import creates no learner status
  And each rule the import created has no learner status until the next grade for its content is recorded

# File problems, failure, and permission

Scenario: An archive without a competency criteria file imports as it does today
  Given an archive with no competency criteria file, such as one exported from an instance that does not write it
  When the archive is imported
  Then the import succeeds as it does today
  And nothing about competency criteria is logged

Scenario Outline: A competency criteria file the destination cannot use is skipped whole
  Given an archive whose competency criteria file <problem>
  When the archive is imported
  Then the import succeeds and the author sees no new message
  And the destination gets no groups or rules from the file
  And the operator log has a warning saying the file was skipped and why

  Examples:
    | problem |
    | cannot be read |
    | is in a newer format version than this instance supports |
    | is readable but has an entry that does not follow its format version, such as a rule with no content |

Scenario: An unexpected failure part way through leaves no partly recreated groups or rules
  Given an archive with rules for several competencies
  And an unexpected error happens after some of the file's groups and rules have been created
  When the archive is imported
  Then the destination course has no partly recreated groups or rules from the file
  And the author sees the import's existing generic failure message
  And an operator can see the underlying error

Scenario: Recreating the rules needs no permission beyond importing the course
  Given a course author permitted to import the course but holding no permission to author competency criteria
  When the author imports the archive
  Then the file's rules are recreated in full, and none are dropped for lack of permission
```

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done.

**Summary**

openedx-core gets one public function that reads the file #695 writes and recreates its criteria for the destination course run, inside one transaction. The function first plans the whole tree in memory, matching each file group to an existing destination group by the content its rules evaluate, then writes only what is new and holds at least one rule. It never edits a surviving group or rule, with one exception: it reactivates an archived shared root or course-level group when it adds a live rule beneath it. openedx-platform calls the function from the course importer right after `tags.csv` has been imported.

**Approach**

1. **openedx-platform call site.** Add `import_competency_criteria(data_path, dest_id)` to `ImportManager` in `xmodule/modulestore/xml_importer.py` as a method that does nothing, and implement it on `CourseImportManager`.
   - Call it from `run_imports` right after the `import_tags` block and before `post_course_import`, outside that block's `try/except`: the handler logs `FileNotFoundError` and `ValueError` at info level and would hide an unexpected error. Studio's import task and the `import` management command both reach `run_imports`. A `COURSE_IMPORT_COMPLETED` receiver cannot do this work, because the event carries only the course key and not the archive path.
   - The method returns early when `COMPETENCY_CRITERIA_FILE_NAME` is absent from the archive.
   - Otherwise it makes sure the destination `CourseRun` row exists, the way #694 does: call `openedx_catalog.api.get_course_run()`, and when there is no row, call `create_course_run_for_modulestore_course_with()` with the course's `display_name`. The publish signal that normally creates the row is sent robustly, so a failure in its handler would go unnoticed.
   - It then passes the file's raw bytes to `openedx_learning.api.import_competency_criteria_for_course(dest_id, contents)`.
2. **openedx-core public function.** Add `import_competency_criteria_for_course(course_key: CourseKey, contents: bytes) -> CompetencyCriteriaImportResult` to `cbe/api.py`, marked UNSTABLE like #695's export function. It returns the counts of groups created, criteria created, and entries skipped as a frozen dataclass in `data.py`, which the importer logs as one summary line. It raises `CourseRun.DoesNotExist` when the run is missing.
3. **Parse before writing anything.** `cbe/criteria_file.py`, the module #695 creates, parses and validates the whole file. The function skips the whole file with a warning and returns zero counts when:
   - the file is not readable JSON (catch `ValueError`, which covers decode errors)
   - its `version` is newer than this instance supports
   - any entry is structurally invalid: an unknown `logic_operator` or `source`, a missing key, a criterion with no block, a block that does not form a usage key, or a competency listed twice

   Rule payloads are validated per rule in step 5.
4. **Resolve competencies, then lock.** Inside one `transaction.atomic()`, find each taxonomy with `openedx_tagging.api.get_taxonomy_by_export_id()`, check it with `is_competency_taxonomy()`, then find the Tag with the taxonomy's `tag_for_external_id()` method. Skip the competency and log when the taxonomy or the Tag is missing or archived, or when the taxonomy is not a competency taxonomy. Lock the resolved Tag rows with `select_for_update()` in primary-key order. Authoring takes the same lock in `associate_competency_criterion()`, and the fixed order keeps two concurrent imports from deadlocking.
5. **Plan in memory first.** Whether a root is reactivated, a course-level group is created, or a nested group is kept depends on whether any rule ends up beneath it, and ADR 0002 forbids persisting an empty group. A null `logic_operator` equals OR at every level.
   - **Root.** Look for the Tag's groups with `parent=None`, archived ones included. When there is more than one, skip the competency and log. When the root's operator differs from the file's, keep the destination's operator, log the difference, and continue.
   - **Course-level group.** Look for the Tag's group for this run under that root. When its operator differs from the file's, leave it as it is, add nothing under it, and log. The root and the course-level group are the only rows the import ever reactivates, and only when the plan adds a live rule beneath them. Reactivation matters for a re-import whose tag step deleted the last live rule, after which #895 archived the emptied course-level group: authoring cannot add under an archived course-level group once #717 lands, so without reactivation that rule would be lost for good.
   - **Nested groups, with the same rule at every depth.** The candidates for a file group are the existing child groups of its matched parent that hold at least one rule somewhere beneath them; a candidate with no rules is ignored. Matching ignores `ordering`.
     - A live candidate matches when every live rule beneath it evaluates content the file records under that file group. An archived candidate matches when every rule beneath it does.
     - When exactly one live candidate matches, refill it. A different name is ignored. A different operator means nothing is added in or under that group, and the difference is logged.
     - When exactly one archived candidate matches, skip the file group and log.
     - When nothing matches, plan a new group with the file's name, ordering, and operator, and with `course=None`, as authoring does.
     - When a candidate partly overlaps the file group, when more than one candidate matches, or when one candidate is matched by more than one file group, skip the file group or groups and log.
   - **Criteria.** Rebuild each object id with `course_key.make_usage_key(block_type, block_id)`, or use the course key itself when `block_type` is `"course"`. Look for the live ObjectTag for that object, the Tag's taxonomy, and that Tag. Criteria the file lists directly on the course-level group are handled the same way, with the course-level group as their group.
     - When the ObjectTag is missing, archived, or tied to a different Tag, skip the criterion and log, with no fallback to matching by value: an unmatched `create_invalid` ObjectTag has no Tag at all, and a renamed value can tie it to a different Tag.
     - In a matched group, an archived rule on the same association means the criterion is skipped and logged. A live rule on the same association is left as it is, and is logged only when its `_effective_rule()` differs from the file's.
   - **Rule.** Use an override verbatim. For `source: "rule_profile"`, use the profile the create path would pick when that profile's `rule_type` and `rule_payload` equal the file's; otherwise use an override carrying the file's values. Factor `create_competency_criterion()`'s lookup (taxonomy-scoped profile, else system default) into one private helper that both call. Validate every planned override with `validate_rule_payload()`, and skip and log any that are rejected, so that pruning empty groups sees the final set.
6. **Write.**
   - Reactivate planned containers with `save()` rather than a queryset update, so that simple-history records the change.
   - Create groups parent-first with `objects.create()`, because each child needs its parent's primary key and `bulk_create` does not return keys on MySQL.
   - A new root or course-level group takes the name authoring derives (factor the name logic out of `_create_leaf_group()`), because the name in the file is the source course's.
   - Create criteria last with `simple_history.utils.bulk_create_with_history`. That function skips `save()` and its `full_clean()`, which is why step 5 validates.
   - The import never creates, changes, or deletes learner status, Tags, or ObjectTags.
7. **Docs.** Add these import semantics to #695's format page.

Tests must cover:
- Fresh imports: into a course on another instance, with and without an existing root; into a new run on the same instance next to the live source course.
- Re-import after the tag import has deleted ungraded rules: rules are refilled into the matched surviving groups, the survivors are untouched, and a repeated import gives the same result.
- The #895 sequence: the course-level group is reactivated and refilled.
- A deliberately archived branch (#675): the course-level group stays archived.
- Every skip: a missing or non-competency taxonomy; a missing or archived Tag; a missing, archived, Tag-less, or renamed ObjectTag; an archived rule; a match to an archived sibling; a partial overlap; an ambiguous match; a differing operator at each level; an override the destination rejects.
- Rule profiles: matching values assign the profile, differing values become an override, and a live taxonomy-scoped profile on the destination is the one compared.
- Bad files: a malformed file or a newer version writes nothing, and the course import still succeeds.
- Failure and depth: a failure mid-write rolls everything back, and nesting deeper than three levels works.
- openedx-platform: a missing file does nothing, a missing `CourseRun` is created, and an unexpected error fails the import task.

Out of scope:
- an association that stays archived because the import no longer carries its tag (the guardrail series)
- the tag-import delete path (#779) and the pruning of emptied groups (#895)
- library copy (#697, #698)
- user-facing docs (#652)

**Files to create and modify**

| File | Change |
| --- | --- |
| src/openedx_learning/applets/cbe/api.py | modified: import_competency_criteria_for_course, shared rule-profile and group-name helpers |
| src/openedx_learning/applets/cbe/criteria_file.py | modified: parser and validation |
| src/openedx_learning/applets/cbe/data.py | modified: CompetencyCriteriaImportResult |
| tests/openedx_learning/applets/cbe/test_criteria_file_import.py | new |
| docs/openedx_learning/competency_criteria_file.rst | modified: import semantics |
| openedx-platform: xmodule/modulestore/xml_importer.py | modified: import_competency_criteria hook and call |
| openedx-platform: xmodule/modulestore/tests/test_xml_importer.py | modified |

**Additional context**

- The work is two PRs. The openedx-core PR goes first and needs #695's `criteria_file.py`. The openedx-platform PR then raises the openedx-core requirement, and should merge together with #695's openedx-platform PR.
- The lookups use the `archived` fields from #776, so #776 is needed even for a fresh import.
- The re-import case also depends on #778 and #779, because without them tag import raises `ProtectedError` before this code runs, and on #895, which prunes the groups that tag import empties.
- The `CourseRun` row normally exists by this step: `course_published` is sent when the first `bulk_operations` block of the import closes, and `_listen_for_course_publish` in `openedx/core/djangoapps/content/course_overviews/signals.py` creates the row.
- Prior art: #694 for creation order and copying live rows only; `associate_competency_criterion()` and `_create_leaf_group()` for the Tag row lock and the derived names; #717 for reactivating an archived root.

</details>

## Open Questions

- (architect, final review) Confirm the group matching rule for re-import. Every group has `ordering` 0 because no create path sets it, so the match by ordering that the Description's pseudo code states would match every file group to every surviving group. The drafted rule in Approach step 5 matches on content instead: a destination sibling holding at least one rule matches a file group when every live rule beneath it is on content the file records for that group; an archived sibling matches when every rule beneath it is, and the file group is then skipped; an empty sibling never matches; a partial overlap, more than one matching sibling, or one sibling matched by more than one file group skips the file group or groups and logs. Alternatives: pair siblings positionally in ordering-then-creation order, or skip the refill for any competency whose course-level group survives.
- (architect, final review) Confirm how archived containers are handled. The drafted rule reactivates an archived shared root, and an archived course-level group for this run, only when the import adds a live rule beneath it, and never un-archives a nested group or a rule. The alternative is to skip the competency whenever its course-level group is archived. In the re-import sequence where #895 archives an emptied course-level group, that alternative loses the deleted rule for good, because authoring cannot add under an archived course-level group (#717). The drafted rule diverges from #717's authoring rule, so #717 may need the same decision. It also means an author's #675 archive can come partly undone: the import cannot tell a #675 archive from the automatic archive #895 makes, so re-importing an archive taken before the #675 archive recreates the ungraded part of that branch live (tag import deletes the ungraded archived rules, #895 removes their emptied groups, the file's groups then have no counterpart and are created, and the course-level group is reactivated). Recommended: accept this and state it in the format doc and in #652.
- (architect, final review) Should this ticket be split? As drafted it is about 3.5 to 4 developer-days. The seam is whether the destination run already has a course-level group for the competency. Fresh import stays here (about 2 days) and skips a competency whose course-level group already exists. The re-import merge (content-anchored matching, survivor comparison, archived siblings and rules, course-level group reactivation; about 1.5 to 2 days, openedx-core only) becomes a companion ticket whose dependencies are exactly the re-import ones: #776, #778, #779, and #895.
