# Handoff: openedx-core #642 part B (criterion and group learner status models)

Written 2026-09-25 at the end of a session, so a later session can continue without the
conversation. The design below was approved section by section by the user on 2026-09-25. It
serves as the written spec for the superpowers workflow.

## How to resume

Paste this into a new Claude Code session opened in `/Users/jesperhodge/openedx/openedx-core`:

> Read `.claude/plans/642b-learner-status-handoff.md` and continue #642 part B with superpowers.
> The design in it is approved. Start at "Next steps".

## Where the superpowers process stands

| Stage | Status |
| --- | --- |
| `superpowers:brainstorming`, classified as architectural | Done. Scope confirmed, base option A chosen, all five design sections approved. |
| Written spec | This file. The user has not yet reviewed it as a written document. |
| `superpowers:writing-plans` | Not started. |
| Choose an execution method (subagent-driven or inline) | Not started. The user picks it after reviewing the plan. |
| `superpowers:using-git-worktrees`, then TDD implementation | Not started. |
| Verification, code review, finishing the branch | Not started. |

## Next steps

1. Ask the user to review this file as the written spec. Apply any changes they ask for.
2. Invoke `superpowers:writing-plans` to turn the "Approved design" section into an
   implementation plan. Save the plan in a scratchpad, not in openedx-core.
3. Let the user choose the execution method. Per `.claude/CLAUDE.md`'s Delegation section, only
   the top-level session dispatches sub-agents, implementation sub-agents are `general-purpose`
   on Sonnet, and `model` is passed explicitly on every dispatch.
4. Create the worktree and branches described in design section 1, then implement with
   `superpowers:test-driven-development`.
5. Commit locally. Push nothing and open no PR until the user asks.

## Sources of truth

- Parent issue #613 is the source of truth. Issue #642's acceptance criteria are narrowed from
  #613's and may be stale in places.
- ADRs 0002, 0003 and 0004 in `docs/openedx_learning/decisions/`. Use ADR-0002 as amended on the
  #641 stack tip. Decisions 5 (indexes), 6 (the learner status tables) and 7 (delete protection)
  matter most for part B.
- The earlier plan for the whole of #642, "642-plan-v2.md", lives in another session's scratchpad
  at `/private/tmp/claude-501/-Users-jesperhodge-openedx-openedx-core-642/f500b34c-1c3f-46a0-8075-5bc7f6c9c25c/scratchpad/642-plan-v2.md`.
  Temporary directories can be cleared, so everything part B needs from it is restated in this
  file. Its section 10 holds a style block for implementing agents, copied below.

## State of the pull requests and branches on 2026-09-25

| Item | State |
| --- | --- |
| #641: PR #800 (`jesperhodge:jesperhodge/feat--641-competency-criteria-models`) | Open, ready for review, unmerged. It is reviewed as fork stack jesperhodge/openedx-core#10 and #2 to #7. Its tip is `origin/jesperhodge/cbe-641-07-criterion` at `cd5d15b`. PR #800's own head, `344745a`, is a merge commit with the same tree. It adds `CompetencyCriteriaGroup`, `CompetencyRuleProfile` and `CompetencyCriterion`, migrations `0002` to `0007`, the `models/` package with `models/criteria.py`, and tests that deletes cascade when no learner status exists. |
| #642 part A: PR #830 (`jesperhodge:642-stack-base-branch`) | Draft, unmerged. It is reviewed as fork stack jesperhodge/openedx-core#16, #17 and #18. Commit `252565f` (#16) is a pure rename of `models.py` into a `models/` package. Commit `24074c6` (#17) adds `MasteryStatus`, `CompetencyMasteryStatus`, migration `0002` and the seed migration `0003`. Commit `b961f23` (#18) adds `StudentCompetencyStatus` and migration `0004`. |
| PR #802 | An older draft with all four #642 models in one PR. Part A plus part B supersede it. It is still open; closing it is the user's call. |
| Conflict between #800 and #830 | Both number their migrations from `0002` and both create `models/__init__.py`. Part B needs both. |
| `upstream/main` | At `739ef47`. That commit adds an `openedx_catalog` ADR and does not affect part B. |
| Local branch `jesperhodge/cbe-641-07-criterion` | Stale. It is an older copy from before the stack was rebased, 17 commits ahead of and 20 behind `origin`. Use `origin/jesperhodge/cbe-641-07-criterion`. |

