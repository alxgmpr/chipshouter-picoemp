import subprocess

import pytest

import conftest
import kicad_parse as kp

KC = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'


def test_erc_clean(tmp_path):
    report = tmp_path / 'erc.rpt'
    proc = subprocess.run(
        [KC, 'sch', 'erc', '--severity-error', '--exit-code-violations',
         '-o', str(report), str(conftest.SCH)],
        capture_output=True, text=True)
    assert proc.returncode == 0, f'ERC violations:\n{report.read_text()}'


def _nets(netlist_text):
    """Map net name -> set of 'REF.PIN' strings.

    The brief's original implementation used a regex assuming
    `(net (code "C") (name "N")...)` sat on one line. kicad-cli actually
    emits one token per line (`(net\n\t(code "C")\n\t(name "N")\n...)`), so
    that regex matched zero nets. Parsed structurally instead, via the same
    s-expression parser the rest of this test suite already uses -- robust
    to whitespace/formatting, unlike a hand-rolled regex.
    """
    tree = kp.parse(netlist_text)

    def walk(node):
        if isinstance(node, list):
            if node and node[0] == 'net':
                yield node
            for child in node:
                yield from walk(child)

    nets = {}
    for net_node in walk(tree):
        name = None
        nodes = set()
        for e in net_node:
            if not (isinstance(e, list) and e):
                continue
            if e[0] == 'name':
                name = kp.sval(e[1])
            elif e[0] == 'node':
                ref = pin = None
                for f in e:
                    if isinstance(f, list) and f and f[0] == 'ref':
                        ref = kp.sval(f[1])
                    elif isinstance(f, list) and f and f[0] == 'pin':
                        pin = kp.sval(f[1])
                if ref is not None and pin is not None:
                    nodes.add(f'{ref}.{pin}')
        if name is not None:
            nets[name] = nodes
    return nets


def test_pico_pin_assignment_unchanged(tmp_path):
    """The firmware pin map must not drift. See spec section 2."""
    out = tmp_path / 'net.net'
    subprocess.run([KC, 'sch', 'export', 'netlist', '--format', 'kicadsexpr',
                    '-o', str(out), str(conftest.SCH)], check=True,
                   capture_output=True)
    nets = _nets(out.read_text())
    node_to_net = {n: name for name, nodes in nets.items() for n in nodes}

    # Pico physical pad -> net name fragment it must belong to.
    expected = {'U1.19': 'HVPULSE', 'U1.24': 'CHARGED',
                'U1.26': 'HVPWM', 'U1.31': 'CHARGED'}
    for node, frag in expected.items():
        assert node in node_to_net, f'{node} not connected'
        assert frag in node_to_net[node], \
            f'{node} on net {node_to_net[node]!r}, expected to contain {frag!r}'


def test_trigger_front_end_connectivity(tmp_path):
    """Netlist-level regression cover for the trigger front-end -- the only
    genuinely new circuitry in this revision, and the highest-risk item in
    the task: a swapped or floating buffer supply pin destroys the part
    (and possibly the Pico's GPIO), and an accidental direct reconnection
    of P1.1 to GP0 would silently bypass the Schmitt buffer and its series
    protection entirely, with no visual difference in the schematic render.
    Auto-generated net names drift across re-exports (see other tests in
    this file), so every check here is by pin co-membership, never by net
    name string.
    """
    out = tmp_path / 'net.net'
    subprocess.run([KC, 'sch', 'export', 'netlist', '--format', 'kicadsexpr',
                    '-o', str(out), str(conftest.SCH)], check=True,
                   capture_output=True)
    nets = _nets(out.read_text())
    node_to_net = {n: name for name, nodes in nets.items() for n in nodes}

    def same_net(a, b):
        assert a in node_to_net, f'{a} not connected'
        assert b in node_to_net, f'{b} not connected'
        return node_to_net[a] == node_to_net[b]

    # U2 is powered from the Pico's own regulated 3V3 rail (U1 pin 36).
    assert same_net('U2.5', 'U1.36'), \
        'U2 VCC (pin 5) is not on the same net as U1.36 (3V3) -- buffer would be unpowered'
    # U2 is grounded. R5.1 is a pre-existing, unrelated component already
    # known to sit on the board GND net -- used as a stable anchor rather
    # than one of this task's own new parts.
    assert same_net('U2.3', 'R5.1'), \
        'U2 GND (pin 3) is not on the board ground net -- buffer would float'
    # U2's input reads the R14/R15 divider node.
    assert same_net('U2.2', 'R14.2'), \
        'U2 A (pin 2, input) is not on the same net as R14.2'
    assert same_net('U2.2', 'R15.1'), \
        'U2 A (pin 2, input) is not on the same net as R15.1'
    # U2's output drives GP0.
    assert same_net('U2.4', 'U1.1'), \
        'U2 Y (pin 4, output) is not on the same net as U1.1 (GP0) -- buffer output is not driving GPIO0'
    # The raw trigger input (header pin + optional DNP SMA) feeds R14.
    assert same_net('P1.1', 'J4.1'), \
        'P1.1 and J4.1 (parallel trigger inputs) are not on the same net'
    assert same_net('P1.1', 'R14.1'), \
        'P1.1 is not on the same net as R14.1 (series input resistor)'

    # THE regression this test exists to catch: P1.1 must NOT be directly
    # wired to GP0 any more. A direct reconnect would bypass the Schmitt
    # buffer and series/pulldown protection entirely and put the raw,
    # unbuffered trigger signal straight on the Pico's GPIO -- silently,
    # since nothing else in this suite checks for it.
    assert not same_net('P1.1', 'U1.1'), \
        'P1.1 and U1.1 (GP0) are on the same net -- the direct trigger-to-GPIO ' \
        'path has been reconnected, bypassing the buffer'


