# [ARCH] Should the new Competency Management authoring page be built in frontend-app-authoring or as a new MFE?

GitHub: https://github.com/openedx/openedx-core/issues/705 (#705, CLOSED)
Cached: 2026-09-21

## Description

#648 surfaced a placement question that needs its own discussion before frontend work on Competency Management ("Manage & Apply Competencies") can start: should the new authoring page be built as a feature inside the existing `frontend-app-authoring` MFE, or as a new standalone MFE (possibly on `frontend-base`)?

jmakowski1123 raised it directly on #648: "this will spark conversation around implementation details. Namely, should this whole page be a brand new MFE? If so, what are the implications of that?" bradenmacdonald has separately recommended a new MFE on `frontend-base`, citing team velocity and its suitability for small, special-purpose MFEs.

This issue lays out both options with their tradeoffs, then closes with a recommendation for the Working Group to review, push back on, or confirm.

## Acceptance Criteria

This is an architecture spike. The deliverable is a documented decision.

- [ ] Every entry in Open Questions is resolved, with the resolution documented as a comment on this issue.
- [ ] If Option A is confirmed (build inside `frontend-app-authoring`): the module-boundary and feature-folder disciplines below are named as a requirement of the eventual build ticket(s).
- [ ] If Option B is confirmed (new standalone MFE): each default-install requirement (i18n FR/ES, Paragon accessibility, OEP-48 theming, OEP-55 maintainer standard, non-root URI support, `tutor-mfe` deployability, `CORE_MFE_APPS` inclusion) has an owner and rough timeline, or is explicitly deferred with stated rationale.
- [ ] The final decision and rationale are posted as a comment on this Github Issue and #648.

## Open Questions

- Does the Working Group concur with the recommendation below (Option A), or prefer Option B?
- Does the code-cut deadline change which option makes sense here, specifically, would a new standalone MFE let the team bypass that deadline in a way that outweighs the tradeoffs below?
- Should the eventual decision be written up as an ADR, given `frontend-app-authoring` already has an ADR practice, or is the closed issue and its comment thread sufficient?

## Context

No code exists for this page today. Two placement options are on the table, raised on #648's UXD sign-off thread.

### Option A: build inside `frontend-app-authoring`

**Pros**

- Inherits everything a new MFE would have to build from nothing: the build toolchain (`@edx/frontend-build`), routing (`src/index.jsx`), i18n extraction (Makefile), CI (`.github/workflows/validate.yml`), and the React Query data pattern.
- Real, shipped precedent for exactly this shape of feature: `src/taxonomy/` exposes a single `index.ts`, isolates its data layer under `data/` on React Query with zero Redux, and its only import leaving the tree goes through shared `src/generic/` utilities, not another feature's internals. This is a working feature in production, not a hypothetical.
- Automatically satisfies every default-install requirement (i18n FR/ES, Paragon accessibility, OEP-48 theming, OEP-55 maintainer standard, non-root URI support, `tutor-mfe` deployability), since they're already met by the app as a whole. No separate PR into `tutor-mfe`'s `CORE_MFE_APPS` needed.
- Structurally encourages UX consistency with the rest of Studio, since the feature is built with, and reviewed alongside, the same Paragon components and shared patterns the rest of the app uses.
- Doesn't foreclose a future standalone MFE: `frontend-app-authoring`'s own ADR-0002 ("Feature-based Application Organization," status Proposed but universally followed) is designed to let a disciplined feature be pulled out into its own package later with minimal rework.

**Cons**

- Extractability depends on team discipline, not tooling: ADR-0002 isn't enforced by any lint rule, so "stay portable" needs explicit follow-through (see disciplines below), not an automatic guarantee.
- Ties the feature's release cadence to the rest of Studio's authoring MFE, rather than an independent deploy cycle.
- Doesn't offer the "clean-room" velocity of starting fresh with no legacy code to navigate (although this is legacy code we're now pretty familiar with from our prior work on Taxonomies).

