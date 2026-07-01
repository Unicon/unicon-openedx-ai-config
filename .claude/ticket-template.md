# Ticket template

The canonical shape for a development ticket in this project. The `ticket-writer`
skill and the `business-analyst` and `software-architect` agents read this to review,
improve, and author tickets, whether tightening an existing one or drafting a new one.

Section ownership: the business-analyst owns Use Case, Description, Acceptance Criteria,
and the non-code parts of Context. The software-architect owns Technical Details, Files
to modify, and the code and prior-art parts of Context.

A ticket has seven sections, in this order.

The most important section is "Open questions". If it's not 100% certain what parts of this
ticket need to say exactly, just leave a "TBD". Add an open question to find out, and then later when the question
has been answered another iteration can fill in the gaps in the ticket.

## Use Case

A user story: who, what, why. "As a <role>, I want <capability>, so that <outcome>."
Name a real Open edX role (course author, library maintainer, learner, operator, plugin
developer), not "the user." The "so that" is the stakeholder's true intent; if you can't
state it, the ticket is not ready.

## Description

Prose context: the problem, the current behavior, the desired behavior, and what is
explicitly out of scope. One or two tight paragraphs. State assumptions and constraints,
and call out what this ticket does NOT do, to hold the scope line.

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
  working code. There is no Gherkin and no QA path."

## Technical Details

How to build it, at the design level: the recommended approach, the data model and
migrations, the public-API and contract impact, the layer it sits in (respect
`.importlinter`), performance and backward-compatibility notes, and the test strategy.
Note any ADR that is warranted. This is the software-architect's recommended approach,
not a code dump.

Close this section with an **Example Resolution Prompt** subsection: a self-contained
prompt a developer (or Claude Code) could use to implement the ticket. It must name the
specific files to touch, the models or functions to write or modify, and the key
constraints and invariants. No generic "implement this ticket" language — if a developer
pasted it cold into an AI assistant, they should get a correct first draft.

**Exception — design spike tickets:** Replace Technical Details and Files to create and
modify with a single **Context for the Designer** section. It covers: the current state
of the relevant UI or flow, the options under consideration (with tradeoffs), constraints
the design must respect, and links to related tickets and the current Figma file. The
software-architect's role on a design spike is scope judgment only (is this one ticket?
does it block anything?), not technical design.

## Context

What a developer should read before starting: relevant code files (with paths), prior
art and similar features, docs and ADRs, and related or blocking tickets. This is the
on-ramp; a good Context section saves the developer the discovery the analyst and
architect already did.

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



## What "awesome" looks like

- The Use Case names a real role and a real outcome; the "so that" is not hand-waved.
- Scope is bounded: the Description says what is out of scope.
- Every acceptance criterion is observable and could fail; unhappy paths are covered.
- Technical Details pick one approach and justify it, respecting the layering and
  contracts.
- Context and Files to modify are concrete, with real paths, so a developer can start
  cold.
- The whole thing is a 1-2 developer-day unit of work, or it is split and says so.
- It is SMART: Specific, Measurable, Achievable, Relevant, Time-bound.
- When a ticket has a hard dependency on an unresolved design decision, it exists as a
  stub only — title plus a one-sentence blocker note. The full ticket is written
  immediately after the blocking decision is documented, not before.
