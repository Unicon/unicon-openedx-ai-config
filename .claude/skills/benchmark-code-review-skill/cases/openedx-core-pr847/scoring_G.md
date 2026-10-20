# Scoring: G = backend-code-review + code-review-openedx, rewritten 2026-10-20 (config repo working tree on top of a67f709; md5s in record/skill_md5_G.txt), report = reports/G_final.md

Tiers locked before the report was read, identical to runs 1 to 4:
- 1.0  found, correct mechanism, actionable recommendation
- 0.75 found and correct, but severity one level soft or the recommendation hedged into a question
- 0.5  noticed but vague, misdiagnosed, severity two levels soft, or (for a multi-part item) only part found
- 0    missed, or the report argues the opposite

Severity ladder (parent skill markers): blocking (Bug, Gap) > Question > Suggestion > Nit > dropped or declined.
Judge content, not labels. B/G/Q/S/N<n> = finding by marker and number, P<n> = premise row, INV = invariants row, AC<n> = criteria row.
Items marked (C) are flagged in circularity_G.md. Run 1's precedent for this ladder: a weight-2 item stated in full at Suggestion scored 1.0 (PR 49's S5, S6).

| GT | w | credit | where in report | note |
|---|---|---|---|---|
| GT1 rule-field validation before DB (xor 500) | 3 | 1.0 | B3 | both shapes reproduced (R1, R2); validate in the serializer before the lock |
| GT2 archived rule_profile_id accepted | 3 | 1.0 | G7 | R4: archived, taxonomy-scoped profile attached with 201; ADR 0002 line 139; drop the field or validate archived and scope |
| GT3 tag_object ValueError 500 (C) | 3 | 1.0 | B6 | allow_multiple=False reproduced (R12), named as a first-class setting of create_competency_taxonomy; map to 400 |
| GT4 group-name overflow 255 (C) | 3 | 1.0 | B8, INV | 307 and 312 characters stored (R9); DataError on STRICT_TRANS_TABLES named as the inferred step; truncate or drop derived names |
| GT5 taxonomy-scoped rule profile never assigned | 3 | 1.0 | G1, AC15 | not implemented, untested; ticket versus ADR MVP note and #672; implement or amend and list the deviation |
| GT6 Http404 / get_object_or_404 in api.py (C) | 3 | 1.0 | G6 | "Nothing else in src/ outside rest_api view modules does this"; every non-HTTP caller inherits HTTP semantics; let DoesNotExist or a domain exception propagate and translate in views.py. First full credit on GT6 since the stock skill (C). |
| GT7 archived groups vs get_or_create and unconditioned constraint (C) | 3 | 0.75 | Q2, Declined to judge (second line), INV rows 1 and 2, G4 | Q2 asks the maintainer's question in its own words ("does the constraint leave room for the result?") and lists every lookup that ignores `archived`; the declined line states "a conditionless constraint in a design with archiving would normally be a Gap on this change" and reads #717 lines 33 and 40-41 as accepting no replacement; G4 recommends the scope_code-style derived column and notes #717's reactivation path keeps working with a constraint. Everything the maintainer wrote is on the page, filed as a Question rather than a blocking decision. First variant above 0.5 here. |
| GT8 migration 0014 collision after rebase (C) | 3 | 1.0 | B1, B2 | leaf-node conflict and 190 test-setup errors reproduced on main plus the commit; renumber to 0015; the isolated_apps break as a second Bug |
| GT9 two select_for_update buy nothing; .exists() (C) | 2 | 1.0 | S1, INV lock assessment | "Remove the locking reads at api.py:223 and :228 and reword the comment"; the Tag lock already serializes same-tag callers; under READ COMMITTED a plain read sees the commit. The .exists() idiom is not mentioned. |
| GT10 REPEATABLE READ premise false (C) | 2 | 1.0 | P3, G9d, Q1 | `django/db/backends/mysql/base.py:238` read in the venv; edx-platform and Tutor checked for overrides; comment and commit message both named |
| GT11 malformed object_id gives 403 not 400 in Studio (C) | 2 | 1.0 | B4, AC20, P30 | platform predicate traced to `except (ValueError, AssertionError): return False`; validate_object_id before has_perm, in the ticket's order |
| GT12 rules.set_perm leaks across session (C) | 2 | 1.0 | S4 | exact fix (yield fixture restoring the predicate); demoted to Suggestion by the tagging tests' precedent, per the skill's own rule |
| GT13 leaf naming vs AC | 2 | 1.0 | G2, AC1 | leaf has no name; ticket inconsistent with itself; decide and list the deviation |
| GT14 test_criteria_group hunk unnecessary, comment wrong (C) | 2 | 1.0 | G9f, P15 | pre-existing form passes (6 passed); PR body claim false; revert |
| GT15 lock-pinning tests mock select_for_update (C) | 2 | 1.0 | S3, Tests checked (BR24) | "Remove the two mock-based lock tests"; mutation shows they pass with no lock taken; an IntegrityError test replaces them once a constraint exists |
| GT16 unique (object_tag, group)? (C) | 2 | 0.75 | INV row 5, Q2 | application check only, no constraint; a constraint judged not possible "while #717 and #666 dispute the semantics"; folded into Q2. Engaged with a reason, not raised as its own question. Same credit as H. |
| GT17 nested re-lock in create_leaf_group | 1 | 1.0 | S2, P29 | remove the nested atomic and second lock once the helper is private |
| GT18 competency_rule_profile_id vs rule_profile_id naming (C) | 1 | 1.0 | G13 | one name per concept across signature, serializer, ticket |
| GT19 mark new api functions UNSTABLE (C) | 1 | 1.0 | G12 | "mark it UNSTABLE: the way get_competency_rule_profiles is (api.py:71-72)" |
| GT20 UserType alias | 1 | 0 | not raised | |
| GT21 duplicated assert line | 1 | 1.0 | N1 | with the "no behavior change forcing it" reason from the skill's pre-existing-test rule |

