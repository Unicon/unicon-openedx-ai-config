#!/usr/bin/env python3
"""Render a PR reading-order spec as one SVG: threads of boxes, top to bottom, with ACs beside them.

Usage:
    python3 render_reading_order.py SPEC.json --acs 683=ticket683.md [--acs 682=ticket682.md] --svg OUT.svg

Each --acs file is a ticket body; the Gherkin scenarios inside its fenced code blocks are the
acceptance criteria. The spec names ACs by scenario title, and the renderer copies their text
verbatim from the ticket, so the drawing never paraphrases a criterion. Every AC must appear
in a thread or in "elsewhere", and with --changed-files every changed file must be named
in some "where". Spec shape: see the "Spec format" section of ../SKILL.md.
Standard library only.
"""
import argparse
import difflib
import json
import re
import sys
import textwrap
from collections import namedtuple
from xml.sax.saxutils import escape

AC = namedtuple('AC', 'ticket title text')

W = 1640
X0 = 30
BOX_W = 560
ANN_X = X0 + BOX_W + 50
BOX_WRAP = 72
NAME_WRAP = 62
AC_WRAP = 122
NOTE_WRAP = 120
LH = 17
PAD = 10
GAP = 34
KINDS = {'source', 'test'}

CSS = """:root{--bg:#ffffff;--fg:#212529;--mut:#6c757d;--line:#868e96;--ac:#1c3d5a;--acb:#f1f5f9;--x:#7048e8;--l:88%;--s:70%;--sl:34%;--mf:#ffc9c9}
@media (prefers-color-scheme:dark){:root{--bg:#16181d;--fg:#e9ecef;--mut:#9aa3ad;--line:#868e96;--ac:#c5d6e8;--acb:#1f252d;--x:#b197fc;--l:22%;--s:45%;--sl:62%;--mf:#5c1a1d}}
text{fill:var(--fg);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;font-size:13px}
.bg{fill:var(--bg)}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.box{fill:hsl(var(--h),var(--s),var(--l));stroke:hsl(var(--h),70%,var(--sl));stroke-width:2}
.box.test{stroke-dasharray:6 4}
.box.missing{fill:var(--mf);stroke:#e03131;stroke-width:2.5}
.box.plain{fill:var(--acb);stroke:var(--line);stroke-width:1.2}
.name{font-weight:700;font-size:14px}
.where{font-size:12px;fill:var(--mut)}
.blast{font-size:12px;font-weight:600}
.acbg{fill:var(--acb)}
.ac{font-size:12px;fill:var(--ac)}
.aclbl{font-size:11px;fill:var(--mut);font-weight:600}
.x{font-size:12.5px;fill:var(--x)}
.arrow{stroke:var(--line);stroke-width:2;fill:none}
.head{fill:var(--line)}
.ttl{font-size:22px;font-weight:700}
.h1{font-size:19px;font-weight:700}
.sub{font-size:13px;fill:var(--mut)}
.rule{stroke:var(--line);stroke-width:1;opacity:.5}"""


def parse_scenarios(text):
    """Return {title: verbatim scenario text} from a ticket body.

    Only fenced code blocks are read when the body has any, so a scenario quoted in prose is
    not mistaken for a criterion.
    """
    blocks = re.findall(r'^```[^\n]*\n(.*?)^```', text, flags=re.S | re.M)
    source = '\n'.join(blocks) if blocks else text
    scenarios = {}
    current = None
    for line in source.splitlines():
        m = re.match(r'\s*Scenario(?: Outline)?:\s*(.+?)\s*$', line)
        if m:
            current = m.group(1)
            scenarios[current] = [line.rstrip()]
        elif current is not None:
            scenarios[current].append(line.rstrip())
    return {title: '\n'.join(lines).rstrip('\n').rstrip() for title, lines in scenarios.items()}


def load_acs(pairs):
    acs = []
    for pair in pairs:
        ticket, _, path = pair.partition('=')
        if not path:
            sys.exit(f'--acs expects TICKET=PATH, got {pair!r}')
        with open(path) as f:
            scenarios = parse_scenarios(f.read())
        if not scenarios:
            sys.exit(f'no Gherkin scenarios found in {path}')
        acs.extend(AC(ticket, title, text) for title, text in scenarios.items())
    return acs


def blast_hue(score):
    return round(120 * (1 - score / 100))