## Scope of part B

Everything left in #642 that needs #641's tables:

1. `StudentCompetencyCriteriaStatus`, the per-criterion status, with ADR-0002 index 6.
2. `StudentCompetencyCriteriaGroupStatus`, the per-group status, with ADR-0002 index 7.
3. Their schema migrations, placed after both #641's and part A's migrations.
4. The `ProtectedError` half of every transitive delete case. #641 tested only the half where
   the delete succeeds and cascades because no learner status exists.
5. Deleting a user removes that user's rows in all three status tables.
6. The three whole-feature gates: migrations apply from scratch, all ten ADR-0002 Decision 5
   indexes exist, and every model #613 adds is annotated for PII.

Out of scope for part B:
- Admin pages.
- The rule that automatic writes may only raise a status, and the staff-correction path.
- The rollup task.
- Edits to the text of #642 and #613.
- The openedx-platform issue for its `.annotation_safe_list.yml`.

Mention the last two to the user as follow-ups when the work is done.

## Approved design

### 1. Branch layout (option A)

| Branch | Built from | Contents |
| --- | --- | --- |
| `642b-stack-base-branch`, local only | `origin/jesperhodge/cbe-641-07-criterion` at `cd5d15b` | Cherry-pick part A's `24074c6` and `b961f23` onto it, and skip `252565f` because #641 already creates the `models/` package. Resolve the `models/__init__.py` conflict so the file exports both #641's and part A's models. Rename part A's migrations to `0008_competency_mastery_status`, `0009_seed_competency_mastery_statuses` and `0010_studentcompetencystatus`. Point `0008`'s dependency at `0007_alter_criterion_override_help_text`, and update the dependencies of `0009` and `0010` to the new names. Fold the renames into the cherry-picks, because this base only exists so part B has something to build on. |
| `cbe-642b-01-criterion-status` | `642b-stack-base-branch` | `StudentCompetencyCriteriaStatus`, migration `0011`, and its tests. |
| `cbe-642b-02-group-status` | `cbe-642b-01-criterion-status` | `StudentCompetencyCriteriaGroupStatus`, migration `0012`, its tests, and the gates. |

This layout assumes #800 merges before #830, which is what #642's ticket text expects. If #830
merges first instead, the only change is the dependency line in `0011`. When the upstream PRs
merge, rebase part B onto `main`.

Do the work in a new git worktree, and leave the main checkout on `cbe-642-01-models-package`
untouched. The worktree at `/Users/jesperhodge/openedx/openedx-core-642` belongs to another
session, so do not use it.

### 2. The two models

Both models go in `src/openedx_learning/applets/cbe/models/learner_status.py`, next to
`StudentCompetencyStatus`. Export them from `models/__init__.py`; `openedx_learning/models.py`
picks them up through its wildcard import. Copy part A's conventions exactly:

- `user` foreign key to `settings.AUTH_USER_MODEL` is `on_delete=CASCADE`.
- The node foreign key and `status` are `on_delete=PROTECT`.
- Every foreign key uses `related_name="+"`. PROTECT still fires with `"+"`, because Django's
  delete collector includes hidden relations. Part A's tag tests prove this.
- `created` and `modified` use `manual_date_time_field()`. Part A chose this deliberately, even
  though #642's criteria say `auto_now_add` and `auto_now`, because `auto_now` does not fire on
  `QuerySet.update()`.
- Each class has a docstring of one or two lines that ends with `.. no_pii:`.
- No `__str__`, `verbose_name`, `ordering`, admin page or `violation_error_message`.

