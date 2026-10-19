# code-review-v2: brief template and scope prompts

Two things live here: the `BRIEF.md` template every reviewer reads first, and the six scope
prompts. Fill the placeholders (`<n>`, `<owner>/<repo>`, SHAs, paths) from step 1 of
`SKILL.md`. Keep each prompt's probe list; add probes specific to the change under review.

## BRIEF.md template

```markdown
# Shared review brief: <owner>/<repo> PR #<n>

You are one of six independent adversarial reviewers of this PR. Each reviewer owns one scope.
Review only your scope, but report anything out of scope you stumble on in a short
"Out of scope, noticed anyway" section at the end.

## Standing rules

- Read-only. Never edit, create, or delete repository files, commit, push, or post to GitHub.
  You MAY run read-only commands: `git`, `pytest` (with `--no-cov -p no:cacheprovider`),
  linters, `python manage.py makemigrations --check --dry-run`, `grep`, and so on.
  Activate the venv first: `source <repo>/.venv/bin/activate`. Use
  `DJANGO_SETTINGS_MODULE=test_settings` for manage.py commands.
  If you want to test "does this test fail when the code is broken", make a temporary edit
  and revert it with `git checkout -- <file>` before you finish. Leave the working tree
  exactly as you found it.
- You cannot dispatch sub-agents. If you need something you cannot fetch, return it as a
  "Needs research" item (what you need and why).
- Be adversarial. Your job is to find what is wrong, missing, or risky. But every finding must
  carry evidence: a quoted acceptance criterion, a cited rule (file plus rule) from an ADR, OEP,
  CLAUDE.md, or repo convention, or a concrete reproduction path with `file:line`. A preference
  without evidence is a "Suggestion", not a finding.
- Distinguish what you CONFIRMED by running or reading something from what you INFER.
- Review the change as it is, not the rest of the roadmap. A pre-existing problem counts only if
  this change makes it newly relevant.
- Prior review on this PR already exists (see pr_<n>_prior_reviews.md). Do not repeat those
  points unless you disagree with them or they were not actually addressed.

## The PR

- Repo: <absolute path> (branch `<head branch>` is checked out; HEAD = <head sha>).
- Base: upstream/main = <base sha>. Merge-base = <merge-base sha>.
  <Note any precedent commit that landed on main after the PR branched, with its SHA.>
- Title: "<title>"
- Closes #<ticket> (issue last updated <updatedAt>).
- Files changed: <list>
- CI on the PR head: <status summary>.

## Context files (read the ones your scope needs)

All in <scratchpad>/context/
- pr_<n>.diff, pr_<n>_body.md, pr_<n>_prior_reviews.md
- issue_<ticket>.md: the ticket with acceptance criteria. SOURCE OF TRUTH for correctness.
- issue_<sibling>.md ...: siblings, precedents, consumers.
- issue_<design>_comments.md: the design discussion; say where the decisive comments start.

Relevant repo documents: <ADR paths, CLAUDE.md, annotation safe list, sibling repo paths,
likely-relevant OEPs>.

## Facts already confirmed by the orchestrator (do not re-derive, build on them)

- <test command> passes: <count>.
- <makemigrations check result>.
- <any grep result that settles a question, with the command>.

## Output format (strict)

Return Markdown with these sections:

1. `## Scope` : one line restating your scope.
2. `## Findings` : a numbered list. Each finding has:
   - **Title** (one line)
   - **Severity**: Blocker | Major | Minor | Nit | Question
   - **Anchor**: `path:line` in the PR (or the file that should have changed)
   - **Evidence**: quoted AC / cited rule / reproduction path. Say CONFIRMED or INFERRED.
   - **Why it matters**: 1-3 sentences, concrete consequence.
   - **Suggested change**: what the author should do (or what question to answer).
   - **Your impact estimate (1-100)**: how much this should matter to the merge decision.
3. `## Checked and found acceptable` : bullet list of what you examined that is fine, so the
   orchestrator can tell "not checked" from "checked, OK".
4. `## Out of scope, noticed anyway` : optional.
5. `## Needs research` : optional.

