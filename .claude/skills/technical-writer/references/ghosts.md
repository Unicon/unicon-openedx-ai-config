# Ghosts

A **ghost** is a concept or relationship that is required to understand a document as
intended, but that appears nowhere in it. It lives only in the author's head. The term and
the analysis are Russ Hodge's, from *Ghosts, models and meaning* (2018); what follows
translates it to software.

## Why this is the central problem, and not "undefined jargon"

A missing definition is a known unknown. The reader hits `promoter`, knows they do not know
it, and looks it up. Annoying, recoverable, and largely self-correcting.

A ghost is an unknown unknown. The reader hits a missing connection, does not notice it is
missing, silently supplies one, and reads on with a coherent story that is not your story.
Nothing in their experience flags a problem. They finish the document feeling they
understood it. Hodge's press-release example: readers conclude the paper is about
explaining some "unknown reasons," which was a throwaway aside, and miss the actual finding
entirely, while following every sentence.

In science that produces a misunderstanding. In software the reader goes on to implement,
review, or operate the thing, so it produces a bug, a bad review approval, or an outage.

**Ghosts are missing edges, not missing nodes.** Defining every term is necessary and
nowhere near sufficient. Most of what makes technical writing fail is unstated relations
between things that were each, individually, named just fine.

## Ghosts are not an audience-level problem

Every worked example in Hodge's essay involves experts. Two senior researchers discover
they have been using "robustness" to mean different things for years. A specialist paper's
description of a molecular assembly misleads specialists about assembly order. A published
journal article leaves trained biologists unable to say how many experimental groups it
used, after fifteen minutes on seven sentences.

So do not treat ghost removal as writing "for beginners." An expert reader carries *more*
models, which means more places where they will silently attach the wrong variant and never
check. What changes with audience is how much background and motivation you owe them. What
does not change is that the load-bearing relations have to be on the page.

See `craft.md`, "Grounding is not simplification."

## The taxonomy

Four families. Each entry gives the detection question and the fix.

### Ghosts of connection

| Ghost | Detect | Fix |
| --- | --- | --- |
| **Missing edge** | For each pair of consecutive sentences and paragraphs, can you name the connective the reader must supply? (`because`, `so`, `unlike`, `which is why`, `in contrast`) If they have to invent it, it is a ghost. | State the relation. One clause is usually enough. |
| **Unstated premise** | For every `therefore`, `so`, `cannot`, `is safe`, list the premises the conclusion needs. Is each one on the page? | Add the missing premise where the argument uses it, not in a preamble. |
| **Ghost of the question** | Can a reader say, from the document alone, what question it answers? Not what it is about. What question. | State the question. In an ADR that is the title and the first line of Context. |

The unstated-premise ghost is the most dangerous one in architecture writing, because the
argument still *reads* as valid. A deadlock-freedom argument that says "locks are taken
child before parent, so two updates always reach a shared ancestor in the same order" is
missing "every node has exactly one parent." Without that premise the conclusion does not
follow, and every reader who already knew the tree shape will nod along and never notice.

### Ghosts of vocabulary

| Ghost | Detect | Fix |
| --- | --- | --- |
| **Loaded name** | List every domain noun. For each, ask: what must the reader believe about this thing for my argument to hold? Is that belief stated? | State the belief the argument depends on, at the point it is used. |
| **Variant ambiguity** | Does the argument depend on one specific reading of a term that has several? | Name the variant. Not "atomic" but "atomic in the database-transaction sense: all four writes commit or none do." |
| **Precision definition doing a translation definition's job** | Could someone who does not already know this use your definition? Or does it only confirm knowledge they already had? | Give the working image first, the precise definition second if at all. |

**Loaded names** are Hodge's `NFkB`: a term that is not a pointer to a thing but a pointer
into a web of models. Software is full of them. `lock`, `transaction`, `event`,
`idempotent`, `cache`, `session`, `tenant`, `retry`, `async`, `consistent`, `signal`,
`grade`. Writing the word transmits the word. It does not transmit the model, and the
reader will supply one.

**Variant ambiguity** is Hodge's "robustness," where two experts held different, coherent,
incompatible models of one word and neither knew for years. Software equivalents:

| Term | Variants that will be silently assumed |
| --- | --- |
| atomic | DB transaction / single CPU instruction / "all-or-nothing" at an API boundary |
| consistent | ACID consistency / CAP consistency / eventual consistency / "not contradictory" |
| idempotent | `f(f(x)) == f(x)` / safe to retry / HTTP method semantics |
| lock | held for the statement / held to commit / advisory / application-level mutex |
| event | in-process signal / durable message / domain event / DB trigger |
| async | not on the request thread / non-blocking IO / eventually / in a separate transaction |

The test is not "is this term ambiguous in general." It is "does my argument break under
the other reading?" If yes, name the variant. If no, leave it alone; over-specifying every
term is its own noise.

