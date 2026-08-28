---
name: clean-up-text
description: Editorial and structural cleanup of an already-written technical text (a doc, ADR, README, RFC, design note, PR or commit body, migration guide, long chat write-up), then a rewritten version written to a new local file. Use when asked to clean up, tighten, trim, de-bloat, condense, restructure, or improve the writing of an existing technical document, or for a brutally honest review of how well it reads. It first audits what the text assumes its reader already knows, grades the text across fixed dimensions (prerequisites, lead, structure, length, bloat, level of detail, grounding accuracy, readability, helpfulness for a junior human and for an AI reader), rewrites it toward whatever canonical shape that kind of document has, and then sends the rewrite to a dedicated accuracy reviewer that confirms nothing was lost, altered, or invented. It does NOT reopen the decisions the text records; beyond defining what a reader needs in order to follow the text, it invents no content and preserves the substance. For a ticket or issue specifically, use clean-up-ticket instead. Advisory: writes to a new local file, never overwrites the source and never publishes anywhere.
---

# Clean up a technical text

Take an existing, already-settled technical document and make it a great one to *read and
act on*: review it brutally honestly, then write a tightened version to a new local file.
The point is editorial and structural quality, not discovering or re-deciding what the
document should say.

## What this skill is, and is not

- **It is** an editorial and structural pass on a text whose content and decisions are
  already settled. It fixes bloat, redundancy, a buried point, over-specification, weak
  structure, and unreadable prose, and rewrites toward the canonical shape for that kind
  of document.
- **It is not** content or design interrogation. It preserves the substance and the
  decisions the text records; it does not ask the user clarifying questions, dispatch
  planning experts, or add and remove claims. The one exception is definitional: where the
  text leans on a term or a relationship it never explains, the rewrite may state what that
  thing is, sourced from ground truth and verified by step 6. Explaining what the source
  assumed is not the same as adding a claim of your own.
- **When to hand off instead:** if the substance is unclear or contested, the point the
  document is making is missing, or a decision it records is genuinely unsettled, this is
  the wrong skill. Say so and point upstream (back to the author, to an ADR for a design
  question, to `ticket-writer` for a ticket), rather than guessing at intent under the
  guise of cleanup.
- **Advisory.** Produces a review and writes the improved text to a **new** local file.
  Never overwrite the source, and publish nowhere (no PR body updated, no wiki page
  edited, no comment posted) except on explicit request and approval.

## Read first

Whatever defines the canonical shape for this kind of document, if anything does:

- A template file in the repo, when one exists for this document type.
- Otherwise the best sibling document of the same kind (the clearest existing ADR, the
  README of a neighboring app), used as the model for section order and section names.
- The **Writing style** and **Say it in full** sections of `CLAUDE.md`, always. They are
  the house style, and the rewrite conforms to them.

