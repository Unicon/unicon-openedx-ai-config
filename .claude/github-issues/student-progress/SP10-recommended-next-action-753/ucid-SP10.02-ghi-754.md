# [BE] GET Recommended Next Action for CBE Learner in Course

GitHub: https://github.com/openedx/openedx-core/issues/754 (#754, OPEN)
Cached: 2026-09-21

## User Story
As a learner, I want to know what my recommended next action is in my CBE course in order to maintain momentum in learning and skill demonstration without having to figure this out myself or have someone tell me.

## Description
This ticket implements the design proposed in #757. It is a learner-facing endpoint that takes in the course and the learner and returns the recommended next action for that learner.

This is the algorithm that will be used to calculate the Recommended Next Action:
1. Given a course and a learner.
2. Find every subsection in the course that carries a competency criterion.
3. Remove from that set:
   - Any subsection the learner can't currently open or act on right now: unreleased, prerequisite-gated, past its due date, graded content locked for the learner's enrollment track, or otherwise unavailable.
   - Any criterion whose ancestor group (at any level), or whose competency, already reports "Demonstrated" for this learner, even when that specific criterion has no status row of its own. This is what keeps an already-satisfied OR group (for example, the duplicate-subsection workaround, once one duplicate is demonstrated) from still recommending its untouched siblings. A competency demonstrated in another course counts.
4. Split what's left into two groups:
   - **Retry candidates:** the learner's status on this subsection's criterion isn't "Demonstrated," the subsection's re-attempt state is retryable, and no resubmission is already awaiting grading. A subsection whose re-attempt state is unknown or not retryable is not a retry candidate, but it doesn't fall into "not-started" either, since it does have a status row; it simply isn't recommended.
   - **Not-started candidates:** the learner has no status row on this subsection's criterion, and no submission or attempt has been recorded against it yet. This keeps a subsection whose submission is still awaiting grading from being mistaken for one the learner hasn't touched at all.
5. If any retry candidates exist, recommend the one that comes chronologically first in the course outline (section order, then subsection order). Otherwise, if any not-started candidates exist, recommend the one that comes chronologically first in the course outline. Otherwise, there's no recommendation.
6. Return, for the selected subsection: its display name, a ready-to-use navigation URL, and, for each of its criteria that is not "Demonstrated" and not removed in step 3, the criterion id, competency tag id, competency name, status (null when the learner has no status row), and rule.

The response payload will be something to the effect of this:
```json
{
  "next_action": {
    "course_id": "course-v1:Org+Course+Run",
    "url": "https://<learning-mfe>/course/<course_id>/<subsection_id>",
    "subsection": {
      "id": "block-v1:Org+Course+Run+type@sequential+block@abc123",
      "display_name": "Poetry Assignment 1"
    },
    "criteria": [
      {
        "criterion_id": 91,
        "tag_id": 41,
        "competency_name": "Writing Poetry",
        "status": "AttemptedNotDemonstrated",
        "rule": {
          "rule_type": "Grade",
          "rule_payload": { "op": "gte", "value": 0.75, "scale": "percent" }
        }
      }
    ]
  },
  "reason": "retry_available"
}
```

## Context
- Corresponding architecture spike: #757
- Frontend counterpart: #755
- Blocked by: UCID10.05 #TBD

## Acceptance Criteria

Every scenario below shares this setup, unless the scenario says otherwise:

- A learner has an active enrollment in course run X, and every subsection named carries a competency criterion.
- A criterion is remaining for a learner when the learner hasn't demonstrated it and no group or competency above it reports Demonstrated for that learner.
- Every subsection named is released, open to the learner, before the learner's due date for it, shows results to learners, and accepts a submission from the learner now.
- Every scenario is observed through the recommended next action endpoint.

Group and competency statuses roll up asynchronously (openedx-core ADR 0004). For a short time after a learner demonstrates one subsection in an OR group, an untouched sibling in that group can still be recommended. The scenarios assume the roll-up has finished.

**Choosing what to recommend**

