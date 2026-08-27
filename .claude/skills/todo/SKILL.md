---
name: todo
description: Read and update the developer's personal one-screen progress sheet at .claude/my-todo.md, and help them decide what to work on next. Covers priority calls, three pomodoro-sized to-dos a day, cutting big work into day-sized pieces, folding a brain dump into the sheet, starting and ending the day, tracking the developer's own hands-on work alongside the Claude sessions, which the bundled agents.py detector refreshes, and moving finished items to the log. Manual only, invoked when the developer types /todo and at no other time.
disable-model-invocation: true
---

# /todo, the personal progress sheet

This developer runs many Claude agents at once and loses the overview. Plenty of their work
never touches an agent at all, and that work belongs here just as much. This skill keeps one
small file that answers four questions at a glance: what is in progress, what matters today,
what is next, and what is waiting. It also does the two jobs the developer cannot
do for themselves in the moment: it calls the priority, and it keeps the day's to-dos small
enough to actually finish.

Being short is the feature. A sheet that no longer fits on one screen has failed at its
job.

## Run only when asked

The developer invokes this skill by typing `/todo`. Never start it on your own, and never
touch the files below outside a `/todo` invocation, even if a task looks related.

## The four files

- `.claude/my-todo.md` is the sheet. Everything that matters now lives here.
- `.claude/my-todo-log.md` is the append-only record of finished items.
- `.claude/my-todo-someday.md` is the overflow dump for backlog items that do not fit on
  the sheet. Nothing in it is scheduled or ordered.
- `.claude/my-todo-archive.md` is an append-only daily snapshot of the sheet, kept purely
  as a history the developer can scroll back through. Nothing reads from it.

All four are gitignored on purpose, so search tools that respect gitignore may not list
them. Always open them by their exact path (`cat .claude/my-todo.md`), never by searching.
`.claude/` is symlinked into the Open edX repositories, so this is the same single sheet
whichever repository the session started in.

These files are the developer's personal notes, not AI configuration. The rule in
`CLAUDE.md` about not modifying `.claude/` without being asked is satisfied by the
developer typing `/todo`, which is the explicit ask. It covers these four files and
nothing else: never edit any other file under `.claude/` from this skill.

## Archiving the sheet once a day

Before the sheet's content changes for a new day, append a copy of it as it stood at the
end of the previous day to `.claude/my-todo-archive.md`, under a heading with that day's
date. This is the only write to the archive file; nothing else in this skill ever reads it
or trims it.

- Do this exactly once per calendar day, the first time a `/todo` invocation notices the
  sheet's `updated:` stamp is from an earlier day and is about to rewrite it. Compare
  against the real date from `date "+%a %d %b, %H:%M"`, never a guess.
- Append, never overwrite: `## <old updated: date>` as a heading, then the sheet's content
  verbatim, then a blank line before the next entry.
- If the archive file does not exist yet, create it with the Write tool.
- Skip the append on the same day the sheet was already archived; check the archive's last
  heading before writing to avoid a duplicate entry.

## The shape of the sheet

Four sections, always in this order, always present even when empty. Do not add, rename,
reorder, or nest sections, and do not add a section for finished items: those go to the log
file.

```markdown
# My To-Do          updated: Thu 27 Aug, 10:18

## ▶️ DO THIS NEXT
Review PR #674. Two agents below are waiting on it, and it is today's must-land to-do.

## 🎯 TODAY · ends 15:30 · 2h meetings
1. [x] Draft ticket 5.10c — 25 min
2. [ ] Review PR #674 — 30 min  ← must land today
3. [ ] Grading spike: get one test case green — 45 min

## 🔄 IN FLIGHT
| what                   | where                 | state         |
|------------------------|-----------------------|---------------|
| 🤖 ticket 5.10c        | ai-config             | NEEDS ME      |
| 🤖 grading spike       | wt-640-cbe-foundation | agent working |
| Review Sarah's PR #712 | core                  | me working    |
| PR #674 CI             | core                  | waiting on CI |

## 📋 BACKLOG · most important at the top
- NOW · Answer the agent's scope question on ticket 5.10c
- PLAN · Grading spike: the remaining two test cases
- PLAN · Write up the stacked-PR tool experiment
- CHORE · Reply to the CI failure email
- MAYBE · Clean up the import-linter layering rule

NOW = urgent and important · PLAN = important, not urgent · CHORE = urgent but minor · MAYBE = probably drop
🤖 = a Claude session · everything else is your own hands
Tell Claude `/todo` plus whatever changed, and Claude tidies this file.
```

