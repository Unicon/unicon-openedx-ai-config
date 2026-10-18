# [FE] Build Display of Recommended Next Action

GitHub: https://github.com/openedx/openedx-core/issues/755 (#755, OPEN)
Cached: 2026-09-21

## User Story
As a learner, I want to know what my recommended next action is in my CBE course in order to maintain momentum in learning and skill demonstration without having to figure this out myself or have someone tell me.

## Description
This ticket implements the Recommended Next Action notice inside the right hand CBE progress panel from #743, which goes in the ProgressTabRelatedLinksSlot.

This implementation will call the endpoint built in #754. If the `reason` listed in that endpoint's response is:
- `continue_available`, then the first word in the sentence should be "Continue", and the button should say "Continue assignment"
- `retry_available`, then the first word should be "Retake", and the button should say "Retake assignment"
- `not_started`, then the first word should be "Take", and the button should say "Take assignment"
- Anything else, then show a "Resume course" button instead of the sentence, using the `resume_url` that #754 returns.

Next in the sentence should be the name of the subsection, in bold. The button below the sentence opens the subsection (the `url` that #754 returns).

Then the sentence should say "and score <threshold>", where the threshold reads the same way as the rule lines on the competency cards: "80% or better", "40% or lower", or "exactly 100%". If the subsection's criteria have different thresholds that can't be combined into one, this part is left out.

The sentence ends with "to demonstrate <competency>", listing each competency in the response's criteria once (for example "Writing Poetry and Analysis").

Therefore, the sentence displayed in the "Recommended Next Action" notice will say: "Continue/Take/Retake <Subsection Name> and score <threshold> to demonstrate <competency>."

## Context
- Corresponding architecture spike: #757
- Frontend counterpart to #754
- Blocked by #743

## UX Design

@illiphilli, please add the UX design screenshot(s) and the Figma link for this ticket.

- Figma: TBD
- Screenshots: TBD

## Acceptance Criteria

These scenarios use the following terms:

- The notice is the "Recommended Next Action" notice in the right-hand CBE progress panel from #743. Its card styling, heading icon, and button follow the UX design.
- The recommendation is what #754 returns for the learner whose progress is shown. It names a subsection to continue, take, or retake, and the competencies on that subsection the learner still has to demonstrate, each with the score its criterion requires.
- A recommendation to continue is for a subsection the learner has started but hasn't finished their own part of. A recommendation to retake is for a subsection the learner has attempted without demonstrating its competency and can submit to again. A recommendation to take is for a subsection the learner hasn't started.
- Subsection and competency names appear as they are stored in the course and aren't translated.

```gherkin
Scenario Outline: The recommendation reads as one sentence that starts with Continue, Take, or Retake, followed by a matching button
  Given the learner's recommendation is to <action> "Poetry Assignment 1", to demonstrate "Writing Poetry", whose criterion on it requires 80% or better
  When the learner opens the course's Progress tab
  Then the notice appears in the right-hand CBE progress panel, headed "Recommended Next Action"
  And the notice reads "<verb> Poetry Assignment 1 and score 80% or better to demonstrate Writing Poetry."
  And below the sentence is a button labeled "<button>"

  Examples:
    | action   | verb     | button              |
    | continue | Continue | Continue assignment |
    | retake   | Retake   | Retake assignment   |
    | take     | Take     | Take assignment     |

Scenario: The button opens the recommended subsection
  Given the learner's recommendation is to retake "Poetry Assignment 1"
  When the learner selects the notice's "Retake assignment" button
  Then "Poetry Assignment 1" opens in the courseware, in the same browser tab

Scenario Outline: The score uses the same wording as the competency cards' rule lines
  Given the learner's recommendation is to take "Quiz 3", to demonstrate "Analysis", whose criterion on it requires a score <comparison> <threshold>%
  When the learner opens the course's Progress tab
  Then the notice reads "Take Quiz 3 and score <score> to demonstrate Analysis."

  Examples:
    | comparison       | threshold | score           |
    | at or above      | 82        | 82% or better   |
    | at or above      | 29        | 29% or better   |
    | at or above      | 82.5      | 82.5% or better |
    | at or below      | 40        | 40% or lower    |
    | exactly equal to | 100       | exactly 100%    |

Scenario Outline: Criteria that compare the same way show the one score that satisfies all of them
  Given the learner's recommendation is to retake "Final Project", to demonstrate "Writing Poetry" and "Analysis"
  And the criterion for "Writing Poetry" requires <first> and the criterion for "Analysis" requires <second>
  When the learner opens the course's Progress tab
  Then the notice reads "Retake Final Project and score <score> to demonstrate Writing Poetry and Analysis."

  Examples:
    | first         | second        | score         |
    | 75% or better | 80% or better | 80% or better |
    | 40% or lower  | 30% or lower  | 30% or lower  |
    | exactly 100%  | exactly 100%  | exactly 100%  |

Scenario Outline: The score is left out when the criteria compare in different ways or require different exact scores
  Given the learner's recommendation is to retake "Final Project", to demonstrate "Writing Poetry" and "Analysis"
  And the criterion for "Writing Poetry" requires <first> and the criterion for "Analysis" requires <second>
  When the learner opens the course's Progress tab
  Then the notice reads "Retake Final Project to demonstrate Writing Poetry and Analysis."

  Examples:
    | first         | second        |
    | 80% or better | 40% or lower  |
    | exactly 100%  | 80% or better |
    | exactly 90%   | exactly 100%  |

Scenario: The score is left out when a criterion's rule isn't recognized
  Given the learner's recommendation is to take "Lab 2", to demonstrate "Analysis" and "Lab Safety"
  And the criterion for "Analysis" requires 80% or better, and the criterion for "Lab Safety" uses a rule the plugin doesn't recognize
  When the learner opens the course's Progress tab
  Then the notice reads "Take Lab 2 to demonstrate Analysis and Lab Safety."
  And the unrecognized rule is reported to the site's logging service

Scenario Outline: Every competency the subsection counts toward is named, as a list, in the order the server returns them
  Given the learner's recommendation is to retake "Poetry Assignment 1", to demonstrate <competencies>, in that order, each requiring 80% or better
  When the learner opens the course's Progress tab
  Then the notice reads "Retake Poetry Assignment 1 and score 80% or better to demonstrate <list>."

  Examples:
    | competencies                                 | list                                   |
    | "Writing Poetry" and "Analysis"              | Writing Poetry and Analysis            |
    | "Writing Poetry", "Analysis", and "Critique" | Writing Poetry, Analysis, and Critique |

Scenario Outline: A competency name that appears in more than one criterion on the subsection is named once, and its score shows only when every one of those criteria requires the same score
  Given the learner's recommendation is to retake "Poetry Assignment 1"
  And the subsection has <criteria>
  When the learner opens the course's Progress tab
  Then the notice reads "<sentence>"

  Examples:
    | criteria                                                                                                              | sentence                                                                          |
    | two criteria for "Writing Poetry", both requiring 80% or better                                                       | Retake Poetry Assignment 1 and score 80% or better to demonstrate Writing Poetry. |
    | two criteria for "Writing Poetry", one requiring 75% or better and one requiring 80% or better                        | Retake Poetry Assignment 1 to demonstrate Writing Poetry.                         |
    | criteria for two different competencies that are both named "Writing Poetry", both requiring 80% or better            | Retake Poetry Assignment 1 and score 80% or better to demonstrate Writing Poetry. |
    | criteria for two different competencies that are both named "Writing Poetry", one requiring 75% or better and one 80% | Retake Poetry Assignment 1 to demonstrate Writing Poetry.                         |

Scenario Outline: A button to resume the course appears when there is no recommendation
  Given a course with competency criteria
  And the learner has no recommendation, because <situation>
  When the learner opens the course's Progress tab
  Then the notice shows a "Resume course" button in place of a recommendation sentence
  And selecting the button opens the course where the learner left off, the same place the course home's "Resume course" button opens

  Examples:
    | situation                                                                                                                                                                    |
    | the learner has demonstrated every competency this course's criteria count toward                                                                  |
    | no subsection the learner still has a competency to demonstrate on can be opened now, for example because none is released yet                    |
    | each subsection the learner still has a competency to demonstrate on is awaiting grading or has no attempts left                                  |
    | each subsection the learner still has a competency to demonstrate on is past the learner's due date                                                |
    | the only subsection the learner could retake is one whose result is hidden from the learner                                                         |

Scenario: Nothing appears when there is neither a recommendation nor a place to resume
  Given a course with competency criteria
  And the server returns no recommendation and no place to resume the course for the learner
  When the learner opens the course's Progress tab
  Then the notice doesn't appear
  And the rest of the right-hand CBE progress panel appears as usual

Scenario: Nothing from the notice appears while the recommendation is loading
  Given a course with competency criteria
  And the learner's recommendation is still loading
  When the learner opens the course's Progress tab
  Then no notice, heading, loading indicator, or placeholder from the notice appears
  And the rest of the right-hand CBE progress panel and the Progress tab appear without waiting for the recommendation

Scenario: The notice stays hidden when the recommendation can't be loaded
  Given the request for the learner's recommendation fails, for example because the site hasn't deployed #754's endpoint, the server returns an error, or the request is refused
  When the learner opens the course's Progress tab
  Then nothing from the notice appears, and no error message is shown to the learner
  And the failure is reported to the site's logging service
  And the rest of the right-hand CBE progress panel appears as usual

Scenario: A failure while displaying the notice doesn't hide the rest of the panel
  Given the learner's recommendation loads, but displaying the notice fails, for example because the recommendation is malformed
  When the learner opens the course's Progress tab
  Then nothing from the notice appears
  And the rest of the right-hand CBE progress panel appears as usual
  And the failure is reported to the site's logging service

Scenario: Course staff viewing a learner's progress see that learner's recommendation
  Given learner A's recommendation is to retake "Poetry Assignment 1", to demonstrate "Writing Poetry", whose criterion on it requires 80% or better
  When a member of course staff opens learner A's progress page, for example from the instructor dashboard
  Then the notice reads "Retake Poetry Assignment 1 and score 80% or better to demonstrate Writing Poetry."

Scenario: Course staff moving between learners see each learner's own recommendation
  Given learner A's recommendation is to retake "Poetry Assignment 1", and learner B's is to take "Quiz 2", to demonstrate "Analysis", whose criterion on it requires 70% or better
  And a member of course staff has opened learner A's progress page
  When the staff member opens learner B's progress page in the same browser session
  Then the notice reads "Take Quiz 2 and score 70% or better to demonstrate Analysis."
  And "Poetry Assignment 1" doesn't appear in the notice

Scenario: Course staff viewing a learner with no recommendation can open the course where that learner left off
  Given learner A has no recommendation, and learner A last worked in "Unit 3"
  And a member of course staff last worked somewhere in the course other than "Unit 3"
  When the staff member opens learner A's progress page
  Then selecting the notice's "Resume course" button opens "Unit 3"

Scenario: Course staff viewing the course as a specific learner see what the server returns for that session
  Given a member of course staff is viewing the course as learner A
  And the server returns the recommendation to retake "Poetry Assignment 1", to demonstrate "Writing Poetry", whose criterion on it requires 80% or better, for that session
  When the staff member opens the course's Progress tab
  Then the notice reads "Retake Poetry Assignment 1 and score 80% or better to demonstrate Writing Poetry."
  And the request for the recommendation names no learner

Scenario: The notice shows the current recommendation after the learner returns from a subsection
  Given the learner opened the course's Progress tab, and the notice read "Take Quiz 1 and score 80% or better to demonstrate Analysis."
  And the learner selected the notice's button, submitted "Quiz 1", and the server now recommends taking "Quiz 2"
  When the learner selects the course's Progress tab again
  Then the notice shows the recommendation for "Quiz 2"
  And "Quiz 1" doesn't appear in the notice

Scenario: The notice shows the current recommendation after the learner uses the browser's Back button
  Given the learner opened the course's Progress tab, and the notice read "Take Quiz 1 and score 80% or better to demonstrate Analysis."
  And the learner selected the notice's button, submitted "Quiz 1", and the server now recommends taking "Quiz 2"
  When the learner uses the browser's Back button to return to the Progress tab
  Then the notice shows the recommendation for "Quiz 2"
  And "Quiz 1" doesn't appear in the notice

Scenario: Each form of the sentence is translated as a whole
  Given the learner's language is one whose translations put the subsection, the score, and the competencies in a different order than English
  When the learner opens the course's Progress tab
  Then whichever form of the notice applies (Continue, Take, or Retake, with or without a score, or the "Resume course" button) appears in the translation's word order
  And the button's label is translated
  And the score is written the way that language writes percentages
  And the competency names are joined the way that language writes a list

Scenario: A screen reader user hears the notice as one sentence
  Given the learner's recommendation is to retake "Poetry Assignment 1"
  When a screen reader user moves through the right-hand CBE progress panel
  Then they hear the notice's heading, followed by the whole sentence in reading order
  And the button is announced with its label after the sentence, and can be reached and selected with the keyboard alone

Scenario: A keyboard and screen reader user can use the "Resume course" button
  Given the learner has no recommendation and the notice shows the "Resume course" button
  When the learner moves through the right-hand CBE progress panel with the keyboard and a screen reader
  Then the button can be reached and selected with the keyboard alone
  And the button is announced with its label

Scenario: The notice reflows on a small screen
  Given the learner's recommendation is for a subsection with a long name, to demonstrate three competencies with long names
  When the learner opens the course's Progress tab at a phone-sized viewport
  Then the notice's sentence wraps onto more lines instead of being cut off
  And the page doesn't scroll horizontally
```

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done.

**Summary**

`RecommendedNextAction` is a self-contained component that #743's Course Progress card renders. It fetches #754's response through the plugin's own react-query client, keyed by course and target learner, and builds one whole translated sentence from it, followed by a button to the subsection: a verb chosen by `reason`, the subsection's name, an optional score that satisfies every listed criterion, and the competency names as a locale-aware list. The cached response is removed whenever the notice unmounts, so returning to the Progress tab always fetches the current recommendation, and a local error boundary keeps a crash in the notice from hiding the rest of the panel.

**Approach**

1. **Request.** Add `getRecommendedNextAction(courseId, targetUserId)` to `src/data/api.js`. It calls #754's route, `api/cbe_learner/v1/next-action/{course_key}`, through `getAuthenticatedHttpClient()`. The optional learner id is a path segment, `/{student_id}`, only when `targetUserId` is set. The final path follows the app name that #754 settles on. Add `useRecommendedNextAction()` to `src/data/apiHooks.js`. It reads `{ courseId, targetUserId }` from `useProgressRouteParams()`, uses the query key `['recommendedNextAction', courseId, targetUserId ?? null]`, and passes #734's plugin query client as `useQuery`'s second argument, so that client's `QueryCache.onError` logs a failed request and a 4xx isn't retried. Leave `placeholderData` unset, so staff switching learners see nothing until the new learner's response arrives.
2. **Freshness.** Set `gcTime: 0` on this query, so its cache entry is removed as soon as the notice unmounts. The notice's buttons are plain links, so following one is a full page navigation away from the Progress tab, so on return the plugin and its query client usually start fresh. `gcTime: 0` covers in-app remounts, for example staff switching learners or a remount inside the app, which trigger a new request and show nothing until it lands, rather than the previous recommendation followed by a swap. Also call `queryClient.resetQueries` for this key on a `pageshow` event whose `persisted` is true, because the browser's Back button can restore the Progress tab from the back-forward cache without remounting anything. The `pageshow` listener lives in a `useEffect` inside the inner component from step 7 and is removed on unmount.
3. **What renders.** #743 mounts the right-hand panel only in a course with competency criteria, so this component adds no criteria check of its own. It renders:
   - the sentence and its button, when `reason` is `continue_available`, `retry_available`, or `not_started` and `next_action` is present;
   - otherwise, the "Resume course" button, when `resume_url` is non-null, for any other `reason`, including one #754 adds later;
   - otherwise, nothing: while loading, after a failed request, for `no_criteria_in_course` (which #743's panel normally prevents), or when `resume_url` is null.

   The component renders nothing when there is no data. The plugin client's `QueryCache.onError` logs a failed request, so the component doesn't branch on `isError`. If a background refetch fails while cached data exists, the cached data keeps rendering.
4. **Threshold.** Add `combineThreshold(criteria)` to `src/ruleText.js`, reusing the recognition that #734's `formatRuleText` already does (rule type `Grade`, `op` of `gte`, `lte`, or `eq`, `scale` of `percent`), so the notice and the rule lines recognize the same rules. `rule_payload.value` is a fraction from 0.0 to 1.0, and `combineThreshold` receives every entry in `criteria[]`. It returns `{ op, value }` or null:
   - when every criterion is `gte`, the highest value;
   - when every criterion is `lte`, the lowest value;
   - when every criterion is `eq` with the same value, that value;
   - when two criteria share a `competency_name` but differ in `op` or value, null, because the notice is naming that competency once and can't tell which group's score the learner needs;
   - when the ops are mixed, the `eq` values differ, or any rule is unrecognized, null, which drops the "and score" clause. An unrecognized rule is logged once per response, as #734's transform does.

   Format the value with `intl.formatNumber(value, { style: 'percent', maximumFractionDigits: 2 })`, as #734 does.
5. **Competency names.** Take `competency_name` from `criteria[]` in server order, keeping only the first occurrence of each name, so a competency with two criteria on the subsection, or two competencies that share a name, are named once. Join the names with `intl.formatList(names, { type: 'conjunction' })`.
6. **Messages.** Add to `src/messages.js` one whole-sentence message per verb and threshold form, twelve in all: Continue, Take, and Retake, each with "{percent} or better", "{percent} or lower", "exactly {percent}", and no score. Add the button labels ("Continue assignment", "Take assignment", "Retake assignment", and "Resume course") and the heading as well. Render the heading as an `h3`, unless #743's card defines its heading levels, in which case use the level below the card's title. The notice container follows the UX design and defaults to plain markup inside #743's card. The message values are `subsection` (`subsection.display_name` in bold, not a link), `percent`, and `competencies`. Select the message with a lookup keyed by verb and op. Below the sentence, render a Paragon `Button` with `href` set to `next_action.url`, which renders a link styled as a button that opens in the same tab; the "Resume course" button uses `resume_url` the same way. The heading is title case with an arrow icon, and the card's colors and border follow the UX design. Check Paragon's `Card` and `Alert` before writing custom CSS for the card.
7. **Error boundary.** Split the component in two. The outer `RecommendedNextAction` renders `ErrorBoundary` from `@edx/frontend-platform/react`, as #839 does, around the inner `RecommendedNextActionContent`, which calls `useRecommendedNextAction()` and renders. A hook can't be wrapped by a boundary inside the same component. That boundary logs the error through `logError`. Pass an empty fragment as `fallbackComponent`, because a falsy fallback makes the boundary render its full-page error, and `SilentErrorFallback` would log the error a second time. A `next_action` with an empty `criteria[]` is malformed but doesn't throw on its own, so throw for it explicitly, and the boundary hides the notice and logs it.

The tests must cover these edge cases:

- each case of the threshold rule in step 4;
- a competency with two criteria on the subsection, and two competencies sharing a name, each named once, with and without matching scores;
- each of the three verbs and its button label;
- `no_criteria_in_course` rendering nothing;
- competency names kept in server order;
- switching `targetUserId` never showing the previous learner's sentence;
- a remount fetching again and showing nothing until the response lands;
- a `reason` other than the three recommendation reasons, both with and without `resume_url`;
- an empty `criteria[]`;
- the error boundary hiding the notice when rendering throws;
- the `pageshow` reset when `persisted` is true;
- one translated word order that differs from English.

Out of scope:

- a click-tracking event on the button;
- polling for a newer recommendation: a Progress tab left open in another browser tab shows its recommendation until it is reloaded;
- linking the notice to the competency cards through `criterion_id` or `tag_id`.

**Files to create and modify**

Paths are relative to the root of the plugin repository from #810.

| File | Change |
| --- | --- |
| `src/RecommendedNextAction.jsx` | new: the outer `RecommendedNextAction` with the error boundary, and the inner `RecommendedNextActionContent` with the sentence and buttons |
| `src/ruleText.js` | modified: add `combineThreshold` |
| `src/messages.js` | modified: add the sentence, button label, and heading messages |
| `src/data/api.js` | modified: add `getRecommendedNextAction` |
| `src/data/apiHooks.js` | modified: add `useRecommendedNextAction` |
| The Course Progress card component from #743 | modified: render `RecommendedNextAction` |

**Additional context**

- #743 must mount the right-hand panel only in a course with competency criteria, because every mount calls #754, an expensive endpoint, and its Course Progress card renders this notice.
- #754 never recommends retaking a subsection whose score is hidden from the learner, so the notice renders #754's response without #739's score masking.
- Group and competency statuses roll up asynchronously (openedx-core ADR 0004, `docs/openedx_learning/decisions/0004-competency-mastery-concurrency.rst`). Right after a learner demonstrates one subsection in an OR group, #754 can briefly still recommend an untouched sibling. #754 accepts this lag, and the notice shows whatever #754 returns.
- In `@edx/frontend-platform`, `src/react/ErrorBoundary.jsx` shows the logging and fallback behavior that step 7 relies on.

</details>
