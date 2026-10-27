# Scoring: F = code-review-v2 (four-scope version, config repo working tree on 2026-10-20 at HEAD a67f709 plus uncommitted edits; SKILL.md md5 66713b73, scopes.md md5 f36a2808), report = reports/F_final.md

Tiers locked before the report was read, identical to runs 1 to 3:
- 1.0  found, correct mechanism, actionable recommendation
- 0.75 found and correct, but severity one level soft or the recommendation hedged into a question
- 0.5  noticed but vague, misdiagnosed, severity two levels soft, or (for a multi-part item) only part found
- 0    missed, or the report argues the opposite

Severity ladder: blocking (kept, impact >= 50) > author's call (kept, impact 25-49) > Minor list > dropped.
Judge content, not labels. K<n> = kept finding n, M = minor list, D = dropped list, PA = premise audit row, INV = invariants row.
Items marked (C) are the ones circularity_F.md flags: the 2026-10-20 skill edits name their failure shape.

| GT | w | credit | where in report | note |
|---|---|---|---|---|
| GT1 rule-field validation before DB (xor 500) | 3 | 1.0 | K4 (60) | both shapes probed (profile plus overrides; payload alone); "enforce profile-xor-overrides before the write" |
| GT2 archived rule_profile_id accepted | 3 | 1.0 | K4 (60), INV rule_profile row | 201 reproduced; ADR 0002 line 139 cited; filter(archived=False) or drop the field |
| GT3 tag_object ValueError 500 | 3 | 0.75 | K21 (35) | both triggers named (allow_multiple=False, 100-tag ceiling), "translate ValueError to a 400"; filed at 35, one level below blocking. Run 1 had it at 60. |
| GT4 group-name overflow 255 (C) | 3 | 1.0 | K9 (50) | 507 and 512 characters reproduced on SQLite; STRICT_TRANS_TABLES from the manual; DataError marked INFERRED; truncate and test |
| GT5 taxonomy-scoped rule profile never assigned | 3 | 1.0 | K2 (70) | probe 10; Decision 4; implement or retire the AC formally |
| GT6 Http404 / get_object_or_404 in api.py | 3 | 0.75 | K7 (50) | "three raise Http404 from a domain layer" is one clause of the public-API finding; the stated fix (make the helpers private) does not remove the Http404 from associate_competency_criterion; no DoesNotExist-in-view fix. Same credit as run 1 for the same reason. |
| GT7 archived groups vs get_or_create and unconditioned constraint (C) | 3 | 0.5 | K1 detail, K19(b), INV course-level row, K6 | first variant to state the consequence ("the schema has no archive-and-replace room") but classes it as accepted by #717 and defers the archived filter to #717; the scope_code column is recommended in K6 for root uniqueness, not for this. The decide-before-merge framing is absent. |
| GT8 migration 0014 collision after rebase | 3 | 1.0 | K1 (85) | reproduced in a worktree at main; 0015 depending on 0014_add_archived; also the nine merge conflicts |
| GT9 two select_for_update buy nothing; .exists() (C) | 2 | 0.75 | K14 (50), K6 detail | "the locking reads are harmless"; "(or drop the redundant FOR UPDATE on the two reads)" offered as the alternative to fixing the comment; the tag-lock-serializes reason and the .exists() idiom are not spelled out. Run 1 dropped it at 12. |
| GT10 REPEATABLE READ premise false (C) | 2 | 1.0 | K14 (50), PA, K12 | mysql/base.py:238 read from the installed Django; no override in edx-platform or Tutor; comment and commit message both named |
| GT11 malformed object_id gives 403 not 400 in Studio | 2 | 1.0 | K20 (35) | platform predicate read; validate_object_id before has_perm. Same tier as run 1's credit at 30. |
| GT12 rules.set_perm leaks across session (C) | 2 | 0.75 | M (25) | correct fix (restore after yield); kept as Minor because the full suite passes, one level soft for a substantive item. Run 1 dropped it at 10. |
| GT13 leaf naming vs AC | 2 | 1.0 | K10 (50) | leaf name '' observed; set the name or amend the AC |
| GT14 test_criteria_group hunk unnecessary, comment wrong | 2 | 1.0 | K15 (50), PA rows 1 and 4 | pr-base form of the test run against pr-head: 6 passed; revert |
| GT15 lock-pinning tests mock select_for_update (C) | 2 | 0.5 | K17 (40) | diagnosis right ("prove a manager method was called, not that a lock exists", mutation shown); the fix is a CaptureQueriesContext test asserting FOR UPDATE, another implementation-pinning test, with the two-thread test optional; the maintainer asked to drop them. No praise of the tests (unlike B and E). Run 1 recommended a real two-connection test and got 0.75. |
| GT16 unique (object_tag, group)? (C) | 2 | 0.5 | INV "at most one criterion per (tag, object) per group" row, K7 | "no database constraint" stated as a gap; the proposed action is to make create_competency_criterion private, not to add the constraint or ask the question. Same credit as E. |
| GT17 nested re-lock in create_leaf_group (C, weak) | 1 | 0 | not raised | grep for savepoint, nested atomic, re-lock: none. K7's "make the helpers private" is half of the maintainer's alternative fix but for a different reason. Run 1 had it at 0.5 under checked-and-acceptable. |
| GT18 competency_rule_profile_id vs rule_profile_id naming | 1 | 1.0 | M (20) | |
| GT19 mark new api functions UNSTABLE | 1 | 1.0 | K7 (50) | get_competency_rule_profiles precedent named |
| GT20 UserType alias | 1 | 0 | not raised | the pylint disable on the User import is listed as acceptable; the alias is not mentioned |
| GT21 duplicated assert line | 1 | 1.0 | M (10) | |