```gherkin
Scenario: A retake is recommended ahead of an earlier subsection the learner hasn't started, listing only what is left to demonstrate there
  Given subsection "Poetry Assignment 1", in section 1, is one the learner hasn't started
  And subsection "Poetry Assignment 2", in section 2, carries criteria for "Writing Poetry" (a grade of at least 80 percent), "Analysis" (at least 60 percent), and "Research" (at least 90 percent)
  And the learner scored 70 percent on "Poetry Assignment 2", demonstrating "Analysis" there but not "Writing Poetry" or "Research"
  And the learner demonstrated the "Research" competency in course run Y
  When the learner requests their recommended next action in course run X
  Then "Poetry Assignment 2" is recommended as a retake
  And the result names "Poetry Assignment 2" and links to it in the courseware
  And the recommendation lists only "Writing Poetry", with its competency name, the learner's status of attempted but not demonstrated, and the rule of a grade of at least 80 percent

Scenario Outline: The candidate earliest in the course outline is recommended, whatever the due dates
  Given course run X has three <candidates>: the second subsection of section 1, the third subsection of section 1, and the first subsection of section 2
  And the first subsection of section 2 has the earliest due date of the three, and the third subsection of section 1 has the latest
  And no other subsection in course run X is a candidate of any kind
  When the learner requests their recommended next action in course run X
  Then the second subsection of section 1 is recommended as <recommendation>

  Examples:
    | candidates                                                               | recommendation |
    | subsections the learner attempted without demonstrating their competency | a retake       |
    | subsections the learner hasn't started                                   | a new attempt  |

Scenario: A new attempt lists every criterion on the subsection, none with a status
  Given the learner hasn't attempted anything in course run X
  And subsection "Poetry Assignment 1" comes first in course run X's outline and carries criteria for "Writing Poetry" and "Analysis"
  When the learner requests their recommended next action in course run X
  Then "Poetry Assignment 1" is recommended as a new attempt
  And the recommendation lists "Writing Poetry" and "Analysis", each with its competency name and rule, and neither with a status for the learner
```

**Criteria already satisfied through a group or competency**

```gherkin
Scenario Outline: A subsection whose criteria are already satisfied higher up is not recommended
  Given subsection D1 comes first in course run X's outline, carries a criterion for "Writing Poetry", and is one the learner hasn't started
  And subsection E, later in the outline, carries a criterion for "Analysis" and is one the learner hasn't started
  And <satisfied>
  When the learner requests their recommended next action in course run X
  Then E is recommended, and D1 is not

  Examples:
    | satisfied                                                                                                                       |
    | D1's criterion shares an OR group with subsection D2's criterion, and the learner demonstrated D2                               |
    | "Writing Poetry"'s course-level group for course run X is an OR group, and the learner demonstrated its other bottom-tier group |
    | the learner demonstrated the "Writing Poetry" competency in course run Y                                                        |
```

**Subsections the learner can't act on now**

