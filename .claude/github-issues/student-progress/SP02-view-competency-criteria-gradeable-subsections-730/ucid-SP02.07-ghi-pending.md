# [FE] Package the frontend plugin as a Tutor plugin and document the operator install

GitHub: not yet filed. Depends on #810.
Cached: 2026-09-22

## User Story

As a site operator, I want to add this frontend plugin to my site by installing and enabling a Tutor plugin, in order to get its widget onto the Progress tab without forking or patching the Learning MFE myself.

## Acceptance Criteria

The deliverable is packaging and documentation rather than new runtime behavior, so this ticket uses a delivery checklist instead of Given/When/Then scenarios. Every item is verified on a Tutor environment. Nothing in this ticket names competency-based education: it installs the generic placeholder component #810 ships, not any CBE-specific widget.

- [ ] A Tutor plugin exists in the subdirectory #810 reserves for it, and enabling it installs the frontend package into the Learning MFE image and registers #810's placeholder component into each of the two Progress tab slots.
- [ ] An operator with no prior knowledge of the plugin, starting from a clean Tutor environment and following only the repository's installation instructions, reaches a successfully built Learning MFE image with the placeholder visible in both positions on a course's Progress tab.
- [ ] The install pins a specific version of the frontend package rather than tracking a moving branch, and rebuilding the image later without changing that version produces the same plugin build.
- [ ] With the plugin installed but not enabled, the Progress tab renders exactly as it does on a site where the plugin is not present at all.
- [ ] Disabling the plugin and rebuilding the Learning MFE image returns the Progress tab to exactly what it showed beforehand.
- [ ] At least one other micro-frontend on the same site, for example the Authoring MFE, builds and behaves unchanged.
- [ ] The README documents the install, enable, and image rebuild steps, and states plainly that the rebuild is required, that it affects every micro-frontend image, and that a git-reference install rebuilds the JavaScript package from source on each build.
- [ ] Continuous integration lints and installs the Tutor plugin, alongside the JavaScript job #810 creates.

## Description

An operator adds this plugin to their site by installing a Tutor plugin that puts the frontend package into their Learning MFE image and registers its slot configuration. The repository, the frontend package, and the placeholder component all come from #810. This ticket proves the whole install-and-render path end to end using that placeholder, before any CBE-specific widget exists to install. A separate, not-yet-filed ticket replaces the placeholder with the real competency progress widgets, editing the registration this ticket creates rather than writing a new one.

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done; everything below exists to save the implementer some thinking.

### In short

**What this ticket delivers.** #810 produces an npm package containing one generic placeholder component. This ticket produces the Tutor plugin that puts it into an operator's running site. The plugin is a small Python package that does three things to an operator's build: it appends an `npm install` of the package's git reference to the MFE image build, it adds an import of that package to `env.config.jsx`, the shared JavaScript configuration file every MFE reads, and it registers the placeholder component into each of the two Progress tab slots, scoped to the Learning MFE. Reading this ticket needs no knowledge of competency-based education: the component is an opaque, prop-less React component to the code written here, and stays that way until a later ticket swaps it for the real widgets.

**Why the npm install cannot be scoped to the Learning MFE, even though only that MFE uses it.** Tutor renders `env.config.jsx` once and copies the same file into every MFE's image. An import statement placed at the top of that file therefore has to resolve in every MFE's `node_modules`, or those other MFE builds fail. That is why the install step uses the unscoped `mfe-dockerfile-post-npm-install` patch rather than its `-learning` variant, and why `openedx/sample-plugin` carries a source comment warning about exactly this. Tutor's own documentation describes an alternative that would allow a scoped install, a dynamic import inside a per-MFE patch, but its failure mode is far worse: the generated configuration file wraps all of its work in a single `try` and `catch`, so one failed dynamic import discards every plugin's slot registration for that MFE, including registrations belonging to other vendors, and leaves nothing behind but one console line. The unscoped install fails loudly at image build time instead. Its honest cost is that every MFE image build runs one extra npm install and grows accordingly, which belongs in the operator documentation. No other MFE registers the widget in any slot, so nothing renders anywhere else.

