#!/usr/bin/env python3
"""Freeze a GitHub pull request at review time, for benchmarking a code-review skill.

Usage:
    python3 freeze_pr.py --repo owner/name --pr 847 --ticket 665 \
        [--issues 613,666,671] [--cutoff 2026-10-14T04:44:39Z] --out DIR

Writes under DIR:
    gh/*.json                   raw API responses
    ground_truth_source.md      timeline, reviews, issue comments, inline comments. This is
                                the answer key. Never place it where a reviewing agent can read it.
    context/pr_<n>_body.md      PR description as it stood at the cutoff
    context/issue_<t>.md        each ticket's body as it stood at the cutoff
    context/issue_<t>_comments.md   the main ticket's comments created before the cutoff
    case.json                   SHAs, cutoff, and the edit timestamps that were selected

The cutoff defaults to the submission time of the earliest review that carries inline
comments. Everything in context/ is chosen as "the last edit before the cutoff", which is
what the human reviewer saw. Requires an authenticated `gh` CLI.
"""
import argparse
import json
import os
import subprocess
import sys
from collections import Counter


def gh(*args):
    out = subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout
    return out


def gh_json_pages(path):
    """gh api --paginate concatenates one JSON array per page; decode them all."""
    raw = gh("api", path, "--paginate")
    dec = json.JSONDecoder()
    items, i = [], 0
    while i < len(raw):
        while i < len(raw) and raw[i].isspace():
            i += 1
        if i >= len(raw):
            break
        obj, j = dec.raw_decode(raw, i)
        items.extend(obj if isinstance(obj, list) else [obj])
        i = j
    return items