Size limits, so the sheet stays glanceable:

| Section | Limit |
| --- | --- |
| `DO THIS NEXT` | Exactly one item, one or two short sentences, and it says why. |
| `TODAY` | Three to-dos, or two on a heavily booked day. Each carries an estimate. |
| `IN FLIGHT` | At most six rows, three columns, one line each. |
| `BACKLOG` | At most ten lines. Everything past ten moves to `my-todo-someday.md`. |
| Whole file | At most 45 lines. |

The `TODAY` heading carries the day's shape when you know it: the time the developer stops,
and the hours already committed to meetings. Leave out whichever you have not been told.

When something has to come off the sheet to stay inside a limit, move it to the backlog,
the someday file, or the log rather than deleting it, and say in chat which item you moved
and where it went.

The sheet holds everything the developer is working on, not only code and not only work an
agent touches: reviews, meetings, answers owed to people, and admin belong here alongside
tickets and pull requests.

## Priority: four tags and one order

Every backlog line starts with one of four tags. They are the Eisenhower quadrants named
by what to do about them, so the sheet needs no legend to read.

| Tag | Urgent? | Important? | What it means in practice |
| --- | --- | --- | --- |
| `NOW` | Yes | Yes | Today, or it hurts. A blocked agent, a blocked colleague, a real deadline. |
| `PLAN` | No | Yes | The work that actually moves things forward. It has to become a daily to-do soon, or it never happens. |
| `CHORE` | Yes | No | Small and loud. Do it fast, batch it, or hand it off. Never let it eat a morning. |
| `MAYBE` | No | No | A candidate for deletion. Ask about dropping it when the backlog is full. |

**The order of the list is the priority.** The most important item is the top line. To
change a priority, move the line; never write priority numbers or scores, because they need
bookkeeping the developer will not keep up. Sort `NOW` first, then `PLAN`, then `CHORE`,
then `MAYBE`, and order within each group by importance.

Two consequences to enforce every time you rewrite the sheet:

- Nothing tagged `MAYBE` ever becomes a daily to-do or `DO THIS NEXT`. If it deserves to be
  worked on, it is not a `MAYBE`; retag it and say that you did.
- A `PLAN` item that has sat in the backlog untouched for a week is the most common way this
  system fails. Say so when you notice it, and offer to make its first slice tomorrow's
  must-land to-do.

## Daily to-dos: three pomodoros, honestly estimated

Three to-dos a day, each one sized to fit a single 45-minute pomodoro. That is the whole
rule. There is no budget arithmetic and no padding factor.

- You do the estimating, not the developer. Put the number on the line as `— 30 min`, and
  estimate what the work will really cost them, including the time spent supervising an
  agent rather than the time it would take if nothing went wrong.
- An item you honestly estimate above 45 minutes does not go on `TODAY`. Cut it into slices
  first, per the next section, and put one slice on the sheet.
- Never shade an estimate down to make something fit. The item you rounded from an hour down
  to 45 minutes is the item that eats the day.
- When more than half the day is taken by meetings and other obligations, drop to two
  to-dos. On a six-hour day, that means three hours or more of meetings.
- If even the to-dos you picked do not fit the free hours left, cut to what fits and say
  plainly what came off.

The to-dos are the top of the priority order: the most important and most urgent things on
the sheet. Anything beyond that comes off the backlog in the order it already has. Never
reach past a `NOW` item for something more appealing, and never promote a `MAYBE`.

One to-do a day may carry the suffix `← must land today`. Use it for the thing that would
make the day a success on its own, and pick it before the others.

If the developer wants a fourth to-do, push back once: three finished days in a row beat
one ambitious day. If they still want it, add it as a final line reading
`stretch: <item> — <estimate>`, and say plainly that the stretch line does not count toward
finishing the day. Never let a stretch item be the must-land to-do.

## Cutting work into day-sized pieces

Any item estimated over 45 minutes gets cut in the conversation, before you write anything
to the sheet.

- A good slice has a result the developer can check when it is done. "Grading spike gets one
  test case green" is a slice. "Start the grading spike" is not, because nothing tells them
  it is finished.
- Slice through the work, not across its phases. Do not write "research, then write, then
  test" as three to-dos; one narrow end-to-end piece beats three phases of a wide one.
- Keep the big item in the backlog as one line and put only the next slice on `TODAY`. The
  sheet never holds a task tree.
