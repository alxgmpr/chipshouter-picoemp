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
    """6-pin opto; the package has 6 leads, pin 3 is electrically NC."""
    text = (root / 'lib' / 'picoemp.kicad_sym').read_text()
    body = text.split('(symbol "LDA111"')[1].split('\n\t(symbol "')[0]
    nums = set(re.findall(r'\(number "(\d)"', body))
    assert nums == {'1', '2', '3', '4', '5', '6'}, f'unexpected LDA111 pins: {sorted(nums)}'


def test_lda111_pin3_is_no_connect(root):
    """Pin 3's lead physically exists on the SOP-6 package (the footprint has
    six pads) even though it is electrically NC, so the symbol must expose it
    as an explicit no_connect pin rather than omitting it."""
    text = (root / 'lib' / 'picoemp.kicad_sym').read_text()
    body = text.split('(symbol "LDA111"')[1].split('\n\t(symbol "')[0]
    # Matching a generic \d+ (rather than a literal "3") keeps each match
    # anchored to its own pin block: non-greedy .*? stops at the nearest
    # (number ...), which is always that same pin's own number, not some
    # later pin's. Searching for a literal "3" instead let the match start
    # at an earlier, unrelated pin and skip forward across pin boundaries
    # to reach pin 3's number, misreporting that pin's own type/name.
    triples = re.findall(
        r'\(pin (\w+) line\s*\(at[^)]*\)\s*\(length[^)]*\)\s*'
        r'\(name "([^"]+)".*?\(number "(\d+)"',
        body,
        re.DOTALL,
    )
    by_number = {number: (pin_type, name) for pin_type, name, number in triples}
    assert '3' in by_number, f'pin 3 not found in LDA111 symbol pins: {sorted(by_number)}'
    pin_type, pin_name = by_number['3']
    assert pin_type == 'no_connect', f'expected pin 3 electrical type no_connect, got {pin_type}'
    assert pin_name == 'NC', f'expected pin 3 named NC, got {pin_name}'


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


# --- Pad-size / containment coverage -----------------------------------
#
# kicad_parse.footprints() only exposes pad (number, x, y): enough for the
# position/pitch tests above, but not enough to catch a pad *size* bug --
# which is exactly where two real defects were found in review: (1) the
# LDA111's pads were sized so adjacent same-column pads touched with zero
# gap (a dead short), and (2) an earlier D_SOD-123FL draft had pads sized
# and centred so they never reached the body/leads at all. Both would have
# sailed through the position-only tests above unchanged. _pads_with_size
# and _fab_body_half_extents below reuse kicad_parse's own primitives
# (parse_file, _walk, sval) to pull the extra fields, without changing
# kicad_parse.py's public Footprint/pads shape that other tasks rely on.

def _pads_with_size(root, name):
    """(number, x, y, size_x, size_y) for every pad in a .kicad_mod file.

    size_x/size_y are the EFFECTIVE footprint-local-frame extents, i.e.
    with the pad's own rotation (the 3rd `at` value) already applied --
    swapped when rotation is an odd multiple of 90 degrees. Reading the
    raw `(size ...)` tuple without this would silently ignore exactly the
    bug found in review (a 90-degree pad rotation that swapped which axis
    the 2.54mm dimension fell on), since the raw tuple is identical
    regardless of rotation.
    """
    tree = kp.parse_file(root / 'lib' / 'picoemp.pretty' / f'{name}.kicad_mod')
    out = []
    for pad in kp._walk(tree, 'pad'):
        num = kp.sval(pad[1]) or ''
        at = next(c for c in pad if isinstance(c, list) and c and c[0] == 'at')
        size = next(c for c in pad if isinstance(c, list) and c and c[0] == 'size')
        x, y = float(at[1]), float(at[2])
        angle = float(at[3]) if len(at) > 3 else 0.0
        sx, sy = float(size[1]), float(size[2])
        if round(angle) % 180 == 90:
            sx, sy = sy, sx
        out.append((num, x, y, sx, sy))
    return out


def _fab_body_half_extents(root, name):
    """(half_x, half_y) of the F.Fab fp_rect body outline in a .kicad_mod."""
    tree = kp.parse_file(root / 'lib' / 'picoemp.pretty' / f'{name}.kicad_mod')
    for rect in kp._walk(tree, 'fp_rect'):
        layer = next(
            (kp.sval(c[1]) for c in rect if isinstance(c, list) and c and c[0] == 'layer'),
            None,
        )
        if layer == 'F.Fab':
            start = next(c for c in rect if isinstance(c, list) and c and c[0] == 'start')
            end = next(c for c in rect if isinstance(c, list) and c and c[0] == 'end')
            xs = sorted([float(start[1]), float(end[1])])
            ys = sorted([float(start[2]), float(end[2])])
            return xs[1], ys[1]
    raise AssertionError(f'no F.Fab fp_rect body outline found in {name}.kicad_mod')


