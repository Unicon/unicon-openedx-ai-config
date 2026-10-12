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
   - Any subsection the learner can't currently open or act on right now: unreleased, prerequisite-gated, past its due date for the learner plus any grace period the course allows, graded content locked for the learner's enrollment track, or otherwise unavailable.
   - Any criterion whose ancestor group (at any level), whose competency, or any ancestor of its competency in the taxonomy already reports "Demonstrated" for this learner, even when that specific criterion has no status row of its own. This is what keeps an already-satisfied OR group from still recommending its untouched siblings. A competency demonstrated in another course counts.
4. Split what's left into three groups, based on what the learner has submitted in each subsection:
   - **Continue candidates:** the learner has submitted some of the subsection's graded parts but not all of them, and the subsection still accepts a submission from the learner.
   - **Retry candidates (retakes):** the learner has submitted every graded part, every one has been graded, a criterion there is still not "Demonstrated," the learner can see the score of their earlier attempt, and the subsection accepts a resubmission from the learner. A subsection whose graded work staff reset for the learner, so the learner has submitted nothing there since, is still a retry candidate when the learner has a status on a remaining criterion there. A subsection where the learner has submitted every graded part but one is still awaiting grading is neither a continue nor a retry candidate.
   - **Not-started candidates (new attempts):** the learner hasn't submitted any of the subsection's graded parts and has no status on any of its remaining criteria.
5. Recommend the candidate, from any of the three groups, with the soonest due date for the learner. Subsections with no due date come after all dated ones. When several candidates share the soonest due date, or none of them has a due date, prefer a continue candidate, then a retry candidate, then a not-started candidate, and among candidates of the same group, the one that comes first in the course outline (section order, then subsection order). Otherwise, there's no recommendation.
6. Return, for the selected subsection: its display name, a ready-to-use navigation URL, and, for each of its criteria that is not "Demonstrated" and not removed in step 3, the criterion id, competency tag id, competency name, status (null when the learner has no status row), and rule. Also return the reason for the recommendation: `continue_available`, `retry_available`, or `not_started`.
7. When there's no recommendation, return the reason there is none and, when the course has competency criteria, a link that resumes the course.

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
  "reason": "retry_available",
  "resume_url": null
}
```

## Context
- Corresponding architecture spike: #757
- Frontend counterpart: #755
- Blocked by: #855

## Acceptance Criteria

Every scenario below shares this setup, unless the scenario says otherwise:

- A learner has an active enrollment in course run X, and every subsection named carries a competency criterion.
- A criterion is remaining for a learner when the learner hasn't demonstrated it, and neither its own competency, an ancestor of that competency in the taxonomy, nor any group above it reports Demonstrated for that learner.
- Every subsection named is released, open to the learner, not past due for the learner, shows results to learners, and accepts a submission from the learner now.
- Every scenario is observed through the recommended next action endpoint.
- The learner's due date for a subsection is the subsection's due date as it applies to that learner, including an individual extension or a self-paced schedule. A subsection is past due for the learner once the learner's due date for it, and any grace period the course has after it, have both passed.
- Unless a scenario gives due dates, no subsection named has a due date, so candidates are ordered by kind and then by course outline order.
- A subsection is categorized as one to continue when the learner has submitted to or been scored on some of its graded parts but not all of them.
- A subsection is categorized as a retake when the learner has submitted every graded part, every one of them has been graded, and a criterion on it is still remaining. It is also a retake when staff reset the learner's work on it after it was graded, so the learner has submitted nothing there since, but the learner still has a status on a remaining criterion there.
- A subsection is categorized as a new attempt when the learner hasn't submitted to or been scored on any of its graded parts and has no status on any of its remaining criteria.
- The result's reason for a recommendation is `continue_available` for a subsection to continue, `retry_available` for a retake, and `not_started` for a new attempt.

The scenarios use this example taxonomy, where "Literary Skills" is the parent competency of "Writing Poetry" and "Analysis":

```
Literary Skills
├── Writing Poetry
└── Analysis
Research
```

In course run X, the criteria for "Writing Poetry" form this group tree:

```
"Writing Poetry" course-level group for course run X (OR)
├── bottom-tier group A (OR)
│   ├── criterion on subsection D1
│   └── criterion on subsection D2
└── bottom-tier group B
    └── criterion on subsection D3
