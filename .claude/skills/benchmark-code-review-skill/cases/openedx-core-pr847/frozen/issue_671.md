# openedx/openedx-core issue #671: [FE] "+ Rule" & "+ Rule Group" Buttons

State: OPEN. updated_at: 2026-10-15T13:42:54Z

---

## User Story

As a course author, I want to add a new bottom-tier group or a new rule box to a competency and set its combining logic or score before any content lands in it, in order to shape a mastery rule's structure as I build it up.

## Acceptance Criteria

```
Scenario: Add a rule box to an existing bottom-tier group
  Given a bottom-tier group containing at least one rule box that already has content
  When I add a rule box
  Then a new empty rule box appears in that same group and takes focus
  And it shows the score the system applies by default
  And the rule boxes that already had content are unchanged

Scenario: Add a bottom-tier group to a course
  Given two courses' rules are shown, and one of those courses has one bottom-tier group
  When I add a bottom-tier group to that course
  Then a second bottom-tier group appears under that same course and takes focus
  And it defaults to requiring any one of its rule boxes
  And a connector appears between the two bottom-tier groups, showing the same combining choice as any other connector in that course
  And the other course's bottom-tier groups are unchanged

Scenario: Only one empty target exists at a time
  Given an empty rule box or an empty bottom-tier group is on the page with no content in it
  When I look for the controls to add another rule box or bottom-tier group
  Then both controls are disabled until I add content to the empty one
  And each explains that the empty one must be filled first

Scenario: Adding an empty bottom-tier group replaces an empty rule box
  Given I have added an empty rule box and put no content in it
  When I add a bottom-tier group instead
  Then the empty rule box is gone
  And the new empty bottom-tier group is the only empty target on the page

Scenario: Expanding a course takes focus away from an empty bottom-tier group or rule box
  Given I have added an empty bottom-tier group or an empty rule box, so it is in focus
  And the course I am about to expand already has bottom-tier groups for this competency
  When I expand that course in the content panel
  Then the empty bottom-tier group or rule box is gone
  And content I select afterwards is added to one of that course's existing bottom-tier groups

Scenario: An empty rule box or bottom-tier group is never kept
  Given I have added a rule box or a bottom-tier group and put no content in it
  When I reload the page
  Then the empty rule box or bottom-tier group is gone
  And every rule box and group that has content is still there, unchanged

Scenario: Set a placeholder bottom-tier group's combining logic before anything is saved
  Given a new, empty bottom-tier group that I have set to require all of its rule boxes
  When the first content is added to a rule box inside it
  Then the bottom-tier group is saved requiring all of its rule boxes, not requiring any one

Scenario: A placeholder rule box's score cannot duplicate one already in the same group
  Given a bottom-tier group containing a rule box that already requires a given score
  When I set an empty rule box in that same group to that same score
  Then the change is refused and the reason is shown
  And the existing rule box's score is unchanged

Scenario: A new rule box whose default score is already used in its group says so
  Given a bottom-tier group with a rule box that already uses the system default score
  When I add a rule box to that group
  Then the new rule box's score settings open with the score selected
  And a message says another rule in this group already uses that score
  And an unused score is offered that I can apply in one step
  And the offered score is the nearest unused one, 5 points stricter at a time with the same comparison (for example, 75% or higher becomes 80% or higher, and 40% or lower becomes 35% or lower)

Scenario: Content is not added to a new rule box until its score is unique in its group
  Given a new rule box whose score another rule box in the same group already uses
  When I select content to add to it
  Then the content is not added
  And the score settings reopen with the message shown as an error

Scenario: A rule box I have not edited keeps following the system default
  Given a placeholder rule box showing the default score, which I have never changed
  When content is added to it
  Then that content is judged by whatever the system default supplies at evaluation time
  And it is not judged by a fixed copy of the number that was on screen when I added it

Scenario: A placeholder rule box I have edited keeps the score I set
  Given a placeholder rule box whose score I have changed from the default
  When content is added to it
  Then that content is judged by the score I set, not by the system default

Scenario: No controls to add anything are offered when the panel could not load
  Given the request for a competency's existing rules fails
  When I open that competency
  Then no control to add a bottom-tier group or a rule box is offered

Scenario: A course I can see but cannot write to offers no way to add to it
  Given a competency has rules against a course I can see via content search but do not have studio write access to
  When I view that course's rules
  Then I can read them
  And no control to add a bottom-tier group or a rule box is offered for that course
```

