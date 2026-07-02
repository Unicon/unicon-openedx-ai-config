# 2.12 Sprint Zero: Competency Taxonomy Issue Re-Organization Plan

## Context

Why this exists: the 2.12 sprint's Competency-Based-Education (CBE) / "Competency
Taxonomy" work is captured across four planning documents of varying maturity and 13 real
GitHub issues that block each other heavily. Issue #613 blocks essentially everything
(accepted and unavoidable, it is the foundational data model), but on top of that the other
issues form several hard chains that force frontend to wait on backend and force two
placeholder tickets to stay unwritten until mid-sprint.

The goal of this plan is **not implementation**. It is to decide how to write/split/combine
the *issues themselves* so they block each other less, strictly following KISS (no new
abstractions, no speculative flexibility), and to pick a preferred organization for sprint
zero. The analysis was produced by the software-architect agent (dependency analysis +
alternatives) and evaluated by the business-analyst agent (scope, sizing, sprint mechanics);
their combined recommendation is in the [Recommendation](#recommendation) section.

### Scope of this analysis

The 13 in-scope GitHub issues (openedx/openedx-core): **#613, #614, #615, #616, #617, #618,
#620, #621, #622, #623, #624, #625, #627**. They map to use cases **UC 1** (taxonomy type),
**UC 2** (competency-management entry point), and **UC 4** (competency ID field). The heavier
UCs (5, 6, 10, 11, 13 and the learner Progress-tab work) are later sprints.

**Excluded (out of scope, per `In Scope _ Out of Scope.csv`):** UC 3 (view competency
statement), UC 7 (superseded association formulation), UC 8 (associations to programs /
OpenCraft dependency), UC 9 (count competencies per content), UC 12 (Course-Author permission
scoping); plus always-out items: Rubrics, Staff Progress Tracking, pilot-partner feature
requests. None of these have issues in the 13-item set. Two live leak vectors are flagged
under [Risks](#risks--conditions).

---

## Part 1 — Cross-reference map

Authority order: GitHub issue bodies + `Markdown Github Issues.md` are authoritative and match
1:1 on the #613–#627 numbering. The BA CSV (`Axim 2.12 Github Issues - Sheet2.csv`) supplies
the older UC numbering and fills gaps only.

| GitHub | Title (short) | Type | Markdown doc | BA CSV UC# | Notes |
|--------|---------------|------|--------------|------------|-------|
| #613 | CBE core data models | BE | Match | 5.1 + 1.1 | **Straddles UC1 + UC5** — far larger than a UC1 marker (see K2) |
| #614 | Create/Import accept Taxonomy Type | BE | Match | 1.2 | Additive write field |
| #615 | Type dropdown in import flow | FE | Match | 1.4 | |
| #616 | Type badge on Taxonomies page | FE | Match | 1.5 | |
| #617 | Workflow for Taxonomies dropdown (design) | UXD | Match | 1.6 | CSV tags "Backlog / Nice-to-have" |
| #618 | GET endpoint returns Taxonomy Type | BE | Match | 1.3 | Additive read field |
| #620 | Studio Home dropdown / filtering | FE (placeholder) | Match | 1.7 | CSV "Backlog / Nice-to-have"; scope set by #617 |
| #621 | Release docs: usage type | Docs | Match | 1.8 | |
| #622 | UX designs: actions menu | UXD | Match | 2.1 | |
| #623 | Competency Management entry point | FE (placeholder) | Match | 2.2 | Scope set by #622 |
| #624 | Release docs: separate screens | Docs | Match | 2.3 | |
| #625 | Competency ID field strategy (spike) | Arch | Match | 4.1 | ~8h sprint-zero budget |
| #627 | Add Competency ID field | BE (placeholder) | Match | 4.2 | May close with no code if spike picks `external_id` |

**Orphans / flags:**
- No GitHub issue yet, correctly later sprints: BA CSV items 4.3–4.7, all of UC 5/6/10/11/13,
  Student-Progress UCs.
- **#613 conflation:** its body already implements the whole UC 5.1 criteria/rule/student-status
  model tree (`CompetencyCriteriaGroup`, `CompetencyCriteria`, `CompetencyRuleProfile`, 3× status
  models, `django-simple-history`, ~10 indexes, PII annotations). Only the tiny
  `CompetencyTaxonomy` MTI marker gates this sprint. See K2.
- **ADR numbering discrepancy:** issues correctly cite `docs/openedx_learning/decisions/0002` &
  `0003`; the CSVs call them "ADR 0023/0024" (stale external numbering). Housekeeping item.

---

## Part 2 — Dependency & blocker graph

Edges are drawn from the issue bodies. **#613 blocks nearly everything and that is accepted**
(it is the MTI parent model); the analysis targets the *other* edges.

```
            #613 [BE] CBE core data models  (accepted root; oversized — see K2)
              │ (H)              │ (H)                 │ (H, weak*)
              ▼                  ▼                     ▼
       #614 [BE] Create/     #618 [BE] GET         #627 [BE ph] Competency ID
       Import accept type    returns type          field  ◄──(H)── #625 [Arch] ID spike
         │ (H)   │ (H)          │ (H)
         ▼       └──────┐       ▼
   #615 [FE] import     └──► #616 [FE] type badge  ◄--(S)-- #622 [UXD] actions-menu design
   type dropdown              (needs #618)                       │ (H)
                                                                 ▼
   #617 [UXD] dropdown workflow ──(H)──► #620 [FE ph] home        #623 [FE ph] mgmt entry point
                                          dropdown / filtering

   Docs leaves: #621 (usage type) ◄--(S)-- #615/#616 ;  #624 (separate screens) ◄--(S)-- #622/#623
```
`(H)` hard, `(S)` soft/convenience. `*` #627→#613 is weak: it may not be a schema change at all.

**Hard edges (with justification):**
- **#613 → #614, #618** — both need the `CompetencyTaxonomy` model (`#618` does
  `hasattr(obj, 'competencytaxonomy')`). Accepted root.
- **#614 → #615** — the dropdown POSTs `taxonomy_type`; the Create/Import API must accept it to
  verify end-to-end.
- **#614 → #618** — share the single `"competency"` constant; read path reads the write path's model.
- **#618 → #616** — the badge reads `taxonomyType` from the GET/list response.
- **#617 → #620** — #620's body: "Depends on the outcome of #617"; it cannot even be *written*
  until #617 picks Option A/B/C (scope = navigation-only vs. +creation vs. label-fix + filtering).
- **#622 → #623** — #623 blocked on #622's navigation-model/label decision.
- **#625 → #627** — #627 blocked on #625; if the spike picks `external_id`, #627 closes with no code.

**Soft edges:** #616 → #622 (badge gives visual context; design proceeds on mockups);
#615/#616 → #621 and #622/#623 → #624 (docs read best after the feature but can be drafted in
parallel).

