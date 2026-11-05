# unicon-openedx-ai-config

Started as config for AI coding assistants working on Open edX. Has grown into the general
home for anything Unicon wants version-controlled about Open edX work that doesn't belong in
an upstream community repo: AI config, local dev setup notes, deployment notes, planning docs.

## Table of contents

- [Contents](#contents)
- [Why bother with all this?](#why-bother-with-all-this)
- [Claude Setup](#claude-setup)
- [Using Claude Code and Codex together](#using-claude-code-and-codex-together)
- [AI Code Reviews](#ai-code-reviews)
- [Using it day to day](#using-it-day-to-day)
- [License](#license)

## Contents

- **`.claude/`** — Claude Code config only, symlinked into your workspace root (see Setup).
  - `CLAUDE.md` — repo conventions and working style for `openedx-core`.
  - `agents/` — `business-analyst` and `software-architect`, expert sub-agents for ticket
    review/authoring and architecture design.
  - `skills/` — `ticket-writer` (interactive ticket drafting, dispatches both agents),
    `code-review`, and two QA skills: `qa-test-prep` (test cases, Postman requests, and
    importable test data for a ticket) and `github-report-creation` (a GitHub-ready test
    report from QA results).
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

**1. Create your workspace directory.** If you already have Open edX set up, skip steps 1 and
2 and use the folder that contains your Open edX repositories as subfolders as your workspace.

```
mkdir openedx
cd openedx
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

**6. Open your workspace in VSCode:** File > Open Folder, select your workspace directory. Open the Claude Code panel from there — it reads `.claude/` automatically and applies
it across every repo in the workspace, with no extra setup.

**7. Install the superpowers plugin for Claude Code.** Implementation work in this setup goes
through the superpowers skills, so it needs the plugin. See
[obra/superpowers](https://github.com/obra/superpowers) for installation instructions.

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

## Using Claude Code and Codex together

[T3 Code](https://t3.codes/) is a desktop app that runs Claude Code and Codex agents side by
side, using the Claude and ChatGPT subscriptions you already have. T3 Code calls each agent
service it connects to a provider. An agent running in T3 Code can delegate a task to an agent
from the other provider. For example, a Claude agent reviewing a change can hand that change to
a GPT agent and check the GPT agent's findings when they come back.

T3 Code is optional, but recommended for code reviews. [AI Code Reviews](#ai-code-reviews)
explains why.

**1. Install T3 Code.** On macOS, run:

```
brew install --cask t3-code
```

You can also download the app from [t3.codes](https://t3.codes/). T3 Code's
[install guide](https://github.com/pingdotgg/t3code/blob/main/docs/user/install.md) covers
Windows and Linux.

**2. Add your Claude Code subscription as a provider.** T3 Code runs the Claude Code CLI you
installed for the [Claude Setup](#claude-setup) and reuses that CLI's login. If you have not
signed in to the CLI yet, run `claude auth login`. Then, in T3 Code, open
**Settings → Providers** and enable Claude.

**3. Add your Codex subscription as a provider.** In **Settings → Providers**, enable Codex and
click **Connect with ChatGPT**. If you already use the Codex CLI, running `codex login` on the
same machine also works.

**4. Update any provider CLI that T3 Code flags.** Delegating between providers needs a recent
version of both CLIs. If **Settings → Providers** flags a provider's version as too old, update
that CLI.

**5. Open your workspace in T3 Code.** Open the `openedx` workspace directory as a project, or
whatever parent folder you have for your Open edX setup that contains `openedx-core` or
`frontend-app-authoring` as subfolders. Agents then start there and read the symlinked
`.claude/` folder, the same way the VS Code panel does.

## AI Code Reviews

Run `/backend-code-review` for a backend change and `/frontend-code-review` for a frontend
change. Both skills build on the `code-review-openedx` skill. They write every file they
produce, including the final review, to a `pr-reviews/` folder in the session's working
directory.

Where you run the skill decides whether the review includes an adversarial review from a
ChatGPT model. An adversarial review tries to break the change: it looks for an input or a
sequence of events that makes the code fail, and for claims in the change that are false.

- **In Claude Code**, either the CLI or the VS Code panel, the review runs Claude agents only.
  Claude Code cannot start a ChatGPT agent, so the review skips that step and tells you it did.
- **In a Claude thread in T3 Code**, meaning a T3 Code conversation running a Claude model,
  **with both the Claude and Codex providers enabled**, the review also hands the change to a
  GPT-6.1-Sol agent, without any extra prompting from you. A different model tends to spot
  different problems. The Claude session checks each of the GPT agent's findings against the
  code before adding it to the final review, the same way it checks its own sub-agents'
  findings.

T3 Code is not required, but run your reviews in it when you can, or find another way to add an
adversarial review from a ChatGPT model, because the second model should raise the quality of
the review.

## Using it day to day

- **Writing or reviewing a ticket:** follow [`ticketDraftingWorkflow.md`](ticketDraftingWorkflow.md).
  The `ticket-writer` skill runs each step, dispatching the business-analyst and
  software-architect agents and asking you the questions that actually change the ticket.
- **Architecture or design question:** just ask; the software-architect agent gets pulled in
  automatically when it's relevant.
- **Implementing a non-trivial change:** the superpowers skills: brainstorm the design, write a
  plan, then implement it test-first. Claude asks you to install superpowers if it is
  missing. Skip this for trivial changes like renames or typo fixes.
- **Reviewing a diff or PR:** the `frontend-code-review` or `backend-code-review` skill as appropriate.
  Run it in T3 Code to include an adversarial review from a ChatGPT model; see
  [AI Code Reviews](#ai-code-reviews). For a frontend PR, `frontend-code-review` first hands you a Markdown file with the PR's component
  tree (edited and new components in red, notes on what changed), made by the `pr-component-tree`
  skill, which you can also run on its own. To know where to start reading a long PR, the
  `pr-reading-order` skill draws an SVG of its main threads of execution, top to bottom, with the
  acceptance criteria each piece implements beside it and each box colored by blast radius.
- **Preparing QA for a ticket:** the `qa-test-prep` skill. It reads the ticket and its
  dependencies, checks whether the ticket is ready for QA, and publishes an Artifact with the
  test cases and verification steps. When Postman is set up, it also builds the matching
  requests in your Postman collection, and it builds Studio-importable test-data files. It
  needs the GitHub MCP server. On first use it asks for your Postman workspace, collection,
  and environment and for a test-data folder, and remembers the answers.
- **Writing a test report:** the `github-report-creation` skill turns your QA results (a
  CSV/XLSX export or notes in chat, or the results of a `qa-test-prep` session) into an
  English, GitHub-ready report that you post to the issue yourself.
- **Everything else** (`CLAUDE.md`, the principles docs) loads as background context
  automatically. You never invoke it directly, it's just informing every response.

## License

Copyright 2026 Unicon, Inc.

Except where otherwise noted, material in this repository is licensed under the
[Apache License 2.0](LICENSE) to the extent Unicon holds the applicable rights.

Most of this repo was written during Unicon's work for Axim Collaborative on competency-based
education in Open edX. The `.claude/github-issues/` folder reproduces issue text from
`openedx/openedx-core` and `openedx/openedx-platform` for reference. The upstream issues are
the source of truth for that text. Reproduced third-party material remains subject to its
applicable terms and is not relicensed by this repository.
