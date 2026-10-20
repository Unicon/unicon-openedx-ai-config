# Design conventions

Naming and annotation rules for Figma files so a copied/mirrored frame still carries enough
signal for a dev's agent to resolve Paragon components and tokens, even though library links
and component keys are lost on copy (see `figmaToCodeWorkflow.md`'s Milestone 3
copy-survival test, which will confirm exactly how much of this survives for a dev account
without Axim library access).

## Instance and layer naming

- **Instance layer names = Paragon component names.** Never rename a component instance.
- A **detached** instance or a **local stand-in** for a Paragon component is named
  `Paragon/<Component> <prop>=<value>` (e.g. `Paragon/Button variant=primary size=sm`).
- **Net-new** UI with no Paragon equivalent is named `NetNew/<Name>` and must have a matching
  row in `paragon-gaps.md`.
- **Frames**: `<ticket#> <Area> / <Screen> / <State>` (e.g. `743 Progress / Summary sidebar /
  Empty`).

## Tokens

Keep variable bindings on fills, strokes, text, and effects — that's the primary signal
`paragon-design-check` and `figma-to-paragon` read. Add a `Token` annotation only where the
copy-survival test shows a binding doesn't make it to a dev's account; don't pre-annotate
everything defensively.

## Annotations

Native Figma annotations, one `key: value` pair per line, in these categories:

- **`Paragon`** — the component and any variant/props the frame's own naming doesn't already
  make obvious.
- **`Token`** — only where a binding doesn't survive (see above).
- **`A11y`** — see the key list below.
- **`Behavior`** — interaction notes a static frame can't show (e.g. "collapses on scroll").
- **`Data`** — what real data looks like (e.g. "up to 40 chars, truncates with ellipsis").

### `A11y` keys

| Key | Meaning |
|---|---|
| `name` | Final accessible name / alt text, as copy — not a placeholder |
| `heading` | Heading level (h1-h6), independent of the visual size used |
| `landmark` | A landmark role this region should carry |
| `focus` | Tab order position, when it isn't DOM/visual order |
| `kbd` | The interaction or WAI-ARIA APG pattern (e.g. "tree": arrow keys, Home/End) |
| `role` | Only for a custom widget with no native element |
| `state` | expanded / selected / checked / etc., and what triggers each |
| `live` | polite / assertive, for async status |
| `desc` | Text alternative for a chart or graphic; status is never conveyed by color alone |
| `target` | Minimum touch target, when smaller than Paragon's default (≥ 24×24px) |

`paragon-a11y-check` verifies each of these as both inspected (in code) and observed (in the
running app) — see `policy.md` §4.

## Sync stamp

Each mirrored section carries a text layer with this exact format, also mirrored into the
project file's Feature files table:

```
SYNC src=<canonical-file-key>#<node-id> ver=sync/YYYY-MM-DD source=<catalog source_id> paragon=<reference version> by=<designer>
```

Example: `SYNC src=VhAdaucNQS49x0Afp9xPZw#16:1245 ver=sync/2026-10-01
source=unicon-copy-2026-09 paragon=23.23.0 by=pball`

See `policy.md` §3 for how drift on a stamped section blocks implementation, and the sync
procedure (referenced from `figmaToCodeWorkflow.md`) for when to re-stamp.
