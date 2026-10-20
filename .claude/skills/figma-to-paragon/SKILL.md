---
name: figma-to-paragon
description: "EXPERIMENTAL. Use when implementing a Figma design, or a ticket's design handoff note with screenshots, as Paragon-based React in an Open edX frontend repo — OR when checking an already-built screen against its Figma design (design QA). Reads the project's design source and the ticket's current handoff revision, reads design intent through the official Figma MCP within a call budget or from the handoff note, resolves Figma variables/styles to --pgn-* tokens with the code value winning and unresolved mappings surfaced rather than guessed. In implement mode it plans components, hands coding to spike-and-stabilize, verifies against the shared definition of complete, runs paragon-a11y-check, and writes a deviation report. In QA mode it triages every difference between a design and its built screen with the shared fidelity rubric and suggests fixes only for real code defects. Never writes to Figma, copies Figma-generated code, or changes code to match an off-system Figma value. Takes precedence over generic Figma design-to-code skills in these repos."
---

# Figma to Paragon (EXPERIMENTAL)

Read `.claude/design-system/policy.md` in full before running either mode of this skill — it
defines the mapping contract, the fidelity rubric, handoff authority, and the definition of
`complete` that this skill implements. Also read `.claude/skills/paragon-ui/SKILL.md` in full
(this skill builds on it for token/component/icon lookups); Codex doesn't auto-load a skill
another skill references, so both must be read explicitly here.

## What this is and is not

- Two modes: **implement** (build a screen from a design) and **QA** (check a built screen
  against its design). Pick the one the request actually asks for — most requests right now
  are QA, since much of the target UI is already built.
- It never writes to Figma, never copies code returned by a Figma design-to-code tool, and
  never changes application code to match a Figma value that Paragon disagrees with
  (`policy.md` §0).
- It takes precedence over the installed Figma plugin's own `figma-design-to-code` skill in
  these repos (see "Precedence" below) — that skill's rules (parallel MCP batches, pixel-match
  as the success bar, using its returned code) actively conflict with this one's.

## 0. Locate the repo and the project

Use `paragon-ui`'s repo-location steps. Then find which `.claude/design-system/projects/*.md`
file lists that repo under its Targets table (ask if none does, or if more than one could
apply — a new repo needs a project file added, see `figmaToCodeWorkflow.md` "Adding a
project"). Run `node .claude/design-system/scripts/paragon-versions.mjs <repo-path>`.

## 1. Read the design source and the current handoff revision

1. Read the project's `catalog` field (`projects/<project>.md`) and cross-check it against
   `catalogs.md`.
2. Compare the map header (`figma-paragon-map.json`'s top-level fields) against the project's
   catalog and the installed Paragon. On a mismatch: warn, use the map for **names only**,
   and re-confirm every value against the installed CSS directly (don't trust `codeValue` in
   the map without a live check).
3. Find the ticket's handoff block (per the project's `handoff_location`). Identify the
   **current revision** (`<ticket>-rN`) per `policy.md` §3:
   - A discussion comment after rN is a possible change, not a supersession — list it, ask
     the dev whether it's in scope, don't apply it.
   - A section marked `drift-pending` in the project file is **blocked**; say so and stop for
     that section specifically (other sections may proceed).
   - Any existing approval the handoff cites is recorded in the deviation report, never
     re-requested.
4. No handoff block at all: for implement mode, ask for one (per `ticket-template.md` §4).
   For QA mode, a screenshot plus the ticket's Figma link is enough to start; note in the
   report that a full handoff wasn't available.

## 2. Read design intent

**MCP path** (default — every dev gets a Dev/Full seat):
- Announce the calls before making them. Budget: `mcp_calls_per_frame` from the project file
  (default 3) — typically `get_variable_defs` + `get_screenshot`, plus `get_design_context`
  only when structure or annotations are actually needed. Never batch calls in parallel (that
  is the conflicting plugin skill's behavior, not this one's).
- Use MCP output for **names, layout, and annotations only**. Never copy generated code or
  literal hex/px values from it — those get resolved through the map (§3) instead.
- `get_variable_defs` output: save it, then run
  `node .claude/design-system/scripts/map-figma.mjs <saved-file>` to check it against the
  committed map. Any `DRIFT` or `UNKNOWN` result means the catalog is stale — say so and
  proceed with the committed map's names (don't block on a catalog refresh mid-ticket).
- Any MCP error: don't retry. Fall back to the handoff path and note the fallback in the
  report.
- View/Collab seat, or no MCP tools available at all: go straight to the handoff path. One
  `get_variable_defs` call only with the dev's explicit opt-in.

**Handoff path** (screenshots + the handoff block): never sample a color or measure spacing
from a screenshot. Anything the handoff block doesn't state is an open design question, not
an inference.

## 3. Resolve every token, component, and icon

Follow `paragon-ui` §§2-4 for each name found in step 2. Per `policy.md` §1: confirmed
statuses get used directly (with `value-differs` called out); unresolved statuses (`value-only`,
`ambiguous`, `figma-only`) are never auto-picked — list them with their candidates.