```gherkin
Scenario Outline: A subsection the learner can't open is never recommended
  Given subsection U comes first in course run X's outline, the learner hasn't started it, and it <state>
  And subsection V, later in the outline, is one the learner hasn't started
  When the learner requests their recommended next action in course run X
  Then V is recommended, and U is not

  Examples:
    | state                                                            |
    | hasn't been released yet                                         |
    | is locked behind a prerequisite the learner hasn't met           |
    | is hidden from learners                                          |
    | is restricted to a content group the learner isn't in            |
    | has been deleted from the course since its criterion was created |

Scenario Outline: A subsection that won't take a submission from the learner now is never recommended
  Given subsection U comes first in course run X's outline, and <state>
  And subsection V, later in the outline, is one the learner hasn't started
  When the learner requests their recommended next action in course run X
  Then V is recommended, and U is not

  Examples:
    | state                                                                                                                                                                              |
    | the learner hasn't started U, and the learner's due date for U has passed                                                                                                          |
    | the learner hasn't started U, the learner is in the audit track, and U's graded content is locked for audit learners                                                               |
    | the learner hasn't started U, U's graded content is an external tool whose submission rules can't be checked, and the learner's due date for U has passed                         |
    | the learner hasn't started U, and U holds no scored content worth points that the learner can see                                                                                  |
    | the learner has no status on U, and checking whether U's graded content accepts a submission from the learner fails                                                                |
    | the learner submitted U and the submission is awaiting grading, so the learner has no status on U yet                                                                              |
    | the learner submitted U, an open response assessment, and U is waiting on the learner's own peer assessment step, so the learner has no status on U yet                           |
    | the learner attempted U without demonstrating its competency and has used all of U's attempts                                                                                      |
    | the learner attempted U without demonstrating its competency, U is an open response assessment staff reset for the learner, and the learner's new submission is awaiting grading |
    | the learner attempted U without demonstrating its competency, and U's graded content is an external tool whose retake rules can't be checked                                     |

Scenario Outline: A subsection the learner hasn't started is recommended even when its graded content can't be checked
  Given subsection L comes first in course run X's outline, and its graded content is <content>
  And the learner hasn't started L, and the learner's due date for L hasn't passed
  When the learner requests their recommended next action in course run X
  Then L is recommended as a new attempt

  Examples:
    | content                                                  |
    | an external tool whose submission rules can't be checked |
    | a timed exam run by the separate exams service           |

Scenario: A retake is recommended when one part of the subsection is awaiting grading and another still accepts a submission
  Given the learner attempted subsection M without demonstrating its competency
  And M holds an open response assessment whose submission from the learner is awaiting grading, and a problem that still accepts answers from the learner
  When the learner requests their recommended next action in course run X
  Then M is recommended as a retake
```

**Scores hidden from the learner**

```gherkin
Scenario Outline: A retake whose score is hidden from the learner is skipped
  Given subsection H comes first in course run X's outline, and the learner attempted it without demonstrating its competency
  And H is set never to show results to learners
  And <rest of the course>
  When the learner requests their recommended next action in course run X
  Then H is not recommended, and <outcome>

  Examples:
    | rest of the course                                                                                          | outcome                                                                                                  |
    | a later subsection K is one the learner attempted without demonstrating its competency, and K shows results | K is recommended as a retake                                                                             |
    | a later subsection N is one the learner hasn't started, and no other subsection is a retake candidate       | N is recommended as a new attempt                                                                        |
    | H holds the learner's only remaining criterion                                                              | no subsection is recommended, and the result gives the reason that nothing remaining can be acted on now |
```

**When there is nothing to recommend**

```gherkin
Scenario Outline: With nothing to recommend, the result says why and offers a link to resume the course
  Given course run X has competency criteria, and <situation>
  And the content the learner last completed in course run X is in subsection "Reading 3"
  When the learner requests their recommended next action in course run X
  Then no subsection is recommended
  And the result gives the reason that <reason>
  And the result includes a link that resumes the course at the content the learner last completed in "Reading 3"

  Examples:
    | situation                                                                                                                                                  | reason                                         |
    | every criterion is demonstrated by the learner or satisfied by a group or competency the learner demonstrated, including one demonstrated in course run Y | everything in the course has been demonstrated |
    | every remaining criterion is on a subsection that hasn't been released yet                                                                                 | nothing remaining can be opened yet            |
    | every remaining criterion is on a subsection whose submission from the learner is awaiting grading                                                        | nothing remaining can be acted on now          |
    | every remaining criterion is on a subsection the learner hasn't started and whose due date for the learner has passed                                     | nothing remaining can be acted on now          |
    | every remaining criterion is on a subsection the learner hasn't started, whose graded content is locked for the audit track the learner is enrolled in | nothing remaining can be acted on now          |
    | one remaining criterion is on a subsection that hasn't been released yet, and the other is on a subsection whose submission is awaiting grading            | nothing remaining can be acted on now          |

Scenario: The resume link starts a learner with no progress at the beginning of the course
  Given every criterion in course run X is on a subsection that hasn't been released yet
  And the learner has completed nothing in course run X
  When the learner requests their recommended next action in course run X
  Then no subsection is recommended
  And the result includes a link that opens the first content in course run X available to the learner

Scenario Outline: A course run with no competency criteria gives no recommendation and no resume link
  Given <course run>
  When the learner requests their recommended next action in course run X
  Then no subsection is recommended
  And the result gives the reason that the course has no competency criteria
  And the result includes no resume link

  Examples:
    | course run                                                                 |
    | course run X has never had competency criteria                             |
    | every criterion in course run X has been archived through #674             |
    | the only competency taxonomy course run X's criteria belong to is disabled |
```

