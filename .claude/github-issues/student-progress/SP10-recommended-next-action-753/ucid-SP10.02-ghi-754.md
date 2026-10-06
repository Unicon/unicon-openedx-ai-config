# [BE] GET Recommended Next Action for CBE Learner in Course

GitHub: https://github.com/openedx/openedx-core/issues/754 (#754, OPEN)
Cached: 2026-09-21

## User Story
As a learner, I want to know what my recommended next action is in my CBE course in order to maintain momentum in learning and skill demonstration without having to figure this out myself or have someone tell me.

## Description
This ticket implements the design decided in #757. This will be a learner facing endpoint that takes in the context of the course and the learner and then outputs the recommended next action for the learner.

This is the algorithm that will be used to calculate the Recommended Next Action:
1. Given a course and a learner.
2. Find every subsection in the course that carries a competency criterion.
3. Remove from that set:
   - Any subsection the learner can't currently open right now (unreleased, prerequisite-gated, or otherwise unavailable).
   - Any criterion whose enclosing group, or whose competency, already reports "Demonstrated" for this learner, even when that specific criterion has no status row of its own. This is what keeps an already-satisfied OR group (for example, the duplicate-subsection workaround, once one duplicate is demonstrated) from still recommending its untouched siblings.
4. Split what's left into two groups:
   - **Retry candidates:** the learner's status on this subsection's criterion isn't "Demonstrated," and the subsection's re-attempt state (section 1) is retryable. A subsection whose re-attempt state is unknown is not a retry candidate, but it doesn't fall into "not-started" either, since it does have a status row; it simply isn't recommended by this round of the calculation, and its criterion is what `retry_state_unknown` (section 5) reports when nothing else is left to recommend.
   - **Not-started candidates:** the learner has no status row on this subsection's criterion, and no submission or attempt has been recorded against it yet. This keeps a subsection whose submission is still awaiting grading from being mistaken for one the learner hasn't touched at all.
5. If any retry candidates exist, recommend the one that comes chronologically first in the course outline. Otherwise, if any not-started candidates exist, recommend the one that comes chronologically first in the course outline. Otherwise, there's no recommendation (section 5 above covers what the response looks like in that case, and why).
6. Return, for the selected subsection: its display name, a ready-to-use navigation URL, and every contributing criterion's competency name, status, and rule.

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
    "reason": "retry_available",
    "criteria": [
      {
        "competency_name": "Writing Poetry",
        "status": "AttemptedNotDemonstrated",
        "rule": {
          "rule_type": "Grade",
          "rule_payload": { "op": "gte", "value": 0.75, "scale": "percent" }
        }
      }
    ]
  }
}
```

## Context
- Corresponding architecture spike: #757
- Frontend counterpart: #755

## Notes for drafting
