# Genres

Pick the document's shape before writing a sentence. Genre fixes voice, density, what
counts as in scope, and which conventions apply. Getting it wrong makes every later
decision wrong, and it is the cheapest thing to settle.

## The four Diátaxis quadrants

|  | Acquisition (study) | Application (work) |
| --- | --- | --- |
| **Action** (doing) | Tutorial | How-to guide |
| **Cognition** (thinking) | Explanation | Reference |

| Quadrant | Serves | Voice | Hard rule |
| --- | --- | --- | --- |
| Tutorial | A learner acquiring a skill | "In this tutorial, we will..." plus imperatives | Must work every time. No digressions, no explanation |
| How-to | A competent user with a goal | "To achieve X, do Y." Conditional imperative | Action only. No teaching |
| Reference | A user who needs certainty | Neutral, austere, factual | Describe. Do not instruct, discuss, or opine |
| Explanation | A user who wants to understand | Discursive. Causal, comparative, weighing alternatives | Takes the wide view. Not tied to a task |

The failure mode named throughout Diátaxis is mixing quadrants in one document: a how-to
that stops to teach, a reference that starts recommending. Each half then serves neither
reader.

ADRs and design docs are Explanation. That is why rationale is their product and why
"describe the mechanism" is not enough on its own.

## ADRs

**Write ADRs short. One numbered bullet per decision, and no more than about six.** This is
the strongest shape rule in this file, because ADR drafts fail far more often by sprawl than
by omission. An author who skims their own ADR has already lost, and length is what makes
them skim.

The target: a decision list a reviewer reads once, top to bottom, without skipping.
Concretely, 60 to 100 lines for a design of this size, in these sections:

| Section | Shape |
| --- | --- |
| Context | One short paragraph. The forces and the vocabulary the decisions need, nothing else |
| Decision | Numbered bullets, one per decision. Bold lead sentence states it; the rest earns its place or goes |
| Unresolved | One line each. Name the hole, do not explore it |
| Rejected Alternatives | The alternative, its real advantage, and why it lost. A few lines each |

Consequences are not optional; only their placement is. Add the section whenever the decision
has costs, risks, or follow-on obligations worth recording, and give it the same terse treatment
as the rest. Where it goes is a local convention: this repo's existing ADRs tend to fold
consequences into the decision bullets and Rejected Alternatives, so match the neighbors if they
fit, and add the section when they do not. Never drop a cost to fit a shape. A cost is precisely
what a reader cannot infer, so it survives the cut every time.

**Length per bullet tracks inferential distance, not importance.** A decision the reader can
take in from its own statement gets one sentence and stops. A decision whose conclusion the
reader cannot reach unaided keeps every step it needs, even if that runs to a paragraph. Do
not even out the bullets. Uneven length is the shape working correctly.

Two habits do most of the damage, and both feel like diligence:

- **Explaining a term the reader already holds.** "In the same atomic transaction" is
  finished. Adding "so the two can never end up disagreeing" restates what `atomic` means to
  anyone who knows the word, and your reader map said they do. Use the term and move on.
- **Narrating a consequence the reader will draw anyway.** After "each write stores the higher
  of the two values", a reader gets that replaying an event changes nothing. One instance is
  enough; do not also supply the general case, and do not spell out what it saves you from.

The test for every sentence after the first in a bullet: **delete it, and ask whether the
reader would now reach a different conclusion, or merely take a second longer to reach the
same one.** Only the first justifies keeping it. "It makes the point easier" does not.

Nygard's structure, which this repo uses, plus what actually separates a good one:

| Section | What belongs |
| --- | --- |
| Title | A question or a short noun phrase naming the decision |
| Status | Proposed / Accepted / Deprecated / Superseded by <n> |
| Context | The **forces**: constraints, competing priorities, what makes this hard. Value-neutral |
| Decision | Committed, active voice. "We will..." |
| Consequences | All of them. The bad ones especially |

Four things distinguish a good ADR from a bad one, and every source agrees on all four:

