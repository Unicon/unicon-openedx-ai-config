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
materialized (stored), not recomputed on read, so a single grade change must recompute and
re-write derived rows up the tree. Under concurrent, out-of-order, multi-node delivery this is
a write-skew hazard (two overlapping evaluations for the same learner each read a stale
"current" and both append a wrong roll-up). The fix is a **single per-learner locked
transaction** around the whole resolve → read-current → evaluate → persist path. That lock and
transaction live in exactly one place: **Ticket 13.3's recording service.** The roll-up itself is
a **pure, in-memory engine (Ticket 13.2)** used as a collaborator inside that transaction. **Ticket
13.4 is a thin event adapter** that unpacks the event and calls the service. **Ticket P**
(openedx-platform) is an optional contention optimization on top; core is correct without it.

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

**Blocking dependencies.** This epic is blocked by:
- **#613** (ticket 1.1 — the CBE data model, ADRs 0002/0003). After 1.1, all models live at
  `src/openedx_learning/applets/cbe/models.py`. Note 1.1's text uses a stale path
  (`openedx_learning/apps/competencies/`); ADR 0001 governs and the correct path is
  `src/openedx_learning/applets/cbe/`.
- **Use Case ID 6**, which must land before this work can proceed.

**How the models fit together.** Competency criteria exist hierarchically via the
`CompetencyCriteriaGroup` and `CompetencyCriteria` tables. The topmost
`CompetencyCriteriaGroup` represents the competency tag itself; its children are groups for
the courses containing subsections associated with the competency, or custom groupings
defined by a platform administrator. Each `CompetencyCriteriaGroup` defines the
`logic_operator` (AND or OR) by which its `CompetencyCriteria` evaluate at that level. Each
`CompetencyCriteria` is tied to a specific subsection used as the instrument for measuring
mastery via its `rule_payload` (for example `{"op":"gte","value":75,"scale":"percent"}`, i.e.
a score of at least 75%). A criterion may defer its rule to a `CompetencyRuleProfile`, resolved by a fallback chain (see
Ticket 13.2). These models come into existence in #613 and provide the scaffolding this epic
builds on.

**ADRs to read first.**
- `docs/openedx_learning/decisions/0001-competency-criteria-location.rst` (why the listener
  lives in openedx-core, consuming the grade event directly — this adopts former alternative 8)
- `0002-competency-criteria-model.rst` (the model, the bottom-up recompute, the
  competency-level status constraint, and why derived levels are materialized)
- `0003-competency-criteria-versioning.rst` (append-only: current status = latest row,
  persist only changes)
- `0004` (this epic)

**Technical Design Document:**
[Competency Criteria Technical Design Document](https://openedx.atlassian.net/wiki/spaces/OEPM/pages/5604573185/Competency+Criteria+Technical+Design+Document)

**Prior art — Python module-interface pattern.** `src/openedx_tagging/api.py` (module
docstring: callers use the API, not the models; no permission enforcement here — the caller
authorizes) and the applet-facade pattern in `src/openedx_content/api.py` re-exporting each
applet's `api.py`.

**Prior art — content ↔ competency mapping.** A competency is a `Tag` in a
`CompetencyTaxonomy`; the association is an `oel_tagging_objecttag` row whose `object_id` is
an opaque, non-FK string (`src/openedx_tagging/models/base.py`, a case-sensitive char field,
max 255). A criterion maps to one objecttag plus a rule.

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

**Ticket 13.3 (out of scope, context only):** takes a per-learner lock, opens one `transaction.atomic()` over resolve → read-current → evaluate → persist, skips stale grades (older `source_edited_timestamp`), and appends a status row only on change (ADR-0003). If you add a transaction, lock, DB write, or staleness check to Ticket 13.2, it's in the wrong ticket.

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

**Scope.** Build the CBE applet's public Python API and the whole correctness-critical database
unit behind it:
- `record_competency_status_for_grade(*, user_id, grade)` — the single write path. In one
  `transaction.atomic()` it takes a per-learner lock, resolves the affected trees (Ticket 13.2),
  reads the learner's current statuses, runs the pure engine (Ticket 13.2), and persists the
  changed rows. The lock + transaction live here and nowhere else, which is what makes the
  feature correct under concurrent, out-of-order, multi-node delivery.
- `get_mastery(*, user_id, competency_tag_id)` — read a learner's current competency mastery
  status.

Persistence is append-only per ADR-0003 (current status = latest row) and writes a new row only
when the computed status differs from the learner's current one; this persist-only-on-change
diffing is separate from Ticket 13.2's engine omitting competency-level `AttemptedNotDemonstrated`.
The write across all three status tables and all affected competencies is atomic: all changed
rows commit together or none do. A grade older than the current leaf's grade (by
`source_edited_timestamp`) is ignored so an out-of-order event cannot regress a newer
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