def resolve(ref, acs):
    """Map a spec reference ("Title" or "TICKET:Title") to its AC, or exit with a useful message."""
    ticket, sep, title = ref.partition(':')
    if sep and any(a.ticket == ticket for a in acs):
        matches = [a for a in acs if a.ticket == ticket and a.title == title]
    else:
        matches = [a for a in acs if a.title == ref]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        sys.exit(f'AC {ref!r} is ambiguous across tickets; write it as "TICKET:{ref}"')
    close = difflib.get_close_matches(ref, [a.title for a in acs], n=1)
    hint = f'; did you mean {close[0]!r}?' if close else ''
    sys.exit(f'unknown AC {ref!r}{hint}')


def validate(spec, acs, changed_files=()):
    for key in ('title', 'subtitle', 'threads'):
        if key not in spec:
            sys.exit(f'spec is missing "{key}"')
    seen = set()
    for thread in spec['threads']:
        for key in ('title', 'summary', 'steps'):
            if key not in thread:
                sys.exit(f'thread is missing "{key}": {thread.get("title")}')
        for step in thread['steps']:
            for key in ('name', 'where', 'kind', 'does', 'blast'):
                if key not in step:
                    sys.exit(f'step is missing "{key}": {step.get("name")}')
            if step['kind'] not in KINDS:
                sys.exit(f'unknown kind {step["kind"]!r} on {step["name"]}')
            check_blast(step['blast'], step['name'])
            check_one_sentence(step['does'], step['name'])
            seen.update(resolve(ref, acs) for ref in step.get('acs', []))
    for item in spec.get('elsewhere', []):
        for key in ('ac', 'where', 'note'):
            if key not in item:
                sys.exit(f'elsewhere entry is missing "{key}": {item.get("ac")}')
        if 'blast' in item:
            check_blast(item['blast'], item['ac'])
        seen.add(resolve(item['ac'], acs))
    for item in spec.get('leftovers', []):
        for key in ('where', 'does', 'blast'):
            if key not in item:
                sys.exit(f'leftover is missing "{key}": {item.get("where")}')
        check_blast(item['blast'], item['where'])
        check_one_sentence(item['does'], item['where'])
    missing = [f'{a.ticket}:{a.title}' for a in acs if a not in seen]
    if missing:
        sys.exit('ACs in neither a thread nor "elsewhere": ' + '; '.join(missing))
    wheres = [step['where'] for thread in spec['threads'] for step in thread['steps']]
    wheres += [item['where'] for key in ('elsewhere', 'leftovers') for item in spec.get(key, [])]
    undrawn = [path for path in changed_files if not any(names_file(where, path) for where in wheres)]
    if undrawn:
        sys.exit('changed files named in no "where" (add them to a step, "elsewhere" or "leftovers"): '
                 + ', '.join(undrawn))


def names_file(where, path):
    """True when a "where" text names the file by its file name."""
    name = path.rsplit('/', 1)[-1]
    return re.search(r'(?<![\w.-])' + re.escape(name) + r'(?![\w-])', where) is not None


def check_one_sentence(text, name):
    if re.search(r'[.!?]["\')]?\s+[A-Z]', text):
        sys.exit(f'"does" must be one sentence on {name}: {text!r}')


def check_blast(score, name):
    if not isinstance(score, int) or not 0 <= score <= 100:
        sys.exit(f'blast must be an integer 0-100 on {name}, got {score!r}')


def wrap(text, width, indent_continuation=False):
    """Wrap one line, keeping leading spaces; continuation lines get two extra spaces if asked."""
    lead = len(text) - len(text.lstrip(' '))
    sub = ' ' * (lead + (2 if indent_continuation else 0))
    return textwrap.wrap(text, width, initial_indent=' ' * lead, subsequent_indent=sub,
                         drop_whitespace=True) or ['']


class Out:
    def __init__(self):
        self.parts = []

    def text(self, x, y, s, cls='', extra=''):
        c = f' class="{cls}"' if cls else ''
        self.parts.append(f'<text x="{x}" y="{y}"{c}{extra}>{escape(s)}</text>')

    def raw(self, s):
        self.parts.append(s)


def box_lines(step):
    lines = [(l, 'name mono') for l in textwrap.wrap(step['name'], NAME_WRAP)]
    lines += [(l, 'where mono') for l in textwrap.wrap(step['where'], NAME_WRAP + 8)]
    lines += [(l, '') for l in textwrap.wrap(step['does'], BOX_WRAP)]
    if 'blast' in step:
        kind = 'test file, ' if step.get('kind') == 'test' else ''
        why = f': {step["blastWhy"]}' if step.get('blastWhy') else ''
        lines += [(l, 'blast') for l in textwrap.wrap(f'Blast radius {step["blast"]} ({kind}0-100){why}', BOX_WRAP)]
    return lines


