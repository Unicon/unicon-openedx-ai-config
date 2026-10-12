# Ticket template

The canonical shape for a development ticket in this project. The `ticket-writer` skill,
the `clean-up-ticket` skill, and the `business-analyst` and `software-architect` agents
read this to draft, review, and improve tickets.

## Who writes what

Axim asked that the parts of a ticket that frame the work be written by a person, not an
LLM, and that everything an LLM drafts be audited by a person before the ticket is posted.
So a ticket has two kinds of sections:

| Section | Written by | Claude's role |
| --- | --- | --- |
| Title | Human | Preserve verbatim |
| User Story | Human | Preserve verbatim |
| Description | Human | Preserve verbatim |
| Context | Human | Preserve verbatim |
| UX Design (frontend tickets only) | Claude adds the placeholder, the designer fills it in | Add the placeholder |
| Acceptance Criteria | Claude drafts, a human audits | Draft |
| Technical Details | Claude drafts, a human audits | Draft |
| Open Questions | Either, rarely | Only for what is genuinely the implementer's to decide |

**Claude never edits the title or the human-written sections**, and neither does any
cleanup pass. In a cache file the title is the `#` line at the top.
That covers wording, formatting, and order within the section. If Claude thinks one of
them has a problem (a missing "in order to", a Context bullet that contradicts the code,
a Description that promises more than the AC cover), it reports that in chat to the person
running the session, who decides whether to change it. Claude never writes those concerns
into the ticket file.

When a human-written section is missing, Claude asks the human for it rather than
drafting it. The one exception is the design spike shape below.

## How a ticket moves from draft to GitHub

The cache file under `.claude/github-issues/<workstream>/<epic>/` passes between the human
architect and the human BA through git. The `ticket-writer` skill covers each step:

1. The architect has Claude scaffold empty User Story, Description, Context, and
   `## Notes for drafting` headings into the cache file, then writes the title (replacing
   any placeholder title) and those sections. The
   notes hold anything the BA and Claude should know that doesn't belong in the posted
   ticket: hunches about the approach, related code, edge cases to cover.
2. The architect runs a pre-handoff check. Claude flags problems in the human-written
   sections and asks the architect every question it can foresee, so that the answers are
   in the file before the BA starts. Then the architect pushes the file to the BA.
3. The BA runs the draft pass with Claude, which drafts the Acceptance Criteria, Technical
   Details, and the UX Design placeholder, then pushes the file back.
4. The architect does a final review: the same audit the BA did, plus a list of questions
   and concerns for Claude, if any. The architect resolves any questions left for them and
   pushes the file back to the BA.
5. The BA runs a pre-post check and posts the ticket to GitHub.

The `## Notes for drafting` section is removed before the ticket is posted. Anything in it
that a reader of the posted ticket needs ends up in the AC or in Technical Details, or, if
the architect chooses, in the Context.

## Order

1. **User Story** (human, required)
2. **Description** (human, required)
3. **Context** (human, optional)
4. **UX Design** (required on frontend tickets, omitted otherwise)
5. **Acceptance Criteria** (required)
6. **Technical Details** (required, collapsible)
7. Open Questions (optional, always last)

Only Technical Details is collapsed. Everything else stays open on the page.

Reference other work by **GitHub issue number only** (e.g. "see #618"), found in its cache filename after ghi-. Only reference by Use Case IDs (ucid) only when that ticket's file says ghi-pending, and replace it once a number exists. Never use spreadsheet IDs or any tracker a reader outside the team can't open. Don't mention target releases or roadmap timing anywhere in the ticket.

Say "archived", never "retired", for a taxonomy, tag, criterion, rule profile, or anything else taken out of use, because archived is the lifecycle term the code and ADRs use. The same goes for "archive" and "archiving" in place of "retire" and "retirement". The one exception is Open edX user account retirement, the platform's account-deletion pipeline, which keeps its own name.

## 1. User Story (human)

Why the user cares, in one sentence:

    As a <role>, I want <capability>, in order to <outcome>.

Example: "As a platform admin, I want to see the instance's default rule profile, in
order to know which rules apply to courses that don't set their own." A ticket that
genuinely serves more than one story can use a short bulleted list instead.

## 2. Description (human)