If Option A is chosen, these disciplines are what make "stay portable" concrete rather than aspirational:
- Own top-level feature directory, single `index.ts(x)` as the only public surface.
- Own `data/` layer on React Query only. No new Redux slice, ever: the app-wide store is `@deprecated` and can't be lifted out later.
- No reaching into another feature's internals for shared data.
- Own route prefix at the top level (parallel to `/taxonomies`, `/libraries`).
- Own `messages.ts`.

### Option B: new standalone MFE (possibly on `frontend-base`)

**Pros**

- Gives outside forkers a clean separate repo from day one, if the page's hidden complexity (the competency criteria hierarchy is being simplified/obscured in this UI) turns out to need more flexibility than core Studio will offer or if people want to add more competency criteria rules or object type assocations faster than core Studio will adopt them.
- Might have an independent release and deploy cadence from day one.
- `frontend-base` shipped v1.0.1 (2026-07-08, non-prerelease), and its GitHub description no longer says "pre-alpha".
- Matches `frontend-base`'s stated design intent of making small, purpose-built MFEs easier to stand up and operate.

**Cons**

- No scaffolding generator exists for building a new app on `frontend-base` from scratch. The only guide found covers migrating an *existing* app onto it, a roughly 70-step process not designed for greenfield builds.
- Every default-install requirement (i18n FR/ES, Paragon accessibility, OEP-48 theming, OEP-55 maintainer standard, non-root URI support, `tutor-mfe` deployability) has to be built and verified independently, plus a separate PR merged into `tutor-mfe`'s `CORE_MFE_APPS` to become an actual default rather than an opt-in extra. None of this, including the translation work, is otherwise in scope for this feature.
- Bets a net-new, deadline-bound feature on a still-young framework's unproven greenfield path, rather than a pattern (Taxonomy) already proven in production inside authoring.
- A separate deployable has to deliberately re-import Studio's UX consistency; nothing structural forces it to.

### Recommendation

Weighing the above, the recommendation is **Option A: build inside `frontend-app-authoring`**, under the module-boundary disciplines listed. Both options serve the same underlying goal, competency management as a core, default-installed capability rather than an add-on. Option A already is that, on day one. Option B could get there too, but only after clearing the scaffolding and default-install steps listed above: more steps to reach the same end state, not a different or better one. That gap matters for two reasons, not just calendar time: the code-cut deadline is one, assuming it applies the same way regardless of which repo the code lives in (see Open Questions above, since a new MFE bypassing that deadline entirely would remove this reason), and the other is scope. Standing up a new repo's scaffolding and clearing the full default-install checklist (i18n FR/ES, accessibility, theming, the `CORE_MFE_APPS` PR) is not currently part of this feature's planned scope. Option B would add that as unplanned work on top of the feature itself, not something already accounted for, and neither of these two reasons reflects a shortcoming in Option B's architecture.

Absent that time pressure, Option B is arguably the cleaner long-term architecture: a purpose-built app matching `frontend-base`'s stated design intent, with its own release cadence from day one.

**Constraints either option must respect**
- No `.importlinter`/backend-layering impact: pure frontend placement decision.
- Whichever option is chosen, the relevant disciplines/requirements above belong in the eventual build ticket(s) as acceptance criteria.

## Context

- Trigger: `openedx-core` #648. jmakowski1123's and bradenmacdonald's comments.
- Prior art: `frontend-app-authoring/docs/decisions/0002-feature-based-application-organization.rst` (status Proposed, universally followed); `frontend-app-authoring/src/taxonomy/`.
- Default-install requirements: BTR's "Requirements for an MFE" doc; `tutor-mfe`'s `CORE_MFE_APPS` (`tutormfe/plugin.py`).
- For information only: #670 already states a "Repo: frontend-app-authoring, MFE-only" assumption predating this discussion. Updating downstream ticket relationships is handled separately.
- Related: a `wg-frontend` agenda-item (to be filed).
