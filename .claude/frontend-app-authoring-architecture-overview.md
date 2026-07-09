# frontend-app-authoring — Architecture Overview

> Orientation doc for Claude agents in **this** (`openedx-core`) repo who pick up
> tickets with a frontend part. It describes the Open edX authoring micro-frontend so
> you can understand its architecture, look things up in its repo, and design the
> frontend side of a change in line with its conventions.
>
> **The frontend repo is NOT in this workspace.** It lives on disk at:
> **`../frontend-app-authoring`** (a sibling of this repo,
> i.e. `../frontend-app-authoring`). File paths below are relative to that repo's root
> unless they start with `.claude/`. To verify anything here, dispatch a sub-agent into
> that directory (see §10) rather than reading it into the main context. If the repo is not found at that path, just ask the user for its location.
>
> Synthesized from the repo's `README.rst`, its ADRs under `docs/decisions/` and
> `src/editors/decisions/`, `package.json`, and the `src/` layout.
> Companion doc (backend): [architecture-overview.md](.claude/architecture-overview.md).

---

## 1. What this repo is

`frontend-app-authoring` (npm package `@edx/frontend-app-authoring`, formerly
`frontend-app-course-authoring`) is the **React micro-frontend (MFE) that implements
most of Open edX Studio** — the course- and library-**authoring** UI (the CMS). It is
the modern replacement for the server-rendered Studio pages that `openedx-platform`'s CMS
used to serve.

- It is a **standalone single-page app**, not part of `openedx-platform` and not part of
  this repo. It talks to the **CMS REST APIs** that `openedx-platform` exposes.
- **License:** AGPLv3.
- A handful of **legacy Studio pages** still render from `openedx-platform` directly and are
  "rapidly being deprecated"; per-feature `legacy_studio.*` waffle flags in
  `openedx-platform` can re-enable them (e.g. `text_editor`, `video_editor`,
  `problem_editor`, `advanced_settings`, `updates`, `export`, `import`, `files_uploads`,
  `exam_settings`).
- Some authoring features defer to **other IDAs/MFEs**: `edx-exams` (proctoring),
  `frontend-app-discussions` (discussion config), `frontend-app-learning` (the learner
  experience). Don't assume every Studio concern lives in this repo.

### How it relates to `openedx-core`

This MFE is a **consumer of the same backend stack** that `openedx-core` underpins. The
chain is: **this MFE → `openedx-platform` CMS REST APIs → (for libraries/content) the
`content_libraries` app → `openedx_content` (this repo)**. So a content-library feature
you build in `openedx_content` surfaces to authors through this MFE's
`library-authoring` feature. There is **no direct import or code dependency** between the
two repos; the contract is the CMS HTTP API.

## 2. Non-negotiable conventions

These come straight from the ADRs and are the rules a frontend change must follow.

1. **Feature-based organization, not type-based.** `src/` is grouped by *feature*
   (e.g. `course-outline/`, `library-authoring/`), never by code-type top-level buckets
   (`components/`, `actions/`, `reducers/`). Everything a feature owns is co-located in
   its directory. Source: [docs/decisions/0002-feature-based-application-organization.rst](../frontend-app-authoring/docs/decisions/0002-feature-based-application-organization.rst)
   (Status: **Proposed**, but universally followed).
2. **Strict module boundaries.** A feature exposes a public interface via its
   `index.ts(x)`; consumers import **only** from that (`import { X } from './feature'`,
   never `import X from './feature/internal/X'`). No reaching past a child's `index`.
3. **No upward/circular imports.** A feature must not import from its parent or
   grandparents; general-purpose modules must not import from more specific ones. Shared
   code is **promoted up the tree** until it's a sibling of all its consumers.
4. **Data/view separation.** Data logic (API calls, query hooks, or Redux
   slice/thunks/selectors) lives in a `data/` subdirectory; React components sit at the
   feature root (not under a `components/` folder).
5. **New data should use React Query, not Redux.** The Redux store is explicitly
   `@deprecated` (see §5). Don't add new Redux slices; follow the React Query pattern.
6. **i18n everything.** User-facing strings go through `@edx/frontend-platform/i18n`
   `defineMessages` in a feature's `messages.ts`. No hard-coded display strings.
7. **Build on Paragon.** UI is composed from `@openedx/paragon` components and design
   tokens, not bespoke styling, wherever a Paragon component fits.

> Guiding caveat from the ADR itself: *"Following the spirit of these principles is more
> important than following them to the letter."*

## 3. Tech stack & runtime