def edits_before(nodes, cutoff):
    eds = [e for e in nodes if e["editedAt"] < cutoff and e.get("diff") is not None]
    eds.sort(key=lambda e: e["editedAt"], reverse=True)
    return eds[0] if eds else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--pr", required=True, type=int)
    ap.add_argument("--ticket", required=True, type=int, help="issue the PR implements")
    ap.add_argument("--issues", default="", help="comma-separated related issues to freeze too")
    ap.add_argument("--cutoff", help="ISO timestamp; default = earliest review with inline comments")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    owner, name = a.repo.split("/")
    out = a.out
    os.makedirs(os.path.join(out, "gh"), exist_ok=True)
    os.makedirs(os.path.join(out, "context"), exist_ok=True)

    def save(nm, data):
        with open(os.path.join(out, "gh", nm), "w") as f:
            json.dump(data, f, indent=1)

    pr = json.loads(gh("api", f"repos/{a.repo}/pulls/{a.pr}"))
    rc = gh_json_pages(f"repos/{a.repo}/pulls/{a.pr}/comments")
    reviews = gh_json_pages(f"repos/{a.repo}/pulls/{a.pr}/reviews")
    ic = gh_json_pages(f"repos/{a.repo}/issues/{a.pr}/comments")
    timeline = gh_json_pages(f"repos/{a.repo}/issues/{a.pr}/timeline")
    for nm, d in [("pr.json", pr), ("review_comments.json", rc), ("reviews.json", reviews),
                  ("issue_comments.json", ic), ("timeline.json", timeline)]:
        save(nm, d)

    author = pr["user"]["login"]
    # Cutoff: earliest review (not by the author) that has inline comments.
    review_ids_with_inline = {c.get("pull_request_review_id") for c in rc}
    candidates = sorted(
        (r for r in reviews if r["user"]["login"] != author and r["id"] in review_ids_with_inline),
        key=lambda r: r["submitted_at"])
    cutoff = a.cutoff or (candidates[0]["submitted_at"] if candidates else None)
    if not cutoff:
        sys.exit("No review with inline comments found; pass --cutoff explicitly.")

    # Head SHA the inline comments were drafted against.
    anchored = Counter(c["original_commit_id"] for c in rc if c["created_at"] < cutoff)
    head_sha = anchored.most_common(1)[0][0] if anchored else pr["head"]["sha"]
    head_commit = json.loads(gh("api", f"repos/{a.repo}/commits/{head_sha}"))
    parents = [p["sha"] for p in head_commit["parents"]]

    # CI on the frozen head, keeping only runs that completed before the cutoff.
    try:
        runs = json.loads(gh("api", f"repos/{a.repo}/commits/{head_sha}/check-runs?per_page=100")).get("check_runs", [])
        ci = Counter(r["conclusion"] or r["status"] for r in runs if (r.get("completed_at") or "9") < cutoff)
    except subprocess.CalledProcessError:
        ci = Counter()

    default_branch = json.loads(gh("api", f"repos/{a.repo}"))["default_branch"]
    main_at_cutoff = json.loads(gh("api", f"repos/{a.repo}/commits?sha={default_branch}&until={cutoff}&per_page=1"))[0]["sha"]
    try:
        cmp = json.loads(gh("api", f"repos/{a.repo}/compare/{main_at_cutoff}...{head_sha}"))
        merge_base = cmp["merge_base_commit"]["sha"]
    except subprocess.CalledProcessError:
        merge_base = None

    # Edit histories (GraphQL) for the PR body, the ticket, and related issues.
    issues = [a.ticket] + [int(x) for x in a.issues.split(",") if x.strip()]
    parts = [f'pr: pullRequest(number:{a.pr}) {{ title userContentEdits(first:100) {{ nodes {{ editedAt diff editor {{ login }} }} }} }}']
    for n in issues:
        parts.append(f'i{n}: issue(number:{n}) {{ title state userContentEdits(first:100) {{ nodes {{ editedAt diff editor {{ login }} }} }} }}')
    q = f'query {{ repository(owner:"{owner}", name:"{name}") {{ {" ".join(parts)} }} }}'
    data = json.loads(gh("api", "graphql", "-f", f"query={q}"))["data"]["repository"]
    save("edit_history.json", data)

    used = {}
    e = edits_before(data["pr"]["userContentEdits"]["nodes"], cutoff)
    if e is None:
        sys.exit("PR body has no edit before the cutoff; check --cutoff.")
    used["pr_body"] = e["editedAt"]
    with open(os.path.join(out, "context", f"pr_{a.pr}_body.md"), "w") as f:
        f.write(f"# {a.repo} PR #{a.pr}: {pr['title']}\n\nAuthor: {author}. Base: {pr['base']['ref']}. "
                f"Head branch: {pr['head']['ref']} ({pr['head']['repo']['full_name'] if pr['head']['repo'] else 'unknown fork'}). "
                f"Created {pr['created_at']}. Body as of {e['editedAt']}.\n\n---\n\n{e['diff']}")
    for n in issues:
        o = data[f"i{n}"]
        e = edits_before(o["userContentEdits"]["nodes"], cutoff)
        if e is None:
            print(f"warning: issue #{n} has no edit before cutoff; skipped", file=sys.stderr)
            continue
        used[f"issue_{n}"] = e["editedAt"]
        with open(os.path.join(out, "context", f"issue_{n}.md"), "w") as f:
            f.write(f"# {a.repo} issue #{n}: {o['title']}\n\nState at freeze time: {o['state']}. "
                    f"Body as of {e['editedAt']} (last edit before the review).\n\n---\n\n{e['diff']}")

    tc = gh_json_pages(f"repos/{a.repo}/issues/{a.ticket}/comments")
    save(f"issue_{a.ticket}_comments.json", tc)
    kept = [c for c in tc if c["created_at"] < cutoff]
    with open(os.path.join(out, "context", f"issue_{a.ticket}_comments.md"), "w") as f:
        f.write(f"# Comments on issue #{a.ticket} created before {cutoff}\n")
        for c in kept:
            f.write(f"\n---\n**{c['user']['login']}** at {c['created_at']}:\n\n{c['body']}\n")

    # Ground-truth source: human-readable dump of everything on the PR.
    with open(os.path.join(out, "ground_truth_source.md"), "w") as f:
        f.write(f"# Ground-truth source for {a.repo} PR #{a.pr} (never give this to a reviewing agent)\n\n")
        f.write("## Timeline\n")
        for ev in timeline:
            t = ev.get("event")
            if t == "committed":
                f.write(f"- committed {ev.get('sha','')[:9]} {ev.get('author',{}).get('date','')} {(ev.get('message','').splitlines() or [''])[0][:90]}\n")
            elif t in ("head_ref_force_pushed", "reviewed", "merged", "ready_for_review", "convert_to_draft", "review_requested"):
                f.write(f"- {t} {ev.get('created_at') or ev.get('submitted_at')} {(ev.get('actor') or ev.get('user') or {}).get('login','')} {ev.get('state','')} {(ev.get('commit_id') or '')[:9]}\n")
        f.write("\n## Reviews\n")
        for r in reviews:
            f.write(f"\n### review {r['id']} by {r['user']['login']} {r['state']} at {r['submitted_at']} on {r['commit_id'][:9]}\n\n{r['body'] or '(no body)'}\n")
        f.write("\n## Issue comments\n")
        for c in ic:
            f.write(f"\n### {c['user']['login']} at {c['created_at']}\n\n{c['body']}\n")
        f.write("\n## Inline review comments (chronological)\n")
        for c in sorted(rc, key=lambda c: c["created_at"]):
            f.write(f"\n### {c['id']} by {c['user']['login']} at {c['created_at']} | review {c.get('pull_request_review_id')} | reply_to {c.get('in_reply_to_id')}\n")
            f.write(f"path={c['path']} line={c.get('line')} original_line={c.get('original_line')} original_commit={c['original_commit_id'][:9]}\n\n{c['body']}\n")

    case = {
        "repo": a.repo, "pr": a.pr, "title": pr["title"], "author": author,
        "cutoff": cutoff,
        "cutoff_rule": "earliest non-author review with inline comments" if not a.cutoff else "explicit",
        "reviews": [{"user": r["user"]["login"], "state": r["state"], "submitted_at": r["submitted_at"], "commit": r["commit_id"]} for r in reviews],
        "head_sha": head_sha, "head_sha_candidates": dict(anchored), "head_parents": parents,
        "head_authored": head_commit["commit"]["author"]["date"],
        "default_branch": default_branch, "main_sha_at_cutoff": main_at_cutoff, "merge_base": merge_base,
        "ci_on_head_before_cutoff": dict(ci), "merge_commit_sha": pr.get("merge_commit_sha"),
        "later_head_shas": sorted({r["commit_id"] for r in reviews if r["submitted_at"] > cutoff} - {head_sha}),
        "ticket": a.ticket, "related_issues": issues[1:], "edits_used": used,
        "ticket_comments_kept": len(kept), "ticket_comments_total": len(tc),
    }
    with open(os.path.join(out, "case.json"), "w") as f:
        json.dump(case, f, indent=2)
    print(json.dumps({k: case[k] for k in ("cutoff", "head_sha", "head_parents", "main_sha_at_cutoff", "merge_base", "ci_on_head_before_cutoff", "merge_commit_sha", "later_head_shas", "edits_used")}, indent=2))
    print(f"\nwrote {out}/case.json, {out}/context/, {out}/ground_truth_source.md")


if __name__ == "__main__":
    main()
