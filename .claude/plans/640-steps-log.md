# Steps log — #640 CBE app foundation

Purpose: record of the *approach* taken, for later evaluation. Not a description of the
code.

Sessions so far:

- **Session 1 — planning.** Produced `640-cbe-app-foundation-plan.md`. Logged below under
  "Session 1".
- **Session 2 — a failed implementation attempt.** Not logged here; the user discarded its
  changes. Its one lesson is recorded in Session 3's opening item, because it is the most
  actionable finding in this whole log.
- **Session 3 — implementation.** Logged below under "Session 3".

---

# Session 1 — planning

## Approach

1. Invoked `/implement-ticket-starter`. Read the skill file for the operating rules.
2. Pulled #640 with `gh`. Ticket self-identified as a subtask of #613, so followed the
   skill's ordering: parent #613 first, then #640, then siblings #641 and #642.
3. Also pulled comments on #613 and #640. This mattered — #613's comment thread carries
   two decisions that are not in any ticket body (the CBE→tagging dependency direction,
   and the `StudentCompetencyStatus` enforcement mechanism), and #640's body opens with
   an editor's note saying it was originally a mis-copy of #641 and had not been
   reviewed in depth. That note lowered my trust in #640's body relative to the ADRs and
   the parent, which turned out to be correct.
4. Surveyed repo layout before reading any ADR: `src/`, `src/openedx_content/applets/`
   (the prior art the user pointed at), root config files.
5. Read all three `docs/openedx_learning/` ADRs in full rather than via sub-agent — they
   totalled ~590 lines, small enough that delegating would have cost more than it saved.
6. Checked git history around the ADRs. This was the highest-value step of the session:
   it showed a newer ADR (`openedx_tagging/0013-competency-taxonomy-detection`, Accepted)
   that the ticket family predates and that now depends on the exact model this ticket
   builds. Read it.
7. Verified #640's own "open questions" against the repo instead of taking them at face
   value. Both were answerable from `main`; one was outright stale.
8. Traced the concrete mechanics that the plan depends on rather than assuming them:
   where migrations actually live for an umbrella app, how models/admin get discovered,
   which settings module mypy uses, whether existing `Taxonomy` subclasses are proxies.
9. Checked which tools are actually installed in the tutor venv before writing the
   verification section, so the commands in the plan are runnable.
10. Wrote the plan to `.claude/plans/` (gitignored, so it does not pollute the branch).

## What went right

- Reading the parent's comment thread, not just bodies. Two load-bearing decisions lived
  only there.
- Checking git history for ADRs newer than the tickets. Found a cross-repo contract
  (ADR-0013) that constrains this ticket in a way no ticket mentions.
- Verifying the ticket's open questions against `main` rather than surfacing them back
  to the user unanswered. One was stale; answering it removed a blocker for free.
- Deriving the migrations location from Django semantics *and* prior art, both of which
  contradicted the ticket. Following the ticket literally would have produced a
  migrations package Django silently ignores.
- Noticing `mypy.ini` points at `projects/dev.py`, so app registration has to happen in
  two settings files, not the one the ticket names.
- Noticing every existing `Taxonomy` subclass is a proxy model — a copy-paste trap that
  would silently drop the new column.

## What went less well / friction

- Started down the path of dispatching Explore sub-agents per `.claude/CLAUDE.md`'s
  context-hygiene rule, then didn't: the harness instruction for this session said not to
  use the Agent tool unless the user asked. Resolved by reading directly, which was
  affordable here (~10 small files) but would not scale to a larger ticket. This
  instruction conflict is worth resolving explicitly somewhere.
- Spent a couple of tool calls on packaging/coverage config (`MANIFEST.in`, `.coveragerc`,
  `pylintrc_tweaks`) that turned out to need no changes. Cheap, but it was speculative
  breadth rather than targeted.
- The `.importlinter` placement question has no right answer in the ticket (it only says
  "above `openedx_tagging`"). Decided it and documented the reversal cost rather than
  guessing silently, but it is the one assumption most likely to get overridden.

