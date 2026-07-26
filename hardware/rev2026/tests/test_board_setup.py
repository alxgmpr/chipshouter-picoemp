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


def test_hv_netclass_clearance_matches_validated_board():
    classes = {c['name']: c for c in _pro()['net_settings']['classes']}
    actual = classes['HV']['clearance']
    assert actual >= HV_CLEARANCE_MM, (
        f'HV clearance {actual} mm is looser than the {HV_CLEARANCE_MM} mm '
        'derived from the hi-pot-validated board'
    )


def test_hv_netclass_is_tighter_than_default():
    classes = {c['name']: c for c in _pro()['net_settings']['classes']}
    assert classes['HV']['clearance'] > classes['Default']['clearance'], (
        'HV clearance must exceed the default class, or it buys nothing'
    )


def test_every_hv_net_is_assigned_to_the_hv_class():
    """A missing pattern silently leaves an HV net on the 0.2 mm default."""
    pats = _pro()['net_settings'].get('netclass_patterns', [])
    assigned = {p['pattern'] for p in pats if p.get('netclass') == 'HV'}
    missing = HV_NETS - assigned
    assert not missing, f'HV nets not assigned to the HV class: {sorted(missing)}'
