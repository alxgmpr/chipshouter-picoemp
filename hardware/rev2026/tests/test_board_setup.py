"""Board-setup invariants for the high-voltage section.

This board relies on an isolation barrier between the HV side (C3, D2, T1/T2
secondaries, Q2, J3, R1, R2) and the logic side. The as-received port shipped
with ``min_clearance = 0.0`` — DRC enforcing nothing at all — and no HV class.

Voltages, from primary sources rather than component ratings:

- HV capacitor charges to **~250 V** (firmware/micropython/cspico_simple.py:
  "This results in around 250V on the HV capacitor")
- Upstream designs the barrier for **400 V minimum**
- Isolation is hi-pot tested at 1 kV, "well beyond the voltages the device can
  generate" (hardware/design_notes/README.md)

C3's 630 V and Q2's 650 V ratings are headroom, not operating points.

The 1.0 mm figure is **upstream's own stated design rule**, annotated directly
on SCH-PICOEMP-REV04.PDF:

    ISOLATION BARRIER, 400V MIN.  >1MM CLEARANCE PER 61010-1.

It is corroborated by measurement: pad geometry on the hi-pot-validated
original board (``hardware/altium_src/kc/ChipShouter-Pico.kicad_pcb``) gives
~1.002 mm across the barrier in routed copper.

Known exception — T1 and T2's own primary-to-secondary pad spacing is 0.770 mm
and 1.220 mm respectively. T1 is below this rule and will flag once the board
carries footprints. That is a property of the ATB3225 package, not a routing
choice, and upstream accepted it. Handle it with a targeted DRC exclusion on
those pad pairs; do not loosen the class to hide it.

Note the original board's *net labels* are unreliable — a track labelled
NetQ1_1 terminates on a pad labelled NetJ3_2, and R1's pad-to-net assignment is
reversed between its legacy and new footprints. The measurement above therefore
used pad geometry classified by component, never by net name, and excluded Q1
whose imported footprint has fused pads.
"""
import json

import conftest

HV_CLEARANCE_MM = 1.0

# Taken from the rev2026 schematic's own netlist, not the old board's labels.
#
# Every net in the isolated HV domain is named HV_*, so ONE netclass pattern
# covers all of them. That is not cosmetic. The domain is galvanically isolated
# -- T1, T2 and the Q1 optocoupler are the only crossings -- and a net that
# floats with the HV return but is missing from the class silently loses the 1 mm
# barrier. That had already happened once: the opto LED anode (then the
# auto-generated Net-(Q1-A)) sat entirely on the HV side of Q1 and was NOT in the
# class, so DRC would have allowed logic copper 0.2 mm from it.
HV_NETS = {
    'HV_RECT',        # T1 secondary -> D2 anode
    'HV_RAIL',        # HV rail: C3, D2 cathode, J1 shell, R2
    'HV_RTN',         # HV return: C3, Q2 emitter, T1/T2, R1, R9, SW3, D7
    'HV_GATE',        # Q2 gate, clamped by D7
    'HV_OUT',         # Q2 collector -> SMA centre (the pulse)
    'HV_SENSE',       # HV calibration tap, J3 pin 2
    'HV_SENSE_LED',   # R1 -> Q1 opto LED anode
    'HV_GATE_DRV',    # T2 secondary -> gate series resistor
}


def _pro():
    return json.loads(conftest.PRO.read_text())


def test_min_clearance_is_enforced():
    """The port shipped with min_clearance = 0.0, i.e. DRC checking nothing."""
    rules = _pro()['board']['design_settings']['rules']
    assert rules['min_clearance'] > 0, 'min_clearance is 0 - DRC is not enforcing'


def test_hv_netclass_exists():
    classes = {c['name'] for c in _pro()['net_settings']['classes']}
    assert 'HV' in classes, f'no HV netclass defined; found {sorted(classes)}'