Weighted: blocking 7.0x3 = 21.0 ; substantive 6.5x2 = 13.0 ; nits 3.0 => 37.0/45 = 82.2%

Split by circularity flag (weights: flagged 17, unflagged 28):
- Flagged items (GT4, 7, 9, 10, 12, 15, 16, 17): F 11.5/17 = 67.6% ; run 1's v2 8.75/17 = 51.5%.
- Unflagged items (the other thirteen): F 25.5/28 = 91.1% ; run 1's v2 26.25/28 = 93.8% (F lost 0.75 on GT3's tier).
The whole gain over run 1 is on the flagged items.

Findings reported: 39 (22 kept at threshold 30, 17 minor). Dropped list: 5 items, none of them a ground-truth item.
- False positives: none. The REPEATABLE READ race (scope 2) was dropped with the READ COMMITTED fact; the "nonexistent rule_profile_id is a 500" claim was dropped after probe 01 showed a 400. One wart inside K6: its fix list includes "make the get_or_create lookups locking reads", which the report's own READ COMMITTED finding makes pointless; the core of K6 (two roots accepted, then every derive request 500s) is correct and reproduced, so K6 is not counted as a false positive.
- Valid extras (verified by the agent that raised them, spot-checked by the scorer where noted): K3 read-merge-write cascade-deletes a sibling criterion on a disabled taxonomy (probe 07; also run 1, B, C, E); K5 leaves with null course_id against ADR 0002 Decision 2 (run 1, E); K6 two roots for one tag make every derive request 500 with MultipleObjectsReturned (run 1, E); K7 __all__ exports helpers that persist an empty leaf and bypass the duplicate check (E); K8 library usage key AssertionError 500 (D, E); K1's nine merge conflicts (D, E); K11 stale PR body and K12 false commit message (B, D, E); K13 the views.py docstring's permission-class rationale is false (E); K16 no test sends any rule field, three mutations green (run 1 as a coverage gap); K22 untested competency-taxonomy check, IsAuthenticated, and indistinguishable group_id messages (E partly); K21's free-text taxonomy and archived-default DoesNotExist 500s; K4's cross-tenant profile binding making another organization's course run undeletable through RESTRICT (new; probe 11); M1 the Tag row lock held for the whole request contends with every tag_object FK check platform-wide (new; MySQL manual on FK shared locks; impact 25); M5 `root, _ = ...` rebinds the gettext_lazy alias `_` imported at api.py:11 (new; verified by the scorer in wt-F); M7 the constraint test guards the migration, not Meta, and no CI step runs makemigrations --check (new; plausible, not re-run).
- Neutral: K18 ADR amendment request; K19 nine downstream open questions; M6 check order; M8 enumeration oracle; M11 __all__ order; M13 U+2014 in the stored name; M14 duplicated helpers; M15 tag resolved twice; M16 "the plan's explicit note"; M17 double-hyphen dashes.
Precision = 1 - 0/39 = 1.00

Communication: 0.85. Verdict and threshold in the first line; a review record; a 29-row premise audit and an 11-row invariants table, each row with the source checked; 22-row kept table (impact, scopes converging, anchor, wrong, do) with a paragraph each; minor list in one line each; dropped list with the disproving fact; checked-and-acceptable with 23 items; gaps naming every inferred MySQL step and every reviewer result not re-run; process log with per-agent tokens. The orchestrator re-ran 12 probes itself. Costs: 59 KB, the longest report in the series; 39 actionable items for one author; five "false premise" findings (K11 to K15) all at exactly 50, so the stale PR body scores the same as the name-overflow 500, a mechanical effect of the skill's "50 or higher" rule; GT3 at 35 under a blocking-class 500.

Composite = 0.70 x 0.822 + 0.15 x 1.00 + 0.15 x 0.85 = 0.575 + 0.150 + 0.128 = 0.853 -> 85%

Cost: orchestrator (general-purpose on fable, default effort) 377,606 tokens, 60 tool uses, 47 min from dispatch to hand-back (2,829,607 ms). Reviewers, all software-architect at the definition's xhigh, concurrent for about 21 min: scope 1 fable 178,948; scope 2 fable 253,107; scope 3 opus 246,684; scope 4 sonnet 252,159; 930,898 in total. Whole run about 1.31M tokens.
