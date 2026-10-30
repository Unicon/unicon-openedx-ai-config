---
name: frontend-code-review
description: "Extends the 'code-review-openedx' skill. Senior UX/Frontend peer review of a diff for this Frontend application. Use when asked to review a PR, a branch, or a diff, or for a second opinion on changes. Review-only: surface findings with file:line anchors and a severity marker; never fix, commit, or push. Post to GitHub only when explicitly asked and approved."
---

# Frontend Code Review (Extension of 'code-review-openedx')

A senior peer review for the general frontend application within the Open edX ecosystem. 
Surface what is wrong and why; let the developer decide what to act on. Never apply fixes,
commit, or push from this skill.

This skill runs in the top-level session. Per the Delegation rule in `CLAUDE.md`, whoever
runs it dispatches the sub-agents the parent skill names; it never runs inside a dispatched
sub-agent that would then need to dispatch further.

## Step 0: component tree map (runs before everything else)

When the review target is a pull request, run the `pr-component-tree` skill on it first, before
reading the parent skill and before the parent's phase A. It does not count against phase A's
tool-call budget. When the target is a branch or the working tree, skip this step and tell the
developer why.

1. Run `pr-component-tree` for the PR. It produces a Markdown file with the component tree as an
   inline SVG, and a plain-text outline of the same tree and notes.
2. Give the developer the result right away, in its own message and before the review starts:
   the absolute path of the Markdown file and the short summary the skill prescribes. The
   developer can read it while the review runs, so do not wait for the review to finish.
3. Make the outline context for the review. In the parent's A4 shared brief, add one line: "Read
   `<absolute path of the outline>` after this brief: the PR's component tree, one line per
   component, with a note on each changed component and changed module." That line counts toward
   the brief's 150 lines; the outline does not. Every B agent reads the outline after the brief.
4. Treat the outline as orientation: which components changed, how they nest on each page, which
   changed modules feed them, and what each change does. A sub-agent derived it from the diff, so
   it is not evidence. Every finding still cites lines read at the head SHA, and a note in the
   outline that the code contradicts is itself worth a finding.

## Parent skill

This skill manually builds on the sibling `code-review-openedx` skill; Codex does not load
that skill automatically. Before starting the review, read
[`../code-review-openedx/SKILL.md`](../code-review-openedx/SKILL.md) in full.

Follow the parent skill's review workflow, review-wide rules, evidence requirements,
and finding format. The frontend-specific checks below belong to the parent's phase B dispatch
wave (remits B3 to B5) and its phase C verification; they do not replace its general review
requirements.

If the parent skill file is missing or unreadable, stop and tell the user before
reviewing the change.

## Frontend remits for the parent's phase B wave

The parent's B3 to B5 remits are written around a Django library: endpoints, exceptions,
columns, constraints, locks. In this repository the same questions take frontend shapes: logic
in components and hooks, data flow through React state and the TanStack Query cache, fetch
requests and mutations, JSX, and accessibility. Give each B agent the parent's remit and the
matching section below, as the frontend reading of that remit. The sections say what to trace
and how to decide what this PR needs investigated. They do not list checks, because what matters
differs from PR to PR, and the agent that has traced the change is the one who can tell.

**Trace each behavior end to end (B4 and B5, before any finding).** For each behavior the change
adds or alters, write down its path through the application: the user event that starts it, the
component that handles it, every piece of state it reads and writes (component state, context,
the query cache, the URL), the request or mutation it sends and the response shape it expects,
how the result reaches the render, and what the user sees at each step. Then walk the same path
a second time, asking at each hop what real use makes this hop produce the wrong result. The
hops where the answer is not "none" are the questions this PR needs answered; investigate those,
and record the rest under "Checked and found acceptable" with the hop named. Prompts for the
second walk, by kind of hop:

- State: which user actions and data events must change or reset this value (selecting a
  different item, paging, searching, navigating, a refetch, unmount), and does each one do so?
  What does the render show while the value is loading, empty, errored, or stale from a previous
  selection?
- Requests: what does the server need in order to answer this, and is that what is sent? Does
  the consumer need the whole result set, and does it receive all of it or one part? What
  happens when the response lands after the user has moved on?
- Mutations: what does the cache believe before, during, and after the request, and what else on
  screen depends on the data that changed? What does the user see when the request fails or
  partly succeeds?
- Render and JSX: what does each visual state mean to the user who reads it, and what does a
  keyboard or screen-reader user get at each state? Does the same information have one
  representation, or does a badge, a tooltip, and a label each say something different?

A hop whose wrong result is reachable in supported use is a `Bug`. A hop whose reachability is
unconfirmed is a `Question`. A hop that behaves correctly but has no test that fails when it
breaks is a `Suggestion` naming the test.

**Judge the change inside its module (B5).** Read the module the change lands in, the hooks it
calls, and the helpers it already imports, before judging the new code. Ask what the module
already has for the job the new code does, and whether the new code uses the module's named
helper for an effect or reaches that effect through side effects on other state. Cite the
"Reuse before rebuild" rule in `.claude/CLAUDE.md`. A new path that duplicates or bypasses an
existing helper in the same module is a `Suggestion`; one that bypasses it and behaves
differently from it is a `Bug` or a `Question`, by reachability.

**Tests (B4).** The parent's map-and-break step applies unchanged. The frontend reading of the
parent's error-path and bounded-write steps is the trace above: every hop the trace marked for
investigation that no existing test exercises goes into the one probe file the parent's B4.2
describes, as a component or hook test that performs the transition or request and asserts what
the user sees, run once. Report each hop that produced the wrong result as a reproduction with
the user action and the observed render.

**The repository's own conventions (B5, B4, and phase C).** Alongside the trace, hold the change
to the conventions `AGENTS.md` and the frontend section of `.claude/CLAUDE.md` state. These are
standing rules, so a finding under them needs the cited line, not a trace. In addition to the
parent's checks in [code-review-openedx](../code-review-openedx/SKILL.md), evaluate the following
questions about the change, and raise any further concern they lead to. Give the component,
accessibility, and styling questions to remit B5, any test question to remit B4, and the rest to
phase C.

1. Is the Paragon design system being used as extensively as possible for the components this
   change adds? Paragon components, Paragon's bootstrap classes, and design tokens, with custom
   CSS used sparingly?
2. Does the implementation meet WCAG AA accessibility standards, if applicable?
3. Does it adhere to general best practices for this repository's version of React?
4. Is it using TypeScript, and TanStack Query instead of Redux for server state, and the other
   conventions `AGENTS.md` names?
5. Is it avoiding inline styles?

## Delivering the review

When the review is done, your response in chat is only a link to the cleaned-up file that the
parent's phase D produces, nothing more. When the user asked questions that are an integral part
of the review, the answers are part of the review in that file. The component tree message from
step 0 is sent earlier, while the review runs.
