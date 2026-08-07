---
name: spike-and-stabilize
description: Incremental coding methodology for non-trivial tasks. Survey the code, get one combined clarify-and-plan approval, write a thin throwaway spike, then stabilize it (types, tests, checks, review). Skip the flow for trivial tasks like renames, typo fixes, and one-liners.
---

# Spike & Stabilize

Requirements are often vague. Discipline comes from stabilizing one layer at a time.
For every non-trivial task, run these four steps in order. Don't reorder, skip, or
merge them; if a step doesn't apply, say why and move on.

1. Recon
2. Clarify and plan (one approval gate)
3. Spike
4. Stabilize

## Who runs the steps

This skill runs in either of two contexts, and the four steps are the same in both. Only
the staffing changes. See "Where you are determines whether you may dispatch at all" in
`CLAUDE.md`; the short version:

- **You are the top-level session.** Delegate as each step describes, provided the user has
  approved those dispatches. If they have not, do the work inline. Never skip a step
  because you cannot delegate it.
- **You are a dispatched sub-agent**, for example the implementer node of an orchestration
  plan. You have no Agent tool and you do not orchestrate. Do the steps you were briefed
  on, inline, and return a "Needs research" item instead of trying to dispatch. If the
  brief covers only some steps, do those; the caller owns the rest.
- **An orchestration plan is active.** The plan owns who runs what, and its required nodes
  and gates take precedence over this skill's default staffing. Do not re-delegate work the
  plan already assigned, and do not skip a plan gate because this file does not mention it.

## Trivial escape hatch

Skip the flow for obviously trivial work: renames, typo fixes, one-line changes,
import tweaks. Say "Trivial: <reason>", make the fix, run one relevant check, present
the result. "Small" or "well-understood" is not trivial; only the absence of business
logic and branching is.

## 1. Recon

Before touching code, get a high-level map, then narrow to the few files that matter.
Where you can delegate, send broad searches to an `Explore` sub-agent (model Haiku for
plain location, Sonnet when it must reason about behavior) so file dumps stay out of the
main context; it returns a summary, not the files. Where you cannot, keep the same
discipline yourself: targeted Grep and Glob over reading directories, and read only what
the task touches rather than everything nearby. Report back:

- Existing patterns for similar features, with file paths.
- Reusable code (helpers, base classes, public APIs) the work can build on.
- Where the new code should live, and why, given the `.importlinter` layering.
- Conflicts and surprises: deprecated code, clashing patterns, naming drift.

Use the findings to answer your own questions before asking the developer.

## 2. Clarify and plan

Do the clarify-and-plan work in plan mode (`EnterPlanMode`). Ask focused questions with
`AskUserQuestion` (2-4 options each), then present a detailed implementation plan. Do not write any
implementation code, including illustrative snippets, until the developer approves the
plan via `ExitPlanMode`.

On plan approval, the coding in steps 3 and 4 should be done by a `general-purpose`
sub-agent on Sonnet, briefed with the approved plan, the target files, and the conventions
to follow, and told that it must not itself dispatch — if it needs a lookup it wasn't
briefed on, it stops and reports back. When you are the top-level session and the user has
approved that dispatch, stay on the strong model to run the gates and judge results rather
than writing the code yourself.

Two cases where the coding is yours to do inline, and doing it is correct, not a
shortcut: you are already the dispatched implementer, or you are top-level and have no
approved dispatch to make. In both, carry on through steps 3 and 4 yourself under the same
rules. The point of this step is that the plan is approved before code is written, not
that a particular agent writes it.

- Enumerate edge cases yourself and propose handling; don't ask the developer to list
  them. Time/timezones, parsing, and concurrency are the usual traps.
- Present options when interpretations differ; don't pick silently.
- Zero questions is fine when recon resolved it: confirm your assumptions and proceed.
- For a significant, hard-to-reverse decision (new dependency, data-model or public-API
  change, new boundary), draft an ADR in proposed status under
  `docs/openedx_content/decisions/` and name it in the plan. See CLAUDE.md.

### ADR grain and voice

For writing ADRs:
Match the repo's existing ADRs, not a design doc. Before drafting, skim 2-3 merged
ADRs in the same `decisions/` directory for length and tone, and hold the draft to
the same bar. The norm across this codebase's ADRs is 40-110 lines: prose decision
statements, single-paragraph rejected alternatives, occasional field/class names
only where they aid clarity. No code blocks, no exhaustive file-by-file
implementation plans, no dependency/merge-order negotiation with other ticket
numbers, no "Open Questions" section — none of the merged ADRs sampled use one.
Length over ~150 lines is only justified when the ADR itself introduces a wholly
new schema or subsystem, not for an addition to existing code.

Content that doesn't fit that grain still needs a home — don't just delete it. Put
implementation plans, dependency coordination with other issues, and open questions
in a comment on the originating ticket instead of in the ADR body.

## 3. Spike

Write the thinnest vertical slice that does something real end-to-end. Rough is fine.
These rules bind whoever writes it, so brief the implementer with them if you dispatched
one, and follow them yourself if you are the implementer:

- Happy path only; defer error handling and edge cases.
- Loose types where the shape is unclear; tighten later.
- Hard limit 50 lines. If it doesn't fit, narrow the scope, don't raise the cap.
- Mark it `# SPIKE: shape not final`.
- Before writing logic that already exists elsewhere, reuse it or say why it doesn't fit.

Show the developer the result and confirm the shape before stabilizing.

## 4. Stabilize

Once the shape is confirmed, add no new features. Run these steps in order. If you
dispatched an implementer, continue that same agent via `SendMessage` so it keeps its
context rather than dispatching a fresh one:

1. Tighten types: full annotations; prefer dataclasses or `TypedDict` over bare `dict`.
2. Write tests: one per behavior, not per function. Ask "what would tell me this works?"
3. Run checks until clean: the relevant linters directly (pylint, mypy, pycodestyle,
   pydocstyle, isort) on changed files, plus targeted `pytest --no-cov` for related
   tests. See CLAUDE.md for why not `make test`. Never suppress a check to go green.
4. Apply the rule of three: don't extract shared code until a third caller needs it.
5. Report: what's covered, which checks ran clean, what's next.

As the final step the diff gets a `code-review` pass, and it must not be run by the same
agent that wrote the code: a reviewer that already believes the code is right is not a
review. If you are the top-level session, run it yourself on the strong model or dispatch
a reviewer. If you are the implementer, do not review your own work; report back that the
change is ready for review and let the caller run it. Under an orchestration plan the
review is a required node with its own gate, so it is already staffed. Fix anything it
flags as wrong before the change is done.

If this increment produced or amended an ADR, run one more pass before calling it
done: re-read it against the "ADR grain and voice" note in step 2 and trim anything
that crept past it. Then, ideally via a fresh sub-agent dispatch rather than the same
context that drafted it, review the whole ADR for: factual claims checked against
their actual cited sources (another ADR, a model's code) directly, not trusted from
an earlier sub-agent's summary; internal contradictions introduced across edits; and
language that assumes framework knowledge the developer doesn't have. For a long or
heavily-revised ADR, offer a compact table summary of its current content before
asking the developer to read the whole thing; catching gaps at that scale is faster
than catching them after a full read.

## Expand

For the next increment, repeat the clarify-and-plan gate unless it's trivial. Pause and
confirm before significant complexity: a new dependency, a data-model or public-API
signature change, going async, cross-module changes, or any ambiguity recon left open.

## When blocked

If the next step is low-confidence and high-cost, stop. Summarize what's not working,
give 2-3 options, and ask which path to take. Don't keep guessing.
