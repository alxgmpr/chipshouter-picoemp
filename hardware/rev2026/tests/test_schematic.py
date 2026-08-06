import kicad_parse as kp

# Every non-power reference expected in the design, post-Task-9.
#
# C6, J4 (the new trigger-input SMA), R14, R15, R16, and U2 are Task 9's
# trigger front-end additions (see docs/superpowers/specs/
# 2026-07-25-picoemp-rev2026-design.md section 6.4). J4 and R16 are DNP.
EXPECTED_REFS = {
    'C1', 'C2', 'C3', 'C5', 'C6',
    'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9',
    'FID1', 'FID2', 'FID3',
    'J1', 'J2', 'J3', 'J4',
    'MH1', 'MH2', 'MH3',
    'J5', 'J6',
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
# Task 9 additions: U2 is the 74LVC1G17 Schmitt buffer in SOT-23-5 (verified
# against the Nexperia 74LVC1G17GV,125 datasheet -- NOT the stock symbol's
# TI-only assumption, since SOT-23-5 single-gate logic pinouts are
# vendor-specific). J4 reuses J1's SMA footprint (optional trigger
# input). Both SMAs are the TE/Linx CONSMA020.062-G edge mount -- 500 V RMS,
# which matters because J1 carries HV_OUT/HV_RAIL. It replaced the Amphenol
# 132289, whose land pattern was within 0.01 mm of this one but which carried
# no published voltage rating. R14/R15/R16 are 0603 resistors. J3 is deliberately absent from
# this dict -- test_j3_is_wide_pitch below covers it with a substring check
# instead of an exact-match, since the point of that test is "not 2.54mm /
# is a wide pitch", not one specific part.
FOOTPRINTS = {
    'C1': 'Capacitor_SMD:C_0805_2012Metric',
    'C2': 'Capacitor_SMD:C_0805_2012Metric',
    'C3': 'Capacitor_SMD:C_2220_5750Metric',
    'C5': 'Capacitor_SMD:C_0603_1608Metric',
    'C6': 'Capacitor_SMD:C_0603_1608Metric',
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
    'U2': 'Package_TO_SOT_SMD:SOT-23-5',
    'J1': 'picoemp:SMA_Linx_CONSMA020_062_G_EdgeMount',
    'J2': 'Connector_JST:JST_XH_S2B-XH-A_1x02_P2.50mm_Horizontal',
    # J3 is the trigger SMA and J4 the HV terminal block. These were the
    # other way round until 2026-08-05; the PCB is authoritative and the
    # schematic was re-designated to match it.
    'J3': 'picoemp:SMA_Linx_CONSMA020_062_G_EdgeMount',
    'J4': 'picoemp:TerminalBlock_Phoenix_MKDSN-1,5-2-5.08_1x02_P5.08mm_Horizontal',
    'J5': 'Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical',
    'J6': 'Connector_PinHeader_2.54mm:PinHeader_1x07_P2.54mm_Vertical',
    'R14': 'Resistor_SMD:R_0603_1608Metric',
    'R15': 'Resistor_SMD:R_0603_1608Metric',
    'R16': 'Resistor_SMD:R_0603_1608Metric',
    'SW1': 'Button_Switch_SMD:SW_Push_1P1T_NO_CK_KSC7xxJ',
    'SW2': 'Button_Switch_SMD:SW_Push_1P1T_NO_CK_KSC7xxJ',
    'SW3': 'picoemp:SW_Push_ESwitch_TL3301AJ',
}


def test_every_symbol_has_a_footprint(syms):
    missing = [s.ref for s in syms if not s.footprint]
    assert not missing, f'symbols with no footprint: {sorted(missing, key=kp.ref_key)}'


def test_every_footprint_has_a_library_prefix(syms):
    """Format check on whatever footprint IS assigned.

    Deliberately skips symbols with no footprint at all -- that gap is
    test_every_symbol_has_a_footprint's job. As of Task 9 every symbol has
    a footprint (J3, the last holdout, was assigned its terminal block).
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
    """Upstream REV04's designator scheme, except for the headers.

    The LED and SMA designators still follow upstream so that
    BUILD-DRAWING-REV04.PDF and the README BOM explainer apply.

    The headers no longer do. They were P1/P2/P3 -- a 7-pin, a 2-pin and a
    4-pin -- and were consolidated on 2026-08-05 into J5 (1x05) and J6
    (1x07), carrying the same signals on twelve pins instead of thirteen.
    This test previously asserted J5/J6 were absent, treating them as
    leftovers from the Altium import; that assertion is now wrong and has
    been removed rather than weakened, since there is no version of it that
    is both true and useful.
    """
    refs = {s.ref for s in syms}
    assert {'D6', 'D8', 'D9'} <= refs, 'LEDs must be D6/D8/D9, not LED1-3'
    assert not (refs & {'LED1', 'LED2', 'LED3'}), 'LED1-3 designators still present'
    assert {'J5', 'J6'} <= refs, 'headers must be J5/J6'
    assert not (refs & {'P1', 'P2', 'P3'}), \
        'P1/P2/P3 still present -- the header consolidation is half-applied'
    assert {'J1', 'J2', 'J3', 'J4'} <= refs


def test_sma_is_j1(syms):
    j1 = next(s for s in syms if s.ref == 'J1')
    assert 'SMA' in j1.footprint


def test_headers_are_2540um_pitch(syms):
    """All headers are 2.54 mm; the port had them at 1.00/1.27 mm."""
    for ref in ('J5', 'J6'):
        s = next(x for x in syms if x.ref == ref)
        assert 'P2.54mm' in s.footprint, f'{ref} footprint {s.footprint!r} is not 2.54 mm pitch'


def test_switches_have_footprints(syms):
    for ref in ('SW1', 'SW2', 'SW3'):
        s = next(x for x in syms if x.ref == ref)
        assert s.footprint, f'{ref} has no footprint'


def test_all_expected_refs_present(syms):
    assert {s.ref for s in syms} == EXPECTED_REFS


def test_trigger_front_end_present(syms):
    by_ref = {s.ref: s for s in syms}
    assert by_ref['U2'].value == '74LVC1G17'
    assert by_ref['R14'].value == '100R'
    assert by_ref['R15'].value == '10k'
    assert by_ref['C6'].value == '100n'


def test_bypass_resistor_is_dnp(syms):
    """R16 bypasses the buffer. Never fitted alongside U2."""
    r16 = next(s for s in syms if s.ref == 'R16')
    assert r16.value == '0R'
    assert r16.dnp, 'R16 must be DNP - fitting it with U2 causes output contention'


def test_trigger_sma_is_populated(syms):
    """The trigger SMA is fitted, not DNP.

    This is J3. It was J4 until 2026-08-05, when the schematic was
    re-designated against the PCB and J3/J4 swapped roles.

    It started as an optional footprint. That is why it was given the cramped
    east strip when the USB notch and the trigger SMA competed for the north
    edge -- the always-used part won and the optional one took the
    compromise. Its being populated changes that trade, so if this ever flips
    back to DNP the placement reasoning should be revisited too.
    """
    j3 = next(s for s in syms if s.ref == 'J3')
    assert not j3.dnp, 'J3 is a fitted connector; DNP would contradict the BOM'
    assert j3.in_bom, 'J3 must be in the BOM'


def test_hv_terminal_block_is_wide_pitch(syms):
    """The HV terminal block carries ~500V. 2.54mm fails IEC 60664-1 creepage.

    This is J4. It was J3 until 2026-08-05, when the schematic was
    re-designated against the PCB and J3/J4 swapped roles -- J3 is now the
    trigger SMA. The test follows the connector, not the designator.
    """
    j4 = next(s for s in syms if s.ref == 'J4')
    assert j4.footprint, 'J4 has no footprint'
    assert '2.54mm' not in j4.footprint, 'J4 must not be 2.54mm pitch'
    assert any(p in j4.footprint for p in ('5.08mm', '5.0mm', '3.96mm')), \
        f'J4 footprint {j4.footprint!r} does not look like a wide-pitch connector'
