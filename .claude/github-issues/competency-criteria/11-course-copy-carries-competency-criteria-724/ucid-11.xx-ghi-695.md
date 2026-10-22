# [NTH - BE] Include Competency Criteria in Course Export

GitHub: https://github.com/openedx/openedx-core/issues/695 (#695, OPEN)
Cached: 2026-10-20

## User Story
As a course author, when I export a course, I want the export to include the competency mastery rules (competency criteria groups and competency criteria) attached to the course's content, in order to recreate them when the course is imported elsewhere without rebuilding each rule by hand.

## Description
Today, when a course is exported in Open edX, its content tags are included (as `tags.csv`), but the competency criteria groups and competency criteria associated with those tags are not. We should update the export to also write a JSON file describing this course's criteria groups and criteria, identifying content and competencies the same way `tags.csv` does, so that course import (#696) can reconstruct them.

At a high level, the export does this:

```
when a course is exported, right after tags.csv is written:
  for each competency that has a live course-level criteria group in this course:
    record the root group's competency (taxonomy export_id, tag external_id, tag value) and its logic operator
    walk the course-level group and every nested group, recording name, ordering, and logic operator
    for each criterion in those groups:
      skip it if its block is not part of this export (for example, a deleted subsection), and log it
      record its block (type and id) and its rule: a reference to the system default plus the default's values, or the override verbatim
    leave out any group that ends up with no criteria
  if anything was recorded, write it as one JSON file beside tags.csv
```

## Context
- #696 is the corresponding ticket for import

## Acceptance Criteria

Every outcome below can be checked by exporting a course in Studio and reading the downloaded archive. Anything left out with a logged reason can also be checked in the operator log. The competency criteria file is the one #696 reads, and both tickets describe it in the same words.

```
# What the export writes

Scenario: A course with mastery rules exports a competency criteria file beside the content tags file
  Given a course whose content is tagged with a competency and governed by live mastery rules
  When a course author exports the course
  Then the export succeeds and the author downloads the archive as usual, with no change to the export page
  And the archive contains a competency criteria file at its top level, beside the content tags file
  And the file records its format version

Scenario: The file identifies each competency the way taxonomy export and import already do
  Given a course with live mastery rules for a competency
  When a course author exports the course
  Then the file identifies the competency by the identifiers that taxonomy export and import already use for its taxonomy and for the competency itself, with the competency's value as a readable label
  And the file records how the competency's shared root combines its alternatives
  And the file contains no definition of the taxonomy or of any competency

Scenario: The file records this course's criteria groups at any depth
  Given a course-level group for a competency holding two bottom-tier groups, one requiring all of its rules and one requiring any of them
  And a group nested inside one of those bottom-tier groups, with rules of its own
  When a course author exports the course
  Then the file records this course's criteria groups for the competency at any depth, each with its name, its position among its siblings, and how it combines its children
  And each group appears under its own parent group, with its own rules

Scenario: The file records the content each rule evaluates the way the content tags file identifies it
  Given a course with one live mastery rule on a graded subsection and one on the course's final grade
  When a course author exports the course
  Then the file records the content each rule evaluates, identified by block type and block ID the same way the content tags file identifies that content
  And the rule on the final grade identifies the course itself, the same way the content tags file identifies the course

Scenario: Only the exported course's groups and rules are written
  Given a course with live mastery rules for two competencies
  And the shared root of one of those competencies also holds criteria groups for another course
  When a course author exports the course
  Then the file contains both competencies, each with only its own groups and rules from the exported course
  And the file contains nothing from the other course's groups

# How each rule is recorded

Scenario Outline: Each rule is recorded with the rule in force at the time of the export
  Given a live mastery rule that <rule source>
  When a course author exports the course
  Then the file records <recorded rule>
  And the recorded rule is the one in force at the time of the export

  Examples:
    | rule source | recorded rule |
    | uses the default rule profile, which requires a grade of at least 75% | the rule as using a rule profile, together with that profile's rule, a grade of at least 75% |
    | uses its competency taxonomy's own rule profile, which requires a grade of at least 70% | the rule as using a rule profile, together with that profile's rule, a grade of at least 70% |
    | uses a former default rule profile that has since been archived, which requires a grade of at least 60% | the rule as using a rule profile, together with that profile's rule, a grade of at least 60% |
    | has its own override requiring a grade of at least 85% | the rule's own override, a grade of at least 85%, exactly, and not as using a rule profile |

# What the export leaves out

Scenario Outline: Archived groups and rules are left out
  Given a course whose mastery rules include <archived item>
  When a course author exports the course
  Then the file contains no equivalent of <archived item> or of anything recorded under it
  And every live group and rule outside it is recorded

  Examples:
    | archived item |
    | an archived mastery rule |
    | an archived bottom-tier group with rules still recorded under it |
    | an archived course-level group with groups and rules still recorded under it |

Scenario Outline: A live rule that cannot be carried is left out and logged
  Given a live mastery rule that <condition>
  When a course author exports the course
  Then the file contains no equivalent of that rule
  And the operator log names the rule's competency, its content, and the reason it was left out
  And the rule's live siblings are recorded

  Examples:
    | condition |
    | evaluates content that is not part of the export, such as a subsection deleted from the course after learners were evaluated against it |
    | evaluates content whose tag for that competency has been archived |
    | belongs to a competency that has been archived |
    | belongs to a competency whose taxonomy has been archived |

Scenario: A group left with no rules is left out
  Given a bottom-tier group whose only live rule is left out with a logged reason
  When a course author exports the course
  Then the file contains no equivalent of that group
  And when that leaves the competency with nothing to record in this course, the competency is absent from the file

Scenario: Learner status, history, and internal identifiers are never exported
  Given learners have mastery statuses against the course's rules, and the rules and groups have edit history
  When a course author exports the course
  Then the file contains no learner, no learner status, and no edit history
  And the file contains no identifier of the source instance's own group or rule records

Scenario Outline: No competency criteria file is written when there is nothing to record
  Given <course state>
  When a course author exports the course
  Then the export succeeds as usual
  And the content tags file is exported exactly as it is today
  And the archive contains no competency criteria file

  Examples:
    | course state |
    | a course with no mastery rules |
    | a course tagged only with taxonomies that are not competency taxonomies |
    | a course whose every mastery rule is archived |
    | a course whose every live mastery rule is left out with a logged reason |

# Failure and permission

Scenario: A failure writing the competency criteria file fails the export
  Given a course with live mastery rules
  And writing the competency criteria file fails
  When a course author exports the course
  Then the export fails the same way the platform reports any other export failure
  And no archive is offered for download
  And an operator can see the underlying error

Scenario: Exporting the rules needs no permission beyond exporting the course
  Given a course author who may export the course but holds no permission to author competency criteria
  When the author exports the course
  Then the competency criteria file contains the course's live rules in full
```

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done.

