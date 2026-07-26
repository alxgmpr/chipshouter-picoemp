"""Regression guard for the Task 5 IGBT/MOSFET pin-remap.

Q2/Q3/Q4 changed from letter-numbered pins (D/G/S) to numeric pins (1/2/3)
when their symbols were corrected to picoemp:IGBT_NCH_Diode and
Transistor_FET:Q_NMOS_GSD. KiCad matches wires to pins by number, so it
could not auto-preserve that renumbering across the symbol swap -- each
pin had to be manually reconnected to the uuid that carried the correct
physical connection. Getting this wrong swaps gate and collector on Q2,
a 650 V IGBT.

Every test in test_schematic.py only asserts `lib_id` strings; none of
them would notice a future edit that silently swaps which uuid maps to
which pin number (the symbol would still be "picoemp:IGBT_NCH_Diode",
lib_id tests all green, board destroyed). These tests parse the
*exported netlist* instead, so they see the same physical connectivity
kicad-cli sch export netlist -- and eventually fab -- would see.

Net *names* are intentionally NOT asserted: KiCad auto-generates them
from pin names, and they are free to drift (e.g. `Net-(Q3-PadD)` became
`Net-(Q3-D)` purely because Q3's pin name changed from letter "D" to
numeric "3", with no change in connectivity). What must NOT drift is
co-membership: which (ref, pin) pairs land on the same net.
"""
import pathlib
import shutil
import subprocess

import pytest

import kicad_parse as kp

KICAD_CLI_DEFAULT = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'


def _find_kicad_cli():
    found = shutil.which('kicad-cli')
    if found:
        return found
    if pathlib.Path(KICAD_CLI_DEFAULT).exists():
        return KICAD_CLI_DEFAULT
    return None


@pytest.fixture(scope='session')
def netlist_membership(root, tmp_path_factory):
    """Export the live schematic's netlist and return it as a list of
    sets of "REF.PIN" strings, one set per net (name discarded)."""
    cli = _find_kicad_cli()
    if cli is None:
        pytest.skip('kicad-cli not found on PATH or at the standard macOS install path')

    out_path = tmp_path_factory.mktemp('netlist') / 'picoemp.net'
    result = subprocess.run(
        [cli, 'sch', 'export', 'netlist', '--format', 'kicadsexpr',
         '-o', str(out_path), str(root / 'picoemp-rev2026.kicad_sch')],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        f'kicad-cli sch export netlist failed (exit {result.returncode}): '
        f'{result.stderr}'
    )

    tree = kp.parse_file(out_path)
    nets = []
    for net in kp._walk(tree, 'net'):
        members = set()
        for node in net:
            if isinstance(node, list) and node and node[0] == 'node':
                ref = pin = None
                for f in node:
                    if isinstance(f, list) and f and f[0] == 'ref':
                        ref = kp.sval(f[1])
                    elif isinstance(f, list) and f and f[0] == 'pin':
                        pin = kp.sval(f[1])
                if ref is not None and pin is not None:
                    members.add(f'{ref}.{pin}')
        nets.append(members)
    return nets


def _shares_net(nets, *pins):
    """True if every pin in `pins` (e.g. "Q2.1") lands on a common net."""
    wanted = set(pins)
    return any(wanted <= net for net in nets)


def _pins_of(nets, ref):
    """All pin numbers seen anywhere for `ref`, across all nets."""
    prefix = f'{ref}.'
    found = set()
    for net in nets:
        for member in net:
            if member.startswith(prefix):
                found.add(member[len(prefix):])
    return found


def test_igbt_pin_mapping_not_swapped(netlist_membership):
    """Q2 is picoemp:IGBT_NCH_Diode on the 650 V HV rail: pin 1=Gate,
    2=Collector, 3=Emitter. Swapping 1<->2 would put the low-voltage gate
    drive signal onto the HV collector and the switched HV rail onto the
    gate driver -- exactly the failure mode Task 5's guardrail existed to
    prevent."""
    assert _shares_net(netlist_membership, 'Q2.1', 'D7.1'), \
        'Q2 pin 1 (Gate) must share a net with D7 pin 1 (cathode / gate drive)'
    assert _shares_net(netlist_membership, 'Q2.2', 'J6.2'), \
        'Q2 pin 2 (Collector) must share a net with J6 pin 2 (HV output connector)'
    assert _shares_net(netlist_membership, 'Q2.3', 'D7.2'), \
        'Q2 pin 3 (Emitter) must share a net with D7 pin 2 (anode)'


