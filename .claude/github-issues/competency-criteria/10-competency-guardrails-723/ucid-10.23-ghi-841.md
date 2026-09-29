# [FE] Explain archived competency rules in the Courses & Content panel

GitHub: https://github.com/openedx/openedx-core/issues/841 (#841, OPEN)
Cached: 2026-09-25

## User Story
As a course author, I need to know which courses' rules for a competency were archived, in order to understand why I can't add new Competency Criteria associations for that course.

## Description
This ticket updates the Courses & Content panel so that when a course's course-level group for the selected competency is archived, expanding that course shows a sentence explaining the situation instead of displaying the course's sections and gradeable subsections. This should work like the "This course has no gradeable subsections." text that already appears in an expanded course row. The list of archived courses comes from the `archived_course_keys` field that #840 adds to #681's response.

## Context
- #840 adds `archived_course_keys` to #681's response, listing the course runs whose course-level group for this competency is archived.

## UX Design

@illiphilli, please add the UX design screenshot(s) and the Figma link for this ticket.

- Figma: TBD
- Screenshots: TBD

## Acceptance Criteria

```gherkin
Scenario: Expanding an archived course shows the archived-rules message instead of its outline
  Given I have selected a competency
  And course run X's course-level group for that competency is archived
  When I expand course run X in the Courses & Content panel
  Then in place of its sections and gradeable subsections, the row shows the archived-rules
    message: "This course's rules for this competency were archived, so no new competency
    criteria associations can be added. This applies only to this course run. Learners'
    recorded progress is kept."
  When I collapse course run X and expand it again
  Then the row shows the archived-rules message again

Scenario: An archived course stays in the course list and can be found by search
  Given course run X's course-level group for the selected competency is archived
  When I view the page of the Courses & Content panel's course list that course run X falls on,
    with no search term or date range applied
  Then course run X is listed there with its expand control, like any other course
  When I search for course run X's title
  Then course run X is among the results
  And expanding it shows the archived-rules message

Scenario: An archived course on another page of the course list shows the message there
  Given course run X's course-level group for the selected competency is archived
  And course run X is listed on a different page of the Courses & Content panel's course list
    than the one I am viewing
  When I move to the page that lists course run X and expand it
  Then the row shows the archived-rules message in place of its outline

Scenario: A course with an active course-level group shows its normal outline, even with archived Rule Groups or criteria under it
  Given course run Y's course-level group for the selected competency is active
  And some of its Rule Groups or criteria for that competency are archived
  When I expand course run Y
  Then its sections and gradeable subsections are shown as usual
  And the archived-rules message is not shown

Scenario: The message follows the selected competency
  Given course run X's course-level group is archived for competency A
  And course run X's course-level group for competency B is not archived
  When I select competency B and expand course run X
  Then its sections and gradeable subsections are shown as usual
  When I select competency A and expand course run X
  Then the row shows the archived-rules message

Scenario: Another run of the same course is unaffected
  Given course run X1's course-level group for the selected competency is archived
  And course run X2 is another run of the same course whose course-level group for that
    competency is not archived
  When I expand course run X2
  Then its sections and gradeable subsections are shown as usual

Scenario Outline: The archived-rules message replaces every other state of the course's content
  Given course run X's course-level group for the selected competency is archived
  And <other state>
  When I expand course run X
  Then the row shows only the archived-rules message in place of its outline

  Examples:
    | other state                                                                             |
    | a competency above or below the selected one already has an association in course run X |
    | I can see course run X but do not have write access to it                               |
    | course run X has no gradeable subsections                                               |
    | course run X's outline cannot be loaded                                                 |

Scenario: While the associations panel's data is loading, an archived course shows its normal outline until it loads
  Given course run X's course-level group for the selected competency is archived
  And the associations panel's data has not finished loading
  When I expand course run X
  Then its sections and gradeable subsections are shown as usual
  When the associations panel's data finishes loading
  Then without a page reload, the row shows the archived-rules message in place of the outline

Scenario: If the associations panel's data fails to load, an archived course shows its normal outline
  Given course run X's course-level group for the selected competency is archived
  And the associations panel's data failed to load
  When I expand course run X
  Then its sections and gradeable subsections are shown as usual

Scenario: A delete that archives a course's rules switches its expanded row without a reload
  Given learners have recorded progress against the selected competency's rules in course run X
  And course run X is expanded in the Courses & Content panel, showing its outline
  When I delete everything course run X has for this competency, whether by deleting its
    course section, its last Rule Group, its last Rule Box, or its last association in the
    Competency Criteria Associations panel, or by removing its last association from its chip
    in course run X's own outline in the Courses & Content panel
  Then without a page reload, course run X's expanded row shows the archived-rules message in
    place of its outline
  And any other expanded course already showing the archived-rules message keeps showing it
    throughout

Scenario: A delete that removes a course's rules outright leaves its outline in place
  Given no learner has recorded progress against the selected competency's rules in course run X
  And course run X is expanded in the Courses & Content panel, showing its outline
  When I delete everything course run X has for this competency
  Then course run X's expanded row keeps showing its outline
  And the archived-rules message is not shown

Scenario: The message is readable on a small screen
  Given I view the page on a small screen
  When I expand a course whose course-level group for the selected competency is archived
  Then the whole archived-rules message wraps within the course row, with no horizontal
    scrolling and no truncated text
```

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done.