**How the registration is written so later work can extend it, not replace it.** A later ticket will register two real widgets in place of this one placeholder, and it will also give operators a choice between two different presentations for the main-column slot. Write this ticket's registration as data: a mapping from slot id to a list of configuration strings, fed to Tutor's plugin-slot filter by a loop, rather than one inline call. That later ticket then edits the entries in this mapping instead of restructuring the loop that reads it. For the same reason, this ticket adds no Tutor settings at all, so an operator who installs the plugin finds no configuration keys that do nothing yet.

**What the operator documentation has to cover.** The plugin is installed from a git reference and is not published to PyPI or npm, so the install instructions are not the usual one-liner and are the most likely thing for a reader to get wrong. The documentation needs the pip install command with its subdirectory fragment, the Tutor enable command, and the image rebuild step, along with a plain statement that the rebuild is required and affects every MFE image. It also needs to say that installing from a git reference rebuilds the JavaScript package from source during each image build, since that is a real and visible cost that a reader will otherwise assume is a hang.

### Implementation specifics

- **Python package layout.** `tutor-contrib-<repository-name>/` in the repository #810 creates, containing `pyproject.toml`, `<module-name>/__init__.py`, `<module-name>/__about__.py`, and `<module-name>/plugin.py`. Follow `openedx/sample-plugin`'s convention of `tutor-contrib-sample` paired with a `tutorsample` module: name both after the repository's own name once #810's Open Question about repository naming and location is settled. Register the plugin through a `tutor.plugin.v1` entry point.
- **Guarded import.** Import `tutormfe.hooks` inside `try`/`except ImportError`, as `openedx/sample-plugin` does, so the plugin degrades rather than crashing when `tutor-mfe` is not installed.
- **The two Tutor patches.** Use `mfe-dockerfile-post-npm-install` for the `RUN npm install` line and `mfe-env-config-buildtime-imports` for the ES import, both in their unscoped form. Do not reach for the `-learning` suffixed variants: there is no `-learning` variant of the imports patch, and Tutor's patch catalog states that imports are available there only if the package was installed for all MFEs.
- **The install line.** `RUN npm install <git reference to this repository at a pinned tag or commit>`. Pin it: a moving branch reference makes an operator's image build unreproducible. If the per-image build cost proves unacceptable later, the cheaper alternative is attaching a packed tarball to a GitHub release and installing from that URL, which skips the clone and the rebuild entirely.
- **Slot registration.** `tutormfe.hooks.PLUGIN_SLOTS.add_item(("learning", <slot id>, <jsx string>))` for `org.openedx.frontend.learning.progress_tab_course_grade.v1` and `org.openedx.frontend.learning.progress_tab_related_links.v1`, both pointing at the same imported placeholder component with two distinct widget ids, for example `demo_widget_main_column` and `demo_widget_sidebar`. Tutor renders each of these as an `addPlugins` call inside a block guarded by the MFE's name, so the registration applies to the Learning MFE only, even though the file itself is shared.
- **Widget configuration.** Each JSX string is a `PLUGIN_OPERATIONS.Insert` whose widget object carries its `id`, `type: DIRECT_PLUGIN`, `priority: 20`, and `RenderWidget` set to the imported placeholder component. `DIRECT_PLUGIN` and `PLUGIN_OPERATIONS` are already in scope in the rendered configuration file, so the JSX string uses them without an additional import patch. Priority 20 places the widget above the slot's stock content, which is itself a widget at priority 50. Leave `keepDefault` at its default of true. Do not set `errorFallbackComponent`: #810 ships no error fallback, and adding one is part of the later ticket that swaps in the real widgets.
- **No example configuration file yet.** Unlike the registration a later ticket will build on top of this one, this ticket writes its JSX directly in `plugin.py`; there is no separate `example.env.config.jsx` to keep it in sync with, since nothing outside Tutor consumes this registration yet. The later ticket introduces that file, once local, Tutor-free development of the real widgets becomes the priority.
- **Operator documentation.** In the repository README: `pip install "git+https://github.com/<org>/<repo>.git@<tag>#subdirectory=tutor-contrib-<repository-name>"`, then `tutor plugins enable <plugin-name>`, then `tutor images build mfe` and a relaunch.
- **Verification on a clean environment.** Beyond the Progress tab itself, open at least one other MFE on the same site, for example the Authoring MFE, and confirm that it builds and behaves unchanged. That is the checklist item the unscoped install is most likely to violate if something in the package's entry point is not import-safe.
- **Continuous integration.** Add a Python job to the existing workflow to lint and install the Tutor plugin, alongside the JavaScript job #810 creates.
- **Forward-looking risk.** The ecosystem is migrating from `env.config.jsx` and `@openedx/frontend-plugin-framework` to `@openedx/frontend-base`, which configures applications through `site.config.tsx` instead. `frontend-app-learning` is firmly on the current model, so this wiring is correct today, but a later upstream migration of that MFE would force the wiring, though not the React components, to be redone. `openedx/frontend-app-notifications` is the worked example of a package that maintains both.
- **A later optimization, deliberately not taken now.** Installing only into the Learning MFE image, through a per-MFE dynamic import, would remove the cost this ticket imposes on every other MFE image build. Before attempting it, verify what a webpack build does when a package named in a literal dynamic import is absent from that MFE's `node_modules`: the configuration file is shared across every MFE build, and the answer determines whether the approach works at all.

