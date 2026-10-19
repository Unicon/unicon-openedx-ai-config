#!/usr/bin/env python3
"""Work with a sub-agent's JSONL transcript without reading it into context.

    python3 extract_handback.py <transcript.output> <report.md>          write the last SubagentHandback report
    python3 extract_handback.py <transcript.output> --audit [needle ...]   print tool-use counts, Agent dispatches,
                                                                          Skill calls, and any tool input containing
                                                                          a needle (for example the answer-key dir)
"""
import json
import sys
from collections import Counter


def tool_uses(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            stack = [rec]
            while stack:
                o = stack.pop()
                if isinstance(o, dict):
                    if o.get("type") == "tool_use" and o.get("name"):
                        yield o
                    stack.extend(o.values())
                elif isinstance(o, list):
                    stack.extend(o)


def main():
    src = sys.argv[1]
    if len(sys.argv) > 2 and sys.argv[2] == "--audit":
        needles = sys.argv[3:]
        counts, agents, skills, hits = Counter(), [], [], []
        for tu in tool_uses(src):
            counts[tu["name"]] += 1
            inp = tu.get("input") or {}
            if tu["name"] == "Agent":
                agents.append(f'{inp.get("subagent_type")} model={inp.get("model")} effort={inp.get("effort")} :: {inp.get("description")}')
            if tu["name"] == "Skill":
                skills.append(inp.get("skill"))
            blob = json.dumps(inp)
            for n in needles:
                i = blob.find(n)
                if i >= 0:
                    hits.append(f'{tu["name"]}: ...{blob[max(0, i - 60):i + len(n) + 60]}...')
        print("tool uses:", dict(counts))
        print("Agent dispatches:")
        for a in agents:
            print("  ", a)
        print("Skill calls:", skills)
        print(f"needle hits ({len(hits)}):")
        for h in hits:
            print("  ", h)
        return
    reports = []
    for tu in tool_uses(src):
        if tu["name"] == "SubagentHandback":
            inp = tu.get("input") or {}
            reports.append(inp.get("report") or inp.get("message") or inp.get("content") or json.dumps(inp))
    print(f"handbacks found: {len(reports)}")
    for i, r in enumerate(reports):
        print(f"  [{i}] {len(r)} chars, starts: {r[:80]!r}")
    if reports:
        open(sys.argv[2], "w").write(reports[-1])
        print("wrote last handback to", sys.argv[2])


if __name__ == "__main__":
    main()
