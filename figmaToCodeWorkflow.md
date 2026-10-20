# Figma-to-Paragon workflow

**Status: experimental** (see `.claude/decisions/0002-experimental-agent-phase.md`). How a
Unicon developer implements a Figma design (or checks a built screen against one) as
Paragon-based React, and how a project's designer keeps the design side in sync. Read
[`.claude/design-system/policy.md`](.claude/design-system/policy.md) for the actual rules;
this doc is the quickstart and the "how this evolves" reference.

## Why

Without this, an agent infers tokens and components from a Figma frame — hardcoding values,
inventing token names that don't exist, hand-rolling components Paragon already has, and
missing accessibility semantics. The core idea: **code is the source of truth.** Figma is
design intent; when a Figma value and Paragon disagree, code wins, and the disagreement gets
reported, not silently resolved either direction.

## Architecture, in one line

`catalogs.md` + `projects/*.md` (which Figma source, which repos) → read design intent (MCP,
budgeted, or a handoff block + screenshots) → look up the generated map
(`figma-paragon-map.json`/`.md`) → confirm against the **installed** Paragon (the truth) →
implement or QA-check → verify against one definition of `complete` → a deviation report.

## Quickstart: developer

1. Clone this repo alongside the Open edX repos and symlink `.claude/` per the root
   [README](README.md#claude-setup) (Claude Code) or the Codex section below.
2. Confirm your target repo has `@openedx/paragon` installed (`node_modules/@openedx/paragon`).
3. Connect the Figma MCP with your own account (Dev/Full seat — see your Unicon Figma
   access). Exact setup command depends on your client; for Claude Code,
   `claude mcp add --transport http --scope user figma https://mcp.figma.com/mcp` then
   `/mcp` to sign in — check this against
   [Figma's current docs](https://developers.figma.com/docs/figma-mcp-server/) before
   relying on it, since MCP setup details change.
4. From `.claude/design-system/`, run `node scripts/paragon-versions.mjs <your-repo-path>` to
   confirm your install is sane.
5. Invoke the `figma-to-paragon` skill (Claude Code loads it automatically when it matches;
   Codex needs it named explicitly — see below) on a ticket with a design attached. Most
   tickets right now need **QA mode** (checking an already-built screen), not implement mode.

## Quickstart: designer

1. Clone this repo into your design workspace and symlink `.claude/` (not set up by default —
   do this once).
2. Confirm the Figma MCP works on your Full seat.
3. Read [`conventions.md`](.claude/design-system/conventions.md) for naming and annotation
   rules, and [`handoff-packet-template.md`](.claude/design-system/handoff-packet-template.md)
   for what a handoff revision needs.
4. Post a handoff revision (`<ticket>-r1`) for the next ticket with a ready frame, using the
   template. `paragon-design-check` (a later milestone, see below) will eventually draft this
   for you from a read-only Figma check; for now it's written by hand.

## The design-system tooling (what actually exists today)

All under `.claude/design-system/`, zero-dependency Node ≥ 20, read-only against your Figma
account (nothing writes to Figma yet), never executes Paragon's own package code:

| Script | What it does |
|---|---|
| `scripts/generate.mjs` | Regenerates `figma-paragon-map.json`/`.md` and `paragon-unmapped.md` from the catalog. `--paragon <dir>`, `--check` (fails if committed files are stale) |
| `scripts/check-tokens.mjs` | Scans SCSS/CSS/JS/TS(X) files (or `--diff <base>`) for unknown `var(--pgn-*)` references and hardcoded colors, against the installed Paragon |
| `scripts/map-figma.mjs` | Checks a live Figma MCP `get_variable_defs` capture against the committed map; reports drift or unknown names |
| `scripts/paragon-versions.mjs` | Reports declared vs installed Paragon (+ brand package) for one or more repos |
| `scripts/seed-source.mjs` | Rebuilds the normalized `sources/<id>.json` from the raw catalog exports under `sources/raw/` |

Run any of them from `.claude/design-system/`: `node scripts/<name>.mjs --help`-equivalent is
each script's own header comment (no `--help` flag built yet).

**The map today** (source: `unicon-copy-2026-09`, Paragon 23.23.0): of 225 Figma variables,
205 resolve exactly by name, 13 by a small curated rename table, 2 have a name match but a
differing value (code wins, both recorded), 1 is a reviewed override, and 4 (`text/secondary`,
`text/disabled`, `text/on-dark`, `text/on-light`) are genuinely Figma-only — surfaced as open
design questions, not guessed. See `paragon-gaps.md` for those and other known gaps, the
biggest being that **styles were captured from only one frame**, not a full library export
(see "Milestone 3" below).

## Milestones (where this is, and what's next)

**Milestone 1 (this PR): an experimental v0 in developers' hands.** The generator, its
tests, `paragon-ui`, `figma-to-paragon` (both modes), and `paragon-a11y-check`. Goal: real
tickets, real feedback, fast — not a fully hardened tool.

**Milestone 2: learn from real use.** Developers use v0 on real tickets. Each use gets a
short evaluation logged in `.claude/ai-output-evaluations/Output-evaluations.md`
(ADR 0002) — what needed correcting, what stayed correctly unresolved, effort, any map/rule
fixes needed. Reviewed periodically (e.g. at the bi-weekly AI Dev Sync). Fixes go through
`skill-improver`.

**Milestone 3: harden the designer side.** Not built yet:
- `paragon-design-check` (a designer-facing skill: checks a Figma frame against Paragon,
  drafts a handoff revision). Its evidence matrix (which checks are provable today vs.
  `unverified`) needs a spike first — see `paragon-gaps.md`'s style-capture gap above.
- `scripts/export-catalog.figma.js`: a read-only `use_figma` Plugin-API script to export
  **every** local variable, style, and component set from a Unicon-side Figma copy (not just
  one frame's used styles, which is all `unicon-copy-2026-09` currently has). Only ever run
  on a Unicon copy or a Community duplicate, never a canonical Axim file
  (`policy.md` §5's guardrails).
- A copy-survival test: how much naming/annotation signal actually reaches a dev's account
  when a frame is copied from Axim to Unicon — decides how much of `conventions.md`'s
  annotation guidance is load-bearing versus redundant.
- CI (`.github/workflows/design-system.yml` — this one already exists and runs
  `node --test` plus `generate.mjs --check` against a pinned, `npm pack`-fetched Paragon;
  "harden" here means keeping the pin current as Paragon releases, and adding it as a
  required check once the team is comfortable with it).

Graduating a piece out of "experimental" isn't a numeric threshold — it's reviewers accepting
its output without mapping/intent corrections, no silent decisions found in practice, and the
maintainers judging the upkeep sustainable.

## Adding a new project

This workflow isn't CBE-specific. To add another Unicon Open edX project:
1. Copy `.claude/design-system/projects/_template.md` to `projects/<project-id>.md` and fill
   it in (designer, catalog, targets).
2. If it uses a different Figma library, add a row to `.claude/design-system/catalogs.md`.
3. Run `scripts/seed-source.mjs`-equivalent for that catalog (today's script is hardcoded to
   the `unicon-copy-2026-09` raw files — generalizing it to take a catalog id as older
   catalogs accumulate is a small, expected follow-up, not yet done).

## Codex

Codex reads skills from `.agents/skills` between the current directory and the repo root,
plus `~/.agents/skills`, and needs only `name`/`description` frontmatter — this repo's
skills already qualify. It does **not** auto-load a skill another skill references (that's
why each skill here says "read `.../SKILL.md` in full" instead of assuming it).

A workspace-root `.agents` symlink (as the root README's "Codex Setup" section describes) is
invisible to Codex when it runs from inside an individual MFE repo, since Codex only looks
between its cwd and *that repo's own* root. Until the symlink setup is reworked repo-wide
(tracked in the open GitHub issues about where `.claude` should live), the reliable path for
this workflow specifically is a **user-level** symlink:

```bash
mkdir -p ~/.agents/skills
ln -s "$(pwd)/.claude/skills/paragon-ui" ~/.agents/skills/paragon-ui
ln -s "$(pwd)/.claude/skills/figma-to-paragon" ~/.agents/skills/figma-to-paragon
ln -s "$(pwd)/.claude/skills/paragon-a11y-check" ~/.agents/skills/paragon-a11y-check
```

There's no Claude-style sub-agent dispatch in Codex — the "Claude Code" sections in each
`SKILL.md` (model/effort routing) don't apply; run everything inline. The Figma MCP is
configured in Codex's own config file; consult Codex's current docs for the exact syntax,
and sign in with your own account same as the Claude Code path.

**Full Codex parity isn't a requirement for this release.** Claude Code is the supported
path; a Codex smoke test (a `paragon-ui` lookup, `figma-to-paragon` up to its plan
checkpoint) is part of Milestone 3, not this one.

## Verifying your own changes to this workflow

```bash
cd .claude/design-system
node --test scripts/test/
node scripts/generate.mjs --paragon <a-real-paragon-install> --check
```

Both must pass before a PR touching `.claude/design-system/` merges (`policy.md` §4). CI runs
the same two checks against a pinned Paragon fetched via `npm pack --ignore-scripts`.
