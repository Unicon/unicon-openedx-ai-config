# [FE] Bundle the CBE Student Progress widgets with tutor-mfe

GitHub: https://github.com/openedx/openedx-core/issues/828 (#828). Depends on #810, #829, and #734.
Cached: 2026-09-22

## User Story

As a site operator, I want the CBE Student Progress widgets to come with tutor-mfe by default, so that learners see them on the Progress tab without me installing a separate plugin or patching the Learning MFE.

## Description

The CBE Student Progress widgets live in the frontend package that #810 creates, and they only appear on a site's Progress tab when something installs that package into the Learning MFE image and registers its widgets into the Progress tab plugin slots. This ticket adds the package to tutor-mfe itself, so every Tutor site that runs the Learning MFE gets the widgets by default, with no separate Tutor plugin for the operator to find and install.

<details>
<summary>Context</summary>

- #810 creates the repository and the npm package that this ticket adds to tutor-mfe.
- `overhangio/tutor-mfe`: its `README.rst` documents every `mfe-*` patch hook, and `tutormfe/templates/mfe/build/mfe/env.config.jsx` shows where a registered slot configuration is rendered in the generated file and what wraps it.
- #829 replaces #810's generic placeholder component with the two starter CBE widgets and adds `example.env.config.jsx` for local development. This ticket installs the package after #829 and #734 have landed.
- A way for operators to leave the widgets out of the Learning MFE build is a nice-to-have, not a requirement, since the goal is to build CBE into the core rather than bolt it on. Add it only if it takes little effort.

</details>

## Acceptance Criteria

The deliverable is a change to tutor-mfe's image build and default slot configuration rather than new runtime behavior, so this ticket uses a checklist. Every item is verified on a Tutor environment that has no Tutor plugins enabled beyond tutor-mfe's own dependencies.

- [ ] Building the Learning MFE image with tutor-mfe's default configuration installs the frontend package from #810 and registers the slot configuration the package exports, which places the competency criteria panel at the top of the Progress tab's main column.
- [ ] tutor-mfe pins a specific version of the package rather than tracking a moving branch, so rebuilding the image without changing the tutor-mfe version produces the same package build.
- [ ] On a course that has competency criteria, the competency criteria panel appears at the top of the Progress tab's main column after a standard image build and launch.
- [ ] On a course that has no competency criteria, the Progress tab renders exactly as it does on a site built from the previous tutor-mfe release.
- [ ] At least one other micro-frontend on the same site, for example the Authoring MFE, builds and behaves unchanged.
- [ ] tutor-mfe's changelog entry states that the Learning MFE now includes the CBE competency criteria panel on the Progress tab, and names the setting that controls where it goes.
- [ ] tutor-mfe has a site-wide setting that decides where the competency criteria panel goes. In both layouts, the panel appears only in courses that have competency criteria, and courses without criteria show the Progress tab unchanged.
  - "Above": the panel appears above the Course completion and Grades cards.
  - "Replacement", the default: the panel appears in place of both cards.
  - tutor-mfe passes the setting's value to the slot configuration function the package exports (#829), so changing the setting and rebuilding the Learning MFE image changes the value that function receives.
  - tutor-mfe's README lists the setting, its two values, and its default.
  - What the package does with each value is #839's scope. Until #839 ships, both values place the panel above the cards.

## Open Questions

- (implementer) Will tutor-mfe call the slot configuration function the package exports (#829) and pass it the placement setting's value, and will it install and import the package only for the Learning MFE? The package's slot configuration imports `@openedx/frontend-plugin-framework`, which the other MFEs don't necessarily have. If tutor-mfe can't do either, #829 and #839 need a different way to register the widgets.
- (implementer) Who bumps tutor-mfe's pinned package version when later tickets (#839, #743, and others) ship a new package release, and on what cadence?
