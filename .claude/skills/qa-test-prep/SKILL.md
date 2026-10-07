---
name: qa-test-prep
description: Prepare QA test materials (test-case tables, fixture/test-data plans, Postman and UI verification steps, and dependency-status flags) for one or more not-yet-implemented tickets. Use when asked to prepare test cases, a test plan, QA prep, or a Postman/UI verification plan for a GitHub issue or a batch of issues, before a PR exists. Verification has to be planned from the ticket text and its dependency chain, not from a diff. Dispatches the reading and drafting to a sub-agent so ticket bodies, dependency chains, and code reads stay out of the orchestrating session. When a ticket's own verification method is Postman and the Postman MCP server is set up (the skill checks, and asks the user once, remembering the answer), that same sub-agent also builds the matching folder, requests, and variables in the user's configured Postman workspace and collection. After publishing, a second sub-agent builds Studio-importable test-data files (taxonomy CSV/JSON, course .tar.gz archives) with a README in a per-ticket subfolder of the user's configured test-data folder, and the Artifact is updated to reference them. The delivered Artifact opens with a plain-language explanation of what is being implemented and why, and a sub-issue whose testing is not independent of a parent ticket gets a short cross-reference to that parent instead of duplicated test material. Delivers the result as a shareable Artifact. Before analyzing, it checks whether the ticket already has an artifact from an earlier run: if the ticket is still not ready for QA it asks the user what to do, and if it has become ready since then it re-analyzes against the merged PR and updates the existing artifact, Postman folder, and test-data files in place.
---

# QA test prep

Turn one or more not-yet-implemented tickets into QA-ready material: a test-case table
expanded from the Acceptance Criteria, a test-data/fixture plan, concrete Postman requests
or UI steps to verify each case, and a flagged list of any blocking-dependency status that
matters before the QA cycle can actually start. The heavy reading happens in a dispatched
sub-agent instead of in this session, so running the skill repeatedly does not fill up the
orchestrating session's context.

The sibling repos `openedx-core`, `openedx-platform`, `frontend-app-authoring`, and
`unicon-openedx-ai-config` live side by side in one workspace folder. This file calls that
folder the workspace root and refers to everything relative to it.

Every artifact this skill produces opens with a plain-language explanation of what is being
implemented and why, written for a colleague who tested the result but doesn't have a clear
picture of what it does or how it is supposed to work. When a ticket is a sub-issue whose own
testing surface is not independent of a parent ticket's (for example, it defers its
acceptance criteria to the parent and introduces nothing a QA engineer could exercise
directly and distinctly from what the parent already covers), its section skips the full
test-case table and fixture plan and instead gets a short cross-reference to where the
testing actually happens.

When at least one test case's verification method is Postman and Postman is set up (see
"Settings: Postman and the test-data folder"), the same dispatched sub-agent also builds the
actual folder, requests, and variables in the user's configured Postman collection,
following the conventions of the folders already there. A QA engineer then gets runnable
requests, not just a table describing what a request should look like.

After the Artifact is published, a second Sonnet sub-agent builds the test-data files a QA
engineer can import through the Studio UI (taxonomy CSV/JSON, course `.tar.gz` archives),
saves them in the ticket's `#<N>/` subfolder of the configured test-data folder with a
`README.txt`, and the Artifact is updated to name those files (step 5).

Everything this skill writes is in English: the sub-agent prompts, the sub-agent reports,
the Artifact, and every `README.txt`.

## Conventions this skill applies

These team conventions apply to every analysis. Steps 3 and 4 repeat the parts a sub-agent
or the Artifact needs.

- **On Master Sandbox, QA works through the UI, Django admin, and Postman.** QA cannot run
  scripts on the shared test environment (Master Sandbox): no shell, no pytest, no Django
  shell. QA verification happens through the LMS and Studio UI, through Django admin (most
  testers have admin access), and through Postman requests against real endpoints. Django
  admin can prepare or inspect data, but it cannot invoke a function that has no REST or UI
  entry point.
- **Do not conclude "not implemented, too early to test" from the local checkout alone.**
  Search for the implementation PR in the repository where the code lives (`openedx-core`,
  `openedx-platform`, or `frontend-app-authoring`) by ticket number or issue URL. Issues are
  filed in `openedx-core`, PRs often live elsewhere, and the issue's
  `closed_by_pull_requests` is often empty. Report the PR state and merge date. When the PR
  is merged but nothing shows it is deployed, say "merged, deployment to Master Sandbox
  unknown" rather than "not implemented". When a PR exists, use its testing instructions to
  resolve ambiguities in the ticket.
- **Scenarios whose data or check is out of reach of the UI, Django admin, and Postman go
  to a local Tutor environment.** Data that Django admin can create or show (the model is
  registered in an `admin.py`) stays on Master Sandbox. Only data that none of the three
  channels can create, or a check that none of them can see (for example learner status
  rows or a deleted root, when their models are not in Django admin), runs in the tester's
  local Tutor environment (for example through `tutor dev run cms ./manage.py cms shell`). If the tester has no local Tutor environment, those cases
  are marked as not testable on Master Sandbox. "The developer seeds the data" is never the
  default path.
