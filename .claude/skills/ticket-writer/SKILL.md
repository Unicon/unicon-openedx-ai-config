---
name: ticket-writer
description: Interactive authoring or review of a feature ticket before development for this Open edX library, with the user in the loop. Use when asked to write, draft, review, refine, scope, sanity-check, or improve a ticket, issue, requirement, or feature idea, and you want to dig into the requirements by asking the human the questions that actually change the ticket. Dispatches the business-analyst and software-architect experts, surfaces their questions to the user, folds the answers back in, and produces a solid ticket in the canonical format (.claude/ticket-template.md) plus the findings behind it. Advisory: does not change code or post to trackers unless asked and approved.
---

# Ticket writing and review

Turn a bare feature idea or a rough ticket into an excellent one by interrogating the
requirements with the user in the loop. Two experts do the deep work as consultants hired to
roll out the feature: the `business-analyst` recovers the true intent and requirements
quality; the `software-architect` scopes it and designs the approach. What makes this skill
different from a one-shot pass is the clarification loop: the experts surface the questions
whose answers would actually change the ticket, you relay those to the user, get answers, and
continue the same experts with that new information before anything is finalized.

Read `.claude/ticket-template.md` first: it is the canonical format (the required and
optional sections, who owns each, the User Story and Acceptance Criteria as the core of
the ticket, and the stub and design-spike shapes). This skill owns the *workflow*; the
template owns the *format*. For competency, skills, or CBE work, also read
`.claude/cbe-project-context.md`.

This is advisory. It produces an assessment and drafted ticket text; it does not change code.
Apply changes to the real ticket (edit the issue, post a comment) only when explicitly asked,
and after the user approves the wording.

## Model and orchestration

You, the top-level session, orchestrate. `business-analyst` and `software-architect` are
pinned to Opus at `xhigh` effort in their own frontmatter, so dispatch them with the Agent
tool without a `model` override. Per the Delegation rule in `CLAUDE.md`, neither expert has
an Agent tool and neither dispatches a sub-agent itself: when one needs context-heavy
reading it wasn't given (a location lookup, reading/reasoning over large docs or many
files, a web lookup), it returns a "Needs research" item in its output instead of fetching
it. You fulfill those the same way you fulfill open questions — dispatch on its behalf
(`Explore` on Haiku for location, `Explore` or `general-purpose` on Sonnet for
read-and-reason and web) and continue it via `SendMessage` with the result. Do not read
large docs or run web lookups inline yourself either.

The experts are sub-agents and **cannot talk to the user**. You are the only one who can. So
every question they raise, and every research need, comes back in their output, and you
broker it: collect, dedupe, prioritize, ask the user with `AskUserQuestion` (for open
questions) or dispatch directly (for research needs), then continue the expert with the
result via `SendMessage` (which preserves its context). Keep each expert's agent id from the
Agent tool so you can continue it.

## Section ownership

- **Business-analyst** owns User Story, Acceptance Criteria, the optional Description, and
  Open Questions raised from a requirements angle (and, for a design spike, Context for the
  Designer in place of Technical Details and Files).
- **Software-architect** owns Technical Details, Files to create and modify, and the code
  and prior-art parts of Context.

The business-analyst surfaces the need for a split or a technical concern but does not design
it; the software-architect designs but does not rewrite the user story.

## Cross-repo scope: frontend and edx-platform

Many tickets here also touch code outside this repo. Understand the neighbor from its
orientation doc first, and reach into the neighbor's actual code only when the doc is not
enough. Tell the experts to do the same, and that when the doc is not enough, the move is a
"Needs research" item back to you, not a dispatch of their own.

- **Authoring frontend** (`frontend-app-authoring`, the Studio MFE, external to this
  workspace at `../frontend-app-authoring`). For any ticket with a frontend part, understand it
  from `.claude/frontend-app-authoring-architecture-overview.md`: the MFE's architecture,
  conventions, and how it connects back to this repo's APIs. Only where that overview is not
  enough, dispatch a low-cost `Explore` or `general-purpose` sub-agent on **Sonnet**, on the
  expert's behalf, with a narrow question against a small, specific set of files there, and
  continue the expert with the answer via `SendMessage`. Never read the repo into the main
  context.

- **openedx-platform** (the monolith, formerly `edx-platform` -- still commonly called that in
  issues, PRs, and discussion; recognize both, external at `../openedx-platform`). It is huge,
  so protect context aggressively. Start from `.claude/architecture-overview.md`, which covers
  how it integrates this library (the `content_libraries` and `content_tagging` layers). Prefer
  that overview to opening the monolith at all. Only where strictly necessary, dispatch a
  **Sonnet** sub-agent on the expert's behalf with a very narrow question pointed at a very
  small, specific selection of files in `../openedx-platform`, and instruct it to be
  protective of its own context: read excerpts, not whole files, and return only the answer.