**Critical path** (ignoring accepted #613 root): `#613 → #614 → #618 → #616` (BE model → write API
→ read API → badge), with `#614 → #615` as a parallel branch needing only #614. This BE→BE→FE
chain is the real bottleneck. UC 2 (`#622 → #623`) and UC 4 (`#625 → #627`) are short
design/spike→placeholder chains that run fully in parallel.

---

## Part 3 — KISS dependency-reduction moves

Each move names the exact issues and the edges it removes. No new abstractions; levers are
additive-API design, thin-slice splitting, early decisions, and de-duplication.

- **K1 — Contract-first decoupling (free, do unconditionally).** Define the `"competency"`
  constant + write `ChoiceField` in **#614** and the read `SerializerMethodField` in **#618**.
  Because `taxonomy_type` is additive/null-default, freeze the request/response contract on day
  one; **#615** builds against the request contract and **#616** against the response shape using
  fixtures/stubs, integrating on merge. Converts `#614→#615` and `#618→#616` from *merge-blocking*
  to *verify-on-merge*, so FE and BE run in parallel. Cost: discipline only (K6 guards the failure).

- **K2 — Split #613** into **#613a** (`CompetencyTaxonomy` MTI marker + migration + PII annotation;
  a real 1–2 day ticket) and **#613b** (the UC5 criteria/rule/student-status tree; epic-sized,
  deferred to the UC5 sprint). `#614`/`#618` then depend on the small #613a, and the oversized tree
  leaves this sprint's critical path. **Condition:** copy #613b's acceptance criteria verbatim
  (PII, `simple-history`, delete-protection) so nothing drops.