def ann_blocks(step, acs):
    """Annotation column for a step: each AC verbatim, then behavior no AC asked for."""
    blocks = []
    for ref in step.get('acs', []):
        ac = resolve(ref, acs)
        lines = []
        for raw in ac.text.splitlines():
            lines.extend(wrap(raw, AC_WRAP, indent_continuation=True))
        blocks.append(('ac', f'#{ac.ticket}' if ac.ticket.isdigit() else ac.ticket, lines))
    for note in step.get('notInAcs', []):
        blocks.append(('x', None, textwrap.wrap(f'Not in any AC: {note}', NOTE_WRAP)))
    return blocks


def ann_height(blocks):
    h = 0
    for kind, label, lines in blocks:
        h += (LH if label else 0) + len(lines) * LH + (2 * PAD if kind == 'ac' else 4) + 8
    return h


def draw_ann(out, y, blocks):
    for kind, label, lines in blocks:
        if kind == 'ac':
            h = LH + len(lines) * LH + 2 * PAD
            out.raw(f'<rect class="acbg" x="{ANN_X}" y="{y}" width="{W - ANN_X - X0}" height="{h}" rx="6"/>')
            ty = y + PAD + 12
            out.text(ANN_X + 12, ty, f'{label} acceptance criterion', 'aclbl')
            for line in lines:
                ty += LH
                out.text(ANN_X + 12, ty, line, 'ac mono', ' xml:space="preserve"')
            y += h + 8
        else:
            ty = y + 12
            for line in lines:
                out.text(ANN_X + 4, ty, line, 'x')
                ty += LH
            y += len(lines) * LH + 4 + 8


def draw_box(out, y, lines, cls, hue):
    h = len(lines) * LH + 2 * PAD
    style = f' style="--h:{hue}"' if hue is not None else ''
    out.raw(f'<rect class="box {cls}"{style} x="{X0}" y="{y}" width="{BOX_W}" height="{h}" rx="8"/>')
    ty = y + PAD + 13
    for line, lcls in lines:
        out.text(X0 + 14, ty, line, lcls)
        ty += LH
    return h


def arrow(out, y1, y2):
    x = X0 + BOX_W // 2
    out.raw(f'<line class="arrow" x1="{x}" y1="{y1}" x2="{x}" y2="{y2 - 8}"/>'
            f'<path class="head" d="M{x - 6},{y2 - 9} L{x + 6},{y2 - 9} L{x},{y2} Z"/>')


def legend(out, y):
    out.raw('<defs><linearGradient id="g" x1="0" x2="1">'
            '<stop offset="0" stop-color="hsl(120,65%,55%)"/><stop offset=".5" stop-color="hsl(60,65%,55%)"/>'
            '<stop offset="1" stop-color="hsl(0,65%,55%)"/></linearGradient></defs>')
    out.text(X0, y + 13, 'Box color is blast radius:', 'sub')
    out.text(X0 + 180, y + 13, '0', 'sub')
    out.raw(f'<rect x="{X0 + 194}" y="{y + 2}" width="220" height="14" rx="3" fill="url(#g)"/>')
    out.text(X0 + 420, y + 13, '100', 'sub')
    out.raw(f'<rect class="box test plain" x="{X0 + 470}" y="{y}" width="40" height="18" rx="4"/>')
    out.text(X0 + 518, y + 13, 'dashed border is a test file', 'sub')
    out.raw(f'<rect class="acbg" x="{X0 + 720}" y="{y}" width="40" height="18" rx="4"/>')
    out.text(X0 + 768, y + 13, 'acceptance criterion, verbatim from the ticket', 'sub')
    out.text(X0 + 1090, y + 13, 'Not in any AC: behavior the diff adds', 'x')


