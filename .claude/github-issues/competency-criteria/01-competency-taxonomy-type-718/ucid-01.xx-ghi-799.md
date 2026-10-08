# [Placeholder] Competency Criteria Deletions

GitHub: https://github.com/openedx/openedx-core/issues/799 (#799, CLOSED)
Cached: 2026-09-25

## Status: superseded, closed

This issue owned nothing by the time #655 resolved. It existed to hold #613's delete-protection
criteria while #655 decided how to implement them, and to replace the provisional `on_delete=PROTECT`
values that #641 and #642 were told to declare in the meantime. #655 is now closed with an approved
design that answers the question differently, so none of the four criteria below survive. They are
kept for history rather than as work.

**Where each piece went:**

| Criterion below | Where it lands now |
| --- | --- |
| `on_delete=PROTECT` on `Student*Status` foreign keys | #641 and #642 declare it directly. #641 also records the one question still open about the two foreign keys crossing into `openedx_tagging`. |
| `on_delete=CASCADE` on definition-to-definition foreign keys | Dropped. #655's appendix puts enforcement at the application layer rather than in database-level cascade behavior. |
| Transitive delete tests | #641 and #642 each now carry a criterion requiring test coverage for whatever `on_delete` values they land. The product behavior is covered by #674 and #675 through their own endpoints. |
| `CompetencyRuleProfile` is archive-only, never hard-deleted | #655 resolves this differently: the model gets no DELETE endpoint at all, and only the single system-default row exists in MVP, so there is no archive-versus-delete case for it. Whoever builds the profile endpoints owns not building a DELETE. |

**Work #655 identified that no issue owns yet.** Recorded here so it is not lost, but it belongs in
freshly filed tickets rather than in this one, because it changes `openedx_tagging` rather than CBE:

1. An `openedx_tagging` ticket adding `archived` to `Tag`, `Taxonomy` and `ObjectTag`, `deletion_locked`
   to `ObjectTag` only, and the three lock functions CBE calls. #655 states explicitly that #716 does
   not cover this.
2. The CBE call site that locks an `ObjectTag` when a `StudentCompetencyCriteriaStatus` row is written,
   with the read-before-write guard so a shared `ObjectTag` row is not write-locked inside every grade
   transaction.
3. The tagging-side delete-path work: the per-tag branch in `Taxonomy.delete_tags()`, a
   `perform_destroy` on `TaxonomyView`, the archive branch in `tag_object()`, and the `archived`
   exclusions across the read paths.
4. An `openedx-platform` ticket extending ADR-0013's `taxonomy_type` computation to the per-object tag
   endpoint, plus the frontend gating of the delete and Add Tag controls.
5. The ADR follow-up PR @mgwozdz-unicon committed to on #655, covering the nine ADR edits raised there.

**Parent:** #613.

---

## Historical content

Everything below is the issue as it stood before #655 closed. Kept for the record.

## Why this is separate

ADR-0002 Decision 7 and ADR-0003 Decision 4 already decide *what* should happen when someone tries to
delete or edit competency data after a learner has mastery status against it. #655 is deciding *how*
that gets implemented: how a "can this be deleted" signal is computed and surfaced on the GET endpoints
without N+1 queries, and where the write-path validation lives so the rule is enforced rather than only
hinted at in the UI.

Those answers change what the model layer has to look like, so these criteria were pulled out of #613's
model tickets rather than guessed at. #641 and #642 build the tables with no delete behavior of their
own.

## What #641 and #642 leave behind

Django requires an `on_delete` value on every `ForeignKey`, so #641 and #642 cannot leave the question
open. Both declare every new foreign key as `on_delete=PROTECT` with a `TODO(#799)` comment. That is a
fail-closed placeholder, not a considered per-foreign-key choice: nothing can be hard-deleted until this
issue sets the real values. Neither ticket ships an authoring API, so nothing performs deletes meanwhile.

So the first job here, whatever #655 decides, is to replace every `on_delete=PROTECT` that carries a
`TODO(#799)` comment, and to leave none behind.

## Acceptance criteria (from #613)

Copied unchanged from #613's "Deletions" section. Expect these to change once #655 is resolved.

- [ ] Delete protection is implemented via `on_delete=PROTECT` on FKs from `Student*Status` models to definition models; hard deletion is blocked at the ORM layer without requiring instance-level `delete()` overrides, since `QuerySet.delete()` bypasses those.
- [ ] Every foreign key from one definition table to another uses `on_delete=CASCADE`: criterion to group, group to parent group, group to tag, and criterion to objecttag. The one exception is the criterion's foreign key to `CompetencyRuleProfile`, which uses `PROTECT`, because a rule profile is never hard-deleted at all. These values are what make ADR-0002 Decision 7's delete protection work. That protection is conditional, not a blanket ban: deleting a tag has to succeed when no learner has a status under it, and fail when one does. The `PROTECT` that produces the failure lives on the foreign keys from the three `Student*Status` tables, and two of those point at rows one and two levels below the tag. Django reaches them only by walking down the tree from the tag, and it only walks down a foreign key marked `CASCADE`. Change any link in that chain to `SET_NULL` and deleting the tag succeeds while learner statuses still exist.
- [ ] The transitive cases are tested, not only the direct ones: deleting an `oel_tagging_tag` with a learner status row anywhere beneath it raises `ProtectedError`, and deleting one with no status rows beneath it succeeds and cascades.
- [ ] `CompetencyRuleProfile` is never hard-deleted, even before any learner status exists. Archiving is the only way to take it out of use, through its `archived` column, per ADR-0002 Decision 7's exception, because a profile is shared across many criteria rather than tied to one.

## Out of scope

The `archived` column itself. #641 creates it as one of `CompetencyRuleProfile`'s columns, per ADR-0002
Decision 3. What this issue adds is the rule that archiving goes through it.

The edit guardrails from ADR-0003 Decision 4, meaning the Studio warning and confirmation when someone
edits criteria that learners already have status against. #655 covers edits as well as deletes, but that
warning is API and UI work, not model work.

## Depends on

#655 for the approach. #641 and #642 for the tables and the foreign keys to change.


