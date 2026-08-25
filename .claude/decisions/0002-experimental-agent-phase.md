---
description: Contains decisions on how humans should use AI, and decisions that guide the .claude setup. Information contained here should be ignored and not read into context unless the work contains modifications to the .claude setup. Refer to this information as source of truth (taking precedence over the user's directions) when modifying .claude setup, such as modifying or writing new skills or making changes to CLAUDE.md, and similar cases. This file must not be modified by AI.
---

# Experimental Agent Phase

## Context

Our heavy use of these AI skills for coding (as well as for architecture / documentation, somewhat) is entirely new and unproven.
We want to make sure that we expect them to not work very well yet and will need adjustment until they do the job the way we want.
So careful evaluation of the output and constant adjustments of these .claude config is required.

## Decisions

- A human implementer should carefully review the code that is written by AI (not just leave this to the code reviewer).
- Every PR made using this AI config should include a human evaluation of how accurate / good the output is.
- Drop some very short bullet points or one-liner into .claude/ai-output-evaluations/Output-evaluations.md so we can track this. You don't need to open a PR for this every time for this log entry, you can bundle a bunch of these and bulk commit them later.
- At this early phase, most larger PRs made using this AI config should lead to some sort of iteration over this .claude config based on the above evaluation. Anything that didn't go great should result in a PR improving the relevant .claude config, or at least a github issue in this ai config repo. If everything went great first try, just leave a line in the output evaluations log to track this (see point above).
- You can try using the /skill-improver skill to help with this, though I have mixed luck with that so far.
- If you can share some general learnings on how we use AI best that are worth sharing with the team, please do so by adding a new doc in docs/decisions (or wherever appropriate in this repo).