- **The i18n acceptance bar is "not hardcoded", not "fully translated".** A new UI string
  that still shows in English after the language is switched is not a defect of the ticket
  when the string goes through the i18n message system (`useIntl` / `intl.formatMessage` in
  React, gettext in Django). Check the source for hardcoding before flagging a string.
- **A bug found during a ticket's QA that turns out to be pre-existing is filed as its own
  ticket.** A pre-existing bug is one that the ticket under test did not introduce. It gets
  a separate ticket with the status "Out of Scope". It is not folded into the ticket under
  test and not skipped.
- **Re-importing the same taxonomy file needs a page reload.** A known, already-reported
  Studio bug makes a second upload of the same file in one page session do nothing. Test
  steps that re-import a file reload the Taxonomies page first (details in
  `references/test-data-files.md`).

## Model and orchestration

Per the Delegation rule in `CLAUDE.md`, you (the top-level session running this skill) are
the only one who dispatches. Do the analysis in a single `general-purpose` sub-agent on
Sonnet per invocation, covering every ticket number the user gave you in that invocation.
The sub-agent reads the tickets, GitHub MCP data, and any cross-repo docs itself; only its
finished report re-enters this session. Never read ticket bodies, dependency chains, or
architecture docs into this session's own context to save the sub-agent the step. That is
exactly the bloat this skill exists to avoid.

## 1. Intake

Collect the GitHub issue numbers from the user's request, in `openedx/openedx-core` by
default (ask only if the user names a different repo or the target repo is genuinely
ambiguous). If the user gives more than one ticket number in the same request, batch them
into one dispatch and one deliverable, for example #615 and #616 together: batching saves
the sub-agent from re-deriving shared context (a common epic, a shared dependency chain,
overlapping fixtures) twice. Split into separate dispatches only when the tickets come from
clearly unrelated requests, or the user asks for them separately.

Do not read the tickets yourself at this stage; the sub-agent in step 3 does that.

Check that a GitHub MCP server is connected, meaning its tools are available in the session.
The sub-agents read tickets, dependencies, and implementation PRs through it, so the skill
cannot work without it. If it is not connected, tell the user that this skill requires the
GitHub MCP server, offer to help set it up, and do not continue until it is connected. Save
nothing to memory for this check. The `gh` CLI is optional: the readiness check falls back to
a PR search when it is missing.

## 2. Check for a previous run

The user usually runs this skill twice on the same ticket: first while it is still in
development, then again after it moves to Ready for QA, to catch what changed. Sometimes
the user also re-runs an already processed ticket by mistake. So before any analysis,
check each ticket for an earlier run. The Artifact is the only resource to check, because
every run publishes one; the Postman folder and the test-data folder are not always created.

List the user's artifacts yourself (`Artifact`, `action: "list"`, `limit: 50`) and look for
a title that contains `#<N>` among its leading ticket numbers (a batch title such as
`#615 #616` counts for both tickets). If several artifacts match, use the most recently
updated one. A ticket with no match is a first run: it goes through steps 3-5 as described.

For every ticket that has a previous artifact, dispatch one readiness-check `Agent` call
(`subagent_type: general-purpose`, `model: sonnet`) covering all such tickets of this run,
with the prompt below. This check is bounded and separate from the full analysis, so a
ticket that is still not ready costs no full re-analysis.

<template>
Check whether openedx/openedx-core ticket(s) #<N>[, #<M>] are ready for testing, and
compare that with what the previous QA artifact recorded. Do not publish, change, or commit
anything, do not write to GitHub, and do not launch other agents. If something is missing,
return a "Needs research" item.

Previous artifacts (read each one through Artifact, action "read"):
- #<N>: <URL>

1. State at the time of the previous analysis. The artifacts have no separate snapshot
   block, so reconstruct it from what is already written on the page:
   - the analysis date: look for a date (usually ISO `YYYY-MM-DD`, but accept any date
     format) next to "Prepared" or "Statuses taken from GitHub", in the header or in the
     footer of the page; if no date is found, report the date as unknown;
   - the readiness verdict: the first callout or banner in the header ("Cannot be tested
     yet", "Implementation merged, deployment must be confirmed", and similar);
   - the board status, if it is recorded (older artifacts do not have it);
   - the PRs and their state (number, repository, open/draft/merged, date);
   - the table in the "Dependencies" / "Dependency status" section: ticket numbers and
     their statuses.
2. Current readiness. Check in order and stop at the first source that gives an answer:
   a. The ticket's status on the GitHub Projects board (the Status field, for example
      through `gh api graphql` and `projectItems` on the issue). Ready for QA and every
      status after it counts as "ready".
   b. If the board status cannot be obtained, check deployment: search for the
      implementation PR by ticket number in the repository where the code lives
      (openedx-core, openedx-platform, or frontend-app-authoring; the issue's
      `closed_by_pull_requests` is often empty, and the local checkout may lag behind
      master). Report its state, its merge date, and any sign that it is deployed to
      Master Sandbox. A merged PR with no sign of deployment is "merged, deployment to
      Master Sandbox unknown", not "not implemented".
   c. If neither source gives a confident answer, return "undetermined" and what you
      found. Do not guess.
