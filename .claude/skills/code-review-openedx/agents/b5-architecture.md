# B5: Architecture

Agent: `software-architect`, model Opus, effort xhigh, budget 35 tool calls.

Read `review-rules.md`, the shared brief, and `agents/report-format.md` first, in that order.
When the dispatch names a section of the extension skill's `review-additions.md`, read that
section too. Write your report as `agents/report-format.md` says, and end with the hand-back
it defines. Paths to other skill files, such as `review-rules.md` and `agents/report-format.md`,
are relative to the skill directory, whose absolute path the dispatch's Read line gives (the directory that holds `review-rules.md`), not to `agents/`.

With the criteria, the diff, the
commits on `main`, and the rule locations, findings each with a `file:line` and the cited rule
or ADR on:

- layering and contracts: `.importlinter` boundaries, public API stability and DEPR, which names
  a module exports as supported API and whether each one upholds the module's invariants on its
  own, `UNSTABLE` markers where the module's neighbors carry them, the identifier conventions
  (`id`, `uuid`, `key`, `num`), and PII annotations on new models;
- framework-boundary leaks: HTTP-layer types (`Http404`, `get_object_or_404`, a DRF exception)
  raised from a module that is not a view or serializer are a `Gap`, because every non-HTTP
  caller of a library API inherits HTTP semantics; the fix is a domain exception translated in
  the view;
- the ADRs that govern the touched area, whether the change follows them, whether the ticket
  and an ADR disagree (name the conflict rather than following either), and whether a decision
  the change makes should itself become a proposed ADR or an ADR amendment;
- the **invariants table**, whenever the diff adds or changes a model, a constraint, an index,
  or a lock: one row per rule the data model relies on, stated in code or comments or implied by
  the tickets and ADRs, including the rules existing constraints, `on_delete` behaviors, and
  signals already encode and the change interacts with: invariant | enforcement (database
  constraint, application check, lock, nothing) | when a row is archived or soft-deleted | when
  deleted | when a replacement row is created | gap. Each gap is a finding: a rule only
  application code or a lock enforces, where a race, an out-of-band writer (the ORM, a fixture,
  an admin, a future endpoint), or a second code path can violate it, is a `Gap` when violation
  breaks a read path or corrupts data, otherwise a `Question` asking for a constraint; a
  constraint without a condition, in a design whose tickets or ADRs describe archiving or soft
  deletion, leaves an archived row occupying the slot so that no replacement row can exist, a
  `Gap` on this change because the constraint is what makes the later ticket impossible without
  a schema change; a lock or locking read whose work an outer lock or a database constraint
  already does is a `Suggestion` to remove it, with the reason; a lookup that will have to
  filter on a lifecycle field that already exists on `main` and does not is a `Question`;
- security of the new surface: authentication and permission checks on new or changed
  endpoints, object-level access, references to another tenant's rows by id, read-merge-write
  sequences that can delete or overwrite rows the change does not own, injection, secrets, new
  dependencies;
- placement: whether each piece lives in the right repository and layer, what companion change
  `edx-platform` or the MFE needs for the feature to reach its users, and whether that companion
  exists or is linked;
- callers: what in this repository, in `edx-platform`, or in community plugins the change can
  break; whether the test strategy fits the layer;
- naming: public functions have clear names and RST docstrings that state the contract, and the
  same concept has one name across the function signatures, the serializer, and the ticket;
- anything else with a concrete impact that the remits above do not name. The listed dimensions
  are where defects usually are, not the complete set.

## Red flags

| Thought | Reality |
| --- | --- |
| "There is no `AGENTS.md`, so there are no conventions to check." | `openedx-core` and `edx-platform` keep theirs in `CLAUDE.md`, ADRs, OEPs, and `.importlinter`. |
| "This is a library change; the platform and the frontend are someone else's problem." | Trace the chain. A missing or unlinked companion change is a `Gap`. |
