# Cleanup: rewrite the explanation (D2), apply the gate's fixes, deliver

Agent: `general-purpose`, model Sonnet, effort high, budget 25 tool calls.

Read the `SKILL.md` of the `clean-up-text` skill first: it sits in the sibling `clean-up-text`
directory of the skill directory that holds `review-rules.md`, and the dispatch's Read line gives
the absolute path of that skill directory. The dispatch names the working directory,
the review's `<slug>`, the source path (`review-<slug>-d1-explanation.md`), the intended reader,
and the path of the C6 file (`review-<slug>-c6.md`). `<slug>` is `pr<N>` for a pull request, and
the branch name with `/` replaced by `-` otherwise. You write every file into that working
directory, never into the checkout under review. You cannot dispatch sub-agents and you never
ask the user anything.

You work in two rounds. The first round is D2. The top-level session then dispatches the
accuracy gate and continues you with the gate's verdict and fixes, and the second round applies
those fixes and performs the Deliver step. When the dispatch carries a gate verdict, skip round
one and go straight to round two; the rewrite and changelog paths are in the dispatch.

## Round one. D2: clean up

Run the `clean-up-text` skill on the D1 file. You run steps 1 to 5 and 7. Step 6, the accuracy
gate, is not yours: you return it as a "Needs verification" item. The repository is read-only,
and you may grep it to confirm that the names in the text exist. Write the rewrite to a new
file next to the source, named `review-<slug>-d1-explanation-cleaned.md`, and the changelog to
`review-<slug>-d2-changelog.md`. The skill's own length check applies: the body of the rewrite
does not grow past the source.

Also follow this layout for the rewrite. The layout lets a reader see every finding at a glance
and open only the detail they need. It uses HTML `<details>` blocks, which GitHub and Markdown
previews render collapsed, with a blank line after `<details>` and before `</details>` so the
Markdown inside them still renders:

- The title names the pull request and what it changes.
- The D1 lead paragraph is removed, including its statement of whether the change is ready to
  merge, which the "Must fix before merge" group already conveys. A sentence of the lead stays,
  as a short paragraph under the title, only when it carries information the implementer
  critically needs and no other part of the review states.
- The first section is "Review Details". Its heading sits outside, and one `<details>` block
  holds the rest of it: the prerequisites section, "Things the review looked at and is leaving
  to other tickets", "What passed", and the action list, in that order, each under its own
  subheading, followed by any other section a reader can skip and still act on the review.
- The four group headings of the findings follow, outside any `<details>` block.
- Each finding is one sentence followed by a `<details>` block that holds the whole finding. The
  sentence says what the finding is, in plain words a reader new to the codebase understands,
  and leaves out every detail: file and function names, the mechanism, the evidence, and the
  fix. A reader who reads only these sentences knows what every finding is about.
- Before you return, check each sentence against the finding in the source: the sentence
  says only what the finding establishes, is exactly as certain and as severe as the finding,
  and names the finding's problem rather than a symptom of it or its fix. Your changelog lists
  the sentences as added text, so the D3 gate checks each one against its finding as well.
- The length check counts the summary sentences as allowed growth, like the prerequisites
  section: the rewrite minus the prerequisites section and the summary sentences comes in at or
  under the source.

Your round-one hand-back is the "Needs verification" item, at most 150 words:

```
Needs verification
Source: <path>  Rewrite: <path>  Changelog: <path>
Definitions added: <number>, <each one in a few words>
```

## Round two. Apply the gate's fixes, then deliver

The continuation message carries the gate's verdict and its fixes. Nothing ships past a FAIL,
so what you do next depends on the verdict:

- **FAIL.** Apply the fixes to the text only. Do not perform the Deliver step. Hand back
  exactly `Corrected: <path>  Fixes applied: <n>`. The top-level session then runs the gate
  again and continues you once more.
- **PASS or PASS WITH FIXES.** Apply any fixes, then perform the Deliver step below, and hand
  back exactly `Cleaned: <path>  Body words: <n>`.

The gate also flags the definitions the rewrite added and could not confirm; that list travels
with the delivery and the reader is told nobody has confirmed it.

**Deliver.** The cleaned file is the review the user receives, and it holds everything the user
needs from the review. Append to it, at the end of the file:

1. One sentence with the gate's verdict and the number of definitions the cleanup added that
   nobody has confirmed, followed by a `<details>` block that lists those definitions.
2. A heading that names the reviewer as its reader, followed by a `<details>` block that holds
   the C6 output, copied from the C6 file the dispatch names.

## The hand-back

Your final message after round one is the "Needs verification" item above. Your final message
after round two is one line, and nothing else:

```
Corrected: <path>  Fixes applied: <n>
```

when the verdict was a FAIL, or

```
Cleaned: <path>  Body words: <n>
```

otherwise, where the word count covers the body of the cleaned file, everything above the
appended delivery blocks.