def test_barrier_rule_file_exists():
    """The 1 mm barrier lives in a custom rule, NOT the netclass clearance.

    A netclass clearance applies between any two differing nets touching the
    class — including the two pads of a single resistor. At 1 mm that makes
    0603 (0.70 mm pad gap) and 0805 (0.80 mm) parts illegal on HV nets, which
    is not what upstream's rule means. Their ">1MM PER 61010-1" governs the
    isolation barrier: HV side to logic side.
    """
    dru = conftest.PRO.with_suffix('.kicad_dru')
    assert dru.exists(), 'picoemp-rev2026.kicad_dru missing — barrier unenforced'


def test_barrier_rule_is_one_mm_and_correctly_scoped():
    dru = conftest.PRO.with_suffix('.kicad_dru').read_text()
    assert 'clearance (min 1.0mm)' in dru.replace('  ', ' '), \
        'barrier rule is not 1.0 mm'
    assert "A.hasNetclass('HV')" in dru and "!B.hasNetclass('HV')" in dru, (
        'barrier rule must be conditioned on HV-to-non-HV, or it re-creates '
        'the intra-component false positives it exists to avoid'
    )


def test_dru_uses_no_silently_dead_condition_functions():
    """An unknown function in a DRU condition is not an error -- it never matches.

    KiCad parses the rule, reports nothing, and the constraint silently enforces
    nothing. ``memberOf()`` is the pre-v7 spelling of ``memberOfFootprint()`` and
    is exactly this trap: it looks correct and does nothing. Verified against
    this board -- ``memberOfFootprint('J1')`` fires, ``memberOf('J4')`` does not.
    """
    import re
    dru = conftest.PRO.with_suffix('.kicad_dru').read_text()
    # Comments document the trap by name, so scan rule text only.
    rules = '\n'.join(l for l in dru.splitlines() if not l.lstrip().startswith('#'))
    dead = re.findall(r'\.(memberOf|insideArea)\(', rules)
    assert not dead, (
        f'DRU uses condition function(s) {sorted(set(dead))} which KiCad accepts '
        'and silently never matches. Use memberOfFootprint()/intersectsArea() and '
        'confirm the rule fires before committing it.'
    )


def test_package_exceptions_come_after_the_broad_rules():
    """KiCad applies the LAST matching rule, so exceptions must be at the bottom.

    Verified empirically: the same narrow rule placed before the barrier is
    overridden by it and placed after it wins. Getting this backwards leaves the
    exceptions inert and the false positives standing.
    """
    dru = conftest.PRO.with_suffix('.kicad_dru').read_text()
    barrier = dru.index('"HV isolation barrier"')
    for exc in ('"Edge-mount SMA pads may reach the board edge"',
                '"ATB3225 intra-package pad spacing - T1"',
                '"ATB3225 intra-package pad spacing - T2"'):
        assert exc in dru, f'missing documented exception {exc}'
        assert dru.index(exc) > barrier, (
            f'{exc} is defined before the broad barrier rule, so the barrier '
            'overrides it and the exception does nothing'
        )


def test_q2_has_no_unverified_clearance_exception():
    """Q2 pads 2 and 3 are the IGBT collector and emitter, ~250 V apart.

    DRC reports 0.080 mm between them; the footprint geometry reads as 1.08 mm
    and the two could not be reconciled. An exception was briefly added on the
    assumption that 0.080 mm was real package geometry, then removed: relaxing
    clearance on a 250 V node to a number nobody has confirmed is the worst
    available outcome. Measure the footprint before any exception goes back in.
    """
    dru = conftest.PRO.with_suffix('.kicad_dru').read_text()
    rules = '\n'.join(l for l in dru.splitlines() if not l.lstrip().startswith('#'))
    assert "memberOfFootprint('Q2')" not in rules, (
        'a clearance exception for Q2 is back in the rules file. Q2 switches '
        '~250 V between pads 2 and 3 - do not suppress that violation until the '
        'lead-pad spacing has actually been measured in the footprint editor.'
    )


def test_edge_mount_sma_exception_covers_both_connectors():
    """J1 and J4 are both edge-launch SMAs whose pads must reach the board edge."""
    dru = conftest.PRO.with_suffix('.kicad_dru').read_text()
    for ref in ('J1', 'J4'):
        assert f"memberOfFootprint('{ref}')" in dru, (
            f'{ref} is an edge-mount SMA but has no copper-to-edge exception; '
            'its pads will flag against the 0.5 mm board constraint'
        )


