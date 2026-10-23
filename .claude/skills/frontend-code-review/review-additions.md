# Frontend review notes and questions

These are review questions in the sense of the parent skill's step A5. Each B agent reads `## All`,
and also its own `## B<n>` section when its remit has one, and answers the questions in the latter. Beyond them, it may raise
any further concern it finds in the same area.

## All

Treat the component tree outline as orientation: which components changed, how they nest on each
page, which changed modules feed them, and what each change does. A sub-agent derived it from the
diff, so it is not evidence. Every finding still cites lines read at the head SHA, and a note in the
outline that the code contradicts is itself worth a finding.

## B3

Q3. Does it adhere to general best practices for this repo's version of React?

Q4. Is it using TypeScript, TanStackQuery instead of Redux, other things?

## B5

Q1. Is the Paragon design system being used as extensively as possible for the given components added in this change? Paragon components, bootstrap classes from Paragon and design tokens, with CSS used sparingly?

Q2. Does the implementation meet WCAG AA accessibility standards, if applicable?

Q5. Is it avoiding inline styles?
