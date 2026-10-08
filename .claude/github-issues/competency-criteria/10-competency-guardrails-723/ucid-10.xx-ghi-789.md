# [Release Docs] Docs for Guardrails

GitHub: https://github.com/openedx/openedx-core/issues/789 (#789, OPEN)
Cached: 2026-09-21

## User Story

As a platform administrator or operator, I want documentation of what happens when competency configuration is deleted or edited, in order to know what is preserved, what is not, and what I can tell an author who asks.

## Acceptance Criteria

```
Scenario: The documentation explains what a delete does
  When a reader consults the competency documentation about deleting configuration
  Then it explains that a record no learner has been evaluated against is removed
    And that a record learners have been evaluated against is archived and kept
    And that the author is not told which of the two happened

Scenario: The documentation explains what an edit does
  When a reader consults the documentation about editing a competency rule
  Then it explains that the change applies to future evaluations only
    And that learners already evaluated keep the status they earned

Scenario: The documentation explains what an archived record does and does not do
  When a reader consults the documentation about archived competency configuration
  Then it explains that an archived record stops appearing in authoring and search
    And that learner mastery recorded through it remains intact and resolvable

Scenario: The documentation explains re-applying a previously removed tag
  When a reader consults the documentation about re-adding a competency tag to content
  Then it explains that the original association returns rather than a fresh one
    And that its previous learner mastery history returns with it

Scenario: The release note describes the change for operators
  When an operator reads the release notes
  Then they can tell what changes about deleting and editing competency configuration
    And that instances with no competency mastery recorded see no change in behavior
```

## Description

There is no documentation of what deleting or editing competency configuration does, because until this use case the answer was simply that it deleted the record. The behavior after this work is materially different and much less obvious: the same action produces one of two outcomes, the author is deliberately not told which, and a re-added tag brings its history back with it.

The existing docs ticket \#651 covers the earlier approach, where the delete control was removed when deletion was prohibited. That is no longer what happens, so its framing needs replacing rather than extending.

## Technical Details

This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done.

### In short

**What has to be documented, and why it is not self-evident.** Three things in this behavior will surprise a reader who has not read the design. The same delete action does one of two different things. The author is deliberately not told which, so support cannot infer it from what the author saw. And re-adding a previously removed competency tag resurrects the original association along with the learner mastery earned through it, rather than starting clean, which is the opposite of what "delete then re-add" usually means.

**Separate what an author sees from what an operator needs.** An author needs to know that their edit affects future evaluations only and that their delete cannot be undone from that screen. An operator needs to know that archived records stay in the database, that they disappear from search once the index catches up, and that nothing changes at all on an instance with no competency mastery recorded.

**Do not document the mechanism as author-facing guidance.** The removed-versus-archived distinction is deliberately hidden from authors in the product. Explaining it plainly in operator documentation is right; putting it in author-facing help would undo the decision the confirmations were designed around.

### Implementation specifics

- **Cover the delete outcome rule:** a record with no learner mastery recorded against it is removed; one with mastery recorded is archived and kept; the author sees the same confirmation and the same result either way.  
- **Cover the five record types** the rule applies to: `Tag`, `Taxonomy`, `ObjectTag`, `CompetencyCriteria`, and `CompetencyCriteriaGroup`. Note separately that `CompetencyRuleProfile` has no delete at all and is only ever archived.  
- **Cover the edit rule:** competency criteria and criteria group edits apply to future evaluations only and never rewrite an earned status; tag and taxonomy edits carry no warning because they do not change how mastery is computed.  
- **Cover what archiving means for a reader:** the record stops appearing in tag lists, searches, autocompletes, exports, and usage counts, and learner mastery recorded through it stays intact.  
- **Cover the re-apply behavior explicitly**, because it is the least intuitive part: re-adding a competency tag to content returns the original association and its mastery history rather than creating a new one.  
- **Cover the search-index timing:** an archived taxonomy's tags stop appearing in search once the reindexing triggered by the change has been processed, not instantly.  
- **The release note should state that instances with no competency mastery recorded see no behavioral change**, since that is the majority of deployments and the most useful single fact for an operator deciding whether to care.  
- **Reference the guardrails tickets by number** once they have GitHub issue numbers, rather than by the internal identifiers used while this set was being drafted.  
- **Revise \#651 rather than leaving it.** It describes removing the delete button when deletion is prohibited, which is not the behavior being shipped. Either fold it into this ticket or close it in favor of this one; do not ship both.  
- **Out of scope:** the two out-of-scope placeholders in this use case, and documentation of the competency mastery evaluation itself, which \#729 covers.  
- Context The approved implementation approach on \#655, which is the source for the delete outcome rule, the edit rule, and the decision to hide the distinction from authors.  
- 10.2 for the confirmation wording an author actually sees.  
- 10.5 for what archiving hides, 10.6 for the re-apply behavior, and 10.8 for the search-index timing.  
- \#651 covers the superseded approach and needs revising or closing in favor of this ticket.  
- \#729 documents competency mastery evaluation and is the neighbouring docs ticket, not a duplicate of this one.

## Open Questions

- Should \#651 be revised into this ticket or closed in favor of it? Its current title and body describe behavior that is not being built. Owner: BA.
