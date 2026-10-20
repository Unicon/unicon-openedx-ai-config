# Scoring: variant C = Claude Code built-in `code-review` (2.1.301), effort high, run as a separate `claude -p` process in wt-C. Report = reports/C_final.md

Tiers (locked before any report was read): 1.0 found + correct mechanism + actionable; 0.75 one severity level soft or hedged; 0.5 vague / misdiagnosed / two levels soft / part of a multi-part item; 0 missed or argues the opposite.
The stock skill emits a severity-ranked JSON list with no labels and no verdict, so severity is read from rank and wording.

| GT | w | credit | where in report | note |
|---|---|---|---|---|
| GT1 rule-field validation before DB | 3 | 1.0 | finding 1 (serializers.py:80) | XOR constraint -> IntegrityError -> 500 for payload-only and profile+overrides; serializer validate() fix. Its first scenario (nonexistent rule_profile_id -> IntegrityError) is wrong: full_clean()'s FK validation already turns that into a 400 (variant B probed it). Core claim right. |
| GT2 archived rule_profile_id accepted | 3 | 1.0 | finding 2 (api.py:197) | cites ADR-0002 Decision 3 |
| GT3 tag_object ValueError 500 | 3 | 1.0 | finding 3 (api.py:193) | allow_multiple=False and OBJECT_MAX_TAGS; "400 keyed on object_id" |
| GT4 group-name overflow 255 | 3 | 1.0 | finding 4 (api.py:136) | Tag.value 500 vs name 255, MySQL strict DataError vs silent truncation, truncate |
| GT5 taxonomy-scoped profile never assigned | 3 | 1.0 | finding 7 (api.py:197) | from ADR-0002 Decision 4 only (no ticket access); names taxonomy- and course-scoped; implement or document |
| GT6 Http404 in api.py | 3 | 1.0 | finding 6 (api.py:34) | raise ObjectDoesNotExist/ValidationError, map to 404 in the view |
| GT7 archived groups vs get_or_create + constraint | 3 | 0 | | not mentioned; the skill never looked at what landed on main |
| GT8 migration 0014 collision | 3 | 0 | | not mentioned; "makemigrations --check shows no drift" was run on the branch alone |
| GT9 duplicate-check locking reads buy nothing | 2 | 0 | | not mentioned (finding 10 is about the tag lock, not these reads) |
| GT10 REPEATABLE READ premise wrong | 2 | 0 | | not mentioned |
| GT11 malformed object_id -> 403 in Studio | 2 | 0 | | not mentioned (the fork grepped for can_change_object_tag_objectid but reported nothing) |
| GT12 set_perm fixture leaks | 2 | 0 | | not mentioned |
| GT13 leaf naming vs AC | 2 | 0 | | no ticket access |
| GT14 test_criteria_group hunk + wrong comment | 2 | 1.0 | finding 9 (test_criteria_group.py:52) | verified by running the pre-PR test body against the new model; revert |
| GT15 drop lock-pinning tests | 2 | 0 | | not mentioned |
| GT16 unique (object_tag, group)? | 2 | 0 | | not mentioned |
| GT17 create_leaf_group re-takes the lock | 1 | 1.0 | finding 10 (views.py:84) | "locked twice in the same transaction ... drop the inner lock when a caller already holds it" |
| GT18 competency_rule_profile_id naming | 1 | 0 | | not mentioned |
| GT19 mark new api functions UNSTABLE | 1 | 1.0 | finding 6 | "keep private or mark UNSTABLE", cites get_competency_rule_profiles' marker |
| GT20 UserType alias | 1 | 0 | | not mentioned |
| GT21 duplicated assert | 1 | 1.0 | prose after the list ("cut by the cap") | stated in full with location; judged by content |

Weighted: blocking 6.0x3 = 18 ; substantive 1.0x2 = 2 ; nits 3x1 = 3 => 23/45 = 51.1%. Blocking items found: 6 of 8.

Findings reported: 10 in the list + 2 cut candidates named in prose = 12.
- False positives: none at finding level (the dangling-FK sub-scenario inside finding 1 is wrong but the finding stands).
- Valid extras: finding 5 (resolve_supplied_leaf_group assumes depth 2; deeper ADR-allowed groups are rejected with a misleading error); finding 6's second half (create_leaf_group alone persists empty groups the ADR forbids); finding 8 (disabled taxonomy: get_object_tags filters it out, so tag_object's replace semantics delete the other competency's ObjectTag and cascade-delete its criterion); finding 10's first half (tag resolved twice per request).
- Neutral: `_` rebound inside create_leaf_group (shadows gettext_lazy).
Precision = 1 - 0/12 = 1.00

Communication: 0.75. Precise anchors (every one verified by the wrapper against the diff), one concrete failure scenario per finding, fixes embedded in the scenario text, two claims verified by execution (pre-PR test body passes, makemigrations clean), no padding. Against it: no merge verdict, no severity labels (only rank order), a JSON array is awkward for a PR author to read and reply to, no reference to the ticket, and one wrong sub-scenario stated as fact.

Composite = 0.70 x 0.511 + 0.15 x 1.00 + 0.15 x 0.75 = 0.62

Cost (from the stream-json result event of the wrapper session): total_cost_usd 5.49; wrapper usage 70k cache-write + 406k cache-read + 15k output tokens; the fork's eight "angles" and their models are not visible to the caller. Wall clock 9 min 53 s (13:11:22 to 13:21:15 EDT), of which about 8 min inside the forked skill. No Agent dispatches visible in the transcript.
