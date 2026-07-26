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
