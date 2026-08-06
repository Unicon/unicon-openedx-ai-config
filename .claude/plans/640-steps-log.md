# Steps log — #640 CBE app foundation

Purpose: record of the *approach* taken, for later evaluation. Not a description of the
code. Phase covered here: planning only (user asked for a plan, not an implementation).

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
