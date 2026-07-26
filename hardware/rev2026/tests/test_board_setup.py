"""Board-setup invariants for the high-voltage section.

This board generates roughly 500 V and relies on an isolation barrier between
the HV side (C3, D2, T1/T2 secondaries, Q2, J3, R1, R2) and the logic side.
The as-received port shipped with ``min_clearance = 0.0`` — DRC enforcing
nothing at all — and no HV net class.

The 0.75 mm figure is derived, not invented. Measuring pad geometry on the
hi-pot-validated original board (``hardware/altium_src/kc/ChipShouter-Pico.kicad_pcb``)
gives an isolation barrier of 0.770 mm at T1's own primary-to-secondary pad
spacing and ~1.002 mm in routed copper. 0.75 mm sits just under the
part-imposed floor so T1/T2's own pads do not false-flag on every DRC run,
while still being 3.75x the default class.

Note the original board's *net labels* are unreliable — a track labelled
NetQ1_1 terminates on a pad labelled NetJ3_2 — so the measurement above used
pad geometry classified by component, never by net name.

Full IEC 60664-1 creepage at 600 V would want ~3.2 mm, which is not achievable
in this form factor. That is why the J3 milled slot exists and why upstream
hi-pot tests rather than relying on spacing alone.
"""
import json

import conftest

HV_CLEARANCE_MM = 0.75

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
