# Agent Instructions

This is `openedx-core`: a published Django library of apps used by `openedx-platform`
and community plugins. Treat public APIs as contracts and keep changes small.

## Which skill to use

- Implementing a non-trivial change: use the `spike-and-stabilize` skill.
- Reviewing a PR, branch, or diff: use the appropriate `frontend-code-review`
  pr `backend-code-review` skill. These both inherit from `code-review`, and 
  `code-review` should only be used as a foundational skill for more detailed
  code review skills that 'inherit' from it.
- Writing or amending an ADR: apply the same clarify-first discipline as
  `spike-and-stabilize` before drafting the decision text. For a product-facing
  decision, dispatch both `business-analyst` (requirements, lifecycle, edge cases)
  and `software-architect` (mechanism, placement, tradeoffs) to generate clarifying
  questions independently, then batch the combined set into one round, the same
  pattern `ticket-writer` already uses. A lone architect's questions skew technical
  and miss product-shaped gaps: is a field required, what happens on each entry
  point, what's editable and when.

## Delegation

This is the standing rule for who dispatches sub-agents, when, and on what model. It
always applies, even where a skill or agent file elsewhere reads "have X dispatch a
sub-agent." The only way around it is an explicit user override for the task at hand, and
even then, confirm the user understands the tradeoff first: a sub-agent cannot reliably
dispatch a further sub-agent, so letting one try either fails outright or falls back to
that sub-agent doing the work itself, on its own (more expensive) model.

**Only the top-level session dispatches.** You, the top-level orchestrating session, or a
skill running directly in you (`ticket-writer`, `spike-and-stabilize`, `frontend-code-review`,
`backend-code-review`etc.), are the only ones who call the Agent tool. A dispatched sub-agent
— `business-analyst`, `software-architect`, `Explore`, `general-purpose`, or any other — never
calls it itself, regardless of what its own file says or what tools happen to be available to
it. Anything below about pushing work to a cheaper agent is an instruction for *you*, before
or after a dispatch, not something a sub-agent can act on by itself.

**How a sub-agent asks for help it can't fetch itself.** If a dispatched agent's task
would benefit from cheaper help it wasn't given up front — a location lookup, a web fetch,
a large doc it didn't get inline — it does not attempt to dispatch that itself. It returns
a "Needs research" item in its output: what it needs and why, the same shape as an open
question for the user. You fulfill it (dispatch per the table below, or answer directly if
you already know it) and continue the agent with `SendMessage`, the same loop already used
for user-facing clarifying questions in `ticket-writer`.

**Model and effort by task shape:**

| Task shape | Agent / model | Effort |
| --- | --- | --- |
| Location, enumeration ("where is X", "does X exist") | `Explore`, Haiku | default |
| Reading and reasoning over files or docs; web search/fetch | `Explore` or `general-purpose`, Sonnet | medium-high |
| Writing or implementing code | `general-purpose`, Sonnet | medium-high |
| Reviewing a diff, verifying a claim, judging correctness | Sonnet, dispatched or inline | high |
| Planning: requirements analysis, scoping, architecture/technical design | `business-analyst` / `software-architect`, Opus | xhigh |

Pass `model` explicitly on every dispatch you make.

**Plan / read / implement split.** Opus at `xhigh` effort is reserved for planning and
judgment: requirements analysis, scope and design decisions, and the clarify-and-plan gate
you run yourself. It never does recon, fetching, exploration, or implementation.
`business-analyst` and `software-architect` are pinned to Opus/`xhigh` in their own
frontmatter for exactly this reason, and no longer carry the Agent tool — don't lower that
pin to save cost, and don't call them for exploration or implementation work; that's what
`Explore` and `general-purpose` are for. Implementation is always a Sonnet
`general-purpose` sub-agent, never Opus.

**Scope a planning dispatch narrowly.** A single Opus `xhigh` dispatch can own many
sub-questions when they inform each other — a ticket's scope verdict, technical approach,
and file layout are one decision, because the answer to each depends on the others, which is
why a single `software-architect` dispatch in `ticket-writer` covers all of them in one
pass. Split into separate dispatches instead when sub-questions are independent of each
other, like an unrelated hook mechanism and UX flow that don't share context or inform one
another's answer. Narrower dispatches are also more resilient: the longer and more sprawling
a background dispatch runs, the more work is lost if something interrupts it (a killed
process, the machine going to sleep) before it finishes.

