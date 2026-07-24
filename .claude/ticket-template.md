# Ticket template

The canonical shape for a development ticket in this project. The `ticket-writer`
skill and the `business-analyst` and `software-architect` agents read this to review,
improve, and author tickets, whether tightening an existing one or drafting a new one.

Section ownership: the business-analyst owns Use Case, Description, Acceptance Criteria,
and the non-code parts of Context. The software-architect owns Technical Details, Files
to modify, and the code and prior-art parts of Context.

A ticket has six core sections, in this order, plus an optional Open Questions section
described below.

## Use Case

A user story: who, what, why. "As a <role>, I want <capability>, so that <outcome>."
Name a real Open edX role (course author, library maintainer, learner, operator, plugin
developer), not "the user." The "so that" is the stakeholder's true intent; if you can't
state it, the ticket is not ready.

## Description

Open with a single sentence stating the actual change, bottom line up front, so a reader
knows the shape of the work before any detail. Then give prose context: the problem, the
current behavior, the desired behavior, and what is explicitly out of scope. One or two
tight paragraphs. State assumptions and constraints,
and call out what this ticket does NOT do, to hold the scope line.

When the ticket modifies an existing UI flow or user-visible behavior, structure the
prose as two labeled subsections rather than a single block:

**Current behavior** — a numbered step-by-step walkthrough: the role to log in as, the
navigation path, and what is currently observable. Specific enough that someone
unfamiliar can reproduce the baseline without a live demo or a Slack thread.

**Requested change** — what is different after this ticket, and why the current state
is insufficient. State what is explicitly out of scope here.

## Acceptance Criteria

Gherkin-style scenarios (Given / When / Then), one per distinct behavior, including the
unhappy paths. Detailed, but treated as living: they evolve as understanding and
alignment change, so write them to be revised, not frozen. Each criterion must be
observable and testable. Cover the empty, error, and permission cases, not just the
happy path.

    Scenario: <short name>
      Given <precondition>
      When <action>
      Then <observable outcome>

**Format by ticket type:**

- *Frontend and full-stack tickets*: standard Gherkin applies. These are QA-testable.
  Cover the happy path, empty/error states, and permission/role cases. Include
  mobile/responsive behavior where the UI is expected to work on small screens.
- *Backend API–only tickets* (no UI, not reachable by QA tooling): Gherkin scenarios
  are appropriate but must be explicitly marked as Postman-verifiable. Open the section
  with: "These scenarios are verifiable via Postman." Each Then clause must name an
  observable response attribute (field name, value, status code), not a vague outcome.
- *Data model / migration tickets* (no API surface, no user-observable behavior): Gherkin
  is not applicable. Use a PR reviewer checklist instead — checkboxes that verify
  alignment with the relevant ADR (column names, index presence, FK constraints, history
  package applied to the correct models, seeded data, delete protections, etc.). Open the
  section with: "There is no manual QA path. Acceptance is determined by a PR reviewer
  verifying the following against [ADR name/link]."
- *Design spike / research tickets* (deliverable is artifacts and decisions, not code):
  Gherkin is not applicable. Use a delivery checklist — checkboxes for the artifacts the
  designer or researcher must produce (e.g., updated Figma, documented decision with
  rationale, notes for the dependent implementation ticket). Open the section with: "This
  is a design spike. The deliverable is design artifacts and documented decisions, not
  working code. There is no Gherkin and no QA path." Each item in the Open Questions
  section must be resolved and documented before this ticket can be closed; add a
  checklist item for each.

## Open Questions

*(Optional — omit when everything is settled. Required for design spike tickets, where
the questions are the decisions the designer must resolve and document.)*

An unordered list of questions the ticket author could not resolve at writing time. Each
entry is a crisp, answerable question with a note on who owns the answer (designer,
implementer, BA, architect). Blocking questions go first.

Answers are documented as comments on the issue; once all blocking questions are
resolved, update the Description or Acceptance Criteria to reflect the decision and
remove the question from this section.

## Technical Details

The recommended approach at the design level, written as pair-programming guidance a
junior engineer can evaluate for correctness: name the major pieces and what each is
responsible for and why, pin the required parts and how they fit, and leave exact
variables, code locations, and line-by-line choices to the implementer. Describe intent
and contract, not implementation.

Structure it as two parts (a data-only or migration ticket may fold them together):

- **Data Structures**: the signature of each major type or piece, with a terse note on
  what it and its fields are for. Favor the signatures over prose. Verify they do not
  conflict with the DB data model, but do not restate the schema; fold anything essential
  into a sentence.
- **Logic**: the flow and rules over those structures, with call order and data flow made
  unambiguous. When the ticket is one of a split, name what a companion ticket does where
  it touches this flow and mark it out of scope.

