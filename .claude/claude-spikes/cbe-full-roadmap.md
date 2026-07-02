# CBE / Competency Taxonomy — Full In-Scope Project Plan

## Context

This document answers a follow-up question to the [2.12 issue re-organization plan](have-a-look-at-cozy-owl.md).
That plan analyzed only the **13 written GitHub issues** (#613–#627), which cover use cases
**UC1 / UC2 / UC4**. But the full list of issues *to create* is much longer — it lives in the
planning CSVs, and some of the not-yet-written items are in scope while others are out. This plan
identifies all the still-unwritten but **in-scope** work, evaluates how it changes the dependency
picture, and lays out a realistic **sprint-by-sprint** schedule (2-week sprints, no sprint zero)
across the entire in-scope feature. Depth per item is deliberately shallow — broad architectural
strokes only, no issue write-ups.

Sources: `2.12 Sprint Zero Tasks - In Scope _ Out of Scope.csv` (authoritative for scope),
`Axim 2.12 Github Issues - Sheet2.csv` (full UC list), `Markdown Github Issues.md`, and the
grounding ADRs `docs/openedx_learning/decisions/0002` & `0003`.

---

## Verdict

The 13 written issues cover roughly **15% of the in-scope feature by effort.** The weight sits in
the unwritten UCs: **UC5** (criteria authoring, ~14 tasks + 2 spikes), the **UC13** mastery-evaluation
engine, **UC6** rule profiles, **UC10** guardrails, **UC11** copy, plus the **entire Student-Progress
tab** (six learner UCs marked in scope). Realistic completion is **~8–9 two-week sprints** at the
stated small-team capacity. Two big rocks dominate: the UC5.1 model tree (already front-loaded into
#613) and the UC13 engine, which has a hard cross-repo dependency on edx-platform grade/completion
events.

Grounding note: the CSV's UC5.1 reference to "ADR 0023/0024" is stale numbering; the real ADRs are
`0002-competency-criteria-model.rst` and `0003-competency-criteria-versioning.rst`, which #613 cites
correctly. Same models — so the UC5 data foundation is genuinely front-loaded into UC1's data-model issue.

---

## 1. In-scope inventory

Layer legend: BE-data / BE-api / FE / UXD / Docs / Arch (spike).

### Competency Criteria Management (2.4 & 2.6)

| UC | Very-broad architectural characterization | Layers | Issue exists? |
|----|------------------------------------------|--------|---------------|
| UC1 | Competency-taxonomy usage type: MTI `CompetencyTaxonomy` + write/read serializer fields + import dropdown + card badge | BE-data, BE-api, FE, UXD, Docs | Yes (#613–#616 + docs) |
| UC2 | Competency-management entry point: taxonomy actions-menu fork ("Manage" vs "Edit") + Apply-Competencies TreeView shell | UXD, FE, Docs | Yes (#622, #623) |
| UC4 | Competency ID field: spike → add field + GET/import/export + Competency-Mgmt-page display | Arch, BE-data, BE-api, FE, Docs | Partial (#625, #627); FE + import/export unwritten |
| UC5 | Criteria authoring: AC expression-tree CRUD API over the UC5.1 models, course-search endpoint + FE, association UI, large-scale pagination | BE-data (#613), BE-api, FE, UXD, Arch, Docs | **No** (14 tasks, 2 spikes) |
| UC6 | Rule-profile management: CRUD API for `CompetencyRuleProfile` scoped org/course/taxonomy + management UI | BE-api, FE, UXD, Docs | **No** (6 tasks) |
| UC10 | Guardrails: "is-deletable" metadata computed across 6 GET endpoints + disable delete in 3 FE surfaces | Arch, BE-api, FE, Docs | **No** (11 tasks) |
| UC11 | Copy propagation: carry criteria through new course run, course export/import, copy to/from library | Arch, BE-api, Docs | **No** (7 tasks, 1 spike) |
| UC13 | Mastery evaluation engine: async listener on grade/completion events computing criterion → group → competency status, persisted append-only | BE-api (engine), Docs | **No** (2 tasks; engine is 1 very large task) |

### Student Progress (2.5 & 2.7) — learner-facing, all in scope

| UC | Very-broad architectural characterization | Layers | Issue exists? |
|----|------------------------------------------|--------|---------------|
| SP-UC2 | Progress-tab: GET criteria-for-a-course + collapsible criteria table (threshold + combination logic) | Arch, BE-api, FE, UXD, Docs | **No** (5 tasks) |
| SP-UC3 | Per-subsection + per-competency status display + the learner-status GET (read side of UC13) | BE-api, FE, UXD, Docs | **No** (5 tasks) |
| SP-UC4 | Top-level competency ("Focus Areas") summary sidebar | FE, Docs | **No** (2 tasks) |
| SP-UC7 | Static sunburst diagram of competencies / sub-competencies / assignments | FE, UXD, Docs | **No** (3 tasks) |
| SP-UC8 | Sunburst hover tooltip (faded overlay + segment info) | FE, UXD, Docs | **No** (3 tasks) |
| SP-UC10 | Recommended Next Action: spike + service/endpoint + right-panel display | Arch, BE-api, FE, Docs | **No** (4 tasks, 1 spike) |

### Explicitly EXCLUDED (do not schedule)

- **UC3** view competency statement (nice-to-have); **UC7** superseded association formulation;
  **UC8** associations to programs (OpenCraft dependency); **UC9** count competencies per content
  (nice-to-have); **UC12** Course-Author permission scoping.
- **Studio-home Taxonomies dropdown (CSV 1.6 / 1.7):** flagged *Backlog / Nice-to-have*, gated on a
  product "Option D = remove from scope" decision. Out of the committed plan unless promoted.
  (Distinct from Criteria-**UC6** rule profiles, which are in.)
- **Always-out:** Rubrics, Staff Progress Tracking, all pilot-partner requests (EDL reusable
  competencies; Calbright problem-level criteria / library criteria / release conditions).
- **Student-Progress out-of-scope:** learner-feedback design loop, author-configurable status
  language, author show/hide config, sunburst click-to-filter, material-progress %, per-section
  competency lists, section/sub-competency counts, remaining-attempts + retake (gated on
  Multiple-Attempts 2.19/2.20), instructor feedback (same gate), lock/unlock views (gated on 2.17/2.18).

---

## 2. Cross-UC dependency graph

`[613]` = the UC5.1 model tree, front-loaded into UC1's data-model issue.

```
                     [613] UC5.1 data-model tree  (CompetencyTaxonomy, CriteriaGroup,
                      Criteria, RuleProfile, MasteryStatuses, 3x StudentStatus)
                               |
    +-----------+-------------+------------+-------------+--------------+
    |           |             |            |             |             |
 UC1 write/  UC4 ID        UC5 criteria  UC6 rule     UC10 guardrails UC11 copy
 read API    field         CRUD API      profiles     (is-deletable   (propagate
 (#614/#618) BE (#627)     + assoc UI    CRUD + UI     over 6 GETs)    on copy paths)
    |                          |            |             |
 UC1 FE                        +-----+------+             |
 (#615/#616)                         |                    |
                          UC13 mastery-evaluation engine  |
                          (needs UC5 criteria + UC6 rules)|
                                     |
                          writes StudentCompetency*Status
                                     |
              +----------+-----------+-----------+-----------+
              |          |           |           |           |
           SP-UC2     SP-UC3      SP-UC4      SP-UC7 (+UC8) SP-UC10
           criteria   status      Focus-Areas  sunburst    next-action
           table      read GET    summary      + tooltip
```

Edges (one line each):
- **[613] → everything CBE.** Every criteria/rule/status feature reads or writes these tables. The
  single global blocker; nothing past UC1's badge is demoable until it lands.
- **UC5 → UC13.** The engine walks the criteria/group tree; no criteria, nothing to evaluate.
- **UC6 → UC13.** Evaluation resolves thresholds from rule profiles. Useful seam: UC13 can start
  against a hardcoded default and treat UC6 as an override layer.
- **UC5 → UC10** and **UC13 → UC10.** Guardrails protect definition rows once statuses exist; only
  meaningfully testable after the engine writes them.
- **[613] → UC11.** Copy can only propagate criteria once the tables exist.
- **UC5 → SP-UC2.** Learner criteria table renders the definitions authored in UC5.
- **UC13 → SP-UC3.** SP-UC3.2's learner-status GET is the read side of the rows UC13 writes — the
  join point between the two workstreams. SP-UC3 owns the status-values/iconography decision that
  SP-UC4/7/8 all assume as done.
- **SP-UC3 → SP-UC4 / SP-UC7 / SP-UC8 / SP-UC10.** Every downstream learner view consumes SP-UC3's endpoint.
- **SP-UC7 → SP-UC8.** Tooltip decorates the static sunburst; the diagram exists first.

**New dependencies the unwritten work creates (invisible in the 13-issue set):**
1. **Course-search backend (UC5.2/5.3/5.4 + scaling 5.11–13):** a new capability (endpoint +
   search-approach spike + large-catalog plan), not just applet CRUD. Spikes should start early.
2. **Grade/completion event contract (UC13):** the engine listens to edx-platform `openedx-events`
   signals. The CSV *assumes* they exist and suffice. If not → upstream coordination + schedule risk.
3. **Shared learner-status read contract (SP-UC3.2):** depended on by four learner UCs; design once
   as a contract, not re-derived per view.
4. **UC10 fans out into non-CBE endpoints:** "is-deletable" must be computed on `openedx_tagging`
   GETs — a package that must not import the CBE applet (`.importlinter`). Needs a pluggable-check /
   extension-point seam, not a field reaching into competency models.

---

## 3. Sprint-by-sprint plan

**Capacity assumption:** ~1 BE dev + ~1 FE dev + shared/part-time UXD, Architect, Docs; ~8–10
issue-days of throughput per discipline per 2-week sprint, BE and FE parallel. The additive-contract
pattern lets FE trail BE by ~half a sprint without blocking. Spikes are cheap in days but carry long
review/community-approval latency, so they start ahead of the work they unblock.

- **Sprint 1 — Foundation + UC1 slice.** BE: #613 model tree (big rock), #614 write API. FE: #615
  import dropdown against the write contract. Arch (async): kick off #625 ID spike + UC5.3
  course-search-approach spike. *Demoable:* import a "competency" taxonomy; row persists.

- **Sprint 2 — UC1 visible + UC4 backend + UC2 design.** BE: #618 read API; UC4.2/4.3 add
  Competency-ID field + GET. FE: #616 type badge (now end-to-end). UXD: #622 entry-point design.
  *Demoable:* competency taxonomies visibly badged; Competency ID in the API.

- **Sprint 3 — UC2 entry point + UC4 finish + UC5 kickoff.** FE: #623 actions-menu + Apply-Competencies
  TreeView shell; UC4.6 Mgmt-page ID display. BE: UC4.4/4.5 import/export of ID; begin UC5.5
  create-group, UC5.7 GET groups+criteria. Arch (async): UC5.11 large-scale plan; **confirm the
  UC13 grade/completion event contract now.** *Demoable:* navigate into a rough Competency
  Management page showing competencies with IDs.

- **Sprint 4 — UC5 authoring API core.** BE: UC5.6 create-criteria (containment/scope validation
  likely its own sub-ticket), UC5.8 remove-association, UC5.9 remove-group; UC5.2 accessible-courses
  endpoint. FE: UC5.10 associations UI shell, UC5.4 course-search FE. *Demoable:* create/read/delete
  criteria groups and criteria via API; UI shell renders existing groups.

- **Sprint 5 — UC5 complete + UC6 rule profiles.** FE: group create/remove UI, course
  select/deselect UI; UC5.13 large-scale FE. BE: UC5.12 backend pagination/filtering; UC6.1–6.3
  rule-profile CRUD API. UXD: UC6.4 design. *Demoable:* a Platform Admin fully configures competency
  criteria associations to gradeable subsections, end to end.

- **Sprint 6 — Mastery evaluation engine (UC13) + rule-profile UI.** BE: UC13.1 async listener +
  evaluation engine (second big rock) consuming UC5 tree + UC6 rules, writing status rows. Requires
  the event contract confirmed in Sprint 3. FE: UC6.5 rule-profile UI. Docs: UC1/2/4/5/6 catch-up.
  *Demoable:* learner completes an associated assignment → competency status computed and persisted.

- **Sprint 7 — Guardrails (UC10) + Progress-tab foundation.** BE: UC10.1 approach spike, then
  UC10.2–10.7 is-deletable across 6 GETs (now meaningful); SP-UC2.3 GET criteria-for-a-course. FE:
  UC10.8–10.10 disable-delete in three surfaces. UXD/Arch: SP-UC2.1/2.2 designs; SP-UC3.1
  status-values/iconography decision (unblocks all learner views). *Demoable:* delete blocked/greyed
  once learner statuses exist; progress-tab groundwork.

- **Sprint 8 — Student Progress tab core.** BE: SP-UC3.2 learner-status GET (the shared read
  contract). FE: SP-UC2.4 collapsible criteria table; SP-UC3.3/3.4 per-subsection + per-competency
  status; SP-UC4.1 Focus-Areas sidebar. *Demoable:* learner opens the Progress tab and sees
  competencies, criteria (threshold + logic), status per assignment, and a top-level summary.

- **Sprint 9 — Sunburst, Next Action, Copy, closeout.** FE: SP-UC7.2 static sunburst, SP-UC8.2
  tooltip, SP-UC10.3 next-action display. BE: SP-UC10.2 next-action service; **UC11 copy** (11.1
  new-course-run, 11.2 export/import spike + 11.3/11.4, 11.5/11.6 library copy). Docs: UC10/11/13 +
  Student-Progress. *Demoable:* full learner sunburst with tooltips and next action; criteria survive
  course copy/export/import/library ops. **Feature complete.**

**Honest note on length:** ~9 sprints (~18 weeks) at assumed capacity. UC11 is BE-only and
dependency-light once the models exist — treat it as floating backlog absorbing slack from Sprint 4
onward rather than waiting until Sprint 9. UC11 and Docs are the main compressible slack. A second
BE dev could partly parallelize UC5 and UC13 and save ~1–2 sprints, but will not shorten
spike-review/community-approval latency or the edx-platform event coordination.

---

## 4. Risks & big rocks

1. **UC5.1 model tree (#613) — largest single item, correctly front-loaded.** Ten models, MTI,
   self-referential tree, JSON validation, simple-history on three models, append-only status tables,
   delete protection, ~10 indexes. It is the global blocker (sized 8 points), so any slip cascades.
   Mitigant: it is written and ADR-backed (0002/0003; the CSV's "0023/0024" is stale for the same
   models). Keep it in Sprint 1 and keep UC5 CRUD scope from leaking into it. See the companion
   [#613b decomposition analysis](cbe-613b-decomposition.md) for how (not) to slice it.

2. **UC13 evaluation engine — highest logic complexity + cross-repo dependency.** The only place
   turning definitions into learner outcomes; hard-depends on UC5 + UC6 and on edx-platform
   grade-persistence / course-completion events via `openedx-events`. The CSV *assumes* those events
   exist and suffice. **Verify in Sprint 3, not Sprint 6.** Insufficient payloads (e.g. no subsection
   granularity) become upstream coordination and can push UC13 — and therefore all of Student
   Progress — by a full sprint. The evaluation semantics (AND/OR tree walk, threshold-resolution
   order, partial vs demonstrated) deserve their own design note before coding.

3. **UC10 guardrails cross a package boundary the wrong way.** "Is-deletable" must be computed on
   `openedx_tagging` GETs — a package that by design has no CBE dependency and must not import the
   CBE applet (`.importlinter`). Needs an extension-point / pluggable-check seam, not a boolean
   reaching into competency models. Under-scoping this to "add a field" will hit the import linter.
   Resolve the mechanism in the UC10.1 spike before the six endpoint tickets start.

4. **Course search + large-scale associations (UC5.2/5.3/5.4/5.11–13).** Two spikes plus a scaling
   plan for searching large course catalogs with permissions and time-range filtering, for instances
   that spin up new course runs each term. A new capability with real performance surface, not CRUD.
   Start the spikes in Sprints 1–3 so the Sprint 4–5 endpoints are not blocked on unresolved approach.

**Secondary watch items:** the #625 ID-field spike gates all of UC4 and needs community approval —
keep it off the critical path by closing it in Sprint 1. The Studio-home Taxonomies dropdown (CSV
1.6/1.7) is nice-to-have pending a scope-cut decision; leave it out of the committed plan.
