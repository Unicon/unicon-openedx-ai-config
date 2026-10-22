#!/usr/bin/env python3
"""Render a component-tree spec as Markdown with an inline SVG, plus a text outline.

Usage:
    python3 render_component_tree.py SPEC.json --md OUT.md [--outline OUT.txt] [--svg OUT.svg]

Spec shape: see the "Spec format" section of ../SKILL.md. Node statuses: same, changed, new, mod.
Standard library only.
"""
import argparse
import json
import sys
import textwrap
from xml.sax.saxutils import escape

X0 = 30
IND = 34
ROWMIN = 34
MODMIN = 24
LH = 17
PADY = 9
ANN_X = 700
WRAP = 104
W = 1500
STATUSES = {'same', 'changed', 'new', 'mod'}

CSS = """:root{--bg:#ffffff;--fg:#212529;--mut:#6c757d;--line:#adb5bd;--sf:#f1f3f5;--sfs:#ced4da;--rd:#c92a2a;--rdf:#ffe3e3;--rds:#e03131;--nw:#e03131}
@media (prefers-color-scheme:dark){:root{--bg:#16181d;--fg:#e9ecef;--mut:#9aa3ad;--line:#5b636c;--sf:#22262c;--sfs:#4a515a;--rd:#ff8787;--rdf:#4a1f22;--rds:#ff6b6b;--nw:#e03131}}
text{fill:var(--fg)}
.bg{fill:var(--bg)}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:13px}
.same rect{fill:var(--sf);stroke:var(--sfs);stroke-width:1.2}
.same text{fill:var(--mut)}
.changed rect{fill:var(--rdf);stroke:var(--rds);stroke-width:2}
.changed text{fill:var(--rd);font-weight:600}
.new rect{fill:var(--nw);stroke:var(--nw);stroke-width:2}
.new text{fill:#fff;font-weight:700}
.lnk{stroke:var(--line);stroke-width:1.4;fill:none}
.note{font-size:13px}
.note.c{fill:var(--rd)}
.note.s{fill:var(--mut);font-size:12px}
.mod{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12px;fill:var(--mut)}
.modnote{font-size:12px;fill:var(--mut)}
.dot{fill:var(--rds)}
.ttl{font-size:22px;font-weight:700}
.h1{font-size:20px;font-weight:700}
.sub{font-size:13px;fill:var(--mut)}
.rule{stroke:var(--sfs);stroke-width:1.5}"""


def validate(spec):
    for key in ('title', 'subtitle', 'pages'):
        if key not in spec:
            sys.exit(f'spec is missing "{key}"')
    for page in spec['pages']:
        for key in ('title', 'sub', 'nodes'):
            if key not in page:
                sys.exit(f'page is missing "{key}": {page.get("title")}')
        for node in page['nodes']:
            if node['status'] not in STATUSES:
                sys.exit(f'unknown status {node["status"]!r} on {node["name"]}')
            if node['depth'] < 0:
                sys.exit(f'negative depth on {node["name"]}')


def box_width(name):
    return int(len(name) * 7.6 + 26)


def layout(spec):
    """Assign y positions; return (sections, y where the closing block starts)."""
    cur = 100
    sections = []
    for page in spec['pages']:
        head_y = cur
        cur += 70
        rows = []
        for node in page['nodes']:
            paras = [textwrap.wrap(n, WRAP) for n in node.get('notes', [])]
            n_lines = sum(len(p) for p in paras)
            if node['status'] == 'mod':
                height = max(MODMIN, n_lines * 15 + len(paras) * 3 + 6)
            elif n_lines:
                height = max(ROWMIN, n_lines * LH + len(paras) * 4 + 2 * PADY - 4)
            else:
                height = ROWMIN
            rows.append(dict(d=node['depth'], name=node['name'], st=node['status'],
                             lines=paras, y=cur, h=height))
            cur += height + (4 if node['status'] == 'mod' else 8)
        sections.append((page, head_y, rows))
        cur += 30
    return sections, cur


