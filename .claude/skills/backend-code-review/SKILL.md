---
name: backend-code-review
description: "Extends the 'code-review-openedx' skill. Senior backend peer review of a diff for this application. Use when asked to review a PR, a branch, or a diff, or for a second opinion on changes. Review-only: surface findings with file:line anchors and a severity marker; never fix, commit, or push. Post to GitHub only when explicitly asked and approved."
---

# Backend Code Review (Extension of 'code-review-openedx')

A senior peer review for the general backend application within the Open edX ecosystem.
Surface what is wrong and why; let the developer decide what to act on. Never apply fixes,
commit, or push from this skill.

This skill runs in the top-level session. Per the Delegation rule in `CLAUDE.md`, whoever
runs it dispatches the sub-agents the parent skill names; it never runs inside a dispatched
sub-agent that would then need to dispatch further.

## Parent skill

This skill manually builds on the sibling `code-review-openedx` skill; Codex and Claude do not load
that skill automatically. Before starting the review, read
[`../code-review-openedx/SKILL.md`](../code-review-openedx/SKILL.md) in full.

Follow the parent skill's review workflow, review-wide rules, evidence requirements,
and finding format. The backend-specific checks below belong to the parent's phase B dispatch
wave (remits B3 to B5) and its phase C verification; they do not replace its general review
requirements.

If the parent skill file is missing or unreadable, stop and tell the user before
reviewing the change.

## In the parent's phase B remits and phase C verification, add the following backend-specific questions:

In addition to the parent's checks in [code-review-openedx](../code-review-openedx/SKILL.md) (give the data-model and
query questions to remit B5, the test questions to remit B4, and the rest to phase C), evaluate the following
detailed questions about this Backend code review and raise any further concerns if prudent

1. Does it adhere to general best practices for this repo's version of Django/Python?
2. Any security issues or vulnerabilities introduced in this pull request?
3. Do all added functions have appropriate, descriptive but concise names?
4. Do all added functions have appropriate, descriptive but concise docstrings? Could they be reworded so that they are
   less verbose if they seem too long?
5. If there are any database changes, do they follow the Open edX database design guidelines?
6. If there are any database changes, are all added database migrations properly documented?
7. If there are any database queries, are they thoroughly, efficiently, and concisely unit tested?
8. If there are any database queries added or changed, are they properly optimized and performant?
9. If there are any database queries added or changed, are they properly secured?
10. If a model field is added, which generic surfaces pick it up without any code naming it: an admin registration
    without an explicit `fields` list, a serializer or form using `__all__`, import/export, `model_to_dict`? Enumerate
    them and check each against what the ticket says may read or write the field.
11. For each new row lock, locking read, or `select_for_update()`, state what it serializes against and whether an
    outer lock or a database constraint already does that work. A lock whose work is already done is a
    `Nit` to remove it; a rule that only a lock enforces, with no constraint behind it, is a row in the invariants
    table, which the parent's B5 remit turns into a `Gap` or a `Nit` recommending a constraint.
12. For each value the change builds from other fields and stores in a bounded column (`max_length`), compare the
    inputs' maximum lengths with the column's; the CI database may reject what the local one silently stores.

Additional Notes:

1. A schema-only migration needs no test of its own. The criterion it serves counts as covered in the parent skill's
   acceptance-criteria table when a behavior test sets and reads the new column or constraint, alongside the
   repository's standard migration check when it has one. A new column that no test touches is a `Gap`, even when
   the migration applies cleanly.

## Complexity measurement

Add this measurement to the parent's B3 remit as its step 4.

**What B3 runs.** The measurement covers the Python files the change touches, leaving out files
under `tests/` and `migrations/` directories. B3 runs both tools on those files twice in its
temporary worktree, once at the head SHA and once at the merge-base:

- Cyclomatic complexity, with a limit of 10:
  `ruff check --isolated --no-cache --select C901 --config 'lint.mccabe.max-complexity=0' --output-format concise <files>`.
  The threshold of 0 makes ruff print the value of every function, in the form
  ``path:line:col: C901 `name` is too complex (<value> > 0)``.
- Cognitive complexity, with a limit of 15: `uvx complexipy@8.3.0 <files>`, which prints one
  `Class::function <value>` line per function. Ruff has no cognitive complexity rule.

The parent's rule against reporting what CI tooling enforces applies per measurement. When the
repository's own lint configuration enforces one of the two, for example by selecting `C901` in
its ruff settings, B3 skips only that measurement and reports it as enforced by CI. A tool that
could not run is reported as a skipped check with the reason, never as a pass.

**Joining the two outputs.** Ruff prints a line number and the bare function name, and complexipy
prints the class-qualified name without a line number. B3 joins the two outputs by function name
within each file. When one file has several functions with the same name, B3 reads the file at
each line number ruff printed to find the enclosing class, and joins on the class-qualified name.

**Which functions count.** B3 classifies the functions it measures as follows.

- **Modified.** The function's body differs between the merge-base and the head SHA. B3 decides
  that by comparing the function's syntax tree at the two commits, with the docstring left out,
  so a change to its docstring, comments, or formatting alone leaves it unmodified.
- **Added.** The function exists only at the head SHA and is not a moved or renamed function. It
  is `new` at the merge-base.
- **Moved or renamed.** A function removed at the merge-base and a function added at the head SHA
  have the same name, or the same body under a different name. B3 compares removed and added
  functions across all the files the change touches. With an unchanged body the function is
  unmodified. With a changed body it is modified, its merge-base values are the ones measured at
  its old location, and its row names that old location.

**What B3 returns.** The per-function table has one row for each added or modified function whose
cyclomatic or cognitive complexity at the head SHA is above its limit, and no other rows:

| Function | `file:line` | Cyclomatic at merge-base | Cyclomatic at head | Cognitive at merge-base | Cognitive at head |
| --- | --- | --- | --- | --- | --- |

When one file has more than five such functions, B3 leaves them out of the per-function table and
returns one row for that file in an aggregate table:

| File | Functions above a limit | Highest cyclomatic | Total cyclomatic | Highest cognitive | Total cognitive | Three highest functions at head |
| --- | --- | --- | --- | --- | --- | --- |

Each number in the aggregate row is computed over the added and modified functions of that file,
once at the merge-base and once at the head SHA, and the cell holds both values, written as
`4 -> 9`. A function the change adds contributes nothing to the merge-base numbers. The last
column names the three functions with the highest cognitive complexity at the head SHA, each with
its two head values. Ties go to the higher cyclomatic complexity, and then to the function that
comes first in the file.

Under the tables, B3 states in one sentence how many added and modified functions are at
or under both limits, and the highest cyclomatic and the highest cognitive complexity among them
at the head SHA. When no function is above a limit, that sentence is the whole result.

**Phase C: turn the tables into findings.**

- A function in the per-function table is a `Nit` when the change added the function or raised
  the value that is above the limit. The `Nit` states the measured values at the merge-base and
  at the head SHA next to the limit, cites this section as its rule, and names the fix: which
  branch, loop, or nested block to extract into a helper.
- A function that was already above a limit at the merge-base, and whose values the change did not
  raise, is dropped.
- A file in the aggregate table is one `Nit` for the whole file, when the change added or raised
  at least one of the functions counted in it. The `Nit` states the file's numbers at the
  merge-base and at the head SHA, and names the three highest functions as the ones to split first.

The tables and the sentence go into the review under the parent's "Checks run and skipped" part.

## Delivering the review

When the review is done, your response in chat is only a link to the cleaned-up file that the
parent's phase D produces, nothing more. When the user asked questions that are an integral part
of the review, the answers are part of the review in that file.