**Precision versus translation definitions** is Hodge's membrane. Told a membrane is "a
lipid bilayer containing proteins and their aggregates, forming a barrier that breaks what
would otherwise be a gradient," he still could not follow a story about dragging a bead
through one. Told it is "more like two soap bubbles, one packed tightly inside the other,
more of a liquid that things float around in," he could. Both are true. Only one is usable.
His observation: "Scientists often define things in order to make things more precise,
rather than to translate them into more general terms. Anyone capable of understanding this
definition almost certainly already knows what a membrane is."

The soap-bubble image is not the dumbed-down version. It is the model the expert actually
runs in their head. The precision definition is a formalization nobody thinks in.

### Ghosts of structure

The reader's real task in a passage is often to build a structure: a sequence, a comparison
matrix, a spatial arrangement. The author has the structure. The prose does not announce
it. The reader has to reverse-engineer it and usually fails.

| Ghost | Detect | Fix |
| --- | --- | --- |
| **Hidden list** | Does the reader need to end up holding an ordered sequence? | Announce the shape before filling it: "recording happens in four steps." Then fill it, in order. |
| **Hidden table** | Are two or more dimensions being crossed? (strategies × properties, states × triggers, options × tradeoffs) | Render the table. Prose crossing two dimensions is a table that has been flattened and lost. |
| **Hidden diagram** | Does correctness depend on relative position, layering, containment, or topology? | Describe it explicitly in mechanism order, or draw it. |
| **Salience order** | Does the first entity you mention match the first entity in the actual mechanism? | Order by how the system works, not by what you find most interesting. |

Hodge's mouse-genetics paper is the canonical hidden table: students given fifteen minutes
on seven sentences of a published paper could not say how many groups of mice the lab bred,
which is central to the entire method. The authors, who had sorted those mice for fifty
generations, had no idea the sentences were confusing. The fix was one printed table.

**Salience order** is subtle and common. A researcher describing a three-protein assembly
put her own protein first because it was the focus of her work; the actual assembly order
put it second. Readers built the stack wrong. In software this is the ADR that opens with
the clever mechanism the author is proud of rather than with the sequence of events, or the
docstring that leads with the interesting edge case.

### Ghosts of scope

| Ghost | Detect | Fix |
| --- | --- | --- |
| **Silent quantifier or duration** | Every claim carrying an implicit *how long*, *how many*, *against what*, *under which conditions*. "The lock is held." "This is safe." "Grades are recomputed." | Say how long, how many, against what, under what assumption. |
| **Negative framing of a positive finding** | Is your actual result stated as the refutation of a model, rather than as a thing that is true? | State it positively. Refute only models the reader actually holds. |

**Silent duration** is the highest-yield check in concurrency, caching, transaction, and
lifecycle writing. "Takes a row lock" is not a claim until you say whether it is released at
the end of the statement or held to commit, and every ordering argument downstream depends
on which.

**Negative framing** needs care because it interacts with a real and well-supported
technique. Refutation text (state the wrong model, mark it wrong, then correct it) beats
plain exposition, but only against a misconception the reader actually holds. Hodge's press
release defines "promoter" by reference to a model the reader has never met and then
immediately retracts that model, which is pure noise. His fix is to state the finding as a
positive fact about the world.

So:

- Reader demonstrably holds the wrong model (a documented support question, a repeated
  review comment, a prior ADR this one supersedes): name it, mark it wrong, correct it.
- Reader has no model here: state the true thing positively. Do not teach by negation.
- Never invent a misconception to refute. A strawman gives the reader nothing to be
  dissatisfied with, which is the only mechanism that makes refutation work in the first
  place.

## The three causes of an unclear passage

When a passage will not come clean, Hodge finds it is always one of three things. The
triage matters more than the rewrite, because only the first two are writing problems.

1. **The writer does not have a clear idea of the concept and its relations.** Fix by going
   back to the source: read the code, the schema, the prior ADR. The prose was a symptom.

2. **The writer has not thought about what the reader knows.** Fix by building the reader's
   map (see `method.md`) and writing the difference.

3. **Nobody has a clear idea. The concept is genuinely unsettled, and the attempt to write
   it down has exposed a real open question.** Do not fix this with prose. Surface it.

The third case is the valuable one, and the reason writing is a design tool rather than a
packaging step. Hodge: "the process of writing and reflection can raise new scientific
questions that may have been hidden by our own ghosts." An ADR that resists clean
explanation is frequently reporting that a boundary is in the wrong place or a decision has
not actually been made. Smoothing the prose destroys that signal.

When you hit case 3, say so explicitly, as a named open question, and hand it to whoever
owns the design. Do not write around it.

## The acceptance test

Not "is this clear." Clarity is unfalsifiable and every author believes they have it.

**Can a reader who has only this document predict the system's behavior in a case the
document does not state?**

That is the test for whether you transmitted a model or transmitted words. Hodge's inner
laboratory: experts do not recall facts about a system, they run a simulation of it. A
document succeeds when the reader can run it too. It fails when the reader can recite it
and cannot run it.

Operationally: write two or three transfer questions before drafting, whose answers are
genuinely derivable but nowhere stated verbatim, and give them to the `naive-reader` agent
along with the draft. Their wrong answers are your ghosts, located precisely.