**Technical details.** Create the public `src/openedx_learning/applets/cbe/api.py` and an
internal `src/openedx_learning/applets/cbe/persistence.py`.

`api.py` (marked UNSTABLE via a one-line docstring "UNSTABLE: may change without a DEPR cycle" —
no decorator, no new convention) exposes exactly two keyword-only functions and declares
`__all__`:

```
record_competency_status_for_grade(*, user_id, grade) -> EvaluationResult
get_mastery(*, user_id, competency_tag_id) -> MasteryStatus | None
```

`record_competency_status_for_grade` is the whole critical section, in one
`transaction.atomic()`:

```
with transaction.atomic():
    _lock_learner(user_id)                                   # SELECT ... FOR UPDATE on the anchor row
    trees = resolve_criteria_for_content(content_key=grade.content_key)   # Ticket 13.2
    if not trees:
        return EvaluationResult.empty()                      # nothing to record
    current = _read_current_statuses(user_id, trees)         # this ticket
    if _is_stale(grade, current):                            # older source_edited_timestamp -> ignore
        return EvaluationResult.empty()
    result = evaluate_trees(grade=grade, trees=trees, current_statuses=current)   # Ticket 13.2, pure
    _persist_changes(user_id, result, grade.source_edited_timestamp)   # this ticket
    return result
```

Why the lock and transaction live here: the engine is pure, so the read of current sibling
statuses that feeds the roll-up must sit inside the same locked transaction as the write.
Putting the lock anywhere else (or only around the write) would evaluate against a stale
snapshot. One per-learner anchor lock — not per-tree — because a single grade can touch several
competency trees; a single anchor lock gives bounded waiting and no multi-tree deadlock, and
different learners never contend.

Anchor lock target: a dedicated tiny per-learner row, `StudentCompetencyProcessingLock(user_id
unique)`; `get_or_create` it, then `select_for_update()`. Handle the `get_or_create` insert race
with the unique constraint + retry. Rejected: locking `auth_user` (intrusive) and MySQL
`GET_LOCK` (not portable; unused in this repo). The lock row is a model owned by #613 (open
question).

`persistence.py` holds `_read_current_statuses` (bulk-read the learner's latest
leaf/group/competency rows for the entities in `trees`, per ADR-0002 §5 indexes, as the
`CurrentStatuses` mapping the engine consumes) and `_persist_changes` (for each computed
`(entity, status)`, compare with the current latest row and INSERT a new row only on change;
never UPDATE; store `source_edited_timestamp` on the leaf row for the staleness guard). Do not
add a partial-unique "one current row" constraint — it would force un-setting prior rows and
break ADR-0003 append-only.

Isolation depends on the caller holding the lock: the write is a set of append-only INSERTs, so
concurrent transactions do not conflict at the row level (write-skew). Correctness therefore
comes from the per-learner lock in `record_competency_status_for_grade`, not from the database's
default isolation. `_persist_changes`/`_read_current_statuses` document that they must run inside
that locked transaction.

Layering / PII: imports only `openedx_learning` / `openedx_tagging` models and Ticket 13.2's
internal modules. The `Student*Status` tables carry a `user_id` FK and are PII; confirm #613's
`make pii_check` annotations exist.

