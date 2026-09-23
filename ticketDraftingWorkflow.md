# Ticket drafting workflow

How the human architect and the human BA work with Claude to take a ticket from a blank
cache file to a posted GitHub Issue.

Axim asked that the parts of a ticket that frame the work be written by a person, and that a
person audit everything Claude drafts before it is posted. So the architect writes the title,
User Story, Description, and Context; Claude drafts the Acceptance Criteria and Technical Details
with the BA; and both humans review before posting. The ticket format itself is defined in
[`.claude/ticket-template.md`](.claude/ticket-template.md).

## Where the draft lives

Each ticket is a file in the GitHub issues cache, for example
`.claude/github-issues/student-progress/SP03-.../ucid-SP03.xx-ghi-738.md`. The architect
and the BA hand that file back and forth by committing and pushing it in this repo. The
GitHub Issue itself is only updated at the very end.

## The steps

| # | Who | What to ask Claude | What you get | Then |
| --- | --- | --- | --- | --- |
| 1 | Architect | "Scaffold #738 and #739." | Empty User Story, Description, Context, and Notes for drafting headings in each file. | Write the title (the `#` line at the top, replacing any placeholder title) and those sections. |
| 2 | Architect | "Run a pre-handoff check on #738." | Concerns about your sections, and every question Claude can foresee, asked now. | Answer the questions, fix what you agree with, commit, and push to the BA. |
| 3 | BA | "Draft #738 with ticket-writer." | Drafted Acceptance Criteria and Technical Details, a UX Design placeholder on frontend tickets, and an audit checklist. | Audit against the checklist, commit, and push back to the architect. |
| 4 | Architect | "Pre-post check on #738," plus your list of questions and concerns, if any. | The same audit checklist the BA used, answers to your list, revisions to the drafted sections, and a readiness check. | Audit against the checklist, commit, and push to the BA. |
| 5 | BA | "Pre-post check on #738." | A final readiness check. | Post to the GitHub Issue, or ask Claude to post it. |

## What to put in each human-written section

- **Title:** what the ticket delivers, in plain words a person skimming the issue list
  understands. "GET default rule profile"
- **User Story:** why the user cares. "As a platform admin, I want to see the instance's
  default rule profile, in order to know which rules apply to courses that don't set their
  own."
- **Description:** what developers need to do, in one to three sentences. "We need to build
  a GET endpoint that returns the instance-wide rule profile."
- **Context** (optional): what else developers should know right now, such as a blocking
  PR, a related issue, or a partial implementation, referenced by GitHub number.
- **Notes for drafting** (optional): anything the BA and Claude should know that shouldn't
  be posted, such as hunches about the approach, related code, or edge cases. Claude uses
  the notes and removes them before posting.

## Things to know

- **Claude never edits the title, User Story, Description, or Context.** It tells you about
  problems in chat, and the architect decides what to change.
- **Answer questions early.** The goal is a posted ticket with no Open Questions except ones
  that are genuinely the implementer's to decide. That is why step 2 asks every question it
  can foresee. During step 3, Claude sends requirements questions to the BA and suggests
  taking scope and technical questions to the architect. Anything still open is saved in
  the ticket labeled `(architect, final review)` or `(implementer)`, and the architect
  resolves the first kind in step 4.
- **Technical Details is collapsed and short.** It is written so that an Axim engineer
  could approve the approach in a couple of minutes: an Approach in pseudo code or steps, a
  Summary only when the Approach is long, a files table, and any extra context Claude wants
  to flag.
- **Frontend tickets get a UX Design section** that tags @illiphilli to add the Figma link
  and screenshots after posting.
- **Nothing is committed, pushed, or posted to GitHub unless you ask.**