**Who can ask, and whose recommendation they get**

```gherkin
Scenario Outline: Each permitted caller gets the recommendation for the right learner
  Given learner L has an active enrollment in course run X, and S is a member of course run X's staff
  And the recommendation computed for L differs from the one computed for S
  When <caller> requests a recommended next action in course run X <naming>
  Then the result is the recommendation computed for <whom>
  And the result contains no username, user id, or email address
  And the result always says whether there is a recommendation, gives the reason, and says whether there is a resume link

  Examples:
    | caller                                                       | naming                   | whom |
    | L                                                            | without naming a learner | L    |
    | S                                                            | naming L                 | L    |
    | S, while masquerading as L                                   | without naming a learner | L    |
    | S, while masquerading as the learner role or a content group | without naming a learner | S    |
    | S, while masquerading as L after L has unenrolled            | without naming a learner | S    |

Scenario Outline: A caller who isn't permitted is refused and learns nothing
  When <caller> requests a recommended next action in course run X <naming>
  Then <response>
  And the response contains no recommendation, reason, or resume link

  Examples:
    | caller                                                                             | naming                          | response                                                                                      |
    | a caller who isn't signed in                                                       | without naming a learner        | the caller is asked to sign in                                                                |
    | a signed-in user with no active enrollment in course run X and no staff role there | without naming a learner        | the response is the same as the one given for a request naming a user who doesn't exist       |
    | a user who enrolled in course run X and later unenrolled                           | without naming a learner        | the response is the same as the one given for a request naming a user who doesn't exist       |
    | a member of course run X's staff                                                   | naming a user who doesn't exist | the response is the one given to any signed-in caller who isn't permitted                     |

Scenario: A learner who names another learner can't tell whether that learner exists
  Given learners L and M both have active enrollments in course run X
  When M requests L's recommended next action in course run X
  And M requests the recommended next action of a user who doesn't exist
  Then both requests receive the same response as a signed-in caller gets for a user who doesn't exist
  And neither response says whether the named user exists
  And neither response contains any part of L's recommendation

Scenario Outline: A staff member viewing a learner sees the recommendation as it applies to that learner
  Given S is a member of course run X's staff who has never attempted anything in course run X
  And learner L has an active enrollment in course run X
  And subsection U comes first in course run X's outline, where <difference>
  And subsection V, later in the outline, is one neither S nor L has started
  When S requests L's recommended next action in course run X
  Then <recommended> is recommended

  Examples:
    | difference                                                                                         | recommended |
    | U hasn't been released yet, though S can open unreleased content                                   | V           |
    | L is in the audit track, and U's graded content is locked for audit learners                       | V           |
    | L attempted U without demonstrating its competency and has used all of U's attempts                | V           |
    | L attempted U without demonstrating its competency, and U is set never to show results to learners | V           |
    | U's original due date has passed, and L has an extension on U to a date that hasn't passed         | U           |

Scenario: A staff member viewing a learner gets the learner's resume link
  Given learner L has nothing to recommend in course run X, and the content L last completed is in subsection "Reading 3"
  And the content staff member S last completed in course run X is in subsection "Reading 1"
  When S requests L's recommended next action in course run X
  Then the result includes a link that resumes the course at the content L last completed in "Reading 3"
```

**Course run key**

```gherkin
Scenario: A malformed course run key is rejected
  Given a signed-in learner
  When the learner requests a recommended next action for a value that isn't a well-formed course run key
  Then the request is rejected with a message saying the course run key is malformed
```

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done.

**Summary**

