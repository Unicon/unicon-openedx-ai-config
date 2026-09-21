# [Release Docs] Docs for handling competency criteria on course copy

GitHub: https://github.com/openedx/openedx-core/issues/652 (#652, OPEN)
Cached: 2026-09-21

This issue adds user-facing documentation and release notes for how competency criteria are handled when a course is copied (e.g., rerun or course copy/import).

Documentation should explain what happens to competency criteria, criteria groups, and their content associations when a course is copied, whether they carry over automatically or need reconfiguration in the new course, and any limitations a course author should expect. Documentation should follow the same process used for the previous taxonomy editing work, with docs added to the Open edX documentation repository.

Release notes should be created as part of this ticket, since this ticket explicitly covers release-note authoring rather than deferring to Axim's separate release-notes process.

**Documentation Location:**
Documentation should be added to the Open edX documentation repository:
https://github.com/openedx/docs.openedx.org

**Outstanding/Needs Confirmation:**
- Confirm the exact documentation page or section where this content should be added in the repository.
- Confirm the actual course-copy behavior for competency criteria (carry over as-is, drop, or require re-association) before documenting it — this isn't settled in the tickets covered so far in this session.
