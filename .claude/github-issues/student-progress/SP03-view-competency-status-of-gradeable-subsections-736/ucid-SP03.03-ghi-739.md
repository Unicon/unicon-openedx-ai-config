# [FE] Display Subsection Competency Statuses for Learner in Course

GitHub: https://github.com/openedx/openedx-core/issues/739 (#739, OPEN)
Cached: 2026-09-21

## User Story
As a learner, I need to know my competency mastery status for each subsection assignment in my course in order to understand what I need to work on improving.

## Description
This ticket implements the oval status indicator display for each subsection assignment in the competency cards on the Course Progress page.

This implementation will call the endpoint built in #738 to get the competency statuses and the Progress API `/api/course_home/v1/progress/{course_key}` to get the subsection percentage scores.

For each subsection, if the learner's competency status on it is:
- Nonexistent, then display the "Available" oval in blue/white with the corresponding icon.
- AttemptedNotDemonstrated, then display the "Not Demonstrated" oval in red with the corresponding icon.
- Demonstrated, then display their percentage score on this assignment in the oval in green with the checkmark icon.

If the course hides the subsection's score from the learner, or the subsection is missing from the Progress API's response, display the "Available" oval, so that it never reveals a hidden result.

## Context
- #738 is the backend counterpart to this ticket.
- Blocked by #734.

## UX Design

@illiphilli, please add the UX design screenshot(s) and the Figma link for this ticket.

- Figma: TBD
- Screenshots: TBD

## Acceptance Criteria

These scenarios use #734's terms (card, group, group line, rule line, placeholder row) and these:

- A named row is a subsection row that shows the subsection's name. A placeholder row is not a named row.
- An oval is the status indicator on a named row. "Available" has an empty-circle icon. "Not Demonstrated" has a circle-with-a-minus icon. "Demonstrated" has a check icon and shows the learner's score on the subsection as a percentage.
- The learner's recorded status on a named row is the status the platform recorded for that learner, on that subsection, for the row's competency, when the subsection's grade was recorded. A learner who hasn't submitted a subsection has no recorded status on it.
- A subsection's results visibility is its assessment results visibility setting in Studio.
- Unless a scenario says otherwise, every subsection is released and its results are always shown to the learner.

