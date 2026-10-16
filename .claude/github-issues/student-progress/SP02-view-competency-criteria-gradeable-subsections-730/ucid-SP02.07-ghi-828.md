# [FE] Package the frontend plugin as a Tutor plugin and document the operator install

GitHub: https://github.com/openedx/openedx-core/issues/828 (#828). Depends on #810, #829, and #734.
Cached: 2026-09-22

## User Story

As a site operator, I want to add the CBE Student Progress features to my Open edX instance by installing and enabling a Tutor plugin, in order to get its widget(s) onto the Progress tab without forking or patching the Learning MFE myself.

## Description

The CBE Student Progress widgets live in the frontend package that #810 creates, and they only appear on a site's Progress tab when something installs that package into the Learning MFE image and registers its widgets into the Progress tab plugin slots. This ticket adds the package to tutor-mfe itself, so every Tutor site that runs the Learning MFE gets the widgets by default, with no separate Tutor plugin for the operator to find and install.

<details>
<summary>Context</summary>

- #810 creates the repository, the npm package, the placeholder component this ticket installs, and the continuous integration workflow this ticket adds a job to.
- `openedx/sample-plugin`: `tutor-contrib-sample/tutorsample/plugin.py` is the reference implementation of all three wiring steps, and carries the source comment explaining why the npm install must not be scoped to a single MFE.
- `overhangio/tutor-mfe`: its `README.rst` documents every `mfe-*` patch hook, and `tutormfe/templates/mfe/build/mfe/env.config.jsx` shows where a registered slot configuration is rendered in the generated file and what wraps it.
- A separate, not-yet-filed ticket replaces the placeholder component this ticket registers with the real CBE widgets, editing this same registration and introducing `example.env.config.jsx` for local development.
- This ticket belongs to epic #730.

</details>

## Acceptance Criteria

The deliverable is a change to tutor-mfe's image build and default slot configuration rather than new runtime behavior, so this ticket uses a checklist. Every item is verified on a Tutor environment that has no Tutor plugins enabled beyond tutor-mfe's own dependencies.

- [ ] Building the Learning MFE image with tutor-mfe's default configuration installs the frontend package from #810, and the built Learning MFE registers the package's widgets into `ProgressTabCourseGradeSlot` and `ProgressTabRelatedLinksSlot`.
- [ ] tutor-mfe pins a specific version of the package rather than tracking a moving branch, so rebuilding the image without changing the tutor-mfe version produces the same package build.
- [ ] On a course that has competency criteria, the widgets appear in both Progress tab positions after a standard image build and launch.
- [ ] On a course that has no competency criteria, the Progress tab renders exactly as it does on a site built from the previous tutor-mfe release.
- [ ] At least one other micro-frontend on the same site, for example the Authoring MFE, builds and behaves unchanged.
- [ ] tutor-mfe's changelog entry states that the Learning MFE now includes the CBE Student Progress widgets and names the two Progress tab positions where they appear.

## Open Questions

- **(architect, final review)** Should tutor-mfe give operators a way to leave the widgets out of the Learning MFE build? A site with no competency criteria sees no change on the Progress tab either way, but its Learning MFE image still carries the package. If the answer is yes, add a checklist item covering how the operator turns the widgets off and what the Progress tab looks like afterward.
- **(architect, final review)** #839 adds an operator setting that chooses whether the competency criteria panel sits above the Grades card or replaces it, and #839 places that setting in a separate Tutor plugin, while this ticket ships the widgets through tutor-mfe. Does that setting become a tutor-mfe setting, and is it part of this ticket or of #839?
