import kicad_parse as kp


def test_node_span_round_trips_source_text():
    """text[node.start:node.end] must reproduce the exact source slice
    for arbitrary nested lists, not just top-level ones."""
    text = '(a (b "x y" 1) (c (d 2 3)))'
    tree = kp.parse(text)[0]
    assert text[tree.start:tree.end] == text

    b_node = tree[1]
    assert text[b_node.start:b_node.end] == '(b "x y" 1)'

    d_node = tree[2][1]
    assert text[d_node.start:d_node.end] == '(d 2 3)'


def test_property_span_on_real_schematic(sch):
    """property_span() must locate a real (property ...) block by name
    within a symbol and its span must round-trip against the source file,
    including the value of the property itself."""
    import pathlib
    text = pathlib.Path(__file__).resolve().parents[1].joinpath(
        'picoemp-rev2026.kicad_sch'
    ).read_text(encoding='utf-8')

    symbol_nodes = [
        n for n in sch if isinstance(n, list) and n and n[0] == 'symbol'
    ]
    found = False
    for node in symbol_nodes:
        span = kp.property_span(node, 'Reference')
        if span is None:
            continue
        found = True
        start, end = span
        block_text = text[start:end]
        assert block_text.startswith('(property')
        assert block_text.endswith(')')
        assert '"Reference"' in block_text
    assert found, 'expected at least one symbol with a Reference property'


def test_property_span_missing_returns_none(sch):
    symbol_nodes = [
        n for n in sch if isinstance(n, list) and n and n[0] == 'symbol'
    ]
    assert symbol_nodes, 'no symbols parsed from schematic'
    assert kp.property_span(symbol_nodes[0], 'NoSuchProperty12345') is None
