#!/usr/bin/env python3
"""Work with an agent's JSONL transcript without reading it into context.

Two transcript shapes are supported: a sub-agent transcript written by the Agent tool (the report is the last
SubagentHandback call) and a `claude -p --output-format stream-json` transcript from a separate Claude Code process
(the report is the final `result` event, which also carries usage and cost).

    python3 extract_handback.py <transcript> <report.md>          write the report
    python3 extract_handback.py <transcript> --audit [needle ...]   print tool-use counts, Agent dispatches, Skill
                                                                   calls, permission denials, usage, and any tool
                                                                   input containing a needle (for example the
                                                                   answer-key dir)
"""
import json
import sys
from collections import Counter


def records(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def walk(rec, kind):
    stack = [rec]
    while stack:
        o = stack.pop()
        if isinstance(o, dict):
            if o.get("type") == kind:
                yield o
            stack.extend(o.values())
        elif isinstance(o, list):
            stack.extend(o)


def tool_uses(path):
    for rec in records(path):
        for tu in walk(rec, "tool_use"):
            if tu.get("name"):
                yield tu


def result_event(path):
    last = None
    for rec in records(path):
        if rec.get("type") == "result":
            last = rec
    return last


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(c.get("text", "") for c in content if isinstance(c, dict))
    return ""


def main():
    src = sys.argv[1]
    if len(sys.argv) > 2 and sys.argv[2] == "--audit":
        needles = sys.argv[3:]
        counts, agents, skills, hits, denials = Counter(), [], [], [], []
        for tu in tool_uses(src):
            counts[tu["name"]] += 1
            inp = tu.get("input") or {}
            if tu["name"] == "Agent":
                agents.append(f'{inp.get("subagent_type")} model={inp.get("model")} effort={inp.get("effort")} :: {inp.get("description")}')
            if tu["name"] == "Skill":
                skills.append(f'{inp.get("skill")} args={inp.get("args")!r}')
            blob = json.dumps(inp)
            for n in needles:
                i = blob.find(n)
                if i >= 0:
                    hits.append(f'{tu["name"]}: ...{blob[max(0, i - 60):i + len(n) + 60]}...')
        for rec in records(src):
            for tr in walk(rec, "tool_result"):
                t = text_of(tr.get("content")).lower()
                # A denial from the harness is a short message; a long result that merely contains the words is code.
                if len(t) < 600 and ("requested permissions" in t or "haven't granted" in t or
                                     ("permission" in t and ("denied" in t or "not allowed" in t))):
                    denials.append(t[:160].replace("\n", " "))
        print("tool uses:", dict(counts))
        print("Agent dispatches:")
        for a in agents:
            print("  ", a)
        print("Skill calls:", skills)
        print(f"permission denials ({len(denials)}):")
        for d in denials[:5]:
            print("  ", d)
        res = result_event(src)
        if res:
            print("result event:", {k: res.get(k) for k in ("subtype", "num_turns", "duration_ms", "total_cost_usd", "is_error")})
            print("usage:", res.get("usage"))
        print(f"needle hits ({len(hits)}):")
        for h in hits:
            print("  ", h)
        return
    reports = []
    for tu in tool_uses(src):
        if tu["name"] == "SubagentHandback":
            inp = tu.get("input") or {}
            reports.append(inp.get("report") or inp.get("message") or inp.get("content") or json.dumps(inp))
    source = "SubagentHandback"
    if not reports:
        res = result_event(src)
        if res and res.get("result"):
            reports.append(res["result"])
            source = "stream-json result event"
    print(f"reports found: {len(reports)} ({source})")
    for i, r in enumerate(reports):
        print(f"  [{i}] {len(r)} chars, starts: {r[:80]!r}")
    if reports:
        open(sys.argv[2], "w").write(reports[-1])
        print("wrote last report to", sys.argv[2])


if __name__ == "__main__":
    main()