```gherkin
Scenario Outline: Each named row shows the oval for the learner's recorded status
  Given "Quiz 1" appears by name under a rule line reading "<rule>"
  And <result>
  When the learner opens the course's Progress tab
  Then Quiz 1's row shows <oval>

  Examples:
    | rule               | result                                                                                     | oval                                       |
    | AT 80% OR BETTER   | the learner hasn't submitted anything in the course                                        | the "Available" oval, with no score        |
    | AT 80% OR BETTER   | the learner scored 12 of 20 points on Quiz 1, so their recorded status is Not Demonstrated | the "Not Demonstrated" oval, with no score |
    | AT 80% OR BETTER   | the learner scored 19 of 20 points on Quiz 1, so their recorded status is Demonstrated     | the "Demonstrated" oval reading "95%"      |
    | AT 60% OR BETTER   | the learner scored 2 of 3 points on Quiz 1, so their recorded status is Demonstrated       | the "Demonstrated" oval reading "66.67%"   |
    | AT 82.5% OR BETTER | the learner scored 33 of 40 points on Quiz 1, so their recorded status is Demonstrated     | the "Demonstrated" oval reading "82.50%"   |
    | AT 40% OR LOWER    | the learner scored 0 of 10 points on Quiz 1, so their recorded status is Demonstrated      | the "Demonstrated" oval reading "0%"       |

Scenario: A subsection under two competencies shows a separate oval under each
  Given "Quiz 3" appears by name under "Analysis", under a rule line reading "AT 80% OR BETTER", and under "Inference", under a rule line reading "AT 90% OR BETTER"
  And the learner scored 17 of 20 points on Quiz 3
  When the learner opens the course's Progress tab
  Then Quiz 3's row under "Analysis" shows the "Demonstrated" oval reading "85%"
  And Quiz 3's row under "Inference" shows the "Not Demonstrated" oval, with no score

Scenario Outline: A row's oval follows whether the learner can see the subsection's results
  Given "Quiz 1" appears by name under a rule line reading "AT 80% OR BETTER"
  And the learner scored <score> on Quiz 1, so their recorded status on it is <status>
  And Quiz 1's results visibility is set to <setting>
  When the learner opens the course's Progress tab
  Then Quiz 1's row shows <oval>

  Examples:
    | setting                                                                                               | score           | status           | oval                                  |
    | never show results                                                                                    | 19 of 20 points | Demonstrated     | the "Available" oval, with no score   |
    | show results once the subsection is past due, and its due date hasn't passed                          | 12 of 20 points | Not Demonstrated | the "Available" oval, with no score   |
    | show results once the subsection is past due, and its due date has passed                             | 19 of 20 points | Demonstrated     | the "Demonstrated" oval reading "95%" |
    | never show individual results, only the overall grade after the due date, and its due date has passed | 19 of 20 points | Demonstrated     | the "Available" oval, with no score   |

Scenario: A subsection that isn't released yet shows the Available oval
  Given "Quiz 4" appears by name under a rule line reading "AT 80% OR BETTER"
  And Quiz 4's release date hasn't arrived
  When the learner opens the course's Progress tab
  Then Quiz 4's row shows the "Available" oval, with no score

Scenario: A Demonstrated row keeps its status when the score is later lowered
  Given "Quiz 1" appears by name under a rule line reading "AT 80% OR BETTER"
  And the learner scored 18 of 20 points on Quiz 1, so their recorded status on it is Demonstrated
  And a member of course staff has since overridden the learner's score on Quiz 1 to 12 of 20 points, for example in the Gradebook
  When the learner opens the course's Progress tab
  Then Quiz 1's row shows the "Demonstrated" oval reading "60%"

Scenario: Placeholder rows have no oval
  Given a rule line with "Quiz 1" by name and a placeholder row reading "1 more subsection that isn't visible to you"
  And the learner scored 19 of 20 points on the hidden subsection before the author hid it from the course outline, so their recorded status on it is Demonstrated
  When the learner opens the course's Progress tab
  Then Quiz 1's row shows an oval
  And the placeholder row shows no oval, no status, and no score

Scenario: Ovals fill in without changing once shown
  Given a course with competency criteria
  And the learner's network connection is slow
  When the learner opens the course's Progress tab
  Then the cards may appear before the ovals, with no oval on any named row until the learner's statuses load
  And once the statuses load, every named row shows its oval
  And no oval changes after it first appears

Scenario: The cards appear without ovals when the learner's statuses can't be loaded
  Given a course with competency criteria
  And the request for the learner's competency statuses fails, for example because the site's LMS doesn't provide #738's endpoint
  When the learner opens the course's Progress tab
  Then the cards appear as #734 describes, with no oval on any named row, including no "Available" oval
  And no error message is shown to the learner

Scenario Outline: Course staff see the learner's ovals, with the learner's hidden results
  Given the learner scored 19 of 20 points on "Quiz 1", whose results are always shown, and on "Quiz 2", whose results are set never to be shown, so their recorded status on each is Demonstrated
  And the staff member has no recorded status on either subsection
  When <viewer>
  Then Quiz 1's row shows the "Demonstrated" oval reading "95%"
  And Quiz 2's row shows the "Available" oval, with no score

  Examples:
    | viewer                                                                                                 |
    | a member of course staff opens that learner's progress page, for example from the instructor dashboard |
    | a member of course staff views the course's Progress tab as that learner                               |

Scenario: Returning to the Progress tab shows a newly recorded status
  Given the learner opened the course's Progress tab, where "Quiz 1" showed the "Available" oval under a rule line reading "AT 80% OR BETTER"
  And the learner then left the Progress tab, scored 19 of 20 points on Quiz 1, and the platform recorded the grade
  When the learner comes back to the Progress tab
  Then Quiz 1's row shows the "Demonstrated" oval reading "95%"

Scenario: A screen reader user hears each row's status as a word
  Given named rows showing the "Available", "Not Demonstrated", and "Demonstrated" ovals
  When a screen reader user moves through those rows
  Then they hear each subsection's name followed by its status: "Available", "Not Demonstrated", or "Demonstrated" with the score, such as "Demonstrated, 95%"
  And no oval's icon is announced on its own or as an unlabeled image

Scenario: Each oval can be told apart without color
  Given named rows showing the "Available", "Not Demonstrated", and "Demonstrated" ovals
  When the learner views the panel with color removed, for example with the browser's grayscale emulation
  Then each oval is still identifiable by its icon and text alone
  And each oval's text and icon meet WCAG 2.1 AA contrast against the oval's background

Scenario: Ovals stay whole on a small screen
  Given named rows showing each oval, including one for a subsection with a long name
  When the learner opens the course's Progress tab at a phone-sized viewport
  Then every oval shows its full icon and text, with nothing cut off
  And each oval stays with its own subsection's row while the long name wraps onto more lines
```

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done.