*Example resolution prompt.*

> Implement the CBE mastery recording service and retrieval in `openedx-core`, on top of Ticket
> 13.2's engine (`evaluate_trees`) and resolution (`resolve_criteria_for_content`). Models come from
> #613 (ADR-0002); ADR-0003 governs append-only.
>
> Create `src/openedx_learning/applets/cbe/persistence.py` with `_read_current_statuses(user_id,
> trees)` (bulk-read latest leaf/group/competency rows as the `CurrentStatuses` mapping) and
> `_persist_changes(user_id, result, source_edited_timestamp)` (for each computed
> `(entity, status)`, read the current latest row — max `created`, tie-break `id` — and INSERT a
> new row only if the status differs; never UPDATE; store `source_edited_timestamp` on the leaf
> row; do not add a one-current-row constraint).
>
> Create `src/openedx_learning/applets/cbe/api.py` (docstring "UNSTABLE: may change without a
> DEPR cycle", `__all__`, `openedx_tagging/api.py` convention, no permission checks) with two
> keyword-only functions. `record_competency_status_for_grade(*, user_id, grade)`: in one
> `transaction.atomic()`, `select_for_update()` a `StudentCompetencyProcessingLock` row
> (`get_or_create` by `user_id`, unique-constraint + retry on the insert race); resolve trees
> (return empty if none); read current statuses; if the grade's `source_edited_timestamp` is not
> newer than the current leaf's stored timestamp, return without changes; run `evaluate_trees`;
> persist changes. `get_mastery(*, user_id, competency_tag_id)`: return the latest
> `StudentCompetencyStatus.status` or `None`.
>
> Add `from .applets.cbe.api import *` to `src/openedx_learning/api.py` (facade from #613). Add
> the `StudentCompetencyProcessingLock(user_id unique)` model + migration (coordinate with #613).
>
> Tests in `tests/openedx_learning/applets/cbe/test_recording.py`: passing grade records up the
> tree; unchanged status not re-recorded (row-count assertion); competency
> `AttemptedNotDemonstrated` never written; multi-competency; no-criteria records nothing;
> all-or-nothing rollback (patch a write to raise mid-call, assert no rows and unchanged
> current); stale older-timestamp grade changes nothing; repeat call is a no-op; `get_mastery`
> present/absent. Assert resolve→read→evaluate→persist runs inside a single `atomic` under the
> lock. No `openedx-platform`, `opaque_keys`, or grading imports. Run `pytest` on that module,
> `lint-imports`, and `make pii_check`.

**Files to create and modify.**

New files:

| File | Purpose |
| --- | --- |
| src/openedx_learning/applets/cbe/api.py | Public API: `record_competency_status_for_grade` (lock + transaction + orchestration), `get_mastery`; UNSTABLE |
| src/openedx_learning/applets/cbe/persistence.py | `_read_current_statuses`, `_persist_changes` (append-only-on-change, internal) |
| tests/openedx_learning/applets/cbe/test_recording.py | DB tests for recording and retrieval |

Modified files:

| File | Nature of modification |
| --- | --- |
| src/openedx_learning/api.py | Add `from .applets.cbe.api import *` (facade file created by #613) |
| src/openedx_learning/applets/cbe/models.py | Add `StudentCompetencyProcessingLock` (per-learner anchor row) + a `source_edited_timestamp` on the leaf status row — coordinate with #613 |

**Open questions.**
- The staleness guard and the per-learner lock both need model changes not in ADR-0002; see
  "Cross-ticket model dependencies to route into #613" at the end of this document.
- Latest-row read strategy (per-entity subquery vs window function) for `_read_current_statuses`
  at scale; ADR-0002 §5 indexes exist; pick during implementation.

---

## Ticket 13.4 — Grade-change event listener (thin adapter)

**Scope.** Subscribe to `PERSISTENT_SUBSECTION_GRADE_CHANGED` and, per event, translate the
payload into a `GradeInput` and call Ticket 13.3's `record_competency_status_for_grade`. That is
the whole job: this ticket owns no evaluation, no persistence, no transaction, and no lock —
those live in Ticket 13.3's service. The listener stringifies `usage_key` at this boundary so no
`opaque_keys` import enters `openedx-core`, retries on transient database contention (deadlock,
lock-wait timeout) with bounded backoff, and connects the receiver in the applet's `ready()`.

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

**Technical details.** Create `src/openedx_learning/applets/cbe/handlers.py` with a receiver for
the openedx-events `PERSISTENT_SUBSECTION_GRADE_CHANGED` signal. Read only payload attributes;
build a `GradeInput` (`content_key = str(usage_key)`; `percent` from
`weighted_graded_earned/possible`; `attempted` from `first_attempted`; `source_edited_timestamp`
from `subsection_edited_timestamp`) and call `record_competency_status_for_grade`. Wrap the call
in a bounded retry-with-backoff that catches transient DB errors (deadlock 1213, lock-wait timeout
1205) and re-raises on exhaustion so the event is treated as unhandled. Idempotency and the
no-criteria no-op are properties of the service, not the adapter — the listener does not
re-implement them. Connect the receiver in the CBE applet's app config `ready()` (created by
#613).

Layering: imports the openedx-events signal and the CBE `api` only. No `openedx-platform`, no
`opaque_keys` (stringify at the boundary), no grading imports.

*Example resolution prompt.*

> Implement the CBE grade-change listener in `openedx-core`. Depends on Ticket 13.3's
> `record_competency_status_for_grade` and the openedx-events `PERSISTENT_SUBSECTION_GRADE_CHANGED`
> signal (PRs #545/#587).
>
> Create `src/openedx_learning/applets/cbe/handlers.py` with a receiver that reads only payload
> attributes, builds a `GradeInput` (`content_key = str(usage_key)` — do NOT import
> `opaque_keys`; `percent` from `weighted_graded_earned/possible`; `attempted` from
> `first_attempted`; `source_edited_timestamp` from `subsection_edited_timestamp`), and calls
> `record_competency_status_for_grade(user_id=..., grade=...)`. Wrap the call in a bounded
> retry-with-backoff catching transient DB errors (deadlock, lock-wait timeout); re-raise on
> exhaustion so the event is left unhandled for redelivery. Do not add evaluation, persistence,
> transaction, or lock logic here — the service owns all of it. Connect the receiver in the CBE
> applet's app config `ready()` (from #613).
>
> Tests in `tests/openedx_learning/applets/cbe/test_handlers.py`: event builds the correct
> `GradeInput` and calls the service (assert `content_key` is a string); no-criteria event
> completes cleanly with no writes; transient DB error is retried then propagates on exhaustion;
> duplicate delivery writes no new rows. No `openedx-platform`, `opaque_keys`, or grading imports.
> Run `pytest` on that module and `lint-imports`.

**Files to create and modify.**

New files:

| File | Purpose |
| --- | --- |
| src/openedx_learning/applets/cbe/handlers.py | Event receiver: payload → `GradeInput` → recording service, with bounded retry |
| tests/openedx_learning/applets/cbe/test_handlers.py | Listener tests (payload mapping, clean no-op, retry, redelivery) |

Modified files:

| File | Nature of modification |
| --- | --- |
| src/openedx_learning/apps.py (or applets/cbe app config) | Connect the receiver in `ready()` (app config created by #613) |

**Open questions.**
- Dispatch/redelivery mechanism (in-process Django signal vs openedx-events event-bus consumer)
  is unresolved pending #545/#587 and the deployment choice. The bounded retry is
  transport-agnostic; upstream redelivery semantics depend on this.
- Final payload field names pending #545/#587.

---

## Ticket P — [openedx-platform] Per-learner event serialization (optional)

*This ticket lives in **`openedx-platform`, not `openedx-core`**, so it has no `.importlinter`
concerns in this repo. It is a contention optimization, not a correctness requirement.*

**Use case.** As an Open edX operator running CBE at scale, I want consumption of
`PERSISTENT_SUBSECTION_GRADE_CHANGED` events to be serialized per learner, so that a burst of
grade changes for one learner is processed one-at-a-time and rarely contends for
`openedx-core`'s per-learner database lock, keeping grade-driven competency recomputation fast.

**Description.** `openedx-core`'s recording service (Ticket 13.3) is already correct under
concurrent, out-of-order, multi-node delivery because of its per-learner lock. This ticket does
not change that: it reduces contention by dispatching events for a given `user_id` to
consumption serially, so overlapping events for one learner rarely reach the core lock at the
same time.

Explicit non-goal (of correctness): core is correct without this work. This is a
throughput/contention optimization only. If descoped or deferred, CBE mastery recording is still
correct, just potentially higher-contention under bursty grading.

Out of scope: event emission/production of `PERSISTENT_SUBSECTION_GRADE_CHANGED` (handled by
openedx-events PRs #545/#587 plus a separate emitter ticket); any change to `openedx-core`;
global ordering across different learners (only per-`user_id` ordering matters, since the core
lock is per-learner). A 1–2 developer-day change confined to how the platform routes/dispatches
consumption.

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

**Technical details.** Route consumption so all events for a given `user_id` are processed by a
single ordered consumer, while different learners spread across the pool. The mechanism depends
on the deployed transport:
- Event-bus consumption (Kafka/Redis via `openedx-events`): set the message partition/ordering
  key to `user_id`. Cleanest option, no per-event locking.
- Celery-task consumption: dispatch the handler task with a routing key derived from `user_id`
  into a small fixed set of ordered queues (e.g. `hash(user_id) % N`), each served by a worker
  with per-queue concurrency 1. Use `acks_late` so a crash redelivers rather than drops.

Recommend the partition-key approach where the event bus is in use; fall back to Celery routing
otherwise. Either way the routing key is a pure function of `user_id`. This complements, never
replaces, the core per-learner lock. Keep the change to dispatch/routing config and consumer
wiring; no business logic.

Test strategy: unit-test that the routing/partition key equals the `user_id`-derived value;
assert same-learner events resolve to the same queue/partition and different learners can differ.
Integration-test (or manually verify) that a same-learner burst is processed serially.

**Context.**
- Epic 13.1 (#643), Ticket 13.3 — the `openedx-core` per-learner locked recording service this
  optimizes for.
- openedx-events PRs #545/#587 — define the event and `PersistentSubsectionGradeData`; emission
  is separate.
- ADR `docs/openedx_learning/decisions/0001-competency-criteria-location.rst` — core owns the
  listener and consumes the event directly.
- The existing `openedx-platform` consumer wiring for `openedx-events` (event-bus consumer management
  command or Celery signal-receiver task) is the code to modify.

**Files to create and modify.** Concrete paths live in `openedx-platform` and depend on its transport
wiring; identify them during implementation. Indicative modified files:

| File | Nature of modification |
| --- | --- |
| openedx-platform event-bus/consumer config (transport-dependent) | Set partition/ordering key to `user_id` for this event, or route the consuming Celery task by a `user_id`-derived key into per-learner-ordered queues |
| openedx-platform consumer/worker settings | Ensure per-queue/per-partition single-ordered consumption; `acks_late` for the Celery path |

**Open questions.**
- Transport in the target deployment (event bus vs Celery) determines the mechanism and files.
  Confirm before implementation.
- The consumption path for this event in `openedx-platform` is coupled to the emission/consumer wiring
  from #545/#587 and a separate emitter ticket; confirm it exists before this ticket starts.
- Queue count `N` (Celery path) balancing parallelism against per-learner ordering. Tune
  operationally.

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
- Recompute-on-read for derived levels. The lock exists only because group/competency levels are
  materialized (ADR-0002 §6, deliberately, for dashboard read performance). Computing them on
  read would largely dissolve the write-skew, but that reopens ADR-0002 and is not in scope here.
- Any REST or UI surface.

---

## Cross-ticket model dependencies to route into #613

Two model changes the design needs are not in ADR-0002 and belong in #613's model work:

- **Leaf `source_edited_timestamp` column** on `StudentCompetencyCriteriaStatus` — required for
  the same-leaf staleness guard (Ticket 13.3).
- **`StudentCompetencyProcessingLock(user_id unique)`** per-learner anchor row — the lock target
  for Ticket 13.3's recording service.

---

## Alternative approach: assume conflicts are rare (no locking)

A stakeholder engineer judged concurrent same-learner conflicts unlikely. This section
records, for completeness, the design that takes that judgment at face value and
deliberately omits the concurrency machinery. It is an alternative to the main design, not
a revision of it.

**Premise and what we drop.** We assume overlapping evaluations for one learner are rare
enough that a transient wrong derived row is acceptable, and we drop the concurrency
machinery entirely: no per-learner lock, no `StudentCompetencyProcessingLock` table, and no
lock-holding transaction around the read-current → evaluate → persist path. Ticket 13.3's
recording service keeps a plain `transaction.atomic()` so a single event's writes across the
three status tables stay all-or-nothing, but there is no `select_for_update` and no anchor
row, so the `StudentCompetencyProcessingLock` model dependency (and its route into #613)
disappears. Ticket 13.2 (pure engine) and Ticket 13.4 (thin adapter) are unchanged. Keep the
same-leaf timestamp guard: it addresses same-leaf out-of-order staleness (an older grade
arriving later), which is a distinct concern from cross-leaf write-skew and is cheap to
retain. Ticket P remains a useful contention reducer but is no longer a lock optimization.

**Effect of a conflict.** When two evaluations for one learner overlap, each may read a
stale snapshot of sibling leaf statuses and append a group/competency roll-up computed from
an incomplete picture. The consequence is narrow:

- The blast radius is one learner and only the trees the two racing events touch.
- Leaf rows are never wrong (each leaf is a pure function of its own grade); only derived
  group/competency current rows can be. No constraint is violated and nothing crashes.
- The damage is a transient wrong derived current row (for example `PartiallyAttempted`
  recorded where both leaves are actually `Demonstrated`). It is self-correcting: the next
  grade-change event for that learner recomputes from the now-complete current leaves and
  appends the corrected row. If no further relevant event ever arrives, the wrong row
  lingers indefinitely.

**How to discover a conflict.** Because history is append-only (ADR-0003), after-the-fact
recomputation and auditing are straightforward:

- A periodic or on-demand reconciliation job recomputes each learner's derived levels from
  their current leaf statuses and compares against the stored current derived row, flagging
  mismatches.
- Optional lightweight logging or metrics around same-learner processing can surface
  overlapping executions, giving an early signal of how often the assumption is violated.

**Mitigation and error handling.** In rough order of cost:

- (a) Do nothing and rely on self-correction from normal grade activity.
- (b) A lightweight optimistic check at write time: just before appending, re-read the
  sibling leaf statuses the roll-up depended on; if they changed, recompute once and retry.
  No lock, cheap, and it closes most of the race window.
- (c) An idempotent "recompute this learner / this competency" management command and/or
  the reconciliation-heal job, which appends corrected rows.

All three are safe: append-only plus persist-on-change means every one of them is idempotent
and none can corrupt data. They only ever add a corrected current row.

**When this is acceptable, and the recommendation.** This alternative is acceptable when
conflict probability is genuinely low (few multi-criteria competencies sharing content, low
per-learner event concurrency, and per-learner upstream ordering from Ticket P likely in
place) and a transient wrong status for one learner until the next event is tolerable for the
MVP. The residual risk is a lingering wrong status when no further event arrives; option (b)
or a scheduled reconciliation job cheaply bounds it. Recommendation: acceptable for the MVP
if Ticket P ships and a reconciliation job is scheduled; revisit if dashboards surface stale
statuses.