What developers need to do, in brief. One to three plain sentences. Example: "We need to
build a GET endpoint that returns the instance-wide rule profile."

## 3. Context (human, optional)

What else developers should know right now: a blocking PR, a related issue, a PR that
partially implements this, a relevant ADR. A short bullet list, referencing work by GitHub
issue or PR number. Context that Claude thinks is worth flagging goes in the Additional
context part of Technical Details, not here.

## 4. UX Design (frontend tickets only)

Every ticket that changes a user interface (an MFE, Studio, the LMS) gets this section,
exactly as written below, so the designer knows to attach the design after the ticket is
posted. Omit it on backend-only tickets.

    ## UX Design

    @illiphilli, please add the UX design screenshot(s) and the Figma link for this ticket.

    - Figma: TBD
    - Screenshots: TBD

Once the design is attached, the Acceptance Criteria should agree with it. If they don't,
update the AC.

## 5. Acceptance Criteria

How a reviewer tests the work. Write one Gherkin scenario per distinct, observable
behavior, including the unhappy paths:

    Scenario: <short name>
      Given <precondition>
      When <action>
      Then <observable outcome>

Phrase outcomes as what a caller, the system, or a downstream reader observes (a returned
result, a state change, what appears on screen), not the mechanism underneath. Don't put
field names, status codes, or schema details here; they belong in Technical Details. Cover
the empty, error, and permission cases, and mobile or responsive behavior where the UI is
expected to work on small screens. Each scenario must be able to fail.

**Exception: artifact tickets use a checklist.** When the deliverable is an artifact
rather than runtime behavior, write the AC as a checkbox list of facts a reviewer confirms
at code review time instead of Gherkin. That covers schema-only and migration-only work,
repository scaffolding (standard files, build, CI), and packaging, install, or
configuration work (a Tutor plugin, install docs, an image build). The test is what
closing the ticket proves: if a person runs it and watches it succeed or fail, use
Gherkin; if a reviewer confirms that something exists and is correct, use a checklist.
When the call is unclear, ask the human.

## 6. Technical Details (collapsible)

The in-the-weeds material: the suggested approach, the files involved, and any context
Claude wants to flag. Every ticket has this section, except a design spike.

**Write it for an Axim engineer who has two minutes.** The goal is that an engineer can
read the approach, agree or push back before any code is written, and not be surprised at
code review. That only works if the section is short. Leave out anything a competent
developer on this codebase would do without being told: "add tests", "run the
migration", "register the URL", "follow the existing serializer pattern". Keep what they
couldn't guess: the non-obvious decision, the place it lives, the edge case that bites.

**It is a suggested approach, not the source of truth.** The User Story, Description, and
Acceptance Criteria define what must be true when the work is done. Say so in the
section's opening sentence.

Wrap the whole section in one collapsible block. Keep a blank line after the `<summary>`
line and before `</details>`, or GitHub renders the Markdown inside as literal text:

    <details>
    <summary>Technical Details</summary>

    This is a suggested approach, not the source of truth. The User Story, Description,
    and Acceptance Criteria define what must be true when the work is done.

    **Summary**

    ...

    **Approach**

    ...

    **Files to create and modify**

    ...

    **Additional context**

    ...

    </details>

The parts, in this order:

- **Summary** (only when the Approach runs past about 15 lines). Two to four plain
  sentences saying what the approach does, for a reader who won't read the Approach. When
  the Approach is 15 lines or fewer, leave the Summary out: the Approach is already short
  enough to read.
- **Approach** (required). Pseudo code or a numbered list of steps, whichever is shorter
  for this ticket, using the real names of the files, classes, functions, and endpoints
  involved. Each step says what happens and, where it isn't obvious, why. Include the
  specific edge cases the tests must cover, public API or contract impact, the layer the
  code sits in (respecting `.importlinter`), and a link to a warranted ADR, but only where
  each one applies. Name companion-ticket work that touches the same flow and mark it out
  of scope by GitHub issue number. State only the recommended approach, not the
  alternatives that were considered; those go to the human synthesizing the ticket, and,
  when the choice is architecturally significant, into a proposed-status ADR this section
  links to.
