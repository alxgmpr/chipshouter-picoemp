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
HV_NETS = {
    'Net-(D2-A)',      # T1 secondary -> D2 anode
    'Net-(D2-K)',      # HV rail: C3, D2 cathode, J1 centre, R2
    'Net-(D7-A)',      # HV return: C3, Q2 emitter, T1/T2, R1, R9, SW3, D7
    'Net-(D7-K)',      # Q2 gate, clamped by D7
    'Net-(J1-Ext)',    # Q2 collector -> SMA
    'Net-(J3-Pin_2)',  # HV calibration tap
    'Net-(R7-Pad2)',   # T2 secondary -> gate series resistor
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
                '"ATB3225 intra-package pad spacing - T2"',
                '"TO-252 intra-package pad spacing - Q2"'):
        assert exc in dru, f'missing documented exception {exc}'
        assert dru.index(exc) > barrier, (
            f'{exc} is defined before the broad barrier rule, so the barrier '
            'overrides it and the exception does nothing'
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
    pats = _pro()['net_settings'].get('netclass_patterns', [])
    assigned = {p['pattern'] for p in pats if p.get('netclass') == 'HV'}
    missing = HV_NETS - assigned
    assert not missing, f'HV nets not assigned to the HV class: {sorted(missing)}'
