---
name: ticket-writer
description: Interactive authoring or review of a feature ticket before development for this Open edX library, with the user in the loop. Use when asked to write, draft, review, refine, scope, sanity-check, or improve a ticket, issue, requirement, or feature idea, and you want to dig into the requirements by asking the human the questions that actually change the ticket. Dispatches the business-analyst and software-architect experts, surfaces their questions to the user, folds the answers back in, and produces a solid ticket in the canonical format (.claude/ticket-template.md) plus the findings behind it. Also covers the passes around drafting: scaffolding blank human-authored sections into cache files, a pre-handoff check of the human-written sections, and a pre-post check before a ticket goes to GitHub. Advisory: does not change code or post to trackers unless asked and approved.
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

## Workflow: which pass you are running

Two people work a ticket in turn, handing the cache file under
`.claude/github-issues/<workstream>/<epic>/` back and forth through git. The human
architect writes the human-authored sections and does the final review; the human BA
drafts the rest with Claude and posts the ticket. Figure out which pass the user is asking
for before doing anything else, and ask if it isn't clear.

| Pass | Run by | What Claude does | Section |
| --- | --- | --- | --- |
| Scaffold | Architect | Writes empty human-authored headings into the named cache files | "Scaffold" below |
| Pre-handoff check | Architect | Verifies the premises of the human-written sections against the code and sibling tickets, checks those sections, and asks every question it can answer now | "Pre-handoff check" below |
| Draft | BA | Drafts the Acceptance Criteria, Technical Details, and UX Design placeholder | Steps 1-8 below |
| Pre-post check | Architect (final review), then BA before posting | Confirms the ticket is ready to post | "Pre-post check" below |

**Questions get answered in the pre-handoff check, not later.** The architect wants as few
Open Questions on a posted ticket as possible. Every question the experts can foresee
should be raised with the architect during the pre-handoff check, when the architect can
answer it into the human-written sections or the notes. An Open Question survives into a
posted ticket only when it is genuinely the implementer's to decide.

## Scaffold

When the architect names cache files to start, write the blank human-authored sections into
each one so the architect can fill them in. Keep the file's existing title line, GitHub link
line, and `Cached:` line. Replace only the "no description yet" placeholder line:

    ## User Story

    ## Description

    ## Context

    ## Notes for drafting

Then remind the architect that the title is theirs to write too: the `#` line at the top
of the file is the GitHub Issue title, and a placeholder title (such as one starting with
`[Placeholder`) needs replacing. Don't rewrite the title yourself.

If a named file already has a real body, don't overwrite it: say so and ask what the
architect wants done with that file. Don't add the UX Design placeholder or any
Claude-drafted section at this stage, and don't dispatch any expert.

## Pre-handoff check

The architect runs this pass after writing the human-authored sections and before pushing
the file to the BA. Its job is to catch problems in those sections, and to surface every
question the draft pass would otherwise raise, while the architect is here to answer it.

1. Read the cache file. If the User Story or Description is empty, or the title is still
   a placeholder, say so and stop.
