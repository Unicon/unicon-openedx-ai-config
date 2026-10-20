# [NTH - BE] Include Competency Criteria in Course Export

GitHub: https://github.com/openedx/openedx-core/issues/695 (#695, OPEN)
Cached: 2026-10-20

## User Story
As a course author, when I export a course, I want the export to include the competency mastery rules (competency criteria groups and competency criteria) attached to the course's content, in order to recreate them when the course is imported elsewhere without rebuilding each rule by hand.

## Description
Today, when a course is exported in Open edX, its content tags are included (as `tags.csv`), but the competency criteria groups and competency criteria associated with those tags are not. We should update the export to also write a JSON file describing this course's criteria groups and criteria, identifying content and competencies the same way `tags.csv` does, so that course import (#696) can reconstruct them.

At a high level, the export side does this:

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

## Notes for drafting

Decisions from the pre-handoff check (2026-10-20):

- Taxonomy definitions: not exported. The file carries references only, which is parity with how tag export/import works today: `tags.csv` carries associations (block type, block id, taxonomy `export_id`, tag values) and no taxonomy or tag definitions, and tag import creates neither a Taxonomy nor a Tag. A column for a taxonomy missing on the target, or a value missing from an existing taxonomy, becomes an ObjectTag with no Tag link that stores the value string and the `export_id`, and re-links via `ObjectTag.resync()` if the taxonomy or tag is created later. Nothing is logged. The ticket must state that it aligns to this parity. ADR 0011 (openedx_tagging, Proposed) describes an auto-create on import that is not current behavior. It stays aspirational beyond MVP; do not amend it and do not build for it.
- Competency identity in the file: taxonomy `export_id` plus tag `external_id`, with the tag value included for readability. Content identity: block type plus block id, as `tags.csv` does, so import rebuilds usage keys from the destination course. A course-grade criterion uses the course row.
- Associations: the file references the (block, taxonomy, tag) triple; it does not duplicate the association data. #696 resolves each triple to the ObjectTag that `tags.csv` import recreated. Caveat for #696: `tags.csv` import uses `create_invalid=True`, so an unmatched tag yields an ObjectTag with no Tag.
- What is serialized: scoped to this course. Include the root group (identified by its competency) as the attach point for the course group, with its logic operator, then everything nested under this course's course-level groups: name, ordering, logic operator, competency. Exclude archived rows (matching #694; #716 adds the `archived` field), learner statuses, and history. Database uuids are not exported because they would collide on a same-instance re-import.
- Rule profile: a criterion on the system default exports a reference to the default AND the default's values verbatim at export time. A criterion with an override exports the override verbatim.
- Criterion whose content is not in this export (deleted subsection, block in another course): skip it and log it. A group left empty is left out too (ADR 0002 forbids empty groups).
- File placement, versioning, failure: mirror `tags.csv`. Fixed file name at the archive root beside `tags.csv`, written only when the course has live groups, with an integer schema version that import refuses if newer. A serialization error fails the whole export. Verified: `export_tags_in_csv_file` runs with no try/except in `CourseExportManager.process_extra` (`xmodule/modulestore/xml_exporter.py` ~296-302); the export task catches it, logs, and marks the task FAILED with no tarball.
- Ticket split: one ticket, two PRs, following #694. openedx-core gets a public serializer function on `openedx_learning.api`; openedx-platform gets a hard-coded call in the course exporter's `process_extra`, beside the tags call. The exporter has no plugin hook or openedx-filters filter (verified), so the monolith passes the exported block set into the library function.
- Defaults, not objected to: no UI change (the file appears in the archive only when live criteria exist); no feature flag (tag export has none, and no CBE flag exists in openedx-platform); no permission beyond course export; learner status is never exported; the format gets a short doc in the openedx_learning docs, since archives outlive releases.
- Research for the draft pass: which blocks the `tags.csv` walk includes (unpublished-only blocks, orphans), since that is the block set the monolith hands to the serializer.
