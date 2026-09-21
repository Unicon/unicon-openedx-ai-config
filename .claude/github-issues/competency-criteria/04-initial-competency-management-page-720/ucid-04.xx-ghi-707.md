# [FE] Guard the Competency Management route by taxonomy type (redirect non-Competency taxonomies)

GitHub: https://github.com/openedx/openedx-core/issues/707 (#707, OPEN)
Cached: 2026-09-21

## Use Case

As a user who reaches the Competency Management page's URL for a taxonomy that is not a Competency type (a typed URL or a stale link), I want to be taken to where I can actually view that taxonomy instead of a competency page that doesn't apply to it, so that I'm not stranded on an irrelevant screen.

## Acceptance Criteria

Frontend/QA-testable.

    Scenario: A Competency taxonomy renders the page
      Given a Competency-type taxonomy
      When a user opens /taxonomy/:taxonomyId/competencies for it
      Then the Competency Management page renders normally

    Scenario: A non-Competency taxonomy is redirected
      Given a taxonomy that is not a Competency type
      When a user opens /taxonomy/:taxonomyId/competencies for it
      Then they are redirected to that taxonomy's detail/editing page (/taxonomy/:taxonomyId)
      And the Competency Management page is not shown

    Scenario: No flash while the type is resolving
      Given the taxonomy's type has not yet loaded
      When the route is entered
      Then the same loading spinner the taxonomy detail page uses is shown
      And neither the competency page nor the redirect fires until the type is known

    Scenario: An inaccessible or missing taxonomy is not redirected
      Given a taxonomy id that does not exist or that the user cannot access
      When a user opens /taxonomy/:taxonomyId/competencies for it
      Then the same error state the taxonomy detail page shows for that id is shown
      And no redirect to the taxonomy detail page occurs

    Scenario: Redirect does not trap the back button
      Given a user was redirected away from the competency route
      When they use the browser back button
      Then they are not bounced back into an immediate redirect loop

## Description

**Current state**

#680 builds the Competency Management page at `/taxonomy/:taxonomyId/competencies`, which is only meaningful for Competency-type taxonomies. Nothing prevents a user from reaching that route with a non-Competency taxonomy id, whether by a hand-typed URL or a stale bookmark. A taxonomy's type comes from the taxonomy-type field #616 surfaces on the frontend, backed by the backend type plumbing (#618/#630).

The sibling taxonomy-detail page already establishes the pattern this guard extends. `TaxonomyDetailPage.jsx` fetches with `useTaxonomyDetails(taxonomyId)` and gates on its flags in a fixed order: `if (!isFetched) return <Loading />;` (line 35-37), then `if (isError || !taxonomy) return <ConnectionErrorAlert />;` (line 39-41), then it renders. `Loading` is the shared component at `src/generic/Loading.tsx`: a Paragon `Spinner` centered in a full-viewport-height flex container, with a translated "Loading..." screen-reader label.

**Requested change**

On entering the `/taxonomy/:taxonomyId/competencies` route, resolve the taxonomy's type:

- If it is a **Competency** taxonomy, render #680's page as normal.
- If it is **not**, **redirect** the user to where they can view that taxonomy — the taxonomy detail / editing page (`/taxonomy/:taxonomyId`).
- While the type is still resolving, render the shared `Loading` spinner, the same one `TaxonomyDetailPage.jsx` shows for its own fetch. Do not flash the competency page before redirecting, and do not redirect before the type is known.

No dedicated error page — this is a silent, immediate redirect.

<details>
<summary>Out of scope</summary>