- Name at most two or three slices out loud. The rest are not knowable yet, and guessing at
  them is how a day gets overfilled.
- If the developer cannot say what the first slice is, the first slice is a 20-minute look at
  the code or the ticket to find out. Write that as the to-do.

## The sheet covers work you do by hand too

Most of what the developer does never involves an agent: reading a ticket, sitting in a
meeting, reviewing a colleague's pull request, writing a document, owing someone an answer.
All of it belongs on the sheet, and all of it competes for the same three daily to-dos.

- `TODAY` and `BACKLOG` never distinguish AI work from hand work. A to-do is a to-do, and an
  hour spent reviewing someone else's branch costs the day exactly what an hour of your own
  feature work costs it.
- `IN FLIGHT` holds anything genuinely in progress, whoever is doing it. `me working` is the
  developer at the keyboard; `agent working` is a Claude session.
- Every row driven by a Claude session starts its `what` cell with `🤖`. Rows without the
  robot are the developer's own. This is what tells the detector which rows it owns, so the
  marker is not decoration: put it on every agent row and on no other row.
- A row does not need a repository. `where` is wherever the work lives: `core`, `ai-config`,
  `Jira 5.10c`, `email`, `a Google Doc`, or `-` when it lives nowhere in particular.

## Keeping IN FLIGHT true

Run this at the start of every `/todo` invocation, before you print or change anything:

```
python3 .claude/skills/todo/agents.py
```

It prints one line per live Claude Code session: directory, git branch, session name, state,
how long it has been idle, its pid, and a label. It reads the session registry in
`~/.claude/sessions/`, the modification time of each session's transcript, one `ps` pass, and
exactly one line of each conversation: its first human prompt, cut to 60 characters. That
opening prompt is the closest thing to a chat name that exists on disk, because the title the
editor shows in its own interface is not persisted anywhere. Nothing else from another
conversation is read, and sub-agents are ignored, which is what the developer wants.

Translate its states into the sheet's words:

| The script says | The sheet says | Because |
| --- | --- | --- |
| `busy` | `agent working` | It wrote to its transcript in the last two minutes, or it is running a command right now. |
| `needs-you` | `NEEDS ME` | Its turn ended, so it is sitting there waiting for the developer. |
| `never-used` | nothing | The session is open but was never given a prompt, so it is an empty tab, not work. Keep it off the sheet. |
| `dismissed` | nothing | The developer already said this one is finished and it has been quiet since. Keep it off the sheet. |

Rules for using it:

- The script owns exactly the rows whose `what` starts with `🤖`, and no others. It may add,
  update, or remove those. Every row without the robot is something the developer told you
  about, so never rewrite its state from the script, even when its `where` matches a
  directory the script reported.
- Stay inside the directories already on the sheet. A session somewhere else is not part of
  the developer's overview; if one outside the sheet is `busy`, say so as a count in one
  chat line and do not add a row.
- Leave `stale` and `never-used` sessions off the sheet entirely. Idle for more than eight
  hours means an abandoned editor tab, and never used means an empty one. Neither is work in
  progress. Report them as a count in one line: "Six old sessions are still open in
  openedx-core, idle since yesterday, and three more were never used."
- Keep `not started` for a task the developer named but has not begun. It is a fact about
  their work, not something the detector ever produces.
- Build the `where` value from the last part of the directory, shortened to whatever the
  developer will recognize: `openedx-core` becomes `core`, `unicon-openedx-ai-config` becomes
  `ai-config`, and a worktree like `wt-640-cbe-foundation` stays as it is. Add the branch
  after a slash only when the directory name does not say what the work is, and keep the
  whole cell under about 26 characters.
- When the six-row limit bites, keep `NEEDS ME` rows first, then `agent working`, and say
  which rows did not fit.
- When two live sessions sit in the same directory, the `where` cell carries the session
  name's last two characters so the rows can be told apart: `branch-viz-1e`, `branch-viz-ad`.
- The `what` cell comes from the label the script prints, shortened to about 30 characters
  while keeping the part the developer will recognize: "Read @DESIGN.md and
  @IMPLEMENTATION_PLAN.md . You are the or" becomes `🤖 Read DESIGN.md, orchestrate`. Never
  leave a row reading `(what is this?)`.
- The label is the conversation's opening prompt, not the name the editor displays, so it can
  be stale for a session that moved on to something else. When the developer corrects a
  label, keep their words: theirs are better than the prompt they typed an hour ago.
- When the label is `-`, the session has nothing to read yet. Use the branch instead, and
  `🤖 (ask it)` when the branch is the repository default and says nothing either.
