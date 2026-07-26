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
