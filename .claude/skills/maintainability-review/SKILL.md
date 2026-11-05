---
name: maintainability-review
description: Reviews a diff for maintainability alone: readability, comments and docstrings, clarity of architecture and where its rationale lives, naming, duplication, and dead or bypassed abstractions. Use when asked to review for maintainability, readability, or code quality, or when correctness, tests, and security are covered by a separate review. Measures against the repository's own precedent rather than asserting taste, and proposes a concrete replacement for every finding. Review-only: never fixes, commits, or pushes.
---

# Maintainability review

Review a diff for one question: what will this cost the next person who has to change it?
Everything else belongs to another reviewer. This is the narrow sibling of `code-review`: use that
skill for a full peer review, and this one when maintainability is the whole assignment.

## Scope

State the boundary in the review's opening lines, so no silence reads as a pass.

**In scope:** the dimensions in step 4's table, and nothing beyond them.

**Out of scope:** correctness, edge cases, security, performance, and whether coverage is
adequate. Do not dress a bug up as a maintainability finding. Note one in a single line at the
end, marked out of scope, and point at `code-review`.

**Review-only.** Surface findings and let the developer decide. Never fix, commit, or push from
this skill, and post nowhere without an explicit request and approved wording.

Per the Delegation rule in `CLAUDE.md`, run this skill in the top-level session and push
context-heavy lookups (where is this called, does this name exist elsewhere) down to a Haiku
`Explore` sub-agent.

## 1. Get the diff

Take the target from what the developer asked: a PR number (`gh pr diff <n>`), a branch, or the
working changes. Default to `git diff "$(git merge-base HEAD origin/main)"..HEAD`. Read the diff
at its own ref, not a stale checkout. If it is empty, say so and stop.

## 2. Calibrate against this repository before judging anything

Comment density, docstring length, and tolerance for verbosity are house style, not universal
constants. "This comment is too long" is an opinion. "The repository's own precedent for this
exact pattern is two lines and this is eight" is evidence.

So before grading anything, read two or three comparable files this change did not write: the
neighboring model, the sibling module, the existing use of the same library. Note what the
codebase does about docstrings, inline comments, type hints, and test structure. Every stylistic
finding then cites that precedent by `file:line`, or it stays out of the review.

## 3. Measure what can be measured

A claim that a change is over-commented invites a difference of taste. A number does not. Count
the prose share (docstring and comment lines over non-blank lines) for every substantial file in
the diff, and put the table in the review:

```bash
python3 - <<'PY'
import ast, io, pathlib, tokenize
for path in ["path/to/file.py"]:  # every substantial file in the diff
    source = pathlib.Path(path).read_text()
    docstring_lines, comment_lines = set(), set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if ast.get_docstring(node, clean=False) is not None:
                docstring = node.body[0]
                docstring_lines.update(range(docstring.lineno, docstring.end_lineno + 1))
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.COMMENT:
            comment_lines.add(token.start[0])
    prose = len(docstring_lines | comment_lines)
    nonblank = sum(1 for line in source.splitlines() if line.strip())
    print(f"{path}: code={nonblank - prose} prose={prose} share={prose * 100 // nonblank}%")
PY
```

The script parses Python only. For a TypeScript or SCSS diff, say what you see rather than
inventing a number.

The measurement is not itself the finding: prose outweighing code is reasonable in a
well-documented public API and, in a test file, a problem worth ranking high. The table turns
"this feels heavy" into a fact the developer can check, and points you at the files worth reading.

## 4. What to look for

Work the diff against these. Skip the rows it does not touch and say which you skipped.

| Look for | The question |
| --- | --- |
| Rationale in the wrong place | Is an architecture decision explained in a twenty-line inline comment instead of the ADR or design doc that already owns the subject? Comments like that drift silently, and a reader who starts from the docs never sees them. |
| Code that outran its documents | Where the change deviates from a governing ADR, README, or ticket, was that document amended? A document that still describes the old design is worse than none, because a reader will trust it. |
| References that dead-end | Does every cited file, document, section, ticket, and symbol exist? Grep for each one. Scratch filenames and unpublished internal IDs are the usual failure. |
| Change narration | Does a comment describe what the code used to be, argue against an alternative, or instruct a future reader not to simplify it? History belongs in `git log`, and defensive prose outlives the objection it answers. |
| Docstrings the code contradicts | Does the caller do what the docstring claims? A docstring saying "constructing one is the validation" beside a caller that validates everything beforehand is a bug, not a style nit. |
| Abstractions carried but bypassed | Is a class, framework, or helper introduced and then routed around at the call site? Either it earns its place or it goes. |
| Speculative surface | Does a public function have no callers, or return `Any` where its docstring promises typed fields? Count the callers with a grep rather than assuming. |
| Reimplemented framework behavior | Is a derived constant, list, or lookup doing what the language or framework already does, next to code that does it the plain way? |
| Export surfaces that are not real | Is a name in `__all__` that the module does not define, or that no aggregating module re-exports? Follow the import chain rather than trusting the list. |
| Duplication | Is the same comment pasted into two settings files or into both a docstring and the comment above it? Is the same logic written twice where one caller would do, or extracted for two callers when three is the bar? |
| Names and structure that mislead | Does each name say what the thing is, consistently with the terms used around it? Can a reader follow the decomposition and the control flow without holding the whole file in their head? |
| Expressions no one can read | Nested conditional expressions inside an f-string, a comprehension doing three things at once, a name that needs its own comment to be understood. |
| Tests as documentation | Does each test name state the behavior expected, in a sentence a stranger can read, rather than naming its subject? Do the tests assert behavior, or restate a declaration from the line above it in the model? Would merging several make the contract clearer rather than dimmer? |

## 5. Every finding carries its replacement

A finding without a suggestion is a complaint. Write the replacement out: the shortened comment,
the merged test, the renamed function, the amended ADR paragraph. Where you recommend deleting
something, say what covers the same ground afterwards.

Anchor each finding with a `file:line` link, and verify the anchor by reading those lines rather
than trusting the diff's own numbering. When a suggestion changes behavior or a public surface,
even slightly, say so in the finding instead of letting it read as a pure cleanup.

Where two resolutions are both defensible, give a two-column trade-off table and name your
recommendation rather than leaving the developer to choose blind.

## 6. Order by cost, and name what is good

Order findings by what each one costs the next maintainer, not by a severity vocabulary. A
document that lies about the current design costs more than nine long comments, so it goes first.
Mark the few findings that should block a merge and leave the rest unranked: a five-level
severity scale is apparatus the reader has to learn.

Then close with what is genuinely good and should survive, named specifically. This is not
padding: a review that only attacks reads as a style preference, and this section is where you
tell the developer which parts of their design you are not asking them to touch.

## Output shape

1. A one-paragraph verdict: is the design sound, and what is actually holding the change back?
2. The scope boundary, in two lines.
3. The measurement table from step 3.
4. The findings, ordered by cost, each with an anchor, the mechanism, and its replacement.
5. What is good and should stay.

Lead each finding with the point, then the mechanism, in complete sentences. Follow `CLAUDE.md`'s
writing style rules otherwise, and add no praise padding. If nothing is wrong, say so plainly and
stop.