Write in full sentences. No em dashes.
```

## Dispatch header (prepend to every scope prompt)

```
First read the shared brief at <scratchpad>/context/BRIEF.md and follow its standing rules
and output format exactly.
```

## Scope 1: Security (software-architect, model: fable)

Adversarially review the PR against OWASP Top 10 (2021) and Django/DRF security best
practices, and look for any vulnerability or security-relevant weakness the change introduces
or newly exposes. Be concrete about attack surface rather than generic. Probe at least:

1. Mass assignment and broken access control: can any existing write path set the new fields
   or reach the new code unintentionally? Check DRF serializers (`fields = "__all__"` versus
   explicit lists; whether ModelSerializer picks up new model fields), Django admin, import or
   bulk paths, and the same models' serializers and admin in the consuming repo.
2. Integrity of any protective or state-carrying data the change adds: every path that copies,
   casts, bulk-updates, or recreates rows, and whether it can clear, reset, or propagate the
   new state onto the wrong row.
3. Migration safety as availability: what the migration emits for MySQL 8 and PostgreSQL on
   large tables (instant versus rewrite), whether CI exercises the MySQL settings, and whether
   the migration is reversible. Mark CONFIRMED or INFERRED.
4. PII and data governance (OEP-30): are new fields covered by existing annotations? Verify
   any PR claim about `make pii_check`.
5. Information disclosure through help_text, serializer output, or logs.
6. Anything else security-relevant.

## Scope 2: Correctness (software-architect, model: fable)

Does the PR do exactly what the ticket asks, and does it comply with the relevant ADRs in this
repo and in the sibling repos? The ticket's acceptance criteria are the source of truth.

1. For EACH acceptance criterion: met / not met / partially met / unverifiable, with evidence
   (file:line or a command run). Give extra attention to any criterion where the PR body admits
   a deviation, and to any criterion whose test a prior reviewer had removed: decide whether
   the criterion is still verifiable as the ticket requires, with your own reasoning.
2. Check every factual claim in the PR body that a reviewer would rely on (precedent shape,
   index reasoning, reversibility, "fails on main for unrelated reasons"). Verify or refute.
3. ADR compliance: read the ADRs the ticket cites and the app's own ADR series; search the
   sibling repo for decisions touching the same area. Report conflicts and any ADR the change
   should have updated or added.

Put the per-criterion table first, then the other findings.

## Scope 3: Architectural conventions and soundness (software-architect, model: opus)

The code must follow the structures and decisions established by Open edX, and be
architecturally solid for a published library consumed by edx-platform and plugins.

1. Field, function, and class conventions against neighbors in the same file and against the
   consuming repo (naming, `editable`, help_text phrasing, placement order).
2. Fidelity to the precedent the ticket says to mirror, and whether a shared abstraction is
   warranted (CLAUDE.md: not before three callers; count them).
3. ADR coverage: does the app's own ADR series need a new or updated ADR for the concept this
   change introduces (CLAUDE.md: impactful decisions get an ADR in proposed status)? Do model
   or module docstrings describe fields in a way that is now stale?
4. Migration conventions against the directory's history and OEP-49 / OEP-38.
5. Public API and library stability: changed public methods, downstream construction or
   serialization of the models, companion changes needed elsewhere, release-note or changelog
   conventions (python-semantic-release from commit subjects).
6. Primitive choice: raise only if the chosen primitive bakes a concrete defect into the schema
   or contract; you are reviewing, not redesigning.
7. Interaction with existing constraints: unique constraints, on_delete behaviors, signals.

## Scope 4: Testing and edge cases (software-architect, model: opus)

Four requirements: every acceptance criterion is covered by a test or explicitly declared
untestable with a reason; all important edge cases are enumerated and the covered ones
identified; each new or changed test fails when the behavior breaks and fails for the reason
its name states; the code handles the edge cases.

1. Mutation checks: temporarily break the code each new test covers, run the test, read the
   assertion message, restore the file with `git checkout --`, confirm `git status` is clean.
   For a test that no plausible mutation can fail, say so and judge whether it earns its place.
2. Round-trip gaps: when the PR body describes a failure mode (for example "saving would
   reset the field"), check whether a test pins that exact mode or only an in-memory proxy.
3. Enumerate edge cases (constructor kwargs, copy and bulk paths, null foreign keys, resync or
   save hooks, database backends in CI, reverse migration) and check each for a test and for
   code handling. Confirm the test framework's semantics for any migration test.
4. Test quality: naming, placement, `is` versus `==` on database-loaded values, docstring
   style, annotation consistency.
5. Coverage table: AC -> test(s) -> verdict (covered / covered by schema not test / uncovered /
   not testable).

Leave the working tree exactly as you found it.

## Scope 5: Open questions and architectural concerns (software-architect, model: opus)

Find what the PR, the ticket, or the approved design left unanswered and that this PR either
should answer now (because it fixes the schema or contract) or should record for downstream
tickets. Each item must be a genuine question with a concrete consequence: say what breaks or
becomes expensive if the answer goes one way. Typical angles: auditability of new state when
no history or timestamps exist; interaction of new state with unique constraints and
un-archive or re-create flows; state that is set and never cleared versus the rule it
implements; derived values across nullable foreign keys; deferred indexes versus the queries
already specified downstream; two overlapping "hidden" states on one model; operational cost
of the migration on large tables and whether the ecosystem asks for a note; semantics left
unstated for the next implementer.

Conclude each item with one of: "Should be answered in this PR", "Should be recorded as an
open question on <downstream tickets> or a new ticket", or "Settled, no action".

## Scope 6: Miscellaneous (software-architect, model: opus)

Everything a careful senior reviewer flags that the other five scopes do not own.

1. Code quality and style in the diff: translation-string wording and punctuation against
   neighbors, quoting, cross-references to other fields by bare name, docstrings and comments
   per CLAUDE.md ("comment why, not what"; stale comments are bugs).
2. Migration file hygiene: header versus installed framework version, evidence of hand edits,
   naming against the directory's convention. Run the repo's linters on the touched files only
   (pylint, pycodestyle, isort, mypy, pydocstyle, lint-imports as configured) and report new
   warnings on touched lines.
3. Test-file hygiene (not semantics): module docstring, constant naming, annotation
   consistency, placement, line length, trailing-comma style.
4. PR hygiene against Open edX expectations: OEP-51 conventional commits and squash
   expectations, PR template sections, accuracy of the testing instructions (run any grep or
   command the instructions name), changelog or release-note conventions.
5. Writing-style rules from CLAUDE.md on committed prose: no em dashes, US spelling, current
   state not history, state what things are.
6. Anything else. Keep nits labelled as nits with low impact scores; do not inflate.
