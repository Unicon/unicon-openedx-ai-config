# Catalog registry

Shared across projects: one row per Figma library the design-system tooling knows how to
read. A project (`projects/<project>.md`) points at one of these by `source_id`. This file
and `projects/*.md` are the only files in this repo that hold Figma file keys (see
`policy.md` §6).

Switching a project from one catalog to another (e.g. a Unicon copy to an OEP-70 Community
release file) is: add or update a row here, point the project's `catalog` field at it,
re-export (`scripts/seed-source.mjs`, or the native/use_figma path once built — see
`figmaToCodeWorkflow.md`), regenerate (`scripts/generate.mjs`), and review the diff. No skill
text changes.

## unicon-copy-2026-09

| Field | Value |
|---|---|
| kind | unicon-copy |
| library_name | Paragon Design System - Unicon Copy |
| library_key | `jZBK8Mp5yFgcDEwEirv4Jl` |
| copied_from_key | `l0kvu7Yu248Vi3X7dDDsO5` (Axim Paragon, view-only to Unicon) |
| library_version | v_Alpha-0.1 |
| legacy_style_prefix | `💎 -` |
| synced_on | 2026-09-24 |
| synced_by | Phil Ball |
| catalog file | `sources/unicon-copy-2026-09.json` |
| raw inputs | `sources/raw/unicon-copy-2026-09-variables.md`, `sources/raw/unicon-copy-2026-09-mcp-baseline-16-1245.json` |
| variables captured | 2026-09-24 (232 variables, full export via the DESIGN.md format) |
| styles captured | 2026-09-21, **partial**: only the styles used by node `16:1245` ("Apply Competencies"), via the official MCP `get_variable_defs`. Not a full style export — see `paragon-gaps.md` for the "export every local style" gap this leaves, and Milestone 3 in `figmaToCodeWorkflow.md` for closing it. |
| paragon_reference | 23.23.0 (light theme) |
| stale_after_days | 45 |
| mcp_calls_per_frame | 3 |

## Adding a new catalog row

Copy the table above, fill in: `kind` (`unicon-copy` \| `community-release` \|
`oep70-branch`), the library name/key, `catalog file` (where the normalized
`sources/<id>.json` will live), and the capture dates once you've exported. Then add a
`projects/<project>.md` pointing at it, or repoint an existing one.
