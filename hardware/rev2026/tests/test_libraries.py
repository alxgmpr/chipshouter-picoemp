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
