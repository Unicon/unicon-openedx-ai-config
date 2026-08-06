---
name: clean-up-ticket
description: Editorial and structural cleanup of an already-scoped ticket, then a rewritten version written to a new local file. Use when asked to clean up, tighten, trim, de-bloat, condense, restructure, or improve the writing of an existing ticket or issue, or for a brutally honest review of how well a ticket reads. It grades the ticket across fixed dimensions (structure, length, bloat, level of implementation detail, readability, helpfulness for a junior human and for an AI implementer), then rewrites it toward the canonical template. Distinct from ticket-writer: it does NOT interrogate requirements or relitigate the design, it improves the ticket as a communication artifact and preserves the decided scope. Advisory: writes to a new local file, never overwrites the source or posts to the tracker unless explicitly asked.
---

# Clean up a ticket

Take an existing, already-scoped ticket and make it a great one to *read and act on*:
review it brutally honestly, then write a tightened version to a new local file. The
point is editorial and structural quality, not requirements discovery.

## What this skill is, and is not

- **It is** an editorial + structural pass on a ticket whose requirements and design are
  already settled. It fixes bloat, redundancy, buried asks, over-specification, weak
  structure, and unreadable prose, and rewrites toward `.claude/ticket-template.md`.
- **It is not** requirements or design interrogation. It preserves the decided scope and
  the chosen approach; it does not ask the user clarifying questions, dispatch the
  business-analyst or software-architect, or add/remove requirements.
- **When to hand off instead:** if the requirements are unclear or contested, the "so
  that" is missing, or the design is genuinely unsettled, this is the wrong skill. Say so
  and point to `ticket-writer` (the interactive, expert-driven skill), rather than
  guessing at intent under the guise of cleanup.
- **Advisory.** Produces a review and writes the improved ticket to a **new** local file.
  Never overwrite the source ticket, and touch the real tracker only on explicit request
  and approval.

## Read first

`.claude/ticket-template.md` — the canonical six-section shape you rewrite toward, and the
standard for how much implementation detail belongs in Technical Details (intent and
contract, not a code dump).

## Model and context