def test_q3_gate_source_drain_pin_mapping(netlist_membership):
    """Q3 is Transistor_FET:Q_NMOS_GSD: pin 1=Gate, 2=Source, 3=Drain."""
    assert _shares_net(netlist_membership, 'Q3.1', 'D4.1'), \
        'Q3 pin 1 (Gate) must share a net with D4 pin 1 (cathode / gate drive)'
    assert _shares_net(netlist_membership, 'Q3.2', 'C1.1'), \
        'Q3 pin 2 (Source) must be grounded (shares GND with C1 pin 1)'
    assert _shares_net(netlist_membership, 'Q3.3', 'T1.1'), \
        'Q3 pin 3 (Drain) must share a net with T1 pin 1 (primary winding)'


def test_q4_gate_source_drain_pin_mapping(netlist_membership):
    """Q4 is Transistor_FET:Q_NMOS_GSD: pin 1=Gate, 2=Source, 3=Drain."""
    assert _shares_net(netlist_membership, 'Q4.1', 'D5.1'), \
        'Q4 pin 1 (Gate) must share a net with D5 pin 1 (cathode / gate drive)'
    assert _shares_net(netlist_membership, 'Q4.2', 'C1.1'), \
        'Q4 pin 2 (Source) must be grounded (shares GND with C1 pin 1)'
    assert _shares_net(netlist_membership, 'Q4.3', 'T2.1'), \
        'Q4 pin 3 (Drain) must share a net with T2 pin 1 (primary winding)'


def test_transformers_have_all_four_pins_and_correct_winding_grouping(netlist_membership):
    """picoemp:ATB322524 is wired primary=1,4 / secondary=2,3 in this
    design -- NOT the stock Device:Transformer_1P_1S grouping of 1,2/3,4.
    Assert all 4 pins are present, and that pin 1 (primary) sits with the
    switching FET's drain while pin 4 (primary) sits with the reservoir
    cap, and pins 2/3 (secondary) sit with the rectifier diodes -- this
    locks the winding grouping to the netlist rather than to a comment or
    to the symbol's arc artwork, either of which could drift silently."""
    for ref in ('T1', 'T2'):
        assert _pins_of(netlist_membership, ref) == {'1', '2', '3', '4'}, \
            f'{ref} must expose exactly pins 1-4'

    # Primary (pins 1, 4): pin 1 <-> switching FET drain, pin 4 <-> reservoir cap.
    assert _shares_net(netlist_membership, 'T1.1', 'Q3.3'), \
        'T1 pin 1 (primary) must share a net with Q3 pin 3 (Drain)'
    assert _shares_net(netlist_membership, 'T1.4', 'C1.2'), \
        'T1 pin 4 (primary) must share a net with C1 pin 2 (reservoir cap)'
    assert _shares_net(netlist_membership, 'T2.1', 'Q4.3'), \
        'T2 pin 1 (primary) must share a net with Q4 pin 3 (Drain)'
    assert _shares_net(netlist_membership, 'T2.4', 'C5.2'), \
        'T2 pin 4 (primary) must share a net with C5 pin 2 (reservoir cap)'

    # Secondary (pins 2, 3): rectifier diode anodes, not the primary side.
    assert _shares_net(netlist_membership, 'T1.2', 'D2.2'), \
        'T1 pin 2 (secondary) must share a net with D2 pin 2 (anode)'
    assert _shares_net(netlist_membership, 'T1.3', 'D7.2'), \
        'T1 pin 3 (secondary) must share a net with D7 pin 2 (anode)'
    assert _shares_net(netlist_membership, 'T2.2', 'D7.2'), \
        'T2 pin 2 (secondary) must share a net with D7 pin 2 (anode)'
    assert _shares_net(netlist_membership, 'T2.3', 'R7.2'), \
        'T2 pin 3 (secondary) must share a net with R7 pin 2'