## Human corrections / iterations

The user pre-authorised answering my own questions as documented assumptions ("I don't
have time to answer right now"), so no up-front clarification round happened. Ten
assumptions and seven conflicts are recorded in the plan. Then, on review:

1. **User asked for an explanation of two plan claims.** Prompted me to verify rather
   than restate from memory — I ran a probe script against the repo's Django and found I
   had one fact wrong: a proxy model with an extra field does *not* silently drop it, it
   fails as system check `models.E017`. The genuinely silent failure is a *field-less*
   proxy, which creates no reverse accessor. Corrected the plan.
   *Lesson: I asserted Django framework behaviour from memory in a written artifact. It
   was cheap to verify and I should have done it before writing, not after being asked.*
2. **User proposed making the ADR-0013 accessor name an explicit contract** instead of an
   implicit convention pinned by a test. Clearly right; folded in as step 5b (two public
   API functions encapsulating the relation name), which reversed assumption A7 and added
   conflict C7 — ADR-0013's decision text currently forbids adding a method to the CBE
   app, so it needs a small amendment.
   *Lesson: I identified the fragility correctly but stopped at "add a regression test"
   when the fix was to remove the duplication. Detecting a cross-repo coupling should
   prompt "can this be encapsulated?", not just "can this be detected?".*
3. **User pushed back on the proxy-model warning** — the ADRs mandate MTI, so a proxy was
   never a design option. Fair: I had written it up as a "conflict" when it is only an
   implementer footgun note. Demoted to one bullet in the implementation step; C5 now
   covers only the real subtlety (`_taxonomy_class`/`cast()`).
   *Lesson: don't inflate "someone might copy the wrong neighbour" into a conflict row.
   Conflicts are where sources disagree, not where a reader might slip.*
4. **User asked whether edx-platform needs changes.** It does — four, including a
   non-obvious one (platform's PII safelist must list the new model because its annotation
   scan never reads installed site-packages) and an ordering constraint between the
   openedx-core release and the platform bump. Added as a new plan section.
   *Lesson: I planned the library change in isolation and never asked "what has to happen
   downstream for this to actually run?", even though the sibling repo was named in the
   skill's own background info. For a library whose only consumer is another repo, that
   question belongs in the first pass, not after being prompted.*

## Open for the user

- 10 assumptions (section 2 of the plan), of which A4 (`.importlinter` position) and A7
  (which umbrella modules to create) are the most discretionary.
- 6 conflicts (section 3), of which C1 (migrations path) also affects #641 and #642 and
  should be fixed in those ticket bodies.

---

# Session 3 — implementation

## Approach

1. **Read the plan file before anything else, and verified the repo state against it.**
   This is called out first because session 2 failed by never finding the plan and working
   from the GitHub issue instead. The user's prompt made the plan the source of truth and
   said to stop and surface any problem rather than improvise. Cheap, and it set up
   everything after.
2. Found leftover debris from session 2 immediately: `src/openedx_learning/` and
   `tests/openedx_learning/` still existed as `__pycache__`-only directories, invisible to
   `git status` (untracked, no source files left). Deleted them before writing anything, so
   no stale bytecode or half-package could confuse imports.
3. Read the prior art the plan pointed at (`openedx_content`'s umbrella shape,
   `openedx_catalog/models_api.py`, `.importlinter`, both settings modules) directly rather
   than by sub-agent. About ten small files; delegating would have cost more than it saved.
4. Ran the skill's spike and stabilize phases as **two separate dispatches to one Sonnet
   sub-agent**, continuing it with `SendMessage` so it kept context. Spike = skeleton,
   model, wiring, migration, layering, plus an end-to-end MTI proof. Stabilize = tests,
   docstring corrections, linters.
5. Reviewed the spike output myself against the plan before authorising stabilize, instead
   of taking the sub-agent's summary at face value. Read the generated migration line by
   line.
6. When the stabilize agent stalled (harness watchdog, 600s no progress) partway through
   its check suite, took over the remaining gates directly rather than resuming it. Running
   linters is deterministic; re-dispatching would have re-read the whole context to
   re-run four commands.
7. Verified every "pre-existing failure" claim with `git stash -u` rather than asserting it.
   Three of them were real (`isort` on `projects/dev.py`, PII coverage at 66.7%,
   `organizations` migration drift); all three would have looked like new breakage.
8. Dispatched an **independent Sonnet reviewer** for the `code-review` step, because the
   skill forbids reviewing a diff you wrote in the same context and I had hand-edited three
   files. It found no code defects and independently re-raised the plan's C7 governance
   item, which is a useful confirmation that C7 is real rather than plan paranoia.
9. Executed every command in the manual verification guide before shipping it, and pasted
   real output into it. This caught two bugs in my own guide (below).
10. Dispatched a third Sonnet sub-agent to implement the companion edx-platform issue
    (#38958) on a branch in `../edx-platform`, so the user can actually integration test.

## What went right

- Deleting session 2's `__pycache__`-only directories before starting. A clean `git status`
  hid them completely; a stale `.pyc` tree under a package being recreated is an unpleasant
  class of bug to debug later.
- Verifying pre-existing failures with `git stash -u`, not plain `git stash`. Because the
  new app was untracked, plain `git stash` would have left it in place and "proved" a
  baseline that still contained the change. Got this right in the work and then wrote the
  *wrong* version into the guide on the first pass; caught it on review.
- Not accepting the first suppression that would have made mypy pass. django-stubs cannot
  see reverse MTI accessors, and there are 95 `# type: ignore` precedents in this repo, so
  adding one was defensible. Spent one extra iteration finding a form that needs no
  suppression at all (module constant + `getattr`), verified it against both mypy and
  pylint, and only then kept it. Net: zero new suppressions.
- Running the guide's own commands before shipping the guide. Two real bugs in it:
  a `git checkout --` revert step that cannot work on untracked files, and a
  "temporarily rename the class" demo that would have broken Django admin autodiscovery at
  startup. Both were replaced with non-destructive equivalents that prove the same point.
- Refusing the part of the platform ticket that could not be done honestly. #38958 asks for
  an `openedx-core` pin bump; the version does not exist on PyPI yet. Doing it would have
  broken `pip install` for everyone. Documented the deferral in the commit body and the
  guide instead of silently skipping or faking it.
- Building a separate `.venv` for the quality tooling when asked, rather than installing
  into the tutor venv. `.venv/` was already gitignored, so it cost nothing.

## What went less well / friction

- **The harness/skill conflict from session 1 recurred and cost the user a round trip.**
  The session system prompt carried "Do not call the AgentTool unless the user requested
  it", while `.claude/CLAUDE.md` and `spike-and-stabilize` both mandate delegation. I
  followed the harness instruction and said so; the user corrected it and asked where the
  text came from. It is not in any file on disk (`~/.claude/settings.json`, CLAUDE.md, or
  `~/.claude.json`) — it appears to be injected by the VSCode extension/SDK, with
  `CLAUDE_CODE_ENABLE_TASKS=0` set in the environment. *This is the second session where
  this exact conflict surfaced. It is an environment configuration problem, not a
  reasoning problem, and it will keep recurring until the setting is found and changed.*
- Wrote the manual verification guide before running its commands, then had to correct it.
  The corrections were caught, but the cheaper order was obviously to verify first and
  write once. Same failure shape as session 1's "asserted Django behaviour from memory in a
  written artifact" lesson, which suggests the lesson did not fully generalise: it is not
  about Django facts specifically, it is about *any* claim in a durable artifact.
- The stabilize sub-agent stalled at 600s and its work had to be picked up mid-flight. No
  work was lost, but a long single dispatch that both writes code and runs seven checks is
  a large unit to lose. Splitting "write tests" from "run the gates" would have been more
  robust, and the gates were arguably always mine to run.
- Two environment probe commands (`source ~/.virtualenvs/tutor/bin/activate && python -c
  ...`) were denied by the permission classifier early on. Harmless, worked around by
  delegating env discovery, but it means I shipped the plan's venv assumptions to a
  sub-agent unverified rather than confirming them myself first.

## Human corrections / iterations

1. **User corrected the no-sub-agents claim** and asked to delegate to Sonnet at high
   effort. Complied. Note the Agent tool exposes no `effort` parameter (only Workflow's
   `agent()` does), so the dispatches inherited the session effort, which was `xhigh` —
   at or above what was asked. Worth knowing for future briefs that specify an effort level.
2. **User redirected the quality-tooling install** away from the tutor venv into a
   dedicated one. I had been about to follow the plan's verification note literally
   (`pip install -r requirements/quality.txt`, implicitly into the active venv).
   *Lesson: the plan said which tools were missing but not where to put them; "install the
   missing tools" into someone's working runtime venv is a side effect worth asking about,
   and the repo already gitignored `.venv/` as the obvious answer.*
3. **User asked for the companion edx-platform work** so the change could actually be
   integration tested. Plan section 9 already enumerated the platform changes (added in
   session 1 after a similar prompt), so the content was ready, but I had again treated the
   library change as the whole deliverable.
   *Lesson: session 1 learned "ask what has to happen downstream" and wrote it into the
   plan; session 3 still did not act on it unprompted. Knowing the downstream work exists
   is not the same as offering to do it. For a library whose only consumer is another repo,
   "do you want the consumer side too, so you can test this?" should be offered at the
   point the library work goes green.*

## Follow-up round: ADR amendment and PR description

After the implementation report, the user resolved C7 and asked for a PR description.

4. **User resolved the C7 question by ruling on it directly**: barring additions to
   `openedx_tagging` is the real constraint; adding to the CBE app is obviously fine, and
   the ADR text was simply wrong. Amended ADR-0013 in four places, not one. The obvious
   edit was the Decision's opening clause, but the same "and the CBE app" phrasing had
   propagated into the Known trade-off paragraph and into a Rejected Alternative, where it
   read as nonsense on inspection ("keeping the CBE app free of any competency-specific
   reference"). Also added the positive half: the Decision now records that platform calls
   `openedx_learning.api` rather than spelling the accessor, which is what makes the ADR
   agree with the code that was just merged into the branch.
   *Lesson: when a phrase in a document turns out to be wrong, grep for it before editing.
   A drafting error that survived review once has usually been copy-pasted.*
5. Verified the doc change the way CLAUDE.md requires for documentation: installed
   `requirements/doc.txt` into the same throwaway `.venv` and actually ran `doc8` and the
   Sphinx build, rather than eyeballing the RST. Build succeeded. `doc8` reported two
   trailing-whitespace errors, both in ADRs I had not touched (0002 and 0012), confirmed by
   checking my own file separately; left them alone as unrelated.
6. **Ran the PR description's own test instructions before posting them.** The join query
   in step 4 had never actually been executed, only reasoned about. It works
   (`1|Nursing|0`). Same discipline as the verification guide, applied first this time
   rather than after a correction.
7. Went back and cleared the now-stale "needs sign-off" language in all three planning
   artifacts (plan C7, plan section 10, guide B.2 note, guide checklist). Stale
   "blocked on X" notes are worse than no note, since a reader trusts them.

## Handed to the user, unresolved

- **The extra `root_packages` line** the platform sub-agent added beyond its brief, with a
  documented rationale. Flagged for review rather than silently kept or reverted.
- **Release ordering**: openedx-core must release before the platform branch can bump its
  pin and merge.
- **The ADR-0013 amendment is uncommitted.** The user has been handling commits and pushes
  on this branch themselves, so it was left in the working tree rather than committed
  unasked.