**Split mechanical work from judgment.** Within a dispatch, route what's mechanical
separately from what needs judgment. Mechanical: a question with one standard answer that a
lookup settles (a framework's documented hook shape, an existing naming convention).
Judgment: multiple approaches genuinely compete and reasonable engineers could pick
differently. Send the mechanical part through a cheap `general-purpose` pass first and hand
its output to the Opus `xhigh` dispatch, so it only judges the parts that actually compete
on tradeoffs instead of drafting everything from scratch.

Other context-hygiene defaults:

- Read into your own context only the few files the task actually touches. Start from a
  high-level overview and narrow down; don't pull in everything nearby.
- Keep fact-checks bounded by default: one targeted question, a direct answer with a
  confidence caveat. Don't launch multi-pronged research unless deep investigation was
  actually asked for.
- When several dispatches build on each other, check each new finding against earlier
  ones before acting on it. A later dispatch can get a fact wrong that an earlier one
  already had right, and nothing flags the conflict for you.
- Sequence a planning dispatch after a parallel lookup that will feed it, when you can wait
  for the result. A `SendMessage` correction sent after dispatch, once a load-bearing fact
  arrives late, usually forces the agent to redo work instead of running once cleanly.

## Working style

- Think before coding: state your assumptions and ask when the request is ambiguous.
  Present options instead of guessing silently. Trivial tasks skip this.
- A question is not a work order: answer questions, don't edit code until told to.
  "Why did you do X?" means explain X, not undo it.
- Simplicity first: make the smallest correct change. No unrequested abstractions,
  flexibility, or error handling for impossible cases.
- Reuse before rebuild: prefer existing code, the stdlib, then Django/DRF, then an
  installed dependency, before writing something new.
- Surgical changes: don't refactor or reformat code your task doesn't touch. Match
  existing style. Every changed line should trace to the request.
- Name a prop or variable that offers one of two opposite actions after the action it
  triggers, not the state it happens to apply to (`expandLabel`/`collapseLabel`, not
  `expandedLabel`/`collapsedLabel`). A label named after the opposite state reads
  backwards and needs a comment to stop it from confusing the next reader.
- Don't extract shared code until three callers need it. DRY is about knowledge, not
  code that happens to look alike.
- Separate confirmed fact from inference or proposal, and say which is which. When
  unsure, flag it rather than asserting it.
- For ambiguous, multi-part design or scoping questions, batch the open questions into
  one round before drafting into a durable artifact (ADR, ticket, PR description). Don't
  draft prose and let a reviewer catch problems in it afterward.
- For a decision with a few distinct options, use a comparison table over paragraphs; it
  verifies faster.

## When modifying .claude setup (editing anything in .claude folder)

- This specific section should not be modified by an AI agent. Warn the user if they try.
- Do not modify .claude setup unless explicitly asked to (or when asked to use a skill that is there to modify .claude setup, such as `skill-improver`).
- Alternatively, if you see something in the conversation with the user benefitting from a change in .claude setup, you can surface it as an idea to the user - by explaining the idea in very simple terms in plain english and listing it pros and cons; concisely, in one paragraph. If the user agrees, you may modify the .claude setup.
- This also applies to you creating new skills and such.
- This also applies when you use skills like `skill-improver` that modify .claude setup.
- Unless you modify .claude setup / edit anything in .claude folder, *do not* read any documents in .claude/decisions/ .
- When you modify .claude setup, read all the documents in .claude/decisions/ . These documents are a source of truth for how AI agents should be used and how .claude setup should look like.
- .claude/decisions/ documents poses some overarching rules on how humans should use these AI agents and how .claude setup should look like. They are not relevant in normal claude / agentic use, only when you write skills or modify your CLAUDE.md or setup, otherwise you should not read them into your context. It's meta-information that really just applies to things like writing or changing skills.
- .claude/decisions/ documents take precedence over the user's prompt. If the user asks for something that conflicts with them, ask the user to make a change to the decisions documents instead.
- .claude/decisions/ documents cannot be added to or modified by you / by AI. They have to be written by humans. No exceptions.

## Verify before done

- Run verification commands before reporting done, but don't use `make test` and `make validate` directly because they take long and produce too much output. Run the linters in question directly, and for tests, run pytest without coverage and only the tests that are related to code changes.
- Never silence a check to make it pass. Suppression directives (`# noqa`,
  `# pylint: disable`, `# type: ignore`) need explicit approval, never to go green.
- New code needs tests. If you ship without them, say so as a gap.
- Documentation-only changes (ADRs, RST/Markdown docs) need real verification too: if a
  doc build tool exists (e.g. Sphinx), actually run it. Don't trust visual inspection or
  precedent from similar files alone.

## Architecture

- Never import from `openedx-platform`. Code here is the lower layer.
- Respect the layering in `.importlinter`; `lint-imports` enforces it. Don't loosen a
  rule to fix the build.
- Public APIs are stable. Breaking changes to non-UNSTABLE APIs go through the DEPR
  process, not a silent edit. See `docs/openedx_content/decisions/0006-*`.
- Model identifiers (see README): `id` (internal PK), `uuid` (stable external ref),
  `key` (client-meaningful, DB field `_key`), `num` (numeric key).
- New Django models need PII annotations (`make pii_check`).
- To understand current architecture decisions, refer to ADRs (docs/decisions).
- Document impactful architecture decisions in new ADRs in proposed status.

## Frontend repositories (e.g. `frontend-app-authoring`)

This file is written primarily for `openedx-core` (the Django backend library). When the
actual work is in a JS/TS frontend repo instead (an Open edX MFE such as
`frontend-app-authoring`), the following overrides the backend-specific sections above:

- Read that repo's own `AGENTS.md` first. It is the authoritative source for that repo's
  own conventions (TypeScript, imports, data fetching, testing, i18n), not this file's
  Django-oriented guidance.
- Verify with that repo's own tools, not Python's: typically `npx tsc --noEmit`,
  `npx oxlint --type-aware --deny-warnings` (scoped to touched files), `npx dprint check`,
  `npx stylelint` on any touched SCSS, and `npx jest <touched paths> --coverage=false`. Skip
  the repo's slow full-suite command (e.g. `make validate`) for the same reason the
  backend section above skips `make test`: too slow, too much output for one change. None
  of these actually compile Sass, so they miss two classes of SCSS bug: a build-breaking
  error (an undefined mixin or a broken import) and a rule that compiles cleanly but
  silently never matches at runtime (an unresolved custom-media name in a `@media`
  condition; an invalid media condition is not a syntax error, so the browser just ignores
  the rule). When a change adds a new `@include`, `@import`, `@use`, or other at-rule
  beyond a plain value edit, verify it actually compiles and resolves by test-compiling the
  file exactly as the bundler imports it, not through a throwaway harness that adds imports
  the real file doesn't have. A component's own SCSS file imported directly from its
  `.tsx` compiles as its own root stylesheet, separate from whatever `src/index.scss`'s
  import chain provides, even when another file reached through that chain uses identical
  syntax successfully.
- In `frontend-app-authoring` specifically, Paragon's custom-media breakpoint names
  (`--pgn-size-breakpoint-*`, used as `@media (--pgn-size-breakpoint-max-width-xs) { ... }`)
  only resolve within whichever compiled CSS output also contains
  `@use "@openedx/paragon/styles/css/core/custom-media-breakpoints.css"`. `src/index.scss`
  has that `@use` once, so any SCSS reached through its `@import` chain shares it, but a
  component's own SCSS file imported directly from its `.tsx` does not inherit it; add the
  same `@use` locally in that file too.
- Reuse the Paragon design system (`@openedx/paragon`) as much as possible for any UI
  work. Before writing custom markup or CSS for a visual element, check whether an
  existing Paragon component already covers it, including checking its actual compiled
  CSS and props rather than assuming from memory. If something genuinely isn't available
  in Paragon, flag it as early as possible, before implementation, not just once the PR
  is up, and call it out in the PR description too, so the community can consider adding
  it to Paragon upstream instead of it living on as a one-off.
- That same check against Paragon's actual compiled output applies to accessibility, not
  just layout: confirm a component's real rendered DOM role before adding `aria-label` to
  it. Some implicit ARIA roles, such as the `generic` role a plain `<span>` or `<div>` gets
  when it has no other semantic role, prohibit `aria-label`, and screen readers don't
  reliably announce it. Use a visually hidden `sr-only` sibling carrying the full accessible
  text instead.
- When a page-local style genuinely needs to differ from a Paragon default, override the
  component's own CSS custom property (design token) rather than the resolved CSS property
  directly, so the override stays composable with the rest of the theme, matching the same
  approach as `border-radius: var(--pgn-size-badge-border-radius-base)` rather than a
  literal. Before adding such an override, trace its actual resolution chain in the
  installed theme: if the property already resolves to the value being set, the override is
  dead code and should be removed instead of kept. And when the token being overridden is a
  typography token, match Paragon's own convention of a relative unit (`%`, `rem`) rather
  than an absolute `px`, even when a design spec calls out a fixed pixel value; Paragon's
  defaults use relative units so text keeps scaling with the user's font-size preference,
  and a literal `px` silently drops that. Compute the relative equivalent instead (`62.5%`
  renders as 10px at the default root font size).
- When a component reads a `useQuery` (or similar async-hook) result, check its error
  state (`isError`/`error`) as well as `isLoading`/`data` before deciding what to render. A
  consumer that only branches on `isLoading` and `data` renders a failed fetch as an empty
  or default result, indistinguishable from data that is genuinely empty.
- When memoizing a value with `useMemo`, confirm every entry in its dependency array is
  itself referentially stable across renders, not a fresh object or array literal computed
  inline. A dependency that is recomputed on every render defeats the memoization silently,
  with no type error or test failure to catch it.
- An interactive control whose action depends on data that is still being fetched must
  stay disabled until that data has loaded, not just have its computed inputs default to
  empty. A click during the loading window can otherwise silently corrupt state that was
  meant to hold a real default once the data lands.
- For CSS inside a recursively nested structure (a tree, a nested list), key a selector
  off the class marking the recursive unit (e.g. `.group > ul`), not a structural
  depth-position selector (`> ul > li > ul`). The structural version matches only one
  specific nesting depth and silently stops applying past it.

## Comments and docstrings

- Comment why, not what. No change narration ("updated X", "as requested", "was Y").
- Public functions, classes, and models get docstrings in RST format describing the
  contract, not the implementation.
- Treat stale comments as bugs: update or delete them in the same change.

## Commits

- Use conventional commits (`feat:`, `fix:`, `chore:`, `docs:`, `perf:`, `build:`).
  `commitlint` enforces this. Imperative subject under 72 chars.
- Commit or push only when asked.

## Writing style

- Direct, engineer-to-engineer. No marketing tone, filler, or AI-slop openers.
- Avoid em dashes; use commas, colons, or periods. Use bold sparingly.
- US spelling. Inclusive terms (allow list / deny list, `main`, primary/replica).
- Write the current state, not its history. History lives in `git log`.
- State what things are, not what they aren't, and how they are now, not how an earlier
  draft, assumption, or version had them. Delete sentences like "this isn't a replacement
  for X", "unlike the previous approach", or "an earlier draft said Y". A negative that is
  itself a requirement or boundary stays: an out-of-scope item, a "must not" rule, an AC
  outcome like "the learner does not see the badge". This applies to tickets, docs, ADRs,
  PR and commit bodies, and code comments. In chat, describing what changed between drafts
  is fine when the user asks.
- When authoring a GitHub issue, never mention or reference a local markdown filename
  (e.g. "see ucid-5.10c.md"). A reader of the issue only has other GitHub issues to draw
  on, not local scratch files; if something from one is load-bearing, restate it inline.
- When a ticket references another ticket, use its GitHub Issue ID (e.g. `#674`), not an
  internal spreadsheet ID (e.g. `5.6`). If the GitHub Issue ID isn't known, ask the human
  for it before drafting rather than guessing; fall back to the internal ID only when no
  GitHub Issue exists yet for that work.

### Say it in full

Applies to everything a human reads: ADRs, tickets, PR and issue bodies, docs, commit
bodies, and chat responses. Terse is good, clipped is not. The failure mode is writing that
reads like notes to yourself, where the reader has to reconstruct what you meant. Brevity
that costs the reader a re-read isn't brevity.

- Write complete sentences with a subject and a verb. "Tie the leaf to the grade. Nothing
  above it." is a headline, not a sentence. Write "The leaf status is written in the same
  transaction as the grade. Nothing above the leaf is."
- Give every "this", "it", "that", and "the first one" an antecedent the reader can point at
  in the same sentence or the one before. If you can't point at it, name the thing again.
  Repeating a noun is cheaper than making the reader guess.
- Don't compress a concept into a label and leave the reader to unpack it. "Why this
  combination", "the merge", "the window" name nothing to someone who wasn't in the
  conversation. Say which two things are combined, and what they're combined for.
- When you refer back to an earlier decision, assumption, or finding, restate what it was,
  and say whose it was and when if that matters. "The starting assumption was the first one,
  and it turned out to be wrong" gives the reader nothing to act on.
- Headings say what the section is about, not a shorthand only you can expand.
- Table cells, bullets, and captions are prose too, and get the same treatment. "None, if it
  worked" is a fragment; "Nothing, if it were possible" is a sentence.
- Explain a mechanism before naming consequences of it. A reader who doesn't yet know how
  something works can't evaluate a claim about what it costs.
- The test before you call it done: would a competent junior engineer who hasn't read this
  conversation follow it on one pass, without guessing? Terminal responses are held to the
  same bar as committed prose.