def test_hv_netclass_carries_wider_default_copper():
    """HV runs a 250 V rail and the discharge loop; 0.2 mm signal track is thin."""
    classes = {c['name']: c for c in _pro()['net_settings']['classes']}
    hv = classes['HV']
    assert hv['track_width'] >= 0.4, \
        f"HV default track width is {hv['track_width']} mm"
    assert hv['via_drill'] >= 0.4, \
        f"HV default via drill is {hv['via_drill']} mm"


def test_hv_netclass_does_not_over_constrain_intra_hv_spacing():
    """HV-to-HV spacing is bounded by component packages, not by the barrier."""
    classes = {c['name']: c for c in _pro()['net_settings']['classes']}
    hv = classes['HV']['clearance']
    assert hv < 0.70, (
        f'HV netclass clearance is {hv} mm; anything >= 0.70 mm makes an 0603 '
        "resistor's own two pads a violation"
    )


def test_every_hv_net_is_assigned_to_the_hv_class():
    """A missing pattern silently leaves an HV net on the 0.2 mm default."""
    import fnmatch
    pats = [p['pattern'] for p in _pro()['net_settings'].get('netclass_patterns', [])
            if p.get('netclass') == 'HV']
    # HV_NETS holds bare names; KiCad's canonical form for a root-sheet local
    # label carries a leading '/'. Accept either so this test is about coverage,
    # not about which spelling happens to be in use -- the prefix itself is what
    # test_hv_patterns_match_the_names_actually_on_the_board pins down.
    missing = {n for n in HV_NETS
               if not any(fnmatch.fnmatch(n, p) or fnmatch.fnmatch('/' + n, p)
                          for p in pats)}
    assert not missing, (
        f'HV nets not covered by any HV pattern {pats}: {sorted(missing)}'
    )


def test_hv_patterns_match_the_names_actually_on_the_board():
    """The patterns must match the BOARD's net names, not an idea of them.

    This failed silently once. The nets were renamed in the .kicad_pcb directly,
    as bare 'HV_RAIL', and a wildcard 'HV_*' pattern was written to match. Then
    'Update PCB from Schematic' rewrote them to KiCad's canonical root-sheet form
    '/HV_RAIL' -- and the pattern stopped matching anything at all. The HV class
    covered zero nets, the 1 mm isolation barrier enforced nothing, and no error
    appeared anywhere: DRC simply reported the offending pads as netclass
    'Default'. Checking patterns against a hardcoded list cannot catch that,
    because the hardcoded list drifts with the pattern.
    """
    import fnmatch
    import re
    pcb = conftest.PRO.with_suffix('.kicad_pcb').read_text()
    on_board = set(re.findall(r'\(net "([^"]+)"\)', pcb))
    pats = [p['pattern'] for p in _pro()['net_settings'].get('netclass_patterns', [])
            if p.get('netclass') == 'HV']

    # Every HV-domain net present on the board must resolve into the class.
    hv_on_board = {n for n in on_board if n.lstrip('/') in HV_NETS}
    assert hv_on_board, (
        f'no HV-domain net found on the board at all; names present: '
        f'{sorted(n for n in on_board if "HV" in n)}'
    )
    missed = {n for n in hv_on_board
              if not any(fnmatch.fnmatch(n, p) for p in pats)}
    assert not missed, (
        f'HV nets on the board that NO pattern in {pats} matches: {sorted(missed)}. '
        'The HV netclass is not being applied to them and the isolation barrier '
        'is inert for that copper.'
    )

    # ...and nothing else may be dragged in. '/HV_DET_LED' is a logic GPIO net
    # driving the indicator LED; a '/HV_*' wildcard would capture it.
    extra = {n for n in on_board
             if any(fnmatch.fnmatch(n, p) for p in pats) and n.lstrip('/') not in HV_NETS}
    assert not extra, (
        f'non-HV nets captured by the HV patterns {pats}: {sorted(extra)}. These '
        'would wrongly demand 1 mm from all surrounding logic copper.'
    )