**Summary**

The archived list that #840 adds to #681's response is read from the #681 query that #672's provider already runs, and is exposed as `isCourseArchived(courseId)` next to `canEditCourse`. An expanded `CourseRow` for an archived course renders the new message instead of mounting `CourseOutlineSubtree`, so the outline is never fetched. The lookup fails open and keeps its last list through refetches.

**Approach**

1. Add `archivedCourseKeys: string[]` to #681's response type in `data/types.ts`. `camelCaseObject` changes only the key, so each value matches a `course.courseKey` as it is.
2. Add `isCourseArchived(courseId)` to the `CompetencyAssociationsContext` value next to `canEditCourse`. Back it with a `Set` memoized from `data?.archivedCourseKeys ?? []` on the provider's existing `useCompetencyCriteriaGroups` query, and have the context's no-op default return `false`. Because the value rides on that query, it needs no new request and adds no invalidation to #709, #710, or #833: the refetch those deletes already make is what switches a newly archived course. Reading `?? []` also makes an MFE running against a backend without #840 fail open.
3. Derive the lookup from `data` only, never from the loading or error flags, so that it fails open. It returns `false` while the first fetch is loading or after it fails. That is the opposite default from `canEditCourse`, and it is safe because #717 still rejects the write. The lookup also keeps the last list through a background or failed refetch, so a row already showing the message doesn't flicker. A stale list is safe because a course-level group can't be unarchived, so a stale list can only leave courses out.
4. In `course-search/CourseRow.tsx`, when the row is expanded and `isCourseArchived(course.courseKey)` is true, render a new `archivedCourseRulesMessage` from `course-search/messages.ts` instead of mounting `CourseOutlineSubtree`. Use the same markup as `noGradedSubsectionsMessage`. Not mounting the subtree skips the outline fetch, because the subtree's own mount is its fetch gate. It also makes the message replace #797's disabled content and the permission-gated controls, which all live inside the outline.
5. Test two edge cases:
   - After a page or search change, #683's scoped query reloads, and a course expanded during that reload shows its outline and then switches to the message. Don't add `placeholderData` to hide this, since #683 requires the associations data to change with the page.
   - When the delete that archives a course starts from #710's chip inside that course's own outline, the refetch unmounts the chip. Confirm #710's post-delete handling still runs, because React Query skips a per-call `mutate` callback after its component unmounts.
6. Out of scope: the field itself (#840), the Competency Criteria Associations panel (#672 already omits archived groups), and the server-side rejection (#717).

**Files to create and modify**

| File | Change |
| --- | --- |
| `src/taxonomy/competency-management/data/types.ts` (path provisional) | modified: add `archivedCourseKeys` |
| `src/taxonomy/competency-management/CompetencyAssociationsContext.tsx` (path provisional) | modified: add `isCourseArchived` |
| `src/taxonomy/competency-management/course-search/CourseRow.tsx` | modified: render the message in place of `CourseOutlineSubtree` |
| `src/taxonomy/competency-management/course-search/messages.ts` | modified: add `archivedCourseRulesMessage` |

**Additional context**

- This ticket is blocked by #672, which creates `CompetencyAssociationsContext`, the #681 response type, and `useCompetencyCriteriaGroups`. The #670 pieces this ticket changes, `CourseRow` and `CourseOutlineSubtree`, are already on master (frontend-app-authoring PR #3235).

</details>

## Open Questions

- (architect, final review) When the message replaces an already-expanded outline after a delete, should it be announced to screen reader users? Options: A) plain text matching `noGradedSubsectionsMessage`, with no live region; B) wrap it in `role="status"`. Recommended: A for the MVP, since the same message renders on every ordinary expand and screen readers announce a live region inserted with its content inconsistently.
