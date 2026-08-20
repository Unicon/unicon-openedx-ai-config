# Ticket template

The canonical shape for a development ticket in this project. The `ticket-writer`
skill and the `business-analyst` and `software-architect` agents read this to review,
improve, and author tickets, whether tightening an existing one or drafting a new one.

**The User Story and Acceptance Criteria are the ticket.** Technical Details always
accompanies them, as required supporting background. Description, Files, and Context
exist to support the ticket further, not to duplicate it. Say each fact once, in its
canonical section.

**Three sections are collapsible: Technical Details, Files to create and modify, and
Context.** Each is wrapped in its own GitHub Markdown `<details>` block, so a reader who
only needs the User Story and Acceptance Criteria isn't confronted with any of them,
while a developer (or an AI implementer) expands the ones they need. Everything else —
User Story, Acceptance Criteria, Description, Open Questions — stays open on the page.

Section ownership: the business-analyst owns User Story, Acceptance Criteria, the
optional Description, and Open Questions raised from a requirements angle. The
software-architect owns Technical Details, Files to create and modify, the optional
Context, and Open Questions raised from a design angle.

Reference other work by **GitHub issue number only** (e.g. "see #618"). Never reference
internal ticket IDs, spreadsheets, or any tracker a reader outside the team can't open.
Don't mention target releases or roadmap timing anywhere in the ticket — that's tracked
elsewhere.

A ticket has three required sections, in this order, plus three optional ones used only
when they earn their place:

1. **User Story** (required)
2. **Acceptance Criteria** (required)
3. Description (optional)
4. **Technical Details** (required — collapsible)
5. Files to create and modify (optional — collapsible)
6. Context (optional, rare — collapsible)
7. Open Questions (optional, always last)

## 1. User Story

One sentence, the desired outcome stated directly:

    As a <role>, I want <capability>, in order to <outcome>.

Name a real Open edX role (course author, library maintainer, learner, operator, plugin
developer), not "the user." The "in order to" is the stakeholder's true intent — if you
can't state it, the ticket is not ready. This is the first thing a reader sees; don't
bury it under context or preamble.

**When a ticket genuinely covers more than one user story** (rare — most tickets have
exactly one), don't force it into a single sentence. Use a short bulleted list instead,
each bullet in plain English stating what the ticket covers, keeping the "as &lt;role&gt;,
I want &lt;capability&gt;, in order to &lt;outcome&gt;" shape where it fits naturally.
This is the exception; reach for it only when the work truly serves distinct stories, not
as a way to avoid picking one clear outcome.

## 2. Acceptance Criteria

Gherkin scenarios only — Given / When / Then — one per distinct, observable behavior,
including the unhappy paths. No technical criteria: no field names, status codes, schema
details, or implementation checkpoints here. If a scenario can't be stated as behavior
someone (or some caller) can observe, it belongs in Technical Details, not here.

    Scenario: <short name>
      Given <precondition>
      When <action>
      Then <observable outcome>

This applies to every ticket type, including backend and data-model tickets that have no
UI. Phrase the outcome in terms of what the caller, the system, or a downstream reader
observes — a returned result, a state change, a query outcome — not the mechanism
underneath. Cover the empty, error, and permission cases, not just the happy path.
Include mobile/responsive behavior where the UI is expected to work on small screens.

Treat these as living: they evolve as understanding changes, so write them to be
revised, not frozen. Each one must be observable and testable — able to fail.

**Exception — design spike / research tickets** (deliverable is artifacts and decisions,
not code): Gherkin doesn't apply because there's no runtime behavior yet. Use a delivery
checklist instead — checkboxes for the artifacts to produce (e.g., updated Figma, a
documented decision with rationale, notes for the dependent implementation ticket). Open
with: "This is a design spike. The deliverable is design artifacts and documented
decisions, not working code." Every item in Open Questions needs a matching checklist
item, since resolving and documenting them is the deliverable.

## 3. Description (optional)