Keep it accurate, complete, and short: self-explanatory over explanatory, DRY. Note the
public-API and contract impact, the layer it sits in (respect `.importlinter`),
backward-compatibility and test strategy, and any ADR that is warranted. This is the
recommended approach, not a code dump.

State only the recommended approach here, not the rejected alternatives. A ticket is
instructions for a developer, not a design-review record; a list of options considered
and discarded is noise once the decision is made. Alternatives and their tradeoffs
belong in the architect's returned analysis (for the human synthesizing the ticket) and,
when the choice is architecturally significant enough to matter to future readers, in a
proposed-status ADR that this section links to.

Close this section with an **Example Resolution Prompt** subsection: a prompt a developer
(or Claude Code) could use to start implementing the ticket. Its job is to orient the
implementer toward the right approach, not to hand them a plan: state the goal, point at
Technical Details and the Acceptance Criteria as the source of truth, and name the scope,
the key constraints and invariants, where the relevant code lives, and how to verify. It
is **not** an implementation plan and is **not** where technical decisions are made: every
technical decision lives in Technical Details above, and the prompt lets the implementer
(human or AI) form its own plan to satisfy that design. The implementer has the whole
ticket in context, so the prompt references its sections rather than restating them. No
generic "implement this ticket" language; a developer pasting it into an AI assistant
should get it working on the right approach rather than a wrong one.

**Exception — design spike tickets:** Replace Technical Details and Files to create and
modify with a single **Context for the Designer** section. It covers: the current state
of the relevant UI or flow, the options under consideration (with tradeoffs), constraints
the design must respect, and links to related tickets and the current Figma file. The
software-architect's role on a design spike is scope judgment only (is this one ticket?
does it block anything?), not technical design. The Open Questions section is required
on design spikes — it lists the decisions the designer must resolve and document as part
of closing the ticket.

## Context

What a developer should read before starting: relevant code files (with paths), prior
art and similar features, docs and ADRs, and related or blocking tickets. Reference files
and functions by path and name, not by line number: line numbers rot on the next change
and read as false precision. This is the on-ramp; a good Context section saves the
developer the discovery the analyst and architect already did.

## Files to create and modify

Two tables: one for new files, one for files being modified. Both are the architect's
map and must match the Technical Details and the import layering. Omit a table if it
is empty.

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

## Splitting into companion tickets

When a piece of work spans repos or layers (for example, a backend contract in this
repo plus a passthrough or consumption change in `openedx-platform` or a frontend repo),
split it into one ticket per repo/layer rather than one ticket with mixed scope. Pick one
ticket to hold the full shared context — usually the one that defines the contract the
others depend on — and keep the rest sparse:

- A companion ticket restates only what is specific to its own repo or layer: its own
  Use Case framing if genuinely different, its own Description of current/requested
  behavior in its own codebase, its own Files to modify.
- Background, rationale, resolved open questions, and Acceptance Criteria that verify the
  same underlying contract should be referenced by ticket number ("see #618") rather than
  copied. Restate only where the companion's scenario is genuinely different (a different
  endpoint, a different response shape) — don't duplicate identical scenarios verbatim.
- Every companion ticket's Context section links back to the ticket holding the shared
  context and to any sibling companions, so a developer starting from any one of them can
  find the rest.
- A companion ticket is still a complete, standalone unit of work: a developer picking it
  up must be able to tell what to build and how to verify it without reading the parent
  ticket's day-to-day discussion, only its resolved contract.

## What "awesome" looks like

- The Use Case names a real role and a real outcome; the "so that" is not hand-waved.
- The change is stated up front: a reader learns the shape of the work in the first
  sentence, not after three paragraphs.
- Scope is bounded: the Description says what is out of scope.
- Each rule or invariant appears once, in its canonical section. The same constraint
  restated across Description, Out of scope, Files, and Technical Details drifts into
  contradiction the moment one copy is edited.
- Every acceptance criterion is observable and could fail; unhappy paths are covered.
- Technical Details read as pair-programming guidance a junior can evaluate: one approach
  at intent altitude, Data Structures then Logic, short and DRY, respecting the layering
  and contracts.
- Every technical decision lives in Technical Details; the Files table and the Example
  Resolution Prompt reference the approach but are not where a decision is made.
- The Example Resolution Prompt orients the implementer toward the right approach and lets
  them plan; it is not a file-by-file implementation plan.
- Context and Files to modify are concrete, with real paths, so a developer can start
  cold.
- The whole thing is a 1-2 developer-day unit of work, or it is split and says so.
- It is SMART: Specific, Measurable, Achievable, Relevant, Time-bound.
- When a ticket has a hard dependency on an unresolved design decision, it exists as a
  stub only — title plus a one-sentence blocker note. The full ticket is written
  immediately after the blocking decision is documented, not before.