2. **Verify the premises before anyone designs against them.** The human-written sections
   rest on claims about what the code does today and what sibling tickets cover. Those
   claims are the cheapest thing to get wrong and the most expensive to discover late: a
   premise that turns out false during the final review reopens the human sections, re-runs
   both experts, and makes the architect re-read sections that were already settled.
   - List every premise: each trigger the sections name ("when X is deleted, imported, or
     archived, Y happens"), each claim that a sibling ticket handles a path, and each
     assumption about an existing mechanism (a handler, a signal, a cascade, an import).
   - Check each one at its source, never from memory and never from the ticket itself.
     Dispatch narrow Sonnet lookups per "Model and orchestration", one question each, and
     require the quoted lines back. Read sibling tickets live with `gh issue view`, and
     quote the sentence that covers, or fails to cover, the path in question. Checks that
     recur on this codebase: what an existing handler does for a given event (which key,
     which signal, before or after the change, robust or not); whether an import path
     replaces or diffs; the `on_delete` of every foreign key on the chain the ticket walks;
     whether a hook the design would need exists at all (a bulk `.update()` fires no
     signal); and whether the thing the sections say "nothing does today" is in fact
     already done by a receiver nobody remembered.
   - Trust rules. A sub-agent's answer is a fact only when it quotes the lines it rests on;
     a summary like "none of the receivers touch that" gets re-checked at the cited
     location before you repeat it. A local checkout can be months stale, so confirm any
     claim about `openedx-platform` against upstream `master` before calling it a fact.
   - Every premise that fails is a finding for step 5. Every fact that opens a scope choice
     (the trigger never reaches this layer today; the sibling ticket does not cover that
     path; no hook exists) becomes a question for step 6. Hand the verified facts to both
     experts in step 3 as a "Verified facts" block with file and line references, so they
     design against the code as it is rather than rediscovering or assuming it.
3. Dispatch `business-analyst` and `software-architect` in parallel. Give each one the
   human-written title, User Story, Description, Context, and Notes for drafting verbatim, plus
   the related tickets and the verified facts from step 2, and tell it this is a pre-drafting
   check: it must not draft any section. Ask each one to return findings on the human-written
   sections (Missing / Contradiction / Outdated / Improvement, anchored to the text), the OPEN
   QUESTIONS it would otherwise raise while drafting (in the format from step 2 below,
   including which ones are truly the implementer's to decide), and any NEEDS RESEARCH items.
   The BA covers the requirements angle and the architect covers scope and design, which is
   why both are needed: an architect alone asks technical questions and misses
   product-shaped gaps.
4. Resolve the NEEDS RESEARCH items per "Model and orchestration" and continue the experts
   if their answers depend on the research.
5. Report the findings on the human-written sections to the architect in chat. Never edit
   those sections.
6. Merge and dedupe the questions, drop the implementer-owned ones, and ask the rest with
   `AskUserQuestion` per step 3 below. Ask them together, in as few rounds as they fit, not
   one at a time as each surfaces. The scope decisions a ticket needs usually depend on each
   other, and a decision answered late forces the experts to run again and the architect
   to re-read sections that were already right.
7. Record each answer so the BA's draft pass sees it. The architect decides where each
   answer goes: into Context, which the architect writes or approves word for word, or
   into Notes for drafting, which is never posted. You may append answers under Notes for
   drafting yourself, as a `Decisions from the pre-handoff check` list, one line per
   question and answer. Don't write into User Story, Description, or Context unless the
   architect gives you the exact wording.
8. Tell the architect the file is ready to commit and push to the BA. Don't commit or push
   it yourself unless asked.

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

- **Human architect** owns the title, User Story, Description, and Context. Claude preserves them
  verbatim in every pass, drafting and cleanup alike, and reports any problem with one in
  chat, never by editing the ticket file. In the architect's own passes that means telling
  the architect directly; in the BA's draft pass, see step 3's routing rule.
- **Business-analyst** owns Acceptance Criteria, the UX Design placeholder on frontend
  tickets, and Open Questions raised from a requirements angle (and, for a design spike,
  Context for the Designer in place of Technical Details).
- **Software-architect** owns the whole Technical Details section (Summary, Approach,
  Files to create and modify, Additional context) and Open Questions raised from a design
  angle.

The business-analyst surfaces the need for a split or a technical concern but does not design
it; the software-architect designs but does not touch the human-written sections.

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

Steps 1 through 8 are the draft pass, which the BA runs. The normal starting point is a cache file a human already wrote under
`.claude/github-issues/<workstream>/<epic>/`, containing the User Story, the Description,
an optional Context, and an optional `## Notes for drafting` section (hunches, related
code, edge cases, questions to chase; use it to inform drafting and drop it from the
finished ticket). The notes may end with a `Decisions from the pre-handoff check` list:
those questions are already answered, so don't raise them again. Treat the User Story and Description as required inputs, not something
Claude drafts: if either is missing from the cache file (or from pasted text, or a GitHub
issue body), ask the human for it, with `AskUserQuestion` or a plain question, before
dispatching either expert. Never have an expert draft a User Story or Description to fill
the gap. For a bare idea with no human-written sections at all, ask the human to write the
User Story and Description first. Draft them yourself only if the user explicitly tells you
to in that session, and say in the handoff that they still need a human rewrite before
posting.

Identify what you are working from and gather the ground truth:

- Pasted text: use it. A file path: read it. A GitHub issue: check
  `.claude/github-issues/<workstream>/<epic>/` first (each workstream's `README.md` maps
  epics to folders) — if a cache file for that issue number exists, read it to save a
  fetch, but still confirm against `gh issue view <n> --comments` before relying on
  anything from it. **GitHub is the source of truth; the cache is a snapshot and can be
  stale.** No cache file: `gh issue view <n> --comments` directly. A URL or other tracker
  (Jira and similar): delegate the fetch to a Sonnet sub-agent, never inline. A bare
  feature idea with no ticket: treat it as a request to draft a new ticket.
- **Comments always need a live fetch — the cache never carries them, only the issue
  body.** On a ticket with a long comment thread, read the comments in order and let the
  most recent one win on any point it addresses: a later comment can resolve an open
  question, correct a technical detail, or narrow scope in a way the original body was
  never edited to reflect. Don't draft or review a heavily-commented ticket off the body
  alone.
- Collect any related or blocking tickets and backlog the user points at, by **GitHub issue
  number** — the architect needs them to judge split and merge boundaries. Never carry over
  an internal ticket ID or a spreadsheet reference.
- Skim `.claude/ticket-template.md` (and `cbe-project-context.md` for competency work). If the
  request has a frontend or edx-platform part, read the relevant overview named in the
  cross-repo section.

If there is neither a ticket nor a feature request to work from, say so and stop.

## 2. Requirements pass (business-analyst)

Dispatch the `business-analyst` agent with an excellent, self-contained prompt. Give it the
human-written User Story, Description, and Context verbatim as fixed input (they are not
its to change), the related tickets, and the context you gathered, and ask it to return,
grounded in the actual repo:

- **True intent**: the real Open edX role and the "in order to"; where the request optimizes
  for the wrong thing or gold-plates past the outcome.
- **Findings on the human-written sections**, grouped and anchored to the text: Missing /
  Open question / Contradiction / Outdated / Improvement. These are for the orchestrator to
  relay to the human in chat, never edits to apply to the User Story, Description, or
  Context.
- **SMART scorecard** and a **1-2 developer-day feasibility flag**.
- **Its owned sections** drafted in the canonical format: Acceptance Criteria as
  Given/When/Then scenarios describing observable behavior only (this applies even to
  backend/data-model tickets with no UI: phrase the outcome in terms of what's observed,
  not the mechanism; for a frontend part, cover the UI states using the frontend overview
  for what is realistic; use a checkbox list instead of Gherkin for an artifact ticket per
  the template), and, on a frontend ticket, the UX Design placeholder tagging
  `@illiphilli`.
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

1. Merge and dedupe the questions, blocking first. Drop any the intake already answers,
   including anything in the notes' `Decisions from the pre-handoff check` list. Then
   route each remaining question by who can answer it. Ask the BA about requirements and
   product behavior. For anything about scope, the technical approach, or the architect's
   User Story, Description, or Context, tell the BA it's a question for the architect and
   suggest taking it to the architect. When it's unclear which one it is, ask the BA whether they can
   answer it or wants to take it to the architect.
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
   further.
5. A question that is still open when the draft is saved goes in the ticket's Open
   Questions, labeled with who resolves it: `(architect, final review)` for one waiting on
   the architect, or `(implementer)` for one that is genuinely the implementer's call.
   The architect resolves the first kind in the pre-post check, so none of them are
   posted. Prefer answering a question over parking it: the goal is no Open Questions
   except the implementer's.

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
- **Its owned sections** in the canonical format: the whole Technical Details block,
  opening with a note that it's a suggested approach and not the ticket's source of truth,
  then in order an optional **Summary** (only when the Approach runs past about 15 lines),
  a required **Approach** (pseudo code or numbered steps, real file/class/function/endpoint
  names, each step saying what happens and, where it isn't obvious, why), an optional
  **Files to create and modify** table (one line per file, marked new or modified), and an
  optional **Additional context** (prior-art files, ADR links, GitHub issue numbers not
  already in the human Context). Hold it to the bar of an Axim engineer who has two
  minutes: short enough to approve before code is written, nothing a competent developer
  on this codebase would do without being told, companion-ticket work marked out of scope
  and referenced by GitHub issue number, no Example Resolution Prompt or other closing
  implementation-plan prompt. **Technical Details is required, not optional**, even a small
  ticket gets a short Approach (the one exception is a design spike, which has no Technical
  Details at all). Wrap the whole section in one collapsible `<details>` block per the
  template; it is the only collapsed section.
- **OPEN QUESTIONS for the human**, in the same format as the business-analyst's, usually
  fewer and more technical (a scope call, a contract tradeoff, a placement decision).
- **NEEDS RESEARCH**, in the same shape as the business-analyst's, for anything it would
  otherwise fetch or explore itself but wasn't given. You resolve these yourself.

For a design spike, ask for scope judgment only; the business-analyst owns Context for the
Designer in place of Technical Details. Keep the architect's agent id.

## 5. Clarify the design with the user (loop)

Run the same loop as step 3 for the architect agent's blocking questions, with the same
routing rule: most of these are questions for the human architect, so the BA takes them to the
architect or they are saved as `(architect, final review)` Open Questions. Ask with
`AskUserQuestion`, continue the architect agent via `SendMessage` with the answers, and
cap the rounds.

## 6. Synthesize

Combine the two into a complete draft ticket, verdict first and skimmable (step 7
finalizes it):

- The assembled ticket in the canonical format and order (`.claude/ticket-template.md`):
  User Story, Description, and Context copied verbatim from the human's cache file
  (dropping the `## Notes for drafting` section, which never appears in the finished
  ticket); the UX Design placeholder on a frontend ticket; Acceptance Criteria; and
  Technical Details, wrapped in its one collapsible `<details>` block, the only collapsed
  section. Merge the BA-owned and architect-owned drafted sections in reflecting the
  answers you gathered. For a bare idea this is the drafted ticket; for a review, the
  improved one. For a split, one ticket per sub-ticket, cross-referenced by GitHub issue
  number.
- The findings behind it: true intent and whether the ticket serves it; the questions that
  were answered and how they shaped the ticket; any remaining open questions or TBDs, blocking
  ones first; the scope verdict with any split or merge; the SMART scorecard and an effort
  estimate; and the rejected technical alternatives in one line each.
- Any concerns the business-analyst or software-architect raised about the human-written
  User Story, Description, or Context: relay these to the BA in chat, not as edits to the
  ticket file. One that needs the architect to decide becomes an `(architect, final
  review)` Open Question if the BA doesn't take it to the architect before saving.

## 7. Editorial cleanup and fidelity check

The step 6 draft is not the deliverable yet. Run one editorial pass over it, then verify
the pass changed only the writing.

1. Dispatch a sub-agent (`Agent`, **no `model` override** so it runs on your model) and
   have it invoke the `clean-up-ticket` skill on the draft: pass the ticket text or its
   file path, and ask it to return the cleaned rewrite plus its "what changed and why"
   changelog. Tell it the title, User Story, Description, and Context are human-written and
   frozen: it must carry them through unedited and raise any concern about them as a
   finding, not a rewrite. That skill tightens structure, removes redundancy and line
   numbers, leads with the change, and rewrites toward the template, without touching
   scope.
2. **Verify fidelity yourself** (a final-review job, keep it on the strong model). Compare
   the cleaned version against the step 6 draft, using the changelog as a guide. Confirm
   every change is editorial (structure, order, deduplication, wording, dropped line
   numbers, a BLUF lead) and that nothing material was lost or invented: every requirement,
   acceptance-criterion behavior, constraint, out-of-scope item, file reference, and
   factual claim must survive with its meaning intact. Diff the title, User Story,
   Description, and Context against the human's cache-file version and confirm they are byte-identical;
   the cleanup preserves scope by design, this step confirms it actually did.
3. If the pass dropped, altered, or invented any content, or touched a human-written
   section, restore it (or re-run the cleanup with a correction) before delivering. Do not
   ship a cleaner but subtly wrong ticket.
4. Deliver the cleaned, verified version as the final ticket; the step 6 draft is
   scaffolding.

Save the delivered ticket to its cache file under `.claude/github-issues/<workstream>/<epic>/`,
the shared drafting surface for you and the BA now, replacing the old Google Doc. Update
the existing `ucid-....xx-ghi-<n>.md` file if you started from one, or create a new one
(using `ghi-pending` in place of the issue number) for a bare idea that has no GitHub issue
yet. **GitHub remains the source of truth for the real ticket, not this cache.**

## 8. Hand off for human audit

Axim asked that a human audit the Acceptance Criteria and Technical Details before a
ticket is posted, since both are Claude-drafted. Give the user a short checklist to run
over the saved ticket before posting:

- Every Acceptance Criteria scenario matches something the Description asks for, and each
  one could actually fail.
- The unhappy paths (empty, error, permission) are covered, not just the happy path.
- The Approach in Technical Details names real files and functions, and nothing in it
  would surprise an Axim reviewer at code review time.
- Nothing in Technical Details is obvious filler a competent developer here wouldn't need
  spelled out.
- A frontend ticket has the UX Design placeholder tagging `@illiphilli`.
- The title, User Story, Description, and Context read exactly as the human wrote them,
  and the title still reads as a human wrote it: plain, specific, and understandable
  without opening the ticket.
- Every Open Question is labeled `(architect, final review)` or `(implementer)`.

Then tell the BA the file is ready to commit and push back to the architect for final
review.

## Pre-post check

Run this when the architect finishes the final review, and again when the BA is about to
post.

**The architect's final review is the same step 8 audit the BA ran, usually plus a list
of questions and concerns.** Give the architect the step 8 checklist to audit against,
and work through their list before running the checks below:

- Answer each question directly, with a bounded lookup if it needs one. When the answer
  shows the ticket is wrong, say what you'd change.
- When a comment rests on a claim about the code or a sibling ticket, verify the claim
  before answering, with the same trust rules as the pre-handoff check's step 2: quoted
  lines, the live issue body, upstream `master` for a platform claim. The architect's own
  assumption can be the wrong one, and so can the ticket's; say which, with the source.
- If the ticket never had a pre-handoff ground-truth pass (step 2 of that check), run it
  now, before revising anything. A final review that discovers false premises one at a time
  is the most expensive place to discover them.
- When the review opens more than one scope decision, collect them and ask in one round
  before revising, then dispatch each expert once with every answer. One dispatch per
  answer re-does the same work as many times as there are answers.
- For each concern about a Claude-drafted section (Acceptance Criteria, Technical Details,
  UX Design placeholder), revise that section. For a concern that changes the technical
  approach, dispatch `software-architect` with the ticket and the concern rather than
  redesigning it yourself.
- A concern about the title, User Story, Description, or Context is the architect's to fix. Edit
  those sections only with wording the architect gives you.
- Resolve any `(architect, final review)` Open Question the list answers, folding the
  answer into the section it belongs in.
- Show the architect what changed, item by item, and ask about anything you couldn't
  resolve.

Then run the checks:

- The `## Notes for drafting` section is gone.
- No `(architect, final review)` Open Question is left. Each resolved one has been folded
  into the Acceptance Criteria, Technical Details, or the architect's Context, then
  removed. If the Open Questions section is now empty, remove the heading.
- Any remaining Open Question is labeled `(implementer)`. Drop the label when posting only
  if the architect asks.
- The step 8 checklist still holds after the architect's edits.

Report what fails. Fix the mechanical items (removing the notes section, removing an
emptied Open Questions heading) when asked. Anything that needs a wording decision goes
back to whoever is running the session. When the BA runs this right before posting, it is
a check only: the architect's list has already been handled.

Touch the real tracker, push the finalized text to the GitHub issue by `gh` or copy/paste,
only on explicit request and approval, never as an automatic next step after either
check. When posting, set the issue title from the file's `#` line as well as the body, and
leave out the cache-only lines (the title line, the `GitHub:` line, and the `Cached:` line)
from the body.
