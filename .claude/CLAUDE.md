# Agent Instructions

This is `openedx-core`: a published Django library of apps used by `openedx-platform`
and community plugins. Treat public APIs as contracts and keep changes small.

## Which skill to use

- Implementing a non-trivial change: use the `spike-and-stabilize` skill.
- Reviewing a PR, branch, or diff: use the `code-review` skill.
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
skill running directly in you (`ticket-writer`, `spike-and-stabilize`, `code-review`,
etc.), are the only ones who call the Agent tool. A dispatched sub-agent — `business-analyst`,
`software-architect`, `Explore`, `general-purpose`, or any other — never calls it itself,
regardless of what its own file says or what tools happen to be available to it. Anything
below about pushing work to a cheaper agent is an instruction for *you*, before or after a
dispatch, not something a sub-agent can act on by itself.

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

Other context-hygiene defaults:

- Read into your own context only the few files the task actually touches. Start from a
  high-level overview and narrow down; don't pull in everything nearby.
- Keep fact-checks bounded by default: one targeted question, a direct answer with a
  confidence caveat. Don't launch multi-pronged research unless deep investigation was
  actually asked for.
- When several dispatches build on each other, check each new finding against earlier
  ones before acting on it. A later dispatch can get a fact wrong that an earlier one
  already had right, and nothing flags the conflict for you.

## Working style

- Think before coding: state your assumptions, and ask when the request is ambiguous.
  Present options instead of guessing silently. Trivial tasks skip this.
- A question is not a work order: answer questions, don't edit code until told to.
  "Why did you do X?" means explain X, not undo it.
- Simplicity first: make the smallest correct change. No unrequested abstractions,
  flexibility, or error handling for impossible cases.
- Reuse before rebuild: prefer existing code, the stdlib, then Django/DRF, then an
  installed dependency, before writing something new.
- Surgical changes: don't refactor or reformat code your task doesn't touch. Match
  existing style. Every changed line should trace to the request.
- Don't extract shared code until three callers need it. DRY is about knowledge, not
  code that happens to look alike.
- Separate confirmed fact from inference or proposal, and say which is which. When
  unsure, flag it rather than asserting it.
- For ambiguous, multi-part design or scoping questions, batch the open questions into
  one round before drafting into a durable artifact (ADR, ticket, PR description). Don't
  draft prose and let a reviewer catch problems in it afterward.
- For a decision with a few distinct options, use a comparison table over paragraphs; it
  verifies faster.

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
