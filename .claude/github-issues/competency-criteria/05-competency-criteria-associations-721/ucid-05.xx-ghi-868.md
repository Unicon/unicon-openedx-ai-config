# [Bug] Competency Management page: long competency names and Competency ID badges overflow the tree and the course panel

GitHub: https://github.com/openedx/openedx-core/issues/868 (#868, OPEN)
Cached: 2026-10-14

**Environment:** Master Sandbox, https://apps.master.openedx.io/

**Steps to reproduce**

1. Download the taxonomy export file [QA758 Closed Taxonomy 13.10 (1).csv](https://github.com/user-attachments/files/33403061/QA758.Closed.Taxonomy.13.10.1.csv).
2. In Studio, go to Taxonomies and import the file as a new taxonomy with a Competency taxonomy type.
3. Open the Competency Management page of the imported taxonomy (`/authoring/taxonomy/<id>/competencies`).
4. Select the first competency.

<img width="1919" height="1048" alt="Image" src="https://github.com/user-attachments/assets/000d4e0b-e4f9-4e6f-ba97-0d8accbd9da7" />
<img width="1919" height="1045" alt="Image" src="https://github.com/user-attachments/assets/eaf46410-8997-4028-b1ec-cfb45b901757" />

**Actual result**

Competency tree (left column):

1. The underscore-joined name does not wrap. Its row extends past the left column, across the course panel, to the edge of the page, and its Competency ID badge is pushed out of view.
2. The hyphen-joined name wraps correctly inside the row, but its Competency ID badge stays on one line and spills out of the left column over the course list.

Course panel (right column), with the first competency selected:

3. The "Demonstrate Mastery For" heading shows the competency name and its ID badge on single lines that run past the right edge of the panel.
4. The selected tree row from item 1 lies on top of the panel's empty-state message, so the line "Make content selections to create competency criteria associations." is covered and cannot be read.

The other tags in the file come from other test scenarios. The two names that start with 255 `A` characters overflow the same way, but they contain no separator at all, which is not a realistic case.

**Expected result**

Every competency name and every Competency ID badge stays inside its own column, in both the tree and the course panel. A long value does not overlap neighboring elements and does not cause horizontal page scrolling.

**Why this matters for real data**

Since #758, a competency that has no institution-assigned ID receives an ID generated from its name, up to 255 characters long. Real competency frameworks contain long competency statements: the EDL Durable Skills Framework on Master Sandbox has 5 competencies longer than 100 characters, the longest being 226 characters. A competency like that, added without its own ID, gets a Competency ID badge as long as its statement. Real statements contain spaces and wrap correctly as names. Whether a long badge whose ID contains spaces wraps has not been checked. The badge in item 2 has no spaces.

**Open question for design**

Should a long Competency ID badge wrap onto several lines, or be truncated with the full value available on hover or focus?

**Technical notes**

- The row is rendered in `src/taxonomy/competency-management/CompetencyTreeItem.tsx`: `.competency-row` contains the label `<span className="competency-row__label">` and `<Badge className="competency-row__badge ml-auto">`.
- `CompetencyTree.scss` already sets `overflow-wrap: anywhere` on `.competency-row__badge`, but the badge text still does not break. A likely cause is that the label and the badge are flex items, and a flex item defaults to `min-width: auto`, so it cannot shrink below the width of its longest unbreakable word. This cause has not been confirmed in code. The course panel heading probably needs the same treatment.
- The page was introduced in #680. The tag list on the taxonomy page (`/authoring/taxonomy/<id>`) has a similar wrapping issue that is tracked separately in #<tag list issue>.
