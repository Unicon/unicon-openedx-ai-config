# Paragon gaps

Net-new UI with no Paragon equivalent, Figma values that differ from Paragon and should be
fixed in Figma (not code — see `policy.md` §0), and design elements (icons, components) that
don't exist in the installed Paragon. Each row should get an upstream issue once there's
enough evidence to file one usefully; `paragon-design-check` drafts these (see its SKILL.md),
but doesn't post them without approval.

Add a row here from `figma-to-paragon` (dev-side, implementation blocked or worked around),
`paragon-design-check` (design-side, found while checking a frame), or by hand.

| Date | Found by | Item | Kind | Status | Upstream issue |
|---|---|---|---|---|---|
| 2026-09-25 | v0 build (this PR) | `Input`, `Input.Inline`, `Multiselect`, `ContentBlockEmpty`, `ContentBlockError` — Figma "Paragon Categories" component names with no matching export in Paragon 23.23.0 | no-equivalent | open | not filed |
| 2026-09-25 | v0 build (this PR) | `💎 - Heading/H5` (20px/25 bold) has no Paragon equivalent near that size; nearest is `.h3` (22px), not a real substitute | figma-differs | open | not filed |
| 2026-09-25 | v0 build (this PR) | Figma text styles use Inter (and Roboto Mono for `Heading Label`); the installed Paragon + `@openedx/brand-openedx` 1.3.0 use the system font stack. Typography ownership between the brand package and Paragon is flagged as unresolved in Paragon WG notes (2026-04-29, 2026-05-06) | figma-differs | open, tracked upstream in the Paragon WG, not this repo | n/a |
| 2026-09-25 | v0 build (this PR) | `text/secondary`, `text/disabled`, `text/on-dark`, `text/on-light` Figma semantic variables have no Paragon token of the same name (only `text/primary` was resolved, to `--pgn-color-body-base` — see `overrides.json`) | figma-only | open — designer decides each on first use (`policy.md` §1) | n/a |

## Filing upstream

Paragon-level fixes never go into Figma branches (see `figmaToCodeWorkflow.md`'s OEP-70
section) — they go to upstream `openedx/paragon` issues (openedx/paragon#4277 already tracks
a related batch of Figma-library inconsistencies; check whether a new row fits there first)
plus the Paragon Working Group, with the Unicon-side workaround recorded in this file until
the fix merges.
