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

`.claude/ticket-template.md`, the canonical shape you rewrite toward. User Story,
Description, and Context are human-written and come first, in that order; the
UX Design placeholder follows on a frontend ticket; then Acceptance Criteria; then
Technical Details, the one required, collapsible section, wrapped in its own `<details>`
block; Open Questions is last. The template defines how much (and how little) belongs in
Technical Details (an optional Summary, a required Approach, an optional Files table, an
optional Additional context) and that there is no Example Resolution Prompt.

**The title, User Story, Description, and Context are human-written and must be left verbatim.**
Never rewrite, reword, reorder, or reformat them, even to fix something that looks wrong.
If you see a genuine problem with one, note it as a review finding for the person running
the session to act on, not as a change to the rewrite.

**A ticket already posted in the old format** (an "In short" / "Implementation specifics"
split, separate Files and Context collapsible blocks, a Description sitting below
Acceptance Criteria) is cleaned up within its existing structure. Don't restructure it into
the new template shape unless the user explicitly asks for that.

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
| Problem framing / User Story | Are User Story, Description, and Context present (or their absence flagged, not filled in) and left exactly as the human wrote them? Is the User Story's "As X, I want Y, in order to Z" direct and unburied, or, for a genuinely multi-story ticket, a short plain-English bulleted list? |
| Scoping discipline | Is out-of-scope explicit? Is related-but-separate work (other ADRs, companion tickets) disentangled and referenced by GitHub issue number? |
| Acceptance criteria | Pure Given/When/Then (or a checkbox list for an artifact ticket), observable and testable? Unhappy paths covered? Any technical checkpoint (a field name, a status code, a schema detail) that should have moved to Technical Details? |
| Grounding accuracy | Are the concrete claims (files, functions, line numbers, "there is no way to X") true? Which will rot? |
| Structure | Is content in one canonical place, or restated across sections that will drift? Does the ticket follow the template's order: User Story, Description, Context, UX Design placeholder (frontend only), Acceptance Criteria, Technical Details, Open Questions? |
| Length / bloat | Is the ticket longer than the diff it will produce? What is pure repetition? |
| Language / writing | Sentence length, bold overuse, one-idea-per-sentence, scannability. |
| Level of implementation detail | Is Technical Details present (it's required, not optional)? Does it carry a Summary only when the Approach runs past about 15 lines, an Approach written as pseudo code or numbered steps naming real files and functions, no obvious filler a developer here wouldn't need spelled out, and is the whole section short enough for an Axim engineer with two minutes to approve? |
| Collapsibility | Is Technical Details the only collapsed section, wrapped in its own `<details>` block with the blank lines GitHub needs to render the Markdown inside? Does a frontend ticket have the UX Design placeholder? Is anything else (User Story, Description, Context, Acceptance Criteria, Open Questions) collapsed that should be open? |
| Helpfulness for a junior human | Can a junior hold it in working memory and start cold, or is it exhausting? |
| Helpfulness for an AI implementer | Do the User Story, Acceptance Criteria, and Technical Details give a complete, unambiguous brief on their own, without a separate implementer prompt restating them? |

## 3. Rewrite to a new local file

Write the improved ticket to a **new** file (e.g. `issue-<n>-cleaned.md` or, for a pasted
ticket, `<slug>-cleaned.md`) in the repo root or scratchpad. Never overwrite the source.
Apply these editorial principles, they are the method:

- **Lead with the human-written sections, untouched.** User Story, Description, and
  Context are frozen: copy them exactly as the human wrote them, in that order, as the
  ticket's first lines. Don't rewrite, reorder within, or otherwise touch their wording,
  even to fix something that looks wrong; raise a genuine problem as a finding in the
  review instead, never as a silent edit.
- **Say each idea once, canonically.** DRY applies to prose. State each invariant or rule
  in exactly one place, normally the Technical Details Approach, and don't restate it in
  the Files table or Additional context. Redundant copies drift out of sync when the
  ticket is edited and become contradictions.
- **Acceptance Criteria are pure Given/When/Then, or a checkbox list for an artifact
  ticket.** Strip out any technical checkpoint, a field name, a status code, a schema
  fact, and move the underlying requirement into Technical Details if it isn't captured
  there already. This applies even to backend or data-model tickets with no UI: rephrase
  around what's observed, not the mechanism. The one exception, per the template: an
  artifact ticket (schema-only or migration-only work, repository scaffolding,
  packaging/install/config) uses a checkbox list of facts a reviewer confirms at code
  review time instead of Gherkin.
- **Description is human-written; leave it alone.** It's not yours to draft, trim, or
  rephrase. If it's missing, flag the gap rather than writing one. If something in it
  looks wrong, technical, or narrates why the ticket is blocked, raise that as a finding
  for the human to act on, don't edit it out. It sits second, right after the User Story,
  per the template's order.
- **Technical Details is required: never delete the section, only its bloat.** If the
  source ticket is missing it entirely, flag that as a gap rather than silently adding
  content you're inventing; if it exists, keep it (don't cut it down to nothing to hit a
  length target). Open it with a line noting it's a suggested approach, not the source of
  truth. Restructure it into the template's single block, in order: an optional
  **Summary** (only when the Approach runs past about 15 lines; if the source Approach is
  15 lines or fewer, drop any Summary it has), the required **Approach** as pseudo code or
  numbered steps naming real files, classes, functions, and endpoints, an optional
  **Files to create and modify** table, and an optional **Additional context**. Cut
  anything a competent developer on this codebase would do without being told ("add
  tests", "run the migration", "register the URL"). Keep every real technical requirement
  the source ticket had; only the duplication, narration, and obvious filler is cut, and
  the whole section should be short enough that an Axim engineer with two minutes could
  approve it.
- **Drop the Example Resolution Prompt entirely.** The current template has no such
  section. Before deleting one from a source ticket, check whether it's the only place
  carrying a real decision or constraint — if so, move that content up into Technical
  Details first, then delete the prompt. Do the same for any "implementation notes"
  paragraph duplicating what Technical Details already says.
- **Collapse only Technical Details.** Wrap it in
  `<details><summary>Technical Details</summary> ... </details>`, so the page a reader
  lands on is the human-written sections, the UX Design placeholder on a frontend ticket,
  and the Acceptance Criteria, plus one collapsed summary. Leave a blank line after the
  `<summary>` line and before the closing `</details>`, or GitHub renders the Markdown
  inside as literal text, and replace the section's `##` heading with the `<summary>` line
  rather than keeping both. Never wrap the User Story, Description, Context, UX Design
  placeholder, Acceptance Criteria, or Open Questions this way; those stay open.
- **One Files table, one line per file.** A single table with a File | Change column
  marking each file new or modified; don't restate the approach there.
- **Technical decisions live in Technical Details, and only there are they authoritative.**
  Technical Details states the contract, the specific decisions (a validation rule, a
  claiming precedence, an error-handling choice) as facts. The Files table is a
  one-line-per-file map that may reference the approach but is not where a decision is
  made. State each decision once, in Technical Details, rather than restating it in the
  Files table or anywhere else. When you move a decision up, confirm it is not silently
  dropped from what used to be its only home.
- **Say what things are, and how they are now.** Delete any sentence about what
  something isn't, or about how an earlier draft or assumption had it, per the Writing
  style rule in `CLAUDE.md`. Keep negatives that are themselves requirements: out-of-scope
  items, "must not" rules, and AC outcomes like "the learner does not see the badge".
  Don't apply this to the human-written sections; flag it there as a finding instead.
- **No line numbers.** Name files and functions; the implementer navigates. Drop stale or
  fragile precision.
- **GitHub issue numbers only.** Replace any internal ticket ID or spreadsheet reference
  with the equivalent GitHub issue number, or drop it if there's no public equivalent a
  reader outside the team could open.
- **Bullets for enumerables.** Anything you can count (out-of-scope items, files) is a
  list, not a bold-studded paragraph. Reserve bold for the few things that must not be
  missed.
- **Fix factual overstatements** surfaced in step 1 (including anything a maintainer
  already corrected in the comments), but never in a human-written section; raise those as
  findings instead.
- **Preserve the genuine strengths** verbatim or near-verbatim, do not rewrite what
  already works (good Gherkin, a careful ADR disentangling).
- **Do not relitigate a settled design.** If an ADR or prior decision fixed the approach,
  keep it and do not reopen it in the ticket. If the design is *genuinely* unsettled, that
  belongs upstream (an ADR or `ticket-writer`), not smuggled into a cleanup, flag it and
  leave it.
- **Align to the canonical template**: User Story, Description, and Context
  (human-written, verbatim) first, then the UX Design placeholder on a frontend ticket,
  then Acceptance Criteria, then Technical Details, the only collapsible section, with
  Open Questions last. Use the house section names. Omit empty tables and empty optional
  sections.

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
a factual fix). State what you deliberately kept and why.
Call out, as one explicit judgment, any design question you left untouched because it is
upstream/ADR work rather than a cleanup concern. If Technical Details was missing from
the source ticket entirely, call that out explicitly rather than silently filling it in.