1. **Context states forces, not background.** Background says what happened. Forces say why
   the decision was rational. Only forces stop a future reader relitigating it without new
   information.
2. **Consequences include the costs.** Omitting the downsides is the single most commonly
   cited ADR failure. If the Consequences section is entirely upside, it is not finished.
3. **Rejected alternatives carry real pros.** An alternative with only cons was never
   considered; it was staged. If you cannot write a genuine advantage for it, either find
   one or drop the alternative.
4. **Accepted ADRs are immutable.** Typos and link rot can be fixed. Substance changes
   through a new, superseding ADR. This is the one rule with zero disagreement across
   Nygard, MADR, AWS, adr.github.io, and the Open edX OEP process.

The ghost that haunts ADRs specifically: **the argument's premises.** An ADR is a chain of
reasoning, so it fails through unstated premises more than through anything else. For every
"therefore," "so," "cannot," and "is safe," list what the conclusion needs and check each
one is on the page. See `ghosts.md`, ghosts of connection.

Open edX ADRs go in `docs/<package>/decisions/`, reStructuredText, cross-referenced with
`:ref:` labels. A doc-only change still needs a real doc build, not visual inspection.

## Design docs

Google's framing: the value is the trade-off analysis, not the implementation instructions.
Sections: Context and Scope, Goals and Non-Goals, the Design, Alternatives Considered,
Cross-Cutting Concerns.

Non-goals are plausible objectives deliberately deprioritized, not negated goals. "Should
not crash" is not a non-goal. "Does not handle multi-region" is.

Skip the design doc entirely when the solution is unambiguous. A document that only says
how you will implement something has no long-term value.

## Code comments and docstrings

Ousterhout's rule is more precise than the "why not what" slogan, and the slogan loses the
useful half. Comments must add information **at a different level of detail than the code**:

- **Lower level than the code**: precision the syntax cannot carry. Units, bounds,
  invariants, what null means here, which lock is assumed held.
- **Higher level than the code**: intuition, rationale, the abstraction the reader should
  hold instead of the line-by-line.
- **Same level as the code**: pure restatement. This is the actual defect. `# increment i`.

So a docstring describing *what* a method does, at the contract level, is exactly right,
even though a naive reading of "why not what" forbids it. What is forbidden is narrating
the implementation the reader can already see.

Interface comments must let a caller use the abstraction without reading the body. If an
interface comment cannot make sense without leaking implementation detail, that is evidence
about the abstraction, not about the comment.

Measured non-information to delete on sight: `Gets the value of X` on a method named
`getX`. Grammatically complete, conveys nothing.

Never narrate a change. No "updated to handle...", "as requested", "was previously". Write
the current state; history lives in `git log`. Stale comments are bugs: update or delete
them in the same change.

## PR descriptions

Give the reviewer three things before the diff: the scope of the change, the reasoning
behind it, and which technical decisions actually mattered. Narrate the decisions, not the
diff; the diff is right there. State what was tested, specifically.

## Commit messages

Conventional Commits, enforced here by `commitlint`. Type prefix, imperative subject under
72 characters, blank line, body wrapped at 72. Body explains why, not what.

## DRY does not apply to prose

Write the Docs calls this ARID: Accept (some) Repetition In Documentation. A how-to and its
reference page will legitimately state the same fact, because they serve readers in
different situations who will not read both.

The distinction that matters: **repeating a fact for a different reader is fine. Stating a
decision in two places is not**, because the copies drift and become contradictions. One
canonical home per decision; other places reference it.

## Voice by genre, resolved

Google's style guide says use "you," never "we." Diátaxis mandates "we" in tutorials. Both
are right inside their genre. Set voice from the quadrant first, then apply phrasing rules
within it. Do not average the two.

Same for structure: Amazon bans bullets to force narrative rigor; Google design docs and
RFC templates are section-structured by design. Follow this repo's existing convention
rather than splitting the difference. Look at the neighboring documents.