**Summary**

openedx-core gets one public function that turns a course run's live competency criteria into the text of a versioned JSON file holding only references that mean the same thing on another instance. openedx-platform's course exporter calls that function right after writing `tags.csv`, passes it the set of blocks the `tags.csv` walk covered, and writes the result beside `tags.csv`. This ticket defines and documents the file that #696 reads.

**Approach**

1. **openedx-platform, block set.** `export_tags_in_csv_file` in `openedx/core/djangoapps/content_tagging/api.py` returns the set of object id strings for the rows it wrote: the course key, plus the full usage key of every block in its walk, collected during that same walk. The walk starts at the course root and follows children, so orphan blocks are not in it. Course and subsection blocks are direct-only categories with no draft-only state, and draft-only units are exported under `drafts/`, so a block in the walk is in the exported OLX. This set is what "part of this export" means.
2. **openedx-platform, call site.** In `CourseExportManager.process_extra` (`xmodule/modulestore/xml_exporter.py`), inside the existing `if tags_count or course_tags_count:` block, pass the course key and that set to `openedx_learning.api.export_competency_criteria_for_course()`. The call belongs inside that block because every criterion points at a tag association, so a course with no tags holds no criteria. When the function returns text, write it to `COMPETENCY_CRITERIA_FILE_NAME` (`competency_criteria.json`) in `export_fs`, beside `tags.csv`. Add no try/except: a failure fails the export, the same way a `tags.csv` failure does.
3. **openedx-core, public surface.** Add `export_competency_criteria_for_course(course_key: CourseKey, object_ids: set[str]) -> str | None` and `COMPETENCY_CRITERIA_FILE_NAME` to `cbe/api.py`'s `__all__`, so `openedx_learning.api` re-exports them. Mark the function UNSTABLE like the rest of the CBE family; the durable contract is the file format, governed by its `version`. Put the format itself (the version constant, the serializer, and the parser that #696 adds) in a new private module, `cbe/criteria_file.py`.
4. **What is read.** Resolve the run with `openedx_catalog.api.get_course_run()`, and return `None` when it does not exist. Start from `CompetencyCriteriaGroup.objects.filter(course=run, archived=False)`, then walk the live child groups through `parent`, one level at a time, until none remain. Bottom-tier groups have `course=None` in code (ADR 0002 Decision 2 says every group in a course-scoped subtree carries `course_id`; this export follows the code), so a filter on the course would miss them. Load the live criteria in those groups together with their `object_tag` and `rule_profile`.
5. **What is left out, each with a log line:**
   - a competency whose Tag or taxonomy is archived
   - a criterion whose ObjectTag is archived
   - a criterion whose `object_tag.object_id` is not in `object_ids`, such as a deleted or orphaned block

   Then, working bottom-up, drop every group left with no criteria and no child groups, and drop a competency whose course-level group ends up empty. Return `None` when nothing remains, so no file is written.