```

Group and competency statuses roll up asynchronously (openedx-core ADR 0004). For a short time after a learner demonstrates one subsection in an OR group, an untouched sibling in that group can still be recommended. The scenarios assume the roll-up has finished.

**Choosing what to recommend**

```gherkin
Scenario: A retake lists only what is left to demonstrate there
  Given subsection "Poetry Assignment 2" carries criteria for "Writing Poetry" (a grade of at least 80 percent), "Analysis" (at least 60 percent), and "Research" (at least 90 percent)
  And the learner submitted every graded part of "Poetry Assignment 2" and scored 70 percent, demonstrating "Analysis" there but not "Writing Poetry" or "Research"
  And the learner demonstrated the "Research" competency in course run Y
  And no other subsection in course run X is a candidate of any kind
  When the learner requests their recommended next action in course run X
  Then "Poetry Assignment 2" is recommended as a retake, with the reason `retry_available`
  And the result names "Poetry Assignment 2" and links to it in the courseware
  And the recommendation lists only "Writing Poetry", with its competency name, the learner's status of attempted but not demonstrated, and the rule of a grade of at least 80 percent

Scenario Outline: Among candidates due on the same date, a subsection to continue comes before a retake, and a retake before a new attempt
  Given subsection P is <P's kind>, and subsection R is <R's kind>
  And R comes before P in the course outline, and <due dates>
  And no other subsection in course run X is a candidate of any kind
  When the learner requests their recommended next action in course run X
  Then P is recommended as <recommendation>

  Examples:
    | P's kind | R's kind | due dates | recommendation |
    | one to continue | a retake | R and P have the same due date for the learner | a subsection to continue |
    | one to continue | a new attempt | R and P have the same due date for the learner | a subsection to continue |
    | a retake | a new attempt | R and P have the same due date for the learner | a retake |
    | a retake whose graded work staff reset for the learner, so the learner has submitted nothing there since | a new attempt | R and P have the same due date for the learner | a retake |
    | one to continue | a retake | neither R nor P has a due date | a subsection to continue |
    | a retake | a new attempt | neither R nor P has a due date | a retake |

Scenario Outline: The candidate due soonest for the learner is recommended, whatever its kind
  Given course run X has three <candidates>: P, Q, and R, in that course outline order
  And <due dates>
  And no other subsection in course run X is a candidate of any kind
  When the learner requests their recommended next action in course run X
  Then <recommended> is recommended

  Examples:
    | candidates                       | due dates                                                                                      | recommended |
    | subsections the learner hasn't started | R is due soonest and Q is due last                                                       | R           |
    | retakes                          | R is due soonest and Q is due last                                                             | R           |
    | subsections to continue          | R is due soonest and Q is due last                                                             | R           |
    | candidates where P is one to continue, Q is a retake, and R is a new attempt | R is due soonest and P is due last                               | R           |
    | candidates where P is one to continue, Q is a retake, and R is a new attempt | only R has a due date                                            | R           |
    | subsections the learner hasn't started | only Q has a due date                                                                    | Q           |
    | subsections the learner hasn't started | none of them has a due date                                                              | P           |
    | subsections the learner hasn't started | P and R share the soonest due date, and Q is due later                                   | P           |
    | subsections the learner hasn't started | P's course-wide due date is soonest, the learner has an extension on P to a date after R's, and Q is due after both | R |
    | subsections the learner hasn't started | P is past its due date for the learner but still within the course's grace period, and Q and R are due later | P |

Scenario: A subsection to continue lists its remaining criteria
  Given the learner submitted subsection M's open response assessment, which is awaiting grading
  And M also holds a problem the learner hasn't answered, which still accepts answers from the learner
  And M carries criteria for "Writing Poetry" and "Analysis"
  And no other subsection in course run X is a candidate of any kind
  When the learner requests their recommended next action in course run X
  Then M is recommended as a subsection to continue, with the reason `continue_available`
  And the recommendation lists "Writing Poetry" and "Analysis", each with its competency name, rule, and the learner's status, or no status where the learner has none

