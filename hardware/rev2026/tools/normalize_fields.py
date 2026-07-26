"""One-shot: flatten ${ALTIUM_VALUE}, rename fields to canonical names,
strip Altium metadata.

Overrides the plan's regex-based approach (see task-3 brief) with a
structural rewrite: the schematic is parsed with the Task 1 s-expression
parser (`kicad_parse.parse`), and `kicad_parse.property_span()` locates the
exact source span of each `(property ...)` block we touch. All edits are
computed as (start, end, replacement) spans against the *original* text and
applied back-to-front, so no edit can shift the offsets used by another.
This avoids the classic regex-on-s-expressions failure mode where a
parenthesis inside a property value corrupts unrelated content.

Three jobs, per symbol:
  1. Flatten Value: if a symbol's Value is the literal string
     "${ALTIUM_VALUE}" and it carries its own ALTIUM_VALUE property, replace
     the Value property's text with the literal value from ALTIUM_VALUE.
     (C5 has no ALTIUM_VALUE property at all -- that symbol is left with an
     unresolved Value for a later explicit fix, matching the audit finding
     that C5's value is simply missing upstream.)
  2. Rename fields in RENAME to their canonical names.
  3. Delete property blocks named in DROP (cruft has no replacement value).

Only `(property ...)` blocks that are direct children of a placed `(symbol
...)` node are touched -- `lib_symbols` definitions and anything else in the
file are untouched.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'tests'))
import kicad_parse as kp

SCH = pathlib.Path(__file__).resolve().parents[1] / 'picoemp-rev2026.kicad_sch'

RENAME = {
    'MANUFACTURE PART NUMBER 1': 'MPN',
    'MANUFACTURER_PART_NUMBER': 'MPN',
    'MANUFACTURE 1': 'Manufacturer',
    'MANUFACTURER_NAME': 'Manufacturer',
    'SUPPLIER PART NUMBER 1': 'DigiKey',
}

DROP = {
    'PART NUMBER', 'COMPONENT GROUP', 'COMPONENT KIND', 'COMPONENT TYPE',
    'PIN COUNT', 'PP MATERIAL STACK', 'PP ROTATION', 'PP ROTATION1',
    'MOUNTING TECHNOLOGY', 'LATESTREVISIONDATE', 'LATESTREVISIONNOTE',
    'PUBLISHER', 'SNAPEDA_LINK', 'CHECK_PRICES', 'AVAILABILITY', 'PRICE',
    'SUPPLIER 1', 'MOUSER PART NUMBER', 'MOUSER PRICE/STOCK',
    'ARROW PART NUMBER', 'ARROW PRICE/STOCK', 'ROHS', 'CASE-EIA',
    'CASE-METRIC', 'RATED POWER', 'RATED VOLTAGE', 'TOLERANCE',
    'TEMPERATURE RANGE', 'HEIGHT', 'PACKAGE', 'PURCHASE-URL', 'MP', 'MF',
    'DATASHEET LINK', 'ALTIUM_VALUE',
}


def _prop_nodes(symbol_node):
    return [e for e in symbol_node
            if isinstance(e, list) and e and e[0] == 'property']


def _extend_for_deletion(text, start, end):
    """Extend a property block's span backward to swallow its own leading
    newline + indentation, so deleting it doesn't leave a blank line."""
    s = start
    while s > 0 and text[s - 1] in ' \t':
        s -= 1
    if s > 0 and text[s - 1] == '\n':
        s -= 1
    return s, end


def compute_edits(text, tree):
    edits = []  # (start, end, replacement)

    for node in tree:
        if not (isinstance(node, list) and node and node[0] == 'symbol'):
            continue
        props = _prop_nodes(node)

        altium_value = None
        for e in props:
            if kp.sval(e[1]) == 'ALTIUM_VALUE':
                altium_value = kp.sval(e[2])

        for e in props:
            name = kp.sval(e[1])

            # 1. Flatten Value == "${ALTIUM_VALUE}" using this symbol's own
            #    ALTIUM_VALUE property, if it has one.
            if name == 'Value' and kp.sval(e[2]) == '${ALTIUM_VALUE}' and altium_value is not None:
                seg = text[e.start:e.end]
                old_frag = '(property "Value" "${ALTIUM_VALUE}"'
                assert seg.startswith(old_frag), (
                    f'unexpected Value property text at offset {e.start}: {seg[:60]!r}'
                )
                new_frag = f'(property "Value" "{altium_value}"'
                edits.append((e.start, e.start + len(old_frag), new_frag))
                continue

            # 2. Rename.
            if name in RENAME:
                seg = text[e.start:e.end]
                old_frag = f'"{name}"'
                assert old_frag in seg[:len(name) + 20], (
                    f'rename target {name!r} not found at start of property block, offset {e.start}'
                )
                idx = seg.index(old_frag)
                new_seg = seg[:idx] + f'"{RENAME[name]}"' + seg[idx + len(old_frag):]
                edits.append((e.start, e.end, new_seg))
                continue

            # 3. Drop.
            if name in DROP:
                s, end = _extend_for_deletion(text, e.start, e.end)
                edits.append((s, end, ''))
                continue

    edits.sort(key=lambda x: x[0])
    for i in range(1, len(edits)):
        assert edits[i][0] >= edits[i - 1][1], (
            f'overlapping edits at offsets {edits[i - 1]} and {edits[i]}'
        )
    return edits


def apply_edits(text, edits):
    for start, end, repl in sorted(edits, key=lambda x: -x[0]):
        text = text[:start] + repl + text[end:]
    return text


def main():
    text = SCH.read_text(encoding='utf-8')
    tree = kp.parse(text)[0]
    edits = compute_edits(text, tree)
    new_text = apply_edits(text, edits)
    SCH.write_text(new_text, encoding='utf-8')
    print(f'{len(edits)} edits applied')


if __name__ == '__main__':
    main()
