# Scoring: H = code-review-v2 two-reviewer budgeted version, rewritten 2026-10-20 (config repo working tree on top of a67f709; md5s in record/skill_md5_H.txt), report = reports/H_final.md

Tiers locked before the report was read, identical to runs 1 to 4:
- 1.0  found, correct mechanism, actionable recommendation
- 0.75 found and correct, but severity one level soft or the recommendation hedged into a question
- 0.5  noticed but vague, misdiagnosed, severity two levels soft, or (for a multi-part item) only part found
- 0    missed, or the report argues the opposite

Severity ladder: blocking (kept, impact >= 50) > author's call (kept, 25-49; the threshold was 25) > Minor > dropped.
Judge content, not labels. H<n> = kept finding n, M = minor list, D = dropped list, PA = premise audit row, INV = invariants row.
Items marked (C) are flagged in circularity_H.md.

| GT | w | credit | where in report | note |
|---|---|---|---|---|
| GT1 rule-field validation before DB (xor 500) | 3 | 1.0 | H4 (70) | both shapes probed (P03, P05); validate the combination, ValidationError keyed to the field |
| GT2 archived rule_profile_id accepted | 3 | 1.0 | H10 (55) | archived and foreign-taxonomy profile both 201 (P02, P17); ADR 0002 line 309; read-only or validate archived=False and scope |
| GT3 tag_object ValueError 500 (C) | 3 | 1.0 | H7 (60) | allow_multiple=False reproduced (P07); catch ValueError, ValidationError on object_id. The 100-tag ceiling is not named, as in run 1's full-credit row. |
| GT4 group-name overflow 255 (C) | 3 | 1.0 | H9 (55) | 507 characters stored on SQLite (P08); tutor's `init_command: SET sql_mode='STRICT_TRANS_TABLES'` cited, stronger evidence than F's manual default; MySQL step labeled INFERRED; truncate |
| GT5 taxonomy-scoped rule profile never assigned | 3 | 1.0 | H8 (55) | not implemented, no test; ticket versus ADR 0002 MVP note and #672; settle in this PR |
| GT6 Http404 / get_object_or_404 in api.py (C) | 3 | 0.75 | H21 (25) | exact mechanism and the maintainer's fix (domain error in api.py, map to 404 in the view); filed at 25 because "the ticket prescribed this", one tier under blocking |
| GT7 archived groups vs get_or_create and unconditioned constraint (C) | 3 | 0.5 | INV rows 2 and 7, H20 (30), M1 | the archived lookups are listed (all four) and recorded for #717; the deferral rule was applied and concluded #717 "can add the filters without undoing anything here", and INV row 2 says the unconditional constraint "fits" #717's never-replace design. The no-room-for-a-replacement-row consequence is thus considered and judged acceptable, not raised as a decision for this PR. |
| GT8 migration 0014 collision after rebase (C) | 3 | 1.0 | H1 (90) | two leaf nodes reproduced on the merged tree; renumber to 0015 depending on main's 0014; nine conflicts |
| GT9 two select_for_update buy nothing; .exists() (C) | 2 | 0 | D1 | scope 2 found it ("redundant") and the orchestrator dropped it, arguing that under a request-wide REPEATABLE READ transaction the locking reads are what lets the duplicate check see a concurrent commit. Argues the opposite. |
| GT10 REPEATABLE READ premise false (C) | 2 | 0 | PA C2, H2 (85) | adopts the premise: "MySQL REPEATABLE READ" is taken as the production isolation level because tutor's auth.yml sets no `isolation_level`; Django's MySQL backend default (`django/db/backends/mysql/base.py:238`, `"read committed"`, confirmed by the scorer in the venv) was never read. The audit row marks the commit-message claim FALSE for the wrong reason. |
| GT11 malformed object_id gives 403 not 400 in Studio (C) | 2 | 1.0 | H5 (60) | platform predicate read (`content_tagging/rules.py:228-232`); parse and resolve before has_perm; extends to AC 21 with the inferred step labeled |
| GT12 rules.set_perm leaks across session (C) | 2 | 1.0 | H17 (30) | exact fix (save, yield, restore); order dependence shown by a probe; kept above the threshold |
| GT13 leaf naming vs AC | 2 | 1.0 | H18 (30) | '' read back (P20); name the leaf or amend AC 1; #672 renders no leaf name |
| GT14 test_criteria_group hunk unnecessary, comment wrong (C) | 2 | 1.0 | H14 (50), PA C11, C12 | pr-base form passes against pr-head; two roots inserted (P13); revert |
| GT15 lock-pinning tests mock select_for_update (C) | 2 | 1.0 | H19 (25) | "assert mock call counts and call order ... detect no race. Remove them"; the alternative offered is a behavioral thread race, not another pinning test |
| GT16 unique (object_tag, group)? (C) | 2 | 0.75 | INV row 5, M1 | the rule is application-enforced only; a constraint is considered and judged foreclosed by #717's insert-after-archive design; "record the decision in a model comment". The question is engaged and answered with a reason, filed as Minor. |
| GT17 nested re-lock in create_leaf_group | 1 | 1.0 | H22 (25) | "takes the Tag lock again inside the lock associate_competency_criterion already holds ... make the helper private and document that the caller holds the lock, then drop the inner lock": the maintainer's fix |
| GT18 competency_rule_profile_id vs rule_profile_id naming (C) | 1 | 1.0 | H6 (60) | inside the one-name-per-concept finding |
| GT19 mark new api functions UNSTABLE (C) | 1 | 1.0 | H11 (55) | neighbors' markers cited by line |
| GT20 UserType alias | 1 | 0 | not raised | the pylint disable on the import is a minor item; the alias is not mentioned |
| GT21 duplicated assert line | 1 | 1.0 | M5 | |

