# B4: Behavior and tests

Agent: `general-purpose`, model Sonnet, effort high, budget 35 tool calls.

Read `review-rules.md`, the shared brief, and `agents/report-format.md` first, in that order.
When the dispatch names a section of the extension skill's `review-additions.md`, read that
section too. Write your report as `agents/report-format.md` says, and end with the hand-back
it defines. Paths to other skill files, such as `review-rules.md` and `agents/report-format.md`,
are relative to the skill directory, whose absolute path the dispatch's Read line gives (the directory that holds `review-rules.md`), not to `agents/`.

In a temporary worktree:

1. **Map and break.** For each criterion in the brief, name the test that fails when the
   behavior it describes is broken, and the assertion that fails; then break the code path,
   run the test, confirm it fails on the asserted behavior rather than on an import error,
   restore. Do this for every test so named and for any test guarding a security or
   data-integrity path. Return the mapping and a table: test | how the code was broken | failed?
   | failed for the stated reason? A test that also passes against broken code is reported in the table and is also a finding
under Findings.
2. **Error paths, enumerated.** For each new endpoint or public function, read the source of
   every callee it invokes and list each exception the callee can raise; check that each one is
   handled or mapped to a client response. Put every unmapped path, every criterion's negative
   case, each first-class configuration option of the input types, a value at the maximum
   length of every input that is concatenated into a stored field, and malformed input through
   any permission check that runs before validation into one probe file, and run it once. Report
   each unhandled error as a reproduction with the input and the exception.
3. **Bounded writes and check order.** Every generated value stored in a column with a length
   limit, checked against the maximum lengths of its inputs; when a permission predicate
   receives raw client input, what the production predicate (not the test stub) returns for
   malformed input, read in the consuming repository if it lives there.
4. **Edited tests.** For every pre-existing test the diff edits, run the pre-existing form
   against the new code. If it passes, the edit was unnecessary and its comment is suspect.
5. **Lean tests.** For the new and changed tests: two tests that assert the same behavior;
   tests of boilerplate or of the obvious (a default value, a field's presence) that the
   surrounding module does not test at that granularity; tests that run the same code with
   different inputs as copies rather than one parameterized test, using what the repository
   already uses (`ddt` or `pytest.mark.parametrize` in Python, `it.each` or `test.each` in
   Jest); a docstring on a test whose name and body already say what it checks; assertions that
   cannot fail; expected values recomputed the way the code computes them rather than taken from
   an independent source; tests that assert how the code is written (a mocked collaborator was
   called, a call order, a query count, a lock or manager method invoked) rather than what it
   does; fixtures or setup that change global state (a settings value, a permission registry, a
   module attribute) without restoring it; values that can go stale (dates) not held in
   constants or fixtures. Name each, with the fix.

## Red flags

| Thought | Reality |
| --- | --- |
| "The migration check covers this criterion." | A migration check proves the schema applies. It proves nothing about the behavior the criterion describes. Name the test or report a `Gap`. |
| "Existing tests cover this." | Name the test and the assertion that would fail. If you cannot, it is not covered. |
| "The tests pass, so the behavior works." | A test that also passes against broken code proves nothing. Break the code and look. |
| "The test mocks the lock call, so the lock is tested." | It tests that a method was called. Replace the call with one that does nothing and the test still passes. |
| "More tests is safer." | Every test is something a reviewer reads. Two tests of one behavior, or five copies instead of one parameterized test, are findings. |
