# [BE] Support editing an existing tag's external_id (Competency ID) on taxonomy re-import

GitHub: https://github.com/openedx/openedx-core/issues/673 (#673, CLOSED)
Cached: 2026-10-22

## Use Case

As a Platform Administrator, I want to correct or change the Competency ID of an existing competency by re-importing its taxonomy, so that a mistyped or externally-changed identifier can be fixed in place without deleting and recreating the competency (which may already carry content associations or be protected from deletion).

## Acceptance Criteria

These scenarios cover the import-time `external_id` rename described above. The import is performed through the Studio taxonomy import wizard: the admin uploads a CSV or JSON file that includes the optional `previous_id` column, the wizard shows a **Plan** preview and requires confirmation, and validation errors surface at the Plan step and block the admin from proceeding. Because `external_id` is **not** shown in the import wizard or the tag list, the resulting `external_id` value is verified by **exporting** the taxonomy from the wizard and inspecting the exported file: `external_id` round-trips as the file's `id` column (CSV) / `id` key (JSON), and `previous_id` is never exported. Export is available in the wizard today, so this verification does not depend on the Competency Management page (4.6). Both export formats are covered below.

The wizard renders validation errors as a single block of text supplied by the backend (`ImportTagsWizard.jsx` prints the API's error message verbatim in one alert; it holds no per-error-type copy of its own). Two consequences for every scenario below that says the wizard "identifies the offending row": the identification has to be inside the message the backend produces, since the wizard cannot add it, and when a file contains more than one rejected row every row's error must appear in that one block rather than only the first, so an admin correcting a large framework is not forced into one upload per mistake.

The Studio taxonomy import is always a **full replace** (the uploaded file is the complete desired state; tags omitted from the file are removed), so a test import file must contain the taxonomy's full desired state.

Two rules govern how a file's rows relate to one another, and both are validated at the Plan step:

- An `id` that is currently held by another competency may be claimed only if the same file also removes that competency (by omitting it). If the file keeps both, the row is rejected.
- Every `parent_id` must reference the `external_id` its parent will hold **after** the import, not the one it held before. A row whose `parent_id` names an `external_id` that the same file renames away is rejected.

```
Scenario: rename an external_id, verified via CSV export
  Given a competency taxonomy contains a tag whose external_id is "COMP-A"
  When the admin imports a file whose row has previous_id "COMP-A" and id "COMP-B"
  Then the import succeeds (a "<taxonomy> updated" toast) with no duplicate competency
  When the admin exports the taxonomy as CSV
  Then the exported CSV has exactly one row for that tag with id "COMP-B"
  And no row has id "COMP-A"
  And the CSV has no previous_id column

Scenario: rename an external_id, verified via JSON export
  Given a competency taxonomy contains a tag whose external_id is "COMP-A"
  When the admin imports a file whose row has previous_id "COMP-A" and id "COMP-B"
  Then the import succeeds with no duplicate competency
  When the admin exports the taxonomy as JSON
  Then the exported JSON has that tag with "id": "COMP-B"
  And no entry has "id": "COMP-A"
  And no entry has a previous_id key

Scenario: re-import is idempotent (previous_id equals the new id)
  Given a competency taxonomy contains a tag whose external_id is "COMP-B"
  When the admin imports a file whose row has previous_id "COMP-B" and id "COMP-B"
  Then the import succeeds with no error
  And a subsequent export (CSV or JSON) still shows that tag's id as "COMP-B" (unchanged)

Scenario: no previous_id, new id (current create behavior preserved)
  Given a competency taxonomy has no tag whose external_id is "COMP-Z"
  When the admin imports a file whose row has no previous_id and id "COMP-Z"
  Then the import succeeds and the new competency appears in the tag list
  And an export (CSV or JSON) shows a row/entry with id "COMP-Z"

Scenario: previous_id is present but matches no existing tag (likely typo)
  Given no tag in the taxonomy has external_id "COMP-GHOST"
  When the admin imports a file whose row has previous_id "COMP-GHOST" and id "COMP-B"
  Then the wizard shows a validation error identifying the offending row (unmatched previous_id)
  And the admin cannot proceed
  And an export afterward is unchanged (no id "COMP-B" was introduced)

Scenario: new id collides with a different tag's external_id in the same taxonomy
  Given a taxonomy contains competency X (external_id "COMP-A") and competency Y (external_id "COMP-B")
  When the admin imports a file whose row has previous_id "COMP-A" and id "COMP-B"
  Then the wizard shows a validation error identifying the offending row
  And the admin cannot proceed
  And an export still shows X with id "COMP-A" and Y with id "COMP-B"

Scenario: a rename claims an id the same import frees by removing its holder
  Given a taxonomy contains competency X (external_id "COMP-Z") and competency Y (external_id "COMP-A")
  When the admin imports a file that omits X entirely
  And the same file has a row with previous_id "COMP-A" and id "COMP-Z"
  Then the import succeeds
  And an export shows X is gone and Y is present with id "COMP-Z"
  And Y is preserved (not deleted and recreated), with its content associations intact
  And the outcome does not depend on the order of the rows in the file

Scenario: a rename onto an id whose holder the same import keeps is rejected
  Given a taxonomy contains competency X (external_id "COMP-Z") and competency Y (external_id "COMP-A")
  When the admin imports a file that still contains X
  And the same file has a row with previous_id "COMP-A" and id "COMP-Z"
  Then the wizard shows a validation error identifying the offending row
  And the admin cannot proceed
  And an export still shows X with id "COMP-Z" and Y with id "COMP-A"

Scenario: two competencies swap external_ids in one import
  Given a taxonomy contains competency X (external_id "COMP-A") and competency Y (external_id "COMP-B")
  When the admin imports a file with a row previous_id "COMP-A" / id "COMP-B"
  And the same file has a row previous_id "COMP-B" / id "COMP-A"
  Then the import succeeds
  And an export shows X with id "COMP-B" and Y with id "COMP-A"
  And the taxonomy's competency count is unchanged (nothing created or deleted)
  And both competencies keep their content associations

Scenario: three competencies rotate external_ids in one import
  Given a taxonomy contains competency X ("COMP-A"), competency Y ("COMP-B"), and competency Z ("COMP-C")
  When the admin imports a file that renames X to "COMP-B", Y to "COMP-C", and Z to "COMP-A"
  Then the import succeeds
  And an export shows each competency holding the id its own row specified
  And the outcome does not depend on the order of the rows in the file

Scenario: a rename chain that collides with a competency the file keeps is rejected whole
  Given a taxonomy contains competency X ("COMP-A"), competency Y ("COMP-B"), and competency Z ("COMP-C")
  When the admin imports a file that renames X to "COMP-B" and renames Y to "COMP-C"
  And the same file keeps Z holding "COMP-C" unchanged
  Then the wizard shows a validation error identifying the offending row
  And the admin cannot proceed
  And an export shows all three competencies with their original ids

Scenario: a child row references its renamed parent's new external_id
  Given a taxonomy contains parent competency P (external_id "COMP-P") and child competency C beneath it
  When the admin imports a file with a row previous_id "COMP-P" / id "COMP-P2"
  And the same file has a row for C with parent_id "COMP-P2"
  Then the import succeeds
  And an export shows P with id "COMP-P2" and C still nested beneath it

Scenario: a child row referencing its parent's pre-import external_id is rejected
  Given a taxonomy contains parent competency P (external_id "COMP-P") and child competency C beneath it
  When the admin imports a file with a row previous_id "COMP-P" / id "COMP-P2"
  And the same file has a row for C with parent_id "COMP-P"
  Then the wizard shows a validation error identifying the child row
  And the error states that the parent_id names an id the same file renames away, and names the new id to use instead
  And the admin cannot proceed
  And an export shows P with id "COMP-P" and C unchanged

Scenario: a parent and its child are both renamed in one import
  Given a taxonomy contains parent competency P ("COMP-P") and child competency C ("COMP-C") beneath it
  When the admin imports a file that renames P to "COMP-P2", and renames C to "COMP-C2" with parent_id "COMP-P2"
  Then the import succeeds
  And an export shows P with id "COMP-P2", C with id "COMP-C2", and C still nested beneath P

Scenario: renaming an external_id preserves the competency's content associations
  Given a competency taxonomy contains a tag (external_id "COMP-A") applied to course content
  When the admin imports a file that renames it via previous_id "COMP-A" to id "COMP-B"
  Then the import succeeds and the competency is preserved (not deleted and recreated)
  And its content associations remain intact
  And an export shows the tag with id "COMP-B"

Scenario: export does not carry previous_id (round-trip safety), CSV and JSON
  Given a taxonomy whose tags have external_id values
  When the admin exports the taxonomy as CSV, and separately as JSON
  Then neither export contains a previous_id column or key (only id, value, parent_id)
  And re-importing either exported file unchanged reports no changes (a clean round-trip)

```

## Description

**Current state.** In `openedx-core`, a competency is a `Tag` in a competency taxonomy, and the "Competency ID" is that tag's `external_id` (ADR 0010, `docs/openedx_tagging/decisions/0010-mutable-tag-external-id.rst`). The taxonomy tag import (`src/openedx_tagging/import_export/`) already reads `external_id` from the import file's required `id` column and sets it when creating a new tag, and it matches import rows to existing tags **by** `external_id`. It is possible to change external_id via the Django admin, but not recommended to use that for editing tags in general: the REST API accepts it only on create (no PATCH path), and the import uses it as the match key rather than an editable value. Once a competency's Competency ID is wrong, it cannot be corrected in place; delete-and-recreate is not a fallback because a tag carrying content associations or learner status is protected from deletion. `external_id` is currently nullable at the DB level; ADR 0012 (merged, not yet implemented — see Decision log) will make it `NOT NULL` for every tag, but that migration is separate future work and doesn't change the problem this ticket solves.

**Requested change (edit an existing ID on re-import).** Extend the tag import to update an existing tag's `external_id` in place, using the optional `previous_id` column defined in ADR 0010\. When an import row's `previous_id` matches an existing tag's current `external_id` and the row's `id` differs, the import rewrites that tag's `external_id` to the row's `id` (preserving the tag's PK and associations), applying any co-changed `value`/`parent_id` in the same pass. `previous_id` is transient: not stored on the tag, not emitted on export. The `(taxonomy, external_id)` uniqueness constraint continues to apply, so a new `id` colliding with another tag's `external_id` is rejected. If `previous_id` is present but matches no existing tag, the row is rejected with an error (a likely typo); if `previous_id` is empty or absent, the row is processed exactly as today (create, or match-by-`id`). This also works under a full `replace` import: a renamed tag is preserved, not deleted-and-recreated. This mechanism is also how an institution replaces a value that ADR 0012's future auto-generation assigned automatically, per that ADR's own note.

**Out of scope.** Editing `external_id` through the REST API or the Competency Management UI (deferred by ADR 0010); persisting or exporting `previous_id`; **clearing** an `external_id` to empty (overwrite-only in MVP); any change to the create path or to matching for rows without `previous_id`; the frontend import affordance (a referenced companion, not built here); **implementing ADR 0012's `NOT NULL` migration, backfill, and create-time auto-generation** (tracked as its own ticket — see Decision log; it's infra-wide across all `openedx_tagging` taxonomies, not scoped to this competency-ID re-import workflow).

<details>
<summary>Context</summary>

- **Parent / siblings.** Descends from UC4 (admin views a Competency ID per competency). 4.1 ([\#625](https://github.com/openedx/openedx-core/issues/625)) produced ADR 0010, which this ticket implements; 4.3 confirmed the tag-list GET already returns `external_id` (no change). 4.6 (Competency Management page) will display the ID; this ticket does not depend on it, verification here is via export.  
    
- **Authoritative design.** ADR 0010, `docs/openedx_tagging/decisions/0010-mutable-tag-external-id.rst` (merged, PR \#637; status Proposed). It defines the `previous_id` mechanism, the transient rule, and that `(taxonomy, external_id)` uniqueness still governs the new `id`. REST/UI editing is explicitly deferred there. **ADR 0012**, `docs/openedx_tagging/decisions/0012-non-nullable-tag-external-id.rst` (merged, PR \#658; status Proposed) is related but not implemented by this ticket: it decides to make `external_id` `NOT NULL` for every taxonomy via a future migration, backfill, and create-time auto-generation. See Decision log.  
    
- **Domain fact.** A competency is a `Tag`; "Competency ID" is that tag's `external_id`. No separate Competency model. `external_id` is currently nullable and unique **per taxonomy** (`(taxonomy, external_id)`), case-insensitive. Per ADR 0012 this will become `NOT NULL` once that (separate, not-yet-built) migration ships; this ticket's mechanism is unaffected either way.  
    
- **Import & export format.** `external_id` round-trips as the file's `id` column/key: `_load_tags_for_export` emits `"id": tag["external_id"]`; CSV columns are `id, value, parent_id`; JSON is `{"tags": [{"id", "value", "parent_id"}]}`. `previous_id` is import-only and never exported.  
    
- **Import format & parse:** `src/openedx_tagging/import_export/parsers.py` — `required_fields`/`optional_fields` (lines 51-52), `_parse_tags` optional-field loop (171-183), CSV header check `_verify_header` (319-334), CSV export field list (307), export row builder `_load_tags_for_export` (187-208).  
    
- **Plan & item:** `src/openedx_tagging/import_export/import_plan.py` — `TagItem` (14-31), `generate_actions` replace/delete logic (136-180), `_get_tag_id` (95-105).  
    
- **Actions & matching:** `src/openedx_tagging/import_export/actions.py` — shared `_get_tag` (71-80), `_validate_value` (119-167), `_validate_parent` (98-117), `CreateTag` (170-252), `RenameTag` (319-371), `UpdateParentTag` (255-316), `available_actions` (444-451).  
    
- **Orchestrator (no change):** `src/openedx_tagging/import_export/api.py` `import_tags` (57-123). Platform import endpoints forward to these (`src/openedx_tagging/rest_api/v1/views.py:302, 337`) and need no change for an optional column.  
    
- **Constraint to respect:** `Tag.external_id` case-insensitive field (`src/openedx_tagging/models/base.py:68`) and `unique_together (taxonomy, external_id)` (`base.py:99-100`).
</details>
<details>
<summary>Technical Notes</summary>

### Files to Create

None. (Part 2's migration and ADR 0011 stub are removed — see Decision log. ADR 0012 already exists and supersedes what ADR 0011 would have proposed.)

### Files to Modify

| File | Nature of modification |
| :---- | :---- |
| `src/openedx_tagging/import_export/parsers.py` | Add an `import_only_fields = ["previous_id"]` category to `Parser`; read it in `_parse_tags` like an optional field (missing/blank → `None`). Keep it out of `required_fields + optional_fields` so CSV headers and both exporters never emit it; `_verify_header` (required-only) is unaffected, so the column stays optional in CSV and JSON. |
| `src/openedx_tagging/import_export/import_plan.py` | Add \`previous\_id: str |
| `src/openedx_tagging/import_export/actions.py` | Add `RenameTagExternalId(ImportAction)`. `applies_for` \= `previous_id` present **and** `id != previous_id` (claims the row even when no tag matches, so a bad `previous_id` errors instead of creating). `validate` \= reject when no tag has `external_id == previous_id` (unmatched previous\_id error); reject when a **different** tag already holds `external_id == id` (DB \+ batch via `_search_action`, mirroring create-time duplicate handling); run `_validate_value` only when the value changes; `_validate_parent` if `parent_id` set. `execute` \= load by `previous_id`, set `external_id = id`, apply value/parent, save. Add a guard at the top of `CreateTag.applies_for` returning `False` when `previous_id` is present and `id != previous_id`, so no duplicate is created. Register `RenameTagExternalId` before `CreateTag` in `available_actions`. |
| `tests/openedx_tagging/import_export/test_parsers.py` | `previous_id` parsed from CSV and JSON; absent/blank → `None`; never present in export output. |
| `tests/openedx_tagging/import_export/test_actions.py` | `RenameTagExternalId` applies/validate/execute; `CreateTag` guard; unmatched `previous_id` rejected; new-id collision rejected; unchanged value not flagged as duplicate. |
| `tests/openedx_tagging/import_export/test_import_plan.py` | Rename row yields one `RenameTagExternalId` and no `DeleteTag` under `replace=True`; no spurious `WithoutChanges`. |
| `tests/openedx_tagging/import_export/test_api.py` | End-to-end `import_tags` then export: rename updates `external_id` in place, preserves PK/associations, and the export round-trips the new `id`; unmatched `previous_id` and colliding new id both rejected. |

### Implementation Notes

Implement ADR 0010's import-only `previous_id` pathway. Add `previous_id` as an import-only parser field (a new `import_only_fields` category, read like optional fields but excluded from `required_fields + optional_fields` so it parses on import and never appears on export) and carry it on the `TagItem` class (src/openedx\_tagging/import\_export/import\_plan.py). Handle the edit with a single new action, `RenameTagExternalId`, that **claims** any row carrying a `previous_id` that differs from the row's `id`; in `validate` it rejects the row when `previous_id` matches no existing tag (surfacing a typo instead of silently creating), and rejects when the new `id` would collide with a different tag's `external_id` in the same taxonomy (a clean `ImportActionError`, not an `IntegrityError`); in `execute` it loads the matched tag, rewrites `external_id` to the new `id` in place, applies the row's `value`/`parent`, and saves, preserving the tag's PK and associations. Guard `CreateTag.applies_for` to skip `previous_id`\-bearing edit rows so no duplicate is created; `RenameTag`/`UpdateParentTag` already skip them because they match on the new `id`. Clearing is not supported and needs no code: `id` is a required column, so a blank new id is already rejected by the parser. Under `replace=True`, exclude tags matched by `previous_id` from the delete set in `generate_actions` so a renamed tag survives; note the Studio taxonomy import always runs in full-replace mode, so this is the primary path, without it a rename would delete the tag and recreate it, losing its content associations. Because `(taxonomy, external_id)` is unique per taxonomy, the rename rows cannot be applied one at a time: a swap or a longer rotation collides the moment the first row is written, while the competency holding the target id still holds it. Resolve the whole file's rename set, together with the replace-mode delete set, into a single plan before writing anything, so that an id freed by a delete is available to a rename and a cycle among renames resolves without a transient duplicate. ADR 0010's transient rule governs how that intermediate state is permitted; validate the whole set at the Plan step so a rejected row blocks the import before any write. `RenameTagExternalId` must be represented in the generated import plan as an in-place update (not a silent no-op and not a delete-and-create), so a file that only changes an `external_id` is processed rather than read as "no changes". The `external_id` value is verified by exporting the taxonomy (it round-trips as the file's `id`); the wizard does not display the value itself. All new behavior is gated on `previous_id` being present, so normal imports are byte-for-byte unchanged. This needs no migration, no export change, and no `openedx-platform` change; it is confined to `src/openedx_tagging/import_export/` and respects `.importlinter`.

### Example Resolution Prompt

In `openedx-core`, implement ADR 0010 (`docs/openedx_tagging/decisions/0010-mutable-tag-external-id.rst`): let the taxonomy tag import edit an existing tag's `external_id` in place via a new optional, import-only `previous_id` column. Do not add a model field, do not migrate, and do not change export output or `openedx-platform`.

1. `src/openedx_tagging/import_export/parsers.py`: add `import_only_fields = ["previous_id"]` to `Parser`. In `_parse_tags`, after the optional-field loop, read each `import_only_fields` entry into `tag_data` with the same coercion as optional fields (missing/blank → `None`). Do NOT add it to `required_fields`/`optional_fields`, so CSV headers (line 307\) and `_load_tags_for_export` never emit it, and `_verify_header` keeps it optional.  
2. `src/openedx_tagging/import_export/import_plan.py`: add `previous_id: str | None = None` to `TagItem`. In `generate_actions`' `replace` branch, also `tags_for_delete.pop(tag.previous_id, None)`.  
3. `src/openedx_tagging/import_export/actions.py`: add `class RenameTagExternalId(ImportAction)` (`name = "rename_external_id"`).  
   - `applies_for(taxonomy, tag)`: `return bool(tag.previous_id) and tag.id != tag.previous_id`.  
   - `validate(indexed_actions)`: if no tag has `external_id == tag.previous_id`, append an `ImportActionError` (unmatched previous\_id). If a *different* tag already has `external_id == tag.id` (DB check \+ `_search_action` for prior create/rename ids), append an `ImportActionError` (duplicate). Run `_validate_value` only if the matched tag's current value differs from `tag.value`; run `_validate_parent` if `tag.parent_id`.  
   - `execute()`: `target = self.taxonomy.tag_set.get(external_id=self.tag.previous_id)`; set `target.external_id = self.tag.id`, `target.value = self.tag.value`, `target.parent = self.taxonomy.tag_set.get(external_id=self.tag.parent_id) if self.tag.parent_id else None`; `target.save()`.  
   - Guard at the top of `CreateTag.applies_for`: `if tag.previous_id and tag.id != tag.previous_id: return False`.  
   - Register `RenameTagExternalId` in `available_actions` immediately before `CreateTag`.  
4. Tests in `tests/openedx_tagging/import_export/`: `test_parsers.py` (previous\_id parsed CSV+JSON, absent/blank → None, never exported), `test_actions.py` (applies/validate/execute, CreateTag guard, unmatched previous\_id rejected, new-id collision rejected, unchanged value not flagged), `test_import_plan.py` (rename → one `RenameTagExternalId`, no `DeleteTag` under replace), `test_api.py` (end-to-end rename preserves PK/associations, the export round-trips the new `id`, both rejection paths).

Constraints: `previous_id` is transient and import-only (not persisted, not exported); enforce `(taxonomy, external_id)` uniqueness as a clean rejection, not an `IntegrityError`; all new behavior gated on `previous_id` so normal imports are unchanged; stay within `src/openedx_tagging/import_export/` (respect `.importlinter`). Run `pytest tests/openedx_tagging/import_export/ -p no:cov` and `lint-imports`.

</details>
