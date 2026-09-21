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
- **When to hand off instead:** if the requirements are unclear or contested, the "in
  order to" is missing, or the design is genuinely unsettled, this is the wrong skill.
  Say so and point to `ticket-writer` (the interactive, expert-driven skill), rather than
  guessing at intent under the guise of cleanup.
- **Advisory.** Produces a review and writes the improved ticket to a **new** local file.
  Never overwrite the source ticket, and touch the real tracker only on explicit request
  and approval.

## Read first

`.claude/ticket-template.md` — the canonical shape you rewrite toward. The User Story and
Acceptance Criteria are the ticket; Technical Details is required alongside them, and
everything else is optional and earns its place. Three sections are collapsible —
Technical Details, Files to create and modify, and Context — each in its own `<details>`
block. The template also defines how much (and how little) belongs in Technical Details,
and that there is no Example Resolution Prompt in the current template.

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

- **Intake.** Pasted text: use it. A file path: read it. A GitHub issue: check
  `.claude/github-issues/<workstream>/<epic>/` first (each workstream's `README.md` maps
  epics to folders) — if a cache file for that issue number exists, read it to save a
  fetch, but still confirm against `gh issue view <n> --repo <owner/repo> --json
  body,comments,...` before relying on it. **GitHub is the source of truth; the cache is a
  snapshot and can be stale.** No cache file: fetch directly (read the comments too; a
  maintainer may have already flagged a factual error). A URL or other tracker: delegate
  the fetch to a Sonnet sub-agent, never inline.
- **The cache never carries comments, only the issue body — always fetch comments live.**
  On a ticket with a long thread, read the comments in order and let the most recent one
  win on any point it addresses: a later comment can resolve an open question, correct a
  claim, or narrow scope in a way the body was never edited to reflect. Ground the rewrite
  in the current state of the discussion, not just the original body.
