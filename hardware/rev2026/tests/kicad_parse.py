"""Minimal KiCad s-expression parser and accessors for design-rule tests.

In addition to the parser/accessors, this module exposes source byte
(character) offsets for every parsed s-expression list, so later tooling
(see Task 3) can locate and remove a `(property ...)` block structurally
instead of with regex. Offsets are Python string indices into the text
passed to `parse()` (i.e. the same string you'd get back from
`open(path, encoding='utf-8').read()`), not raw on-disk byte offsets --
for pure-ASCII KiCad files the two coincide, but callers that need exact
raw-byte offsets on a file containing multi-byte UTF-8 characters should
re-encode and re-measure rather than assume equivalence.
"""
import pathlib
import re
from dataclasses import dataclass, field


def _tokens(s):
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c == '"':
            start = i
            j, buf = i + 1, []
            while j < n:
                if s[j] == '\\':
                    buf.append(s[j + 1]); j += 2; continue
                if s[j] == '"':
                    break
                buf.append(s[j]); j += 1
            yield ('str', ''.join(buf), start); i = j + 1
        elif c in '()':
            yield ('paren', c, i); i += 1
        elif c.isspace():
            i += 1
        else:
            j = i
            while j < n and not s[j].isspace() and s[j] not in '()"':
                j += 1
            yield ('sym', s[i:j], i); i = j


class Node(list):
    """A parsed s-expression list that also remembers its source span.

    `node.start` / `node.end` are string offsets such that
    `text[node.start:node.end]` reproduces the exact source text of this
    s-expression (including its enclosing parens), assuming `text` is the
    same string that was passed to `parse()`.
    """
    __slots__ = ('start', 'end')


def parse(text):
    """Parse s-expression text. Quoted strings become ('S', value) tuples.

    Every parenthesized list in the result is a `Node` (a list subclass)
    carrying `.start`/`.end` source-offset attributes.
    """
    stack = [[]]
    starts = [None]
    for kind, val, pos in _tokens(text):
        if kind == 'paren':
            if val == '(':
                stack.append([])
                starts.append(pos)
            else:
                node = Node(stack.pop())
                node.start = starts.pop()
                node.end = pos + 1
                stack[-1].append(node)
        elif kind == 'sym':
            stack[-1].append(val)
        else:
            stack[-1].append(('S', val))
    return stack[0]


def parse_file(path):
    return parse(open(path, encoding='utf-8').read())[0]


def sval(x):
    """Unwrap a quoted-string node, else None."""
    return x[1] if isinstance(x, tuple) and x and x[0] == 'S' else None


def _walk(node, name):
    """Yield every sub-list whose head is `name`, at any depth."""
    if isinstance(node, list):
        if node and node[0] == name:
            yield node
        for child in node:
            yield from _walk(child, name)


def property_span(node, prop_name):
    """Return the (start, end) source-offset span of the direct child
    `(property "prop_name" ...)` block of `node`, or None if absent.

    `node` must have been produced by `parse()`/`parse_file()` so its
    children are `Node` instances carrying offsets. Intended to let a
    later structural-rewrite step (e.g. deleting a stale property) slice
    the original text rather than pattern-match it with regex.
    """
    for e in node:
        if isinstance(e, list) and e and e[0] == 'property' and sval(e[1]) == prop_name:
            return (e.start, e.end)
    return None


@dataclass
class Symbol:
    ref: str = ''
    value: str = ''
    lib_id: str = ''
    footprint: str = ''
    props: dict = field(default_factory=dict)
    in_bom: bool = True
    dnp: bool = False


@dataclass
class Footprint:
    ref: str = ''
    lib_id: str = ''
    value: str = ''
    pads: list = field(default_factory=list)


def symbols(tree, include_power=False):
    out = []
    for node in tree:
        if not (isinstance(node, list) and node and node[0] == 'symbol'):
            continue
        s = Symbol()
        for e in node:
            if not isinstance(e, list) or not e:
                continue
            if e[0] == 'lib_id':
                s.lib_id = sval(e[1]) or ''
            elif e[0] == 'property':
                s.props[sval(e[1])] = sval(e[2])
            elif e[0] == 'in_bom':
                s.in_bom = (e[1] == 'yes')
            elif e[0] == 'dnp':
                s.dnp = (e[1] == 'yes')
        s.ref = s.props.get('Reference', '')
        s.value = s.props.get('Value', '')
        s.footprint = s.props.get('Footprint', '') or ''
        if s.ref.startswith('#') and not include_power:
            continue
        out.append(s)
    return out


def footprints(tree):
    out = []
    for node in _walk(tree, 'footprint'):
        f = Footprint(lib_id=sval(node[1]) or '')
        for e in node:
            if isinstance(e, list) and e and e[0] == 'property':
                if sval(e[1]) == 'Reference':
                    f.ref = sval(e[2]) or ''
                elif sval(e[1]) == 'Value':
                    f.value = sval(e[2]) or ''
        for pad in _walk(node, 'pad'):
            num = sval(pad[1]) or ''
            at = next((c for c in pad if isinstance(c, list) and c and c[0] == 'at'), None)
            if at:
                f.pads.append((num, float(at[1]), float(at[2])))
        out.append(f)
    return out


def ref_key(ref):
    """Sort key: ('R', 9) for 'R9'. Lets R9 sort before R10."""
    m = re.match(r'([A-Za-z]+)(\d+)', ref)
    return (m.group(1), int(m.group(2))) if m else (ref, 0)


def _version_key(name):
    """Sort key for a plugin version directory name like '2.0.0'.

    Purely-numeric dot-separated versions sort numerically (so '10.0.0' >
    '2.0.0'); anything else falls back to a string comparison, bucketed
    after all numeric versions so the two schemes never get compared
    against each other.
    """
    try:
        return (0, tuple(int(p) for p in name.split('.')))
    except ValueError:
        return (1, name)


def kicad_happy_skills():
    """Locate the installed kicad-happy plugin's `skills` directory.

    Globs `~/.claude/plugins/cache/kicad-happy/kicad-happy/*/skills` and
    returns the path under the highest version directory found, so
    callers don't have to hardcode a specific plugin version (which
    breaks the moment the plugin is upgraded).

    Raises RuntimeError if no such directory exists.
    """
    base = pathlib.Path.home() / '.claude' / 'plugins' / 'cache' / 'kicad-happy' / 'kicad-happy'
    candidates = sorted(base.glob('*/skills'), key=lambda p: _version_key(p.parent.name))
    if not candidates:
        raise RuntimeError(
            f'kicad-happy skills directory not found under {base} '
            '(globbing "*/skills"). Is the kicad-happy plugin installed?'
        )
    return candidates[-1]
