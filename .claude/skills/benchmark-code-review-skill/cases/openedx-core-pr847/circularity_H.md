# Circularity check for variant H (written before the report was read)

The two-reviewer code-review-v2 keeps F's four mechanisms (premise audit, invariants table, three-list sort,
conditional deferral) and adds the error-path enumeration, bounded-length probes, permission-order probe, lock-redundancy
row, pre-existing-test rerun, and the "never another pinning test" rule. It inherits F's mapping (GT4, GT7, GT9, GT10,
GT12, GT15, GT16) and adds GT3, GT6, GT11, GT14, GT18, GT19 by the same passages listed in circularity_G.md.
The question this run answers is cost: whether the two-reviewer, budgeted shape holds F's coverage at about a quarter of
F's 1.31M tokens. Any gain over F is circular for the same reason as F's gain over run 1.