- The full session name, `dependent-branch-visualization-1e`, is the only handle that
  identifies a session anywhere else: it is what `ListAgents` prints and what `SendMessage`
  addresses. Keep the sheet cell short and give the full name in your chat line instead, so
  the developer can match the row to a session.
- When the developer says they have no idea what a session is, offer to ask the session
  itself: `SendMessage` to its full name with one question, "In one line: what are you
  working on, and what do you need from Jesper?" Get approval first, because the message
  wakes that session and shows up in its conversation. Never message a `busy` session, which
  is mid-task, and use whatever comes back as the `what` value.
- Asking makes that session busy for a minute or two while it answers, so its state on the
  next run says `agent working` because of your question rather than because of real work.
  Say so rather than reporting it as progress.
- If the script fails or prints nothing, say so in one line and leave the table as it was.
  Never guess a state.

### When the developer says a session is finished

A session stays open in the editor long after its work is done, so it sits there reading
`NEEDS ME` forever. Only the developer can say it is finished: `needs-you` means the turn
ended, which usually means something came back for them to look at. Never decide on your own
that a session is done.

When they do say it, take three steps:

1. Append a line to the log in exactly this shape, with the time as well as the date, because
   the script parses it:
   `- 2026-08-27 11:20 — Competency taxonomy accessor tests (session wt-640-cbe-foundation-16 done)`
2. Take the row off the sheet.
3. Say nothing more about it. The script reports that session as `dismissed` from then on, so
   it will not reappear on the next `/todo`.

If the developer picks the work back up in that same session, the script sees activity newer
than the log line and reports the session's real state again, so the row comes back on its
own. Suggest closing the editor tab as well, since a closed session leaves the registry and
stops being counted at all.

The state words in the table below are the only ones allowed anywhere in the `state` column.
Uppercase is reserved for the one state where the developer is the blocker, so their own eye
finds it first.

| State | Means |
| --- | --- |
| `NEEDS ME` | An agent or a person is blocked until the developer answers or decides. |
| `agent working` | A Claude agent is running and nothing is needed from the developer. |
| `me working` | The developer is doing this one by hand right now. No agent involved. |
| `waiting on CI` | A build or test run has to finish. |
| `waiting on <name>` | Another person owes an answer or a review. |
| `stuck` | It failed or went nowhere. Add three to five words on why. |
| `not started` | Claimed a slot but no work has begun. |

If a situation fits none of these, use the closest one and ask the developer about it in your
closing line. Never invent a new state word.

## How to write the entries

- Plain words a non-engineer would follow. Write "Fix the import-linter layering rule", not
  "fix `.importlinter`".
- One line per item. No nesting, no sub-bullets, no parenthetical asides stacked up.
- About twelve words per item, and never more than one line on screen.
- Name the thing so it can be found again: "PR #674 (grading leaf status)", not "the PR".
- No secrets, no client-confidential detail, and no long explanations. This is a pointer to
  work, not a record of it.

## What to do for each kind of request

**`/todo` on its own.** Refresh `IN FLIGHT` from the detector, print the sheet, then add
one sentence saying what to do next and why. Change nothing else. If the `updated:` stamp is
from an earlier day, archive the sheet per *Archiving the sheet once a day*, then say so
and offer to start the day.

**`/todo` followed by a brain dump.** This is the main path. Read the sheet, run the
detector, get the real date and time from `date "+%a %d %b, %H:%M"`, archive the sheet per
*Archiving the sheet once a day* if its `updated:` stamp is from an earlier day, fold in
what the developer said, retag and reorder the backlog, rewrite the whole file, append
anything finished to the log, and print the new sheet. Keep the developer's own wording for
an item wherever it fits the limits.

**"I have three hours of meetings today."** Put the hours in the `TODAY` heading, and if
they take more than half the day, drop to two to-dos and say which one came off.

**"What next?", "I'm lost", "where was I?"** Pick one item and name the first physical
action: "Open PR #674 and read the two review comments." Choose the must-land to-do first,
then anything that unblocks a waiting agent or another person, then the top `NOW`. Never
choose a `MAYBE`. Set `DO THIS NEXT` to it.

**"What is most important?"** Answer with the top of the order and the reason in one
sentence, and name what it beats: "PR #674, because two agents are blocked on it. The
stacked-PR writeup can wait, nobody is waiting on it."

**"Break this down."** Run the slicing rules above. Return two or three slices with
estimates, put the first on `TODAY` if it fits, and leave the parent in the backlog as one
line.

