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

Read `.claude/ticket-template.md` first: it is the canonical format (the six sections, who
owns each, the acceptance-criteria rules by ticket type, the Example Resolution Prompt, and
the stub and design-spike shapes). This skill owns the *workflow*; the template owns the
*format*. For competency, skills, or CBE work, also read `.claude/cbe-project-context.md`.

This is advisory. It produces an assessment and drafted ticket text; it does not change code.
Apply changes to the real ticket (edit the issue, post a comment) only when explicitly asked,
and after the user approves the wording.

## Model and orchestration

You, the main session on the strong model, orchestrate. Dispatch the two experts with the
Agent tool and **no `model` override**, so they inherit your model and their judgment runs on
the strong model; both push their own context-heavy reading down to cheaper sub-agents
(`Explore` on Haiku for location, `Explore` or `general-purpose` on Sonnet for read-and-reason
and web). Do not read large docs or run web lookups inline.

The experts are sub-agents and **cannot talk to the user**. You are the only one who can. So
every question they raise comes back in their output, and you broker it: collect, dedupe,
prioritize, ask the user with `AskUserQuestion`, then continue the expert with the answers via
`SendMessage` (which preserves its context). Keep each expert's agent id from the Agent tool
so you can continue it.

## Section ownership

- **Business-analyst** owns Use Case, Description, Acceptance Criteria, and the non-code parts
  of Context (and, for a design spike, Context for the Designer).
- **Software-architect** owns Technical Details, Files to create and modify, and the code and
  prior-art parts of Context.

The business-analyst surfaces the need for a split or a technical concern but does not design
it; the software-architect designs but does not rewrite the user story.

## Cross-repo scope: frontend and edx-platform

Many tickets here also touch code outside this repo. Understand the neighbor from its
orientation doc first, and reach into the neighbor's actual code only when the doc is not
enough. Tell the experts to do the same, and to keep this work in cheap sub-agents so the
strong-model context stays lean.

- **Authoring frontend** (`frontend-app-authoring`, the Studio MFE, external to this
  workspace at `../frontend-app-authoring`). For any ticket with a frontend part, understand it
  from `.claude/frontend-app-authoring-architecture-overview.md`: the MFE's architecture,
  conventions, and how it connects back to this repo's APIs. Only where that overview is not
  enough, have an expert dispatch a low-cost `Explore` or `general-purpose` sub-agent on
  **Sonnet** with a narrow question against a small, specific set of files there. Never read
  the repo into the main context.

- **openedx-platform** (the monolith, formerly `edx-platform` -- still commonly called that in
  issues, PRs, and discussion; recognize both, external at `../openedx-platform`). It is huge,
  so protect context aggressively. Start from `.claude/architecture-overview.md`, which covers
  how it integrates this library (the `content_libraries` and `content_tagging` layers). Prefer
  that overview to opening the monolith at all. Only where strictly necessary, dispatch a
  **Sonnet** sub-agent with a very narrow question pointed at a very small, specific selection
  of files in `../openedx-platform`, and instruct it to be protective of its own context: read
  excerpts, not whole files, and return only the answer.

## 1. Intake

Identify what you are working from and gather the ground truth:

- Pasted text: use it. A file path: read it. A GitHub issue: `gh issue view <n> --comments`.
  A URL or other tracker (Jira and similar): delegate the fetch to a Sonnet sub-agent, never
  inline. A bare feature idea with no ticket: treat it as a request to draft a new ticket.
- Collect any related or blocking tickets and backlog the user points at; the architect needs
  them to judge split and merge boundaries.
- Skim `.claude/ticket-template.md` (and `cbe-project-context.md` for competency work). If the
  request has a frontend or edx-platform part, read the relevant overview named in the
  cross-repo section.

If there is neither a ticket nor a feature request to work from, say so and stop.

## 2. Requirements pass (business-analyst)

Dispatch the `business-analyst` agent with an excellent, self-contained prompt. Give it the
ticket or idea verbatim, the related tickets, and the context you gathered, and ask it to
return, grounded in the actual repo:

- **True intent**: the real Open edX role and the "so that"; where the request optimizes for
  the wrong thing or gold-plates past the outcome.
- **Findings**, grouped and anchored to the text: Missing / Open question / Contradiction /
  Outdated / Improvement.
- **SMART scorecard** and a **1-2 developer-day feasibility flag**.
- **Its owned sections** drafted in the canonical format (Acceptance Criteria in the style the
  template prescribes for this ticket type; for a frontend part, cover the UI states and use
  the frontend overview for what is realistic).
- **OPEN QUESTIONS for the human** as a clean, prioritized list it knows you will relay. Tell
  it to format each as:
  `[BLOCKING|non-blocking] <crisp question> (why it matters: <one line>). Options: A) … B) … [recommended: X]`
  Only questions whose answer would actually change the ticket. 2-4 candidate answers each,
  with a recommended default, so the user can decide fast. Blocking questions are ones the
  ticket cannot be written correctly without.

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
  section and narrow Sonnet sub-agents only where necessary.
- **Its owned sections** in the canonical format: Technical Details closing with the Example
  Resolution Prompt, Files to create and modify (two tables), and the code and prior-art
  Context.
- **OPEN QUESTIONS for the human**, in the same format as the business-analyst's, usually
  fewer and more technical (a scope call, a contract tradeoff, a placement decision).

For a design spike, ask for scope judgment only; the business-analyst owns Context for the
Designer in place of Technical Details and Files. Keep the architect's agent id.

## 5. Clarify the design with the user (loop)

Run the same loop as step 3 for the architect's blocking questions: ask with
`AskUserQuestion`, continue the architect via `SendMessage` with the answers, cap the rounds,
and defer the unresolvable to TBD.

## 6. Synthesize

Combine the two into the deliverable, verdict first and skimmable:

- The assembled ticket in the canonical format (`.claude/ticket-template.md`): all six
  sections, BA-owned and architect-owned merged into one coherent ticket, with the answers you
  gathered reflected in the criteria and design. For a bare idea this is the drafted ticket;
  for a review, the improved one. For a split, one ticket per sub-ticket.
- The findings behind it: true intent and whether the ticket serves it; the questions that
  were answered and how they shaped the ticket; any remaining open questions or TBDs, blocking
  ones first; the scope verdict with any split or merge; the SMART scorecard and an effort
  estimate; and the rejected technical alternatives in one line each.

Touch the real tracker only on explicit request and approval.