Some inputs have no type: a review comment on a proposal, a design note, a long chat
write-up. For those, no template and no sibling document will exist, and a related skill's
output spec (`code-review`'s finding format, say) is not a document of the same kind. Borrow
at most its section vocabulary, never its apparatus. Choose a shape yourself, state in the
review which shape you chose and why, and hold it consistently through the rewrite.

## Model and context

Whoever runs this skill does the review and the rewrite; that judgment is the whole point
of the skill. The text under review and its template are small, read them inline. Per the
Delegation rule in `CLAUDE.md`, if you are the top-level session, push context-heavy
*fetching* down yourself: a URL or a published page to a Sonnet sub-agent, code-location
lookups to a Haiku `Explore`. Never read a neighbor repo (`openedx-platform`,
`frontend-app-authoring`) into context to verify a claim; use its overview doc, or dispatch a
narrow Sonnet sub-agent per the same rule.

**If you were dispatched to run this skill**, none of the dispatching above is yours to do,
because you have no Agent tool. Fetch nothing yourself: return a "Needs research" item to
whoever dispatched you. Step 6's accuracy gate is also a dispatch, so you cannot run it
either. Finish the rewrite, then return the gate as an explicit "Needs verification" item
naming the source path, the rewrite path, and the ground truth behind every definition you
added. Never skip the gate silently, and never self-certify accuracy in its place.

## 1. Get the text and ground it

- **Intake.** Pasted text: use it. A file path: read it. A URL or a page behind a tool:
  delegate the fetch to a Sonnet sub-agent, never inline. If the source carries review
  feedback alongside it (PR review comments, doc comments, an email thread), read that
  too; a reviewer may have already flagged a factual error you would otherwise reproduce.
- **Spot-check the falsifiable claims**, cheaply and targeted. Does each referenced file,
  function, setting, and command exist? Are the line numbers accurate? Is a categorical
  assertion ("there is no way to X", "this always happens") actually true? A couple of
  `grep`s or one Haiku `Explore` for location is enough; do not audit the codebase. Note
  anything wrong or overstated, it feeds both the review and the rewrite. **Treat line
  numbers as a liability even when currently correct:** they rot on the next merge and
  read as false precision, so the rewrite drops them.
- **Note any reference a reader of the finished text could not follow.** Internal ticket
  or spreadsheet IDs, local scratch filenames, "as we discussed", a link only the author
  can open. The rewrite replaces each with a public equivalent, restates the load-bearing
  content inline, or drops it.

## 2. Audit what the reader must already know

A text that reads badly to an outsider is usually not badly written. It is written for
someone who already holds a model the reader does not hold. Establish that before grading
anything.

Name the intended reader in one line, then write out two lists. Both are mechanical: put
the lists on the page rather than judging in your head, because a judgment call here
reliably flatters the source.

1. **Undefined load-bearing terms.** Every term, model name, table, role, and piece of
   jargon the text leans on without ever saying what it is, each with a count of how often
   it appears. A word used fifteen times and defined zero times is the single most common
   reason a technical text is unreadable outside the conversation that produced it.
2. **Assumed structure.** Every relationship the argument needs and never states: what
   contains what, what is derived from what, which of several similarly named things is the
   one that matters here, and in what order things happen.

Then close the gaps. For each entry on either list that the rewrite will need to explain,
read the authoritative source in this repo, the ADR or the model or the module that defines
it, and note the definition **together with where you got it**. This is the only place this
skill adds content the source did not have, so every added definition carries its source and
step 6 verifies it. Stay bounded: look up what the reader needs defined, not everything
nearby.

If both lists come back empty, that is a real result. Say so in the review and move on.

## 3. Brutally honest review, verdict first

Lead with a one-line verdict, then a graded table across the fixed rubric below, then a
short dimension-by-dimension section quoting the text's own words for each point. Be
brutally honest but fair: name the genuine strengths too, a review that only attacks is
not trustworthy. Grade each dimension (A-F is fine) so the author sees at a glance where
it stands.

Rubric:

| Dimension | The question it asks |
| --- | --- |
| Prerequisites | Can the intended reader enter the document at all? Grade against step 2's two lists, weighted by what the gaps actually cost: a term the argument turns on counts, a term mentioned once in passing does not. Nearly every real technical document has a non-empty list, so the list alone is not the finding. What it means is that the rewrite owes the reader a prerequisites section. |
| Lead | Does the first line say what this document is and what it wants from the reader, or is the point buried under preamble, history, and throat-clearing? Would a reader who stops after the first paragraph have the main thing? |
| Scoping discipline | Is the subject bounded, and is the boundary stated where a reader would wonder? Is related-but-separate material disentangled and referenced rather than inlined and re-explained? |
| Grounding accuracy | Are the concrete claims (files, functions, commands, versions, line numbers, "there is no way to X") true? Which will rot? |
| Structure | Is content in one canonical place, or restated across sections that will drift? Do the sections run in an order a reader can follow, and does each heading say what its section is about rather than a shorthand only the author can expand? |
| Length / bloat | Is the document longer than the thing it describes deserves? What is pure repetition, and what is narration of how the document came to be rather than what it says? |
| Language / writing | Sentence length, bold overuse, one idea per sentence, scannability. Complete sentences rather than headline fragments. Does every "this", "it", and "that" have an antecedent the reader can point at? |
| Level of detail | Judge the document as a whole, not one item at a time: an argument whose every step explains its own mechanism can still be impossible to enter, which is what step 2 measures. Does the whole document give a non-specialist a way in and a specialist the concrete facts, without padding past what it needs? |
| Formatting mechanics | Does the markup actually render? Tables well-formed, code fences opened and closed and language-labeled, list nesting consistent, and any `<details>` block carrying the blank lines the renderer needs around its inner Markdown. |
| Helpfulness for a junior human | Two questions, both required. Could a junior follow it on one pass without looking anything up, which is what step 2's lists answer? And can they hold it in working memory and act on it cold, or is it exhausting? |
| Helpfulness for an AI reader | Do the sections give a complete, unambiguous brief on their own, without a second document restating them? |

## 4. Rewrite to a new local file

Write the improved text to a **new** file (e.g. `<original-name>-cleaned.md`, or
`<slug>-cleaned.md` for pasted text) in the repo root or scratchpad. Never overwrite the
source. Apply these editorial principles, they are the method. Four of them do most of the
work on a first draft: lead with the point, give the reader the model first, say each idea
once, and turn same-shaped prose into a table. Draft with those four, then run the rest as a
checklist during step 5 rather than trying to hold all of them at once.

- **BLUF.** Lead with the point: what this document is, and what the reader is supposed to
  do or know as a result. That belongs in the first line, not after preamble. If the
  document genuinely covers several parallel points, lead with a short plain-English
  bulleted list rather than force them into one sentence, but do not split a single
  coherent point into bullets just for variety.
- **Give the reader the model first.** If step 2's lists were not empty, open with a short
  prerequisites section stating the terms and structure the rest of the text assumes: what
  the things are, how they relate, which name means which. Put it before the body, hold it
  to what the document actually leans on, mark it skippable for the reader who already knows
  ("Skip this if you know the model"), and source every definition. It usually pays for
  itself: once the model is stated once, every item below stops re-explaining it.
- **Say each idea once, canonically.** DRY applies to prose. State each rule, invariant,
  and decision in exactly one place, and let any plain-language summary elsewhere give the
  same fact rather than a second, divergent one. Redundant copies drift out of sync when
  the document is edited and become contradictions.
- **Keep the altitudes separate.** A summary, the body, and a reference table are
  different altitudes on the same material, not three copies of it. When two sections say
  the same thing at the same level of detail, one of them is dead weight: pick the
  canonical home and cut the other down to a pointer.
- **Every section earns its place.** Keep an optional section only if it carries something
  essential the rest does not. Cut it to a few terse sentences, put it where a reader would
  look for it, and strip out material that belongs in a different section. If nothing
  survives that filter, delete the section.
- **Never delete a section for its bloat alone.** This and the bullet above are different
  tests, and both apply: "earns its place" asks whether any substance survives, while this one
  forbids cutting for length. A required section that is merely padded gets trimmed, never
  deleted. A section with no substance left goes. If a section is required for this
  document type, keep it and cut only the duplication and narration inside it. If a
  required section is missing from the source entirely, flag that as a gap rather than
  silently inventing content to fill it. Being required does not license padding either.
- **Give dense technical content both halves.** A few plain-language paragraphs, one per
  major mechanism or decision, each with a bold lead-in phrase, that a non-specialist can
  follow; and a bullet list of the concrete facts the prose does not spell out, one per
  signature, file location, rule, or constraint. If the source is a wall of dense bullets
  with no prose on-ramp, write the missing paragraphs from what the bullets already say,
  do not invent new claims. If it is unstructured prose, extract its concrete facts into
  bullets underneath. Keep every real technical fact the source had in one half or the
  other.
- **Explain a mechanism before naming consequences of it.** A reader who does not yet know
  how something works cannot evaluate a claim about what it costs. Reorder where the
  source gets this backwards.
- **Delete anything that narrates the document rather than the subject.** How the text
  came to be written, why it was not split, what was cut, what a previous draft said, and
  any release or version timing that is not itself the subject. History lives in `git log`.
  Before deleting such a passage, check whether it is the only place carrying a real
  decision or constraint; if it is, move that content into its proper section first, then
  delete the passage.
- **No line numbers.** Name files and functions; the reader navigates. Drop stale or
  fragile precision.
- **Public references only.** Replace every internal ID, scratch filename, private link, and
  bare in-conversation pointer ("as suggested on <date>", "as we discussed", "see the thread")
  with a reference a reader outside the conversation could open, restate the load-bearing
  content inline, or drop it.
- **Bullets for enumerables.** Anything you can count (out-of-scope items, files, steps,
  options) is a list, not a bold-studded paragraph. Reserve bold for the few things that
  must not be missed. For a decision with a few distinct options, use a comparison table
  over paragraphs. Three or more items sharing one argument shape, each of them some
  variation on *X says A, we do B, so fix C*, become a table with those columns rather than
  three or more paragraphs. Same-shaped prose is where a document hides most of its length,
  but only if the cells are terse: a table of full paragraphs costs more than the prose it
  replaced and buys nothing but a border.
- **One source per claim.** Cite the single strongest source for a point and drop the
  corroborating ones. A sentence citing three decisions and two rejected alternatives to
  establish one fact costs the reader more than the extra citations are worth. The exception
  is a claim whose whole point is convergence: when the finding is that three separate
  decisions independently assert the same outdated thing, the multiplicity *is* the finding
  and every citation stays. Cut corroborating citations, never converging ones.
- **Fix factual overstatements** surfaced in step 1, including anything a reviewer already
  corrected in the feedback attached to the source.
- **Preserve the genuine strengths** verbatim or near-verbatim. Do not rewrite what already
  works. Precision, completeness, and mechanism-before-consequence are strengths and stay.
  The author's assumed level of knowledge is not one of them. An expert-to-expert register
  reads as a strength on its own terms and is the very thing that makes a text unenterable,
  so keep the precision and drop the assumption.
- **Do not relitigate settled content.** If a decision is fixed, keep it and do not reopen
  it here. If it is *genuinely* unsettled, that belongs upstream rather than smuggled into
  a cleanup: flag it and leave it.
- **Align to the canonical shape** you identified in "Read first": house section names,
  template section order, the optional sections that earned their place. Omit empty tables
  and empty optional sections. Apparatus the reader has to learn, a severity vocabulary or a
  marker taxonomy or a numbering convention, is a cost rather than a free improvement: adopt
  it only where it tells the reader something the section headings do not, and drop it once
  the headings carry it.
- **Count the words: the source, the rewrite, and the rewrite minus any prerequisites
  section.** Run `wc -w`, never estimate, and report all three. The third number is the test:
  the body must come in at or under the source, because the prerequisites section is the only
  growth this skill licenses. If the body will not come down, say so plainly and say why,
  rather than forcing real deletions to hit a number or quietly declaring victory. A source
  that explained nothing inline has little for a prerequisites section to reclaim, so a total
  that grows by roughly what that section cost is an honest outcome. A body that grew is not.

## 5. Second pass: re-review your own rewrite

Do not trust the first rewrite. Re-read it cold, as if someone else wrote it, and put it
back through the step 2 rubric. The first pass reliably leaves residual redundancy in the
technical middle: the same mechanism restated in two sections, or a leftover summary
paragraph that should have been deleted outright once its content moved. Hunt that
specifically, and check that sections which should sit at different altitudes actually do
rather than repeating each other. If the re-review finds anything past cosmetic nits,
rewrite again and repeat; stop only when a pass turns up nothing but nits. Each time you
tighten, confirm the tightened version still says everything the prior one did. That
self-check is worth doing and is not sufficient: step 6 is the independent check on it, and
passing your own eye over the text is not a reason to skip it.

## 6. Accuracy gate: an independent verification pass

Writing quality and technical truth are different properties, and one pass cannot check
both. Step 5 was yours. This one is not yours, because you cannot audit a text against a
source you have just spent two passes reshaping.

Dispatch the **`doc-accuracy-reviewer`** agent, Sonnet at high effort per the Delegation
table in `CLAUDE.md`, passing the source path, the rewrite path, and every ground-truth
source behind a definition you added in step 2, and the changelog of what you cut on
purpose, which the agent needs in order to tell a deliberate cut from a loss. If the agent
type does not resolve, which can happen for a while after the agent file is first added,
dispatch a Sonnet `general-purpose` agent instead and tell it to read
`.claude/agents/doc-accuracy-reviewer.md` and adopt it as its brief. A registration problem
is not a reason to skip the gate. It runs three checks, nothing lost, nothing
altered in meaning or force, and nothing invented, and it verifies your added definitions
itself instead of trusting your citations.

- **Nothing ships past a FAIL.** Correct what it found and dispatch it again on the
  corrected text. A gate you overrule is not a gate.
- **On PASS WITH FIXES**, apply the fixes, and re-dispatch only when a fix was substantive
  rather than a wording correction.
- **Do not argue with a finding you cannot disprove.** If the agent has it wrong, show the
  ground truth that makes it wrong. Otherwise treat the finding as correct.
- The added definitions are the highest-risk part of the rewrite, because a plausible wrong
  definition reads as authoritative. Make sure the agent's report says explicitly which ones
  it checked.

If you cannot dispatch because you are yourself a sub-agent, return the gate as a "Needs
verification" item per **Model and context** above. An unverified rewrite is not done.

## 7. Summarize what changed and why

Close with a short changelog: each significant cut or restructure traced to the principle
behind it (bloat, redundancy, over-specification, a buried point, stale line numbers, a
duplicated summary deleted, an internal ID swapped for a public reference, sections
reordered, a lead rewritten as bullets for a genuinely multi-point document, a factual
fix). State what you deliberately kept and why. Call out, as one explicit judgment, any
substantive question you left untouched because it is upstream work rather than a cleanup
concern. If a section required for this document type was missing from the source
entirely, call that out explicitly rather than silently filling it in.

Report alongside the changelog: the word count before and after, the accuracy gate's verdict
with any finding you corrected because of it, and the definitions the rewrite added with the
ground truth each came from. If the gate could not be run, say so in place of a verdict
rather than leaving it unmentioned.