Scenario: A new attempt lists the subsection's remaining criteria, none with a status
  Given the learner hasn't attempted anything in course run X
  And subsection "Poetry Assignment 1" comes first in course run X's outline and carries criteria for "Writing Poetry" and "Analysis"
  When the learner requests their recommended next action in course run X
  Then "Poetry Assignment 1" is recommended as a new attempt, with the reason `not_started`
  And the recommendation lists "Writing Poetry" and "Analysis", each with its competency name and rule, and neither with a status for the learner

Scenario Outline: A subsection to continue or a new attempt lists only its remaining criteria
  Given subsection M carries criteria for "Writing Poetry" and "Research", and is <kind>
  And the learner demonstrated the "Writing Poetry" competency in course run Y
  And no other subsection in course run X is a candidate of any kind
  When the learner requests their recommended next action in course run X
  Then M is recommended as <kind>
  And the recommendation lists only "Research"

  Examples:
    | kind |
    | a subsection to continue |
    | a new attempt |

Scenario: A reset subsection whose only status is on an already-demonstrated criterion is a new attempt
  Given subsection M carries criteria for "Analysis" and "Writing Poetry"
  And the learner demonstrated "Analysis" on M, and the criterion for "Writing Poetry" was added to M after the learner's work there was graded, so the learner has no status on it
  And staff then reset the learner's graded work on M, and the learner has submitted nothing there since
  And no other subsection in course run X is a candidate of any kind
  When the learner requests their recommended next action in course run X
  Then M is recommended as a new attempt
  And the recommendation lists only "Writing Poetry", with no status for the learner
```

**Criteria already satisfied through a group or competency**

```gherkin
Scenario Outline: A subsection whose criteria are already satisfied higher up is not recommended
  Given subsection D1 comes first in course run X's outline, carries a criterion for "Writing Poetry", and is <D1's kind>
  And D1's criterion shares OR group A with D2's criterion, and group A and group B, which holds D3's criterion, sit under "Writing Poetry"'s course-level OR group for course run X
  And "Writing Poetry" is a child of the competency "Literary Skills" in the taxonomy, and "Research" is not
  And subsection E, later in the outline, carries a criterion for "Research" and is one the learner hasn't started
  And <satisfied>
  When the learner requests their recommended next action in course run X
  Then E is recommended, and D1 is not

  Examples:
    | D1's kind | satisfied |
    | one the learner hasn't started | the learner demonstrated D2, so bottom-tier group A is demonstrated |
    | one the learner hasn't started | the learner demonstrated D3, so bottom-tier group B and the course-level group are demonstrated |
    | one the learner hasn't started | the learner demonstrated the "Writing Poetry" competency in course run Y |
    | one the learner hasn't started | the learner demonstrated the parent competency "Literary Skills" |
    | one to continue | the learner demonstrated D2, so bottom-tier group A is demonstrated |
    | a retake | the learner demonstrated the parent competency "Literary Skills" |
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
    | the learner hasn't started U, and U is past due for the learner                                                                                                          |
    | the learner hasn't started U, the learner is in the audit track, and U's graded content is locked for audit learners                                                               |
    | the learner hasn't started U, U's graded content is an external tool whose submission rules can't be checked, and U is past due for the learner                         |
    | the learner hasn't started U, and U holds no scored content worth points that the learner can see                                                                                  |
    | the learner has no status on U, and checking whether U's graded content accepts a submission from the learner fails                                                                |
    | the learner submitted U and the submission is awaiting grading, so the learner has no status on U yet                                                                              |
    | the learner submitted U, an open response assessment, and U is waiting on the learner's own peer assessment step, so the learner has no status on U yet                           |
    | the learner submitted every graded part of U, one of them is still awaiting grading, and another is a problem the learner answered and may answer again                                          |
    | U is one to continue, and U is past due for the learner                                                                                                                  |
    | U is a retake, and the learner has used all of U's attempts                                                                                                                        |
    | U is a retake, staff reset U's open response assessment for the learner, and the learner's new submission is awaiting grading                                                     |
    | U is a retake, and U's graded content is an external tool whose retake rules can't be checked                                                                                      |
    | U is a retake whose graded work staff reset for the learner, and U's graded content is an external tool whose retake rules can't be checked |
    | U is a retake whose graded work staff reset for the learner, and U is set never to show results to learners |

