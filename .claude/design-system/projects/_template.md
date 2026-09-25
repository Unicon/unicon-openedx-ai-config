# Project: `<project-id>`

Copy this file to `projects/<project-id>.md` when a new Unicon Open edX project adopts the
Figma-to-Paragon workflow. Fill in every field; delete this comment block once done.

| Field | Value |
|---|---|
| designer | `<name>` — the person `figma-to-paragon` and `paragon-design-check` treat as the design authority for this project (see `policy.md` §3) |
| catalog | `<source_id from catalogs.md>` |
| brand_package | `<npm package name and version, e.g. @openedx/brand-openedx 1.3.0, if this project has one>` |
| mcp_calls_per_frame | `3` (default; raise only if a real workflow needs more and the seat's daily budget supports it) |
| handoff_location | `<where the handoff revision lives, e.g. "GitHub issue 'UX Design' section">` |

## Feature files

| Area | Mirror file + key | Canonical source key | Section | Synced ver | Status |
|---|---|---|---|---|---|
| _(add one row per design area once work starts)_ | | | | | in-sync \| drift-pending \| frozen |

## Targets

| Repo folder | Role | Host (if plugin) | Declared Paragon |
|---|---|---|---|
| _(add one row per repo this project's UI work touches)_ | host-mfe \| plugin | | |

`scripts/paragon-versions.mjs` reads this table (once it accepts a `--project` flag; for now
pass repo paths directly, see `figmaToCodeWorkflow.md`) to report each target's installed vs
declared Paragon version against this project's `catalog`'s reference version.