<img width="1211" height="876" alt="Image" src="https://github.com/user-attachments/assets/bee085b4-d36d-4d81-9b8e-b16ed51d54e8" />

<img width="1212" height="878" alt="Image" src="https://github.com/user-attachments/assets/0a1943c8-6720-4c85-aca2-5a4f69c5fcbe" />

## Description

\#672 renders a competency's existing associations: the per-course sections, the bottom-tier group cards, the rule boxes inside them, and the chips inside those, all read-only. This ticket adds the two controls that create a new, not-yet-saved bottom-tier group or rule box inside that structure, makes the combining-logic and score controls editable on those not-yet-saved cards only, and carries the author's choices onto the request that saves the first piece of content into them.

This ticket has nothing to render for a competency with no associations at all: \#672 shows an empty-state message in that case, not a card, so a not-yet-saved bottom-tier group only ever appears inside a course section that already exists.

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done; what follows exists to save the implementer some thinking, not to bind them.

### In short

**Adding a group or a rule box never calls the backend.** There is no endpoint that creates a Competency Criteria Group on its own: groups come into existence only as a side effect of creating the first criterion inside them, and the data model forbids storing a group with nothing in it. So both add actions here are pure client-side state changes. The author adds an empty box, then selects content into it, and the single create-criterion request \#672 sends is what brings the group into existence on the server, carrying the operator and score this ticket's card is displaying at that moment.

**A placeholder is not a separate piece of state; it is the attributes of whichever unbacked target is currently in focus.** \#672 stores focus as one pair, the bottom-tier group and the rule box within it, and every writer it has sets both parts to real values. This ticket gives an unset part its second meaning: an unset group is the not-yet-saved bottom-tier group, and an unset rule box inside a real group is the not-yet-saved rule box. Because that pair has exactly one slot per level, there can be at most one placeholder group and at most one placeholder rule box on the page at any moment, and a placeholder stops existing the instant focus moves to something real, whether because the author clicked elsewhere, expanded a course, or saved content. This ticket adds to the provider only the values a placeholder needs and a real row already has: which course section a placeholder group belongs under, the any/all operator the author chose for it, and the score the author typed into a placeholder rule box. Implementing the placeholder as an independent object with its own lifetime, cleaned up by an effect when focus changes, would create a second thing to keep consistent with focus and a cleanup path that is easy to forget when later tickets add state.

**The placeholder card is not a new component; it is the existing card given placeholder values.** \#672 builds `CriteriaGroupBox`, `RuleBox`, `LogicOperatorSelect`, `ScoreThresholdField`, and `GroupConnector`, and builds the lists that render them per course and per group. This ticket appends a placeholder entry to those two lists rather than drawing a parallel card of its own: the placeholder bottom-tier group is one more child in its course section, which also means the section draws one more connector, and the placeholder rule box is one more entry in its group's rule box list, sorted last. Rendering it any other way would give the page two card implementations that have to be kept looking alike.

**The two field components are already built to be edited; this ticket is the first caller that edits them.** Each takes an optional change handler, and renders read-only text when it is not given one. \#672 never gives one. Here the placeholder bottom-tier group's card passes one that writes the chosen operator into the provider, and the placeholder rule box passes one that writes the entered score there. Nothing about the components changes.

**Both add controls are disabled whenever any placeholder is on the page, which is a single condition.** An unset group always implies an unset rule box, because a placeholder bottom-tier group's own rule box is a placeholder too, so "some placeholder exists" reduces to the rule box part of focus being unset. Writing the two controls against two separate conditions instead would leave the group control live while an empty rule box sat on the page, which is not what the author is shown.

