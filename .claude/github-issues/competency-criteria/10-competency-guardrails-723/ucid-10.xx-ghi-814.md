# [FE] Treat an archived tag as no longer part of its taxonomy on create, import, and export

GitHub: https://github.com/openedx/openedx-core/issues/814 (#814, OPEN)
Cached: 2026-09-21

## User Story

As a platform administrator, I want a tag value that belongs to an archived tag to explain why it’s unavailable rather than failing with a generic duplicate error, in order to understand what happened and pick a value I can actually use.

## Acceptance Criteria

**This ticket covers three surfaces, not one:** adding a tag interactively through the Taxonomy Editing UI (and the API/model method it calls), importing a file, and exporting a taxonomy.

### Adding a tag via the Taxonomy Editing UI

```
Scenario: Adding a tag whose value belongs to an archived tag explains what happened
  Given a taxonomy with an archived tag whose value is "Photosynthesis"
  When an administrator adds a tag with the value "Photosynthesis"
  Then the tag is not created
  And the error says the value belongs to an archived tag and that a different value should be used

Scenario: Adding a tag whose value is genuinely taken still reports a duplicate
  Given a taxonomy with an unarchived tag whose value is "Photosynthesis"
  When an administrator adds a tag with the value "Photosynthesis"
  Then the tag is not created
  And the error reports the duplicate as it does today

Scenario: Adding a tag whose value is free succeeds
  Given a taxonomy with no tag of any kind holding the value "Respiration"
  When an administrator adds a tag with the value "Respiration"
  Then the tag is created
```

### Importing a file

```
Scenario: Importing a value that belongs to an archived tag is refused
  Given a taxonomy with an archived tag whose value is "Photosynthesis"
  When a file containing that value is imported into that taxonomy
  Then the archived tag is not updated or revived by the import
    And the import reports that the value belongs to an archived tag and a different value should be used

Scenario: Importing an external identifier that belongs to an archived tag is refused
  Given a taxonomy with an archived tag holding a given external identifier
  When a file containing that external identifier is imported into that taxonomy
  Then the archived tag is not updated or revived by the import
    And the import reports that the identifier belongs to an archived tag

Scenario: An import that collides changes nothing else
  Given an import file containing one colliding value and several valid new tags
  When the file is imported
  Then the collision is reported
    And the taxonomy is left as it was before the import
```

### Exporting a taxonomy

```
Scenario: An archived tag is absent from an export
  Given a taxonomy with one archived tag and two that are not archived
  When the taxonomy is exported
  Then only the two unarchived tags appear in the exported output

Scenario: Re-importing an export of a taxonomy containing archived tags is clean
  Given a taxonomy containing archived tags
  When it is exported and the result imported into an empty taxonomy
  Then the import succeeds
    And the resulting taxonomy contains only the tags that were not archived
```

## Description

Once tags can be archived, a taxonomy contains rows that are invisible on every read path but still occupy their value and their external identifier. Creating a tag with one of those values fails today with the generic message for a value that already exists, which is confusing: the administrator can see no such tag anywhere and has no way to work out why the value is refused.

Import has the same problem and a worse failure mode. Its usual behavior on encountering an existing value or external identifier is to update the matching row, so without a change it would silently write to an archived tag and effectively revive it as a side effect of an import.

The decision is that an archived tag is treated as no longer part of the taxonomy, on every surface that can encounter one: the Taxonomy Editing UI, import, and export. Export omits it entirely, and any attempt to create or import over its value or external identifier is refused with a message explaining why and telling the administrator to use a different value.

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done.

### Implementation specifics

- **Create path (Taxonomy Editing UI and its API):** `add_tag_to_taxonomy` in `src/openedx_tagging/api.py`, and whatever validation raises the existing "value already exists" error. Distinguish the archived case before raising and use a distinct message naming the problem and pointing at using a different value Keep the unarchived duplicate message exactly as it is today, so existing callers and tests are unaffected.  
- **Match on both keys.** A collision can be on the tag value or on the external identifier, and both must produce the archived-specific message when the matching row is archived.  
- **Import path:** the parsers and the import plan under `src/openedx_tagging/import_export/`. Whatever step resolves an incoming row to an existing tag must not resolve it to an archived one and must not update it. Raise the same archived-specific error.  
- **Report the collision as an import error, not a warning**, and leave the taxonomy unchanged, so a partly-applied import cannot revive some tags and not others. Confirm how the existing import plan reports and rolls back before choosing where to raise.  
- **Export path:** already excludes archived tags via \#778; this ticket adds the round-trip test proving export and import agree with each other, it does not change export's own behavior.  
- **Do not add a restore action in this ticket.** No restore path exists yet beyond direct database access; do not invent an endpoint or a UI affordance here.  
- **Wording should be reviewed rather than invented in code review.** The message is administrator-facing text; "that value belongs to an archived tag, restore it instead" is a starting point, not final copy.  
- **Tests** in the existing `openedx_tagging` API and import and export test modules, one per scenario, plus a round-trip test exporting a taxonomy containing archived tags and importing the result into an empty taxonomy.  
- **Out of scope:** a restore endpoint or UI, the archive branches themselves (\#779, \#780), and read-path exclusion (\#778). Also out of scope: the frontend's lack of translation for backend-sourced error text on either the Taxonomy Editing UI or the import wizard (confirmed pre-existing, not something this ticket changes) — this message inherits that same limitation, consistently with every other error on those pages today.

## Files to create and modify

**Modified files**

| File | Nature of modification |
| :---- | :---- |
| src/openedx\_tagging/api.py | distinguish the archived collision in `add_tag_to_taxonomy` (the Taxonomy Editing UI's create path) and raise a message pointing at using a different value |
| src/openedx\_tagging/import\_export/ | refuse to resolve an incoming row to an archived tag on value or external identifier, and report it as an import error |
| tests/openedx\_tagging/ | one test per scenario plus an export-then-import round-trip test |

## Context

- The approved implementation approach on \#655, and the decision that an archived tag is treated as no longer part of its taxonomy.  
- \#778 excludes archived tags from read paths and from export; this ticket relies on that and adds the round-trip check.  
- \#776 adds the `archived` field these paths inspect.  
- `src/openedx_tagging/api.py`, `add_tag_to_taxonomy`, and `src/openedx_tagging/import_export/` for the two paths involved.  
- \#758 implements the non-nullable external identifier work whose auto-generation must also treat archived rows as occupying their slot; see the prerequisite note for that issue.  
- **Restoring an archived tag today means a direct database change** (SQL, or the Django admin if a later ticket happens to register these models there) — there is no application-level restore path, and this ticket does not add one. This is why the administrator-facing message points at choosing a different value rather than at restoring the archived one.

</details>
