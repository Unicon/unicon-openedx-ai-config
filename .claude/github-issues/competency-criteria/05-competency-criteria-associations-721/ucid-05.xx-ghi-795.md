# [BE] Make oel_tagging.can_tag_object's course check authorization-service aware

GitHub: https://github.com/openedx/openedx-core/issues/795 (#795, CLOSED)
Cached: 2026-10-22

**Repo: `openedx-platform` (this fix lives entirely in `openedx/core/djangoapps/content_tagging/`).**

**Companion to `openedx-core` \#665** (build endpoint for creating Competency Criteria): \#665 calls `user.has_perm('oel_tagging.can_tag_object', ...)` directly to decide whether a course author may tag a subsection. That permission currently ignores the new authorization service for course objects, so \#665 is a real, if not yet visible, consumer of the gap this ticket fixes. This ticket is not competency-criteria-specific: `oel_tagging.can_tag_object` is the general tagging permission, used by anything that tags a course object, not only CBE.

## User Story

As a course team member granted tagging access only through the new authorization service, with no legacy course role, I want any code that checks `oel_tagging.can_tag_object` to honor that access the same way Studio's own tag-editing screen already does, in order to be able to tag content consistently no matter which feature or endpoint I use.

## Acceptance Criteria

```
Scenario: A course switched to the new authorization service grants access through it
  Given a course has been switched to the new authorization service
  And a user holds courses.manage_tags on that course only through the new authorization service, with no legacy course role
  When code calls user.has_perm('oel_tagging.can_tag_object', ...) directly for an object in that course
  Then the permission check returns true

Scenario: A course switched to the new authorization service denies access when the new service denies it
  Given a course has been switched to the new authorization service
  And a user does not hold courses.manage_tags on that course through the new authorization service
  When code calls user.has_perm('oel_tagging.can_tag_object', ...) directly for an object in that course
  Then the permission check returns false, even if the user holds a legacy course role
  And this matches the exclusive-switch behavior Studio's own tag-editing endpoint already applies, not an "either system" check

Scenario: A course not yet switched to the new authorization service is unaffected
  Given a course has not been switched to the new authorization service
  And a user holds a legacy course role granting studio write access
  When code calls user.has_perm('oel_tagging.can_tag_object', ...) directly for an object in that course
  Then the permission check returns true, exactly as it does today

Scenario: Content Library objects are unaffected
  Given an object belongs to a Content Library, not a course
  When code calls user.has_perm('oel_tagging.can_tag_object', ...) directly for that object
  Then the permission check behaves exactly as it does today

Scenario: The direct permission check and Studio's own tag-editing endpoint agree
  Given a course and a user, in any combination of switch state and role or authorization-service assignment
  When Studio's own tag-editing endpoint decides whether the user may tag an object in that course
  And code elsewhere calls user.has_perm('oel_tagging.can_tag_object', ...) directly for the same user and course
  Then both give the same answer
```

## Description

**Current state**

`can_change_object_tag_objectid` in `openedx/core/djangoapps/content_tagging/rules.py` is the predicate registered for `oel_tagging.can_tag_object` (via `rules.set_perm`), so it's what any direct `user.has_perm('oel_tagging.can_tag_object', ...)` call resolves to. For a Content Library object, it already checks the new authorization service (`authz_api.is_user_allowed` against `MANAGE_LIBRARY_TAGS`). For a course object, it only ever checks the legacy `has_studio_write_access` role check; it never looks at the new authorization service at all, regardless of whether that course has been switched over.

Meanwhile, `ObjectTagOrgView` in `content_tagging/rest_api/v1/views.py`, the view Studio's own tag-editing screen calls, already implements the correct behavior for courses: it checks `should_use_course_authz_for_object(object_id)` (in `content_tagging/auth.py`), and when that course has been switched to the new service, it checks `courses.manage_tags` through the authorization service exclusively, not falling back to legacy roles at all. When the course hasn't been switched, it falls back to the original permission check. This toggle-aware logic exists, but only in that one view class, not in the shared predicate every other caller of `oel_tagging.can_tag_object` actually depends on.

**Requested change**

Give `can_change_object_tag_objectid`'s course branch the same toggle-aware behavior `ObjectTagOrgView` already has, so every caller of `oel_tagging.can_tag_object`, not just Studio's own tag-editing view, gets the correct answer. Once the shared predicate handles this itself, `ObjectTagOrgView`'s own override duplicates the same logic in a second place; see Technical Details for whether it can be simplified away.

**Explicitly out of scope**