**Summary**

The panel makes two more requests through #734's plugin-owned query client: #738's statuses and the Progress API's per-subsection scores. Both start only once #733 returns criteria. A pure function, `buildCompetencyStatuses`, joins them with #733's criteria and the course outline into one display status per named row, applying the hidden-score mask. A hook, `useCompetencyStatuses(courseId, targetUserId)`, exposes that result so #740, #743, and #745 read the same masked statuses, and a new `StatusOval` component renders all four states.

**Approach**

1. **Requests.** Add two functions to `src/data/api.js`:
   - `getCompetencyStatuses(courseId, targetUserId)` calls #738's LMS route and passes `targetUserId` as #738's learner parameter when it is set.
   - `getProgressScores(courseId, targetUserId)` calls `GET {LMS_BASE_URL}/api/course_home/v1/progress/{courseId}`, with `/{targetUserId}` appended on the staff route.

   Both query keys include `targetUserId`. Masquerade needs no key entry, because changing it reloads the page. Enable both queries only when #734's `hasCompetencyCriteria` is true, and run them in parallel with the outline query. That way a course without criteria still costs one request and never calls the expensive Progress API a second time.
2. **Unknown statuses.** `getCompetencyStatuses` logs, once per response, any `status` other than `PartiallyAttempted`, `AttemptedNotDemonstrated`, or `Demonstrated`. It keeps those entries, because an unknown status must render no oval rather than "Available".
3. **Masking.** `buildCompetencyStatuses(criteriaResponse, outline, statusesResponse, progressResponse)` in `src/data/buildCompetencyStatuses.js` returns `{ criteria }`, where `criteria` is a `Map` from criterion `id` to `{ status, percentGraded, masked }`. #740 adds `tags` beside it, so the hook's shape doesn't change when #740 lands. It covers named rows only, so placeholder rows get no oval. A criterion is a named row when its `object_id` is in the outline index that `buildCompetencyCards` builds. Export that index from `src/data/buildCompetencyCards.js` rather than rebuilding it, so the named-row check can't drift from #734's rows. Index `section_scores[].subsections[]` by `block_key`, then apply these rules to each named row:
   - A subsection whose outline `effective_start` is in the future is "Available" with `masked: false`, because an unreleased subsection has no result to hide. The Progress API leaves unreleased subsections out of a learner's `section_scores`, so check this first.
   - Otherwise, if the subsection is missing from that index, or its `show_grades` is false, the result is "Available" with `masked: true`, whatever the stored status.
   - Otherwise the result is the stored status, or "Available" when there is no status row. `percentGraded` is set only on `Demonstrated`. A criterion whose status is unknown is left out of the map.

   The function never compares a score with the rule and never recomputes a status.
4. **Hook.** `useCompetencyStatuses(courseId, targetUserId)` in `src/data/apiHooks.js` composes #734's criteria and outline hooks with the two new queries, and returns `{ isPending, statuses }`.
   - `isPending` is true until #733 answers. When #733 returned criteria, it stays true until the other three requests settle. Derive it from #733's result first, because react-query v5 reports a disabled query as pending indefinitely.
   - `statuses` is null when #738 or the Progress API fails; #734's query cache has already logged the error. Otherwise `statuses` is `buildCompetencyStatuses`'s result, memoized on the four responses' `data`.
   - The hook reads nothing from props or slot context, so #743's sidebar can call it from its own slot and share the cache without new requests.
5. **Join guard.** The join assumes #733's `object_id` string equals the Progress API's `block_key` for the same subsection. Both are `str()` of the usage key, but the equality has not been confirmed on a devstack. If the two never match, every oval reads "Available" with no other symptom. So when `section_scores` lists subsections and no named row matches any `block_key`, the hook logs one error. Confirm the equality on a devstack before merging.
6. **Panel.** `CompetencyProgressPanel` calls the hook with both values from `useProgressRouteParams`. It renders the cards as soon as #734 does, without waiting for the hook, and passes `statuses?.criteria` down to `CriteriaGroupList` as a plain prop. While `isPending` is true or `statuses` is null, the rows render as #734 has them, with no oval, so no row shows a temporary "Available" that later changes.
   - `buildCompetencyCards` carries each named subsection row's criterion `id`, alongside the tag ids #734 already carries. Each named row looks up its own criterion `id`, so a subsection under two tags, or in two groups under one tag, shows each criterion's own status. Joining by `object_id` would give both rows the same status.
   - #839's `useCompetencyPanelState` and its loading rule need no change, because the cards don't wait for #738 or the Progress API.