openedx-core adds one Python API function that returns a learner's remaining criteria in a course run: the criteria the learner hasn't demonstrated and that no Demonstrated ancestor group or competency already satisfies. openedx-platform adds a new LMS djangoapp for CBE learner features. Its endpoint resolves the target learner with #738's shared resolver, orders the remaining criteria's subsections by that learner's course outline, and makes two passes, retry candidates first and then not-started candidates, asking #855 whether each openable subsection accepts a submission. When nothing qualifies, the reason is chosen from openability alone, and the response carries a resume link computed for the target learner.

**Approach**

openedx-core, in `openedx_learning`:

1. `get_remaining_course_criteria(course_key, user_id)` in `applets/cbe/api.py` goes in `__all__`, because openedx-platform imports it from `openedx_learning.api`. The function is additive, but it becomes a supported contract, so it returns frozen dataclasses instead of model instances: `RemainingCourseCriteria(has_criteria, criteria)`, where each `RemainingCriterion` carries `criterion_id`, `tag_id`, `competency_name` (the tag's value), `object_id` (the subsection usage key), `status` (the status string, or `None` when there is no row), `rule_type`, and `rule_payload`.
2. The function reuses #733's `get_course_competency_criteria(course_key)` walk, so #733's archived and disabled exclusions apply, and it returns `has_criteria=False` when the walk finds no criteria. Otherwise it loads this learner's `StudentCompetencyCriteriaStatus` rows for the walked criteria and `StudentCompetencyStatus` rows for their competency tags, reusing #738's status queries. It also loads `StudentCompetencyCriteriaGroupStatus` rows for every walked group, root included, which #738 doesn't read.
3. A criterion is dropped when its own status, the status of any ancestor group up to and including the root, or its competency tag's status is Demonstrated. The root group and `StudentCompetencyStatus` span course runs, so a competency demonstrated in another course run drops this run's criteria for it, including criteria with no status row of their own. A Demonstrated parent tag in the taxonomy drops nothing. The query count stays constant as the number of criteria grows.

openedx-platform, in a new `lms/djangoapps/cbe_learner/` app with no models:

4. `lms/urls.py` mounts the app at `api/cbe_learner/`. The app's `urls.py` routes `v1/next-action/{COURSE_KEY_PATTERN}`, and the same path followed by `/(?P<student_id>[^/]+)`, to `NextActionView`, mirroring ProgressTabView's two routes and its authentication classes.
5. `NextActionView` returns 400 with a message on `InvalidKeyError`. A value that doesn't match `COURSE_KEY_PATTERN` gets a routing 404 before it reaches the view, so the malformed-key test needs a value that matches the pattern but fails to parse. The view resolves the learner by calling #738's shared resolver (extracted from `ProgressTabView._get_student_user`) directly, and returns 404 when the named user doesn't exist, when a requester without staff access names another learner, or when no learner is named and the requester has no active enrollment and no staff access. Every later step uses the resolved learner, never `request.user`.
6. `get_next_action(course_key, learner)` in the app's `api.py` does the ranking:
   1. Call `get_remaining_course_criteria(course_key, learner.id)`. If the course run has no criteria, return `no_criteria_in_course` before any outline work, so a course run without CBE costs one query. An empty list of remaining criteria returns `all_demonstrated`.
   2. Call `details = get_user_course_outline_details(course_key, learner, now)` for the learner, never the requester, because `can_see_all_content` skips every outline processor for staff. Order the remaining criteria's subsections by `details.outline.sections` and then each section's `sequences`, matching parsed `UsageKey`s. A subsection is openable only when it is in `details.outline.accessible_sequences`. A subsection missing from the outline (deleted, staff-only, or in another content group) is not openable. A past-due subsection set to hide after its due date leaves `accessible_sequences`, so it counts as not openable.
   3. Retry pass, in outline order, over openable subsections where at least one remaining criterion has a status row: skip a subsection whose score is hidden (step 7), then call `get_subsection_submission_state(learner, subsection_key)` (#855). The first subsection whose result has `.accepts == "yes"` is recommended as `retry_available`. An `"unknown"` answer doesn't qualify.
   4. Not-started pass, only when the retry pass finds nothing, over openable subsections where no remaining criterion has a status row: the first subsection where `get_subsection_submission_state(learner, subsection_key)` returns `.attempted == False` and `.accepts` of `"yes"` or `"unknown"` is recommended as `not_started`. #855 returns `.accepts == "no"` past the learner's due date, so #754 checks no dates itself.
   5. Otherwise, the reason is `nothing_actionable` when any remaining subsection was openable, and `nothing_openable` when none was. The outline alone decides this, so it costs no #855 calls.
7. A retry candidate's score is hidden when #739's masking rule holds for the learner: its `show_correctness` is `never_but_include_grade`, or `ShowCorrectness.correctness_available(show_correctness, due, learner_has_staff_access)` is false. `show_correctness` comes from the collected block structure (the grades transformer collects it). `due` comes from the outline schedule, which carries the learner's own dates. `learner_has_staff_access` comes from `has_access(learner, "staff", course_key)`, as in ProgressTabView.
8. `resume_url` is set for every null `next_action` except `no_criteria_in_course`. When `get_key_to_last_completed_block(learner, course_key)` succeeds, `resume_url` is the absolute `jump_to` URL for that block, as on the course home. On `UnavailableCompletionData`, it is `make_learning_mfe_courseware_url(course_key, sequence)` for the first sequence in outline order that is in `accessible_sequences`, or for the course alone when no sequence is. Don't reuse the course home's code path, because it builds this fallback from the requester's outline.
9. The response follows the Description's sample, plus a top-level `resume_url` that is null whenever step 8 doesn't set it, so all three top-level keys are always present. `subsection.display_name` is the outline's sequence title, and `url` is `make_learning_mfe_courseware_url(course_key, subsection)`. `reason` is one of `retry_available`, `not_started`, `no_criteria_in_course`, `all_demonstrated`, `nothing_openable`, or `nothing_actionable`. `criteria` lists the recommended subsection's remaining criteria in criterion id order, and `rule_payload` is returned as stored, so a Grade threshold is a fraction from 0.0 to 1.0.

Tests the Acceptance Criteria don't cover:

- openedx-core: a Demonstrated bottom-tier group, course-level group, root group, or competency status each drops its criteria, including a sibling criterion with no status row. A group status other than Demonstrated, another learner's rows, and a Demonstrated parent tag drop nothing. `status` is `None` when there is no row. #733's exclusions give `has_criteria=False`. The query count is constant.
- openedx-platform: #855 is never called for an unopenable subsection or on the `no_criteria_in_course` and `all_demonstrated` paths. #855 answers whether a subsection's graded content accepts a submission from a learner now and whether the learner has attempted it. Each AC example is a product state that produces one of #855's answers; ranking tests drive those answers through a mock, because #855's own tests cover the product states behind each answer.
- The openedx-core read is covered by the unit tests in the openedx-core bullet above, not by AC scenarios.

Out of scope:

- The re-attempt check itself (#855).
- The frontend (#755).
- Response caching.

**Files to create and modify**

| File | Change |
| --- | --- |
| src/openedx_learning/applets/cbe/api.py | modified: get_remaining_course_criteria() and its result dataclasses |
| openedx-platform: lms/djangoapps/cbe_learner/apps.py | new: app config |
| openedx-platform: lms/djangoapps/cbe_learner/api.py | new: get_next_action() |
| openedx-platform: lms/djangoapps/cbe_learner/views.py | new: NextActionView |
| openedx-platform: lms/djangoapps/cbe_learner/serializers.py | new: response serializers |
| openedx-platform: lms/djangoapps/cbe_learner/urls.py | new: the two next-action routes |
| openedx-platform: lms/urls.py | modified: mount api/cbe_learner/ |
| openedx-platform: lms/envs/common.py | modified: add the app to INSTALLED_APPS |

**Additional context**

- #733: the criteria walk and its exclusions, the `api/cbe/` mount, and the learner-facing API pattern for CBE.
- #738: the learner status reads, the shared learner resolver, and the caller rules this endpoint matches.
- #642 adds the learner status tables. #699, #643, and #701 are needed to see real statuses end to end; none of them blocks building this ticket.
- The openedx-platform PR can merge only after an openedx-core release that contains `get_remaining_course_criteria` is pinned in openedx-platform's requirements.
- `docs/openedx_learning/decisions/0002-competency-criteria-model.rst`: the group tree and the three learner status tables.
- `lms/djangoapps/course_home_api/progress/views.py`: ProgressTabView, the reference for authentication, masquerade, and the `never_but_include_grade` filter.
- `lms/djangoapps/grades/subsection_grade.py`: `show_grades`, the masking rule #739 relies on.

</details>

## Open Questions

- (architect, final review) Should #754 stay one ticket with two PRs, or should the openedx-core read become its own ticket? The estimate is 3 to 3.5 developer-days against the 1-2 day bar, and the openedx-platform PR can't merge until an openedx-core release carrying the new function is pinned, so the two PRs already ship on separate schedules. Options: A) keep one ticket, as #733 and #738 do; B) split the openedx-core read (about 1 day) into a companion ticket that #754 depends on, leaving #754 at about 2 to 2.5 days; C) do B and also drop the resume link, bringing #754 to about 2 days. Recommended: B.
- (architect, final review) Who enforces the learner's due date when #855 can't evaluate a not-started subsection's content, for example an LTI tool? #754 and #855 must agree, or a past-due external-tool subsection is either recommended or checked twice under different rules. Options: A) #855 reports "does not accept" for any subsection past the learner's due date plus grace period, before it checks content type, and #754 checks no dates; B) #855 reports "unknown", and #754 checks the learner's due date from the outline schedule. Recommended: A, which is how both tickets state it.
- (architect, final review) Is the resume link firmly in scope? It adds about 0.25 day, and it is the only way #755 can show a fallback link for the target learner, because the course home computes its link from the requester's outline. Options: A) keep it, as the Approach states; B) drop it, and #755 hides the notice when there is no recommendation. Recommended: A.
- (architect, final review) Is it enough that every AC scenario is verified through the LMS endpoint? Under this default, the openedx-core PR is verified only by the unit tests listed in Technical Details, and the ranking tests drive #855's answers through a mock. Options: A) yes; B) add AC scenarios marked for the openedx-core PR, as #733 does; C) also require real product states in #754's endpoint tests (about a day more, duplicating #855's tests). Recommended: A.
- (architect, final review) Does a Demonstrated parent competency in the taxonomy, for example "Problem Solving" above "Root Cause Analysis", suppress the child competency's criteria? #643 rolls statuses up through parent tags, but a Demonstrated parent doesn't show that each child was demonstrated. Options: A) no, only the criterion's own competency and its ancestor groups suppress, as the Approach states; B) yes. Recommended: A.
- (architect, final review) What are the new djangoapp's name and URL? #755 calls this URL, and later CBE learner features will live in the same app. Options: A) `lms/djangoapps/cbe_learner`, serving `api/cbe_learner/v1/next-action/<course_key>`; B) another name. Recommended: A.
- (architect, final review) Should every signed-in refusal be a 404, including a learner requesting their own result with no active enrollment? #738's caller rules refuse anyone else with a 404, but ProgressTabView returns 401 for that case and #733 returns 403. Options: A) 404 for every signed-in refusal, as the Approach states; B) match ProgressTabView. Recommended: A.
- (architect, final review) What does course staff get when they name a learner who exists but has no active enrollment in the course run? ProgressTabView returns that learner's progress to staff whatever the learner's enrollment, and #738 doesn't address the case. Options: A) match ProgressTabView and return the learner's recommendation; B) refuse it the same way as naming a user who doesn't exist. Recommended: A, for parity with ProgressTabView. Add an AC scenario for whichever answer is chosen.
- (implementer) In what order should #754 call #855, and should anything be cached? In the worst case, when nothing is actionable, #855 is called once for every openable subsection with remaining criteria. Recommended: call #855 one candidate at a time during the two outline-order passes, stopping at the first hit in each, and build the learner's course block structure once per request and pass it to #855 if profiling shows #855 rebuilding it on each call.