## 1. Intake

Identify what you are working from and gather the ground truth:

- Pasted text: use it. A file path: read it. A GitHub issue: `gh issue view <n> --comments`.
  A URL or other tracker (Jira and similar): delegate the fetch to a Sonnet sub-agent, never
  inline. A bare feature idea with no ticket: treat it as a request to draft a new ticket.
- Collect any related or blocking tickets and backlog the user points at, by **GitHub issue
  number** — the architect needs them to judge split and merge boundaries. Never carry over
  an internal ticket ID or a spreadsheet reference.
- Skim `.claude/ticket-template.md` (and `cbe-project-context.md` for competency work). If the
  request has a frontend or edx-platform part, read the relevant overview named in the
  cross-repo section.

If there is neither a ticket nor a feature request to work from, say so and stop.

## 2. Requirements pass (business-analyst)

Dispatch the `business-analyst` agent with an excellent, self-contained prompt. Give it the
ticket or idea verbatim, the related tickets, and the context you gathered, and ask it to
return, grounded in the actual repo:

- **True intent**: the real Open edX role and the "in order to"; where the request optimizes
  for the wrong thing or gold-plates past the outcome.
- **Findings**, grouped and anchored to the text: Missing / Open question / Contradiction /
  Outdated / Improvement.
- **SMART scorecard** and a **1-2 developer-day feasibility flag**.
- **Its owned sections** drafted in the canonical format: a one-sentence User Story ("As a
  &lt;role&gt;, I want &lt;capability&gt;, in order to &lt;outcome&gt;" — or, for the rare
  ticket genuinely covering more than one story, a short plain-English bulleted list
  instead of forcing one sentence), Acceptance
  Criteria as Given/When/Then scenarios describing observable behavior only (this applies
  even to backend/data-model tickets with no UI — phrase the outcome in terms of what's
  observed, not the mechanism; for a frontend part, cover the UI states using the frontend
  overview for what is realistic), and a Description only if something essential doesn't
  fit in the User Story or AC (a few terse sentences, never technical, never why the ticket
  is blocked or unsplit).
- **OPEN QUESTIONS for the human** as a clean, prioritized list it knows you will relay. Tell
  it to format each as:
  `[BLOCKING|non-blocking] <crisp question> (why it matters: <one line>). Options: A) … B) … [recommended: X]`
  Only questions whose answer would actually change the ticket. 2-4 candidate answers each,
  with a recommended default, so the user can decide fast. Blocking questions are ones the
  ticket cannot be written correctly without.
- **NEEDS RESEARCH**, for anything it would otherwise fetch or explore itself but wasn't
  given: what it needs and why, in the same list shape. You resolve these yourself (dispatch
  or answer directly), never by asking the user.

Keep its agent id. Reason over its summary; do not redo its reading.

## 3. Clarify the requirements with the user (loop)

If the business-analyst raised blocking questions, resolve them before design:

1. Merge and dedupe the questions, blocking first. Drop any the intake already answers.
2. Ask the user with `AskUserQuestion`: up to four per call, batching across calls if there
   are more (blocking first). Map each expert question to one item: the question text, a short
   `header`, and the expert's 2-4 candidate answers as options with the recommended one first,
   labeled "(Recommended)". Do not add an "Other" option; the tool always offers free text.
   Use `multiSelect` only when several answers can genuinely coexist.
3. Continue the business-analyst via `SendMessage` with the user's answers (and any free-text
   notes). Ask it to fold them into its sections and to raise any *new* blocking question the
   answers created.
4. Repeat only while new blocking questions appear, and cap it: after about two rounds, stop
   and treat any residual unknown as a TBD or a stub per the template rather than interrogating
   further. Non-blocking questions can ride along as open questions in the final ticket.

If the user defers a blocking question ("I don't know yet", "decide later"), do not guess:
mark it TBD, and if the whole ticket hinges on it, produce a stub (title plus a one-line
blocker note) and say the full ticket comes after the decision is documented.

## 4. Scoping and design pass (software-architect)

Dispatch the `software-architect` agent with the ticket, the clarified requirements and the
business-analyst's refined sections, and the related tickets. Ask it to return, grounded in
the code:

- **Scope verdict**: ready / refine / split / merge, with the seams named (layer, applet, API
  vs model vs migration, backend vs surface); its own SMART and 1-2 developer-day feasibility
  read; and the ticket-level architecture risks (stable-API impact and DEPR, layer crossing, a
  new model and PII, a migration, a warranted ADR).