Scenario Outline: A subsection the learner hasn't started is recommended even when its graded content can't be checked
  Given subsection L comes first in course run X's outline, and its graded content is <content>
  And the learner hasn't started L, and L isn't past due for the learner
  When the learner requests their recommended next action in course run X
  Then L is recommended as a new attempt

  Examples:
    | content                                                  |
    | an external tool whose submission rules can't be checked |
    | a timed exam run by the separate exams service           |

Scenario: A subsection to continue is recommended even when the part the learner hasn't submitted can't be checked
  Given subsection L comes first in course run X's outline
  And the learner answered L's problem, and hasn't yet sent a score from L's external tool, whose submission rules can't be checked
  And L isn't past due for the learner
  When the learner requests their recommended next action in course run X
  Then L is recommended as a subsection to continue
```

**Scores hidden from the learner**

```gherkin
Scenario Outline: A retake whose score is hidden from the learner is skipped
  Given subsection H is a retake, and the learner's due date for H is sooner than for any other subsection in course run X
  And H <hiding>
  And <rest of the course>
  When the learner requests their recommended next action in course run X
  Then H is not recommended, and <outcome>

  Examples:
    | hiding | rest of the course | outcome |
    | is set never to show results to learners | a later-due subsection K is a retake, and K shows results | K is recommended as a retake |
    | is set to show results only after its due date, which hasn't passed | a later-due subsection K is a retake, and K shows results | K is recommended as a retake |
    | is set never to show whether answers were correct, though it shows the learner's grade | a later-due subsection K is a retake, and K shows results | K is recommended as a retake |
    | is set never to show results to learners | a later-due subsection K is one to continue, and K is also set never to show results to learners | K is recommended as a subsection to continue |
    | is set never to show results to learners | a later-due subsection N is one the learner hasn't started, and no other subsection is a retake candidate | N is recommended as a new attempt |
    | is set never to show results to learners | H holds the learner's only remaining criterion | no subsection is recommended, and the result gives the reason that nothing remaining can be acted on now |
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
    | every remaining criterion is on a subsection that hasn't been released yet                                                                                 | nothing remaining can be opened                |
    | every remaining criterion is on a subsection whose submission from the learner is awaiting grading                                                        | nothing remaining can be acted on now          |
    | every remaining criterion is on a subsection the learner hasn't started, which is past due for the learner and still shown to learners after its due date | nothing remaining can be acted on now          |
    | every remaining criterion is on a subsection the learner hasn't started, which is past due for the learner and hidden from learners after its due date | nothing remaining can be opened |
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
    | S                                                            | naming L, after L has unenrolled | L |
    | S, who has no enrollment in course run X                     | without naming a learner | S    |
    | C, a CCX coach for course run X who isn't on its staff       | naming L                 | L    |

Scenario Outline: A caller who isn't permitted is refused and learns nothing
  Given learners L and M both have active enrollments in course run X
  When <caller> requests a recommended next action in course run X <naming>
  Then <response>
  And the response contains no recommendation, reason, or resume link
  And the response doesn't say whether the named user exists

  Examples:
    | caller                                                                             | naming                          | response                                                       |
    | a caller who isn't signed in                                                       | without naming a learner        | the caller is asked to sign in                                 |
    | a signed-in user with no active enrollment in course run X and no staff role there | without naming a learner        | the request is refused as not enrolled (401)                   |
    | a user who enrolled in course run X and later unenrolled                           | without naming a learner        | the request is refused as not enrolled (401)                   |
    | M                                                                                  | naming L                        | the request is refused as not found (404)                      |
    | M                                                                                  | naming a user who doesn't exist | the request is refused as not found (404)                      |
    | a signed-in user with no active enrollment in course run X and no staff role there | naming L                        | the request is refused as not found (404)                      |
    | a member of course run X's staff                                                   | naming a user who doesn't exist | the request is refused as not found (404)                      |

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
    | U is a retake for L, and L has used all of U's attempts                                            | V           |
    | U is a retake for L, and U is set never to show results to learners                                | V           |
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
  When the learner requests a recommended next action for a value that fits the course run key part of the URL but doesn't parse as a course run key
  Then the request is rejected as a bad request (400) with a message saying the course run key is malformed
