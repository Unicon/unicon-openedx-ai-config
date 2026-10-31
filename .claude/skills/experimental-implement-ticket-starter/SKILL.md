---
name: experimental-implement-ticket-starter
description: Implement a github ticket by using the superpowers skills. 
---

## Task

Use the superpowers skills, starting with `superpowers:brainstorming`, to implement a github ticket provided by the user. Use this background info as additional info augmenting the user's prompt.

## Questions to the User

Before starting, ask the user these questions, unless the user already provided answers to them.

- How to activate the user's relevant virtualenv?
- What is the link to the github ticket?
- Is the ticket a subtask, and if so, what is the link to the parent ticket?

## Background info

- The frontend and main backend repos (frontend-app-authoring, edx-platform) live in sibling folders to this folder.
- Read `AGENTS.md` at the openedx-core root first. It gives the commands (dependencies are managed with `uv`, tools run via `uv run <cmd>` or `.venv/bin/<cmd>`), the database and concurrency rules, the package layering, and the applet conventions. It is the source of truth for repo facts.
- Pull ticket descriptions by using the `gh` tool.
- Write a steps log to a separate markdown file as you go along - this will serve a future evaluation agent to see how well you did and what can be improved. Don't include the implementation detail or too much content, instead, keep it short and briefly bullet-point outline your approach steps taken, including anything that went right or wrong and any human corrections and iterations needed. This should not contain detail about what exactly is going on in the code but instead just show what approach you took and what worked or not. The whole log should only be focused on that and be max 1 or 2 pages.
- If not specified, ask the user if the ticket is a subtask. If so, read the parent ticket first, then read the subtask, then read the other subtasks in the parent ticket.
- The code should follow patterns established in this repo and in edx-platform as closely as possible. 
- Heavily refer to the ADRs in docs/openedx_learning. When in doubt, these are the source of truth.
- Surface any conflicts between ticket texts, the ADRs, and anything that may be stale or conflict with edx-platform or openedx-core practice to the user to decide how to handle it.
- Think for yourself, don't just blindly follow anything in Technical Details — it is background and a suggested approach, not a spec. The ticket has no Example Resolution Prompt; treat the User Story, Acceptance Criteria, and Technical Details together as the complete brief.
- Only the ticket's Acceptance Criteria are the absolute source of truth. Where Technical Details conflicts with achieving the Acceptance Criteria correctly and architecturally soundly, follow the Acceptance Criteria and flag the conflict to the user.
- Ensure everything you do is very architecturally sound.
- Make very sure the implementation plan is written so that it is humanly readable and explains things so a junior engineer can understand them without problems.