For components: also check `paragon-ui/references/component-guide.md`'s Figma-name table.
Name the WAI-ARIA APG pattern for any custom widget before planning it. Check
`.claude/design-system/paragon-gaps.md` for net-new items before writing any code for one.

## Implement mode

4. **Plan.** Enter `spike-and-stabilize` step 2 (clarify-and-plan) with: the component table,
   the token table (confirmed + unresolved, with candidates), gaps found, the handoff
   revision, and the file list. **One approval covers both skills** — don't ask twice.
5. **Build** via `spike-and-stabilize` steps 3-4 (spike, then stabilize), following the
   target repo's own `AGENTS.md`/`CLAUDE.md` conventions throughout (TypeScript, `messages.ts`
   with descriptions, `var(--pgn-*)` in SCSS, utility classes before custom CSS, relative
   typography units).
6. **Verify** against `policy.md` §4:
   - The repo's own types/lint/stylelint/tests.
   - `node .claude/design-system/scripts/check-tokens.mjs --diff <base-ref> <changed-paths>`
     from the repo root — must be clean (no `unknown-token` errors).
   - Run `paragon-a11y-check` (read its SKILL.md in full) for both the inspected and observed
     a11y checks §4 requires.
   - Optional: a screenshot at the frame's viewport (the `run-frontend-app-authoring` recipe,
     where applicable) compared against the Figma screenshot.
7. **Report.** Write the status (`complete` or `incomplete` with reasons) and a deviation
   report as a block for the dev to paste into their own PR body (an assist, like testing
   instructions — PR bodies stay human-written). Contents: handoff revision cited; Figma vs
   code for every `value-differs`/unresolved item, with both values; net-new UI; Paragon
   gaps; unverified/skipped checks; what came from the MCP vs the handoff vs was inferred. No
   `.claude` paths in it — PRs are public. Remind the dev about the ADR 0002 output
   evaluation, then run `frontend-code-review` (or the target repo's equivalent) as the final
   step.

## QA mode (checking an already-built screen against its design)

1. Locate the screen's source files (ask if not obvious from the ticket) and the design
   (frame link, or the handoff's screenshots).
2. Read intent per §2 (same MCP budget and rules).
3. Run the scripts against the screen's files: `check-tokens.mjs` (hardcoded values, unknown
   tokens) and, if a live MCP capture was taken, `map-figma.mjs` (each variable/style's map
   status).
4. Compare design and code by **components, tokens, layout, content, and states** — never by
   pixels (`policy.md`'s fidelity standard).
5. **Triage every difference** into one of the four `policy.md` §1 buckets: code defect,
   Figma issue (code wins, no code change), open design question, accepted variance.
6. **Report** a triage table: difference | bucket | evidence | suggested action.
   - Code-defect fixes are suggestions only; applying any of them goes through the normal
     `spike-and-stabilize` plan-approval gate, same as implement mode.
   - Figma issues and open design questions go to the designer (via `paragon-gaps.md` if
     they're Paragon-level, or directly in the report otherwise).
   - Anything whose evidence isn't available (e.g. no MCP capture and only a rough
     screenshot) is `unverified`, not silently skipped from the table.

## Precedence over `figma-design-to-code` (the installed Figma plugin's skill)

- No parallel `get_design_context`/`get_variable_defs` batches — calls in this skill are
  announced and sequenced against the budget in §2.
- Code values beat a pixel-perfect match with the screenshot — the fidelity standard in
  `policy.md` is the bar, not visual identity.
- Paragon's own icon set beats a downloaded/inlined SVG.
- Never use code returned by `get_design_context` directly (§2).

If the Claude Code session loaded `figma-design-to-code`'s instructions for a task this skill
also matches, this skill's rules win for anything in an Open edX frontend repo under this
workflow.

## Claude Code: model dispatch

A design-intent read (§2) and an implementation build (`spike-and-stabilize`'s spike/stabilize
steps) go to a Sonnet `general-purpose` sub-agent, briefed with the plan and told not to
dispatch further sub-agents itself (only the top-level session dispatches). A simple
existence check (does this token exist in the installed CSS) can go to Haiku. Planning
(clarify-and-plan) and the final review stay in the top-level session on the strong model, per
the target repo's own delegation rules if it has them (`openedx-core`'s `CLAUDE.md` has one;
frontend repos generally don't yet). Codex: run all of this inline; there's no equivalent
sub-agent dispatch.

## When blocked

- No design and no handoff block: ask for one (implement mode) or proceed QA-only from a
  screenshot, labeled partial (QA mode).
- A Paragon gap blocks progress: offer three options — compose from existing Paragon parts,
  build a local component on tokens (flagged in `paragon-gaps.md`), or raise it upstream and
  defer the ticket. Don't pick silently.
- Acceptance criteria conflict with the design: the AC wins for behavior; ask which should
  change.
