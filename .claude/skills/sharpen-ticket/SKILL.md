---
name: sharpen-ticket
description: "Invoke only when the user asks for it by name (\"/sharpen-ticket\", \"sharpen this ticket\"). Do not select it for general requests to clean up, tighten, de-bloat, review, or improve a ticket: those are clean-up-ticket, and requirements work is ticket-writer. Sharpens an already-scoped ticket onto its outcome by making the User Story prominent and authoritative, emptying the Description to load-bearing non-technical bullets, demoting Technical Details to explicitly non-authoritative background, and dropping the Example Resolution Prompt unless it carries instruction for an AI implementer found nowhere else. Fetches with gh, writes a paste-ready local .md, never posts to the tracker."
---

# Sharpen a ticket onto its outcome

Take an already-scoped ticket and make the outcome impossible to miss: one prominent User
Story, acceptance criteria that hold the contract, and everything else demoted to its real
authority. The output is a paste-ready local `.md` file for the human to review.

## Invocation gate

Run this **only** when the user names it. If a request is a general "clean this up",
"tighten this", or "review this ticket", that is `clean-up-ticket`, not this skill. Say so
and stop rather than sharpening something the user did not ask to be sharpened.

The two skills serve different purposes and do not compose. Never run `clean-up-ticket` as a
step of this pipeline, and never invoke this one from there.

## What this skill is, and is not

- **It is** a fixed pipeline that re-seats existing content into the right authority level,
  then verifies it did so without changing the ticket's meaning.
- **It is not** requirements discovery or design work. It does not relitigate scope, add
  requirements, or reopen a settled approach. If the outcome itself is unclear, that is
  `ticket-writer`; hand off rather than inventing intent.
- **It is not** an over-specification hunt. This is a deliberate local exception: the
  template holds Technical Details to intent altitude and `clean-up-ticket` enforces that,
  but within *this* pipeline, Technical Details left carrying more implementation detail
  than strictly needed is acceptable and is not a finding. Relocating technical content out
  of the Description bloats the section by design, and the section is advisory, so the
  bloat is cheap. Do not trim it, and do not carry this exception into any other skill.
- **It does not touch the Acceptance Criteria.** They pass through untouched.
- **Advisory.** Writes a **new** local file. Never overwrite the source, and never
  `gh issue edit` or `gh issue comment` unless the user explicitly asks and approves the
  wording.

## Read first

`.claude/ticket-template.md` for the canonical section shape and the authority hierarchy
this skill enforces.

## Model and context

You run the pipeline and own every judgment in it. Per the Delegation rule in `CLAUDE.md`:
push context-heavy fetching down (a non-GitHub tracker or URL to a Sonnet sub-agent,
code-location lookups to a Haiku `Explore`) and pass `model` explicitly on every dispatch.
Never read a neighbor repo (`openedx-platform`, `frontend-app-authoring`) into context to
check a claim; use its overview doc or a narrow Sonnet sub-agent. The evaluator agents in
steps 5 and 6 have no Agent tool: they return "Needs research" items, and you fulfill those
and continue them with `SendMessage`.

## The sharpened shape

| Section | Authority | Sharpened form |
| --- | --- | --- |
| **User Story** | source of truth | one "As a &lt;role&gt;, I want &lt;capability&gt;, so that &lt;outcome&gt;", first thing in the ticket |
| **Acceptance Criteria** | source of truth | copied through verbatim; the contract the implementer must satisfy |
| **Description** | understanding only | terse one-sentence bullets, or omitted; zero technical or implementation content |
| **Technical Details** | background and suggestion | opens with the disclaimer below; extra detail tolerated |
| **Context**, **Files to create and modify** | pointers | left as-is |
| **Example Resolution Prompt** | none | omitted, unless it carries instruction for an AI implementer that exists nowhere else |

Technical Details opens with exactly this line:

> These notes are background and suggestion, not specification. The User Story and
> Acceptance Criteria are the source of truth; depart from what follows where a better
> approach exists.

Advisory does not mean scattered. Technical content still has one canonical home in
Technical Details rather than being restated across the Files table and the Description.

## 1. Intake

