# Project: `cbe`

Competency-Based Education (CBE) work for Axim Collaborative — the pilot project for the
Figma-to-Paragon workflow.

| Field | Value |
|---|---|
| designer | Phil Ball |
| catalog | `unicon-copy-2026-09` (see `../catalogs.md`) |
| brand_package | `@openedx/brand-openedx` 1.3.0 (installed as `@edx/brand` in `frontend-app-authoring`) |
| mcp_calls_per_frame | 3 |
| handoff_location | The GitHub issue's "UX Design" section (`ticket-template.md` §4) |

## Feature files

| Area | Mirror file + key | Canonical source key | Section | Synced ver | Status |
|---|---|---|---|---|---|
| Competency Application | Unicon copy, `62BanDdK5d8PWqJI625Mmu` | `VhAdaucNQS49x0Afp9xPZw` (Axim) | Apply Competencies (`16:1245`) | 2026-09-21 capture | in-sync (verify at next design-check) |
| Student Progress | _(not yet mirrored to a Unicon copy under this workflow)_ | `VqDdtf3NOsUihle6SNS6Kw` (Axim) | | | drift-pending (no sync stamp yet) |

Add a row per design area as `paragon-design-check` / the sync procedure (`../conventions.md`)
covers it. Until a row has a sync stamp, `figma-to-paragon` treats its sections as
`drift-pending` and blocks implementing from it (`policy.md` §3).

## Targets

| Repo folder | Role | Host (if plugin) | Declared Paragon |
|---|---|---|---|
| `Dev/frontend-app-authoring` | host-mfe | — | `^23.5.0` (installed 23.23.0) |
| `2.3/student-progress` | plugin (Vite prototype; production plugin repo TBD) | frontend-app-learning (assumed; not confirmed) | `^23.4.5` (installed 23.20.3) |

`node scripts/paragon-versions.mjs <repo-path> ...` reports each target's declared vs
installed Paragon against `unicon-copy-2026-09`'s reference (23.23.0). Run it from
`.claude/design-system/`.
