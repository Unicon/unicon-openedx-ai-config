This is a sample review written to test the prepare-pr-review skill. It is not a real review of this PR.

# Review of openedx/frontend-app-authoring#3246

**Ready to merge: with fixes.** The permission gating works, but the "Learn More" link has no test and an invalid upstream key would crash the unit page.

## Inputs

- Repository: openedx/frontend-app-authoring
- PR: https://github.com/openedx/frontend-app-authoring/pull/3246
- Base SHA: 87cba01fffc4a7648b7f8c27c688135d51513f1a
- Head SHA: 6c660364fda5a031bef163eef038ab69e68d01f6
- Ticket: openedx/openedx-authz#450 (no formal acceptance criteria; the PR description's behavior list is used)

## Findings

### Gap

- `src/course-unit/CourseUnit.tsx:304-308`: No test asserts that the "Learn More" link still renders for a user without `canViewLibrary`, so the third criterion has no test that fails if the link is lost.

### Question

- `src/course-unit/CourseUnit.tsx:223-231`: The permission query is enabled by `upstreamRef`, but the alert at line 292 is shown when `upstreamLink` is set, so can a unit have an `upstreamLink` without an `upstreamRef` and always see plain text?

### Nit

- `src/course-unit/CourseUnit.tsx:300-303`: The same `FormattedMessage` is written in both ternary branches, and it could be rendered once and wrapped in `Alert.Link` only when the user can view the library.

### Outside the changed files

- `src/generic/key-utils.ts:51-57`: `getLibraryId` throws `Invalid usageKey` for a key that is not `lb`, `lib-collection`, or `lct`, and the PR now calls it during render at `src/course-unit/CourseUnit.tsx:224`, so a malformed `upstreamRef` crashes the whole unit page.