**"Can I finish X today?"** Compare your honest estimate against the free hours that are
left today, and give a yes or a no. If the answer is no, say which slice of X does fit.

**"What are my agents doing?"** Run the detector and report what changed, in at most four
lines: who needs the developer, who is working, and how many stale sessions are cluttering
things up.

**"What is the state of my pull requests?"** `gh pr list --author @me --state open` and, for
a specific one, `gh pr checks <number>`. Update `waiting on CI` rows from that, and nothing
else.

**"Start my day."** Roll the day over: archive the sheet as it stood yesterday per
*Archiving the sheet once a day*, append every ticked to-do to the log, move unfinished
ones back to the top of the backlog, clear `TODAY`, then ask at most three short questions,
one of which is how many hours of meetings there are. Pick the new to-dos off the top of the
priority order, size each to a pomodoro, mark the must-land one, propose `DO THIS NEXT`, and
print the sheet.

**"End my day", "wrap up."** Append finished items to the log, make sure every row in
`IN FLIGHT` says what it is waiting on overnight, and set `DO THIS NEXT` to tomorrow's
first action so the next morning starts without thinking. Say in one line how the day went
against its to-dos, and if the estimates were off again, say by how much.

**"Done with X."** Tick it if it is a `TODAY` to-do, append it to the log with today's date,
and remove it from `IN FLIGHT` and the backlog.

**"Park X."** Move it into the backlog with a tag, or to `my-todo-someday.md` if the backlog
is full.

**"That session is finished", "I'm done with that one."** Follow the three steps under *When
the developer says a session is finished*. This is the only way an agent row leaves the sheet
while its session is still open.

## Push back, do not just record

The developer asked for this. A silent secretary is no use to them, so say the uncomfortable
thing, once, in one or two plain sentences.

- Working on the wrong thing: "Stop that and take PR #674 first. Two agents are blocked
  behind it, and what you are on is a `CHORE`."
- A day that will not fit: "Those four are more than three pomodoros, and two of them are
  over 45 minutes each. Pick two, and I will slice the rest."
- Half the day gone, nothing ticked: compare the clock from `date` against the end-of-day
  time in the `TODAY` heading. If more than half the free time is gone and nothing is ticked,
  say so and propose cutting the day down to the must-land to-do alone.
- The must-land to-do at risk near the end of the day: "You have 90 minutes left and PR #674
  is untouched. Do that one, and let the spike run overnight."
- A to-do that keeps rolling over: if the same one comes back unfinished for a third day, say
  so and offer to slice it smaller, because the size is the problem, not the day.
- Agents piling up: if the detector shows three or more sessions with `NEEDS ME`, say it
  plainly. Blocked agents are the most expensive thing on the sheet, because nothing behind
  them moves.
- A backlog full of `MAYBE`: offer to delete them, by name, and wait for a yes.

Say at most one of these per response. Do not stack three of them in one reply, and do not
repeat a nudge the developer has already answered.

## Rules for editing

- Never drop something the developer told you about without asking. When you cannot tell
  whether an item is finished, leave it in place and ask one question at the end.
- Rewrite the whole file each time rather than patching around the existing text. The file is
  small, and a clean rewrite keeps the section order, the priority sort, and the limits
  intact.
- This shell has `noclobber` set, so `cat > file` fails when the file exists. Write the sheet
  with the Write tool, or with `cat >| file`.
- Take the `updated:` stamp from `date` output. Never guess the time.
- Append to the log one line per item, newest at the bottom. A finished to-do carries the
  date: `- 2026-08-27 — Draft ticket 5.10c (ai-config)`. A finished Claude session carries the
  time too, and the session's full name, because `agents.py` parses that line:
  `- 2026-08-27 11:20 — Competency taxonomy accessor tests (session wt-640-cbe-foundation-16 done)`.
- Never dispatch a sub-agent from this skill. Reading and rewriting a 45-line file is cheaper
  inline, and a dispatch would lose the conversation the sheet is built from.
- Close with at most four short lines in chat: what changed, the one nudge if you have one,
  and the one question if you have one. The printed sheet is the report; do not narrate it.

## When the sheet does not exist yet

Create it from the template above, run the detector to fill `IN FLIGHT`, and ask at most
three questions for the rest: what has to happen today, who or what you are waiting on, and
how many hours of meetings there are. Pick the to-dos off the top of the priority order, size
each to a pomodoro, print the sheet, and stop.