Include only if there's something critical a reader needs beyond the User Story and
Acceptance Criteria — essential background, a constraint, a fact that would otherwise
confuse the ticket. A few terse sentences, not paragraphs. If there's nothing that meets
that bar, omit the section entirely.

Never include here:

- Implementation or technical detail — that's Technical Details.
- Why this ticket is blocked, or why it wasn't split or merged with another — that's a
  meta-fact about the ticket's status, not about the work. Note a real dependency, if one
  exists, in Context or Open Questions, referencing the other work by GitHub issue number.
- Release or version timing.

If a Description exists, it goes here, below Acceptance Criteria — not above the User
Story or Acceptance Criteria.

## 4. Technical Details (required)

**Every ticket includes this section.** It is not optional — even a small ticket gets a
few bullets naming the real approach. Being required doesn't mean being long: keep it
exactly as concise and non-redundant as an optional section would be, it just always
shows up.

**This section is background information and a suggested approach — not the source of
truth.** The User Story and Acceptance Criteria define what must be true when the work
is done; Technical Details exists to save the implementer some thinking, not to bind
them. Say so with an opening sentence before the content.

**Wrap the whole section in a GitHub Markdown collapsible block**, per the collapsible
rule above:

    <details>
    <summary>Technical Details</summary>

    ...content as described below...

    </details>

Keep a blank line after the `<summary>` line and before the closing `</details>`, or
GitHub renders the Markdown inside as literal text. The section's own `##` heading is
replaced by the `<summary>` line; don't write both.

