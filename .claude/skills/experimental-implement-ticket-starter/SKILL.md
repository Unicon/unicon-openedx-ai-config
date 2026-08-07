---
name: experimental-implement-ticket-starter
description: Implement a github ticket by using the /spike-and-stabilize skill. If a plan document already exists (in .claude/plans/), that plan is the source of truth and the github ticket is only context; read and follow the plan rather than re-deriving the work from the ticket.
---

## Task

Implement a github ticket provided by the user, using the background info below to augment
their prompt.

Route the work through the `orchestrate` skill: it picks the orchestration plan, shows it
to the user as a diagram for approval, and enforces the review gate. The `implementation`
plan is the usual match, and its own steps invoke `spike-and-stabilize` for the coding. Go
to `spike-and-stabilize` directly only if the user declines the orchestration.

This is a top-level entry point: it asks the user questions and then hands off. It is not
something to run inside a dispatched sub-agent.

## Questions to the User

Before starting, ask the user these questions, unless the user already provided answers to them.

- How to activate the user's relevant virtualenv?
- What is the link to the github ticket?
- Is the ticket a subtask, and if so, what is the link to the parent ticket?
- Is there already a plan document? If so, where is it?

## Rules

If the user states there's already a plan, you have to read it and follow it as source of truth (the github ticket is just the context). The plan lives in .claude/plans/ . If you cannot find the plan, immediately stop your work and bring this to the user as a serious problem to be resolved first.

## Background info

- The frontend and main backend repos (frontend-app-authoring, edx-platform) live in sibling folders to this folder.
- Pull ticket descriptions by using the `gh` tool.
- Write a steps log to a separate markdown file as you go along - this will serve a future evaluation agent to see how well you did and what can be improved. Don't include the implementation detail or too much content, instead, keep it short and briefly bullet-point outline your approach steps taken, including anything that went right or wrong and any human corrections and iterations needed. This should not contain detail about what exactly is going on in the code but instead just show what approach you took and what worked or not. The whole log should only be focused on that and be max 1 or 2 pages.
- If not specified, ask the user if the ticket is a subtask. If so, read the parent ticket first, then read the subtask, then read the other subtasks in the parent ticket.
- The code should follow patterns established in this repo and in edx-platform as closely as possible. 
- Heavily refer to the ADRs in docs/openedx_learning. When in doubt, these are the source of truth.
- Surface any conflicts between ticket texts, the ADRs, and anything that may be stale or conflict with edx-platform or openedx-core practice to the user to decide how to handle it.
- Think for yourself, don't just blindly follow the implementation steps in the tickets.
- Use the example prompt in the ticket, if available, with the ticket context, as a starting point, but re-evaluate it and clarify with user if there's any questions, and change things as needed - don't stick to the example prompt blindly; instead, take it as useful hint but only the ticket ACs are absolute source of truth.
- Strictly follow the ticket ACs; if there's any problem with them, surface them to the user.
- Ensure everything you do is very architecturally sound.
- Make very sure the implementation plan is written so that it is humanly readable and explains things so a junior engineer can understand them without problems.
