# Visual Documents

Use this file for any text-heavy page: an explainer, a design doc, an ADR summary, a report, a review. A text-heavy page is the easiest one to get wrong, because it can pass as HTML while still being a Markdown document with styling: headings, then bullets, then more headings, all in one long column. The reader then has to rebuild the structure in their head. The page should show that structure instead.

## Order: highest level first, then detail

Write the page as a zoom, from the whole picture down to the specifics.

1. **The whole picture.** Show the TL;DR and one overview figure above the fold. The overview figure shows the main parts and how they connect, such as the three stages of a pipeline or the four tables of a data model. A reader who stops here still has the right model in their head.
2. **One band per part.** A band is a full-width section of the page. Each part from the overview gets its own section, in the same order and with the same name as in the overview figure. Group the content by what belongs together for the reader, not by the order in which the source material happened to say it.
3. **Detail, folded away.** Edge cases, rationale, rejected alternatives, field lists, and full quotes go into collapsibles inside the band they belong to.

Before drafting, write the grouping as a short page outline: the overview, the bands, and what goes into each band's collapsibles. If one band's content belongs in another band, or the order jumps between levels of detail, fix the page outline before you start on the HTML.

## Layout: use the width of the page

A list of parallel things is a row, not a column. When the content has several items of the same kind, such as stages, options, actors, layers, or before and after, put them side by side so the eye can compare them.

| The content is… | Lay it out as… |
|---|---|
| Steps in order (a pipeline, a lifecycle, a request flow) | A row of columns joined by arrows, one column per step, each with its own small figure and two or three lines of text |
| Options or alternatives | Columns with the same rows in each, so the same attribute lines up across options |
| Layers or a hierarchy | Stacked horizontal bands, with the highest layer at the top |
| Two states (before and after, current and proposed) | Two panels side by side with the differences highlighted |
| One concept with its parts | A figure with callouts, and the text for each callout next to it |
| Rules with conditions | A matrix with conditions as rows and outcomes as columns |

Use CSS grid with `repeat(auto-fit, minmax(16rem, 1fr))` so a row wraps to one column at phone width. Keep a row to four items or fewer. Five or more parallel items usually means the content needs another level of grouping.

## Keep the full text, but fold the detail

Nothing from the source text is deleted to make the page shorter. The text moves to a level the reader opens only when they want it.

- **`<details>`** for rationale, edge cases, and long examples. The summary line states the point of the hidden text in one sentence, so a reader who never opens it still gets the point. "Why not a plain unique constraint: NULLs never collide" works as a summary line. "More details" does not.
- **Tabs** for content that is parallel and long, such as the same rule shown for each of three roles.
- **A side panel** for content behind a diagram: clicking a node opens its text. See `diagrams-and-illustrations.md`.
- **Open by default:** the overview and the lead sentence of every band. **Closed by default:** everything a reader needs only for a specific question.

Open every `<details>` on `beforeprint` (see `accessibility-and-print.md`), so the printed page keeps the full text.

## Which diagrams to draw

A diagram earns its place when it shows a relationship that the text needs a paragraph to describe: an order, a containment, a contrast, a flow, a state change, or which outcome follows from which condition. Draw one for the overview, and one for each band whose content has such a relationship. Skip the diagram when:

- the content is a single fact, a definition, or a list with no relationships between its items;
- the diagram would only repeat the heading in boxes;
- the information is minor. Leave minor information out of the diagram and keep it in the text or a collapsible.

Keep each diagram to one takeaway and about nine elements or fewer. When a diagram needs more elements, split it, or move the rare branches into the text.

## The outline check: verify each diagram before drawing it

Never draw a diagram straight from your understanding of the topic. Write it down as a text diagram outline first, check the outline against the page text, and then draw from the outline.

1. **Write the diagram outline** with one line per field. Any field may take a second line when it needs one:
   - **Takeaway:** the one sentence the diagram proves.
   - **Elements:** the boxes, nodes, columns, or rows, with their labels.
   - **Relations:** the arrows, nesting, or alignment, and what each one means.
   - **Inferred:** the elements and relations that follow from the text without being stated there, or "none". They stay under Elements or Relations too.
   - **Left out:** the minor points that stay in the text.
2. **Check the outline line by line against the text** of the section it illustrates. For each element and relation, find the sentence that says it. If an element or relation follows from the text without being stated there, also list it under Inferred. Fix every line that the text does not support, and every line that contradicts the text. If the text itself is wrong, fix the text first. Repeat until every line passes, at most three rounds. A line that still fails after three rounds is dropped from the diagram and mentioned to the user.
3. **Draw exactly the outline.** Add no element, label, or arrow that is not in the outline. Once the outline passes, you do not need to check the drawing against the text again. Check the render only for layout and legibility, as described in `verify-before-delivering.md`.
4. **Keep the outline as evidence.** Put it in an HTML comment directly above the `<figure>`, with the section each line was checked against, so a reviewer can repeat the check without asking you:

```html
<!-- diagram-outline (checked against #deploy)
  Takeaway: a change reaches production only after it passes staging.
  Elements: merge; build; staging; production.
  Relations: merge -> build -> staging -> production, each arrow "triggers" (#deploy, paragraph 1).
             staging -> build "on failure, rebuild after a fix" (#deploy, paragraph 2).
  Inferred: none.
  Left out: the nightly cleanup job (covered in #operations).
-->
<figure>…</figure>
```

When the outline uses a term, use the same word in the text, the diagram label, and the outline. A diagram that says "group" next to text that says "node" makes the reader wonder whether these are two different things.

## Example sketch: a band with steps side by side

```html
<section id="deploy">
  <h2>From merge to production in three steps</h2>
  <p class="lead">A merge triggers a build, the build goes to staging, and only a passing staging run goes to production.</p>
  <div class="steps"><!-- grid: repeat(auto-fit, minmax(16rem, 1fr)) -->
    <article>
      <h3>1. Build</h3>
      <svg viewBox="0 0 240 120" role="img" aria-label="…">…</svg>
      <p>Two or three lines that state the step.</p>
      <details><summary>Why the build runs once per merge, not per commit</summary><p>Full rationale…</p></details>
    </article>
    <article>…2. Staging…</article>
    <article>…3. Production…</article>
  </div>
</section>
```