State it as facts, not explanation. No prose paragraphs walking through the reasoning —
short bullets, one requirement or decision per line. Keep every real technical
requirement (don't drop information to make it shorter), just don't narrate it. Don't let
being required become an excuse to pad it — a one-line Data Structures bullet and a
two-line Logic list is a complete Technical Details section when the work is that small.

Structure it in two parts (fold together for a data-only or migration ticket):

- **Data Structures** — one bullet per major type or piece: its signature and a
  terse note on what it's for. Don't restate the DB schema; fold anything essential
  into the bullet.
- **Logic** — one bullet per rule or step in the flow, in order. Name companion-ticket
  work that touches this flow and mark it out of scope, referencing the companion by
  GitHub issue number.

Also fold in, as bullets, wherever relevant: public-API/contract impact, the layer or
app it sits in (respecting `.importlinter`), backward-compatibility notes, test
strategy, and a link to a warranted ADR.

State only the recommended approach — not the alternatives considered and rejected.
Those belong in the architect's returned analysis for the human synthesizing the ticket,
and, when the choice is architecturally significant, in a proposed-status ADR that this
section links to.

Do not add an Example Resolution Prompt or any closing "how to implement this" prompt.
The User Story, Acceptance Criteria, and the facts above are what an implementer —
human or AI — needs; a separate prompt only restates them.

**Exception — design spike tickets:** this is the one case where Technical Details is
not required. Replace it and Files to create and modify with a single **Context for the
Designer** section: the current state of the relevant UI or flow, the options under
consideration with tradeoffs, constraints the design must respect, and links to related
tickets (by GitHub issue number) and the current Figma file. That section is the body of a
spike ticket, so leave it open rather than collapsing it. The software-architect's
role on a spike is scope judgment only — is this one ticket, does it block anything —
not technical design.

## 5. Files to create and modify (optional)

Two tables, one for new files and one for modified files. Both are the architect's map
and must match Technical Details and the import layering. Keep each row to one line.
Omit a table if it's empty; omit the whole section if there's nothing to name yet.

Wrap the section in its own collapsible block, the same way Technical Details is wrapped:

    <details>
    <summary>Files to create and modify</summary>

    ...the two tables...

    </details>

**New files**

    | File | Purpose |
    | --- | --- |
    | src/openedx_learning/applets/cbe/models.py | CompetencyTaxonomy and related models |
    | src/openedx_learning/applets/cbe/migrations/0001_initial.py | schema migration |

**Modified files**

    | File | Nature of modification |
    | --- | --- |
    | src/openedx_tagging/rest_api/v1/serializers.py | add taxonomy_type SerializerMethodField |
    | src/openedx_tagging/rest_api/v1/views.py | add select_related to get_queryset |

## 6. Context (optional, rare)

Omit unless there's something a developer genuinely needs before starting that isn't
already covered above: a prior-art file, an ADR, or a related/blocking ticket. When
included, it's a bullet list — file paths and names (never line numbers, they rot), ADR
links, and GitHub issue numbers — not prose. A good Context section is short because the
User Story, AC, and Technical Details already carry the substance.

Wrap it in its own collapsible block too:

    <details>
    <summary>Context</summary>

    ...the bullet list...

    </details>

## 7. Open Questions (optional, always last)

Omit when everything is settled. Required for design spike tickets, where the questions
are the decisions the designer must resolve and document.

An unordered list of questions the ticket author could not resolve at writing time. Each
entry is a crisp, answerable question with a note on who owns the answer (designer,
implementer, BA, architect). Blocking questions go first. Reference any related ticket by
GitHub issue number.

Answers are documented as comments on the issue; once a blocking question is resolved,
update the Acceptance Criteria (or Description, if that's where it matters) to reflect
the decision and remove the question from this section.

## Splitting into companion tickets

When a piece of work spans repos or layers (for example, a backend contract in this
repo plus a passthrough or consumption change in `openedx-platform` or a frontend repo),
split it into one ticket per repo/layer rather than one ticket with mixed scope. Pick one
ticket to hold the full shared context — usually the one that defines the contract the
others depend on — and keep the rest sparse:

- A companion ticket restates only what is specific to its own repo or layer: its own
  User Story framing if genuinely different, its own Files to modify.
- Background, rationale, resolved open questions, and Acceptance Criteria that verify the
  same underlying contract are referenced by GitHub issue number ("see #618") rather than
  copied. Restate only where the companion's scenario is genuinely different (a different
  endpoint, a different response shape) — don't duplicate identical scenarios verbatim.
- Every companion ticket's Context section links back to the ticket holding the shared
  context and to any sibling companions by issue number, so a developer starting from any
  one of them can find the rest.
- A companion ticket is still a complete, standalone unit of work: a developer picking it
  up must be able to tell what to build and how to verify it without reading the parent
  ticket's day-to-day discussion, only its resolved contract.
- Don't explain, in any companion ticket, why the work was split this way — that's a
  process fact for the people who did the splitting, not part of the work itself.

## What "awesome" looks like

- The User Story states a real role and outcome directly, in one sentence, up front —
  or, for the rare ticket covering more than one story, a short plain-English bulleted
  list instead of a forced single sentence.
- Acceptance Criteria are pure Given/When/Then, observable, and could each fail —
  including for backend and data-model tickets with no UI.
- There's no Description at all unless it earns its place; when present, it's a few
  sentences of essential context, nothing technical, and it sits below Acceptance
  Criteria.
- Technical Details is always present, opens by saying it's background and a suggestion,
  then reads as short facts — signatures and bullets — never a paragraph explaining
  itself, and never padded just to look complete.
- Technical Details, Files to create and modify, and Context are each in their own
  `<details>` block, so the page a reader lands on is the User Story, the Acceptance
  Criteria, and three collapsed summaries.
- Each rule or invariant appears once, in its one canonical section. The same constraint
  restated across Description, Technical Details, and Files drifts into contradiction the
  moment one copy is edited.
- There's no Example Resolution Prompt and no other closing implementation-plan prompt.
- Context and Files, when present, are concrete — real paths, real GitHub issue numbers
  — and short, because the substance already lives in the sections above, and each is
  collapsed behind its own summary.
- Nothing in the ticket references an internal ticket ID, a spreadsheet, or a release
  date.
- The whole thing is a 1-2 developer-day unit of work, or it is split and says so via
  companion tickets.
- It is SMART: Specific, Measurable, Achievable, Relevant, Time-bound.
- When a ticket has a hard dependency on an unresolved design decision, it exists as a
  stub only — title plus a one-sentence blocker note. The full ticket is written
  immediately after the blocking decision is documented, not before.
