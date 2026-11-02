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
      skip it if its subsection is not part of this export (for example, a subsection deleted from the course)
      record its subsection (block type and block ID) and its rule: a reference to the system default plus the default's values, or the override verbatim
    leave out any group that ends up with no criteria
  if anything was recorded, write it as one JSON file beside tags.csv
```

## Context
- #696 is the corresponding ticket for import

## Acceptance Criteria

Every outcome below can be checked by exporting a course in Studio and reading the downloaded archive.

Terms used in the scenarios:

- A **mastery rule** is a competency criterion. A **group** is a competency criteria group. A competency's groups form a tree: one shared root, one course-level group per course, and bottom-tier groups under the course-level group that hold the rules.
- For MVP every mastery rule evaluates a subsection.

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

Scenario: The file records this course's criteria groups
  Given a course-level group for a competency holding two bottom-tier groups, one requiring all of its rules and one requiring any of them
  When a course author exports the course
  Then the file records the course-level group and both bottom-tier groups, each with its name, its position among its siblings, and how it combines its children
  And each bottom-tier group appears under the course-level group, with its own rules

Scenario: The file records the subsection each rule evaluates the way the content tags file identifies it
  Given a course with live mastery rules on two graded subsections
  When a course author exports the course
  Then the file records the subsection each rule evaluates, identified by block type and block ID the same way the content tags file identifies that subsection

Scenario: Only the exported course run's groups and rules are written
  Given a course run with live mastery rules for two competencies
  And another run of the same course with live mastery rules of its own for one of those competencies, under the same shared root
  When a course author exports the first run
  Then the file contains both competencies, each with only its own groups and rules from the exported run
  And the file contains nothing from the other run's groups

# How each rule is recorded

Scenario Outline: Each rule is recorded with the rule in force at the time of the export
  Given a live mastery rule that <rule source>
  When a course author exports the course
  Then the file records <recorded rule>
  And the recorded rule is the one in force at the time of the export

  Examples:
    | rule source | recorded rule |
    | uses the default rule profile, which requires a grade of at least 75% | the rule as using a rule profile, together with that profile's rule, a grade of at least 75% |
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

# Failure and permission

Scenario: A failure writing the competency criteria file fails the export
  Given a course with live mastery rules
  And writing the competency criteria file fails
  When a course author exports the course
  Then the export fails the same way it fails today when writing the content tags file fails, and the author sees the export page's usual failure message
  And an operator can see the underlying error

Scenario: A course author who can export the course can export its mastery rules
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
2. **openedx-platform, call site.** In `CourseExportManager.process_extra` (`xmodule/modulestore/xml_exporter.py`), inside the existing `if tags_count or course_tags_count:` block, pass the course key and that set to `openedx_learning.api.export_competency_criteria_for_course()`. The call belongs inside that block because every criterion points at a tag association, so a course with no tags holds no criteria. When the function returns text, write it to `COMPETENCY_CRITERIA_FILE_NAME` (`competency_criteria.json`) in `export_fs`, beside `tags.csv`. Add no try/except: a failure fails the export, the same way a `tags.csv` failure does, because the `export_tags_in_csv_file` call in `process_extra` has no try/except of its own.
3. **openedx-core, public surface.** Add `export_competency_criteria_for_course(course_key: CourseKey, object_ids: set[str]) -> str | None` and `COMPETENCY_CRITERIA_FILE_NAME` to `cbe/api.py`'s `__all__`, so `openedx_learning.api` re-exports them. Leave the function without an UNSTABLE marker unless the implementer sees a reason for one; the durable contract is the file format, governed by its `version`. Put the format itself (the version constant, the serializer, and the parser that #696 adds) in a new private module, `cbe/criteria_file.py`.
4. **What is read.** Resolve the run with `openedx_catalog.api.get_course_run()`, and return `None` when it does not exist. Load the live course-level groups with `CompetencyCriteriaGroup.objects.filter(course=run, archived=False)`, then the live groups below them one level at a time through `parent`, until none remain. Only the course-level group carries `course` (ADR 0002 Decision 2, as amended on 2026-10-22); the groups below it have `course=None`, so a filter on the course alone would miss them. #919 (option C) adds a column to every group in a course-scoped subtree naming that subtree's course; once it lands, one filter on that column replaces the walk. Load the live criteria in those groups in one query, with `select_related` on `object_tag`, its `tag` and `taxonomy`, and `rule_profile`, so the archived checks and the rule read no further rows per criterion.
5. **Stale criteria are left out, each with one log line** naming the competency, the content, and the reason. A stale criterion is a live one whose subsection or competency is gone or archived. #895 archives such a criterion when the change happens, so the export meets one only when that cleanup was bypassed, which is why no Acceptance Criteria scenario covers these cases and the tests below do. Log at info level, or whatever level the implementer prefers below warning: each of these is an expected state of a course's data, and the export page cannot show it to the author.
   - a competency whose Tag or taxonomy is archived
   - a criterion whose ObjectTag is archived
   - a criterion whose `object_tag.object_id` is not in `object_ids`, such as a deleted or orphaned block

   Then, working bottom-up, drop every group left with no criteria and no child groups, and drop a competency whose course-level group ends up empty. Return `None` when nothing remains, so no file is written.
6. **Content.** Record `block_type` and the local `block_id` from the usage key, which is what `tags.csv` writes in its ID column. For MVP every criterion's `object_id` is a subsection usage key.
7. **Rule.** When `rule_profile_id` is set, record `source: "rule_profile"` with that profile's current `rule_type` and `rule_payload`. Otherwise, record `source: "override"` with the override verbatim. `_effective_rule()` already returns the pair.
8. **Output.** Sort competencies by taxonomy `export_id` and then tag `external_id`, sibling groups by `ordering` and then `id`, and criteria by `id`. Serialize with `json.dumps(..., indent=2, sort_keys=True)`, so re-exporting unchanged criteria produces an identical file. Never write a database id or uuid, because a uuid would collide on a same-instance re-import. A group's `groups` key is present only when it has child groups, and its `criteria` key only when it has criteria; every other key below is required. `logic_operator` is `"AND"`, `"OR"`, or `null`. `tag_value` and the root and course-level group names are there for readers only; import restores nested group names. `ordering` is recorded as stored; nothing reads it today and the field may be removed from the model later, so a reader of the file must not depend on it beyond restoring the value.

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
            ]
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
- each kind of stale criterion left out while its live siblings are kept: one whose block is not in `object_ids`, one whose ObjectTag is archived while its Tag is live, one whose Tag is archived, and one whose taxonomy is archived
- a bottom-tier group whose only criterion is stale dropped while a sibling group is kept, a competency whose every criterion in the course is stale dropped while another competency is kept, and no file written when nothing remains
- a rule on the system default profile, and an override
- a group nested below a bottom-tier group, created directly through the model since no API creates one, serialized under its parent with its own criteria
- two runs of the same course, each exporting only its own groups

Out of scope:

- import, including the import half of the format doc (#696)
- library export (#697)
- user-facing docs (#652)
- showing the author, on the export page, which rules the export left out
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

- The work is two PRs. The openedx-core PR goes first; the openedx-platform PR then raises the openedx-core requirement to a version that contains the function. The openedx-platform PR can land independently of #696's: a criteria file that no importer reads yet is ignored. #895 keeps a re-import's existing rules in place, so nothing depends on #696 recreating them.
- The archived filters on Tag, Taxonomy, and ObjectTag use the fields #776 adds. #776 is open, so until it merges those three left-out cases cannot occur and their tests wait on it.
- ADR 0011 (openedx_tagging, Proposed) describes creating taxonomies automatically on import. This format makes no provision for it.
- Prior art: `generate_csv_rows` in `content_tagging/api.py` and `helpers/objecttag_export_helpers.py` for the `tags.csv` walk, and `_export_drafts` in `xml_exporter.py` for how draft-only units are exported.

</details>
