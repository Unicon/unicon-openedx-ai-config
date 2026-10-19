---
name: github-report-creation
description: Turn QA test results the user supplies (a CSV/XLSX export of a test-case spreadsheet, or notes given directly in chat) plus environment, test-user, and free-form remarks into a GitHub-ready test report. Use when asked to prepare, write, or draft a test report, QA report, or testing summary for a GitHub issue. Writes the report in English regardless of the language the source notes were given in, verifies GitHub-flavored markdown tables render correctly by saving a local .md file first, and delivers both a chat message ready to copy-paste and the saved file.
---

# GitHub report creation

Produces a single, GitHub-issue-ready test report from whatever raw QA material the user
hands over: a spreadsheet export of test cases and pass/fail results, plus environment,
test-user, and any extra remarks they want folded in (edge cases tested outside the main
spreadsheet, implementation caveats surfaced during code review, or behavior worth
flagging that isn't a bug). The user posts the finished report into GitHub themselves;
this skill only prepares it and hands it back.

## 1. Intake

Collect the following before drafting, asking only for whatever is actually missing
rather than guessing at it (per CLAUDE.md's working-style rule to ask when a request is
ambiguous):

- The GitHub issue number the report is for.
- The test-results source: a CSV/XLSX file path, or test cases pasted directly in chat.
  When the user can choose, prefer CSV over XLSX: it's plain text and reads reliably,
  while XLSX parsing is not guaranteed.
- If the same session already ran `qa-test-prep` and the testing itself, use that as the
  source: the test cases come from the `qa-test-prep` Artifact, and the results come from
  the conversation, both the checks the agent ran itself and the results the user reported
  in chat. Ask only for results that are still missing, rather than asking for a
  spreadsheet export.
- The environment tested (a URL). The team's shared test environment is the Master
  Sandbox; default to it instead of asking, and use a different environment only when
  the user names one.
- The test user/account the testing was performed on. Each tester has their own account
  on the shared environment, so always ask for it rather than reusing one from an earlier
  report.
- Whether it was API or UI testing, and if API, which tool (e.g. Postman).
- The overall verdict: did every case pass, or are there bugs that need to be reported.
- Any additional notes to fold in beyond the spreadsheet: extra scenarios tested outside
  the main table, implementation notes worth flagging, or observed-but-not-a-bug behavior.

## 2. Read the source data

Read the CSV/XLSX directly with the Read tool; it's small enough to read inline; there's
no need to dispatch a sub-agent for this step. If the spreadsheet groups rows into
scenarios through merged or blank cells (a header row per scenario, blank cells beneath
it), reconstruct that grouping as separate report sections instead of one flat table.

## 3. Draft the report

- **Always write the report content in English**, whatever language the user's own
  notes, spreadsheet, or chat messages are in. The report is a GitHub-facing artifact
  read by the wider Open edX community.
- Structure the report as a short header block (environment, test user, test type,
  overall result), followed by one section per scenario. Use a table for a scenario
  that's naturally tabular (a set of filter/input combinations checked against expected
  and actual results), and prose bullets for a scenario that isn't (a checklist-style
  verification, a set of error-response checks).
- Judge coverage against the ticket's acceptance criteria. A scenario counts as verified
  when its acceptance criteria are met. Extra edge cases that the `qa-test-prep` Artifact
  added on its own are not requirements of the ticket, so an untested one does not go into
  a "Not verified" section. Before marking a manual-only check (such as a screen reader
  announcement) as not verified, ask the user: they often perform those checks themselves
  and may not have mentioned it yet.
- Fold in the user's extra remarks as their own labeled sections (for example
  "Implementation note", "Additionally tested: ...", "Observation: ..."), rather than
  squeezing them into the main results table.
- Write plain, human-sounding sentences, not notes to yourself. Follow CLAUDE.md's "say
  it in full" rule even though the destination is a GitHub comment: give every claim a
  subject and a verb, and avoid an absolute claim the underlying reality doesn't actually
  support. For example, if a constraint is "not expected to occur in normal usage" rather
  than a hard impossibility, say it that way instead of asserting it "cannot happen" or
  "cannot exist" outright.
- Follow CLAUDE.md's writing-style rule: no em dashes, US spelling, direct
  engineer-to-engineer tone, no marketing language or filler.

## 4. Verify the markdown renders before delivering

GitHub-flavored markdown tables are sensitive to how they're produced and pasted. Before
handing the report back:

1. Save it as a local `.md` file (default to the scratchpad directory unless the user
   names a location).
2. If there's any doubt about rendering, for example the user previously reported broken
   tables, or this is the first report of the session, have the user open the file in a
   markdown previewer (e.g. VS Code) to confirm the tables render correctly before they
   paste into GitHub. A table that renders correctly in a local previewer but breaks on
   GitHub points at the paste path (a rendered preview copied instead of the raw markdown
   source), not at the markdown itself; in that case, tell the user to copy from the raw
   file rather than from a rendered preview.

## 5. Deliver

Every time, deliver both of these:

- The full report as a chat message, in GitHub-flavored markdown, ready to copy-paste
  into the issue.
- The same content saved to a local `.md` file, so the user can preview its rendering or
  reuse it later.

The user posts the report to GitHub themselves. Per CLAUDE.md's default of confirming
before actions visible to others, this skill does not post it on their behalf unless the
user explicitly asks and approves that.
