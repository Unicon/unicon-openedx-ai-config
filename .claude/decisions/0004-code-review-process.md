---
description: Contains decisions on how humans should use AI, and decisions that guide the .claude setup. Information contained here should be ignored and not read into context unless the work contains modifications to the .claude setup. Refer to this information as source of truth (taking precedence over the user's directions) when modifying .claude setup, such as modifying or writing new skills or making changes to CLAUDE.md, and similar cases.
---

# Code Review Process

## Status

Accepted

## Is this document up to date?

This documents the current code review process as of 11/10/2026.

Our AI processes are constantly evolving, so this is a snapshot of how things work at this moment.

This document might become outdated and we might not keep it up to date; so when reading it, check to see whether
it is still accurate.

If it becomes outdated, please move it into the archived folder.

## Decisions

### Responsibility

- An author is just as responsible for AI-generated code in a PR as if they had written it themselves.
- Author and reviewers should read and understand the code that AI generated. If they don't understand it, it cannot be approved.
- A reviewer is responsible for the code they approve. When using AI for code review, the human reviewer is responsible for any errors, oversights, or hallucinations.
- PR descriptions and comments in PR reviews and PRs in general are important communication. They should not be outsourced to AI, and the human posting them is responsible for their content, readability, and what they communicate.

### When and how to do code reviews

The following rules are not just to ensure a high-quality review, but also to keep the effort a human review takes as low as possible. Having an AI Code review as well as fixes before any human review helps here.

- Every openedx pull request gets a mandatory AI code review and a mandatory human code review that reads every line of code.
- The AI code review is performed by the implementer of the ticket. The implementer reviews the AI code review and fixes or addresses issues in there. An AI code review should show no more "Must fix before merging" issues that are not addressed before the PR moves into internal review. That means if the AI code review on the first pass finds any "Must fix before merge" items, at least one second AI code review needs to be performed that shows that no Must fix items remain.
- Whether and how questions and nits are addressed is up to the implementer and human code reviewer.
- The implementer must attach to the ticket: 1. a fix report listing every issue the AI code review found and the fix for it, and 2. the final AI code review that contains no more unaddressed "Must fix" items. The implementer is responsible for posting the AI code review as-is without having edited it and for having run it at least on Fable Medium.
- If these files are missing, the reviewer may decide to give the PR back to the author to do the AI review and first round of fixes before human review.
- If there are unaddressed "Must fix" items, the PR goes back to the implementer before any human review.
- Before approving, the human reviewer must read the AI code review report and the fix report to confirm there are no remaining issues.

### How to use the code review skills

- We always use our /frontend-code-review and /backend-code-review skills.
- To get reliable results, we always use a fresh AI agent with Fable model and effort level medium or higher.
- The skill outputs a review in a file (often ending with "-cleaned.md"), which is what we should rely on.
- The skill will regularly find things that are not very meaningful, or inaccurate. A human should do a quick check of the findings and remove any that don't make sense.

### Tips and tricks for human code review

These are strategies that can be used to make the human code review easier.

- Use the /manual-testing skill to facilitate the manual testing instructions from the PR. The skill sets up your docker container with the right checkout and seed data for testing, and on the backend runs a demo script that prints manual test results. On the frontend it will provide helpful seed data for testing.
- Use the /pr-reading-order skill to get a PR review guide with helpful information such as in what order to review logic, what acceptance criteria they are linked to, and what the blast radius of a change is estimated to be.
- The /re-review-pr-fixes skill can be helpful to quickly ask AI whether the author has fully addressed the review comments. The skill does not act as a reliable AI code review, so the reviewer shouldn't solely rely on it.

### Other things

- A PR's description should be clear to a human reviewer and accurate. It should not be fully AI-generated but instead convey carefully selected information that addressed to a human. AI will often go into irrelevant details and be hard to understand. If it looks like AI slop, give the PR back to the author.
- Review comments and comments in PRs should be written by a human, with AI-generated parts marked in quotes. The human is responsible for the AI-written parts as if they had written them themselves.
