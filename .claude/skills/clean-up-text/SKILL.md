---
name: clean-up-text
description: Editorial and structural cleanup of an already-written technical text (a doc, ADR, README, RFC, design note, PR or commit body, migration guide, long chat write-up), then a rewritten version written to a new local file. Use when asked to clean up, tighten, trim, de-bloat, condense, restructure, or improve the writing of an existing technical document, or for a brutally honest review of how well it reads. It audits what the text assumes its reader already knows, grades it against a fixed rubric, rewrites it toward whatever canonical shape that kind of document has, and sends the result to a dedicated fidelity reviewer that confirms the technical concepts and decisions survived the rewrite unchanged, and that flags anything the rewrite added for you to confirm. It does NOT reopen the decisions the text records; beyond defining what a reader needs in order to follow the text, it invents no content and preserves the substance. For a ticket or issue specifically, use clean-up-ticket instead. Advisory: writes to a new local file, never overwrites the source and never publishes anywhere.
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
  planning experts, or add and remove claims. The one exception is definitional, and step 2
  governs it: explaining what the source assumed is not adding a claim of your own.
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

Whoever runs this skill does the review and the rewrite; that judgment is the whole point of
the skill. The text under review and its template are small, read them inline. Per the
Delegation rule in `CLAUDE.md`, if you are the top-level session, push context-heavy
*fetching* down yourself: a URL or a published page to a Sonnet sub-agent, code-location
lookups to a Haiku `Explore`, a neighbor repo (`openedx-platform`, `frontend-app-authoring`)
never into your own context.

**If you were dispatched to run this skill**, none of the dispatching above is yours to do,
because you have no Agent tool. You keep your own read tools, so run the cheap local checks
yourself, a `grep` or a file read, exactly as a top-level runner would. What you cannot do is
delegate: return a "Needs research" item for anything needing a network fetch or a sub-agent.
Step 6's accuracy gate is also a dispatch, so finish the rewrite and return the gate as a
"Needs verification" item naming the source path, the rewrite path, and your changelog, plus
the list of definitions you added for a human to confirm. Never skip the gate silently, and
never self-certify accuracy in its place.

Stated plainly, because it is otherwise an inference across two sections: **a dispatched run
of this skill never reaches a finished state.** It always ends at a handoff, because the gate
that would finish it is not yours to run.

## 1. Get the text and ground it

- **Intake.** Pasted text: use it. A file path: read it. A URL or a page behind a tool:
  delegate the fetch to a Sonnet sub-agent, never inline. If the source carries review
  feedback alongside it (PR review comments, doc comments, an email thread), read that
  too; a reviewer may have already flagged a factual error you would otherwise reproduce.
  Check whether the input is also read as live configuration somewhere (a `CLAUDE.md`, a
  skill, a settings file). If it is, say so in the review: the rewrite is a proposal about
  something with behavior attached, not just a document.
- **Spot-check the falsifiable claims**, cheaply and targeted. Does each referenced file,
  function, setting, and command exist? Are the line numbers accurate? Is a categorical
  assertion ("there is no way to X", "this always happens") actually true? A couple of
  `grep`s or one Haiku `Explore` for location is enough; do not audit the codebase. Note
  anything wrong or overstated, it feeds both the review and the rewrite. **Treat line
  numbers as a liability even when currently correct:** they rot on the next merge and
  read as false precision, so the rewrite drops them.
- **Note any reference a reader of the finished text could not follow**, for the rewrite to
  deal with under "Every reference must be one the reader can follow" in step 4.

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

Then close the gaps. For each entry the rewrite will need to explain, find the authoritative
definition and note it **together with where you got it**. This is the only place this skill
adds content the source did not have, so every definition carries its provenance. The gate in
step 6 compares the two texts only and cannot confirm a definition is true, so the provenance
is what lets the author check it. Where to look depends on the kind of term:

- **Repo-native terms**, a model, an ADR concept, a setting, have a source here. Read it and
  cite it.
- **External vocabulary**, a third-party tool, an ecosystem term, an acronym, has no in-repo
  source and never will. Define it from general knowledge and mark the definition
  **unsourced**, so step 6 scrutinizes it and the author can confirm it. Do not hunt the repo
  for a definition that cannot be there.

Stay bounded: look up what the reader needs defined, not everything nearby.

If both lists come back empty, that is a real result. Say so in the review and move on.

## 3. Brutally honest review, verdict first

Lead with a one-line verdict, then a graded table across the fixed rubric below, then a
short dimension-by-dimension section quoting the text's own words for each point. Be
brutally honest but fair: name the genuine strengths too, a review that only attacks is
not trustworthy. Grade each dimension (A-F is fine) so the author sees at a glance where
it stands.

Scale the review to the source. Every dimension gets a grade, always, but only the ones that
are actually costing the reader get a written justification; the rest need a few words. A
review that approaches the length of the document it reviews has become part of the bloat
problem it exists to name.

Rubric:

| Dimension | The question it asks |
| --- | --- |
| Prerequisites | Can the intended reader enter the document at all? Grade against step 2's lists, weighted by what each gap costs: a term the argument turns on counts, one mentioned in passing does not. Nearly every real document has a non-empty list, so the list alone is not the finding; what it means is that the rewrite owes the reader a prerequisites section. |
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
`<slug>-cleaned.md` for pasted text) in the repo root or scratchpad. Apply these editorial
principles, they are the method. Four of them do most of the
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
  and decision in exactly one place; redundant copies drift apart on the next edit and
  become contradictions. A summary, the body, and a reference table are three altitudes on
  the material, not three copies of it, so a summary may restate a fact more briefly but
  never at the same level of detail. Where two passages sit at the same altitude, pick the
  canonical home and cut the other to a pointer.
- **Two tests decide a section's fate, and both apply.** Does it carry something essential
  the rest does not, and is it required for this document type? An optional section carrying
  nothing essential gets deleted. Everything else gets trimmed, never deleted: cut the
  duplication and the narration inside it, put it where a reader would look, and move out
  material belonging to another section. Length alone is never grounds for deleting a
  section, and being required never licenses padding. If a required section is missing from
  the source, flag the gap rather than inventing content to fill it.
- **Give dense technical content both halves.** A plain-language paragraph per major
  mechanism, each with a bold lead-in, that a non-specialist can follow; and beneath it the
  concrete facts, one bullet per signature, file location, rule, or constraint. Supply
  whichever half the source lacks, drawn from what it already says rather than from new
  claims, and keep every technical fact it had in one half or the other.
- **Explain a mechanism before naming consequences of it.** A reader who does not yet know
  how something works cannot evaluate a claim about what it costs. Reorder where the
  source gets this backwards.
- **Delete anything that narrates the document rather than the subject.** How the text
  came to be written, why it was not split, what was cut, what a previous draft said, and
  any release or version timing that is not itself the subject. History lives in `git log`.
  Before deleting such a passage, check whether it is the only place carrying a real
  decision or constraint; if it is, move that content into its proper section first, then
  delete the passage.
- **Every reference must be one the reader can follow.** Drop line numbers and name the file
  and function instead; the reader navigates, and line numbers rot. Replace internal IDs,
  scratch filenames, private links, and bare in-conversation pointers ("as suggested on
  <date>", "as we discussed", "see the thread") with a public equivalent, restate the
  load-bearing content inline, or drop it.
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

### The length check

Unlike the bullets above, which are craft, this is a pass/fail gate. Run it as a check.

Count the words with `wc -w`, never by estimate, and report all three numbers: the source,
the rewrite, and the rewrite minus any prerequisites section. **The third is the test: the
body must come in at or under the source**, because the prerequisites section is the only
growth this skill licenses. A total that grew by roughly what that section cost is an honest
outcome. A body that grew is not. If the body will not come down, say so and say why, rather
than forcing real deletions to hit a number or quietly declaring victory.

## 5. Second pass: re-review your own rewrite

Do not trust the first rewrite. Re-read it cold, as if someone else wrote it, and put it
back through the step 3 rubric. The first pass reliably leaves residual redundancy in the
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
table in `CLAUDE.md`. Pass it three things: the source path, the rewrite path, and your
changelog of deliberate cuts, without which it cannot tell a cut from a loss. It compares the
two texts against each other and nothing else, deliberately: it does not research the repo,
because that costs far more than it returns here. It checks that nothing was lost, that
nothing changed meaning or force, that every count adds up, and it recognizes a concept
restated in different words as unchanged rather than reporting it.

Agent definitions are snapshotted when the type first registers, not re-read on each
dispatch. Two situations therefore need the fallback: the type does not resolve at all, which
happens for a while after the file is first added, and the brief has been edited during this
session, in which case the live type silently still holds the old text and its old tool list.
In either case dispatch a Sonnet `general-purpose` agent and tell it to read
`.claude/agents/doc-accuracy-reviewer.md` and adopt it as its brief, which reads the file
fresh from disk. Neither situation is a reason to skip the gate.

- **Nothing ships past a FAIL.** Correct what it found and dispatch it again on the
  corrected text. A gate you overrule is not a gate.
- **On PASS WITH FIXES**, apply the fixes, and re-dispatch only when a fix was substantive
  rather than a wording correction.
- **Do not argue with a finding you cannot disprove.** If the agent has it wrong, show the
  ground truth that makes it wrong. Otherwise treat the finding as correct.
- **The agent flags what the rewrite added; it does not certify it.** Confirming an added
  definition needs the research this gate deliberately skips. Its Additions list is therefore
  the rewrite's residual risk, and closing it is the author's job: carry that list into step 7
  so a human sees it, and never treat a PASS as evidence that a definition you wrote is true.

An unverified rewrite is not done.

## 7. Summarize what changed and why

Close with a short changelog: each significant cut or restructure traced to the principle
behind it, naming the principle rather than describing the edit. State what you deliberately
kept and why. Call out, as one explicit judgment, any
substantive question you left untouched because it is upstream work rather than a cleanup
concern. If a section required for this document type was missing from the source
entirely, call that out explicitly rather than silently filling it in.

Report alongside the changelog: the three word counts, the gate's verdict with any finding
you corrected because of it, and **every definition the rewrite added, with its provenance
and a note that nobody has confirmed it**. That last list is the one thing here a human must
act on rather than read, so do not bury it. If the gate could not be run, say so in place of
a verdict rather than leaving it unmentioned.
