# Scoring: <variant>, report = reports/<file>

Credit tiers, applied identically to every variant:
- 1.0  found, correct mechanism, actionable recommendation
- 0.75 found and correct, but severity one level soft or the recommendation hedged into a question
- 0.5  noticed but vague, misdiagnosed, severity two levels soft, or (for a multi-part item) only part found
- 0    missed, or the report argues the opposite

Severity ladder for "levels": blocking (Bug / Gap / impact >= 50) > Question (impact 25-49) > Suggestion / Nit / dropped.
Judge content, not labels: two reports that say the same thing with different labels get the same credit.

| GT | w | credit | where in report | note |
|---|---|---|---|---|
| GT1 ... | 3 | | | |

Weighted: blocking <sum>x3 ; substantive <sum>x2 ; nits <sum> => <total>/<max> = <coverage %>

Findings reported: <n>.
- False positives (wrong, unreachable, something CI enforces, or a premise the maintainer rejected): <list>
- Valid extras (a maintainer would accept them; not in the ground truth): <list>
- Neutral (questions or nits with no cost): <list>
Precision = 1 - FP / findings

Communication (0 to 1): verdict first; file:line anchors; evidence (probe, citation, or reproduction) per finding;
actionable fixes; severity calibration; signal-to-noise; honesty about inference versus execution. Note length.

Composite = 0.70 x coverage + 0.15 x precision + 0.15 x communication

Cost: orchestrator tokens, sub-agents (type, model, count), wall clock, from the report's process log.
