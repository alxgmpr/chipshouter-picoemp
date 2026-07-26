import kicad_parse as kp

# Every non-power reference expected in the design, post-Task-8.
#
# This set originally also carried C6, J4 (the new trigger-input SMA), R14,
# R15, R16, and U2 -- all Task 9 additions to the trigger front end that
# don't exist as symbols yet. Task 8 only renames/re-footprints existing
# symbols, so those six refs are removed here; Task 9 should add them back
# (and its own test coverage) once it creates the corresponding parts.
EXPECTED_REFS = {
    'C1', 'C2', 'C3', 'C5',
    'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9',
    'FID1', 'FID2', 'FID3',
    'J1', 'J2', 'J3',
    'MH1', 'MH2', 'MH3',
    'P1', 'P2', 'P3',
    'Q1', 'Q2', 'Q3', 'Q4',
    'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R9',
    'R10', 'R11', 'R12', 'R13',
    'SW1', 'SW2', 'SW3',
    'T1', 'T2',
    'U1',
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
# FINAL (post-Task-8) reference designator -- Task 7's version of this dict
# was keyed by the pre-rename designators (J6 for the SMA, etc.) because the
# final names didn't exist as symbols yet at that point; Task 8 renamed the
# schematic, so this dict is re-keyed to match.
#
# D1/D3/D4/D5 use picoemp:D_SOD-123FL rather than the spec's stock
# Diode_SMD:D_SOD-123F: Task 6 found the stock land is 2.80mm pad-centre
# span while the correct SOD-123FL land is 3.10mm (confirmed against both
# Central Semiconductor's drawing and the as-fabricated original board).
#
# SW3 uses a project-local footprint rather than the shared stock
# Button_Switch_SMD:SW_Push_1P1T_NO_CK_KSC7xxJ used for SW1/SW2: upstream
# says the TL3301A "shares" the KSC741J footprint, but the two datasheets
# disagree materially (6.0x6.0mm body vs 6.2x6.2mm, and a 4.50mm pin row
# pitch vs the KSC7xxJ land's 4.00mm -- a 12.5% mismatch). See the Task 8
# report for the full comparison.
#
# Two spec-table entries are intentionally still absent from this dict:
# C6 and U2 are new trigger-front-end parts Task 9 adds; they don't exist
# as symbols yet. The spec's second "J4" (SMA, DNP optional trigger input)
# likewise doesn't exist yet -- Task 9 creates it. None of this is a test
# gap: a symbol that does not exist cannot carry a wrong footprint, and
# test_every_symbol_has_a_footprint only inspects symbols that exist.
# Task 9 adds its own footprint coverage for the parts it creates.
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
    'J1': 'Connector_Coaxial:SMA_Amphenol_132289_EdgeMount',
    'J2': 'Connector_JST:JST_XH_S2B-XH-A_1x02_P2.50mm_Horizontal',
    'P1': 'Connector_PinHeader_2.54mm:PinHeader_1x07_P2.54mm_Vertical',
    'P2': 'Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical',
    'P3': 'Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical',
    'SW1': 'Button_Switch_SMD:SW_Push_1P1T_NO_CK_KSC7xxJ',
    'SW2': 'Button_Switch_SMD:SW_Push_1P1T_NO_CK_KSC7xxJ',
    'SW3': 'picoemp:SW_Push_ESwitch_TL3301AJ',
}


def test_every_symbol_has_a_footprint(syms):
    missing = [s.ref for s in syms if not s.footprint]
    assert not missing, f'symbols with no footprint: {sorted(missing, key=kp.ref_key)}'


def test_every_footprint_has_a_library_prefix(syms):
    """Format check on whatever footprint IS assigned.

    Deliberately skips symbols with no footprint at all (just J3 as of
    Task 8) -- that gap is test_every_symbol_has_a_footprint's job, and J3
    sits out of scope here (Task 9 owns it).
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


def test_upstream_designators_restored(syms):
    """NOTE: the design spec's second SMA (also called "J4", the DNP
    optional trigger input) is a Task 9 addition and deliberately not
    asserted here -- it doesn't exist as a symbol until Task 9 creates it.
    """
    refs = {s.ref for s in syms}
    assert {'D6', 'D8', 'D9'} <= refs, 'LEDs must be D6/D8/D9, not LED1-3'
    assert not (refs & {'LED1', 'LED2', 'LED3'}), 'LED1-3 designators still present'
    assert {'P1', 'P2', 'P3'} <= refs, 'headers must be P1/P2/P3'
    assert {'J1', 'J2', 'J3'} <= refs
    assert 'J5' not in refs and 'J6' not in refs, 'stale J5/J6 designators remain'


def test_sma_is_j1(syms):
    j1 = next(s for s in syms if s.ref == 'J1')
    assert 'SMA' in j1.footprint


def test_headers_are_2540um_pitch(syms):
    """All original headers are 2.54 mm; the port had them at 1.00/1.27 mm."""
    for ref in ('P1', 'P2', 'P3'):
        s = next(x for x in syms if x.ref == ref)
        assert 'P2.54mm' in s.footprint, f'{ref} footprint {s.footprint!r} is not 2.54 mm pitch'


def test_switches_have_footprints(syms):
    for ref in ('SW1', 'SW2', 'SW3'):
        s = next(x for x in syms if x.ref == ref)
        assert s.footprint, f'{ref} has no footprint'


def test_all_expected_refs_present(syms):
    assert {s.ref for s in syms} == EXPECTED_REFS
