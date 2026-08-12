# Craft

Sentence and paragraph mechanics. This is the last pass, not the first. Line-editing a
document whose target map is wrong is polishing the wrong object.

## Grounding is not simplification

Writing so that a junior engineer can follow it makes the document better for architects
too. This is not a concession to the weakest reader, and the two moves are often confused:

| Simplification (do not) | Grounding (do) |
| --- | --- |
| Omit a constraint because it is fiddly | State the constraint, plainly |
| Round off a claim until it stops being true | Keep the claim exact, drop the ornament around it |
| Replace the real mechanism with a friendly story | Give the working image the expert actually runs, then the precise mechanism |
| Explain less because the reader is senior | Explain the same, with less background and less motivation |

What changes with audience is **how much background and how much motivation you owe**, not
how clearly the mechanism is stated. A senior reader needs less setup for why the problem
matters. They need exactly as much precision about which variant of "lock" is in play, and
they are *more* likely to attach a confident wrong variant, because they carry more models.

Every worked example in Hodge's essay is a case of experts failing to communicate with
experts. Ghosts are not a novice problem.

The corollary for terms and abbreviations: writing `READ COMMITTED` and moving on transmits
the token. A reader who knows the term still has to stop, retrieve the model, and check
which property of it your argument uses. Naming the property you depend on ("under `READ
COMMITTED`, each statement sees the latest committed rows rather than a snapshot fixed
earlier in the transaction, which is what the sibling reads rely on") costs one clause and
removes the work for everyone, expert included.

## Sentence mechanics

The convergent rules, where four independent authorities agree (Williams, Gopen & Swan,
Pinker, Garner). Each is checkable.

| Check | Test |
| --- | --- |
| Real actor as subject, real action as main verb | Abstract subject plus a form of *be* usually means the action is frozen in a noun. `The determination of X is performed by Y` → `Y determines X` |
| New information at the end | The last clause of a sentence should carry its point. If the tail is throwaway, restructure |
| Sentence opens with what the reader already has | The first noun phrase should be a term from the previous sentence or an established topic, never a brand-new one |
| Subject next to its verb | Count intervening words. A long parenthetical between subject and verb reads as an interruption and demotes what it contains |
| One topic string per paragraph | List the grammatical subject of each sentence. They should cluster on a small set of the same referents |
| No stacked negatives | Two or more negations in a clause forces the reader to do algebra. Rewrite positive |
| Cut what carries nothing | Bracket the phrase, delete it, check whether the meaning survives |

## "Avoid passive voice" is three different rules, and one of them is wrong

Pullum showed that of Strunk & White's own four examples of the flaw, only one is actually
passive. The label conflates three unrelated problems, and an agent given "avoid passive"
will hunt for `was`/`were` and mangle correct sentences. Split it:

1. **True agentive passive hiding the actor.** `The row is locked.` By what? Fix by naming
   the actor, but only if the actor matters here.
2. **Existential burying the subject.** `There is a lock taken on the parent row.` Fix by
   promoting the real subject: `Recomputing a parent takes a row lock.`
3. **Weak copula standing in for a real verb.** `The status is a reflection of...` Fix by
   finding the verb: `The status reflects...`

And the passive is often correct. Gopen & Swan: voice is a topic-position decision, not a
grammar-purity one. If the passive's subject is the established topic and the agent is the
new information, the passive is the right sentence. `Pollen is dispersed by bees` is correct
when the paragraph is about pollen.

## Metadiscourse: cut the reflexive kind, keep the functional kind

Classic style says strip signposting. Technical documentation needs some of it. The test is
whether removing the phrase removes information the reader needs in order to navigate or to
calibrate trust.

| Cut | Keep |
| --- | --- |
| `It is interesting to note that` | `This assumes READ COMMITTED` |
| `As we will see` | `Not covered here: the async path` |
| `Needless to say` | `Confirmed against the schema as of <sha>` |
| `In this section I will discuss` | `If you have not read ADR-0002, start there` |

## Banned words

`simply`, `just`, `obviously`, `of course`, `easy`, `easily`, `clearly`, `trivially`,
`merely`.

Every one of them makes a claim about the reader's experience that the writer cannot check,
and each is doing the work a real explanation should be doing. The exception is when the
word marks a genuine contrast you have already earned: after showing a Rube Goldberg
version, "simply loop over the values directly" is fine, because the reader has seen the
alternative and can verify the comparison.

## Date what will rot

Any claim about a version, a default, a capability, or a state of the world gets a marker
inline: `as of Django 5.0`, `Django's MySQL default, which the platform does not override`,
`confirmed at <sha>`. Not in a changelog. In the prose, where a reader five years from now
will see it.

Line numbers are the opposite: never cite them. They rot on the next merge and read as
false precision. Name files and symbols; the reader navigates.

## Concision: three kinds, only one of them good

| Kind | What got cut | Result |
| --- | --- | --- |
| Compressed | Connective tissue: transitions, the `because`, the intermediate step | Denser, harder. The reader reconstructs your reasoning |
| Lossy | A load-bearing fact or scope qualifier | The reader is confidently wrong. Worst outcome |
| Good | Anything the reader's next decision does not depend on | Signal rises. Easier, not harder |

The test after every cut: **what could a reader now get wrong that they could not before?**
Nothing means the cut was free.

Note the trap: compression looks like good concision on every word-level metric. A
paragraph with the `because` clauses removed is shorter, has fewer hedges, scores better on
every readability formula, and is worse. Length is not the variable. What the reader can
still derive is.

## Readability scores

Do not use Flesch-Kincaid or any grade-level metric as a gate. Built and validated on
children's texts, conflates short with familiar, trivially gamed by chopping sentences, and
silent on accuracy, structure, and whether the document answers the reader's question.

Use cohesion checks instead: are pronouns and referents traceable without backtracking, are
causal and contrastive relations marked explicitly rather than left implied, is necessary
jargon grounded rather than merely used.

## House style

From `CLAUDE.md`, and it applies to everything this skill produces:

- Direct, engineer to engineer. No marketing tone, filler, or AI-slop openers.
- Avoid em dashes. Use commas, colons, or periods.
- US spelling. Inclusive terms.
- Bold sparingly.
- Write the current state, not its history. History lives in `git log`.
- Comment why, not what. No change narration.
- Public functions, classes, and models get RST docstrings describing the contract, not the
  implementation.