def render_svg(spec):
    validate(spec)
    sections, closing_y = layout(spec)
    other = spec.get('otherPages')
    other_lines = []
    if other:
        other_lines = [w for line in other['lines'] for w in textwrap.wrap(line, 170)]
    foot = spec.get('footnotes', [])
    if other:
        foot_y = closing_y + 48 + len(other_lines) * 18 + 22
    else:
        foot_y = closing_y + 8
    height = foot_y + len(foot) * 17 + 26

    out = []
    emit = out.append
    emit(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {height}" width="{W}" height="{height}" '
         'font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">')
    emit(f'<style>\n{CSS}\n</style>')
    emit('<rect class="bg" width="100%" height="100%"/>')
    emit(f'<text x="30" y="40" class="ttl">{escape(spec["title"])}</text>')
    emit(f'<text x="30" y="62" class="sub">{escape(spec["subtitle"])}</text>')
    emit('<g transform="translate(30,76)">\n'
         ' <g class="changed"><rect width="22" height="16" rx="3"/></g><text x="30" y="13" class="note">Edited component</text>\n'
         ' <g class="new" transform="translate(150,0)"><rect width="22" height="16" rx="3"/></g><text x="180" y="13" class="note">New component</text>\n'
         ' <g class="same" transform="translate(300,0)"><rect width="22" height="16" rx="3"/></g><text x="330" y="13" class="note">Unchanged component</text>\n'
         ' <text x="490" y="13" class="mod">↳ grey text</text><text x="600" y="13" class="note">Changed non-React module, under the component that calls it</text>\n'
         '</g>')

    for page, head_y, rows in sections:
        emit(f'<line class="rule" x1="30" x2="{W - 30}" y1="{head_y - 4}" y2="{head_y - 4}"/>')
        emit(f'<text x="30" y="{head_y + 24}" class="h1">{escape(page["title"])}</text>')
        emit(f'<text x="30" y="{head_y + 44}" class="sub">{escape(page["sub"])}</text>')
        stack = []
        for i, r in enumerate(rows):
            r['x'] = X0 + r['d'] * IND
            r['w'] = box_width(r['name'])
            if r['st'] == 'mod':
                r['parent'] = None
                continue
            while stack and rows[stack[-1]]['d'] >= r['d']:
                stack.pop()
            r['parent'] = stack[-1] if stack else None
            stack.append(i)
        for r in rows:
            if r['parent'] is not None:
                p = rows[r['parent']]
                emit(f'<path class="lnk" d="M{p["x"] + 14} {p["y"] + 28} V{r["y"] + 17} H{r["x"]}"/>')
        for r in rows:
            if r['st'] == 'mod':
                ty = r['y'] + 15
                emit(f'<text class="mod" x="{r["x"]}" y="{ty}">↳ {escape(r["name"])}</text>')
                nx = r['x'] + int(len(r['name'] + '↳ ') * 7.3) + 10
                if r['lines']:
                    emit(f'<path class="lnk" style="stroke-dasharray:2 5;stroke-width:1" d="M{nx} {ty - 4} H{ANN_X - 12}"/>')
                    for para in r['lines']:
                        for line in para:
                            emit(f'<text class="modnote" x="{ANN_X + 8}" y="{ty}">{escape(line)}</text>')
                            ty += 15
                        ty += 3
                continue
            emit(f'<g class="{r["st"]}"><rect x="{r["x"]}" y="{r["y"] + 3}" width="{r["w"]}" height="28" rx="5"/>'
                 f'<text class="mono" x="{r["x"] + 11}" y="{r["y"] + 22}">{escape(r["name"])}</text></g>')
            if r['st'] == 'new':
                emit(f'<g class="new"><rect x="{r["x"] + r["w"] + 6}" y="{r["y"] + 8}" width="36" height="18" rx="9"/>'
                     f'<text x="{r["x"] + r["w"] + 24}" y="{r["y"] + 21}" text-anchor="middle" style="font-size:10px">NEW</text></g>')
            if r['lines']:
                nx = r['x'] + r['w'] + (48 if r['st'] == 'new' else 8)
                colored = r['st'] != 'same'
                emit(f'<path class="lnk" style="stroke-dasharray:3 4" d="M{nx} {r["y"] + 17} H{ANN_X - 12}"/>')
                ty = r['y'] + PADY + 9
                for para in r['lines']:
                    for j, line in enumerate(para):
                        if colored and j == 0:
                            emit(f'<circle class="dot" cx="{ANN_X - 2}" cy="{ty - 4}" r="3"/>')
                        emit(f'<text class="note {"c" if colored else "s"}" x="{ANN_X + 8}" y="{ty}">{escape(line)}</text>')
                        ty += LH
                    ty += 4

    if other:
        emit(f'<line class="rule" x1="30" x2="{W - 30}" y1="{closing_y - 4}" y2="{closing_y - 4}"/>')
        emit(f'<text x="30" y="{closing_y + 24}" class="h1">{escape(other["heading"])}</text>')
        for k, line in enumerate(other_lines):
            emit(f'<text class="sub" x="30" y="{closing_y + 48 + k * 18}">{escape(line)}</text>')
    for k, line in enumerate(foot):
        emit(f'<text class="modnote" x="30" y="{foot_y + k * 17}">{escape(line)}</text>')
    emit('</svg>')
    svg = '\n'.join(out)
    if '\n\n' in svg:
        sys.exit('svg contains a blank line, which would end the HTML block in Markdown')
    return svg


def render_outline(spec):
    """Indented text outline: one line per node, notes beneath it."""
    lines = [spec['title'], spec['subtitle'], '']
    for page in spec['pages']:
        lines += [page['title'], page['sub'], '']
        for node in page['nodes']:
            pad = '  ' * node['depth']
            tag = {'same': 'unchanged', 'changed': 'CHANGED', 'new': 'NEW',
                   'mod': 'changed non-React module'}[node['status']]
            lines.append(f'{pad}- {node["name"]} [{tag}]')
            for note in node.get('notes', []):
                lines.append(f'{pad}    {note}')
        lines.append('')
    other = spec.get('otherPages')
    if other:
        lines += [other['heading']] + other['lines'] + ['']
    lines += spec.get('footnotes', [])
    return '\n'.join(lines) + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('spec')
    ap.add_argument('--md', required=True, help='Markdown file with the SVG inline')
    ap.add_argument('--outline', help='plain-text outline of the tree and notes')
    ap.add_argument('--svg', help='also write the bare SVG')
    args = ap.parse_args()
    with open(args.spec, encoding='utf-8') as f:
        spec = json.load(f)
    svg = render_svg(spec)
    with open(args.md, 'w', encoding='utf-8') as f:
        f.write(svg + '\n')
    if args.svg:
        with open(args.svg, 'w', encoding='utf-8') as f:
            f.write(svg)
    if args.outline:
        with open(args.outline, 'w', encoding='utf-8') as f:
            f.write(render_outline(spec))


if __name__ == '__main__':
    main()