def test_hv_domain_nets_all_share_the_hv_prefix():
    """The wildcard pattern is only safe while this holds.

    'HV_*' covers the class automatically, which is what stops a newly added HV
    net from being forgotten. If someone names one without the prefix, the
    wildcard silently misses it and the isolation barrier develops a hole with
    no error anywhere.
    """
    off = {n for n in HV_NETS if not n.startswith('HV_')}
    assert not off, (
        f'HV-domain nets without the HV_ prefix: {sorted(off)}. Either rename '
        'them or stop relying on the HV_* wildcard pattern.'
    )


def test_board_carries_no_autogenerated_net_names():
    """Auto names like Net-(D7-A) say nothing about what a net is.

    On a board with an isolated 250 V domain the name is the main cue for
    whether a given piece of copper is dangerous, so every net is labelled.
    """
    import re
    pcb = conftest.PRO.with_suffix('.kicad_pcb').read_text()
    auto = sorted(set(re.findall(r'\(net "(Net-\([^"]+\))"\)', pcb)))
    assert not auto, f'unnamed nets still on the board: {auto}'


def _edge_arcs():
    """Every Edge.Cuts arc as (centre, radius), derived from its 3 points."""
    import math
    import kicad_parse as kp
    d = kp.parse_file(str(conftest.PRO.with_suffix('.kicad_pcb')))
    out = []
    for n in kp._walk(d, 'gr_arc'):
        lay = next((c for c in n if isinstance(c, list) and c and c[0] == 'layer'), None)
        if not lay or kp.sval(lay[1]) != 'Edge.Cuts':
            continue
        p = {}
        for tag in ('start', 'mid', 'end'):
            c = next((x for x in n if isinstance(x, list) and x and x[0] == tag), None)
            p[tag] = (float(c[1]), float(c[2]))
        (ax, ay), (bx, by), (cx, cy) = p['start'], p['mid'], p['end']
        dd = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        ux = ((ax**2 + ay**2) * (by - cy) + (bx**2 + by**2) * (cy - ay)
              + (cx**2 + cy**2) * (ay - by)) / dd
        uy = ((ax**2 + ay**2) * (cx - bx) + (bx**2 + by**2) * (ax - cx)
              + (cx**2 + cy**2) * (bx - ax)) / dd
        out.append(((ux, uy), math.hypot(ax - ux, ay - uy)))
    return out


def test_corner_radii_match_at_every_corner_that_has_a_mounting_hole():
    """Three corners at R=4.000; the north-east one is deliberately smaller.

    R=4.000 is not a style choice -- it equals the mounting-hole inset, which is
    what makes each arc concentric with its hole. The north-east corner has no
    hole, so its radius buys nothing there, and it was the one thing cheap enough
    to give up when the north edge ran out of room: the USB notch plus J4 need
    more than the 32 mm that two R=4 corners leave. Dropping NE to 1.270 freed
    2.73 mm and let J4 sit in the east strip with 1.36 mm to spare.
    """
    import math
    arcs = _edge_arcs()
    assert len(arcs) == 4, f'expected 4 corner arcs, found {len(arcs)}'
    big = sorted(r for _, r in arcs if r > 2.0)
    small = sorted(r for _, r in arcs if r <= 2.0)
    assert len(big) == 3, f'expected 3 large corner radii, found {[round(r,3) for r in big]}'
    assert big[-1] - big[0] < 0.005, \
        f'the three hole corners do not share a radius: {[round(r, 4) for r in big]}'
    assert len(small) == 1 and abs(small[0] - 1.27) < 0.005, \
        f'expected exactly one 1.270 mm corner (north-east), found {[round(r,4) for r in small]}'