- Any change to Content Library permission handling; it's already correct and untouched by this change.  
- Any change to view-only permissions (`oel_tagging.can_view_object_tag` and similar). A similar course-versus-library asymmetry may exist there too, but it hasn't been verified as part of this ticket; see Open Questions.  
- Any change in `openedx-core` (CBE's `#665` or anywhere else). \#665 needs no change: once this predicate is fixed, `has_perm('oel_tagging.can_tag_object', ...)` gives the right answer without \#665 knowing anything changed.
<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done; what follows exists to save the implementer some thinking, not to bind them.

### In short

**The fix is adding one more branch to an existing function, not building anything new.** `can_change_object_tag_objectid` already special-cases Content Libraries before falling through to a general write-or-org-admin check. This ticket adds an equivalent special case for courses, ahead of that same fallback: when `should_use_course_authz_for_object` says the course has been switched over, check `courses.manage_tags` through the authorization service and return that answer directly, without also checking legacy roles. `should_use_course_authz_for_object` is the exact function `ObjectTagOrgView` already calls, so this reuses existing logic rather than re-deriving it.

**The behavior has to be an exclusive switch, not an added "or."** For a switched-over course, the new authorization service is the system of record, and legacy roles are deliberately not consulted, matching `ObjectTagOrgView`'s own behavior. A caller who instead ORs the two checks together would let a stale legacy role continue granting access after a course has been switched over, which is a real behavior difference from what Studio's own tag-editing screen does today, not just a stylistic difference.

**Once the shared predicate is fixed, `ObjectTagOrgView`'s own override may be redundant.** Its `_authz_check`, `get_permissions`, and `ensure_user_has_can_tag_object_permissions` overrides exist specifically because the shared predicate didn't know about the toggle. Confirm what the parent `ObjectTagView`'s default permission handling actually does before removing anything: if it already resolves through `user.has_perm('oel_tagging.can_tag_object', ...)`, the override in `ObjectTagOrgView` becomes pure duplication of logic that now lives in one place, and removing it consolidates the toggle-check to a single implementation, closing off the exact kind of drift this ticket exists to fix. If the parent's default handling does something else entirely, keep the override and say so.

### Implementation specifics

- **File and function to change.** `openedx/core/djangoapps/content_tagging/rules.py`, `can_change_object_tag_objectid`. Add a branch after the existing Content Libraries check and before the "general write or org-admin access" fallback: call `should_use_course_authz_for_object(object_id)` (already imported elsewhere in this app from `content_tagging/auth.py`); if it returns `(True, course_key)`, return `authz_api.is_user_allowed(user.username, authz_permissions.COURSES_MANAGE_TAGS.identifier, str(course_key))` directly, without falling through to `has_studio_write_access` or the org-admin check.  
- **Do not add an org-admin fallback inside the new branch.** `ObjectTagOrgView`'s existing authz check has no equivalent fallback either; matching that exactly is what "Studio's own tag-editing endpoint and this predicate agree" actually requires. If org-level admins need to retain access after a course switches over, that has to already be modeled inside the authorization service's own role graph, not added here.  
- **`ObjectTagOrgView` simplification.** In `content_tagging/rest_api/v1/views.py`, once the predicate above is confirmed correct, check whether `_authz_check`, `get_permissions`, and `ensure_user_has_can_tag_object_permissions` can be deleted, letting `ObjectTagOrgView` fall back to `ObjectTagView`'s default permission handling. Leave `ensure_has_view_object_tag_permission` (the view-permission override) alone; it's a separate permission (`oel_tagging.can_view_object_tag` or similar) not touched by this ticket, see Open Questions.  
- **Test strategy.** Unit tests directly against `can_change_object_tag_objectid` (or `user.has_perm('oel_tagging.can_tag_object', ...)`, whichever is more direct to set up): a course switched over with only an authz-granted role, allowed; a course switched over with no authz-granted role but a legacy role, denied; a course not switched over with a legacy role, allowed, unchanged from today; a Content Library object, unchanged from today. If `ObjectTagOrgView`'s override is removed, extend or replace its existing permission tests to confirm identical behavior through the simplified path, so the "both paths agree" acceptance criterion is covered by an actual test, not just inspection.

Files to create and modify **Modified files**

| File | Nature of modification |
| :---- | :---- |
| `openedx/core/djangoapps/content_tagging/rules.py` | Add the course-authz-aware branch to `can_change_object_tag_objectid`. |
| `openedx/core/djangoapps/content_tagging/rest_api/v1/views.py` | Remove `ObjectTagOrgView`'s now-redundant `_authz_check`, `get_permissions`, and `ensure_user_has_can_tag_object_permissions` overrides, if confirmed safe per Technical Details. |
| Existing test modules for `content_tagging/rules.py` and `content_tagging/rest_api/v1/views.py` | Add the new-branch coverage described in Technical Details; update or remove tests that exercised the overrides being deleted. |

- Context **`openedx-core` \#665:** the CBE create-criterion endpoint that surfaced this gap by calling `user.has_perm('oel_tagging.can_tag_object', ...)` directly. Needs no change once this ticket lands.  
- `openedx/core/djangoapps/content_tagging/auth.py`'s `should_use_course_authz_for_object`: the toggle-check this ticket reuses, already used by `ObjectTagOrgView`.  
- `openedx/core/djangoapps/content_tagging/rest_api/v1/views.py`'s `ObjectTagOrgView`: the existing, correct, toggle-aware implementation this ticket generalizes out of one view class and into the shared predicate.  
- `openedx_authz.api.is_user_allowed` and `openedx_authz.constants.permissions.COURSES_MANAGE_TAGS`: the authorization-service check this ticket calls, already a dependency of this app.

## Open Questions

- **\[non-blocking, owner: implementer\]** Does the equivalent view-only permission (`oel_tagging.can_view_object_tag` or similar, checked via `ensure_has_view_object_tag_permission`'s `COURSES_VIEW_COURSE` check in `ObjectTagOrgView`) have the same course-versus-library asymmetry as the tagging permission this ticket fixes? Not verified as part of this ticket; worth checking, since the same pattern (an authz-aware override existing only in the REST view, not in the shared predicate) may repeat there.
</details>
