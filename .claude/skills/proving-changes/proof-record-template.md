# Proof record: <branch>

Base: `<base sha>`  Head: `<head sha>`  Taken: <date, after the last commit>

## Acceptance criteria

| Criterion | Proof | Result |
|---|---|---|
| <criterion text, from the ticket or spec> | P1, P3 | PASS |

## Proofs

### P1: <what this proves, one sentence>

- Kind: reproduction | CI check | focused test | run the app
- Covers: `path/to/file.py` (hunks: <function or line range>), `path/to/test_file.py`
- Command or steps:

```
<command exactly as run, or the steps taken in the app>
```

- Observed:

```
<the lines of output that carry the result, trimmed>
```

- Result: PASS | FAIL (PASS means the run showed what this proof claims, so a reproduction that fails before the fix as expected is a PASS)
- Screenshot: `<file beside this record>` (when one helps)

## Diff coverage

| Changed file or hunk | Proof |
|---|---|
| `path/to/file.py` | P1 |
| `path/to/other.py` (hunk: `handle_submit`) | P2 |

Uncovered: none

## Open

<Changes with no way to prove them, and why. Empty when the work is done.>
