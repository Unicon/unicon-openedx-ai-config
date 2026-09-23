# unicon-openedx-ai-config

Started as config for AI coding assistants working on Open edX. Has grown into the general
home for anything Unicon wants version-controlled about Open edX work that doesn't belong in
an upstream community repo: AI config, local dev setup notes, deployment notes, planning docs.

## Table of contents

- [Contents](#contents)
- [Why bother with all this?](#why-bother-with-all-this)
- [Claude Setup](#claude-setup)
- [Using it day to day](#using-it-day-to-day)

## Contents

- **`.claude/`** — Claude Code config only, symlinked into your workspace root (see Setup).
  - `CLAUDE.md` — repo conventions and working style for `openedx-core`.
  - `agents/` — `business-analyst` and `software-architect`, expert sub-agents for ticket
    review/authoring and architecture design.
  - `skills/` — `ticket-writer` (interactive ticket drafting, dispatches both agents),
    `code-review`, `spike-and-stabilize`.
  - `*-principles.md`, `architecture-overview.md`, `cbe-project-context.md`,
    `ticket-template.md` — reference docs the agents ground their judgment in.
  - `github-issues/` — local cache of GitHub issue descriptions from `openedx-core`,
    organized by workstream and epic (see its own README). GitHub is still the source of
    truth; this is a snapshot for reference so drafting doesn't re-fetch every time.
  - `settings.local.json` — personal, gitignored; recreate your own after cloning.
  - `claude-spikes/` — design spike write-ups.
  - `supporting-docs/` — sprint/ticket planning artifacts.
- **`ticketDraftingWorkflow.md`**: how the human architect and BA work with Claude to draft
  a ticket, from a blank cache file to a posted GitHub Issue.
- **`localEnvSetup.md`** — Tutor-based local dev environment setup. Only needed to actually run
  Open edX locally, not for AI context.
- **`awsDeploymentNotes.md`** — AWS deployment notes (being filled in).

## Why bother with all this?

Claude Code reads everything in `.claude/` automatically at the start of a session, so you
don't re-explain this repo's conventions, architecture, and business context every
conversation. The agents and skills package repeatable workflows (ticket writing, architecture
review) so everyone gets the same process instead of ad hoc prompting, and the reference docs
mean the AI catches repo-specific rules (layering, stable APIs) that generic use would miss.
It's plain text, so it's cheap to maintain and cheap to delete if a piece isn't pulling its
weight.

## Claude Setup

This is specifically for [Claude Code](https://claude.com/claude-code). 
[Codex](https://openai.com/blog/openai-codex/) can be used to some extent with this setup
as well, see the [Codex Setup](##Codex Setup) section, though Claude remains our teams
preferred day-to-day AI assistant. If you do not have a Unicon Claude Code account, you
will need to submit an EOR to get one as a prerequisite to using the Claude Setup in this
repo.

**1. Create your workspace directory.**

```
mkdir axim
cd axim
```

**2. Clone the Open edX repos as siblings inside it.** Fork a repo first on GitHub and clone
your fork's URL instead if you intend to push commits or open a PR from it. Otherwise a plain
clone is fine, and you can switch to a fork later without redoing anything.

```
git clone https://github.com/openedx/openedx-core.git
git clone https://github.com/openedx/openedx-platform.git
git clone https://github.com/openedx/frontend-app-authoring.git
```

`openedx-proposals` is Open edX's governance docs — reference-only, always a plain clone, no
need to fork it:

```
git clone https://github.com/openedx/openedx-proposals.git
```

**3. Clone this repo into the same workspace.** It's Unicon's own repo and the team already has
push access, so no fork needed here either.

```
git clone https://github.com/Unicon/unicon-openedx-ai-config.git
```

**4. Symlink its `.claude/` folder into your workspace root**, so Claude Code picks it up
automatically. Skip the `rm -rf` if you don't already have a `.claude` folder there.

```
rm -rf .claude
ln -s unicon-openedx-ai-config/.claude .claude
```

**5. If you need personal Claude Code permission overrides**, create
`unicon-openedx-ai-config/.claude/settings.local.json` yourself. It's gitignored, so it stays
local to you.

**6. Open your workspace in VSCode:** File > Open Folder, select the `axim` directory you just
created. Open the Claude Code panel from there — it reads `.claude/` automatically and applies
it across every repo in the workspace, with no extra setup.

## Codex Setup

This section is specifically for Codex/ChatGPT, which currently relies on our 
[Claude Setup](#claude-setup) for its functionality. Claude is currently our teams' first choice
for AI assistance and receives first order development and support in this repo, but Codex can
be used effectively with that same development effort to some extent.

The main difference is in architecture and how the different agents will automatically
understand the context of their environment. Namely, Claude will look under a `.claude`
directory for its context definitions, where Codex/ChatGPT will look under a `.agents`
directory. There are other differences to be sure, but at the time of writing this appears
to be the only major stumbling block that must be addressed for basic functionality.

**1. Symlink to .claude/ from .agents**

At this time, follow the setup instructions for Claude. Once those are complete, you
can seemingly just create a symlink named `.agents` to `<root path>/.claude` in your working
directory:

```
ln -s .agents <root path>/.claude
```

Our Claude Skills, agents, and so forth are generic enough that Codex seems to read them in and
perform the same functionality with minimal concern. Again, though, this is only proven minimally
at the time of this writing, namely the code review functionality, and has not been tested with
the other various tasks.

## Using it day to day

- **Writing or reviewing a ticket:** follow [`ticketDraftingWorkflow.md`](ticketDraftingWorkflow.md).
  The `ticket-writer` skill runs each step, dispatching the business-analyst and
  software-architect agents and asking you the questions that actually change the ticket.
- **Architecture or design question:** just ask; the software-architect agent gets pulled in
  automatically when it's relevant.
- **Implementing a non-trivial change:** the `spike-and-stabilize` skill — survey the code, get
  one combined clarify-and-plan approval, write a thin throwaway spike, then stabilize it
  (types, tests, checks, review). Skip it for trivial changes like renames or typo fixes.
- **Reviewing a diff or PR:** the `frontend-code-review` or `backend-code-review` skill as appropriate.
- **Everything else** (`CLAUDE.md`, the principles docs) loads as background context
  automatically. You never invoke it directly, it's just informing every response.