- **Technical design**: the constraints and forces, at least three genuinely different
  approaches with their tradeoffs, and one recommended approach (simplest correct, cleanest,
  reuses before it rebuilds), justified against the rest. When the work spans repos, trace the
  full chain and name which layer each piece lands in (this repo, `content_libraries` or
  `content_tagging` in edx-platform, the MFE feature), using the overviews per the cross-repo
  section and a Needs Research item, per that section, wherever a narrow Sonnet lookup is
  necessary.
- **Its owned sections** in the canonical format: Technical Details written in two parts,
  opening with a note that it's background and a suggestion rather than the ticket's
  source of truth — "In short", a few plain-language paragraphs (one per major mechanism
  or decision, each with a bold lead-in phrase) that a non-specialist can follow, then
  "Implementation specifics", one bullet per concrete fact the prose doesn't spell out
  (exact signatures, file/function locations, specific methods, migration shape, test
  cases); Files to create and modify (two tables, one line per file); and the code and
  prior-art Context. Hold Technical Details to the standard in `.claude/ticket-template.md`:
  intent and contract captured in both parts, structured In short then Implementation
  specifics, aggressively DRY between them, companion-ticket work marked out of scope and
  referenced by GitHub issue number. No Example Resolution Prompt or other closing
  implementation-plan prompt — the User Story, Acceptance Criteria, and Technical Details
  are what the implementer needs. **Technical Details is required, not optional** — even a
  small ticket gets a short "In short" paragraph and a couple of Implementation specifics
  bullets (the one exception is a design spike, which has no Technical Details at all).
  Technical Details, Files to create and modify, and Context each go in their own
  collapsible `<details>` block per the template.
- **OPEN QUESTIONS for the human**, in the same format as the business-analyst's, usually
  fewer and more technical (a scope call, a contract tradeoff, a placement decision).
- **NEEDS RESEARCH**, in the same shape as the business-analyst's, for anything it would
  otherwise fetch or explore itself but wasn't given. You resolve these yourself.

For a design spike, ask for scope judgment only; the business-analyst owns Context for the
Designer in place of Technical Details and Files. Keep the architect's agent id.

## 5. Clarify the design with the user (loop)

Run the same loop as step 3 for the architect's blocking questions: ask with
`AskUserQuestion`, continue the architect via `SendMessage` with the answers, cap the rounds,
and defer the unresolvable to TBD.

## 6. Synthesize

Combine the two into a complete draft ticket, verdict first and skimmable (step 7
finalizes it):

- The assembled ticket in the canonical format (`.claude/ticket-template.md`): User Story,
  Acceptance Criteria, and Technical Details (required) as the core, plus only the optional
  sections (Description, Files, Context, Open Questions) that earn their place, with
  Technical Details, Files, and Context each wrapped in its own collapsible `<details>`
  block and everything else left open on the page, with BA-owned and architect-owned content merged into one coherent
  ticket reflecting the answers you gathered. For a bare idea this is the drafted ticket;
  for a review, the improved one. For a split, one ticket per sub-ticket, cross-referenced
  by GitHub issue number.
- The findings behind it: true intent and whether the ticket serves it; the questions that
  were answered and how they shaped the ticket; any remaining open questions or TBDs, blocking
  ones first; the scope verdict with any split or merge; the SMART scorecard and an effort
  estimate; and the rejected technical alternatives in one line each.

## 7. Editorial cleanup and fidelity check

The step 6 draft is not the deliverable yet. Run one editorial pass over it, then verify
the pass changed only the writing.

1. Dispatch a sub-agent (`Agent`, **no `model` override** so it runs on your model) and
   have it invoke the `clean-up-ticket` skill on the draft: pass the ticket text or its
   file path, and ask it to return the cleaned rewrite plus its "what changed and why"
   changelog. That skill tightens structure, removes redundancy and line numbers, leads
   with the change, and rewrites toward the template, without touching scope.
2. **Verify fidelity yourself** (a final-review job, keep it on the strong model). Compare
   the cleaned version against the step 6 draft, using the changelog as a guide. Confirm
   every change is editorial (structure, order, deduplication, wording, dropped line
   numbers, a BLUF lead) and that nothing material was lost or invented: every requirement,
   acceptance-criterion behavior, constraint, out-of-scope item, file reference, and
   factual claim must survive with its meaning intact. The cleanup preserves scope by
   design; this step confirms it actually did.
3. If the pass dropped, altered, or invented any content, restore it (or re-run the cleanup
   with a correction) before delivering. Do not ship a cleaner but subtly wrong ticket.
4. Deliver the cleaned, verified version as the final ticket; the step 6 draft is
   scaffolding.

Touch the real tracker only on explicit request and approval.
