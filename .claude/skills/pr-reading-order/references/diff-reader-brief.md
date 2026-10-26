# Diff-reader brief

Fill in the bracketed parts and send this as the prompt of one `general-purpose` Sonnet
sub-agent.

---

You are helping a reviewer plan the order in which to read a pull request. Read-only task: do
not edit any repository, do not post anything to GitHub, and do not dispatch sub-agents. If you
need something you cannot get yourself, list it under "Needs research" in your report.

PR: [URL] ("[title]", ticket [owner/repo#n]). Head SHA [sha], base SHA [sha].

Get the diff with `gh pr diff [n] --repo [owner/repo] > [scratch dir]/pr.diff` and the per-file
counts with `gh pr view [n] --repo [owner/repo] --json files`. Read the whole diff. For file
context beyond the diff, read the file at the head SHA
(`gh api "repos/[head owner]/[repo]/contents/<path>?ref=[sha]" -H "Accept: application/vnd.github.raw"`).

[Optional: what an earlier review already established, marked as claims to verify against the
diff rather than trust.]

Report back (this is the only thing the reviewer's session will see, so be complete but
compact):

1. A table of every changed file: path, +/- lines, new or modified, test or source.
2. For every changed non-test file, the changed functions, components, constants and hooks with
   their line ranges at the head SHA (new-file line numbers from the diff hunks), and one
   sentence on what each changed piece does now.
3. The execution threads: the 1 to 5 major end-to-end flows of data or control through the
   changed code. For each thread, list the pieces in the order a reviewer should read them
   (file:function:line-range), who calls or feeds whom, and the test files and test names (with
   line numbers) that exercise that thread most directly. Order the threads by importance, with
   the thread whose output the others read first.
4. Changed code that fits no thread, with file:lines and one sentence each.
5. A blast-radius score from 0 to 100 for each changed source piece, with a one-phrase reason
   naming the worst plausible failure. Score it with this rubric:

   [Paste the "Scoring blast radius" section of SKILL.md here, without its heading.]
6. Anything surprising in the diff, or anything that contradicts the claims above.

Mark anything you inferred rather than read in the diff as INFERRED.