- **K3 — Resolve the #625 spike in sprint zero.** It is a decision (~8h architect budget), not
  construction, and leans toward reusing `external_id`. Outcome (a): **#627 closes with no code**
  and the UC4 branch evaporates. Outcome (b): #627 becomes a concrete thin additive-field ticket.
  Either way removes a mid-sprint blocking spike.

- **K4 — Fold placeholders into design-spike DoD** (make "write the impl ticket" a deliverable of
  #617→#620 and #622→#623). Collapses those cross-issue edges. **BA recommends AGAINST this** — see
  Recommendation.

- **K5 — Merge docs #621 + #624** into one "CBE authoring docs & release notes (2.12)" issue (same
  `docs.openedx.org` target, identical boilerplate). De-duplication, low risk.

- **K6 — Guardrail (not a move):** whatever #617 decides, keep any filtering/tab scope *inside*
  #620; do not let it expand #616 or #623, and do not let #622/#625/#617 pull the out-of-scope UCs
  back in. Option C (label-fix) keeps #620 smallest.

---

## Part 4 — Alternatives (pros / cons)

### Option 0 — Leave as-is (baseline)
- **Changes:** none. 13 issues as written.
- **Graph:** full graph above; critical path `#613 → #614 → #618 → #616` plus three parallel tails.
- **Pros:** zero reorg cost; issues are already well-written with acceptance criteria and explicit
  dependencies; no risk of a careless split.
- **Cons:** badge gated behind two BE issues in series *plus* the oversized #613; FE scheduled
  behind BE merges rather than built in parallel; #613 conflates UC1 + UC5 (a 40h+ tree on the UC1
  foundation); duplicate doc issues; placeholders un-writable until mid-sprint.

### Option A — Contract-first only (K1)
- **Changes:** add a contract-freeze line to #614/#618 and a fixture-build note to #615/#616.
- **Graph:** same topology, but `#614→#615` and `#618→#616` downgrade to verify-on-merge.
- **Pros:** biggest parallelism gain for the least change; leans on an API property that already
  exists; fully reversible.
- **Cons:** relies on discipline; a late contract change still forces FE rework; does nothing about
  #613's size, the placeholders, or the duplicate docs.