```

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done.

**Summary**

openedx-core adds one Python API function that returns a learner's remaining criteria in a course run: the criteria the learner hasn't demonstrated and that nothing above them already satisfies, meaning no Demonstrated ancestor group, competency, or ancestor competency in the taxonomy. openedx-platform adds a new LMS djangoapp for CBE learner features. Its endpoint accepts and refuses callers the way ProgressTabView does, sorts the openable subsections that carry remaining criteria by the learner's due dates, and asks #855 about each one in that order. The first due date that has any candidate wins. Among candidates sharing that due date, a subsection to continue beats a retake, which beats a new attempt. When nothing qualifies, the response carries a resume link computed for the target learner.

**Approach**

openedx-core, in `openedx_learning`:

1. `get_remaining_course_criteria(course_key, user_id)` in `applets/cbe/api.py` goes in `__all__`, because openedx-platform imports it from `openedx_learning.api`. The function is additive, but it becomes a supported contract, so it returns frozen dataclasses instead of model instances: `RemainingCourseCriteria(has_criteria, criteria)`, where each `RemainingCriterion` carries `criterion_id`, `tag_id`, `competency_name` (the tag's value), `object_id` (the subsection usage key), `status` (the status string, or `None` when there is no row), `rule_type`, and `rule_payload`.
2. The function reuses #733's `get_course_competency_criteria(course_key)` walk, so #733's archived and disabled exclusions apply, and it returns `has_criteria=False` when the walk finds no criteria. Otherwise it makes three reads for this learner: `StudentCompetencyCriterionStatus` rows for the walked criteria, reusing #738's query; `StudentCompetencyCriteriaGroupStatus` rows for every walked group, root included, which #738 doesn't read; and the learner's Demonstrated `StudentCompetencyStatus` rows in the taxonomies of the walked criteria's competency tags, each with its tag's taxonomy and `lineage`.
3. A criterion is dropped when any of these is Demonstrated: its own status, the status of any ancestor group up to and including the root, or the status of its competency tag or of any ancestor of that tag in the taxonomy. For example, a Demonstrated "Problem Solving" drops the criteria for its child "Root Cause Analysis". `Tag.lineage` lists the tag's values from the taxonomy root down, each followed by a tab, and a value is unique within its taxonomy. So a Demonstrated tag is the criterion's tag or one of its ancestors exactly when it is in the same taxonomy and the criterion tag's `lineage` starts with its `lineage`. `Tag.descendant_count` uses the same prefix match. The check runs in Python over step 2's rows, so the query count stays constant as the number of criteria and the depth of the taxonomy grow. The root group and `StudentCompetencyStatus` span course runs, so a competency demonstrated in another course run drops this run's criteria for that competency and for its descendants, including criteria with no status row of their own.

openedx-platform, in a new `lms/djangoapps/cbe_learner/` app with no models:

4. `lms/urls.py` mounts the app at `api/cbe_learner/`. The app's `urls.py` routes `v1/next-action/{COURSE_KEY_PATTERN}`, and the same path followed by `/(?P<student_id>[^/]+)`, to `NextActionView`, mirroring ProgressTabView's two routes.
5. `NextActionView` returns 400 with a message on `InvalidKeyError`. A value that doesn't match `COURSE_KEY_PATTERN` gets a routing 404 before it reaches the view, so the malformed-key test needs a value that matches the pattern but fails to parse. The view then refuses callers exactly as ProgressTabView does:
   - It uses ProgressTabView's authentication classes and `IsAuthenticated`, so a caller who isn't signed in gets whatever that permission returns.
   - It resolves the learner with `get_student_user()`, which #738 extracts from `ProgressTabView._get_student_user` into `lms/djangoapps/course_home_api/utils.py`, passing the requester's staff access from `has_access(request.user, "staff", course_key)`. That function raises 404 when a requester without staff access names anyone else, whether or not that user exists, and when staff name a user who doesn't exist. A CCX coach naming a learner also passes, as on the Progress tab.
   - The same function applies masquerade. `setup_masquerade` silently drops a masquerade as a specific learner who no longer has an active enrollment (`lms/djangoapps/courseware/masquerade.py:230-240`), so that request resolves to the staff member.
   - The view returns 401 with the body `"User not enrolled."` when the resolved learner has no active enrollment and the requester has no staff access, the same check ProgressTabView makes. Staff who name an existing learner with no active enrollment therefore get that learner's recommendation.

   Every later step uses the resolved learner, never `request.user`.
6. `get_next_action(course_key, learner)` in the app's `api.py` does the ranking:
   1. Call `get_remaining_course_criteria(course_key, learner.id)`. If the course run has no criteria, return `no_criteria_in_course` before any outline work, so a course run without CBE costs one query. An empty list of remaining criteria returns `all_demonstrated`.
   2. Call `details = get_user_course_outline_details(course_key, learner, now)` for the learner, never the requester, because `can_see_all_content` skips every outline processor for staff. A subsection is openable only when it is in `details.outline.accessible_sequences`. A subsection missing from the outline (deleted, staff-only, or in another content group) is not openable. A past-due subsection set to hide after its due date leaves `accessible_sequences`, so it counts as not openable.
   3. Sort the openable subsections that carry remaining criteria by the learner's due date, soonest first. Subsections with no due date go after every dated one. Ties, including among subsections with no due date, go in outline order: by `details.outline.sections`, then each section's `sequences`, matching parsed `UsageKey`s. The learner's due date is `details.schedule.sequences[usage_key].due`. The outline's schedule processor reads it from edx-when's `get_dates_for_course(course_key, user)` for this learner, so it includes individual extensions and self-paced schedules, and it is the same edx-when date #855 reads through `get_course_blocks`. A subsection inside its grace period already has a due date in the past, so it sorts ahead of the rest.
   4. Walk the sorted list once. Call `get_subsection_submission_state(learner, subsection_key)` (#855) for each subsection and classify it from the answer:
      - Continue (`continue_available`): `attempted` is true, `all_submitted` is false, and `accepts` is `"yes"` or `"unknown"`.
      - Retake (`retry_available`): `accepts` is `"yes"`, the score isn't hidden from the learner (step 7), and either `all_scored` is true or `attempted` is false while a remaining criterion on the subsection has a status row. The second case is a staff reset: the reset deletes the learner's submission or attempts, so #855 reports nothing attempted, but the criterion status from the earlier grade remains.
      - New (`not_started`): `attempted` is false, no remaining criterion on the subsection has a status row, and `accepts` is `"yes"` or `"unknown"`.
      - Anything else is not a candidate. That includes a subsection whose counting components are all submitted while one is still awaiting grading (`all_submitted` true, `all_scored` false), and a retake whose `accepts` is `"unknown"`.

      The walk stops once it has classified every subsection that shares the due date of the first candidate it finds, treating "no due date" as one shared date. Among those candidates, recommend the first continue, else the first retake, else the first new attempt, in the step 3 order. `"unknown"` qualifies a continue for the same reason it qualifies a new attempt: the content the learner hasn't submitted to yet is usually the content #855 can't check, such as an external tool. #855 answers `"no"` once the subsection is past the learner's due date plus grace period, so #754 checks no dates itself.
   5. When the walk finds nothing, the reason is `nothing_actionable` if any remaining subsection was openable, and `nothing_openable` if none was. The outline alone decides which of the two applies.
7. The hidden-score skip applies only to retake candidates. A continue candidate is recommended even when its subsection never shows results, because it asks the learner to submit the parts they haven't submitted yet, not to redo a scored attempt. A retake's score is hidden when #739's masking rule holds for the learner: its `show_correctness` is `never_but_include_grade`, or `ShowCorrectness.correctness_available(show_correctness, due, learner_has_staff_access)` is false. `show_correctness` comes from the collected block structure (the grades transformer collects it). `due` is the learner's due date from step 6.3. `learner_has_staff_access` comes from `has_access(learner, "staff", course_key)`, as in ProgressTabView.
8. `resume_url` is set for every null `next_action` except `no_criteria_in_course`. When `get_key_to_last_completed_block(learner, course_key)` succeeds, `resume_url` is the absolute `jump_to` URL for that block, as on the course home. On `UnavailableCompletionData`, it is `make_learning_mfe_courseware_url(course_key, sequence)` for the first sequence in outline order that is in `accessible_sequences`, or for the course alone when no sequence is. Don't reuse the course home's code path, because it builds this fallback from the requester's outline.
9. The response follows the Description's sample. `resume_url` is null whenever step 8 doesn't set it, so all three top-level keys are always present. `subsection.display_name` is the outline's sequence title, and `url` is `make_learning_mfe_courseware_url(course_key, subsection)`. `reason` is one of `continue_available`, `retry_available`, `not_started`, `no_criteria_in_course`, `all_demonstrated`, `nothing_openable`, or `nothing_actionable`. `criteria` lists the recommended subsection's remaining criteria in criterion id order, and `rule_payload` is returned as stored, so a Grade threshold is a fraction from 0.0 to 1.0.

Tests the Acceptance Criteria don't cover:

- openedx-core: a Demonstrated bottom-tier group, course-level group, root group, competency status, or ancestor competency at any depth each drops its criteria, including a sibling criterion with no status row. These drop nothing: a group status other than Demonstrated, another learner's rows, a Demonstrated descendant competency, a Demonstrated tag with the same value in another taxonomy, and a Demonstrated sibling whose value is a prefix of the criterion tag's value ("Writing" beside "Writing Poetry"). `status` is `None` when there is no row. #733's exclusions give `has_criteria=False`. The query count is the same for one criterion as for many, and for a two-level taxonomy as for a deeper one.
- openedx-platform: #855 is never called for an unopenable subsection or on the `no_criteria_in_course` and `all_demonstrated` paths, and it is not called for a subsection due after the first due date that has a candidate. A candidate with an earlier due date beats one of any kind due later, and on the same due date a continue beats a retake, which beats a new attempt. #855 answers whether a subsection accepts a submission from a learner now, whether the learner has attempted it, and whether every counting component is submitted and scored. Each AC example is a product state that produces one of #855's answers; ranking tests drive those answers through a mock, because #855's own tests cover the product states behind each answer.
- The openedx-core read is covered by the unit tests in the openedx-core bullet above, not by AC scenarios.

Out of scope:

- The submission-state check itself, including its `all_submitted` and `all_scored` answers (#855).
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
- #738: the learner status reads and the extracted `get_student_user()`.
- #642 adds the learner status tables. #699, #643, and #701 are needed to see real statuses end to end; none of them blocks building this ticket.
- The openedx-platform PR can merge only after an openedx-core release that contains `get_remaining_course_criteria` is pinned in openedx-platform's requirements.
- `docs/openedx_learning/decisions/0002-competency-criteria-model.rst`: the group tree and the three learner status tables.
- `lms/djangoapps/course_home_api/progress/views.py`: ProgressTabView, the reference for authentication, refusals, masquerade, and the `never_but_include_grade` filter.
- `lms/djangoapps/grades/subsection_grade.py`: `show_grades`, the masking rule #739 relies on.

</details>

## Open Questions

- (implementer) In what order should #754 call #855, and should anything be cached? A subsection's kind depends on #855's answer, so the walk calls #855 for each openable subsection with remaining criteria, in due-date order, until it has found a candidate and classified every subsection sharing that candidate's due date. In the worst case, when nothing is actionable, that is one #855 call per openable subsection. Recommended: walk the candidates once in due-date order, calling #855 one subsection at a time, and stop as described in the Approach. Build the learner's collected block structure once per request and pass it to #855 through the optional `collected_block_structure` argument #855 proposes. Profile a course with about 50 subsections carrying criteria; if it is too slow, add a batch form of #855 that takes many subsection keys as a follow-up.