| Model | Node foreign key | Unique constraint |
| --- | --- | --- |
| `StudentCompetencyCriteriaStatus` | `criterion` to `CompetencyCriterion`, `db_column="competency_criteria_id"` | `(user, criterion)`, named `oex_learning_studentcriteriastatus_user_criterion_uniq` (ADR-0002 index 6) |
| `StudentCompetencyCriteriaGroupStatus` | `group` to `CompetencyCriteriaGroup`, `db_column="competency_criteria_group_id"` | `(user, group)`, named `oex_learning_studentcriteriagroupstatus_user_group_uniq` (ADR-0002 index 7) |

Neither model gets a check constraint, because both accept all three status values. The
constraint names are shortened on purpose: a name built from the full model name would pass 64
characters, MySQL's identifier limit. Generate migrations with `makemigrations`; do not write
them by hand.

### 3. Tests

Use the fixtures in #641's `tests/openedx_learning/applets/cbe/conftest.py`: `organization`,
`course_run`, `competency_taxonomy`, `tag`, `object_tag`, `group` and `default_rule_profile`.
`CompetencyCriterion.save()` calls `full_clean()`, so create criteria with
`rule_profile=default_rule_profile`. PR 642b-01 moves the `user` and `now` fixtures into
`conftest.py`, because three test files will need them. It also deletes the identical copies of
`user`, `now`, `competency_taxonomy` and `tag` from part A's `test_learner_status.py`.

PR 642b-01 adds `test_criterion_status.py`:
- A second row for the same user and criterion raises `IntegrityError`, and the same user can
  hold a row for a second criterion.
- `AttemptedNotDemonstrated` is accepted, which contrasts with the competency-level table.
- A criterion status blocks each of these deletes with `ProtectedError`:
  - the criterion itself;
  - its `ObjectTag`;
  - the root group, with the status on a criterion two levels down;
  - the tag;
  - the taxonomy;
  - a `CourseRun` whose course-scoped group holds the criterion. #642 does not list this case;
    it was added to test #613's claim that a course only hard-deletes once nothing beneath it
    needs protecting.
- Deleting a sibling branch with no status beneath it succeeds, while another branch of the same
  tree holds status. This shows PROTECT applies to specific rows, not to the whole tree.
- Deleting the `CompetencyMasteryStatus` row a criterion status references raises
  `ProtectedError`.
- Deleting the user removes the row.

PR 642b-02 adds `test_criteria_group_status.py`:
- A second row for the same user and group raises `IntegrityError`, and
  `AttemptedNotDemonstrated` is accepted.
- Deleting the group itself raises `ProtectedError`. So does deleting a root group above a
  descendant group that holds status.
- Deleting a tag whose tree holds only a group status, and no criterion status, raises
  `ProtectedError`. #642's technical details want this fail-closed behavior on purpose: the
  application layer checks only the criterion table, but the database blocks on all three.
- Deleting the `CompetencyMasteryStatus` row a group status references raises `ProtectedError`.
- Deleting one user removes their rows from all three status tables.

Follow the style block below. One behavior per test, and the test name states the behavior.

### 4. Whole-feature gates (PR 642b-02)

- **Indexes.** Add `test_adr_0002_indexes.py`. It reads each table's indexes through
  `connection.introspection.get_constraints()` and asserts that every one of the ten ADR-0002
  Decision 5 indexes exists with exactly the listed columns, and is unique where the ADR says
  unique. The expected columns:
  1. `CompetencyCriteriaGroup(oel_tagging_tag_id, course_id)`
  2. `CompetencyCriteriaGroup(parent_id)`
  3. `oel_tagging_objecttag(object_id)`
  4. `CompetencyCriterion(oel_tagging_objecttag_id)`
  5. `CompetencyCriterion(competency_criteria_group_id)`
  6. `StudentCompetencyCriteriaStatus(user_id, competency_criteria_id)`, unique
  7. `StudentCompetencyCriteriaGroupStatus(user_id, competency_criteria_group_id)`, unique
  8. `StudentCompetencyStatus(user_id, oel_tagging_tag_id)`, unique
  9. `CompetencyRuleProfile(scope_code)`, unique
  10. `CompetencyMasteryStatus(status)`, unique

  Indexes 2, 4 and 5 come from Django's automatic foreign key indexes, not from explicit
  `Meta.indexes`. On MySQL, InnoDB creates them along with the foreign key constraint. Run this
  test on both SQLite and MySQL.
