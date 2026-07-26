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


def test_no_wildcard_or_altium_lib_ids(syms):
    bad = [(s.ref, s.lib_id) for s in syms
           if '*' in s.lib_id or 'AltiumLib' in s.lib_id or 'DBLib' in s.lib_id]
    assert not bad, f'unresolvable lib_ids: {bad}'


def test_mosfets_are_enhancement_not_depletion(syms):
    bad = [s.ref for s in syms if 'Depletion' in s.lib_id]
    assert not bad, f'depletion-mode symbol used for enhancement parts: {bad}'


def test_igbt_uses_igbt_symbol(syms):
    q2 = next(s for s in syms if s.ref == 'Q2')
    assert q2.lib_id == 'picoemp:IGBT_NCH_Diode'


def test_rectifiers_are_not_schottky(syms):
    """Upstream errata: D1/D3/D4/D5 were never Schottky diodes."""
    for ref in ('D1', 'D3', 'D4', 'D5'):
        s = next(x for x in syms if x.ref == ref)
        assert 'Schottky' not in s.lib_id, f'{ref} still drawn as Schottky'


def test_opto_uses_custom_symbol(syms):
    q1 = next(s for s in syms if s.ref == 'Q1')
    assert q1.lib_id == 'picoemp:LDA111'


def test_transformers_use_project_symbol(syms):
    for ref in ('T1', 'T2'):
        s = next(x for x in syms if x.ref == ref)
        assert s.lib_id == 'picoemp:ATB322524'


def test_mosfets_use_numeric_pin_symbol(syms):
    """SOT-23 pads are 1/2/3, so the symbol's pins must be too."""
    for ref in ('Q3', 'Q4'):
        s = next(x for x in syms if x.ref == ref)
        assert s.lib_id == 'Transistor_FET:Q_NMOS_GSD'


# Target footprints from the Rev-2026 design spec (docs/superpowers/specs/
# 2026-07-25-picoemp-rev2026-design.md, section 6.1) plus the custom
# footprints Task 6 drew into lib/picoemp.pretty/. Keyed by each symbol's
# CURRENT reference designator, not the upstream one.
#
# D1/D3/D4/D5 use picoemp:D_SOD-123FL rather than the spec's stock
# Diode_SMD:D_SOD-123F: Task 6 found the stock land is 2.80mm pad-centre
# span while the correct SOD-123FL land is 3.10mm (confirmed against both
# Central Semiconductor's drawing and the as-fabricated original board).
#
# Three spec-table entries are intentionally absent from this dict:
#   - The spec's "J1" (SMA) is today's J6 -- already correct below, just
#     not yet renamed. The spec's "J4" (SMA, DNP optional trigger input)
#     doesn't exist as a symbol yet. Both resolve when Task 8 renames J6 to
#     J1 and Task 9 creates the new J4.
#   - C6 and U2 are new trigger-front-end parts Task 9 adds; they don't
#     exist as symbols yet.
# None of this is a test gap: a symbol that does not exist cannot carry a
# wrong footprint, and test_every_symbol_has_a_footprint only inspects
# symbols that exist. Tasks 8/9 add their own footprint coverage for the
# parts they create/rename.
FOOTPRINTS = {
    'C1': 'Capacitor_SMD:C_0805_2012Metric',
    'C2': 'Capacitor_SMD:C_0805_2012Metric',
    'C3': 'Capacitor_SMD:C_2220_5750Metric',
    'C5': 'Capacitor_SMD:C_0603_1608Metric',
    'D1': 'picoemp:D_SOD-123FL',
    'D2': 'Diode_SMD:D_SMA',
    'D3': 'picoemp:D_SOD-123FL',
    'D4': 'picoemp:D_SOD-123FL',
    'D5': 'picoemp:D_SOD-123FL',
    'D7': 'Diode_SMD:D_SOD-323F',
    'Q1': 'picoemp:SOP-6_LDA111',
    'Q2': 'Package_TO_SOT_SMD:TO-252-3_TabPin2',
    'Q3': 'Package_TO_SOT_SMD:SOT-23',
    'Q4': 'Package_TO_SOT_SMD:SOT-23',
    'T1': 'picoemp:ATB322524',
    'T2': 'picoemp:ATB322524',
    'U1': 'Module:RaspberryPi_Pico_SMD',
    'J2': 'Connector_JST:JST_XH_S2B-XH-A_1x02_P2.50mm_Horizontal',
    'J6': 'Connector_Coaxial:SMA_Amphenol_132289_EdgeMount',  # -> J1 in Task 8
}


def test_every_symbol_has_a_footprint(syms):
    missing = [s.ref for s in syms if not s.footprint]
    assert not missing, f'symbols with no footprint: {sorted(missing, key=kp.ref_key)}'


def test_every_footprint_has_a_library_prefix(syms):
    """Format check on whatever footprint IS assigned.

    Deliberately skips symbols with no footprint at all (SW1-3, J3 at this
    stage) -- that gap is test_every_symbol_has_a_footprint's job, and
    those refs sit out of Task 7's scope (Tasks 8/11 own them).
    """
    bad = [(s.ref, s.footprint) for s in syms if s.footprint and ':' not in s.footprint]
    assert not bad, f'footprints with no library prefix: {bad}'


def test_no_absolute_path_footprints(syms):
    bad = [(s.ref, s.footprint) for s in syms
           if 'Users' in s.footprint or 'Documents' in s.footprint]
    assert not bad, f'absolute-path footprints: {bad}'


def test_expected_footprint_assignments(syms):
    by_ref = {s.ref: s.footprint for s in syms}
    wrong = {r: (by_ref.get(r), want) for r, want in FOOTPRINTS.items()
             if by_ref.get(r) != want}
    assert not wrong, f'footprint mismatches (got, want): {wrong}'