### Option B — Contract-first + thin-slice + resolve spike (K1 + K2 + K3)
- **Changes:** split #613 → #613a/#613b (defer #613b to UC5 sprint); resolve #625 in sprint zero
  (close or rewrite #627); apply the K1 contract freeze.
- **Graph:** critical path shortens to *small* `#613a → #614 → #618 → #616`; UC4 branch vanishes or
  becomes a thin standalone; #613b exits the sprint.
- **Pros:** removes the set's two structural risks (oversized foundation, mid-sprint blocking spike)
  using only splitting + early decision; every resulting issue fits the 1–2 day norm; UC1/UC5 are
  correctly separated bounded concerns.
- **Cons:** moderate planning churn now; deferring #613b needs BA/PM buy-in; the split must not drop
  acceptance criteria.

### Option C — Full remix (K1–K5)
- **Changes:** Option B, plus fold #620 into #617's DoD and #623 into #622's, and merge #621 + #624.
- **Graph:** flattest; fewest standing issues and cross-issue blockers.
- **Pros:** fewest issues/blockers; design spikes own their follow-through; doc de-duplication.
- **Cons:** highest planning cost; folding placeholders removes public, contributor-claimable backlog
  units (bad for open-source visibility); risk of over-optimizing a 13-issue set.

---

## Recommendation

**Adopt Option B + apply K1 unconditionally + pull K5 (docs merge) forward from Option C. Hold K4
(keep the placeholder issues standing). Enforce the K6 guardrail regardless of option.**

This is the architect's lean (B + unconditional K1) refined by the business-analyst on sprint
mechanics: take the docs merge (K5) because #621/#624 are never independently valuable, but keep
#620/#623 as standing, clearly "design-blocked" placeholder issues because this is public,
community-reviewed work and a claimable backlog issue is worth far more than a bullet buried in a
design ticket's definition-of-done. Full Option C over-optimizes a 13-issue set and trades away
that community visibility for negligible tidiness.

Why B over 0/A: it is the flattest arrangement that (a) keeps every committed UC1/UC2/UC4 issue
inside the 1–2 developer-day norm, (b) puts a demoable author outcome (import "Competency" →
persisted → GET → badge) on the shortest critical path, (c) defers the genuinely large UC5 model
tree that the CSV schedules for a later sprint, and (d) preserves the contributor-facing backlog
that is this epic's actual sprint-zero deliverable.

### Sprint-zero actions (decisions, not construction)
1. **Split #613** → #613a (marker, this sprint) + #613b (UC5 tree, deferred), copying #613b's ACs
   verbatim (PII, `simple-history`, delete-protection).
2. **Run the #625 ID-field spike** to a decision; close or rewrite #627 on the outcome.
3. **Get the product owner's call on #617/#620** — Option A/B/C, or D (remove filtering from scope).
   This is the one blocking product question; resolve the "Backlog / Nice-to-have" vs "in scope"
   inconsistency in favor of *design-only this sprint* (#620 not committed as FE build until #617
   lands and any filtering scope is sized).
4. **Freeze the `taxonomy_type` request/response contract** (K1); note the fixture-build approach on
   #615/#616.
5. **Merge #621 + #624** into one docs issue (K5).
6. **Reconcile the ADR numbering** (housekeeping, below) before #613b is written.

### During the sprint
Build the critical path `#613a → #614 → #618 → #616`, with `#614 → #615` in parallel; run
`#622 → #623` and (if the spike kept it) `#627` as short parallel design/spike→placeholder chains.

### Risks & conditions
- **#613 split** must not drop #613b acceptance criteria (PII, history, delete-protection). One-time
  careful-copy risk.
- **K1 parallelism** depends on FE/BE honoring the frozen contract; if they can't, fall back to
  Option 0's serialized order (a schedule loss, not a correctness loss).
- **#620 is not committed FE build** until #617's design lands and any filtering scope is sized; the
  team accepts it may grow or be cut.
- **Out-of-scope leak vectors:** (1) #617 Option A/B filtering is the nose of the camel for
  UC9-style "count competencies per content" — keep it inside #620 (K6), prefer label-fix.
  (2) When #613b is scheduled, keep it data-model-only; UC7 (association targets) and UC12
  (permission scoping) must not ride in on it.

### Housekeeping — ADR numbering
On disk the CBE ADRs are `0001-competency-criteria-location`, `0002-competency-criteria-model`,
`0003-competency-criteria-versioning` under `docs/openedx_learning/decisions/`. The CSVs cite the
stale external "ADR 0023/0024" (traceable to an external "ADR 0022" renumbered on the move into the
repo). The issue bodies already cite 0002/0003 correctly; update the CSV/BA references (and any
issue that inherited "0023/0024") so the deferred #613b cites the right ADRs.

---

## How to act on this plan

This is an issue-organization plan, so "verification" is a review of the resulting backlog, not a
code run. After executing the sprint-zero actions, confirm:
- The 13-issue set becomes: **#613a, #614, #618** (BE) + **#615, #616** (FE) + **#617, #622** (design
  spikes, each referencing its placeholder) + **#620, #623** (standing placeholders, marked
  design-blocked) + **#625** (spike) + **#627** (thin ticket or closed) + **one merged docs issue**;
  **#613b** moved to the UC5 backlog.
- Re-draw the dependency graph and confirm the FE issues (#615/#616) no longer merge-block on BE, and
  that no in-scope issue references an out-of-scope UC.
- Sanity-check each new/split issue against the 1–2 developer-day norm.

Note: this plan does not itself write or edit any GitHub issues. Executing it (splitting #613,
merging the docs issues, rewriting placeholders, posting to the tracker) is a follow-up step to be
done only when approved.