**What this ticket adds to the request that saves the first content into a placeholder.** \#672's create call already handles two cases: content selected into a real group in the same course, and everything else. This ticket adds the two cases a placeholder introduces. When the placeholder rule box inside a real group is in focus and the selected subsection is from that group's course, the request targets that group and carries the author's score, but only if the author actually changed it: the number a placeholder displays is a presentation default, not a value anyone set, and sending it as an override would assert a rule the author never chose. When the placeholder bottom-tier group is in focus and the selected subsection is from the course that placeholder sits under, the request names no group, so the backend builds one, and carries the author's any/all choice, which unlike a score is never unset and so is always sent. If the author picks content from a different course than the one the placeholder sits under, the placeholder is not the target at all and neither the operator nor the score is sent.

**A rule box's identity is its rule, so a placeholder cannot be given a score another box in its group already has.** If it were, the criterion created from it would join that other box and the placeholder would simply vanish on the next refetch, with no explanation the author could act on. \#672 owns both halves of what is needed to detect this: the helper that computes a rule's identity key and the helper that lists a group's existing rule boxes. This ticket refuses the value in the field using those two, rather than adding a shared validation helper, since the sibling ticket that edits a persisted row's score writes the same one-line check against the same two helpers and neither needs the other to exist.

**Being rendered at all and being writable are two different gates, and this ticket only needs to check the second one.** \#672 already decides whether a course-level group renders at all, based on content-search visibility; \#672 also established that content search can return a course the author can only read, not write to. So a rendered bottom-tier group card is not automatically one the author may add to. Every add control this ticket builds is gated by whether the author has studio write access to that card's course, the same `oel_tagging.can_tag_object` composite \#665's endpoint enforces server-side; \#672 resolves this per course via Studio's permission-validation API and exposes it as `canEditCourse(courseId)` on the provider. No add control appears when the panel failed to load or found nothing either, but for a simpler reason: the controls live on a rendered bottom-tier group card, and neither of those states renders one.