Weighted: blocking 7.25x3 = 21.75 ; substantive 5.75x2 = 11.5 ; nits 4.0 => 37.25/45 = 82.8%
Pass/fail: FAIL: GT7 (0.5). Blocking false positives: 1 (H2 at 85).

Against F (82.2%): H gains GT12 (+0.25x2), GT15 (+0.5x2), GT16 (+0.25x2), GT17 (+1x1), GT3 (+0.25x3) = +3.25; loses GT9 (-0.75x2), GT10 (-1x2) = -3.5; net -0.25. Same coverage within noise, with the loss concentrated on the one item class (isolation level) where F's Fable structure reviewer read Django's source and H's budgeted orchestrator read tutor's config and the MySQL manual instead.

Findings reported: 31 (22 kept at threshold 25, 9 minor). Dropped: 2.
- False positives: H2 (85), the root-creation race "in the production database configuration": it rests on MySQL REPEATABLE READ applying under ATOMIC_REQUESTS, and Django sets READ COMMITTED on every MySQL connection unless settings override it, which tutor does not. The maintainer rejected this premise on the PR. Its fix (make the group lookups locking reads, rewrite the comment to state a configuration dependency) would add code that does nothing and a comment that is wrong. The same premise caused D1, the wrong drop of GT9, which coverage already counts.
- Valid extras: H3 isolated_apps import-linter break on the merged tree (D, E, F); H6's response-key and function-name mismatches against AC 1, #672, #674, #675, #717 (B, D, E, F); H12 stale PR body and commit message (B, D, E, F); H13 the views.py docstring's permission-class rationale is false (E, F); H15 every leaf created with ordering=0 against ADR 0002's sibling sequence, and the comment at criteria.py:110-112 giving a reason that does not apply to a (parent, ordering) constraint (F had the ordering half as an open question; the comment half is new and holds on reading); H16 archived or missing system default is a 500 (F); H11's empty-leaf and bypass exports (E, F); M3 error keys `rule_profile` and `__all__` not matching request fields (E); M7 migration header predates its dependency (F).
- Neutral: H20 (record the archived lookups on #717), M1, M2, M4, M6, M8, M9.
Precision = 1 - 1/31 = 0.97

Communication: 0.80. For it: verdict and threshold first; a review record with sha256 of each context file; premise audit reduced to the rows that failed; invariants reduced to the rows with a gap; one evidence paragraph per kept finding with probe ids and the inferred step named; 33 KB against F's 59 KB with the same number of kept findings; process log with per-agent tokens, tool uses, and durations, and the budgets reported against their limits. Against it: the verdict's second-named blocker is wrong, and its fix would ship a useless lock and a false comment; the kept table and the evidence list repeat each finding twice; GT6 at the lowest kept score.

Composite = 0.70 x 0.828 + 0.15 x 0.97 + 0.15 x 0.80 = 0.580 + 0.146 + 0.120 = 0.845 -> 84%

Cost: orchestrator (general-purpose on fable, default effort) 237,071 tokens, 21 tool uses (12 in step 1 and 6 in step 3 against budgets of 12 and 15, plus the brief and skill reads), 26.9 min dispatch to hand-back. Reviewers, concurrent for about 8.5 min: scope 1 general-purpose fable high 178,851 tokens, 16 tool uses, 502 s; scope 2 software-architect opus high 112,979 tokens, 17 tool uses, 369 s. Whole run 528,901 tokens, 40% of F's 1.31M, 57% of F's wall clock. Target was a quarter; the orchestrator at 237k is the gap: it reads two 2,000-word reviewer reports and writes a 33 KB report that states each finding twice.