7. **Oval.** `StatusOval({ status, percentGraded })` in `src/StatusOval.jsx` renders Available, Partially Attempted, Not Demonstrated, and Demonstrated. #740 reuses it on card headings.
   - Icons: #768's icons, which Paragon exports as `RadioButtonUnchecked`, `Contrast`, `RemoveCircle`, and `CheckCircle`.
   - Outlined "Available" oval: Paragon's `Badge` has no outlined variant. If the design's "Available" oval is outlined, override `Badge`'s `--pgn-badge-bg` and add a border locally, and call out the gap in the PR description.
   - Accessibility: when `percentGraded` is passed, the Demonstrated oval shows the percentage as visible text, with "Demonstrated" in an `sr-only` sibling placed before it, so a screen reader reads "Demonstrated, 95%". The icon is `aria-hidden`.
   - Percentage format: copy the Grade Summary table's `getGradePercent` verbatim (`toFixed(0)` when `percentGraded * 100` is a whole number, otherwise `toFixed(2)`), with the same right-to-left mark before "%" in RTL locales, so the oval matches the Progress tab exactly. That includes the host's float quirk: 0.29 shows as "29.00%", because `0.29 * 100` is `28.999999999999996`.
8. **Test cases beyond the AC:**
   - A `PartiallyAttempted` criterion shows the Partially Attempted oval.
   - An unknown status shows no oval and is logged once.
   - When the Progress API fails while #738 succeeds, no ovals appear.
   - When #738 or the Progress API fails, the failure is reported to the logging service.
   - While the statuses are pending, named rows show no oval.
   - A masked criterion whose stored status is unknown shows "Available".
   - `percentGraded` values of 0, 0.29, 0.6667, and 0.825 render as 0%, 29.00%, 66.67%, and 82.50%, the same as the Grade Summary table.

Out of scope:

- Tag statuses and propagating the mask to tags (#740).
- The Focus Areas sidebar (#743).

**Files to create and modify**

Paths are relative to the root of the plugin repository from #810.

| File | Change |
| --- | --- |
| `src/data/api.js` | modified: `getCompetencyStatuses` and `getProgressScores` |
| `src/data/apiHooks.js` | modified: the two new queries and `useCompetencyStatuses` |
| `src/data/buildCompetencyStatuses.js` | new |
| `src/data/buildCompetencyCards.js` | modified: export the outline index, and carry each named row's criterion `id` |
| `src/StatusOval.jsx` | new |
| `src/CompetencyProgressPanel.jsx` | modified |
| `src/CompetencyCard.jsx` | modified: passes `statuses` to `CriteriaGroupList` |
| `src/CriteriaGroupList.jsx` | modified: an oval on each named row |
| `src/messages.js` | modified |

**Additional context**

- Known limitations:
  - A Demonstrated oval can show a current percentage below its own rule line, because #699 never lowers a stored status.
  - A subsection set to never show individual assessment results (`never_but_include_grade`) never shows its status, which matches the Progress page itself.
  - On the staff route, subsections the learner can't see appear by name and read "Available".
  - The masking changes only the display, so #738's response still carries a hidden subsection's status.
- In frontend-app-learning, `GradeSummaryTable.jsx` (`getGradePercent`) and `DetailedGradesTable.jsx` under `src/course-home/progress-tab/grades/` show the host's percentage format and its `show_grades` hiding. The course tabs in `src/course-tabs/CourseTabLink.tsx` are plain links, so every visit to the Progress tab starts with an empty query cache.
- In openedx-platform, `lms/djangoapps/course_home_api/progress/views.py` computes `show_grades` with the learner's staff access rather than the viewer's, and leaves `never_but_include_grade` subsections out of `section_scores`. `lms/djangoapps/course_blocks/transformers/start_date.py` (`StartDateTransformer`) removes unreleased subsections from a learner's grade structure, while the learning_sequences outline keeps them by name.

</details>

## Open Questions

- (implementer) Should the two new queries keep the client's default retries on a 5xx response? The named rows show no oval through the retries, about 7 seconds, before the panel gives up on the ovals.