</details>

<details>
<summary>Files to create and modify</summary>

Paths are relative to the root of the repository created in #810.

**New files**

| File | Purpose |
| --- | --- |
| `tutor-contrib-<repository-name>/pyproject.toml` | Python package metadata and the `tutor.plugin.v1` entry point. |
| `tutor-contrib-<repository-name>/<module-name>/__init__.py` | Package marker. |
| `tutor-contrib-<repository-name>/<module-name>/__about__.py` | Package version. |
| `tutor-contrib-<repository-name>/<module-name>/plugin.py` | The two Tutor patches and both slot registrations, pointing at #810's placeholder component. |

**Modified files**

| File | Nature of modification |
| --- | --- |
| `README.rst` | Add the operator install, enable, and image rebuild instructions. |
| `.github/workflows/ci.yml` | Add a Python job that lints and installs the Tutor plugin. |
| `CHANGELOG.rst` | Record the addition of the Tutor plugin. |

</details>

<details>
<summary>Context</summary>

- #810 creates the repository, the npm package, the placeholder component this ticket installs, and the continuous integration workflow this ticket adds a job to.
- `openedx/sample-plugin`: `tutor-contrib-sample/tutorsample/plugin.py` is the reference implementation of all three wiring steps, and carries the source comment explaining why the npm install must not be scoped to a single MFE.
- `overhangio/tutor-mfe`: its `README.rst` documents every `mfe-*` patch hook, and `tutormfe/templates/mfe/build/mfe/env.config.jsx` shows where a registered slot configuration is rendered in the generated file and what wraps it.
- A separate, not-yet-filed ticket replaces the placeholder component this ticket registers with the real CBE widgets, editing this same registration and introducing `example.env.config.jsx` for local development.
- This ticket belongs to epic #730.

</details>

## Open Questions

- **Non-blocking, owned by the implementer together with the program leads.** Where does the operator-facing install documentation live: the plugin repository's own README only, or also a page on the Open edX documentation site? An operator who does not already know this plugin exists will not find a README in an unfamiliar repository, so the answer affects whether the install is discoverable at all. The Acceptance Criteria above hold either way, since both places are "the repository's installation instructions" or a link from them.
- **Non-blocking, owned by the implementer.** Which Learning MFE versions does the plugin declare support for? The two extension points it targets are present and identical across the current lines, so nothing diverges today, but an operator needs a stated compatibility range before they plan an upgrade around it.
