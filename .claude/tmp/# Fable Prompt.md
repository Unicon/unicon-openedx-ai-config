# Fable Prompt

Task:
Write missing tickets from .claude/supporting-docs/Axim 2.12 Github Issues - Sheet2.csv .
That file lists the basic requirements.
Skip any tickets that already exist, even as placeholders.

What tickets already exist:
- any ticket in .claude/supporting-docs/Axim 2.12 Github Issues - Sheet2.csv
- tickets UC ID 6.1, 6.2, 6.3 . They are defined in:
  1. uc6-ticket-1-create-competency-rule-profile-endpoint.fable.md
  2. uc6-ticket-2-update-delete-competency-rule-profile-endpoint.fable.md
  3. uc6-ticket-3-get-competency-rule-profile-endpoint.fable.md
  Note that these tickets are very tentative and may change substantially based on the open questions attached to them.
- Any tickets on the project board https://github.com/orgs/openedx/projects/100 - use cheap Sonnet subagent to read them using gh and report. If the board or its tickets are not accessible, stop running immediately and await instructions from the user.

Knowledge:
- An overview over the CBE effort tickets can be found in .claude/supporting-docs, including the initial ticket requirements.
- .claude/supporting-docs/Markdown Github Issues.md outlines tickets that are already planned and will be done before UC ID 6. So for example the data models should already be in place.
- The .claude folder has different .md files directly inside - like `.claude-architecture-overview.md` - which explain how the architecture works.

Sub-agent usage:
- Any context-heavy task that does not need an extremely heavy model should be deferred to a sub-agent that uses a cheaper "Sonnet" model; that sub-agent can report back.
- Investigations into the codebases should be done by cheaper "Sonnet" model sub-agents - with specific questions and narrow things to look at so they don't get lost in the large codebases.
- Don't use skills or sub-agents that are already defined in the .claude folder - I want you to look at this from a fresh perspective.

Ticket format:
Tickets should follow the format outlined in .claude/ticket-template.md

Codebases:
- Mainly the current codebase (openedx-core)
- If necessary sub-agents with cheaper models can look at code or possible changes needed in ../edx-platform - but only with narrow questions so they don't read all the repo as context, it's too large.

Output: Create 3 markdown files, one for each ticket.