Weighted: blocking 7.75x3 = 23.25 ; substantive 7.75x2 = 15.5 ; nits 4.0 => 42.75/45 = 95.0%
Pass/fail: PASS (lowest blocking item GT7 at 0.75). Blocking false positives: 0.

Split by circularity flag (circularity_G.md maps 14 items, weight 31; the unmapped seven weigh 14):
- Mapped items: G 29.75/31 = 96.0% ; PR 49 skill (run 1) 22.75/31 = 73.4%.
- Unmapped items (GT1, 2, 5, 13, 17, 20, 21): G 13/14 = 92.9% ; PR 49 skill 13/14 = 92.9%.
The whole gain over the PR 49 skill is on items the rewrite was written from.

Findings reported: 44 (8 Bug, 13 Gap, 9 Question, 8 Suggestion, 6 Nit). Dropped: 7, none a ground-truth item. Declined to judge: 6.
- False positives: none. The architect's REPEATABLE READ race was dropped with the installed backend's default cited; the gap-lock deadlock survives only as a reason to remove the redundant reads; G4's isolation note is framed as a dependency on a non-default configuration.
- Valid extras: B5 disabled-taxonomy read-merge-write cascade-deletes a sibling criterion, reproduced through the API and the view (run 1, B, C, E, F); B7 library usage key AssertionError 500 (D, E, F, H); B2 isolated_apps break on the merged tree (D, E, F, H); G4 root uniqueness by lock only, two roots then MultipleObjectsReturned, with the scope_code pattern as the fix (F, H); G5 leaves with null course_id against ADR 0002 line 86 (run 1, F); G8 roots and course-level groups keep a null logic_operator with two children (run 1); G9a to G9g and G10, the false claims in commit message, docstrings, comments, and PR body (E, F, H); G11 the companion mount path that would serve /api/cbe/cbe/v1/, with the correct path (run 1); G12 the exports that persist empty groups and bypass the checks (E, F, H); G13 response keys versus AC 1 and #672 (B, D, E, F, H); S5 the tag resolved twice per request with a query count (F minor); S6 and S7 negative clauses and the ObjectTag rollback not asserted (F minor); N5 error key `rule_profile` versus the request field (E, H); N6 #672's expected camelCase key (run 1). New in this run: AC 4, 7, 11 negative clauses unasserted with the exact tests named; AC 18's second branch untested (E had the taxonomy check untested); the 24-row break-and-restore table showing five tests fail with a 500 rather than on the asserted status.
- Neutral: Q1, Q3 to Q9 (questions with consequences stated), S8, N2, N3, N4.
Precision = 1 - 0/44 = 1.00

Communication: 0.85. For it: verdict first with the two reasons the branch cannot merge; an inputs table with the commits on main that change the picture; a 22-row criteria table whose "Tested by" cell names the assertion that failed under mutation; premise audit of 30 rows with the FALSE ones re-read; invariants table with a lock assessment; findings grouped by marker with mechanism, reproduction id, cited rule, and fix; a tests-checked table that distinguishes "failed" from "failed for the stated reason"; declined-to-judge lines that state what the owning ticket must do; a dropped list with the disproving fact; a process log with tokens per agent. Against it: 69 KB and 44 items, the longest project-skill report in the series; a maintainer reads the invariants and premise tables before reaching the first Bug.

Composite = 0.70 x 0.950 + 0.15 x 1.00 + 0.15 x 0.85 = 0.665 + 0.150 + 0.128 = 0.943 -> 94%

Cost: orchestrator (general-purpose on fable, default effort) 340,541 tokens, 44 tool uses, 117 min dispatch to hand-back. Sub-agents, dispatched in sequence as the skill's steps order them: Explore haiku (usage not reported by the Agent tool result); general-purpose sonnet high, ticket and history condensation, 204,650 tokens, 37 tool uses, 6.2 min; general-purpose sonnet high, mechanical verification (merge, cherry-pick, 30 premise lookups, 14 reproductions, 24 break-and-restore checks, linters), 210,194 tokens, 75 tool uses, 13.9 min; software-architect opus xhigh 242,590 tokens, 68 tool uses, 17.4 min; general-purpose sonnet medium, documentation lookup, 43,649 tokens, 4 tool uses. Reported sub-agent total 701,083; whole run about 1.04M tokens plus the unreported Explore call, with two of the three large sub-agents on Sonnet. Wall clock is the cost: the skill's steps are sequential, so the run took 2.5 times F's 47 minutes.
