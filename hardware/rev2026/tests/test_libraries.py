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