| Concern | Package(s) | Notes |
|---|---|---|
| MFE runtime | `@edx/frontend-platform` `^8.7.0` | Boot lifecycle (`initialize`, `subscribe`, `APP_READY`), `getConfig`, `getAuthenticatedHttpClient`, `AppProvider`, `PageWrap` |
| Build toolchain | `@openedx/frontend-build` `^14.6.6` | Provides `fedx-scripts` wrapping webpack/jest/dev-server |
| Design system | `@openedx/paragon` `^23.5.0` | Components + theming; `@edx/brand` (aliased to `@openedx/brand-openedx`) for brand assets |
| Extensibility | `@openedx/frontend-plugin-framework` `^1.8.0` | Slot-based UI injection (see §7) |
| Shared chrome | `@edx/frontend-component-header` `^8.2.1`, `@edx/frontend-component-footer` `^14.9.0` | Shared Studio/LMS header & footer |
| UI framework | `react` / `react-dom` `^18.3.1`, TypeScript | New code is `.tsx`/`.ts`; `tsconfig` from `@edx/typescript-config` |
| Routing | `react-router` / `react-router-dom` `6.30.3` | Data-router API (`createBrowserRouter`) |
| Data fetching (preferred) | `@tanstack/react-query` `5.95.2` | The forward direction for server state |
| Global state (legacy) | `@reduxjs/toolkit` `2.11.2`, `react-redux` `7.2.9`, `redux` `4.2.1` | `@deprecated` — being migrated off |
| Search | `meilisearch` `^0.41.0` | Content/library search client |
| Forms | `formik` `2.4.9` + `yup` | Forms & validation |
| Drag & drop | `@dnd-kit/*` | e.g. course-outline reordering |
| Rich text | `tinymce` + `@tinymce/tinymce-react` | The editors subsystem (§6) |
| Tables | `@tanstack/react-table` `^8.21.3` | Headless tables |
| Lint/format | `oxlint` `^1.42.0`, `dprint`, `stylelint` | ESLint replaced by `oxlint` (`--type-aware`) |
| Tests | `jest`, `@testing-library/react` `^16.2.0`, `@testing-library/user-event`, `@testing-library/jest-dom`, `axios-mock-adapter`, `fetch-mock-jest` | No MSW |

**Common commands** (`package.json` scripts, run with `npm`): `dev` (dev server at
`apps.local.openedx.io:2001`, MFE config from `localhost:8000`), `build`
(`fedx-scripts webpack`), `test` (`fedx-scripts jest --coverage`), `test:dev` (watch),
`lint` / `lint:fix`, `types` (`tsc --noEmit`), `i18n_extract`. The recommended dev
environment is **Tutor** (`tutor dev start lms cms mfe`), with the MFE run on the host in
dev mode and CMS reachable at `localhost:18010` / `studio.local.openedx.io`.

## 4. App structure: boot, routing, feature folders

**Boot** ([src/index.jsx](../frontend-app-authoring/src/index.jsx)): `initialize({...})`
from frontend-platform runs setup, then `subscribe(APP_READY, …)` mounts `<App />` via
`createRoot`; `APP_INIT_ERROR` renders `<ErrorPage />`.

**Provider tree** (inside `<App />`):

```
<AppProvider store={initializeStore()} wrapWithRouter={false}>   # frontend-platform
  <ToastProvider>
    <QueryClientProvider client={queryClient}>                    # staleTime 1h
      <RouterProvider router={router} />                          # createBrowserRouter
```

**Routing** ([src/CourseAuthoringRoutes.tsx](../frontend-app-authoring/src/CourseAuthoringRoutes.tsx)):
top-level routes map URL prefixes to feature components, e.g. `/home` & `/libraries` →
`StudioHome`; `/library/:libraryId/*` → `LibraryLayout`; `/course/:courseId/*` →
`CourseAuthoringRoutes` (all course-editing sub-routes); `/course_rerun/:courseId`;
`/taxonomies` & `/taxonomy/:taxonomyId` (gated by `getConfig().ENABLE_TAGGING_TAXONOMY_PAGES`);
component-picker routes. `CourseAuthoringRoutes` maps sub-paths under `/course/:courseId/`
to `CourseOutline`, `CourseUnit`, `AdvancedSettings`, `GradingSettings`, `Certificates`,
`FilesPage`, `VideosPage`, editors, etc., and wraps them in `CourseAuthoringProvider`
([src/CourseAuthoringContext.tsx](../frontend-app-authoring/src/CourseAuthoringContext.tsx))
plus feature context providers (`CourseImportProvider`, `CourseExportProvider`,
`IframeProvider`).