- **Spot-check the falsifiable claims**, cheaply and targeted. Does each referenced file
  and function exist? Are the line numbers accurate? Is a categorical assertion ("there is
  no way to X") actually true? A couple of `grep`s or one Haiku `Explore` for location is
  enough; do not audit the codebase. Note anything wrong or overstated, it feeds both the
  review and the rewrite. **Treat line numbers as a liability even when currently correct:**
  they rot on the next merge and read as false precision, so the rewrite drops them.
- **Note any internal ticket IDs or spreadsheet references** the source ticket carries.
  The rewrite replaces every one with a GitHub issue number, or drops it if there's no
  public equivalent.

## 2. Brutally honest review, verdict first

Lead with a one-line verdict, then a graded table across the fixed rubric below, then a
short dimension-by-dimension section quoting the ticket's own words for each point. Be
brutally honest but fair: name the genuine strengths too, a review that only attacks is
not trustworthy. Grade each dimension (A–F is fine) so the author sees at a glance where
it stands.

Rubric:

| Dimension | The question it asks |
| --- | --- |
| Problem framing / User Story | Real role and a non-hand-waved "in order to"? Is the direct "As X, I want Y, in order to Z" statement in the first line, or buried under preamble? If the ticket genuinely covers more than one story, is it a short plain-English bulleted list rather than one sentence forced to cover too much? |
| Scoping discipline | Is out-of-scope explicit? Is related-but-separate work (other ADRs, companion tickets) disentangled and referenced by GitHub issue number? |
| Acceptance criteria | Pure Given/When/Then, observable and testable? Unhappy paths covered? Any technical checkpoint (a field name, a status code, a schema detail) that should have moved to Technical Details? |
| Grounding accuracy | Are the concrete claims (files, functions, line numbers, "there is no way to X") true? Which will rot? |
| Structure | Is content in one canonical place, or restated across sections that will drift? Does Description (if present) sit below Acceptance Criteria, stay free of technical detail, and avoid narrating why the ticket is blocked, unsplit, or tied to a release? |
| Length / bloat | Is the ticket longer than the diff it will produce? What is pure repetition? |
| Language / writing | Sentence length, bold overuse, one-idea-per-sentence, scannability. |
| Level of implementation detail | Is Technical Details present (it's required, not optional), with both a plain-language "In short" pass and a factual "Implementation specifics" bullet list — or missing one of the two, a wall of bullets with no prose on-ramp, a prose spec with no concrete facts, or padded past what the ticket actually needs? |
| Collapsibility | Are Technical Details, Files to create and modify, and Context each wrapped in their own `<details>` block, with the blank lines GitHub needs to render the Markdown inside? Is anything else (User Story, Acceptance Criteria, Description, Open Questions) collapsed that should be open? |
| Helpfulness for a junior human | Can a junior hold it in working memory and start cold, or is it exhausting? |
| Helpfulness for an AI implementer | Do the User Story, Acceptance Criteria, and Technical Details give a complete, unambiguous brief on their own, without a separate implementer prompt restating them? |

## 3. Rewrite to a new local file

Write the improved ticket to a **new** file (e.g. `issue-<n>-cleaned.md` or, for a pasted
ticket, `<slug>-cleaned.md`) in the repo root or scratchpad. Never overwrite the source.
Apply these editorial principles, they are the method:

- **BLUF.** Lead with the User Story, stated directly: "As &lt;role&gt;, I want
  &lt;capability&gt;, in order to &lt;outcome&gt;." That is the shape of the work; it
  should land in the first line, not after preamble. If the source ticket genuinely
  covers more than one story, rewrite it as a short plain-English bulleted list rather
  than force it into one sentence — but don't split a single coherent story into bullets
  just for variety.
- **Say each idea once, canonically.** DRY applies to prose. State each invariant/rule in
  exactly one place (usually Technical Details → Implementation specifics, with "In
  short" giving the plain-language version of the same fact rather than a second,
  divergent one). Redundant copies drift out of sync when the ticket is edited and become
  contradictions.
- **Acceptance Criteria are pure Given/When/Then.** Strip out any technical checkpoint —
  a field name, a status code, a schema fact — and move the underlying requirement into
  Technical Details if it isn't captured there already. This applies even to backend or
  data-model tickets with no UI: rephrase around what's observed, not the mechanism.
- **Description is optional, and most tickets don't need one.** Keep it only if it
  carries something essential the User Story and Acceptance Criteria don't. Cut it to a
  few terse sentences, move it below Acceptance Criteria, and strip: implementation
  detail (→ Technical Details), any narration of why the ticket is blocked or wasn't
  split (→ drop, or Open Questions/Context with a GitHub issue reference if it's a real
  dependency), and any release or version timing (→ drop). If nothing survives that
  filter, delete the section.
- **Technical Details is required — never delete the section, only its bloat.** If the
  source ticket is missing it entirely, flag that as a gap rather than silently adding
  content you're inventing; if it exists, keep it (don't cut it down to nothing to hit a
  length target). Open it with a line noting it's background and a suggested approach,
  not the source of truth. Restructure it into the template's two parts: "In short", a
  few plain-language paragraphs (one per major mechanism or decision, each with a bold
  lead-in phrase) a non-specialist can follow, and "Implementation specifics", one bullet
  per concrete fact the prose doesn't spell out — a signature, a file location, a rule, a
  constraint. If the source is a wall of dense bullets with no prose on-ramp, write the
  missing "In short" paragraphs from what the bullets already say, don't invent new
  requirements. If it's unstructured prose, extract its concrete facts into
  "Implementation specifics" bullets underneath. Keep every real technical requirement the
  source ticket had in one part or the other; only the duplication and narration is cut,
  and being required doesn't mean padding either part past what the ticket needs.
- **Drop the Example Resolution Prompt entirely.** The current template has no such
  section. Before deleting one from a source ticket, check whether it's the only place
  carrying a real decision or constraint — if so, move that content up into Technical
  Details first, then delete the prompt. Do the same for any "implementation notes"
  paragraph duplicating what Technical Details already says.
- **Collapse the three supporting sections.** Technical Details, Files to create and
  modify, and Context each get their own `<details><summary>Section name</summary> ...
  </details>` wrapper, so the page a reader lands on is the User Story, the Acceptance
  Criteria, any Description, and three collapsed summaries. Leave a blank line after the
  `<summary>` line and before the closing `</details>`, or GitHub renders the Markdown
  inside as literal text, and replace the section's `##` heading with the `<summary>` line
  rather than keeping both. Never wrap the User Story, Acceptance Criteria, Description,
  or Open Questions this way; those stay open.
- **One Files table per direction, one line per file.** Collapse the Files table to a
  single line per file; don't restate the approach there.
- **Technical decisions live in Technical Details, and only there are they authoritative.**
  Technical Details states the contract, the specific decisions (a validation rule, a
  claiming precedence, an error-handling choice) as facts. The Files table is a
  one-line-per-file map that may reference the approach but is not where a decision is
  made. State each decision once, in Technical Details, rather than restating it in the
  Files table or anywhere else. When you move a decision up, confirm it is not silently
  dropped from what used to be its only home.
- **No line numbers.** Name files and functions; the implementer navigates. Drop stale or
  fragile precision.
- **GitHub issue numbers only.** Replace any internal ticket ID or spreadsheet reference
  with the equivalent GitHub issue number, or drop it if there's no public equivalent a
  reader outside the team could open.
- **Bullets for enumerables.** Anything you can count (out-of-scope items, files) is a
  list, not a bold-studded paragraph. Reserve bold for the few things that must not be
  missed.
- **Fix factual overstatements** surfaced in step 1 (including anything a maintainer
  already corrected in the comments).
- **Preserve the genuine strengths** verbatim or near-verbatim, do not rewrite what
  already works (a strong User Story, good Gherkin, a careful ADR disentangling).
- **Do not relitigate a settled design.** If an ADR or prior decision fixed the approach,
  keep it and do not reopen it in the ticket. If the design is *genuinely* unsettled, that
  belongs upstream (an ADR or `ticket-writer`), not smuggled into a cleanup, flag it and
  leave it.
- **Align to the canonical template**: User Story and Acceptance Criteria first, then
  only the optional sections that earn their place (Description, Technical Details,
  Files, Context) in template order, Open Questions last. Use the house section names.
  Omit empty tables and empty optional sections.

## 4. Second pass: re-review your own rewrite

Do not trust the first rewrite. Re-read it cold, as if someone else wrote it, and put it
back through the step 2 rubric. The first pass reliably leaves residual redundancy in the
technical middle: the same mechanism restated across Technical Details and the Files
table, or a leftover implementer-prompt paragraph that should have been deleted outright.
Hunt that specifically, and check that Technical Details and the Files table actually sit
at different altitudes rather than repeating each other. If the re-review finds anything
past cosmetic nits, rewrite again and repeat; stop only when a pass turns up nothing but
nits. Each time you tighten, confirm the tightened version still says everything the
prior one did, no requirement, constraint, or fact lost in the edit.

## 5. Summarize what changed and why

Close with a short changelog: each significant cut or restructure traced to the principle
behind it (bloat, redundancy, over-specification, buried ask, stale line numbers, a
dropped Example Resolution Prompt, an internal ID swapped for a GitHub issue number,
a section wrapped in a collapsible block, a User Story split into bullets for a
genuinely multi-story ticket, a factual fix). State what you deliberately kept and why.
Call out, as one explicit judgment, any design question you left untouched because it is
upstream/ADR work rather than a cleanup concern. If Technical Details was missing from
the source ticket entirely, call that out explicitly rather than silently filling it in.