Whoever runs this skill does the review and the rewrite; that judgment is the whole point
of the skill. The ticket under review and the template are small, read them inline. Per
the Delegation rule in `CLAUDE.md`: if you are the top-level session, push context-heavy
*fetching* down yourself (a URL or non-GitHub tracker to a Sonnet sub-agent, code-location
lookups to a Haiku `Explore`). If you were dispatched to run this skill (e.g. by
`ticket-writer`'s fidelity-check step), you have no Agent tool and fetch nothing yourself —
return a "Needs research" item to whoever dispatched you instead. Never read a neighbor
repo (`openedx-platform`, `frontend-app-authoring`) into context to verify a claim; use its
overview doc, or dispatch/flag a narrow Sonnet sub-agent per the same rule.

## 1. Get the ticket and ground it

- **Intake.** Pasted text: use it. A file path: read it. A GitHub issue:
  `gh issue view <n> --repo <owner/repo> --json body,comments,...` (read the comments too;
  a maintainer may have already flagged a factual error). A URL or other tracker: delegate
  the fetch to a Sonnet sub-agent, never inline.
- **Spot-check the falsifiable claims**, cheaply and targeted. Does each referenced file
  and function exist? Are the line numbers accurate? Is a categorical assertion ("there is
  no way to X") actually true? A couple of `grep`s or one Haiku `Explore` for location is
  enough; do not audit the codebase. Note anything wrong or overstated, it feeds both the
  review and the rewrite. **Treat line numbers as a liability even when currently correct:**
  they rot on the next merge and read as false precision, so the rewrite drops them.

## 2. Brutally honest review, verdict first

Lead with a one-line verdict, then a graded table across the fixed rubric below, then a
short dimension-by-dimension section quoting the ticket's own words for each point. Be
brutally honest but fair: name the genuine strengths too, a review that only attacks is
not trustworthy. Grade each dimension (A–F is fine) so the author sees at a glance where
it stands.

Rubric:

| Dimension | The question it asks |
| --- | --- |
| Problem framing / Use Case | Real role and a non-hand-waved "so that"? Is the actual ask findable in the first few lines, or buried? |
| Scoping discipline | Is out-of-scope explicit? Is related-but-separate work (other ADRs, companion tickets) disentangled? |
| Acceptance criteria | Observable and testable? Unhappy paths covered? Or bloated and repetitive? |
| Grounding accuracy | Are the concrete claims (files, functions, line numbers, "there is no way to X") true? Which will rot? |
| Structure | Is content in one canonical place, or restated across four sections that will drift? |
| Length / bloat | Is the ticket longer than the diff it will produce? What is pure repetition? |
| Language / writing | Sentence length, bold overuse, one-idea-per-sentence, scannability. |
| Level of implementation detail | Intent and contract, or a code dump in prose that removes the engineer's judgment? |
| Helpfulness for a junior human | Can a junior hold it in working memory and start cold, or is it exhausting? |
| Helpfulness for an AI implementer | Is there one clean, concrete implementer block, or three redundant ones the AER will read in full? |

## 3. Rewrite to a new local file

Write the improved ticket to a **new** file (e.g. `issue-<n>-cleaned.md` or, for a pasted
ticket, `<slug>-cleaned.md`) in the repo root or scratchpad. Never overwrite the source.
Apply these editorial principles, they are the method:

- **BLUF.** Open with a one-sentence statement of the actual change, before the Use Case,
  so the shape of the work lands immediately.
- **Say each idea once, canonically.** DRY applies to prose. State each invariant/rule in
  exactly one place (usually Technical Details → Logic). Redundant copies drift out of
  sync when the ticket is edited and become contradictions.
- **Intent, not a code dump.** Describe the contract and the flow at pair-programming
  altitude a junior can evaluate. Leave exact expressions, variable names, and line-by-line
  choices to the implementer, per the template.
- **One implementer block.** Keep a single concrete **Example Resolution Prompt**; delete
  duplicate "implementation notes" paragraphs and collapse the Files table to one line per
  file. Do not describe the solution three times.
- **Technical decisions live in Technical Details, and only there are they authoritative.**
  Technical Details / Logic states the contract, the *why*, and every specific decision (a
  validation rule, a claiming precedence, an error-handling choice). The Files table is a
  one-line-per-file map and the Example Resolution Prompt is an orientation guide; both may
  *reference* the approach, but a decision that appears only in a Files-table row or in the
  Resolution Prompt is misplaced, move it up. State each decision once, in Technical
  Details, rather than restating it across all three technical renderings (the triplication
  that survives a careless first pass). When you move a decision up, confirm it is not
  silently dropped from what used to be its only home.
- **The Example Resolution Prompt is an approach guide, not an implementation plan.** Its
  job is to point the implementer (human or AI) at the right approach and keep them off a
  wrong one: the goal, the authoritative sources (Technical Details and the Acceptance
  Criteria), the scope and invariants, where the relevant code lives, and how to verify.
  The agent has the whole ticket in context, so the prompt references those sections rather
  than restating them. It must not spell out a file-by-file, step-by-step sequence, let the
  agent form its own plan. When cleaning up, strip numbered "edit file X, then Y" steps down
  to that orientation, first moving any decision they carried up into Technical Details.
- **No line numbers.** Name files and functions; the implementer navigates. Drop stale or
  fragile precision.
- **Bullets for enumerables.** Anything you can count (out-of-scope items, files) is a
  list, not a bold-studded paragraph. Reserve bold for the few things that must not be
  missed.
- **Fix factual overstatements** surfaced in step 1 (including anything a maintainer
  already corrected in the comments).
- **Preserve the genuine strengths** verbatim or near-verbatim, do not rewrite what
  already works (a strong Use Case, good Gherkin, a careful ADR disentangling).
- **Do not relitigate a settled design.** If an ADR or prior decision fixed the approach,
  keep it and do not reopen it in the ticket. If the design is *genuinely* unsettled, that
  belongs upstream (an ADR or `ticket-writer`), not smuggled into a cleanup, flag it and
  leave it.
- **Align to the canonical template**: the six sections in order, house section names,
  omit empty tables.

## 4. Second pass: re-review your own rewrite

Do not trust the first rewrite. Re-read it cold, as if someone else wrote it, and put it
back through the step 2 rubric. The first pass reliably leaves residual redundancy in the
technical middle: the same mechanism restated across Technical Details, the Example
Resolution Prompt, and the Files table. Hunt that specifically, and check that the three
technical renderings actually sit at different altitudes rather than repeating each other.
If the re-review finds anything past cosmetic nits, rewrite again and repeat; stop only
when a pass turns up nothing but nits. Each time you tighten, confirm the tightened version
still says everything the prior one did, no requirement, constraint, or fact lost in the
edit.

## 5. Summarize what changed and why

Close with a short changelog: each significant cut or restructure traced to the principle
behind it (bloat, redundancy, over-specification, buried ask, stale line numbers, factual
fix). State what you deliberately kept and why. Call out, as one explicit judgment, any
design question you left untouched because it is upstream/ADR work rather than a cleanup
concern.