**Feature folder anatomy** (the unit you'll add to / model new work on):

```
src/<feature>/
  index.ts(x)              # public interface — consumers import only from here
  <Feature>.tsx            # root component(s), named semantically
  <sub-concern>/           # nested sub-features, each with their own index
  data/
    api.ts                 # async fns using getAuthenticatedHttpClient(); base URL getConfig().STUDIO_BASE_URL
    apiHooks.ts            # React Query useQuery/useMutation hooks  (React Query features)
    queryKeys.ts           # query-key factories
    slice.ts/thunks.ts/selectors.ts   # RTK  (legacy Redux features only)
  messages.ts              # defineMessages for i18n
  constants.ts
  hooks.ts                 # feature-level custom hooks
  *.test.tsx               # tests co-located with components
```

## 5. State & data layer — two coexisting patterns

The codebase is **mid-migration**. Know which pattern a feature uses before touching it,
and use Pattern B for new work.

**Pattern A — Legacy Redux (deprecated).** [src/store.ts](../frontend-app-authoring/src/store.ts)
defines `DeprecatedReduxState`, explicitly annotated `@deprecated` with a TODO to move to
React Context + React Query. Registered slices include `customPages`, `discussions`,
`assets`, `pagesAndResources`, `studioHome`, `models`, `live`, `courseUpdates`,
`courseOptimizer`, `generic`, `videos`, `courseUnit`, `certificates`. Each such feature's
`data/` has a RTK `slice.ts` plus separate `thunks.ts` and `selectors.ts`.

**Pattern B — React Query (preferred).** Newer features (e.g. `library-authoring`,
`course-outline`) use **only** `@tanstack/react-query`, no Redux slice. Their `data/`
holds: `api.ts` (plain async functions calling `getAuthenticatedHttpClient()` with base
URL `getConfig().STUDIO_BASE_URL`), `apiHooks.ts` (`useQuery`/`useMutation` wrappers),
`queryKeys.ts` (key factories), and feature-specific query/cache files
(e.g. `cacheInvalidation.ts`).

**Backend access is uniform across both:** every request goes through
`getAuthenticatedHttpClient()` (from `@edx/frontend-platform/auth`) against a base URL
read at request time from `getConfig().STUDIO_BASE_URL`. Config values come from
frontend-platform's runtime config (env + the MFE config API), not hard-coded.

## 6. The editors subsystem (`src/editors/`)

A distinct architecture-within-the-app for the **rich content "V2 editors"** (problem,
text/HTML, video, etc.). It matters for any ticket touching content-block editing. Its
ADRs live in [src/editors/decisions/](../frontend-app-authoring/src/editors/decisions/).

- **Why it's separate** (0001): it began as a cross-MFE shared content-editing library
  (intended for the learning MFE, the authoring MFE, and a shared content MFE), so it's
  designed as an embeddable piece rather than app-specific screens.
- **V2 content editors** (0003, Status: *Adopted*, explicitly **interim/incremental**):
  legacy XBlock editing is replaced by MFE redirection. The `Editor` component selects
  the correct editor type from the `xblock id` it receives; `EditorContainer` provides
  shared save/cancel/title UI. **Redux is mandated here** (this subsystem predates the
  app-wide React Query move, so it does **not** follow §2 rule 5).
- **Network request layer** (0004, *Adopted*): all network work flows through a two-level
  thunk chain — `thunkActions/app` → `thunkActions/requests` → `data/services/cms/api`.
  Each request key (in `data/constants/requests`) has a four-state lifecycle
  `[inactive, pending, completed, failed]`; components read status via Redux selectors to
  drive conditional rendering. Example save chain:
  `thunkActions/app:saveBlock` → `thunkActions/requests:saveBlock` → `services/cms/api:saveBlock`.
- **Text editor** (0002, *Accepted*): keeps **TinyMCE v6**, wrapped via
  `@tinymce/tinymce-react` in `TextEditor.jsx` (config in `TextEditor/pluginConfig.js`);
  image upload is an internal TinyMCE extension that opens a modal and `execCommand`s the
  inserted tag.
- **Testability conventions** (0005): `StrictDict`/`keyStore` for safe key access;
  modules **self-import** (`import * as module from './myFile'`) so Jest can spy on their
  own methods; **hook/component separation** with hooks mocked in snapshot tests
  (`mockUseState`, `useCallback`/`useEffect` mocks); `useDispatch` is called in the
  component and passed down, never inside hooks. Paragon, paragon icons, and
  frontend-platform i18n are mocked in `setupTests` (integration tests must `jest.unmock`).
- **Test naming** (0006): three-part names via nested `describe`/`it` (unit → scenario →
  expected behavior); avoid the word "test", prefer "should"; one behavior per test.
- **Feature org within editors** (0007, *Accepted*): same feature-module ("ducks")
  organization as the app-wide ADR 0002.

## 7. Extensibility: plugin slots

[src/plugin-slots/](../frontend-app-authoring/src/plugin-slots/) holds ~16 named slot
directories (e.g. `CourseOutlineHeaderActionsSlot`, `CourseAuthoringUnitSidebarSlot`,
`StudioFooterSlot`, `PageBannerSlot`). These use `@openedx/frontend-plugin-framework` to
let operators/plugins inject UI at defined extension points **without forking the MFE**.
When a feature needs operator-customizable UI, add a slot rather than a hard-coded hook.

## 8. How it connects to the backend

- **Transport:** REST over `getAuthenticatedHttpClient()` to `getConfig().STUDIO_BASE_URL`
  (the CMS). JWT auth is handled by frontend-platform.
- **Libraries & content:** `library-authoring` and content features ultimately exercise
  `openedx-platform`'s `content_libraries` app, which is backed by **`openedx_content`** in
  this repo. A new content capability typically needs: a model/API change in
  `openedx_content` → a CMS REST endpoint in `content_libraries` → an `api.ts` +
  `apiHooks.ts` + UI in the matching MFE feature.
- **Tagging/taxonomies:** the `taxonomy` and `content-tags-drawer` features back onto
  `openedx-platform`'s `content_tagging`, which builds on **`openedx_tagging`** here.
- **Search:** content search uses Meilisearch via the `search-manager`/`search-modal`
  features.

When designing a frontend change, trace the full chain and call out which layer each
piece of work lands in. The MFE side is almost always: a `data/api.ts` function, a React
Query hook, and feature UI + i18n + tests.

## 9. Where to read things (ADR map)

| Folder (in the frontend repo) | What's in it |
|---|---|
| [docs/decisions/](../frontend-app-authoring/docs/decisions/) | Repo-wide: 0001 ADR process (*Accepted*); 0002 feature-based organization (*Proposed*). |
| [src/editors/decisions/](../frontend-app-authoring/src/editors/decisions/) | Editors subsystem: 0001 library purpose, 0002 text editor/TinyMCE (*Accepted*), 0003 V2 content editors (*Adopted*, interim), 0004 network request layer (*Adopted*), 0005 testability, 0006 test names, 0007 feature org (*Accepted*). |
| [README.rst](../frontend-app-authoring/README.rst) | What the app is, install/dev/test, Tutor setup, legacy-page waffle flags. |
| [docs/how_tos/](../frontend-app-authoring/docs/how_tos/) | `i18n.rst`, `override-external-urls.rst`. |

**Always check an ADR's `Status:` line before trusting it as current; but understand sometimes the status line is outdated.** Notable: ADR 0002
is *Proposed* (yet followed everywhere); editors ADR 0003 is *Adopted* but explicitly
interim/incremental; none of the editors ADRs are superseded.

## 10. How to investigate the frontend repo from here

The frontend repo is large and **outside this workspace**. Keep the main context lean:

- Dispatch an `Explore` (Haiku) sub-agent for "where is X / does X exist" location work,
  pointed at `/Users/jesperhodge/openedx/frontend-app-authoring`.
- Dispatch a `general-purpose` or `Explore` sub-agent on **Sonnet** for reading-and-
  reasoning (reading a feature's `data/` to mirror its pattern, confirming an API shape).
- Read ADRs and `README.rst` in a sub-agent, not inline. Pass `model` explicitly on every
  dispatch (per this repo's CLAUDE.md context-hygiene rules).
- Read into the main context only the few files a frontend design actually hinges on.

---

## 11. Glossary — wider Open edX frontend context

- **MFE (micro-frontend)** — a standalone React SPA in the Open edX ecosystem, built on
  `@edx/frontend-platform`, that replaces a slice of the legacy server-rendered UI. Each
  MFE is its own repo/deployable.
- **frontend-platform** — the shared MFE runtime: app initialization lifecycle, JWT auth
  (`getAuthenticatedHttpClient`), runtime config (`getConfig` + MFE config API), i18n,
  logging, analytics, and React glue (`AppProvider`, `PageWrap`).
- **Paragon** (`@openedx/paragon`) — the Open edX React design system (components + theme
  tokens). The default source of UI building blocks.
- **frontend-plugin-framework** — the slot/plugin system letting operators inject or
  replace UI at named slots without forking an MFE.
- **fedx-scripts** — the CLI from `@openedx/frontend-build` that wraps webpack/jest/
  dev-server with Open edX defaults; the `npm` scripts call it.
- **Tutor** — the Docker-based Open edX deployment/dev tool; `tutor dev start lms cms mfe`
  brings up the backend + MFEs for local development.
- **Studio / CMS** — the authoring application (this MFE is its frontend) vs the **LMS**
  (learner experience, served by `frontend-app-learning`).
- **XBlock** — Open edX's plugin framework for course-content components; the editors
  subsystem provides the React editing UI for XBlock content types.
- **Legacy Studio pages** — server-rendered CMS pages this MFE is replacing; still
  toggleable per-feature via `legacy_studio.*` waffle flags in `openedx-platform`.
