# Backend review questions

These are review questions in the sense of the parent skill's step A5. Each B agent whose remit has a
`## B<n>` section reads it and answers its questions. Beyond them, it may raise any further concern it
finds in the same area. The consolidation agent reads the whole file.

## B2

Q3. Do all added functions have appropriate, descriptive but concise names?

Q4. Do all added functions have appropriate, descriptive but concise docstrings? Could they be reworded so that
they are less verbose if they seem too long?

## B3

Q1. Does it adhere to general best practices for this repo's version of Django/Python?

## B4

Q7. If there are any database queries, are they thoroughly, efficiently, and concisely unit tested?

Q12. For each value the change builds from other fields and stores in a bounded column (`max_length`), compare
the inputs' maximum lengths with the column's; the CI database may reject what the local one silently stores.

## B5

Q2. Any security issues or vulnerabilities introduced in this pull request?

Q5. If there are any database changes, do they follow the Open edX database design guidelines?

Q6. If there are any database changes, are all added database migrations properly documented?

Q8. If there are any database queries added or changed, are they properly optimized and performant?

Q9. If there are any database queries added or changed, are they properly secured?

Q10. If a model field is added, which generic surfaces pick it up without any code naming it: an admin
registration without an explicit `fields` list, a serializer or form using `__all__`, import/export,
`model_to_dict`? Enumerate them and check each against what the ticket says may read or write the field.

Q11. For each new row lock, locking read, or `select_for_update()`, state what it serializes against and whether
an outer lock or a database constraint already does that work. A lock whose work is already done is a
`Suggestion` to remove it; a rule that only a lock enforces, with no constraint behind it, is a `Question` for
the invariants table.

## Consolidation

A schema-only migration needs no test of its own. The criterion it serves counts as covered in the parent skill's
acceptance-criteria table when a behavior test sets and reads the new column or constraint, alongside the
repository's standard migration check when it has one. A new column that no test touches is a `Gap`, even when
the migration applies cleanly.