def test_every_mounting_hole_is_concentric_with_its_corner_arc():
    """Each hole must share a centre with the corner arc that curves around it.

    Only a shared centre gives a constant FR4 web. With the original 1.27 mm
    corners the straight edges sat 4.000 mm from MH3's centre while the arc cut
    in to 2.591 mm, so the web visibly pinched at the diagonal.

    This holds for all three holes because each sits at an equal 4.000 mm inset
    from both of its nearest edges, which is also the corner radius -- so the arc
    centred on the hole is automatically tangent to both straight edges.

    MH1/MH2 were originally 5.855 mm from the south edge, inherited from
    upstream. Moving them to 4.000 mm changed only their Y; their 32.000 mm X
    spacing, which is what any shield or bracket actually keys off, is untouched.
    """
    import math
    import kicad_parse as kp
    d = kp.parse_file(str(conftest.PRO.with_suffix('.kicad_pcb')))
    holes = {}
    for fp in kp._walk(d, 'footprint'):
        ref = next((kp.sval(p[2]) for p in fp if isinstance(p, list) and p
                    and p[0] == 'property' and kp.sval(p[1]) == 'Reference'), None)
        if ref and ref.startswith('MH'):
            at = next(c for c in fp if isinstance(c, list) and c and c[0] == 'at')
            holes[ref] = (float(at[1]), float(at[2]))
    assert len(holes) == 3, f'expected MH1-3, found {sorted(holes)}'

    arcs = _edge_arcs()
    for ref, pos in sorted(holes.items()):
        centre, _ = min(arcs, key=lambda a: math.dist(a[0], pos))
        off = math.dist(centre, pos)
        assert off < 0.005, (
            f'{ref} at {pos} is {off:.4f} mm from the nearest corner-arc centre '
            f'{tuple(round(v, 4) for v in centre)}; the web around it is not constant'
        )


def test_mounting_hole_x_spacing_is_preserved():
    """32.000 mm between MH1 and MH2 -- inherited from upstream's layout and the
    dimension a shield or bracket keys off. Y may be tuned for the corners; this
    must not move with it."""
    import kicad_parse as kp
    d = kp.parse_file(str(conftest.PRO.with_suffix('.kicad_pcb')))
    xs = {}
    for fp in kp._walk(d, 'footprint'):
        ref = next((kp.sval(p[2]) for p in fp if isinstance(p, list) and p
                    and p[0] == 'property' and kp.sval(p[1]) == 'Reference'), None)
        if ref in ('MH1', 'MH2'):
            at = next(c for c in fp if isinstance(c, list) and c and c[0] == 'at')
            xs[ref] = float(at[1])
    assert abs(abs(xs['MH2'] - xs['MH1']) - 32.0) < 0.005, \
        f"MH1/MH2 X spacing is {abs(xs['MH2'] - xs['MH1']):.4f} mm, must stay 32.000"


def test_sma_tab_is_centred_on_the_board_axis():
    """The HV SMA outcropping must sit on the board's centreline.

    It was drawn 0.500 mm east of it -- tab centred on x=124.890 against a board
    centre of x=124.390 -- while J1 itself sat at x=124.390. So the connector was
    centred on the board but off-centre in its own tab, and the whole outline was
    visibly asymmetric.
    """
    import kicad_parse as kp
    d = kp.parse_file(str(conftest.PRO.with_suffix('.kicad_pcb')))
    xs = []
    for n in kp._walk(d, 'gr_line'):
        lay = next((c for c in n if isinstance(c, list) and c and c[0] == 'layer'), None)
        if not lay or kp.sval(lay[1]) != 'Edge.Cuts':
            continue
        pts = [next(c for c in n if isinstance(c, list) and c and c[0] == t)
               for t in ('start', 'end')]
        for c in pts:
            if abs(float(c[2]) - 149.872) < 0.001:      # the tab's south edge
                xs.append(float(c[1]))
    assert len(xs) >= 2, 'tab south edge not found on Edge.Cuts'
    board_centre = (104.39 + 144.39) / 2
    tab_centre = (min(xs) + max(xs)) / 2
    assert abs(tab_centre - board_centre) < 0.005, (
        f'SMA tab is centred on x={tab_centre:.3f} but the board centre is '
        f'x={board_centre:.3f}; the outline is asymmetric by '
        f'{tab_centre - board_centre:+.3f} mm'
    )
