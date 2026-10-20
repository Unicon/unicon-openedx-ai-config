# Circularity check for variant G (written before the report was read)

code-review-openedx and backend-code-review were rewritten on 2026-10-20 by the person who had scored runs 1 to 4
on this case, with the instruction that nothing may name this PR. The text names no PR 847 term (no "MySQL",
"select_for_update", "set_perm", "Tag.value", "REPEATABLE READ"), but its new checks were chosen from this case's
failure classes, so a gain on the mapped items shows that the text carries the lesson, not that it generalizes.

| GT | New text in code-review-openedx or backend-code-review | Strength |
|---|---|---|
| GT3 | Step 9 "Error paths, enumerated"; rule "supported input includes every option the product exposes as a first-class setting"; red flag "That configuration is exotic" | strong |
| GT4 | Step 9 "Bounded writes"; backend question 12 | strong |
| GT6 | Step 8 "framework-boundary leaks: HTTP-layer types raised from a module that is not a view" | strong |
| GT7 | Step 7 invariants: "a constraint without a condition, in a design whose tickets or ADRs describe archiving"; step 10 deferral rule; red flag "The other ticket owns this" | strong |
| GT8 | Step 3 "what landed on main"; step 6.1 merge with main and migration graph check | strong (PR 49 already found it) |
| GT9 | Step 7 "a lock whose work an outer lock or a database constraint already does"; backend question 11 | strong |
| GT10 | Step 5 premise audit | strong |
| GT11 | Step 9 "Order of checks" | strong |
| GT12 | Step 6 "fixture that changes global state and does not restore it is a Gap" | strong |
| GT14 | Step 6 "an edit to a pre-existing test needs a behavior change that forces it" | strong |
| GT15 | Step 6 "asserts how the code is written ... never propose another test of the same kind"; red flag on mocked locks | strong |
| GT16 | Step 7 "a rule enforced only by application code or a lock ... a Question asking for a constraint" | medium |
| GT18 | Step 9 "the same concept has one name across the function signatures, the serializer, and the ticket" | medium |
| GT19 | Step 8 "UNSTABLE markers where the module's neighbors carry them" | medium (PR 49 already found it) |
| GT1, GT2, GT5, GT13 | Unchanged from PR 49, which found them | none new |
| GT17, GT20, GT21 | Nothing specific | none |

Fourteen of the twenty-one items have a mapping. This case therefore measures whether the rewrite can carry its own
lessons at a cost no higher than PR 49's; the generalization question needs a held-out PR.