**Nothing here may assume a single course on the page.** The panel can show several course sections at once, each independently collapsible (\#672's scope); the placeholder records which course-level group it belongs under, and the card that renders it appears in that section only, regardless of how many other sections are expanded or collapsed alongside it.

### Implementation specifics

- **No mutation endpoint is called by this ticket at all.** The only backend contact is the create-criterion request \#672 already makes, which this ticket extends with two additional cases. Persisting a change to an existing bottom-tier group's operator or an existing rule box's score belongs to a sibling ticket with no GitHub issue number yet.  
- **Provider additions.** Extend `src/taxonomy/competency-management/CompetencyAssociationsContext.tsx` with `addPlaceholderGroup`, `addPlaceholderRuleBox`, `placeholder`, `setPlaceholderLogicOperator`, and `setPlaceholderRulePayload`, where `placeholder` is `{ parentRuleGroupId: number; logicOperator: 'AND' | 'OR'; rulePayload: GradeRulePayload | null }`. `parentRuleGroupId` is never null: a placeholder bottom-tier group can only be added inside a course section that already exists, so there is always a real course-level group to record it under.  
- **Placeholder existence is derived, never stored.** A placeholder bottom-tier group exists exactly when `focus.groupId === null` and at least one course-level group is visible; a placeholder rule box exists exactly when `focus.ruleKey === null`. Do not add a boolean for either. The `placeholder` fields above are only meaningful while the corresponding part of `focus` is unset.  
- **`addPlaceholderRuleBox(groupId)`** writes `focus = { groupId, ruleKey: null }` and resets `placeholder.rulePayload` to `null`. It takes the id of the group whose "+ Rule" control was clicked rather than reading the group currently in focus, because the control sits on a specific card and clicking it must add the placeholder to that card's group. Writing both parts of the pair together also keeps \#672's rule that no setter writes one focus field alone. A `rulePayload` of `null` means the author has not changed the displayed default, which is the distinction the create call needs in order to decide whether to send rule fields at all.  
- **`addPlaceholderGroup(parentRuleGroupId)`** writes `focus = { groupId: null, ruleKey: null }`, sets `placeholder.parentRuleGroupId`, and resets `placeholder.logicOperator` to `'OR'` and `placeholder.rulePayload` to `null`. Called only from the "+ Rule Group" control inside an already-rendered course section, so `parentRuleGroupId` is always a real, existing course-level group's id. There is no equivalent action for a competency with no course-level groups at all: \#672 renders an empty-state message for that case instead of a card, and the first association for such a competency is created directly from the content panel with no card of this ticket's ever involved.  
- **Add-button disabled rule.** Both "+ Rule" and "+ Rule Group" are disabled while `focus.ruleKey === null`. Give each a tooltip saying an empty box must be filled first, and wrap the disabled button in a span for the tooltip trigger, since a disabled button fires no mouse events.  
- **Placeholder bottom-tier group rendering.** In `criteria-groups/RuleGroupSection.tsx`, append one extra `CriteriaGroupBox` to the section whose course-level group id equals `placeholder.parentRuleGroupId` while `focus.groupId === null`, after that section's real group cards, and include it in the count that decides how many `GroupConnector`s to draw.  
- **Placeholder rule box rendering.** In `criteria-groups/RuleBoxList.tsx`, append one extra `RuleBox` after the derived boxes when `focus.ruleKey === null` and that list's group is the one in focus, or when the list belongs to the placeholder bottom-tier group. Pass it the system default rule to display, read from `useDefaultCompetencyRuleProfile()`; the provider already runs the same query, so this resolves from cache and the panel has already waited on it before rendering anything.  
- **Editable placeholder fields.** Pass an `onChange` to the `LogicOperatorSelect` on the placeholder bottom-tier group's card, wired to `setPlaceholderLogicOperator`, and to the `ScoreThresholdField` on the placeholder rule box, wired to `setPlaceholderRulePayload`. Pass no `onChange` anywhere else; that is what keeps every persisted row read-only.  
- **Duplicate score inside one group.** Supply `getInlineValidationMessage` to the placeholder rule box's `ScoreThresholdField`, returning a message when `ruleBoxesForGroup(groupId)` already contains a box whose key equals `ruleKeyOf` of the candidate rule. Both helpers are \#672's. Add the message to `messages.ts` if it is not already there; the sibling ticket that edits a persisted row's score writes the same check independently and may have added it first.  
- **A new rule box whose default score is already taken.** Because most rule boxes use the system default, "+ Rule" often creates a box whose default score matches an existing one, and the inline check above only runs on a score the author types. Add `nextUnusedScore(rule, boxes)` to `utils.ts`: it steps 5 points stricter at a time and keeps the operator (`gte` goes up, `lte` goes down) until it finds a score no box in the group uses. When the placeholder's score is taken, open its score field with the score selected, show "Another rule in this group already uses {score}. Choose a different score.", and offer a "Use {score}" link that applies the suggestion. If the author selects content while the score is still taken, refuse it before any request is sent.  
- **Create-request additions.** Extend `associateSubsection` in the provider, and the `createCompetencyCriterion` payload type in `data/types.ts`, with two cases beyond the two \#672 defines. When `focus.groupId` is a real group whose course matches the selected subsection and `focus.ruleKey` is `null`, send `group_id: focus.groupId`, and send `rule_type_override` and `rule_payload_override` from `placeholder.rulePayload` only when it is not `null`. When `focus.groupId` is `null` and `placeholder.parentRuleGroupId` is the course-level group of the selected subsection's course, omit `group_id`, send `logic_operator` carrying `placeholder.logicOperator` unconditionally, and send the rule fields from `placeholder.rulePayload` only when it is not `null`. When `focus.groupId` is `null` but the selected subsection belongs to a different course than the placeholder's, fall through to \#672's existing behavior of omitting `group_id` and every optional field, since the author's choices were made about a group in another course.  
- **`logic_operator` is added to the API surface here.** Add the field to `createCompetencyCriterion`'s request payload type and to the request body it builds in `data/api.ts`. \#672 deliberately leaves it out, because nothing in that ticket can populate it.  
- **Focus after a successful create needs no work here.** \#672 writes both parts of focus from the group id in the response and the rule key of whatever rule the request sent, falling back to the system default's key when it sent none. That rule already covers both of this ticket's cases, so the placeholder resolves into the real card it became without any additional handling.  
- **The score conversion is not repeated here.** `ScoreThresholdField` converts between the displayed percentage and the stored fraction, so `placeholder.rulePayload` already holds the fraction the API expects and this ticket passes it through untouched.  
- **Permission gating.** Route both add controls through \#672's `canEditCourse(courseId)`, read from the provider context, resolved for the course the card's group belongs to; do not define a second copy or fetch this ticket's own permission data.  
- **All user-facing strings** go through `defineMessages` in the feature's `messages.ts`, per this MFE's i18n convention.  
- **Module boundaries.** Import other features only through their `index.ts`, and do not import upward from `competency-management` into `taxonomy`. Nothing here touches `openedx-core`, so its import-layering and DEPR rules do not apply.  
- **Out of scope, owned elsewhere.** Rendering a persisted bottom-tier group card, rule box, connector, chip, or course-level header, the panel's loading, error, and empty states, the display-name lookup, the group and rule-box derivation helpers, the default rule profile fetch, the create-criterion request itself, and course-expansion focus all belong to \#672. Persisting a change to an existing bottom-tier group's combining operator or an existing rule box's score belongs to a sibling ticket with no GitHub issue number yet. The content panel's browse, search, and course tree belong to \#670. Deleting a group is \#709; deleting a single association is \#710. Renaming a group has no authoring control in this design and is not built. Adding a course-level group directly is not a thing the UI does: one is created implicitly by \#672's create call when the author selects content from a course that has none.  
- **Test cases to cover.**  
  - "+ Rule" on a card that is not currently in focus adds the empty rule box to that card's group, not to the group that was in focus.  
  - "+ Rule" puts the new empty rule box in focus and disables both add controls until it has content.  
  - "+ Rule Group" adds an empty bottom-tier group inside the same course section, puts it in focus, defaults its operator to "any", and disables both add controls.  
  - "+ Rule Group" while an empty rule box is on the page removes the empty rule box.  
  - Clicking a persisted group, or expanding a course that has groups, while a placeholder exists removes the placeholder.  
  - A course section holding two real bottom-tier groups plus a placeholder renders three cards and two connectors.  
  - A placeholder rule box's score field is editable; every persisted rule box's score field in the same group stays read-only.  
  - Typing 75 into a placeholder's score field leaves `placeholder.rulePayload` holding `0.75`, not `75`.  
  - The field rejects a decimal, a non-numeric character, and a value outside 0-100; entering 100 is accepted as the one valid three-digit value.  
  - Setting a placeholder's score to a value another box in the same group already carries is refused with an inline message, and the existing box is unchanged.  
  - Selecting a subsection with a placeholder rule box in focus and an unchanged score sends `group_id` and no rule fields; with a changed score it sends `group_id` and both rule fields.  
  - Selecting a subsection with a placeholder bottom-tier group in focus sends no `group_id`, sends `logic_operator` whether or not the author changed it, and sends rule fields only when the author changed the score.  
  - Selecting a subsection from a course other than the one the placeholder bottom-tier group sits under sends neither `group_id`, `logic_operator`, nor rule fields.  
  - A failed panel load renders no add control at all.  
  - A course the author can see but cannot write to renders the add buttons as non-interactive.

Files to create and modify Every path under `src/taxonomy/competency-management/` is provisional: that directory is created by \#670 and \#672. Confirm the real names once those land, and extend the files they created rather than adding parallel ones. This ticket creates no new files; all of its work extends files \#672 builds, which is what keeps the dependency between the two running one way.

**Modified files**

| File | Nature of modification |
| :---- | :---- |
| `src/taxonomy/competency-management/CompetencyAssociationsContext.tsx` | Add `addPlaceholderGroup`, `addPlaceholderRuleBox`, `placeholder`, `setPlaceholderLogicOperator`, and `setPlaceholderRulePayload`; extend `associateSubsection` with the two placeholder cases. |
| `src/taxonomy/competency-management/CompetencyAssociationsContext.test.tsx` | Placeholder lifecycle at both levels, the one-at-a-time rule, placeholder removal when focus moves to a persisted target, and the create payload each placeholder case produces. |
| `src/taxonomy/competency-management/criteria-groups/CriteriaGroupBox.tsx` | Add the "+ Rule" and "+ Rule Group" controls and their shared disabled rule; pass an `onChange` to `LogicOperatorSelect` when the card is the placeholder bottom-tier group. |
| `src/taxonomy/competency-management/criteria-groups/CriteriaGroupBox.test.tsx` | The two add actions, their shared disabled state and tooltips, and the placeholder card's editable operator against a persisted card's read-only one. |
| `src/taxonomy/competency-management/criteria-groups/RuleGroupSection.tsx` | Append the placeholder bottom-tier group card to the section it belongs under, and include it in the connector count. |
| `src/taxonomy/competency-management/criteria-groups/RuleGroupSection.test.tsx` | Placeholder card placement across two course sections, and connector count with a placeholder present. |
| `src/taxonomy/competency-management/criteria-groups/RuleBoxList.tsx` | Append the placeholder rule box last, showing the system default rule, with an `onChange` and a `getInlineValidationMessage` on its `ScoreThresholdField`. |
| `src/taxonomy/competency-management/criteria-groups/RuleBoxList.test.tsx` | Placeholder rule box ordering, its editable score field, the fraction round trip, and the duplicate-score refusal. |
| `src/taxonomy/competency-management/data/api.ts` | Add `logic_operator` to the body `createCompetencyCriterion` builds. |
| `src/taxonomy/competency-management/data/types.ts` | Add `logic_operator` to the create-request payload type. |
| `src/taxonomy/competency-management/messages.ts` | Add strings for the two add controls, their disabled tooltips, the duplicate-score message if it is not already present, and the default-score-taken hint and "Use {score}" link. |
| `src/taxonomy/competency-management/utils.ts` | Add `nextUnusedScore`. |

- Context **\#672** builds everything this ticket extends: the provider and its focus pair, the per-course section, the bottom-tier group card, the rule box, the connector, the operator and score field components with their optional `onChange` and validation seams, the `ruleKeyOf` and `ruleBoxesForGroup` helpers this ticket's duplicate check uses, `canEditCourse` for permission gating, the default rule profile fetch, and the create-criterion request. This ticket adds no new files of its own.  
- ADR `docs/openedx_learning/decisions/0002-competency-criteria-model.rst` in `openedx-core` is the source for three facts this ticket relies on: a persisted group is never empty, which is why no add action can call the backend on its own; a criterion carries either a shared rule profile reference or its own complete override, never both and never neither, which is why an unchanged placeholder score must not be sent; and a Grade rule payload is `{op, value, scale}` with `value` a fraction between 0.0 and 1.0.  
- The associations panel's control for adding a bottom-tier group is labeled "+ Rule Group" but creates a bottom-tier group, not a course-level group. This ticket set uses "bottom-tier group" and "rule box" throughout rather than the signed-off design's own terms, to keep this distinction unambiguous. Kept as-is here.  
- There is no group-create endpoint and no UI action that creates a course-level group directly. \#665 creates whatever part of the hierarchy is missing as a side effect of creating the first criterion.  
- \#773 provides the system default rule profile endpoint behind the score a placeholder rule box displays. \#672 owns the fetch.  
- Frontend prior art: `src/taxonomy/tree-table/TreeTableContext.tsx` for the context shape, `src/taxonomy/tree-table/EditableCell.tsx` for the `getInlineValidationMessage` prop this ticket supplies, `src/taxonomy/tag-list/hooks.ts` for a caller building one of those validators, and `src/grading-settings/credit-section/index.jsx` for a percentage input backed by a stored fraction.  
- Related tickets: \#670 builds the page and the content panel; \#681 supplies the group and criterion data; a sibling ticket with no GitHub issue number yet owns persisting a change to an existing group's operator or an existing rule box's score; \#709 and \#710 own deleting a group and an association.
</details>