3. Whether the ticket was ready at the time of the previous analysis: by the board status
   if the artifact recorded one, otherwise by the readiness verdict (a verdict of "cannot
   be tested" or "too early" means "was not ready").

Reply in English. For each ticket give: the date of the previous analysis and the artifact
URL; whether the ticket was ready then (yes/no) and what that conclusion rests on; whether
it is ready now (yes/no/undetermined), the source (board or deployment), and the concrete
facts (status, PR number, merge date).
</template>

Then decide per ticket from the report. Tickets in one batch can land in different rows:
handle each by its own row, and batch every question for the user into one
`AskUserQuestion` round.

| Previous run | Ready now | What to do |
| --- | --- | --- |
| None | Any | This is a first run: steps 3-5 as described. |
| Not ready | Not ready | Tell the user the ticket was already analyzed on `<date>` (with the artifact link) and is still not ready for testing, with the facts behind that verdict. Ask what to do next, for example re-run the analysis anyway or stop. |
| Not ready | Ready | This is a re-analysis: steps 3-5 in re-run mode (below). |
| Ready | Ready | Tell the user the ticket was already analyzed after it became ready (date and artifact link), and wait for the user to say what to do next. Do not start any analysis. |
| Any | Undetermined | Ask the user directly whether the ticket is ready for testing now, with what the check did find, then follow the matching row. |

**Re-run mode.** The goal is to find what changed since the previous analysis and bring
every resource up to date, without asking the user before each update. Re-run tickets and
first-run tickets of one batch still share the single analysis dispatch in step 3; append
this block to that prompt, with the re-run ticket numbers and previous artifact URLs filled in:

<template>
Tickets #<K>[, #<L>] are a repeat analysis: the ticket was analyzed while it was in
development and is now ready for testing. Previous artifact: #<K>: <URL>. Read it through
Artifact (action "read"). For these tickets, an implementation PR exists: find it, read its description, its testing instructions, and
its diff, and check the testing plan against what is actually implemented (endpoints,
fields, response codes, screens, and UI elements).

Compare the ticket text and Acceptance Criteria, the dependency statuses, and the
implementation in the PR against the previous artifact. Prepare the full report again from
the current state, not as edits to the old one. In a separate section at the end, list the
differences from the previous artifact: what changed, in which test case or section, and
from which source (ticket, PR, dependency).

This paragraph applies only when Postman is used in this run. The Postman folder of such a
ticket was created by an earlier run of this same process. The
rule in `postman-conventions.md` "if the folder already exists, stop and ask" does not apply
to these tickets: update the existing folder to match the current plan (add missing
requests, fix changed ones, delete those that no longer match any test case) and list what
you changed in the report. If there is no Postman folder and one is now needed, create it as
usual.
</template>

In step 4, update the previous artifact through its `url` (read it first, as the Artifact
tool requires) instead of publishing a new one. The page shows only the current state: no
"what changed since last time" section and no history. The readiness callout on the page
must name the analysis date and the board status, as described in step 4, so the next run
can compare against them. Put the discrepancy list in the chat summary instead.

In step 5, the `#<N>/` test-data folder of a re-run ticket also comes from the previous run.
Add this to that prompt: "The `#<N>/` folder was created by an earlier run of this same
process. The rule 'if the folder exists, return an open question' does not apply to it:
update the files and README.txt to match the current test-data plan and list what you
changed in the report." When the current plan needs no importable data, skip step 5 for that
ticket, leave an existing folder in place, and say so in the summary.

## Settings: Postman and the test-data folder

Resolve these two settings after step 2 has decided that an analysis will run, and before
the step 3 dispatch (Postman) or the step 5 dispatch (test-data folder). The user's answers
are remembered, so most runs ask nothing.

### Memory mechanics

Claude Code's auto memory can be enabled or disabled per user. When it is available (the
session's system prompt describes a memory directory), save each setting as a memory entry
following that system prompt's memory format, and read it back on later runs. When memory is
not available, ask for the setting on each run instead. Memory is stored per project
folder, so a run started from a different folder asks again; that is expected.

Sub-agents do not read memory. You read the saved values here and pass them to the
sub-agent inside its prompt.

### Postman setup

Run this check once per invocation, before step 3.

1. Check memory first for a saved Postman setting for this skill. If memory says the user
   declined Postman, skip all Postman work silently and describe the requests only in the
   Artifact. The exception is a current request in which the user explicitly asks to use
   Postman: in that case run the check below again and update memory.
2. Otherwise check whether a Postman MCP server is connected, meaning its tools are
   available in the session.
3. If it is not connected, tell the user that Postman work needs the Postman MCP server
   installed and configured, and offer a choice: set it up now (then continue once it is
   connected), or proceed without Postman. If the user declines, save "user declined
   Postman" to memory so the skill does not ask again, and describe the requests only in
   the Artifact.
4. If it is connected and memory has no saved workspace, collection, and environment, run
   the first-time setup:
   a. Ask the user for the Postman workspace name and the collection name.
   b. Ask which Postman environment holds the Master Sandbox settings. If the user has none,
      create one in that workspace (for example "Master Sandbox") with `createEnvironment`.
   c. Make sure the environment has the base variables the auth requests in
      `references/postman-conventions.md` use: `lms_base_url`, `base_url` (Studio),
      `studio_username`, `studio_password`, `oauth_client_id`, `oauth_client_secret`,
      `bearer_token`, and `csrftoken`. Add only the missing ones, using the read, merge, and
      write pattern from the "Environment and variables" section of that file, so existing
      values are kept. Ask the user for the values of `lms_base_url`, `base_url`, and
      `studio_username`. Create `studio_password`, `oauth_client_id`, and
      `oauth_client_secret` with empty values and type `secret`, then tell the user to fill
      them in directly in Postman. Never ask for a password or a client secret in chat and
      never save one to memory. `bearer_token` and `csrftoken` start empty, because the login
      requests write them.
   d. Save the workspace, collection, and environment names to memory.
5. If saved values exist, use them without asking. If the saved workspace, collection, or
   environment is not found in Postman (renamed or deleted), ask again, rerun the matching
   part of the first-time setup, and update memory.

Variables a ticket needs beyond these base variables are created during the analysis
itself, as described in the "Environment and variables" section of
`references/postman-conventions.md`.

When Postman is not used, task 6 in the step 3 prompt is replaced by an instruction not to
touch Postman and to describe each Postman-verified request fully in the report (method,
path, headers, body, expected response). The Postman-related Artifact changes in step 4 are
skipped; the request descriptions stay in the verification section.

### Test-data folder

Resolve this just before the step 5 dispatch, and only if step 5 will run.

1. Check memory for a saved base folder for test-data files. If one is saved, use it
   without asking.
2. If none is saved, ask the user for a base folder and save the answer to memory.
3. If the user does not want to give one, build the files in the session scratchpad
   directory, tell the user the path, and save nothing.

Files always go into a per-ticket subfolder `#<N>/` under the base folder (or under the
scratchpad directory in the fallback case).

## 3. Dispatch the analysis

Dispatch one `Agent` call, `subagent_type: general-purpose`, `model: sonnet`, with a
self-contained prompt built from the template below. Fill in the actual ticket numbers and
repo, and the Postman workspace, collection, and environment names from the Postman setup (or the
no-Postman variant of task 6). Keep the numbered task list as-is unless the user explicitly
asked for something narrower than the full set. Write the prompt in English.

<template>
You are preparing QA testing for GitHub Issue(s) #<N>[, #<M>, ...] in the repository
`openedx/openedx-core`. The ticket(s) may have no PR yet and development may be unfinished,
so the task is purely analytical: you do not change code, create commits, or post anything
to GitHub. You only read and prepare material locally. Do not publish an Artifact yourself,
even if you technically have access to that tool: publishing is a separate step that only
the session that launched you performs, and only after it runs the design gate
(`artifact-design`). Return the finished report as text at the end of your work. Write the
report in English.

Context to read before you start:
- Read each ticket in full through the GitHub MCP (issue_read, owner=openedx,
  repo=openedx-core, issue_number=<N>).
- Determine from the ticket text where the code actually changes: in this repository
  (openedx-core), in openedx-platform, or in frontend-app-authoring. Tickets in this
  tracker are often filed here by convention while the implementation lives in another
  repository. The sibling repositories are checked out next to each other under the
  workspace root. If there is no local checkout of the needed repository, do not guess the
  current state of the code: work from the ticket text and mark it explicitly as "Needs
  research: access to <repository> to compare against the current code".
- Do not conclude "not implemented, too early to test" from the local checkout alone. Search
  for the implementation PR by ticket number or issue URL in the repository where the code
  lives (openedx-core, openedx-platform, or frontend-app-authoring); the issue's
  `closed_by_pull_requests` is often empty and the local checkout can lag behind master. In
  the report give the PR number, its state (open, draft, merged), and the merge date. If the
  PR is merged and nothing shows it is deployed, write "merged, deployment to Master Sandbox
  unknown", not "not implemented". If a PR exists, read its description and testing
  instructions and use them to resolve ambiguities in the ticket.
- Read the text of every blocking or related ticket mentioned in the Description or
  Dependencies section the same way (issue_read), and record its current `state` and, if
  present, `state_reason`. A ticket can be closed as `not_planned` rather than merged even
  though the referencing ticket treats it as a completed blocker. If you find such a
  discrepancy, raise it as a separate item in task 5 below.
- If the ticket concerns CBE/competencies (Competency Taxonomy, Competency Criteria,
  Student Progress, and similar), also read `.claude/architecture-taxonomies-and-competencies.md`
  and `.claude/cbe-project-context.md` in the `unicon-openedx-ai-config` repository. They are
  the source of implicit business rules and MVP boundaries that the ticket text itself does
  not contain (for example: protection against deletion once a learner status exists, two
  different status vocabularies in the backend and the UI, features intentionally deferred
  beyond the MVP such as retakes or versioning). Use them to extend the test-case table in
  task 1 with the edge cases that follow from these rules, and to flag in task 4 when a
  ticket's AC actually describes behavior outside the MVP scope. For tickets outside
  CBE/competencies (tagging, catalog, and so on), do not read these files; they are not
  relevant.

Before starting the tasks below, classify EVERY ticket of the numbers you were given into
exactly one of three categories. Use two checks:

- Check 1 (own acceptance criteria): does the ticket body contain its own self-contained
  Given/When/Then or otherwise independent acceptance criteria, or does it explicitly refer
  to a parent ticket for acceptance criteria (wording such as "Part of #N. See parent for use
  case, acceptance criteria...")?
- Check 2 (independent verifiable surface): can a QA engineer verify what the ticket
  describes directly and get an independently meaningful, checkable result that does not
  reduce to re-checking the same endpoint or UI already covered by the parent ticket? A new
  model, an internal-only function, a check of the kind "the value reaches the internal call
  and is not truncated on the way", or any other change observable only through the parent's
  endpoint does NOT count as an independent verifiable surface. A new or changed endpoint
  response, a new UI element or flow, or any user-visible behavior change does count.

From these two checks, assign the ticket to one of the categories:

1. Full testing material ("main task"): the ticket has its own acceptance criteria (check 1
   finds no reference to a parent), whether or not it belongs to an epic. For this ticket do
   the whole task list 1-6 below as usual.
2. No independent testing required ("sub-task without separate testing"): the ticket refers
   to a parent for acceptance criteria (check 1: yes) AND has no independent verifiable
   surface (check 2: no). For this ticket do not do tasks 1-6 from the list below. Prepare
   only: (a) a block of 2-4 sentences in plain language about what this ticket implements and
   why; (b) an explicit statement that this ticket needs no separate QA testing, and where
   the testing actually happens (the parent ticket number); (c) a list of the related ticket
   numbers with a one-line role for each. See the worked example below.
3. Partially covered by the parent ("hybrid"): the ticket refers to a parent for acceptance
   criteria (check 1: yes), but check 2 finds at least one scenario that is independently
   observable and not covered by the parent's own testing plan. For this ticket prepare the
   same short block as in category 2, plus a small table of test cases containing ONLY the
   scenarios unique to this ticket, explicitly marked as not duplicating the parent's testing
   (for example the heading "Checks unique to this sub-task, not covered by the testing of
   #<parent>").

Worked example (a real, already implemented case; use it as a model of tone and form, and do
not add details beyond what is written here): tickets #614, #628, and #629.

- #614 (the parent ticket): a full testing plan with test cases, fixtures, Postman requests,
  and dependencies. The ticket describes the ability to pass `taxonomy_type` when creating or
  importing a taxonomy, so that either an ordinary tag taxonomy or a Competency Taxonomy can
  be created directly through these endpoints.
- #628 (a sub-task in openedx-core, the low-level library): implements the mechanism itself.
  It teaches taxonomy creation to understand the `taxonomy_type` value, but it cannot decide
  what to create, because for architectural reasons it must not know about competency
  taxonomies. This task needs no direct QA testing. Testing has to be done in #614.
- #629 (a sub-task in openedx-platform, the upper layer where Studio lives): makes sure the
  `taxonomy_type` field is not lost on the way to openedx-core, and implements there the
  actual choice of what to create, an ordinary taxonomy or a competency one. This task needs
  no direct QA testing. Testing has to be done in #614.

Both #628 and #629 fall into category 2: their own ticket bodies refer to #614 for acceptance
criteria, and the changes they describe are observable only through an endpoint that the
testing of #614 already covers.

If you cannot confidently assign a ticket to any of the three categories (for example, the
parent-deferral wording is ambiguous, or you cannot tell whether a described change is
independently observable), do not guess. Record it in the report as an open question, in the
same form as the open-question mechanism described in task 6 below for an "existing folder in
Postman", and leave the section for that ticket unfinished until an answer arrives.

Separately: if, while reading a requested ticket, you find that its testing actually belongs
to a parent ticket that is NOT among the ticket numbers requested in this run, do not expand
the scope yourself. Under this project's Delegation rule you can neither launch other agents
nor address the end user directly. Record it as a separate "Scope decision needed" item in
the report: name the parent ticket number and explain why this ticket's testing depends on
it, and leave the section for this ticket as only a short category 2/3 block until the
session that launched you decides.

Regardless of category, for each ticket (or, if the tickets form one closely related group,
such as a parent and its sub-tasks or a single epic, for the group as a whole) prepare a
simple explanation of what is being implemented and why, in the language of a colleague who
tested the result but has no clear picture of what it does or how it is supposed to work. For
a group of closely related tickets, describe the shared feature once, and describe how the
tickets relate to each other (who implements which part and why the split is the way it is),
instead of repeating the same wording for every ticket separately. This block goes at the
start of the final report, before the test-case table and the other category 1 material. For
category 2 and 3 tickets it is the same as the "what and why" block described above and is
not repeated twice.

Tasks (tasks 1-6 below apply in full to category 1 tickets and to the unique scenarios of
category 3 tickets; they are not done for category 2 tickets, see the classification above):

1. Expand each Gherkin scenario from the Acceptance Criteria into a structured test-case
   table (with a "Ticket" column if there are several tickets). The columns are: Test case
   ID, Precondition, Steps, Expected result, Verification method. Take the verification
   method literally from the ticket text (Postman, manual check in the UI, and so on). Do
   not skip a single scenario from the AC.

   The QA test environment (Master Sandbox) does not allow running files or arbitrary code;
   QA has the LMS and Studio UI, Django admin, and Postman requests. Django admin can prepare
   or inspect data but cannot invoke a function. If the verification method that the ticket
   itself names is pytest, a direct function call, `manage.py shell`, or another code-level
   path (that is, the described behavior has no REST endpoint or screen through which it can
   be invoked yet), that is not an alternative verification method for QA. It is a sign that
   QA cannot test these scenarios right now. Record this explicitly as a separate conclusion
   at the start of the report (for example: "QA cannot test ticket #NNN: the function has no
   REST/UI surface, and the verification method in the ticket text is pytest, which is an
   instruction for the developer"), and name which dependency (usually the ticket that adds
   the calling code or the endpoint) must be implemented for a real entry point for QA to
   exist. Keep any pytest-level steps from the ticket as a separate section clearly labeled
   "for the developer or PR reviewer, not QA steps". Frame the test-case table of such a
   ticket as a reference of expected behavior, to be revisited once an entry point exists.

   For data a scenario needs and for checks of stored state, first check in the code whether
   the model is registered in Django admin (an `admin.py` in the app). If it is, the data is
   created or the state is checked through Django admin on Master Sandbox, and the test case
   marks those steps as requiring Django admin access. If some scenarios need data that none
   of the UI, Django admin, and Postman can create (for example learner status rows), or a
   check that none of them can see (for example a deleted root), mark them as
   local-environment cases: they run in the tester's local Tutor environment
   (`tutor dev run cms ./manage.py cms shell`). Everything reachable through the UI, Django
   admin, and Postman stays on Master Sandbox. In the report split the test cases by
   environment (Master Sandbox and local Tutor) with a reason for each group, and add a
   section "Preparation for the local run" with the shell snippets that create the data and
   the DB-check queries. Do not propose "the developer seeds the data" as the default path.
   The boundary with the previous paragraph: when the behavior under test has no REST or UI
   entry point at all, QA cannot test it yet, even when Django admin can prepare its data.
   When the behavior is reachable through REST or UI and only the setup data or a final
   check is out of reach of Django admin, the case is a local Tutor case.

   When a scenario imports the same taxonomy file more than once in one Studio page session
   (for example after deleting and recreating a test taxonomy), include a "reload the
   Taxonomies page" step before the second import. A known, already-reported Studio bug
   makes the "Continue" button on the "Upload file" step do nothing when the same file is
   uploaded again without a reload; do not report it as a new finding.

   For UI cases that involve text, apply the i18n acceptance bar: the criterion is "not
   hardcoded", not "fully translated". A new UI string that still shows in English after the
   language is switched is not a defect of the ticket if the string goes through the i18n
   message system (`useIntl` / `intl.formatMessage` in React, gettext in Django). Check the
   source for hardcoding before treating a string as a defect.

2. Design the test fixture plan: the concrete data (records, users, files) that must be
   created or configured in the test environment to cover each test case from task 1. If
   several tickets share the same fixtures, describe them once and say which test cases of
   each ticket use them.

3. Document the concrete verification requests: for Postman cases, the method, path, request
   body, authorization format, expected response code, and response body; for UI cases, a
   step-by-step scenario (where to go, what to click, what should be displayed).

4. List separately any inconsistencies or missing details you find while comparing the
   ticket with the current code, if you have access to the needed repository. If a defect or
   inconsistency turns out to be pre-existing (not introduced by this ticket), list it in a
   separate group "Pre-existing, to be filed as its own ticket with status Out of Scope".

5. List separately the status of every blocking dependency (open/closed, `state_reason`,
   including any discrepancy between how the referencing ticket describes the dependency and
   its actual status). This is not something to fix; it is what has to be passed to whoever
   plans the QA cycle, so that testing does not start too early.

6. <Postman variant> If at least one test case from task 1 has Postman as its verification
   method (not only the UI), build the corresponding requests directly in Postman. This
   applies only to test cases of category 1 tickets and the unique test cases of category 3
   tickets; for category 2 tickets no Postman requests are built, because they have no test
   case table of their own. Use the Postman workspace "<workspace name>", the collection
   "<collection name>", and the environment "<environment name>". Read `.claude/skills/qa-test-prep/references/postman-conventions.md`
   (in the `unicon-openedx-ai-config` repository) in full and follow it literally: it
   describes how to name the folder and the requests, what the folder description must
   contain, how to write the login / JWT requests, which environment and variables to reuse,
   and what to do if a folder for this ticket number already exists (do not create or change
   anything silently; in that case return an open question in the report and wait for the
   answer). If no test case is verified through Postman, say so explicitly in the report that
   a Postman folder is not needed, and do not create one.

Report format: at the start of the report, a plain-language block about what is being
implemented and why (one shared block for a group of closely related tickets, or a separate
block per ticket if they are not closely related). Then, for category 1 tickets and the
unique part of category 3 tickets: a summary table of test cases, a separate section with the
fixture plan, a separate section with the concrete verification requests or scenarios, a
separate section with the dependency status, and, if a Postman folder was created or
extended, a separate section with its name, link or ID, and a "test case -> Postman request
name" mapping table. For category 2 tickets: only the "what and why" block, the explicit
statement that the ticket needs no separate QA testing with the parent ticket number, and the
list of related tickets with a one-line role for each; there must be no test-case table,
fixture plan, or Postman section for such a ticket. Write so that a QA engineer without
access to this conversation understands the result in one read: in complete sentences, with
concrete values, without abbreviations and without references to "as discussed earlier".
</template>

If the sub-agent's report includes "Needs research" items (per the Delegation rule in
`CLAUDE.md`, it cannot dispatch further agents itself), resolve the cheap ones (a location
lookup or enumeration) with an `Explore` sub-agent on Haiku, then continue the QA-prep
sub-agent via `SendMessage` with the answer. Leave anything more expensive (a deep read
across a repo you don't have local access to) as a flagged item in the final deliverable
instead of escalating further. A "Needs research" item saying the configured Postman
workspace or collection was not found is handled by the Postman setup: ask the user again,
update memory, and continue the sub-agent with the corrected names.

If the report instead comes back with an open question about an **existing Postman folder**
for this ticket number (per `references/postman-conventions.md`, the sub-agent stops and asks
rather than silently creating or overwriting), that decision is the user's, not yours to
guess: summarize what the sub-agent found (the existing folder's name and its requests, one
line each) and ask the user via `AskUserQuestion` whether to use it as-is, extend it with
whatever the analysis says is missing, or leave it alone and create a separate new folder.
Continue the sub-agent via `SendMessage` with the user's answer before moving to delivery.

If the report instead flags a **Scope decision needed** item (the sub-agent found, while
reading a requested ticket, that its real testing surface lives in a parent ticket that is
not among the ticket numbers this run was asked to cover), that decision is also the user's:
ask via `AskUserQuestion` whether to (a) expand this run to also produce full test material
for that parent ticket, or (b) keep this run limited to the short cross-reference block for
the requested ticket, with a recommendation to separately invoke this skill for the parent.
Continue the same sub-agent via `SendMessage` with the user's decision, adding the parent
ticket to scope if expansion was chosen, before moving to delivery.

If the report flags an ambiguous classification instead (the sub-agent could not confidently
place a ticket into one of the three categories from the classification step in the template
above, for example because the parent-deferral language was unclear or it could not tell
whether a described change is independently observable), resolve it with the user the same
way: batch all such open questions into one `AskUserQuestion` round if there are several, then
continue the sub-agent via `SendMessage` with the answers before moving to delivery.

If the report contains test cases marked as local-environment cases (data or checks out of
reach of the UI, Django admin, and Postman), find out whether the tester has a local Tutor
environment. Check memory first (see "Memory mechanics") and use a saved answer without
asking. If none is saved, ask the user via `AskUserQuestion`, batched into the same round as
any other open question, and save the answer to memory. If the user later says the answer
has changed, update memory. With a
local environment, the Artifact keeps the environment split and the local-run preparation
section. Without one, the Artifact marks those cases as not testable on Master Sandbox.

## 4. Deliver

You (the top-level session) are the only one who publishes the Artifact, and only after
running the design gate, never before it, and never by trusting or reusing an Artifact a
sub-agent produced on its own. A `general-purpose` sub-agent has the Artifact tool available
to it regardless of what this skill asks it to do; if its finished report says it already
published a page, that page skipped the design gate and must not be treated as the
deliverable. Build the real one yourself as below (updating that stray URL via the `url`
parameter is fine, to avoid leaving an orphaned duplicate, but the content and design must
be yours).

Take the sub-agent's finished report and publish it as an Artifact: load `artifact-design`
first, then build a page whose every ticket's section opens with its plain-language "what and
why" block. For a batch of tightly related tickets (a parent and its sub-issues, or a single
epic), use judgment: one shared block describing the whole feature and how the tickets relate
to each other, followed by each ticket's own short role line, usually reads better than
repeating the same summary once per ticket; for tickets that are not tightly related, give
each its own block instead. After that opening block, build the rest of each ticket's section
according to the category the sub-agent's report assigned it:

- A category-1 ticket keeps the full treatment as its own sections: the test-case table, the
  fixture plan, the verification requests/steps, and the dependency-status section. If the
  report flagged that QA cannot test the ticket yet because its only verification method is
  code-level (pytest, a direct function call, a shell snippet) and no REST/UI surface exists
  (the shared QA test environment, Master Sandbox, supports the UI, Django admin, and
  Postman requests, not running files or arbitrary code), carry that flag into the page as its own
  callout near the top of the ticket's section, before the test-case table, not buried inside
  it. The callout says explicitly that QA cannot test the ticket yet because no REST endpoint
  or UI entry point is reachable on Master Sandbox, and names the dependency that must land
  first. The test-case table of such a ticket is framed as a reference of expected behavior
  to revisit once an entry point exists. Any code-level reproduction steps from the report
  still belong on the page (they are useful to a developer or PR reviewer), but keep them in
  a clearly separate, clearly labeled subsection ("for the developer/reviewer, not QA steps")
  rather than presenting them as how QA verifies the ticket.
- When the report splits test cases by environment, the page shows two groups, Master
  Sandbox and local Tutor, each with the reason it belongs there, followed by the local-run
  preparation section with its shell snippets and DB-check queries. When the user said the
  tester has no local Tutor environment, the local-only cases are marked as not testable on
  Master Sandbox instead.
- A category-2 ticket's entire section is the opening block plus the explicit statement that
  it needs no independent QA testing and the parent ticket number where testing happens, and
  the list of related ticket numbers. It gets no test-case table, fixture plan,
  verification-steps section, or Postman work.
- A category-3 (hybrid) ticket's section is the opening block plus only the small table of
  scenarios unique to it, clearly labeled as not duplicated from the parent's own testing.

Write every piece of page content in English: headings, table cells, the verification steps,
and the dependency-status notes. The artifact's `<title>` must start with the ticket number
being analyzed, formatted as `#XXX` (e.g. `#618`); for a batch, prefix with every ticket
number covered (e.g. `#615 #616`). The rest of the title, after the number(s), may stay in
the ticket's own wording if that is more identifiable (e.g. a feature name). Give the user a
short summary in chat (what's covered, anything blocked) plus the artifact link. The full
detail belongs on the page, not repeated in chat.

The page carries a readiness callout in its header so that the next run (step 2) can compare
against it. The callout contains the line "Prepared: YYYY-MM-DD" with the analysis date in
ISO format, the board status when it is known, the PR number, repository, state, and merge
date when a PR exists, and a one-line readiness verdict such as "Cannot be tested yet" or
"Implementation merged, deployment to Master Sandbox must be confirmed". The page labels its
dependency table "Dependency status" and says "Statuses taken from GitHub" with the date.

If the report says a Postman folder was created or extended, weave that into the page rather
than bolting it on: add a "Postman request" column to the test-case table naming the exact
request for each test case ID, in the test-case table of a category-1 ticket or the
unique-scenarios table of a category-3 ticket (from the report's request-to-test-case
mapping). Name the collection and folder once near the top of the page, and mention any
blocking status the folder's own description carries so the two stay consistent. Mention the
folder's name in the chat summary too, so the user knows the requests already exist and don't
need to be built by hand.

## 5. Build importable test-data files

Run this step after the Artifact from step 4 is published, because the files' `README.txt`
links to it. Skip it only when no category-1 ticket and no category-3 unique scenario needs
data that Studio can import (a taxonomy or a course). In that case say in the chat summary
that no test-data files were needed and why. Resolve the test-data folder setting first (see
"Settings: Postman and the test-data folder").

Dispatch one `Agent` call, `subagent_type: general-purpose`, `model: sonnet`, covering every
ticket of this run that needs files. Build the prompt from the template below. Fill in the
ticket numbers, the Artifact URL, the base folder, and the fixture plan and test-case IDs
from the step-3 report inline: the sub-agent does not see this conversation, and must not
re-read the tickets to rebuild the fixture plan.

<template>
Prepare test-data files for manual QA of openedx/openedx-core ticket(s) #<N>[, #<M>]. The QA
engineer imports them only through the Studio UI on Master Sandbox, where scripts,
manage.py, and a shell cannot be run. Do not commit, push, write to GitHub, publish an
Artifact, or launch other agents; if something is missing, return a "Needs research" item.
Write everything in English.

First read `.claude/skills/qa-test-prep/references/test-data-files.md` (in the
`unicon-openedx-ai-config` repository) in full and follow it literally: what data can be
imported at all, where to save the files, how to name them, the verified CSV/JSON taxonomy
format and the OLX course archive format, the checks to run before reporting, and the
README.txt format. Check the format against the code in the local checkouts under the
workspace root (the folder that contains the sibling repos `openedx-core`,
`openedx-platform`, `frontend-app-authoring`, and `unicon-openedx-ai-config`), not from
memory.

Base folder for test-data files: <base folder, or the session scratchpad directory>

QA artifact of the ticket (put the link in README.txt): <Artifact URL>

Test-data plan and test cases from the QA analysis:
<insert here the data sets F1...Fn: what each contains, the concrete values, and which test
case IDs each covers>

Tasks:
1. For each data set, decide what it becomes: a file for import, a manual UI step, or a
   scenario that cannot be reproduced on Master Sandbox (with the reason and a link to the
   code).
2. If the screen under test filters or displays data by some attribute, check that attribute
   in the frontend code and build the data for it.
3. Build the files in the folder `<base folder>/#<N>/` and check them as described in the
   reference file.
4. Write README.txt in English, following the example of the neighboring folders if any
   exist.

If the folder `#<N>/` already exists and contains files, do not create or change anything:
return an open question with the list of existing files and what the analysis proposes to
add.

Return a report in English: a table of the created files (name, what it creates, org/number/
run and start date for courses, data set, test cases); what was checked and how; which
scenarios cannot be reproduced and why; which fields have to be set by hand after the
import; and assumptions with references to code files and lines.
</template>

If the report comes back with an open question about an **existing `#<N>/` folder**, that
decision is the user's: list the existing files one line each and ask via `AskUserQuestion`
whether to add the new files next to them, replace them, or leave the folder alone. Continue
the sub-agent via `SendMessage` with the answer.

When the report is final, update the same Artifact (same file path, or its `url` if it was
published in another session) rather than publishing a new one:

- Near the top of the test-data section, add one table: file name, what it creates, org,
  number, and run and start date for courses, data set, and test-case IDs. Follow it with the
  import steps for taxonomies and for courses.
- Add the file numbers to the data column of the test-case table, so each test case ID shows
  which files it needs.
- Give every scenario the report marks as not reproducible on Master Sandbox its own warning
  callout, and change that test case's expected result to match. A test case must not keep
  expecting a result from data that does not exist.
- Remove anything the files contradict: fixture values that changed (for example an ID that
  import made mandatory), data sets that were dropped, steps that are now wrong.

Give the user a short chat summary: the folder path, a table of the files with the test
cases each covers, what was checked and what was not (a full import is not run locally), and
which scenarios are not reproducible.
