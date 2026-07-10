# Epic 13.1 (#643): Competency mastery evaluation, persistence, and grade-change listener

## Executive summary

This epic turns a graded subsection into recorded competency mastery, automatically and with no
manual review. openedx-core owns all CBE-model knowledge and consumes the openedx-events
`PERSISTENT_SUBSECTION_GRADE_CHANGED` event directly (adopting ADR-0001's former alternative 8);
the platform keeps all grading knowledge. The work is three openedx-core tickets: a pure,
in-memory evaluation engine plus criteria resolution (13.2), a recording service that is the public
Python API and owns persistence (13.3), and a thin event listener (13.4) — plus one optional
openedx-platform ticket (P). Persistence is append-only with write-on-change (ADR-0003); group and
competency levels are materialized (ADR-0002). Explicitly out of scope: event emission, non-Grade
rule types, non-subsection criteria, any REST or UI surface, downstream credentialing (D), and
learner- or instructor-facing surfacing (E, later Willow work). Effort is roughly one to two
developer-days per core ticket, blocked on #613 (the CBE data model) and Use Case ID 6, with two
small model additions (a leaf timestamp column and a per-learner lock row) routed into #613.

The one non-trivial architecture decision is concurrency. Because derived levels are materialized,
a grade change must recompute and re-write the parent rows up the tree, and under concurrent,
out-of-order, multi-node delivery two overlapping evaluations for the same learner can write a
stale roll-up (write-skew). Atomicity alone does not prevent this: the writes are append-only
INSERTs, so concurrent transactions do not conflict at the row level. The recommended design places
a single per-learner lock and one transaction around the whole resolve → read-current → evaluate →
persist path, all inside Ticket 13.3's recording service, which lets Ticket 13.2 stay a pure function
(trivially unit-tested with no database) and Ticket 13.4 stay a thin adapter. The cost is one small
lock table, one leaf timestamp column, and a modest amount of locking machinery, in exchange for
guaranteed correctness regardless of delivery order or node count.

The document also records an "assume conflicts are rare" alternative (a stakeholder's judgment)
that drops the lock, the lock table, and the locking transaction. Its failure mode is narrow and
self-correcting: a conflict can leave one learner's derived status transiently wrong until their
next relevant grade event, with leaf rows never corrupted and no crash; a scheduled reconciliation
job (recompute-from-leaves) or a cheap optimistic re-read bounds the residual risk of a wrong status
lingering when no further event arrives. So the trade is guaranteed correctness for a little
machinery (main design) versus less machinery for a rare, bounded, self-healing inconsistency
(alternative). Recommendation: default to the locked design; the alternative is acceptable for the
MVP only if conflicts are genuinely rare and Ticket P (per-learner ordering) plus a reconciliation
job are in place. The deeper lever, out of scope here, is materialization itself: computing derived
levels on read would dissolve the write-skew entirely, but that reopens ADR-0002, which materializes
deliberately for dashboard read performance.

---

This work is split into three openedx-core implementation issues (13.2, 13.3, 13.4), one optional
openedx-platform issue (P), and two explicitly out-of-scope future efforts (D, E). Each issue
below is self-contained: it has its own scope, use case, acceptance criteria, and technical
details. Shared context (dependencies, ADRs, prior art) is stated once at the top and applies
to the openedx-core issues (13.2, 13.3, 13.4).

**Concurrency note that shapes the whole epic.** Group- and competency-level statuses are
materialized (stored), not recomputed on read, so a grade change recomputes and re-writes derived
rows up the tree. Same-learner correctness comes from **partitioning, not a database lock**: the
emitter sets the event's partition key to `user_id` (**Ticket P**), and the event bus gives each
partition a single consumer, so a learner's events are always processed serially by one worker and
two workers can never write conflicting roll-ups for one learner. Different learners spread across
partitions and process in parallel, so the design scales horizontally by partition count. Each
consumer processes a **windowed micro-batch** and writes it in bulk, which collapses per-event
transaction and commit overhead. The pieces: **Ticket P** owns per-learner partitioning (the
correctness boundary); **Ticket 13.4** is the batch consumer that accumulates a micro-batch and
calls the recording service once; **Ticket 13.3** is the bulk recording service (cached resolve,
bulk read-current, evaluate, bulk persist), holding no lock; **Ticket 13.2** is the pure in-memory
engine, unchanged, iterated to fold multiple same-learner events. A **reconciliation job** (its own
ticket) recomputes derived levels from current leaves and appends corrections, backstopping the
rare partition-boundary anomaly (a partition-count change, a rebalance gap, or a misconfigured
consumer).

## A note on "API" terminology

In Open edX, "API" is overloaded: it means both a public REST/HTTP surface and a private
Python module interface. **Everywhere in this epic, "the API" means the CBE applet's
Python module interface defined in `src/openedx_learning/applets/cbe/api.py`** — the
functions other `openedx-platform` code imports and calls. It is not a REST endpoint, not
public-facing, and not a web API. There is no HTTP or UI surface anywhere in this epic.

The UI-facing CRUD REST API on top of the `Student*Status` tables is a separate future
effort (and will likely reshape the data for the frontend rather than expose the backend
tables directly). See out of scope.

## Shared context (applies to 13.2, 13.3, and 13.4)

**Upstream event dependency.** The input is the `PERSISTENT_SUBSECTION_GRADE_CHANGED`
event being defined in `openedx-events` (PRs
[#545](https://github.com/openedx/openedx-events/pull/545) /
[#587](https://github.com/openedx/openedx-events/pull/587), nearly complete but not yet
merged). Those PRs only add the event and its payload (`PersistentSubsectionGradeData`);
they do not emit it from a call site or listen for it. Producing the event is out of scope
here. Because the PRs are unmerged, the input contract for Ticket 13.4 is that payload shape,
not a downstream API signature. Confirm the final `PersistentSubsectionGradeData` fields
(`user_id`, `course`, `subsection_edited_timestamp`, `grading_policy_hash`, `usage_key`,
`weighted_graded_earned/possible`, `weighted_total_earned/possible`, `first_attempted`)
before merge, and re-check if either PR's schema changes before Ticket 13.4 ships.
openedx-events is already a base dependency (`openedx-events==11.2.0`, for producing events
today); consuming this new event will require bumping to the release that ships it once
#545/#587 merge.

**Blocking dependencies.** This epic is blocked by:
- **#613** (ticket 1.1 — the CBE data model, ADRs 0002/0003). After 1.1, all models live at
  `src/openedx_learning/applets/cbe/models.py`. Note 1.1's text uses a stale path
  (`openedx_learning/apps/competencies/`); ADR 0001 governs and the correct path is
  `src/openedx_learning/applets/cbe/`.
- **Use Case ID 6**, which must land before this work can proceed.

**How the models fit together.** Competency criteria form a hierarchy. A
`CompetencyCriteriaGroup` is an internal node that combines its children with a
`logic_operator` (AND or OR); groups nest via a self-referential `parent_id`, and the topmost
group for a competency represents the competency tag itself (its child groups are typically
per-course, OR-ed together by default, or custom groupings defined by a platform
administrator). A `CompetencyCriterion` (the model; database table `CompetencyCriteria`) is a
leaf under a group: it points at one `oel_tagging_objecttag` (the graded subsection, via that
row's opaque `object_id`) and carries the Grade rule used to measure mastery (for example
`{"op":"gte","value":75,"scale":"percent"}`, a score of at least 75%). The rule may come from
the criterion's own `CompetencyRuleProfile` or a fallback lookup; Ticket 13.2 owns the full
resolution order. Per-learner mastery is recorded at three levels in append-only tables:
`StudentCompetencyCriteriaStatus` (criterion), `StudentCompetencyCriteriaGroupStatus` (group),
and `StudentCompetencyStatus` (competency, keyed by `oel_tagging_tag_id` and constrained to
Demonstrated/PartiallyAttempted). These models come into existence in #613 (ADR-0002) and
provide the scaffolding this epic builds on.

**ADRs to read first.**
- `docs/openedx_learning/decisions/0001-competency-criteria-location.rst`: places all CBE code
  in openedx-core, in the new top-level `openedx_learning` app as the `cbe` applet. It does not
  itself decide to consume the grade event. Consuming `PERSISTENT_SUBSECTION_GRADE_CHANGED`
  directly is ADR-0001's *rejected* Alternative 8 ("migrate grading signals to openedx-events
  and consume directly"), rejected only because that openedx-events support did not yet exist.
  This epic revisits that call now that PRs #545/#587 add the event.
- `0002-competency-criteria-model.rst`: the models above; the bottom-up recompute; the
  persist-only-on-change update flow (§6); the competency-level Demonstrated/PartiallyAttempted
  constraint; the index list (§5); and why derived group/competency levels are materialized.
- `0003-competency-criteria-versioning.rst`: the learner status tables are append-only (a new
  row per change, never updated in place); current status is the most recent row for a
  learner + entity, ordered by `created` with `id` as tie-breaker.
- `0004` (proposed, to be written for this epic). It must record the **partitioned-batch
  concurrency model**: same-learner correctness comes from one consumer per learner-partition
  (partition-as-lock), not a database row lock; the write path is bulk per micro-batch;
  `StudentCompetencyProcessingLock` is dropped; Ticket P is correctness-critical rather than an
  optimization; and the reconciliation job backstops partition-boundary anomalies. It supersedes
  the earlier per-learner-lock concurrency stance. It does not exist yet.

**Technical Design Document:**
[Competency Criteria Technical Design Document](https://openedx.atlassian.net/wiki/spaces/OEPM/pages/5604573185/Competency+Criteria+Technical+Design+Document)

**Prior art — Python module-interface pattern.** `src/openedx_tagging/api.py`'s module
docstring states callers use the API functions, not the models, and that no permissions are
enforced there (the caller authorizes). The umbrella facade re-exports each applet's `api.py`
via `from .applets.<x>.api import *` (`src/openedx_content/api.py`); every `openedx_content`
applet `api.py` declares `__all__` and documents its contract in an RST docstring. `UNSTABLE`
is a documented `README.rst` convention: an UNSTABLE API may change without a DEPR cycle.
`openedx_learning`'s umbrella `api.py` and its single app config are created by #613.

**Prior art — content ↔ competency mapping.** A competency is a `Tag` in a
`CompetencyTaxonomy`; the association is an `oel_tagging_objecttag` row whose `object_id` is
an opaque, non-FK identifier (`src/openedx_tagging/models/base.py`, a `case_sensitive_char_field`,
max 255). Because that column is case-sensitive, matching a graded subsection's key against it
is case-sensitive with no special-casing in resolution. A criterion maps to one objecttag plus
a resolved rule.

**Overall use case (the "why" behind the epic).** As a learner, when I receive a grade for
a gradeable subsection that has a competency criterion attached, I want the platform to
evaluate whether I have demonstrated the associated competency and record my mastery status
automatically, without anyone manually reviewing my grades. Recording this data is a
prerequisite for later surfacing demonstrated competencies to learners, instructors, and
downstream credentialing — but those surfaces are separate future tickets (see out of
scope), not part of this epic.

**Status:** blocked on #613 and Use Case ID 6. Fully specified; ready to implement once the
blockers merge.

---

## Ticket 13.2 — Mastery evaluation engine and criteria resolution

**Scope.** Build two independent, internal building blocks (no public API, no DB writes) plus the data types they share:

1. **Resolution** — given a graded subsection, read the CBE/tagging models and build the **competency trees** it feeds, each leaf's rule resolved. Reads the DB; learner-independent.
2. **The engine** — a **pure function**: given a grade, those trees, and the learner's current statuses, compute the new statuses. No DB, deterministic.

Ticket 13.3 orchestrates: it calls resolution (DB read), reads the learner's current statuses (DB read), then calls the engine (pure). Resolution and the engine never call each other. This split is what keeps the correctness-critical logic unit-testable with no database and lets Ticket 13.3 wrap the two reads in its lock and transaction.

**Use case.** As the recording service (Ticket 13.3), I need to find the competency trees a graded subsection feeds and compute the resulting mastery statuses as a pure function, so my write path is a thin, well-tested shell.

**Acceptance criteria.** Acceptance is confirmed by a PR reviewer verifying these scenarios
are covered by automated unit tests. Engine scenarios run in memory with no database;
resolution scenarios use database fixtures. Each Then names an observable result.

```
Scenario: Leaf criterion met by a passing grade
  Given a leaf criterion with a rule of {"op":"gte","value":75,"scale":"percent"}
  When the engine evaluates a grade of 80% for that criterion
  Then the criterion result is Demonstrated

Scenario: Leaf criterion attempted below threshold
  Given a leaf criterion with a rule of {"op":"gte","value":75,"scale":"percent"}
  When the engine evaluates a grade of 60% for that criterion
  Then the criterion result is AttemptedNotDemonstrated

Scenario: AND group fully satisfied
  Given an AND group over two leaf criteria, both Demonstrated
  When the engine rolls the group up
  Then the group is Demonstrated
  And the competency result is Demonstrated

Scenario: AND group partially attempted
  Given an AND group over two leaf criteria, one Demonstrated and one with no result yet
  When the engine rolls the group up
  Then the group is PartiallyAttempted
  And the competency result is PartiallyAttempted

Scenario: AND group fully not demonstrated
  Given an AND group over two leaf criteria, both AttemptedNotDemonstrated
  When the engine rolls the group up
  Then the group is AttemptedNotDemonstrated
  And no competency result is produced (competency level omits AttemptedNotDemonstrated)

Scenario: OR group satisfied by one child
  Given an OR group over two leaf criteria, at least one Demonstrated
  When the engine rolls the group up
  Then the group is Demonstrated
  And the competency result is Demonstrated

Scenario: OR group fully not demonstrated
  Given an OR group over two leaf criteria, both AttemptedNotDemonstrated
  When the engine rolls the group up
  Then the group is AttemptedNotDemonstrated
  And no competency result is produced

Scenario: OR group partially attempted with one failed leaf
  Given an OR group over two leaf criteria, one AttemptedNotDemonstrated and one with no result yet
  When the engine rolls the group up
  Then the group is PartiallyAttempted
  And the competency result is PartiallyAttempted

Scenario: Competency level omits AttemptedNotDemonstrated
  Given a top-level group that rolls up to AttemptedNotDemonstrated
  When the engine computes the competency result
  Then no competency result is produced
  And the only competency-level values the engine ever emits are Demonstrated or PartiallyAttempted

Scenario: The engine is a pure computation
  Given any engine input
  When the engine runs
  Then it performs no database reads or writes
  And the same input always produces the same result

Scenario: Rule resolved via the CompetencyRuleProfile fallback chain
  Given a leaf criterion with no rule override and a CompetencyRuleProfile at the taxonomy level
  When resolution resolves that criterion's rule
  Then the taxonomy-level profile is used
  And the resolution order is override, then the criterion's CompetencyRuleProfile, then taxonomy, then course, then org, then system default

Scenario: Non-Grade rule type during MVP
  Given a leaf criterion whose resolved rule type is View or MasteryLevel
  When resolution resolves that criterion
  Then NotImplementedError is raised (only Grade rules are supported in the MVP)

Scenario: Subsection with no criteria resolves to nothing
  Given a subsection with no competency criteria attached
  When resolution runs for that subsection
  Then it returns no trees

Scenario: One subsection feeding multiple competencies
  Given a subsection referenced by criteria in two different competencies
  When resolution runs for that subsection
  Then it returns one tree per competency, each with its leaf rules resolved

Scenario: Content matching is case-sensitive
  Given a criterion attached to a subsection whose content key differs only in letter case from the graded subsection
  When resolution runs for the graded subsection
  Then that criterion is not matched
```

**Technical details.** Three internal parts under `src/openedx_learning/applets/cbe/` (see Files table).

### 1. Data structures

Plain frozen dataclasses and one enum, **no Django imports**, so the engine stays pure. Field names are illustrative.

```
MasteryStatus (enum) = DEMONSTRATED | ATTEMPTED_NOT_DEMONSTRATED | PARTIALLY_ATTEMPTED
    # values must match the seeded CompetencyMasteryStatuses (ADR-0002 §6.1)
    # "no result yet" (not attempted) = absence of a status, not a fourth value

GradeInput
    content_key: str            # the graded subsection; matches objecttag.object_id
    percent: float               # score, in the rule's scale
    attempted: bool               # attempted at all? (unattempted → no result, distinct from failed)
    source_edited_timestamp     # used by Ticket 13.3's staleness check; engine ignores it

CriteriaTree                    # one per competency the subsection feeds; structure + rules only, no learner data
    competency_tag_id           # → competency-level status row
    root: GroupNode

GroupNode
    group_id                    # → group-level status row (CompetencyCriteriaGroup.id)
    logic_operator: AND | OR
    children: [GroupNode | LeafNode]   # in DB order (order doesn't affect AND/OR)

LeafNode
    criterion_id                # → criterion-level status row (CompetencyCriteria.id)
    content_key: str            # subsection this leaf measures; compared to GradeInput.content_key
    rule                        # resolved Grade rule, e.g. {"op":"gte","value":75,"scale":"percent"}

CurrentStatuses                 # learner snapshot; read by Ticket 13.3, passed in
    { node identity (criterion/group/competency id) : current MasteryStatus }   # missing key = no status

EvaluationResult                # engine output
    entries: [(level, node identity, MasteryStatus)]   # level ∈ criterion | group | competency
                                                        # competency entries: only DEMONSTRATED | PARTIALLY_ATTEMPTED
    .empty()                    # the "nothing to record" form
```

The node ids and status values above are exactly what Ticket 13.3 stores, so they must match #613's models: `MasteryStatus` = the seeded statuses, and the competency level is DB-constrained to Demonstrated/PartiallyAttempted (the engine must never emit `ATTEMPTED_NOT_DEMONSTRATED` there). `CurrentStatuses` is a snapshot of each node's *latest* row (ADR-0003: current = latest row).

**Engine signature:** `evaluate_trees(grade, trees, current_statuses) -> EvaluationResult`.

### 2. Logic

**Resolution** `resolve_criteria_for_content(content_key) -> list[CriteriaTree]` *(Ticket 13.2)* — reads models, writes nothing, takes no `user_id`:
1. Match `content_key` **case-sensitively** against `oel_tagging_objecttag.object_id`, restricted to competency taxonomies.
2. Walk each matched leaf up to its root competency, building one `CriteriaTree` per competency (empty list if none — a normal no-op).
3. Resolve each leaf's rule, most specific first: override → the criterion's `CompetencyRuleProfile` → taxonomy → course → org → system default. A non-Grade rule (View/MasteryLevel) raises `NotImplementedError` (MVP is Grade only).

**Engine** `evaluate_trees(...)` *(Ticket 13.2)* — pure, computes bottom-up:
1. **Leaves:** recompute only leaves whose `content_key` matches the grade; others keep their `current_statuses` value. Attempted + met → `DEMONSTRATED`; attempted + unmet → `ATTEMPTED_NOT_DEMONSTRATED`; not attempted → no result.
2. **Groups:** roll up by `logic_operator` per the **Acceptance Criteria** (authoritative case table).
3. **Competency (root):** the root's status, but only `DEMONSTRATED` or `PARTIALLY_ATTEMPTED` is emitted (a failed/absent root emits nothing) — matching the DB constraint.

**Bounded cost.** Per event the engine's work is bounded by the size of the affected trees
(trees per subsection × depth × branching, all small and fixed by how competencies are authored)
and does not grow with the number of learners, events, or competencies in the system: it
recomputes the changed leaves and rolls their ancestors up to each root (ADR-0002), leaving
unaffected subtrees at their `current_statuses` value. This bound is what lets recomputation
keep up with a high grade-event rate; a test should assert the engine's work tracks
affected-tree size, not total system size.

**Ticket 13.3 (out of scope, context only):** records mastery in bulk per micro-batch (cached resolve, bulk read-current, evaluate, bulk persist) under Ticket P's one-consumer-per-learner-partition boundary, with no database lock; it skips stale grades (older `source_edited_timestamp`) and appends a status row only on change (ADR-0003). If you add a transaction, DB write, caching, or staleness check to Ticket 13.2, it is in the wrong ticket.

**Layering.** Data types and engine import nothing from Django, `openedx-platform`, `opaque_keys`, or grading; resolution reads only `openedx_learning`/`openedx_tagging` models (downward per `.importlinter`). The public surface is Ticket 13.3.

*Example resolution prompt.*

> Implement the CBE mastery-evaluation engine and criteria resolution in `openedx-core`. These
> are **internal** applet modules — no public API, no transaction, no lock, no DB writes (all of
> that is Ticket 13.3). The `openedx_learning` app and CBE models are created by blocking ticket
> #613 (ADRs 0001/0002/0003); confirm the CBE applet's `.importlinter` layering is in place first.
>
> Build the three parts described in **Technical details → Data structures** and **Logic**,
> under `src/openedx_learning/applets/cbe/`:
>
> 1. **Data types** (`data.py`) — the `MasteryStatus` enum and the `GradeInput`,
> `CriteriaTree`/`GroupNode`/`LeafNode`, `CurrentStatuses`, and `EvaluationResult` structures
> with their fields as listed. Stdlib `dataclasses` and `enum` only, no Django. Keep
> `MasteryStatus`'s values matching the seeded `CompetencyMasteryStatuses` (ADR-0002 §6.1);
> represent "no result yet" as the absence of a status, not a fourth value.
>
> 2. **Engine** (`_evaluation.py`) — the pure `evaluate_trees(grade, trees, current_statuses) ->
> EvaluationResult`: no Django, no queries, no writes, deterministic. Compute bottom-up (leaves →
> groups → competency) exactly as the Logic section states. Recompute only leaves whose
> `content_key` matches the grade; take every other leaf from `current_statuses`. **Roll groups
> up per the Acceptance Criteria scenarios — treat them as the authoritative case table; do not
> invent your own.** Emit only `DEMONSTRATED` or `PARTIALLY_ATTEMPTED` at the competency level.
>
> 3. **Resolution** (`_resolution.py`) — `resolve_criteria_for_content(content_key) ->
> list[CriteriaTree]`: reads models, writes nothing, takes no `user_id`. Case-sensitive match
> against `oel_tagging_objecttag.object_id` restricted to competency taxonomies; walk each
> matched leaf up to its root competency; resolve each leaf's rule most-specific-first (override
> → the criterion's `CompetencyRuleProfile` → taxonomy → course → org → system default). Return
> one tree per competency (empty list if none); raise `NotImplementedError` for a resolved
> non-Grade rule.
>
> **Tests:** `tests/openedx_learning/applets/cbe/test_evaluation.py` covers every roll-up
> scenario from the Acceptance Criteria in memory with **no database** (assert no queries run).
> `tests/openedx_learning/applets/cbe/test_resolution.py` uses DB fixtures for the fallback
> chain, the case-sensitive object-id match, the empty result, one subsection feeding multiple
> competencies, and the non-Grade `NotImplementedError`.
>
> Do not import `openedx-platform`, `opaque_keys`, or grading, and do not add any transaction,
> lock, persistence, or staleness logic (that is Ticket 13.3). Run `pytest` on the new modules and
> `lint-imports`.

**Files to create and modify.**

New files:

| File | Purpose |
| --- | --- |
| src/openedx_learning/applets/cbe/data.py | `MasteryStatus` enum + `GradeInput`, tree, `CurrentStatuses`, `EvaluationResult` dataclasses (no Django) |
| src/openedx_learning/applets/cbe/_evaluation.py | Pure leaf→group→competency roll-up engine |
| src/openedx_learning/applets/cbe/_resolution.py | `resolve_criteria_for_content` + per-leaf rule resolution |
| tests/openedx_learning/applets/cbe/test_evaluation.py | DB-free unit tests of the engine |
| tests/openedx_learning/applets/cbe/test_resolution.py | Resolution + content↔criteria mapping tests |

**Open questions.**
- Final event field names (`weighted_graded_earned/possible`, `first_attempted`, `usage_key`)
  are pending PR #545/#587. `GradeInput` fields are derived at Ticket 13.4's boundary, so a rename
  is isolated, but confirm before merge.
- `.importlinter` registration of `openedx_learning` is owned by #613; confirm the CBE applet's
  layering is in place before 13.2 merges.

---

## Ticket 13.3 — Mastery recording service and retrieval (the public API)

**Scope.** Build the CBE applet's public Python API and the bulk recording unit behind it:
- `record_competency_status_batch(*, entries)`: the primary write path. Resolve (cached),
  bulk-read current statuses, evaluate (the pure Ticket 13.2 engine), and bulk-persist the changed
  rows for a whole micro-batch. It takes no database lock; same-learner correctness comes from
  Ticket P (one consumer per learner-partition).
- `record_competency_status_for_grade(*, user_id, grade)`: a thin single-event wrapper over the
  batch path, for tests, backfill, and ad-hoc callers.
- `get_mastery(*, user_id, competency_tag_id)`: read a learner's current competency mastery status.

Persistence is append-only per ADR-0003 (current status = latest row) and writes a new row only
when the computed status differs (ADR-0002 §6 update flow); this persist-only-on-change diffing is
separate from Ticket 13.2's engine omitting competency-level `AttemptedNotDemonstrated`. Each batch
write is atomic: all changed rows commit together or none do. A grade older than the current leaf's
grade (by `source_edited_timestamp`) is skipped so an out-of-order event cannot regress a newer
status.

Follow the `openedx_tagging/api.py` convention: callers use these functions, not the models,
and the caller authorizes (no permission checks here). Re-export from the umbrella
`src/openedx_learning/api.py` facade.

**Use case.** As a caller (the Ticket 13.4 listener, or any `openedx-platform` code), I can hand
the CBE API a learner and a grade and have the learner's competency mastery recomputed and
durably recorded in one atomic, concurrency-safe call, and I can read a learner's current
mastery back, so grading knowledge (the platform's) and CBE-model knowledge (openedx-core's)
stay on their correct sides of the boundary.

**Acceptance criteria.** Confirmed by a PR reviewer via automated unit tests exercising the API
directly. Each Then names an observable result (a recorded current status, a return value, or an
unchanged row count).

```
Scenario: A passing grade records mastery up the tree
  Given a subsection whose leaf criterion sits under an AND group forming a competency for a learner
  And the grade meets the leaf's rule and satisfies the group
  When record_competency_status_for_grade is called
  Then the learner's current criterion, group, and competency statuses are all Demonstrated

Scenario: A changed status is recorded, an unchanged one is not
  Given a learner whose current criterion status is already Demonstrated
  When record_competency_status_for_grade is called with a grade that again yields Demonstrated
  Then no new row is written for that criterion and its current status is unchanged (persist only on change)

Scenario: Competency level never records AttemptedNotDemonstrated
  Given a grade that makes a competency roll up to AttemptedNotDemonstrated for a learner
  When record_competency_status_for_grade is called
  Then no competency-level row is written and no database constraint is violated
  (the competency-level record is constrained to Demonstrated or PartiallyAttempted)

Scenario: One subsection feeding multiple competencies is recorded for all
  Given a subsection referenced by criteria in two different competencies for a learner
  When record_competency_status_for_grade is called
  Then each competency whose status changed has its current status updated

Scenario: A grade with no matching criteria records nothing
  Given a subsection with no competency criteria attached
  When record_competency_status_for_grade is called
  Then no rows are written and the call returns without error

Scenario: Recording is all-or-nothing
  Given a grade that would change statuses at multiple levels and across multiple competencies
  When the write fails partway through
  Then no rows from that call are committed and the learner's prior statuses are unchanged

Scenario: A stale (older) grade does not regress a newer status
  Given a learner whose current leaf status reflects a grade with a newer source_edited_timestamp
  When record_competency_status_for_grade is called with an older-timestamp grade for that subsection
  Then no status is changed

Scenario: Concurrent recording for one learner converges to the correct result
  Given two grade changes for the same learner recorded concurrently on different workers
  When both calls complete
  Then the learner's final current group and competency statuses equal what a single recording over both final leaf statuses would produce

Scenario: Repeating the same recording is a no-op
  Given a grade that has already been fully recorded for a learner
  When record_competency_status_for_grade is called again with the same grade
  Then no new rows are written

Scenario: Retrieve a learner's current mastery
  Given a learner with a recorded competency mastery status
  When get_mastery is called for that learner and competency
  Then it returns the current (latest) mastery status

Scenario: Retrieve when no mastery exists
  Given a learner with no recorded mastery for a competency
  When get_mastery is called
  Then it returns an empty/absent result without error
```

**Technical details.** This ticket is the bulk recording orchestrator: it owns the write path and
composes Ticket 13.2's cached, learner-independent resolution and pure engine with bulk
persistence. Same-learner correctness comes from Ticket P (one consumer per learner-partition), so
this ticket takes no database lock. Create the public `src/openedx_learning/applets/cbe/api.py` and
an internal `src/openedx_learning/applets/cbe/persistence.py`.

### 1. Data structures

`api.py` is UNSTABLE (one-line module docstring "UNSTABLE: may change without a DEPR cycle", per
the `README.rst` convention; no decorator), declares `__all__`, and exposes three keyword-only
functions. It defines no new persisted types; `GradeInput`, `EvaluationResult`, `CriteriaTree`, and
`MasteryStatus` are Ticket 13.2's `data.py` types.

```
record_competency_status_batch(*, entries) -> BatchSummary
    # primary write path; entries: iterable of (user_id, GradeInput)
    # BatchSummary: rows written per level, entries skipped stale, entries with no criteria (for metrics and tests)
record_competency_status_for_grade(*, user_id, grade) -> EvaluationResult
    # thin wrapper over the batch path (a batch of one); for tests, backfill, ad-hoc callers
get_mastery(*, user_id, competency_tag_id) -> MasteryStatus | None
    # latest StudentCompetencyStatus.status for (user_id, tag), or None
```

Internal to `persistence.py`: a **resolution cache** (`content_key` to `list[CriteriaTree]`,
version-stamped, invalidated on authoring writes; `CriteriaTree` is a plain dataclass, so it
serializes into the Django cache with no Django models), and a **bulk snapshot** (`(user_id,
entity_id)` to current `MasteryStatus`, plus the current leaf `source_edited_timestamp`) that feeds
both the engine and the staleness guard.

One model change remains, owned by #613 (see Files): a nullable `source_edited_timestamp` on
`StudentCompetencyCriteriaStatus`, plus a composite `(user_id, entity_id, created)` index on each
of the three status tables for the bulk read. `StudentCompetencyProcessingLock` is **not** created;
the partition is the concurrency boundary.

### 2. Logic

`record_competency_status_batch` runs four phases, no per-learner lock:
1. **Resolve (cached, learner-independent).** For each distinct `content_key` in `entries`, get its
   `CriteriaTree` list from a cache wrapping Ticket 13.2's `resolve_criteria_for_content`, keyed by
   `content_key` and version-bumped on `CompetencyCriterion` / `CompetencyCriteriaGroup` /
   `CompetencyRuleProfile` writes. Resolution runs at most once per distinct subsection, and zero
   times warm.
2. **Bulk read.** For every `(user_id, entity_id)` pair the resolved trees touch, read the latest
   status row per pair in one query per status table via a MySQL 8 window function, `ROW_NUMBER()
   OVER (PARTITION BY user_id, <entity_id> ORDER BY created DESC, id DESC)` filtered to the first
   row, backed by the composite `(user_id, entity_id, created)` index. This is the one
   performance-critical query and the only per-learner read; `get_mastery` reuses it for a single
   pair.
3. **Evaluate (pure, in memory).** Group `entries` by `user_id`. For each learner, fold their
   events in `source_edited_timestamp` order against an evolving in-memory snapshot: skip an event
   not newer than the leaf it touches (per-leaf staleness guard), else call `evaluate_trees`
   against the running snapshot and merge its result back in. The engine is unchanged; folding just
   iterates it. Diff each computed `(entity, status)` against the snapshot and keep only changes
   (persist-on-change).
4. **Persist.** In one `transaction.atomic()` per batch, `bulk_create` the accumulated append-only
   rows per table; store `source_edited_timestamp` on leaf rows; never UPDATE. The batch is
   all-or-nothing.

`record_competency_status_for_grade` is phases 1 to 4 for a single `(user_id, grade)`.

**Why no lock.** Ticket P routes all of a learner's events to one partition and the event bus gives
each partition a single consumer, so same-learner processing is never concurrent. The writes are
append-only bulk INSERTs with no cross-row conflict, so correctness needs no database lock; the
per-batch transaction only makes a batch atomic. Partition-boundary anomalies are caught by the
reconciliation job.

**Persist-only-on-change and the competency constraint.** The engine already omits competency-level
`AttemptedNotDemonstrated`, so no `StudentCompetencyStatus` row violates its
Demonstrated/PartiallyAttempted constraint (ADR-0002 §6). Do not add a partial-unique "one current
row" constraint; it would force un-setting prior rows and break ADR-0003 append-only.

**Layering / PII.** `api.py` and `persistence.py` import only `openedx_learning` /
`openedx_tagging` models, Ticket 13.2's internal modules, and `django.core.cache` (no new
dependency): no `openedx-platform`, `opaque_keys`, or grading imports. Re-export the public
functions from the `openedx_learning` umbrella `api.py` facade (#613). The `Student*Status` tables
carry a `user_id` FK and are PII; confirm #613's `make pii_check` annotations exist.

**Test strategy.** DB tests exercise the batch API directly; the partition boundary is Ticket P's,
so no concurrency test lives here. Cover: a multi-learner batch records each learner up the tree;
two same-learner events in one batch fold in timestamp order (the second sees the first); a stale
event is skipped; an unchanged status writes no row; a no-criteria entry records nothing; the batch
is all-or-nothing (patch a write to raise, assert no rows); resolution runs once per distinct
subsection (assert cache hits); `get_mastery` present/absent. The window-function read runs on the
default test DB (SQLite 3.25+ has window functions) and on the MySQL tox target
(`mysql_test_settings`).

*Example resolution prompt.*

> Implement the CBE bulk mastery recording service in `openedx-core`, on Ticket 13.2's
> `evaluate_trees` (pure) and `resolve_criteria_for_content` (learner-independent). Models come from
> #613 (ADR-0002); ADR-0003 governs append-only, ADR-0002 §6 the update flow. There is no lock:
> Ticket P guarantees one consumer per learner-partition.
>
> Create `src/openedx_learning/applets/cbe/persistence.py` with: a cached resolver wrapping
> `resolve_criteria_for_content` (Django cache, keyed by `content_key`, a version integer bumped by
> `post_save`/`post_delete` receivers on `CompetencyCriterion` / `CompetencyCriteriaGroup` /
> `CompetencyRuleProfile`); `_read_current_statuses(pairs)` bulk-reading the latest row per
> `(user_id, entity_id)` across the three status tables with `ROW_NUMBER() OVER (PARTITION BY
> user_id, <entity_id> ORDER BY created DESC, id DESC)`, returning the snapshot plus current leaf
> `source_edited_timestamp`; `_persist_changes(rows)` doing one `bulk_create` per table,
> append-only, never UPDATE.
>
> Create `src/openedx_learning/applets/cbe/api.py` (UNSTABLE docstring, `__all__`,
> `openedx_tagging/api.py` convention, no permission checks) with `record_competency_status_batch(*,
> entries)` (resolve cached per distinct `content_key`; bulk read; group by `user_id` and fold
> same-learner events in `source_edited_timestamp` order against the running snapshot, skipping
> stale ones; diff persist-on-change; one `transaction.atomic()` per batch),
> `record_competency_status_for_grade(*, user_id, grade)` (a batch of one), and `get_mastery(*,
> user_id, competency_tag_id)`.
>
> Add `from .applets.cbe.api import *` to `src/openedx_learning/api.py` (#613). In `models.py`
> (coordinate with #613) add the nullable `StudentCompetencyCriteriaStatus.source_edited_timestamp`
> and a composite `(user_id, entity_id, created)` index on each status table; do NOT add
> `StudentCompetencyProcessingLock`. Connect the cache-invalidation receivers in the umbrella
> `AppConfig.ready()`.
>
> Tests in `tests/openedx_learning/applets/cbe/test_recording.py`: multi-learner batch up the tree;
> same-learner fold in one batch; stale event skipped; unchanged status not re-recorded
> (row-count); competency `AttemptedNotDemonstrated` never written; multi-competency; no-criteria
> records nothing; batch all-or-nothing rollback; resolution cached (one query per distinct
> subsection); `get_mastery` present/absent. No `openedx-platform`, `opaque_keys`, or grading
> imports. Run `pytest`, `lint-imports`, `make pii_check`.

**Files to create and modify.**

New files:

| File | Purpose |
| --- | --- |
| src/openedx_learning/applets/cbe/api.py | Public API: `record_competency_status_batch`, `record_competency_status_for_grade`, `get_mastery`; UNSTABLE |
| src/openedx_learning/applets/cbe/persistence.py | Cached resolver, bulk latest-row read, bulk append-only persist |
| tests/openedx_learning/applets/cbe/test_recording.py | DB tests for batch recording, folding, staleness, caching, retrieval |

Modified files:

| File | Nature of modification |
| --- | --- |
| src/openedx_learning/api.py | Add `from .applets.cbe.api import *` (facade from #613) |
| src/openedx_learning/applets/cbe/models.py | Add nullable `source_edited_timestamp` on `StudentCompetencyCriteriaStatus` and a composite `(user_id, entity_id, created)` index on each status table; coordinate with #613. Do not add `StudentCompetencyProcessingLock` |
| src/openedx_learning/apps.py | Connect the resolution-cache invalidation receivers in the umbrella `AppConfig.ready()` |

**Open questions.**
- Bulk latest-row read at large batch sizes: window function vs GROUP BY-max join, and feeding many
  `(user_id, entity_id)` pairs via a values-list join rather than a large `IN`. Pick during
  implementation; the composite `(user_id, entity_id, created)` index is the requirement either way.
- Resolution-cache invalidation granularity: a global version bump on any authoring write (simple,
  correct, authoring is rare) vs per-`content_key` invalidation. Recommended: the version bump,
  with a TTL backstop.
- The leaf timestamp column and the composite indexes are #613's model work; see "Cross-ticket
  model dependencies".

---

## Ticket 13.4 — Grade-change event-bus batch consumer

**Scope.** Consume `PERSISTENT_SUBSECTION_GRADE_CHANGED` from the event bus and, per assigned
partition, accumulate a windowed micro-batch of `(user_id, GradeInput)` and call Ticket 13.3's
`record_competency_status_batch` once. That is the whole job: this ticket owns no evaluation,
persistence, resolution, or lock; those live in Ticket 13.3's service. The consumer stringifies
`usage_key` at this boundary so no `opaque_keys` import enters `openedx-core`, dead-letters a poison
event without failing the batch, and commits offsets only after the batch commits.

**Use case.** As a learner, when the grade for a subsection I completed changes, the platform
reacts automatically: the listener hands the grade to the recording service and my competency
mastery is recomputed and recorded, with no manual step.

**Acceptance criteria.** Confirmed by a PR reviewer via automated unit tests exercising the
receiver directly. Each Then names an observable result.

```
Scenario: A grade-change event drives recording
  Given a PERSISTENT_SUBSECTION_GRADE_CHANGED event for a learner and subsection
  When the listener receives it
  Then it calls record_competency_status_for_grade with a GradeInput built from the payload
  And usage_key is passed as a string (no opaque_keys import)

Scenario: An event for a subsection with no criteria completes cleanly
  Given an event for a subsection with no competency criteria attached
  When the listener receives it
  Then the listener completes without error (the no-op is the service's behavior, not re-implemented here)

Scenario: Transient database contention is retried
  Given recording fails with a transient database error (deadlock or lock-wait timeout)
  When the listener handles the event
  Then it retries with bounded backoff
  And if retries are exhausted it lets the error propagate so the event is left unhandled for redelivery

Scenario: A non-transient error is not retried
  Given recording fails with a non-transient error
  When the listener handles the event
  Then the error propagates immediately without retry

Scenario: Redelivery of the same event is a no-op
  Given an event that was already fully recorded
  When the same event is delivered again (at-least-once delivery)
  Then the listener passes the event to the service once and completes without error (idempotency is the service's guarantee)
```

**Technical details.** Create a batch-accumulating event-bus consumer for the openedx-events
`PERSISTENT_SUBSECTION_GRADE_CHANGED` signal. This ticket owns consumption and batching only: no
evaluation, persistence, resolution, or lock.

### 1. Data structures

Per event, map the payload to a `GradeInput` (Ticket 13.2's type):

| GradeInput field | From payload | Note |
| --- | --- | --- |
| content_key | `str(usage_key)` | stringified at the boundary; keeps `opaque_keys` out of openedx-core |
| percent | `100 * weighted_graded_earned / weighted_graded_possible` | on the MVP Grade rule's percent scale (0 to 100); guard `weighted_graded_possible == 0` |
| attempted | `first_attempted is not None` | unattempted differs from attempted-and-failed |
| source_edited_timestamp | `subsection_edited_timestamp` | drives Ticket 13.3's staleness guard |

### 2. Logic

The consumer subscribes to the event topic in a consumer group. Ticket P sets the produce-time
partition key to `user_id`, and the event bus gives each partition to one consumer in the group, so
a learner's events are read by exactly one consumer in order. Per assigned partition the consumer:
1. Accumulates a micro-batch bounded by size or time, whichever comes first.
2. Maps each payload to `(user_id, GradeInput)`; a per-event mapping or validation failure is
   isolated and dead-lettered, never allowed to fail the batch.
3. Calls `record_competency_status_batch` once with the surviving entries.
4. Commits offsets only after the batch transaction commits. A transient database error retries the
   batch with bounded backoff, then leaves offsets uncommitted for redelivery. At-least-once
   delivery is safe because recording is idempotent (persist-on-change plus the staleness guard).

The stock openedx-events consumer dispatches one signal per message and cannot batch, so this
ticket needs a batch-capable consumer loop (a management command running a custom consumer, or a
batching wrapper over the event-bus client). The in-process Django signal receiver is ruled out: it
processes per event inside the caller and cannot batch or partition.

**Layering.** Imports the openedx-events signal/consumer and the CBE `api` only. No
`openedx-platform`, no `opaque_keys` (stringify at the boundary), no grading imports. Bump
openedx-events to the release shipping the event (#545/#587) and confirm the event-bus consumer
library (Kafka or the Redis variant) is a dependency.

*Example resolution prompt.*

> Implement the CBE grade-change batch consumer in `openedx-core`, on Ticket 13.3's
> `record_competency_status_batch` and the openedx-events `PERSISTENT_SUBSECTION_GRADE_CHANGED`
> signal (#545/#587), consumed over the event bus. Ticket P sets the partition key to `user_id`.
>
> Create `src/openedx_learning/applets/cbe/consumer.py` with a batch consumer that, per assigned
> partition, accumulates a micro-batch bounded by size or time, maps each payload to `(user_id,
> GradeInput)` (`content_key = str(usage_key)`, no `opaque_keys`; `percent = 100 *
> weighted_graded_earned / weighted_graded_possible` with a zero-possible guard; `attempted =
> first_attempted is not None`; `source_edited_timestamp = subsection_edited_timestamp`),
> dead-letters any per-event mapping failure, calls `record_competency_status_batch(entries=...)`
> once, and commits offsets only after the batch commits with bounded batch-level retry on transient
> DB errors. Add a management command to run it. Do not add evaluation, persistence, resolution, or
> lock logic.
>
> Tests in `tests/openedx_learning/applets/cbe/test_consumer.py`: a batch of events builds the
> correct `GradeInput`s and calls `record_competency_status_batch` once (assert `content_key` is a
> `str`); a poison event is dead-lettered and the batch still commits the rest; a transient DB error
> retries the batch then leaves offsets uncommitted; duplicate delivery writes no new rows. No
> `openedx-platform`, `opaque_keys`, or grading imports. Run `pytest` and `lint-imports`.

**Files to create and modify.**

New files:

| File | Purpose |
| --- | --- |
| src/openedx_learning/applets/cbe/consumer.py | Batch event-bus consumer: accumulate micro-batch, map payloads, call `record_competency_status_batch`, manage offsets |
| src/openedx_learning/applets/cbe/management/commands/consume_cbe_grades.py | Entry point to run the consumer |
| tests/openedx_learning/applets/cbe/test_consumer.py | Consumer tests (mapping, poison isolation, batch retry, redelivery) |

Modified files:

| File | Nature of modification |
| --- | --- |
| requirements/base.in | Bump openedx-events to the event-shipping release; add the event-bus consumer library if not present |

**Open questions.**
- Batch-capable consumer: a custom loop vs contributing batch support upstream to
  openedx-events/the event-bus client. Confirm what the deployment's bus (Kafka vs Redis) exposes
  for batch polling.
- Micro-batch bounds (max size, max time) to tune latency against commit amortization.
- Dead-letter destination and alerting for poison events.
- Final payload field names pending #545/#587.

---

## Ticket P — [openedx-platform] Per-learner event partitioning (required)

*This ticket lives in **`openedx-platform`, not `openedx-core`**, so it has no `.importlinter`
concerns in this repo. It is **correctness-critical**, not an optimization.*

**Use case.** As an Open edX operator running CBE, I want consumption of
`PERSISTENT_SUBSECTION_GRADE_CHANGED` events partitioned by learner, so that every learner's grade
events are processed serially by one consumer, which is what keeps `openedx-core`'s mastery
recording correct under concurrent delivery.

**Description.** Ticket P is the partitioning that replaces a per-learner database lock. The
emitter sets the event's partition key to `user_id`, so every event for a learner lands on one
partition; the event bus gives each partition a single consumer (Ticket 13.4), so a learner's
events are processed serially by construction and two workers can never record conflicting rows for
one learner. Different learners spread across partitions and process in parallel, so the design
scales horizontally by partition count. The partition count is **fixed**: changing it reshuffles
learners across partitions and can briefly break single-owner-per-learner, which is exactly the
anomaly the reconciliation command (Ticket R) heals. Without Ticket P, `openedx-core` has no
same-learner concurrency boundary, so this work is required, not deferrable.

Out of scope: event emission/production of `PERSISTENT_SUBSECTION_GRADE_CHANGED` (openedx-events
PRs #545/#587 plus a separate emitter ticket); any change to `openedx-core`; global ordering across
different learners (only per-`user_id` ordering matters).

**Acceptance criteria.** Verifiable by inspecting dispatch routing and worker logs.

```
Scenario: Two events for the same learner are processed serially
  Given two PERSISTENT_SUBSECTION_GRADE_CHANGED events for the same user_id
  When they are dispatched for consumption
  Then they are routed to the same ordered stream (queue or partition)
  And the second is not processed until the first completes

Scenario: Events for different learners are not serialized against each other
  Given events for two different user_ids
  When they are dispatched for consumption
  Then they may be processed concurrently on different workers

Scenario: The routing key is derived from user_id
  Given any PERSISTENT_SUBSECTION_GRADE_CHANGED event
  When it is dispatched
  Then its routing/partition key is a deterministic function of user_id only

Scenario: Emission is unaffected
  Given the event is produced by the existing emitter
  When this change is deployed
  Then event production is unchanged and only consumption routing is affected
```

**Technical details.** Set the partition/ordering key to `user_id` at produce time for
`PERSISTENT_SUBSECTION_GRADE_CHANGED`, in the emitter. Fix the topic's partition count and run the
consumer group so each partition has one consumer (the bus guarantees single ownership). No payload
or schema change; only the produce-time key. Keep the change to producer routing config; no
business logic.

**Context.**
- Epic 13.1 (#643), Ticket 13.3: the `openedx-core` bulk recording service whose same-learner
  correctness this partitioning provides.
- openedx-events PRs #545/#587: define the event and `PersistentSubsectionGradeData`; emission is
  separate.
- ADR `docs/openedx_learning/decisions/0001-competency-criteria-location.rst`: core owns the
  consumer and consumes the event directly.
- The existing `openedx-platform` emitter and event-bus wiring for `openedx-events` is the code to
  modify.

**Files to create and modify.**

| File | Nature of modification |
| --- | --- |
| openedx-platform emitter for `PERSISTENT_SUBSECTION_GRADE_CHANGED` | Set the produce-time partition/ordering key to `user_id` |
| openedx-platform event-bus topic/consumer-group config | Fixed partition count; one consumer per partition in the group |

**Open questions.**
- Partition count `N`: fixed, sized for target parallelism; a change requires a reconciliation
  sweep (Ticket R).
- Bus variant (Kafka vs Redis) determines the exact partition-key API; confirm before implementation.
- Coordinate with the emitter ticket (#545/#587 plus the separate emitter) that produces the event.

---

## Ticket R — Competency mastery reconciliation command (backstop)

**Use case.** As an Open edX operator, after a deliberate partition-count change (or if monitoring
flags drift), I want a command that recomputes affected learners' derived competency levels from
their current leaf statuses and appends corrections, so the rare partition-reshuffle anomaly is
healed without waiting for organic grade events.

**Description.** Same-learner processing is serial as long as the learner-to-partition mapping is
stable (Ticket P). Changing the partition count reshuffles learners and can briefly let two
consumers touch one learner, appending a derived roll-up from a stale sibling snapshot. Leaf rows
are always correct (each is a pure function of its own grade); only derived group/competency rows
can drift, and any drift self-heals on the learner's next relevant grade event. This command is the
backstop for a learner who gets no further event. It is **on-demand only** (no scheduled sweep in
the MVP), append-only, and idempotent. Out of scope: recomputing leaves, lowering a status, and any
change to the live recording path.

**Acceptance criteria.** Verified by automated tests.

```
Scenario: A drifted derived row is corrected
  Given a learner whose stored competency row differs from a recompute from their current leaves
  When heal_competency_mastery runs for that learner
  Then a corrected derived row is appended and becomes the current status
  And no leaf row is written

Scenario: A matching learner and a re-run write nothing
  Given a learner whose derived rows already match a recompute from their current leaves
  When heal_competency_mastery runs
  Then no new rows are written
```

**Technical details.** A management command `heal_competency_mastery` (scoped by learner id range,
single learner, or competency) reusing Ticket 13.2's engine and Ticket 13.3's bulk read/persist:
bulk-read current leaf/group/competency rows for the scope, recompute derived levels from the
leaves, and `bulk_create` corrected derived rows only where the stored current row differs; never
write leaf rows; never UPDATE. Idempotent by append-only plus persist-on-change.

**Files to create and modify.**

| File | Purpose |
| --- | --- |
| src/openedx_learning/applets/cbe/management/commands/heal_competency_mastery.py | On-demand, scoped reconciliation command |
| tests/openedx_learning/applets/cbe/test_reconciliation.py | Reconciliation tests |

---

## Out of scope (separate work)

**Out of scope for this epic (may become future tickets):**

- **Ticket D — sending grades/competencies to downstream credentialing.** Completely out of
  scope; the architecture for this is not defined.
- **Ticket E — surfacing competencies to learners and instructors.** Handled by us and the
  Aspects team in future tickets for Willow. This includes the UI-facing CRUD REST API over
  the `Student*Status` tables (which will likely reshape the data for the frontend rather
  than expose the backend tables directly).

**Also out of scope for this epic:**

- The `openedx-events` production/emission of subsection-grade-changed events.
- Rule types other than `Grade` (`View` / `MasteryLevel` deferred — a non-Grade rule raises
  `NotImplementedError` during the MVP).
- Criteria on courses, sections, units, or problems (MVP is subsection only).
- Course-run-date windowing.
- Re-evaluation on later criteria changes or regrades, and any lowering of a status
  (forward-only per decision — a separate follow-up).
- Recompute-on-read for derived levels. Group/competency levels are materialized (ADR-0002 §6,
  deliberately, for dashboard read performance). Computing them on read would remove the write-skew
  hazard entirely, but that reopens ADR-0002 and is not in scope here.
- Any REST or UI surface.

---

## Cross-ticket model dependencies to route into #613

Two model additions the design needs are not in ADR-0002 and belong in #613's model work:

- **Leaf `source_edited_timestamp` column** on `StudentCompetencyCriteriaStatus` (nullable): the
  per-leaf staleness guard (Ticket 13.3).
- **Composite `(user_id, entity_id, created)` index** on each of the three `Student*Status` tables:
  backs Ticket 13.3's bulk latest-row-per-`(user_id, entity)` read; confirm or extend the ADR-0002
  §5 indexes to cover it.

Separately, #613 must register the new `openedx_learning` package in `.importlinter`
(`root_packages` plus a layering rule) before any of 13.2 through 13.4 can pass `lint-imports`.
`StudentCompetencyProcessingLock` is no longer needed: the partition (Ticket P) is the concurrency
boundary.

---

## Concurrency: chosen approach and rejected alternatives

The chosen concurrency approach is the partitioned-batch design: same-learner correctness comes
from one consumer per learner-partition (Ticket P), the write path is bulk per micro-batch (Ticket
13.3), and an on-demand reconciliation command (Ticket R) heals the rare partition-boundary
anomaly. The two rejected alternatives, a per-learner database row lock and a lock-free "assume
conflicts are rare" design, and the reasoning for choosing partitioning over both, are recorded in
ADR-0004.
