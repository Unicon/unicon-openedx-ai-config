---
name: re-review-pr-fixes
description: Invoked manually to check whether a PR author fixed everything brought up in review comments in the PR.
---

Assume the role of the software-architect agent (.claude/agents/). Look over the PR the user linked and read all reviews and comments. Go to the linked issues and read all acceptance criteria.
Tell me:
- whether every review comment was satisfyingly fixed
- whether the changes that occurred after the last round of reviews are architecturally solid and acceptable
- whether the changes broke anything that was previously working in the PR
- whether all acceptance criteria are met

Run /clean-up-text on your response before you give it to me.