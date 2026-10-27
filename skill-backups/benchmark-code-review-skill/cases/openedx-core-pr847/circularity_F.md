# Circularity check for variant F (written before the report was read)

The version under test is the code-review-v2 working tree of 2026-10-20: config repo HEAD a67f709 plus the
uncommitted edits in record/code-review-v2_uncommitted.diff (381 lines). Those edits were made after PR 847's
review (2026-10-11 to 2026-10-15) and after runs 1 to 3 on this case, which scored every item below. Passages in
the new text that map onto a ground-truth item the earlier v2 run missed or half-found:

| GT | Passage in the 2026-10-20 edits | Mapping |
|---|---|---|
| GT4 | Common mistakes: "No MySQL locally means the DataError was not executed; the field lengths were. Score the 500 and label the inference." Step 3.7: "INFERRED lowers confidence, never impact". | Names GT4's exact failure shape (name overflow, DataError, no MySQL). |
| GT7 | Scope 3 invariants table: "a constraint without a condition that an archived row would keep occupying, so that no replacement row can exist"; step 3.6: a deferring ticket must be able to do its work "without undoing something this PR adds: a constraint". | Names GT7's no-room-for-a-replacement-row argument and the deferral-to-#717 failure. |
| GT9, GT10 | Scope 2 premise audit: "transaction isolation, locking ... verify against the installed source ... never against memory"; step 3.3 and Common mistakes: "a fact that overrules a reviewer also indicts the text that got it wrong". | Run 1's v2 settled the READ COMMITTED question but dropped the wrong comment as noise; the new text forbids exactly that. |
| GT12 | Scope 4.4: "fixtures that change global state (settings, permission registries) without restoring it"; Common mistakes: "'the full run showed no leak' argues ... low impact, not ... absent". | Names the set_perm fixture leak and the reason run 1's v2 dropped it. |
| GT15 | Scope 4.4: "tests that assert how the code is written (a mocked manager method was called, a query count, a lock call) rather than what it does". | Names the lock-pinning tests. |
| GT16 | Scope 3 invariants: "a rule enforced only by application code or a lock when a race or an out-of-band write can violate it"; step 3.4: "no database backstop scores 50 or higher". | Points at the missing (object_tag, group) constraint. |
| GT17 | Invariants table includes "lock" as an enforcement kind. | Weak mapping; the nested re-lock is a code-shape nit, not an invariant. |

Items with no mapping in the edits: GT1, GT2, GT3, GT5, GT6, GT8, GT11, GT13, GT14, GT18, GT19, GT20, GT21.

Consequence for reading the score: a gain on GT4, GT7, GT9, GT10, GT12, GT15, or GT16 relative to run 1 (82%) shows
that the skill text can carry those lessons, not that the skill generalizes. Those seven items weigh 17 of 45.
A held-out PR is needed before a composite from this case is quoted as the skill's expected performance.
Run 1's v2 (a0998b2, 2026-10-16) also post-dates the review, so the same caveat applied, more weakly, to that row.
