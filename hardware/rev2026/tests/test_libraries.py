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
    """DPAK IGBT: pin 1 Gate, pin 2 Collector, pin 3 Emitter."""
    text = (root / 'lib' / 'picoemp.kicad_sym').read_text()
    body = text.split('(symbol "IGBT_NCH_Diode"')[1].split('\n\t(symbol "')[0]
    for num, name in (('1', 'G'), ('2', 'C'), ('3', 'E')):
        assert f'(name "{name}"' in body, f'IGBT missing pin name {name}'
        assert f'(number "{num}"' in body, f'IGBT missing pin number {num}'


def test_lda111_pin_numbers(root):
    """6-pin opto, pin 3 is absent (NC)."""
    text = (root / 'lib' / 'picoemp.kicad_sym').read_text()
    body = text.split('(symbol "LDA111"')[1].split('\n\t(symbol "')[0]
    nums = set(re.findall(r'\(number "(\d)"', body))
    assert nums == {'1', '2', '4', '5', '6'}, f'unexpected LDA111 pins: {sorted(nums)}'
