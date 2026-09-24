# [BE] GET taxonomy tags from an LMS route

GitHub: not yet filed. Needed by #734.

## User Story
As a learner, I need to be able to see the taxonomy tag hierarchy associated with my course's content so that I can understand how to demonstrate mastery of competency tags in the course.

## Description

This ticket should build a GET taxonomy tags endpoint that works in the LMS identically to the one that works in Studio. It should have a taxonomy id that it takes in as input and then it should return the tags in a way that the taxonomy hierarchy can be understood.

## Context
Blocks #734.

## Notes for drafting

Placeholder for the ticket we discovered we needed in 733, which I think is a ticket to get taxonomy tags from a learner LMS route.

### Decided so far, in #734's pre-handoff check

- For each tag #734 asks about, the endpoint returns the tag with its depth and its ancestor chain, built from `Tag.lineage`, which every Tag row already stores. #734 uses this for parent grouping, the breadcrumb, and detecting a topmost-level tag. A straight copy of Studio's taxonomy-tags endpoint returns `depth` and `parent_value` but no lineage, and returns the whole tree only below a size threshold (one level at a time, 30 tags per page, above it). That's why the endpoint returns ancestors per tag.
- #733's endpoint is not changed for lineage.
