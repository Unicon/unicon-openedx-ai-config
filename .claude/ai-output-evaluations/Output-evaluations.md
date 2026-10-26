# Output Evaluations

After developing a feature with AI, drop a very short note in here: what went well or didn't? Your PR link, a few bullet-points, or just one sentence.

## Log

*08/25/2026 -- Jesper Hodge -- <PR Link>*

- This is an Example Entry
- AI hallucinated a folder that didn't exist; I added some context to the code-review-openedx skill to fix it. (I just made up this example)

*10/25/2026 -- mgwozdz-unicon -- https://github.com/Unicon/unicon-openedx-ai-config/pull/71*

- Architect final review of #895 with ticket-writer. It took six and a half hours to review just this one ticket. The ticket's premises (what Studio deletes, what course import does, what the sibling guardrail tickets actually cover, whether a hook exists) were only checked during the final review, so each false premise reopened the human sections and re-ran both experts. Claude also passed on three wrong facts from sub-agents without reading the cited code, and asked scope questions one round at a time instead of batching them.
- Fix: ticket-writer now verifies the premises against the code and sibling tickets in the pre-handoff check, before anything is drafted, and batches the scope decisions: https://github.com/Unicon/unicon-openedx-ai-config/pull/72

*Date -- Name -- PR Link*