- **Files to create and modify** (optional). One table, one line per file. Mark each file
  as new or modified. The table is a map; any decision about a file is stated in the
  Approach, not here.

      | File | Change |
      | --- | --- |
      | src/openedx_learning/applets/cbe/api.py | modified: add get_default_rule_profile() |
      | src/openedx_learning/applets/cbe/rest_api/v1/views.py | new: RuleProfileView |

- **Additional context** (optional). Context Claude thinks a developer should know that
  the human-written Context section doesn't already cover: prior-art files, a related
  ADR, a related issue. A short bullet list of file paths (never line numbers, they rot),
  ADR links, and GitHub issue numbers. Don't repeat anything in the human Context.

Omit an optional part entirely when it's empty. Say each fact once: a rule stated in the
Approach is not restated in the Files table or in Additional context.

Do not add an Example Resolution Prompt or any closing "how to implement this" prompt.

## 7. Open Questions (optional, rare, always last)

A posted ticket should have no Open Questions except ones that are genuinely the
implementer's to decide while building (for example, a naming choice or an internal
structure that the AC and Approach don't constrain). Everything else gets answered before
posting: the architect answers foreseeable questions during the pre-handoff check, and the
BA answers requirements questions during the draft pass. Omit the section when nothing is
left.

While a ticket is still being drafted, label each question with who resolves it:
`(architect, final review)` for one waiting on the architect, or `(implementer)`. The
architect resolves every `(architect, final review)` question during final review, folds
the answer into the AC, Technical Details, or Context, and removes the question, so none
of them are posted. Each question is crisp and answerable.

## Design spike tickets

A design spike's deliverable is design artifacts and documented decisions, not code. It
differs from the standard shape in three ways:

- The Acceptance Criteria are a delivery checklist (updated Figma, a documented decision
  with rationale, notes for the dependent implementation ticket), opening with: "This is
  a design spike. The deliverable is design artifacts and documented decisions, not
  working code." Every Open Question needs a matching checklist item.
- Technical Details is replaced by an open (not collapsed) **Context for the Designer**
  section, which Claude drafts: the current state of the relevant UI or flow, the options
  under consideration with tradeoffs, the constraints the design must respect, and links
  to related tickets and the current Figma file.
- Open Questions is required, and its questions are the designer's to resolve, which is
  the one exception to the implementer-only rule in section 7.

## Stubs

When a ticket depends on a design decision that isn't made yet, it exists only as a stub:
a title plus a one-sentence blocker note. The full ticket is written after the blocking
decision is documented.

## Splitting into companion tickets

When a piece of work spans repos or layers (for example, a backend contract in
`openedx-core` plus a consuming change in `openedx-platform` or a frontend repo), split it
into one ticket per repo or layer. The human writes each ticket's User Story,
Description, and Context as usual. For the sections Claude drafts:

- Pick one ticket to hold the full shared contract, usually the one that defines what the
  others depend on. The other tickets reference it by GitHub issue number instead of
  copying its Technical Details or its identical AC scenarios. Restate a scenario only
  where the companion's behavior is genuinely different.
- Each companion is still a complete unit of work: a developer can tell what to build and
  how to verify it from that ticket plus the shared contract, without reading the other
  ticket's discussion.
- Don't explain in any ticket why the work was split.

## What a good ticket looks like

- The page a reader lands on shows the human-written User Story, Description, and
  Context, the UX Design placeholder on a frontend ticket, the Acceptance Criteria, and
  one collapsed Technical Details summary.
- The title, User Story, Description, and Context read exactly as the human wrote them,
  and the title still reads as a human wrote it: plain, specific, and understandable
  without opening the ticket.
- The Acceptance Criteria are Gherkin (or a checklist for an artifact ticket), and each
  one could fail.
- Technical Details is short enough that an Axim engineer could approve the approach from
  it, with a Summary only when the Approach is long, and nothing in it that a developer on
  this codebase would do without being told.
- Each fact appears once, in its one canonical place.
- The Claude-drafted sections say what the work is and how things are now. Nothing
  describes what something isn't or how an earlier draft had it, except negatives that
  are themselves requirements, such as out-of-scope items and "must not" rules.
- Nothing references an internal ticket ID, a spreadsheet, or a release date.
- The work is a 1-2 developer-day unit, or it is split into companion tickets.