def test_atb322524_pad_size(root):
    """Pads must be a plausible physical size (matching the as-fabricated
    reference's 0.55 x 1.0mm pads) and must not be wide enough to touch
    across the 3.0mm column pitch."""
    pads = _pads_with_size(root, 'ATB322524')
    for num, _, _, sx, sy in pads:
        assert 0.3 <= sx <= 1.0, f'pad {num} width {sx}mm implausible for a 3.2x2.5mm part'
        assert 0.6 <= sy <= 1.6, f'pad {num} height {sy}mm implausible for a 3.2x2.5mm part'
    xs = sorted({round(x, 2) for _, x, _, _, _ in pads})
    pitch = xs[1] - xs[0]
    assert max(sx for _, _, _, sx, _ in pads) < pitch, (
        'pad width reaches across the column pitch -- pads would touch/overlap'
    )


def test_lda111_pad_size_and_gap(root):
    """Regression test for the fused-pad defect found in review: the pads
    were `(size 2.54 1.27)` rotated 90 degrees, which puts the 2.54mm
    dimension along Y -- the 2.54mm pitch axis -- so adjacent same-column
    pads touched with zero gap (pins 1-2-3 and 4-5-6 shorted together on
    the optocoupler). The fix removes the rotation so 2.54mm runs along X
    (toe-to-heel, away from the body) and 1.27mm along Y, leaving a real
    gap. This test pins both the individual pad size and a strictly
    positive inter-pad gap within each column, so a reintroduced rotation
    (or any other zero/negative-gap regression) fails here instead of only
    being visible in a rendered SVG."""
    pads = _pads_with_size(root, 'SOP-6_LDA111')
    for num, _, _, sx, sy in pads:
        assert 2.3 <= sx <= 2.8, f'pad {num} width (toe-to-heel, X) {sx}mm, expected ~2.54mm'
        assert 1.0 <= sy <= 1.5, f'pad {num} height (pitch axis, Y) {sy}mm, expected ~1.27mm'
        assert sx > sy, (
            f'pad {num} size {sx}x{sy}mm: X (toe-to-heel) must exceed Y (pitch axis), '
            'or adjacent pads in the same column will touch'
        )
    by_column = {}
    for num, x, y, sx, sy in pads:
        by_column.setdefault(round(x, 2), []).append((y, sy))
    for col_x, entries in by_column.items():
        entries.sort()
        for (y1, sy1), (y2, sy2) in zip(entries, entries[1:]):
            gap = (y2 - sy2 / 2) - (y1 + sy1 / 2)
            assert gap > 0, (
                f'pads at x={col_x} touch or overlap (y={y1} and y={y2}, gap={gap}mm) -- '
                'this shorts adjacent pins together'
            )


def test_d_sod_123fl_footprint_geometry(root):
    """SOD-123FL land for SM4005PL-TP (D1/D3/D4/D5), per Central
    Semiconductor's mounting-pad drawing (4.1mm overall pad-to-pad envelope
    minus a 0.95mm pad width = 3.15mm centre span) and the as-fabricated
    main:DSS13UTR footprint on the original board (+/-1.55mm centres,
    3.10mm span, 1.15x1.30mm pads). An earlier draft misread MCC's
    suggested-pad-layout figure: its "2.36mm" turned out to be the
    inner-edge gap between pads, not the centre-to-centre span, so the
    pads landed entirely inside the body outline, nowhere near the leads.
    This test pins the corrected span, sane pad sizes, and -- the check
    that would have caught the original mistake -- that each pad's outer
    edge actually reaches past the body outline."""
    pads = _pads_with_size(root, 'D_SOD-123FL')
    assert len(pads) == 2, f'expected 2 pads, got {len(pads)}'
    xs = sorted(x for _, x, _, _, _ in pads)
    span = xs[1] - xs[0]
    assert 3.0 <= span <= 3.3, f'pad-centre span {span}mm, expected ~3.10-3.15mm'
    for num, _, _, sx, sy in pads:
        assert 0.8 <= sx <= 1.5, f'pad {num} width {sx}mm implausible'
        assert 1.0 <= sy <= 1.6, f'pad {num} height {sy}mm implausible'
    half_x, _ = _fab_body_half_extents(root, 'D_SOD-123FL')
    for num, x, _, sx, _ in pads:
        outer_edge = abs(x) + sx / 2
        assert outer_edge > half_x, (
            f'pad {num} outer edge at {outer_edge}mm does not reach the body half-length '
            f'{half_x}mm -- the land does not reach the leads'
        )
