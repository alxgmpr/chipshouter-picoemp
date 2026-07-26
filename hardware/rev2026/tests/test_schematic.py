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


ALTIUM_CRUFT = {
    'PART NUMBER', 'ALTIUM_VALUE', 'COMPONENT GROUP', 'COMPONENT KIND',
    'COMPONENT TYPE', 'PIN COUNT', 'PP MATERIAL STACK', 'PP ROTATION',
    'PP ROTATION1', 'MOUNTING TECHNOLOGY', 'LATESTREVISIONDATE',
    'LATESTREVISIONNOTE', 'PUBLISHER', 'SNAPEDA_LINK', 'CHECK_PRICES',
    'AVAILABILITY', 'PRICE', 'MANUFACTURE 1', 'MANUFACTURE PART NUMBER 1',
    'SUPPLIER 1', 'SUPPLIER PART NUMBER 1', 'MANUFACTURER_NAME',
    'MANUFACTURER_PART_NUMBER', 'MOUSER PART NUMBER', 'MOUSER PRICE/STOCK',
    'ARROW PART NUMBER', 'ARROW PRICE/STOCK', 'DATASHEET LINK', 'ROHS',
    'CASE-EIA', 'CASE-METRIC', 'RATED POWER', 'RATED VOLTAGE', 'TOLERANCE',
    'TEMPERATURE RANGE', 'HEIGHT', 'PACKAGE', 'PURCHASE-URL', 'MP', 'MF',
}


def test_no_unresolved_value_variables(syms):
    bad = [s.ref for s in syms if '${' in s.value]
    assert not bad, f'symbols with unresolved value variables: {bad}'


def test_c5_has_its_value(syms):
    c5 = next(s for s in syms if s.ref == 'C5')
    assert c5.value == '100n'


def test_no_altium_cruft_fields(syms):
    offenders = {s.ref: sorted(set(s.props) & ALTIUM_CRUFT)
                 for s in syms if set(s.props) & ALTIUM_CRUFT}
    assert not offenders, f'Altium metadata remains: {offenders}'


def test_r9_part_data_is_2k_not_75r():
    """Upstream bug: R9 carried R4's part data throughout."""
    import conftest
    syms = kp.symbols(kp.parse_file(conftest.SCH))
    r9 = next(s for s in syms if s.ref == 'R9')
    assert r9.value == '2k'
    assert r9.props.get('MPN') == 'RC0805FR-072KL'
    assert r9.props.get('DigiKey') == '311-2.00KCRCT-ND'
