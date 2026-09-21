# [Arch] Determine Competency ID field strategy for taxonomy competency data

GitHub: https://github.com/openedx/openedx-core/issues/625 (#625, CLOSED)
Cached: 2026-09-21

## Architecture Spike: Determine Competency ID field strategy for taxonomy competency data

### Use Case

As a Platform Administrator, I want a stable, human-readable Competency ID visible for each competency in the Competency Management UI and on the assignment workflow, so that I can reference and communicate specific competencies using a meaningful identifier that my institution recognizes.

### Description

**Current behavior**

The existing tag/taxonomy data model exposes several identifier fields per tag: an internal PK (`id`, never user-visible), a stable external reference (`uuid`), and a client-meaningful key (`_key` / `key`). None of these is designed for use as a human-readable Competency ID in a management UI or assignment workflow. No such field currently exists.

**Requested change**

Determine the ID field strategy for competency taxonomies: which field or fields represent the Competency ID, how the ID is assigned, and how it behaves across import, re-import, API retrieval, and UI display. This spike produces a documented recommendation for the data model implementation ticket — not code.

Key constraints the recommendation must respect:

- This is an internal identifier. If CASE IDs or CTDL IDs are added in the future, they are separate fields with their own semantics — this ID is not a CASE ID.  
- Changes to the data model are additive; existing identifier fields are not replaced.  
- The recommendation must be approved by the engineering team and the Open edX community.

### Acceptance Criteria

This is an architecture spike. The deliverable is a documented technical recommendation, not working code. There is no Gherkin and no QA path.

- [ ] Recommendation document published (see Open Questions for format).  
- [ ] Recommendation specifies whether a new field is added or an existing field is repurposed, and justifies the choice.  
- [ ] ID assignment strategy decided and documented (see Open Questions).  
- [ ] Uniqueness scope decided: within a taxonomy, globally, or advisory only.  
- [ ] Import and re-import behavior specified: whether the ID is preserved, overwritten from the import file, or conflict-flagged.  
- [ ] API serialization specified: which field is exposed and under what name.  
- [ ] Backward compatibility and migration implications documented.  
- [ ] Recommendation reviewed and approved by the engineering team and Open edX community.  
- [ ] All Open Questions resolved before this ticket is closed.

### Open Questions

1. **ID assignment strategy (architect, blocking):** Two options:  
     
   - Option A (auto-generate with override): derive a default from the competency name — initials of each word plus a hierarchical position suffix (e.g., `PK-1`, `PK-1.2`, `PK-1.2.3` for root / second level / third level). User can override. The exact format of the suffix is part of what this spike defines.  
   - Option B (user-entered only): field is blank until the operator supplies a value. No auto-generation.

   

   Option B is simpler to implement and avoids the edge case where a name change silently invalidates a previously meaningful auto-generated ID. Which fits the operator use case better?

   

2. **Uniqueness scope (architect):** Must the Competency ID be unique within a taxonomy, unique globally across all competency taxonomies, or is it advisory (displayed but not enforced)?  
     
3. **Re-import behavior (architect):** On re-import, is the stored Competency ID preserved, overwritten if the import file includes an ID column, or always preserved (import file ID column ignored)? What import file column, if any, maps to this field?  
     
4. **Recommendation format (architect):** ADR under `docs/decisions/`, a GitHub discussion for community comment, or both? The community approval requirement suggests at minimum a public discussion before the ADR is finalized.

### Context for the Architect

**Existing data model identifiers** (see `src/openedx_tagging/core/tagging/models/`):

- `id` — internal PK, never user-visible  
- `uuid` — stable external reference  
- `_key` / `key` — client-meaningful, the DB field used in tagging operations

**UX context:** The existing UX designs for the Competency Management page and the assignment workflow show a visible Competency ID per competency. This ID appears on the control used to apply a competency to an assignment. The exact field this maps to is what this spike must determine.

**Architect's current position (starting point, not a decision):**

The Competency ID should be an internal identifier. CASE IDs and CTDL IDs, if added, are separate fields — conflating them (as has been suggested in the past) mixes internal and external identifier semantics and will cause problems when institutions want both.

The natural auto-generation scheme is: initials of each word in the competency name plus a hierarchical depth/position suffix. However, Option B (user-entered only) is likely simpler and avoids name-change invalidation. This is the core design question the spike should resolve with team and community input.  