- Building the Competency Management page and its competency tree (#680).
- The "Apply Competencies" entry point (#663) and the "Import Competency Framework" button (#706).
- The taxonomy-type field itself and its backend plumbing: the frontend field is #616, the backend that produces the type is #618/#630. This ticket only reads the type, it doesn't build it.
- Behavior for a taxonomy id that does not exist or the user cannot access. That is an error case, not a redirect case, and it reuses whatever the taxonomy-detail page already does for the same failure.
- Any change to the shared `Loading` component or to `useTaxonomyDetails`.
</details>
<details>
<summary>Technical Notes</summary>

### Files to Modify

| File | Nature |
| --- | --- |
| `src/taxonomy/competency-management/CompetencyManagementPage.tsx` (from #680) | Add the taxonomy-type guard at the page entry: resolve the taxonomy's type, render the page for a Competency taxonomy, otherwise redirect. Alternatively wrap the route (confirm placement with #680). |
| the taxonomy route config (if the guard is a route wrapper rather than in-page) | Only if the guard is implemented as a route-level element rather than inside the page component. |
| co-located RTL tests | competency → renders; non-competency → redirects to `/taxonomy/:taxonomyId`; unfetched → `Loading`; errored/inaccessible id → error state, not a redirect; no back-button loop. |

### Implementation Notes

Resolve the taxonomy for `:taxonomyId` via the existing taxonomy-detail query (`useTaxonomyDetails` or equivalent) and read its type using #616's predicate.

Reuse the gate ladder `TaxonomyDetailPage.jsx` already uses, in the same order, and insert the type check as a fourth rung:

1. `!isFetched` → `return <Loading />`, importing the shared `Loading` from `src/generic/Loading.tsx` exactly as `TaxonomyDetailPage.jsx:13` does. Do not write a new spinner, do not inline a Paragon `Spinner`, and do not reach for `LoadingSpinner` (the named export, which is the bare inline spinner for small in-page regions). The default export gives the full-page centered treatment this route needs, and reusing it keeps the competency route visually identical to the detail page during load, which matters because the guard's whole job is to be invisible when it passes.
2. `isError || !taxonomy` → the same error treatment the detail page gives that case, so a missing or forbidden id behaves consistently across both routes. Keep this rung ahead of the type check: an errored query has no type, and treating "no type" as "not a Competency" would silently redirect a broken fetch instead of reporting it.
3. Not a Competency type → `<Navigate to={`/taxonomy/${taxonomyId}`} replace />`. `replace` is required so the back button does not bounce into a redirect loop.
4. Otherwise render #680's page.

### Example Resolution Prompt

> In `frontend-app-authoring`, add a taxonomy-type guard to the Competency Management route `/taxonomy/:taxonomyId/competencies` (the page built by #680). At the page entry (or a route wrapper — match #680's structure), resolve the taxonomy via the existing taxonomy-detail query (`useTaxonomyDetails` or equivalent) and check its type using the predicate #616 introduces (`isCompetencyTaxonomy`-style; confirm its actual name). Mirror the gate ladder in `src/taxonomy/taxonomy-detail/TaxonomyDetailPage.jsx:35-41` in the same order: while `!isFetched`, return the shared `<Loading />` from `src/generic/Loading.tsx` (the default export, the full-page centered spinner, imported the same way `TaxonomyDetailPage.jsx:13` imports it, not a new spinner and not the `LoadingSpinner` named export); then on `isError || !taxonomy`, show the same error treatment the detail page shows, keeping this ahead of the type check so a failed fetch is reported rather than silently redirected; then, if it is a Competency taxonomy, render #680's page; otherwise redirect with `<Navigate to={`/taxonomy/${taxonomyId}`} replace />` (the taxonomy detail/editing page; confirm this is the intended destination). No error page for the type mismatch itself; that redirect is silent and immediate. Add RTL tests: a Competency taxonomy renders the page, a non-Competency taxonomy redirects to `/taxonomy/:taxonomyId` without showing the page, an unfetched query renders `Loading` and neither the page nor a redirect, an errored id shows the error state rather than redirecting, and the redirect uses `replace` so there's no back-button loop.

**Prerequisite:** #618 (with its sibling #630), the backend taxonomy-type plumbing that supplies the type this guard checks. The guard has nothing to read until the type is a real value on the taxonomy-detail response.

**Can be built alongside #616.** #616 surfaces that same type on the frontend `TaxonomyData` and shares #618 as its prerequisite, so it is not a blocker for this ticket, it is a peer. Both consume #618's field. Coordinate on the field name and the Competency predicate's name so the two land compatibly, rather than sequencing this behind #616. #680 provides the page and route this guard wraps. **Related:** #663 (the entry point, only surfaced for Competency taxonomies, so normal navigation will not reach here for a non-Competency taxonomy; this guard covers direct or stale URLs).
</details>