def render_svg(spec, acs, changed_files=()):
    validate(spec, acs, changed_files)
    out = Out()
    out.text(X0, 40, spec['title'], 'ttl')
    y = 62
    for line in textwrap.wrap(spec['subtitle'], 200):
        out.text(X0, y, line, 'sub')
        y += LH
    legend(out, y + 6)
    y += 48

    for t, thread in enumerate(spec['threads'], 1):
        out.raw(f'<line class="rule" x1="{X0}" y1="{y}" x2="{W - X0}" y2="{y}"/>')
        y += 30
        out.text(X0, y, thread['title'], 'h1')
        for line in textwrap.wrap(thread['summary'], 190):
            y += LH + 2
            out.text(X0, y, line, 'sub')
        y += 18
        for s, step in enumerate(thread['steps'], 1):
            step = dict(step, name=f'{t}.{s}  {step["name"]}')
            lines = box_lines(step)
            blocks = ann_blocks(step, acs)
            bh = draw_box(out, y, lines, step['kind'], blast_hue(step['blast']))
            draw_ann(out, y, blocks)
            row = max(bh, ann_height(blocks))
            if s < len(thread['steps']):
                arrow(out, y + bh, y + row + GAP)
            y += row + GAP
        y += 10

    if spec.get('elsewhere'):
        out.raw(f'<line class="rule" x1="{X0}" y1="{y}" x2="{W - X0}" y2="{y}"/>')
        y += 30
        out.text(X0, y, 'Acceptance criteria outside the main threads', 'h1')
        y += LH + 2
        out.text(X0, y, 'Where each one is implemented, and how far it is tested. Read these after the threads.', 'sub')
        y += 18
        for item in spec['elsewhere']:
            lines = [(l, 'where mono') for l in textwrap.wrap(item['where'], NAME_WRAP + 8)]
            lines += [(l, '') for l in textwrap.wrap(item['note'], BOX_WRAP)]
            if item.get('missing'):
                lines.insert(0, ('NOT IMPLEMENTED', 'name'))
            hue = blast_hue(item['blast']) if 'blast' in item else None
            cls = 'missing' if item.get('missing') else ('' if hue is not None else 'plain')
            blocks = ann_blocks({'acs': [item['ac']]}, acs)
            bh = draw_box(out, y, lines, cls, hue)
            draw_ann(out, y, blocks)
            y += max(bh, ann_height(blocks)) + 14

    if spec.get('leftovers'):
        out.raw(f'<line class="rule" x1="{X0}" y1="{y}" x2="{W - X0}" y2="{y}"/>')
        y += 30
        out.text(X0, y, 'Everything else in the diff: skim last', 'h1')
        y += 18
        for item in spec['leftovers']:
            lines = textwrap.wrap(item['does'], 150)
            where = textwrap.wrap(item['where'], 58)
            n = max(len(lines), len(where))
            out.raw(f'<rect class="box" style="--h:{blast_hue(item["blast"])}" x="{X0}" y="{y}" '
                    f'width="34" height="{n * LH + 6}" rx="4"/>')
            out.text(X0 + 8, y + 16, str(item['blast']), 'blast')
            for i, line in enumerate(where):
                out.text(X0 + 48, y + 16 + i * LH, line, 'mono where')
            for i, line in enumerate(lines):
                out.text(ANN_X - 120, y + 16 + i * LH, line)
            y += n * LH + 14

    for note in spec.get('footnotes', []):
        y += 6
        for line in textwrap.wrap(note, 200):
            y += LH
            out.text(X0, y, line, 'sub')

    h = y + 40
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}">'
            f'<style>{CSS}</style><rect class="bg" width="{W}" height="{h}"/>'
            + ''.join(out.parts) + '</svg>\n')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('spec')
    ap.add_argument('--acs', action='append', required=True, metavar='TICKET=PATH')
    ap.add_argument('--changed-files', metavar='PATH',
                    help='one changed file path per line; each must be named in some "where"')
    ap.add_argument('--svg', required=True)
    args = ap.parse_args(argv)
    with open(args.spec) as f:
        spec = json.load(f)
    changed = []
    if args.changed_files:
        with open(args.changed_files) as f:
            changed = [line.strip() for line in f if line.strip()]
    svg = render_svg(spec, load_acs(args.acs), changed)
    with open(args.svg, 'w') as f:
        f.write(svg)
    print(args.svg)
    print(summary(spec, load_acs(args.acs), changed))


def summary(spec, acs, changed_files):
    """One line stating what the validation covered, so a passing render is checkable."""
    in_threads = {resolve(ref, acs) for t in spec['threads'] for s in t['steps'] for ref in s.get('acs', [])}
    elsewhere = spec.get('elsewhere', [])
    missing = sum(1 for item in elsewhere if item.get('missing'))
    n = len(spec['threads'])
    files = f'{len(changed_files)} changed files all named' if changed_files else 'changed files not checked'
    return (f'{n} thread{"s" if n != 1 else ""}; {len(acs)} ACs: {len(in_threads)} in threads, '
            f'{len(elsewhere)} elsewhere ({missing} missing); {files}')


if __name__ == '__main__':
    main()
