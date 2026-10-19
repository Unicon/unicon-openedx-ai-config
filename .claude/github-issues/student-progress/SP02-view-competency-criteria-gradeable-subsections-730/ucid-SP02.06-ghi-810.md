# [FE] Create the Open edX frontend plugin repository and its package skeleton

GitHub: https://github.com/openedx/openedx-core/issues/810 (#810, OPEN)
Cached: 2026-09-22

## User Story

As the developer of the CBE Student Progress plugin, I want a repository to serve as a starting point for an Open edX frontend plugin package, in order to add plugin widgets to it without first solving repository standards, packaging, and continuous integration.

## Description

This ticket builds the repository that will hold a frontend plugin that adds competency progress information to the learner Progress tab in the Learning micro-frontend. It creates the repository, the package skeleton, and the build, including one generic placeholder component with no CBE-specific content, used later to prove the plugin install path before any real widget exists. It registers nothing into any plugin slot itself. The real CBE widgets are a separate ticket, #829, and #828 adds the package to tutor-mfe.

## Acceptance Criteria

- [ ] The repository exists, and the Open Question below about where it lives and who maintains it is answered, with the answer recorded as a comment on this issue.
- [ ] It carries the standard Open edX repository files: `LICENSE` (AGPL-3.0), `README.rst`, `CHANGELOG.rst`, `CODE_OF_CONDUCT.md`, `openedx.yaml`, and the standard issue templates.
- [ ] An npm package sits at the repository root.
- [ ] `npm install` run against a git reference to the repository, on a machine that has never built it before, produces a package whose build output is populated rather than empty.
- [ ] The package declares React and its companion libraries as peer dependencies, so a consuming micro-frontend resolves them to its own copies rather than to nested duplicates.
- [ ] The package exports at least one component, and a test covering that component passes.
- [ ] Continuous integration runs lint, tests, and the build on a proposed change, and reports a pass or fail result.
- [ ] A change that breaks the build or the test reports a failure rather than passing silently.
- [ ] The README states what the package is for and how to build and test it locally.


<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done; everything below exists to save the implementer some thinking.

### In short

**What to copy from.** `openedx/sample-plugin` is a worked example of every major Open edX plugin interface, and its `frontend-plugin-sample/` directory is the closest prior art for this package. That directory is five files: a package manifest, a re-export barrel, one component, and the two npm configuration files. Copying its manifest and configuration files, rather than deriving them, is the fastest correct route.

**Where the npm package sits, and why it sits at the repository root.** The package is installed from a git reference rather than from a package registry, and npm installs whatever package sits at the repository root, so the package has to be at the root. This is the one place where the layout is forced rather than chosen, and it is the opposite of how `openedx/sample-plugin` arranges itself, because that repository publishes to registries and so never needs a git install to work.

**Why the package manifest needs a `prepare` script and not only a `build` script.** What a consumer actually uses is compiled JavaScript in `dist/`, which is built rather than committed. When npm installs a dependency from a git URL it clones the repository, installs that package's development dependencies, runs its `prepare` script, and only then packs the result. A package with a `build` script but no `prepare` script therefore installs with an empty `dist/`, and any import of it resolves to nothing, with no error that points at the cause. This is why the checklist tests an install against a git reference rather than only testing that `npm run build` works locally.

**Why React and its companions must be peer dependencies rather than regular ones.** React libraries hand data down through a context, which is a JavaScript object with its own identity. If this package listed React, Paragon, `@edx/frontend-platform`, or `react-router-dom` as regular dependencies, npm would install second copies nested underneath it. Those copies would carry their own separate and empty contexts, and any hook reading a context would come back with nothing, with no error of any kind. Declaring each as a peer dependency at `"*"` is what makes npm resolve to the single copy the host micro-frontend already has.

**Why the package entry point must do no work when it is imported.** The Learning micro-frontend's configuration imports this package when the micro-frontend starts, before any Progress tab renders. Keep the entry point a re-export barrel with no side effects.

### Implementation specifics

