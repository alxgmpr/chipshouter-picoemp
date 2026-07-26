import re

import kicad_parse as kp


def test_sym_lib_table_exists_and_registers_picoemp(root):
    path = root / 'sym-lib-table'
    assert path.exists(), 'project-local sym-lib-table missing'
    text = path.read_text()
    assert 'picoemp' in text
    assert '${KIPRJMOD}/lib/picoemp.kicad_sym' in text


def test_fp_lib_table_exists_and_registers_picoemp(root):
    path = root / 'fp-lib-table'
    assert path.exists(), 'project-local fp-lib-table missing'
    text = path.read_text()
    assert 'picoemp' in text
    assert '${KIPRJMOD}/lib/picoemp.pretty' in text


def _lib_symbol_names(root):
    text = (root / 'lib' / 'picoemp.kicad_sym').read_text()
    return set(re.findall(r'\n\t\(symbol "([^"]+)"', text))


def test_custom_symbols_exist(root):
    names = _lib_symbol_names(root)
    assert 'IGBT_NCH_Diode' in names, 'IGBT symbol with antiparallel diode missing'
    assert 'LDA111' in names, 'LDA111 Darlington opto symbol missing'


def test_igbt_pin_names(root):
    """DPAK IGBT: pin 1 Gate, pin 2 Collector, pin 3 Emitter.

    Parses each (name, number) pair from within the same pin block, rather
    than checking name/number substrings independently, so the test fails
    if a name and number are ever mismatched (e.g. pin 1 named "C").
    """
    text = (root / 'lib' / 'picoemp.kicad_sym').read_text()
    body = text.split('(symbol "IGBT_NCH_Diode"')[1].split('\n\t(symbol "')[0]
    pairs = re.findall(
        r'\(pin \w+ line\s*\(at[^)]*\)\s*\(length[^)]*\)\s*'
        r'\(name "([^"]+)".*?\(number "(\d+)"',
        body,
        re.DOTALL,
    )
    mapping = {number: name for name, number in pairs}
    assert len(pairs) == 3, f'expected exactly 3 pins, found {len(pairs)}: {pairs}'
    assert mapping == {'1': 'G', '2': 'C', '3': 'E'}, f'unexpected IGBT pin mapping: {mapping}'


def test_lda111_pin_numbers(root):
    """6-pin opto, pin 3 is absent (NC)."""
    text = (root / 'lib' / 'picoemp.kicad_sym').read_text()
    body = text.split('(symbol "LDA111"')[1].split('\n\t(symbol "')[0]
    nums = set(re.findall(r'\(number "(\d)"', body))
    assert nums == {'1', '2', '4', '5', '6'}, f'unexpected LDA111 pins: {sorted(nums)}'


def _fp(root, name):
    return kp.footprints(kp.parse_file(root / 'lib' / 'picoemp.pretty' / f'{name}.kicad_mod'))[0]


def test_atb322524_footprint_geometry(root):
    """TDK ATB3225: 3.2 x 2.5 mm body, 4 pads, two per side."""
    fp = _fp(root, 'ATB322524')
    assert len(fp.pads) == 4, f'expected 4 pads, got {len(fp.pads)}'
    xs = sorted({round(x, 2) for _, x, _ in fp.pads})
    assert len(xs) == 2, f'pads should form two columns, got x positions {xs}'
    assert 2.0 <= (xs[1] - xs[0]) <= 3.2, f'pad column spacing {xs[1]-xs[0]} mm out of range'


def test_lda111_footprint_has_all_six_pads(root):
    """Pin 3 is electrically NC but the lead physically exists, so it needs a
    pad. Verified against the original SamacSys footprint in
    hardware/altium_src/kc/ChipShouter-Pico.kicad_pcb, which has 6 pads with
    pad 3 at (-4.425, 2.54). Omitting it would leave a lead unsoldered."""
    fp = _fp(root, 'SOP-6_LDA111')
    nums = {n for n, _, _ in fp.pads}
    assert nums == {'1', '2', '3', '4', '5', '6'}, f'unexpected pads: {sorted(nums)}'


def test_lda111_footprint_geometry(root):
    """SOP254P952X470-6N: 2.54 mm pitch, pad centres at x = +/-4.425
    (8.85 mm span). The 9.52 mm in the package name is lead-tip to lead-tip,
    not pad centre to pad centre."""
    fp = _fp(root, 'SOP-6_LDA111')
    ys = sorted({round(y, 2) for _, _, y in fp.pads})
    pitches = {round(b - a, 2) for a, b in zip(ys, ys[1:])}
    assert pitches == {2.54}, f'expected uniform 2.54 mm pitch, got y positions {ys}'
    xs = sorted({round(x, 2) for _, x, _ in fp.pads})
    assert len(xs) == 2, f'pads should form two rows, got x positions {xs}'
    span = xs[1] - xs[0]
    assert 8.6 <= span <= 9.1, f'pad-centre span {span} mm, expected ~8.85'