Pasted text: use it. A file path: read it. A GitHub issue: `gh issue view <n> --repo
<owner/repo> --json title,body,comments,labels`, and read the comments, a maintainer may
have already corrected something. Keep the original verbatim in context; step 6 needs it.

## 2. Confirm the User Story (blocking)

The human owns the outcome. Ask with `AskUserQuestion`, two options:

- the User Story already in the issue is final, use it verbatim, or
- the user gives the exact wording in chat, and you use that verbatim.

Do not draft candidates, do not reword a story declared final, and do not proceed on an
assumed outcome. Every later step depends on knowing what the outcome is. If the ticket has
no user story at all, or the existing one has no real "so that", say so and ask again rather
than accepting "already final". Rename the section heading to **User Story** and move it to
the top.

## 3. Relocate technical content out of the Description

Move every technical or implementation statement from the Description into Technical
Details. This step only relocates. Nothing is cut here, and nothing is reworded beyond what
the new surroundings require.

## 4. Reduce the Description

From what remains, keep only points that are both load-bearing for understanding the ticket
correctly **and** not already stated in the Acceptance Criteria or Technical Details.
Rewrite each as a one-sentence bullet and replace the Description with them. If nothing
qualifies, omit the section. For a ticket that changes a user-visible flow, terse numbered
**Current behavior** and **Requested change** steps are allowed, since reproducing the
baseline is load-bearing and non-technical.

A point may turn out to be an untested requirement, better placed in the Acceptance Criteria
than in a Description bullet. Never act on that yourself. Writing, editing, reordering, or
deleting an acceptance criterion is out of bounds for this skill, because the criteria are
the contract and changing them is a decision only the human makes. Collect such points as
suggestions, raise them with the user before you deliver, and apply only what the user
decides, in the wording they choose. Until then the point stays where it is and the criteria
stay untouched.

## 5. First gap pass

Would an engineer new to this project understand the ticket, or is context missing? Add what
is missing as one-sentence bullets: technical gaps to Technical Details, everything else to
the Description. This is the only step that creates content rather than moving or cutting
it, so ground each added technical claim with a cheap `grep` or a Haiku `Explore`, and mark
anything you could not ground as unverified. Expect this pass to be weak: you have the
original in context and will fill gaps from it without noticing. Step 6 is the real detector.

## 6. Evaluate, in parallel

Dispatch all three in one message so they run concurrently.

- **Readability**, `general-purpose` on **Sonnet**, high effort. Give it the sharpened
  ticket **only**, never the original, framed as an engineer new to `openedx-core`. It is
  the one party with fresh eyes, so it is the real missing-context detector as well: what it
  cannot understand, what it would have to ask, where it would guess wrong, and whether the
  Description and Technical Details read cleanly.
- **Technical fidelity**, `software-architect` on **Opus**. Give it both versions. Did the
  rewrite change the architecture or a technical decision, and was any load-bearing
  technical fact lost when the Description was cut?
- **Product fidelity**, `business-analyst` on **Opus**. Give it both versions. Did the
  rewrite change the User Story, an acceptance criterion, or the scope, and was any
  requirement lost, added, or weakened?

Fidelity is the bar, not improvement. An evaluator suggesting the ticket be *better* than
the original is out of scope; only drift and lost content are findings.

## 7. Fix

Apply the findings, with one exception: a finding that would change an acceptance criterion
is never applied. Restoring a criterion the rewrite altered is a fix; anything else about
the criteria becomes a suggestion you raise with the user, per step 4. Re-dispatch the
evaluators at most once more, and only if a fix was substantive rather than cosmetic.
Otherwise close on your own re-read.

## 8. Deliver

Write the sharpened ticket to a new file (`issue-<n>-sharpened.md`, or `<slug>-sharpened.md`
for pasted text) in the repo root or the scratchpad. The file holds the ticket text and
nothing else, so the human can paste it straight into the tracker: no changelog, no notes to
the reviewer, no commentary inside it.

Put the changelog in your reply instead, covering what moved where, what was cut and why,
anything added in step 5 and whether it is grounded or unverified, and anything an evaluator
flagged that you deliberately left alone. List any acceptance-criteria suggestions separately
as open items for the user, alongside what the user already decided about them.
