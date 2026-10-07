# Importable test-data files

Read this file in full before building any test-data file. It describes what the QA engineer
can actually import on the test environment, where the files go, how they are named, and
which formats have already been verified against the code, so a new ticket's folder reads
like the folders already there.

## What can be imported, and what cannot

The shared QA test environment (Master Sandbox) cannot run scripts, `manage.py`, or a Django
shell. The QA engineer has the LMS and Studio UI, Django admin, and Postman. A test-data
file is therefore useful only if Studio can import it through its own UI:

| Data | Format | Where it is imported in Studio |
| --- | --- | --- |
| Taxonomy with tags | CSV and JSON, same tag set in both | Taxonomies → Import |
| Course with content and settings | `.tar.gz` in the Studio export format (OLX) | New course, then Tools → Import in that course |

Anything else (users, enrollments, learner progress, grades, database rows without a UI) is
not a file. Describe it in the README as a manual UI or Django admin step, or as not
reproducible on Master Sandbox. Scenarios whose data or check is out of reach of the UI,
Django admin, and Postman belong in a local Tutor environment if the tester has one; the QA analysis already splits
those cases out, so mark them in the README as local-environment scenarios.

Never build a file for a state that Studio cannot produce through its UI. For example, a
course with no start date cannot be created: Studio always sets a start date, and when none
is given it uses the default 2040-01-01. A hand-crafted archive with `"start": null` would be
a synthetic state that no real user can reach. Say in the report and the README that the
scenario is not reproducible on Master Sandbox, and cite the code that makes it so.

## Where the files go

The orchestrating session gives you the base folder in your prompt. It is either the user's
configured test-data folder or, when the user gave none, the session scratchpad directory.
Save every file under `<base folder>/#<N>/`, where `<N>` is the GitHub issue number. For a
batch of tickets, use one folder per ticket. Write nothing anywhere else. Temporary build
directories go in the session scratchpad.

Before writing, list the base folder and the target folder:

- If the base folder already holds sibling `#<N>/` folders from earlier tickets, read one or
  two of them and their `README.txt` to pick up the current naming and README style.
- If `#<N>/` already exists and contains files, do not overwrite or add to it silently. Stop
  and return an open question: list the existing files, one line each, and say what the
  analysis would add or change.

## Naming

The ticket number lives only in the folder name. File names follow `NN_description.ext`:

- `NN` is a two-digit sequence starting at `01`, in the order the README describes the files.
- `description` is lowercase with underscores and says what the file is for, for example
  `competency_tree`, `course_search_alpha`, `course_date_out_of_range`,
  `course_outline_graded`.
- No spaces and no `#` in file names.
- The CSV and JSON versions of the same taxonomy share one number and one description
  (`01_competency_tree.csv`, `01_competency_tree.json`).

## Taxonomy files: verified format

The parsers are in `openedx-core/src/openedx_tagging/import_export/parsers.py`, and the
parent-order check is in `actions.py`. Re-check them if the code has moved.

- Required fields are `id` and `value`. `parent_id` is optional. A tag with an empty or
  missing `id` is rejected, so a "tag without an ID" cannot be created by import.
- The parent must appear in the file before its children. Otherwise the import fails with
  "Unknown parent tag".
- CSV is read as UTF-8 with a header row `id,value,parent_id`.
- JSON must have a top-level `tags` array. Top-level `name` and `description` are allowed
  and match what Studio's own export writes, so set them.
- Reference templates in the same package: `import_export/template.csv` and
  `import_export/template.json`.

### Known Studio bug: re-importing the same file in one page session

This is a known, already-reported bug in Studio; do not report it as a new finding. It may
have been fixed since this note was written. On the Taxonomies page, if a file was imported
and then the same file is uploaded again in the same page session, the "Continue" button on
the "Upload file" step does nothing, and no network request is sent. A different file works.

Before re-importing a fixture that was already imported in the current page session (for
example after deleting and recreating a test taxonomy), reload the Taxonomies page. Put this
reload step into the import steps of the README and of the test case whenever a scenario
imports the same file more than once.

## Course archives: verified format

The importer and exporter are in `openedx-platform/xmodule/modulestore/` (`xml.py`,
`xml_importer.py`, `xml_exporter.py`). Sample courses are in
`openedx-platform/common/test/data/` (`toy`, `simple`).

- The archive root is `course/`. Inside it: `course.xml` pointing at the run,
  `course/<run>.xml` listing chapters, then `chapter/`, `sequential/`, `vertical/`, and
  `html/` files, plus `policies/<run>/policy.json` and `policies/<run>/grading_policy.json`.
- Set `display_name` and `start` explicitly in `policies/<run>/policy.json`. The import
  overwrites every field that is explicitly set in the archive, so the QA engineer does not
  have to set the name or start date by hand. Fields not set in the archive (end date,
  enrollment dates, pacing) keep the values of the empty course.
- The org, number, and run inside the archive do not have to match the course being imported
  into: Tools → Import always writes into the target course. Still pick readable values (for
  example org `QA<N>`, number `ALPHA`, run `2026`) and list them in the README, because the
  QA engineer uses them when creating the empty course.
- `graded` and `format` go as attributes on `<sequential>`. Add every `format` used to
  `grading_policy.json`.
- Give every subsection one vertical with one simple HTML block, so the outline is never
  empty.

When the screen under test filters or displays data by some attribute, check that attribute
in the frontend code and build the data for it. For example, the #670 course browser treats
a subsection as gradeable only by its `graded` flag; `format` has no effect on the display.

Watch for side effects between data sets and state them in the README. For example, if most
courses share the start date 2026-03-15, all of them fall inside a 2026 date-range filter,
and the QA engineer must know which course is supposed to disappear.

## Checks before reporting

- `tar -tzf` every archive and confirm the `course/` root and the expected files.
- Parse every XML file (`xml.etree.ElementTree`) and every JSON file (`json.loads`),
  including those inside the archives.
- Read every CSV with `csv.DictReader` and confirm the expected columns and rows.
- A full import needs Django and a database, which the local workspace does not have. Do not
  set one up. Say in the report that the files were checked statically against the code, and
  that the import on Master Sandbox is the final check.

## README.txt

Write `README.txt` in English, in the style of the sibling folders' README files when any
exist:

- The first lines: what the fixtures are for (ticket number and screen) and a link to the QA
  artifact.
- One numbered block per file or per group of similar files. Each block says what the file
  creates (the tag tree or the course outline, drawn as indented text), the org, number, run,
  and start date for courses, which test cases it covers, and the exact import steps: where
  to go, what to click, what to type, what to check after the import, and what to finish by
  hand.
- A block for every scenario that is not reproducible on Master Sandbox, with the reason.
- Scenarios that need no file (for example a request failure reproduced by blocking the URL
  in the browser's devtools) get a short block that says so and how to do it.
- A closing block with the common preconditions: feature flags, the user role, and how to open
  the page under test (by direct URL if the menu entry may not exist yet).