6. **Content.** Record `block_type` and the local `block_id` from the usage key, which is what `tags.csv` writes in its ID column. A course-grade criterion (its object id is the course key) records `block_type: "course"` and the source course key string as its `block_id`; import ignores that `block_id` and uses the destination course key, the same way `tags.csv` import treats its course row.
7. **Rule.** When `rule_profile_id` is set, record `source: "rule_profile"` with that profile's current `rule_type` and `rule_payload`, whichever profile it is: the system default, a taxonomy-scoped profile, or a former default that has since been archived. Otherwise, record `source: "override"` with the override verbatim. `_effective_rule()` already returns the pair.
8. **Output.** Sort competencies by taxonomy `export_id` and then tag `external_id`, sibling groups by `ordering` and then `id`, and criteria by `id`. Serialize with `json.dumps(..., indent=2, sort_keys=True)`, so re-exporting unchanged criteria produces an identical file. Never write a database id or uuid, because a uuid would collide on a same-instance re-import. Every key below is required. `logic_operator` is `"AND"`, `"OR"`, or `null`. `tag_value` and the root and course-level group names are there for readers only; import restores nested group names.

```json
{
  "version": 1,
  "competencies": [
    {
      "taxonomy_export_id": "nursing-competencies",
      "tag_external_id": "patient-safety",
      "tag_value": "Patient Safety",
      "root_logic_operator": "OR",
      "course_group": {
        "name": "Patient Safety (Intro to Nursing)",
        "ordering": 0,
        "logic_operator": null,
        "criteria": [],
        "groups": [
          {
            "name": "",
            "ordering": 0,
            "logic_operator": "OR",
            "criteria": [
              {
                "block_type": "sequential",
                "block_id": "4f6c1a",
                "rule": {"source": "rule_profile", "rule_type": "Grade",
                         "rule_payload": {"op": "gte", "value": 0.75, "scale": "percent"}}
              },
              {
                "block_type": "sequential",
                "block_id": "9b2e77",
                "rule": {"source": "override", "rule_type": "Grade",
                         "rule_payload": {"op": "gte", "value": 0.85, "scale": "percent"}}
              }
            ],
            "groups": []
          }
        ]
      }
    }
  ]
}
```

9. **Format doc.** Add `docs/openedx_learning/competency_criteria_file.rst` and link it from `docs/openedx_learning/index.rst`. It documents every field, states the parity with `tags.csv` (no taxonomy or tag definitions travel in the archive, and tag import creates neither), and states the version policy: bump `version` for any change an older importer would misread, and every importer reads every older version and skips a newer one whole.

Tests must cover:

- each archived row left out: a group, a criterion, an ObjectTag, a Tag, and a taxonomy
- a criterion on a block that is not in `object_ids`
- emptied groups dropped, up to the whole competency, and no file written when nothing remains
- a rule on the system default, on a taxonomy-scoped profile, on an archived profile, and an override
- a course-grade criterion
- nesting deeper than three levels
- two runs of the same course, each exporting only its own groups

Out of scope:

- import, including the import half of the format doc (#696)
- library export (#697)
- user-facing docs (#652)
- learner status and history, which are never exported

**Files to create and modify**

| File | Change |
| --- | --- |
| src/openedx_learning/applets/cbe/criteria_file.py | new: format version, file name, serializer |
| src/openedx_learning/applets/cbe/api.py | modified: export `export_competency_criteria_for_course` and `COMPETENCY_CRITERIA_FILE_NAME` |
| tests/openedx_learning/applets/cbe/test_criteria_file_export.py | new |
| docs/openedx_learning/competency_criteria_file.rst | new |
| docs/openedx_learning/index.rst | modified |
| openedx-platform: openedx/core/djangoapps/content_tagging/api.py | modified: `export_tags_in_csv_file` returns the exported object ids |
| openedx-platform: xmodule/modulestore/xml_exporter.py | modified: `CourseExportManager.process_extra` writes the file |
| openedx-platform: openedx/core/djangoapps/content_tagging/tests/test_api.py | modified |
| openedx-platform: xmodule/modulestore/tests/test_cross_modulestore_import_export.py | modified |

**Additional context**

- The work is two PRs. The openedx-core PR goes first; the openedx-platform PR then raises the openedx-core requirement to a version that contains the function. Merge the openedx-platform PRs for this ticket and #696 together, because #895 relies on re-import recreating the rules that a tag re-import deletes.
- The archived filters on Tag, Taxonomy, and ObjectTag use the fields #776 adds.
- ADR 0011 (openedx_tagging, Proposed) describes creating taxonomies automatically on import. This format makes no provision for it.
- Prior art: `generate_csv_rows` in `content_tagging/api.py` and `helpers/objecttag_export_helpers.py` for the `tags.csv` walk, and `_export_drafts` in `xml_exporter.py` for how draft-only units are exported.

</details>
