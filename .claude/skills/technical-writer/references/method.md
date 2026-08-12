# Method: three maps and the diff between them

Ghosts are missing edges. You cannot see a missing edge in an outline or a bullet list,
because both are lists of nodes. You can see one in a graph. So the pre-writing artifact is
a graph, not an outline.

This is Joseph Novak's concept mapping, used the way Hodge uses it: map the subject, map
what the reader already has, and the document is the difference.

## The proposition format

Write maps as propositions, one relation per line:

```
<node> --[relation]--> <node>     [tag]
```

The relation label carries the meaning and is the part that must not be vague. `relates
to` and `is associated with` are not relations; they are ghosts wearing a label. Use verbs
that commit: `is held until`, `is computed from`, `blocks`, `is derived from`, `overwrites`,
`commits with`, `is triggered by`, `never lowers`.

Tag every proposition:

| Tag | Meaning |
| --- | --- |
| `verified` | Confirmed against source, with the anchor: `models.py:88`, `ADR-0002`, commit sha |
| `inferred` | Follows from verified facts, but is not written anywhere |
| `assumed` | Taken on faith. If wrong, something in the document is wrong |
| `unknown` | Genuinely undecided. A candidate open question, not a gap to paper over |

The tags are the guard against the one failure that matters most for an LLM writing
technical prose: fluency is independent of accuracy, so a fabricated relation reads exactly
like a verified one. Tagging forces the distinction before it can hide inside a
well-turned sentence. Anything still `assumed` or `unknown` at drafting time must appear in
the document as an explicit assumption or open question, never as a plain assertion.

A mermaid rendering next to the propositions is worth adding when the human will review the
map, since a graph is much faster to check visually. The propositions stay authoritative,
because they are what you check coverage against.

## Map 1: the subject map (what is true)

Build from source, not from memory. Read the code, the schema, the migrations, the prior
ADRs, the commit that introduced the thing. Every node and edge gets an anchor or a weaker
tag.

Stop when the map covers the acceptance questions plus one step beyond. Mapping the whole
subsystem is a failure of scope, not thoroughness.

The `unknown` edges you find here are often the most valuable output of the whole exercise.
Hodge's third cause of unclear writing is that the concept is genuinely unsettled; the map
is where that becomes visible, because you go to write down a relation and discover nobody
has decided what it is.

## Map 2: the reader map (what they already hold)

Do not guess this, and do not invent a persona out of thin air. Derive it from the
document's actual neighborhood, which is evidence rather than speculation:

- The documents this one references, and the ones that reference it. An ADR in a numbered
  series can assume its predecessors; that is what the series is for.
- The module's README, the repo's `CLAUDE.md`, the architecture overview.
- The layer the document sits in. A doc inside `openedx-core` can assume Django and DRF.
  It cannot assume anything about `edx-platform` internals, because that is the layer above.
- Whoever actually reads it: a reviewer of this ADR, an implementer of this ticket, an
  operator paged at 3am, a plugin author.

Where the neighborhood genuinely does not settle it, say so and pick, rather than
pretending to knowledge you do not have. An explicit "this assumes you have read ADR-0002"
is worth more than a paragraph of hedged background.

Then, for every shared term, record the **variant** the reader will attach, not just
whether they know the word. This is where most ghosts live. "The reader knows what a lock
is" is not a useful entry. "The reader knows what a row lock is and will default to
assuming statement duration" is.

## Map 3: the target map (what they should hold afterward)

The subject map, cut down to what the reader needs, plus the reader map as its base.

Cut rule: **keep every node and edge on a path to an acceptance question. Cut everything
else.** That is what makes conciseness principled rather than a matter of taste. You are
not cutting words you dislike; you are cutting nodes the reader's next decision does not
depend on.

Then apply the cut test to each removal: *what could a reader now get wrong that they could
not before?* Nothing means the cut was free. "They would assume this applies to the async
path too" means you cut a load-bearing scope qualifier and need it back.

Keep the cut list. It becomes the document's explicit "not covered here" note, which is the
mark of a writer who cut deliberately rather than one who ran out of material.

## The diff is the document

```
target map − reader map = the propositions this document must state
```

Every one of those propositions has to appear in the text. Hodge: "each link represents a
proposition or statement that needs to be stated in the story. This vastly simplifies my
efforts to reduce a sprawling piece of science into a reasonable number of statements; now
all I have to worry about is presenting them in an order that helps the reader build the
whole structure."

This buys three things that an outline does not:

- **Coverage is checkable.** Walk the diff. Point at the sentence carrying each
  proposition. An uncovered proposition is a ghost you can find before a reader does.
- **Conciseness is principled.** Anything in the draft carrying no proposition from the
  diff is either scaffolding that earns its place (an example, a transition, a signpost) or
  it is cut.
- **Order becomes a separate, solvable problem.** Once the set is fixed, the only remaining
  question is sequence.

## Ordering

Order by the reader's question queue, which is the same rule as Williams' old-before-new
one level up: **every paragraph should answer a question the previous paragraph raised.**

Two corollaries that catch most real ordering failures:

- **Mechanism order, not salience order.** Sequence by how the system works, not by what
  you find most interesting or worked hardest on. The most common violation is opening with
  the clever part.
- **Announce a structure before filling it.** If the reader has to end up with a list, a
  table, or a spatial arrangement, say what shape is coming before you start filling it in.
  Building the container and its contents simultaneously is what makes readers lose count.

## Coverage check before you hand it over

1. Every proposition in the diff maps to a specific sentence. Name the sentence.
2. Every sentence maps to a proposition in the diff, or is deliberate scaffolding.
3. No proposition tagged `assumed` or `unknown` appears in the text as a bare assertion.
4. Every `verified` claim's anchor still resolves.

Then run `naive-reader`. Its reconstructed map is a second, independent measurement of the
same thing, taken from the only vantage point that counts.
