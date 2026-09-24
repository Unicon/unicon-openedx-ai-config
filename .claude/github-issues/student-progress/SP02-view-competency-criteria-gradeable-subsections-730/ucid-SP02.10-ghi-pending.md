# [FE?] Let the operator choose to replace Grade summary with CBE Progress

GitHub: not yet filed. Depends on #734 and #828.

## User Story
As a site operator, I want to be able to have the Grade summary replaced with CBE Progress for courses that have competency criteria while courses without competency criteria still show the Grade summary, so that neither students of CBE courses nor students of traditional courses get confused about their overall progress.

## Description

## Context

## Notes for drafting

### Known scope, decided during #734's pre-handoff check

- #734 renders the competency criteria panel above the stock "Grades" card, the default content of `ProgressTabCourseGradeSlot`. The Figma shows the panel with no Grades card, which is the "in place of" layout this ticket adds.
- The operator chooses between "above" and "in place of". "In place of" uses `PLUGIN_OPERATIONS.Wrap` on the slot's `default_contents`, with a wrapper that renders the stock Grades card only in courses with no competency criteria. That wrapper needs #734's check against #733's endpoint, which is why this ticket follows #734.
- Extends #828's data-driven Tutor slot mapping rather than rewriting it.
- frontend-app-learning#1905 moves plugin slots to frontend-base's `Slot` API, so the `PLUGIN_OPERATIONS.Wrap` mechanism may change before this ticket is built.