def test_hv_charge_feedback_led_path_intact(tmp_path):
    """Regression cover for the Q1 optocoupler LED feedback path.

    Q1 is an LDA111 optocoupler that provides HV charge feedback: its LED
    (pins 1/2, anode/cathode) must sit in series between the HV+ tap
    (through R2 and R1) and the HV return, so that LED current flows and
    the phototransistor half (pins 4/5/6) can pull /CHARGED. The
    as-received Altium->KiCad import left Q1 pin 1 (the LED anode)
    unconnected while R1's free end ran straight to the HV return instead
    -- silently shorting the LED out of the circuit. With no LED current,
    the phototransistor never conducts, /CHARGED never asserts, and the
    firmware's charge feedback is dead, even though the schematic renders
    with no obviously missing wires. Every check here is by pin
    co-membership, never by net name string, since auto-generated net
    names drift across re-exports (see other tests in this file).
    """
    out = tmp_path / 'net.net'
    subprocess.run([KC, 'sch', 'export', 'netlist', '--format', 'kicadsexpr',
                    '-o', str(out), str(conftest.SCH)], check=True,
                   capture_output=True)
    nets = _nets(out.read_text())
    node_to_net = {n: name for name, nodes in nets.items() for n in nodes}

    def same_net(a, b):
        assert a in node_to_net, f'{a} not connected'
        assert b in node_to_net, f'{b} not connected'
        return node_to_net[a] == node_to_net[b]

    # R1 is a resistor -- which physical pin faces the tap vs. Q1 is
    # electrically irrelevant, so find whichever one Q1.1 actually landed
    # on rather than hard-coding an orientation.
    r1_pins = ['R1.1', 'R1.2']
    q1_pin_for_r1 = [p for p in r1_pins if same_net('Q1.1', p)]
    assert len(q1_pin_for_r1) == 1, \
        f'Q1.1 (LED anode) must share a net with exactly one R1 pin, found {q1_pin_for_r1}'
    other_r1_pin = [p for p in r1_pins if p not in q1_pin_for_r1][0]

    # Q1.2 (LED cathode) is the HV return, shared with Q2.3.
    assert same_net('Q1.2', 'Q2.3'), \
        'Q1.2 (LED cathode) is not on the same net as Q2.3 (HV return) -- ' \
        'feedback LED cathode has come adrift from the HV return'

    # R2 (300k, HV rail dropper) bridges the HV rail down to the same node
    # R1's other pin sits on -- i.e. HV+ -> R2 -> [tap] -> R1 -> Q1.1.
    r2_pins = ['R2.1', 'R2.2']
    assert any(same_net(other_r1_pin, p) for p in r2_pins), \
        f'Neither R2 pin shares a net with {other_r1_pin} -- the HV+ -> R2 -> ' \
        'R1 -> Q1.1 feedback divider is broken'

    # THE regression this test exists to catch: Q1 pin 1 (LED anode) must
    # not be left floating. A floating anode silently kills HV charge
    # feedback -- no LED current, no phototransistor conduction, /CHARGED
    # never asserts -- with no visual difference in the schematic render.
    assert not node_to_net['Q1.1'].startswith('unconnected-'), \
        'Q1.1 (LED anode) is on an unconnected-* net -- the feedback LED ' \
        'anode is floating again'


def test_mounting_holes_and_lda111_pin3_no_connect(tmp_path):
    """Regression cover for the MH1-3 symbol/footprint mismatch fix and the
    LDA111 pin 3 no-connect restoration.

    MH1-3 previously used Mechanical:MountingHole_Pad_MP (pin "MP") paired
    with footprint MountingHole:MountingHole_3.2mm_M3_Pad_Via (pad "1") --
    a numbering mismatch in both directions that produced per-hole ERC
    warnings/errors, and left plated copper floating at no defined
    potential right in the HV region. They were switched to
    Mechanical:MountingHole / MountingHole:MountingHole_3.2mm_M3, which
    have no pins and no pads at all, so MH1-3 must contribute zero pins
    to the netlist.

    Separately, LDA111 (Q1) pin 3 is electrically NC but its lead
    physically exists on the SOP-6 package. It must appear in the netlist
    as its own no-connect node -- omitting it entirely (as the buggy
    symbol did) or accidentally tying it to another net would both be
    wrong.
    """
    out = tmp_path / 'net.net'
    subprocess.run([KC, 'sch', 'export', 'netlist', '--format', 'kicadsexpr',
                    '-o', str(out), str(conftest.SCH)], check=True,
                   capture_output=True)
    nets = _nets(out.read_text())
    node_to_net = {n: name for name, nodes in nets.items() for n in nodes}

    # MH1-3 must contribute no pins at all -- no MHn.* node of any kind.
    mh_nodes = [n for n in node_to_net if n.split('.')[0] in ('MH1', 'MH2', 'MH3')]
    assert mh_nodes == [], \
        f'MH1-3 must have no pins/pads in the netlist, found: {mh_nodes}'

    # Q1.3 must exist, and sit on its own unconnected/no-connect net rather
    # than being silently tied to some other signal.
    assert 'Q1.3' in node_to_net, 'Q1.3 (LDA111 pin 3, NC) is missing from the netlist'
    assert node_to_net['Q1.3'].startswith('unconnected-'), \
        f'Q1.3 expected on an unconnected-* net, found {node_to_net["Q1.3"]!r}'
