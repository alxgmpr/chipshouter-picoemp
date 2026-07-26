import kicad_parse as kp

# Every non-power reference expected in the design, post-rework.
EXPECTED_REFS = {
    'C1', 'C2', 'C3', 'C5', 'C6',
    'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9',
    'FID1', 'FID2', 'FID3',
    'J1', 'J2', 'J3', 'J4',
    'MH1', 'MH2', 'MH3',
    'P1', 'P2', 'P3',
    'Q1', 'Q2', 'Q3', 'Q4',
    'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R9',
    'R10', 'R11', 'R12', 'R13', 'R14', 'R15', 'R16',
    'SW1', 'SW2', 'SW3',
    'T1', 'T2',
    'U1', 'U2',
}


def test_parser_finds_symbols(syms):
    """Sanity: the parser reads a plausible number of components."""
    assert len(syms) > 30


def test_every_symbol_has_a_reference(syms):
    assert all(s.ref for s in syms)


def test_no_duplicate_references(syms):
    refs = [s.ref for s in syms]
    dupes = {r for r in refs if refs.count(r) > 1}
    assert not dupes, f'duplicate refs: {sorted(dupes)}'