- **Migrations.** Apply all migrations from scratch on SQLite and on MySQL: a fresh test
  database, without `--reuse-db`. `makemigrations --check --dry-run openedx_learning` must report
  no changes.
- **PII.** Run the `pii_check` command and record in the PR description that every model #613
  adds is annotated. That is the seven models from #641 and #642, plus
  `HistoricalCompetencyCriteriaGroup`, `HistoricalCompetencyCriterion` and
  `HistoricalCompetencyRuleProfile`, which #641 already lists in `.annotation_safe_list.yml`. The
  overall percentage will stay below 100%. The earlier plan says `main` already has about 20
  unannotated models; that claim has not been verified.

### 5. Small edits that follow from part B

- **`learner_status.py` module docstring:** it describes only `StudentCompetencyStatus`, and it
  calls #641's CASCADE chain "a future PR's". PR 642b-01 rewrites it to cover all three status models,
  and to describe the chain as it exists now.
- **`src/openedx_learning/applets/cbe/README.rst`:** it says the learner status tables are still
  needed. PR 642b-02 corrects that sentence.

## Style block for implementing agents (from the earlier plan's section 10; paste verbatim)

- No docstring longer than two lines unless it states a contract the code cannot show.
- A comment answers "why", once, in one sentence, and never restates an ADR paragraph. Cite the
  ADR decision or index number; do not paraphrase it.
- No shared helper until three tests need the same five lines. Inline setup beats a factory.
- One behavior per test. The test name is the specification; the body needs no docstring.
- Do not add admin, `__str__`, `verbose_name`, `ordering`, or `related_name` that nothing queries.
- Every line traces to an AC line in the plan or to a Django requirement (migration, annotation).
- Write the failing test first for every behavior (constraint, seed, PROTECT, CASCADE, update
  shape). Field declarations get no test of their own.

## Environment facts and gotchas

- The virtualenv is `/Users/jesperhodge/openedx/openedx-core/.venv` (Python 3.12.8, Django
  5.2.16). It installs openedx-core as editable from the main checkout. When you run tests from
  a different worktree, set `PYTHONPATH=src`. Otherwise `openedx_learning` is imported from the
  main checkout's `src`. Confirm with
  `python -c "import openedx_learning; print(openedx_learning.__file__)"` before trusting a test
  run.
- The MySQL test container `oel-mysql-test` (image `mysql:8`) is running. Run tests against it
  with `pytest tests/openedx_learning --no-cov -q --ds=mysql_test_settings`. Add `--reuse-db`
  only when a from-scratch migration check is not the point.
- Run the PII check with `code_annotations django_find_annotations --config_file
  .pii_annotations.yml --lint --report --coverage`, the command that `tox -e pii_check` runs with
  `DJANGO_SETTINGS_MODULE=test_settings`.
- `.claude/CLAUDE.md` rules that apply: don't run `make test` or `make validate`; run pytest
  without coverage on the related tests only; never add `noqa`, `pylint: disable` or
  `type: ignore` without approval; use conventional commit messages; commit or push only when
  asked.
- zsh treats `$VAR:s...` as a history modifier. Write `git show "${REF}:src/..."`, never
  `git show $REF:src/...`, because `:s` in `:src` otherwise mangles the path. Also, don't start
  an `echo` argument with `=`, because zsh expands it as a command path.
- Part A's `test_learner_status.py` defines its own `competency_taxonomy` and `tag` fixtures,
  which match `conftest.py`. They shadow the conftest fixtures harmlessly until PR 642b-01 removes
  them.

## Reminders for the eventual part B PR

- Per the ai-config decision 0002, the PR description needs a human evaluation of the AI output,
  and the user logs one line in `.claude/ai-output-evaluations/Output-evaluations.md`.
- The upstream PR for part B closes #642. Pass along to the user: #642's text still describes
  the old two-slice plan, `auto_now` timestamps and migration numbers `0004` and `0005`. The
  openedx-platform repo also needs an issue for adding ten entries to its
  `.annotation_safe_list.yml` before its openedx-core pin is bumped.