- **Repository root.** `package.json`, `src/`, `.npmrc`, `.nvmrc`, plus `LICENSE`, `README.rst`, `CHANGELOG.rst`, `CODE_OF_CONDUCT.md`, `openedx.yaml`, and `.github/`. Copy `.npmrc` and `.nvmrc` unchanged from `openedx/sample-plugin`: its `.npmrc` sets a registry cooling-off period and its `.nvmrc` pins the Node version.
- **Package manifest.** `main` pointing at `dist/index.js`, `files` limited to `["dist"]`, a `build` script running `fedx-scripts babel src --out-dir dist --source-maps --ignore **/*.test.jsx,**/*.test.js` as `openedx/sample-plugin` does, and a `prepare` script running `npm run build`.
- **Dependencies.** `@edx/frontend-platform`, `@openedx/paragon`, `react`, and `react-router-dom` as peer dependencies, every one at `"*"`. No regular dependencies. `@openedx/frontend-build` as the only development dependency, since npm installs development dependencies every time it builds a git dependency, so anything added here is paid for on every install.
- **Entry point.** `src/index.jsx` re-exports named components and performs no work at import time.
- **The component this ticket ships.** Name it `PlaceholderWidget` and make it a Paragon `Card` with static text, accepting no required props. One trivial component is enough to give the build and the test something real to act on, and #829 replaces it with the starter CBE widgets. Because a plugin slot passes no props, `PlaceholderWidget` must not require any either.
- **Continuous integration.** A workflow that runs lint, Jest through `@openedx/frontend-build`, and the build on pull requests.
- **Publishing is out of scope.** Nothing is published to the npm registry. Consumers install from a git reference, which is an established pattern in the Open edX organization: `openedx/frontend-plugin-aspects` is configured for publishing and has tagged releases, but has never been published, and is consumed from git. Give the package an unscoped name for now; adding a scope, if it is ever published, is a rename rather than a redesign.
- **Out of scope, in the widgets ticket.** Plugin slot registration, the example configuration file, the local development loop against a `frontend-app-learning` checkout, and every competency-specific component. This ticket names no plugin slot.
- **Out of scope.** Adding the package to tutor-mfe, which #828 does.

</details>

<details>
<summary>Files to create and modify</summary>

This ticket creates a new repository and modifies no file in any existing repository, so there is no table of modified files. Paths are relative to the new repository's root.

**New files**

| File | Purpose |
| --- | --- |
| `package.json` | The npm package manifest at the repository root, declaring `main`, `files`, the `build` and `prepare` scripts, and peer dependencies only. |
| `.npmrc` | Copied unchanged from `openedx/sample-plugin`; it sets the registry cooling-off period. |
| `.nvmrc` | Pins the Node version used to build the package. |
| `src/index.jsx` | The side-effect-free barrel, re-exporting the package's components as named exports. |
| `src/PlaceholderWidget.jsx` and its test | The generic placeholder component, replaced by #829's starter CBE widgets. |
| `README.rst` | What the package is for, and how to build and test it locally. |
| `LICENSE` | AGPL-3.0, matching Open edX frontend repositories. |
| `CHANGELOG.rst` | Version history. |
| `CODE_OF_CONDUCT.md` | Required by the Open edX repository standard. |
| `openedx.yaml` | Repository metadata, required by the Open edX repository standard. |
| `.github/ISSUE_TEMPLATE/` | The standard Open edX issue templates. |
| `.github/workflows/ci.yml` | Lints, tests, and builds the package on pull requests. |

</details>

<details>
<summary>Context</summary>

- `openedx/sample-plugin` is the reference implementation to copy from: its `frontend-plugin-sample/` directory is the shape of the manifest, the barrel, and the build script.
- `openedx/frontend-plugin-aspects` is prior art for an Open edX plugin package consumed from a git reference rather than from the npm registry.
- The widgets ticket adds the plugin widgets and the slot configuration to this package.
- #828 adds this package to tutor-mfe after #829 and #734 have landed.
- This ticket belongs to epic #730.

</details>

## Open Questions

- **[BLOCKING]** Where does this repository live, and who is its long-term maintainer? Unicon is building the plugin but cannot commit to being its long-term maintainer, so whichever option is chosen has to name someone who will be.

| Option | What has to happen before work can start | What it costs later |
| --- | --- | --- |
| Create the repository in the `openedx` organization now. | A maintainer has to volunteer. Creating the repository means filing a "Systems Request - Miscellaneous" issue in `openedx/axim-engineering`, whose Reasoning field requires naming a maintainer, and that person then comments on the request to confirm. Work cannot start until such a person volunteers. | Nothing. This option reaches the desired end state directly, and the package can eventually publish under the `@openedx` npm scope, which Axim administers and which is restricted to members of the Open edX npm organization. |
| Create the repository in a Unicon-owned organization now and transfer it to `openedx` once a maintainer volunteers. | Nothing. Work can start immediately. | A transfer to `openedx`, plus a scope-only npm rename. Because `@openedx` npm scope access is restricted to Open edX npm organization members, this package cannot pre-claim an `@openedx/...` name; it would publish under Unicon's own scope until it transfers. Axim has a documented migration process for that rename, so the rename is a routine cost rather than a one-off problem. |

A plugin does not have to live in the `openedx` organization to be consumed through plugin slots: `@opencraft/frontend-plugin-sandbox` and `@edunext/frontend-slot-footer` are both published and consumed this way from organizations outside `openedx`.
