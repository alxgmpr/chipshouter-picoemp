"""Host-side checks on the bring-up firmware.

Two things are enforced here. First, the scripts' pin numbers must match
the board -- a transposed digit would light the wrong LED at best and
drive HVPWM at worst. Second, bringup.py must remain structurally unable
to make high voltage: Phase 2 of the spec claims "there is no command, no
code path, and no button that can make high voltage", and that claim is
only worth anything if something checks it.

Spec: docs/superpowers/specs/2026-08-05-picoemp-rev2026-bringup-design.md
"""

import ast
import subprocess

import pytest

import conftest
from test_netlist import KC, _nets

REPO = conftest.ROOT.parents[1]
BRINGUP = REPO / 'firmware' / 'micropython' / 'bringup.py'
CHARGETEST = REPO / 'firmware' / 'micropython' / 'chargetest.py'

# Raspberry Pi Pico GPIO number -> physical pad number on the module.
# The Pico is not regularly numbered (GND pads interrupt the sequence at
# 3, 8, 13, 18, 23, 28, 33, 38), so this is an explicit table rather than
# arithmetic.
GPIO_TO_PAD = {
    0: 1, 1: 2, 2: 4, 3: 5, 4: 6, 5: 7, 6: 9, 7: 10, 8: 11, 9: 12,
    10: 14, 11: 15, 12: 16, 13: 17, 14: 19, 15: 20, 16: 21, 17: 22,
    18: 24, 19: 25, 20: 26, 21: 27, 22: 29, 26: 31, 27: 32, 28: 34,
}

# bringup.py constant name -> net-name fragment its GPIO must land on.
BRINGUP_PINS = {
    'PIN_STATUS_LED': 'STATUS_LED',
    'PIN_HV_DET_LED': 'HV_DET_LED',
    'PIN_CHARGE_LED': 'CHARGE_LED',
    'PIN_ARM_SW': 'ARM_SW',
    'PIN_PULSE_SW': 'PULSE_SW',
    'PIN_CHARGED': 'CHARGED',
}

# GPIOs that must never appear in bringup.py, and why.
FORBIDDEN_IN_BRINGUP = {
    20: 'HVPWM -- would enable charging',
    14: 'HVPULSE -- pulsing is out of scope',
}


def _constants(path):
    """Module-level `NAME = <int>` assignments, as a dict."""
    tree = ast.parse(path.read_text())
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, int):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    out[target.id] = node.value.value
    return out


def _int_literals(path):
    """Every integer literal anywhere in the module."""
    return {n.value for n in ast.walk(ast.parse(path.read_text()))
            if isinstance(n, ast.Constant) and isinstance(n.value, int)}


@pytest.fixture(scope='module')
def node_to_net(tmp_path_factory):
    out = tmp_path_factory.mktemp('net') / 'net.net'
    subprocess.run([KC, 'sch', 'export', 'netlist', '--format', 'kicadsexpr',
                    '-o', str(out), str(conftest.SCH)], check=True,
                   capture_output=True)
    nets = _nets(out.read_text())
    return {n: name for name, nodes in nets.items() for n in nodes}


def test_bringup_pin_map_matches_netlist(node_to_net):
    """Every pin constant lands on the net its name claims."""
    consts = _constants(BRINGUP)
    for name, fragment in BRINGUP_PINS.items():
        assert name in consts, f'{name} not defined in bringup.py'
        gpio = consts[name]
        assert gpio in GPIO_TO_PAD, f'{name} = GP{gpio} is not a Pico GPIO'
        node = f'U1.{GPIO_TO_PAD[gpio]}'
        assert node in node_to_net, f'{name} = GP{gpio} ({node}) is not connected'
        assert fragment in node_to_net[node], \
            f'{name} = GP{gpio} sits on net {node_to_net[node]!r}, expected {fragment!r}'


def test_bringup_cannot_drive_hv():
    """bringup.py must not mention GP20 or GP14 at all.

    This is deliberately blunt. Checking "GP20 is only used behind a guard"
    would require reasoning about reachability; checking that the number
    never appears is decidable, and costs nothing because bringup.py has
    no legitimate reason to reference either pin.
    """
    literals = _int_literals(BRINGUP)
    for gpio, why in FORBIDDEN_IN_BRINGUP.items():
        assert gpio not in literals, \
            f'bringup.py contains the literal {gpio} -- {why}'


def test_bringup_never_references_pwm():
    """No PWM name in the code means no way to drive the transformer at all.

    Checked over the AST, not the raw text: the header comment legitimately
    names HVPWM when explaining what the script does not do, and a substring
    search would flag that.
    """
    tree = ast.parse(BRINGUP.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            assert node.id != 'PWM', 'bringup.py references the name PWM'
        elif isinstance(node, ast.Attribute):
            assert node.attr != 'PWM', 'bringup.py references an attribute PWM'
        elif isinstance(node, ast.ImportFrom):
            imported = {a.name for a in node.names}
            assert 'PWM' not in imported, \
                f'bringup.py imports PWM from {node.module}'


def test_chargetest_pin_map_matches_netlist(node_to_net):
    """chargetest.py's own pin constants land on the right nets."""
    expected = {
        'PIN_HVPWM': 'HVPWM',
        'PIN_CHARGED': 'CHARGED',
        'PIN_HV_DET_LED': 'HV_DET_LED',
    }
    consts = _constants(CHARGETEST)
    for name, fragment in expected.items():
        assert name in consts, f'{name} not defined in chargetest.py'
        gpio = consts[name]
        assert gpio in GPIO_TO_PAD, f'{name} = GP{gpio} is not a Pico GPIO'
        node = f'U1.{GPIO_TO_PAD[gpio]}'
        assert node in node_to_net, f'{name} = GP{gpio} ({node}) is not connected'
        assert fragment in node_to_net[node], \
            f'{name} = GP{gpio} sits on net {node_to_net[node]!r}, expected {fragment!r}'


def test_chargetest_does_not_pulse():
    """Pulsing is out of scope: GP14 must not appear."""
    assert 14 not in _int_literals(CHARGETEST), \
        'chargetest.py contains the literal 14 -- HVPULSE, pulsing is out of scope'


def test_chargetest_pwm_is_bounded():
    """Charging must be enabled only inside a try whose finally stops it.

    Without this, an exception mid-charge (a keyboard interrupt from
    mpremote, an mpremote disconnect) leaves the transformer running with
    nobody watching.
    """
    tree = ast.parse(CHARGETEST.read_text())
    tries = [n for n in ast.walk(tree) if isinstance(n, ast.Try) and n.finalbody]
    assert tries, 'chargetest.py has no try/finally'

    def calls_pwm_off(nodes):
        return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                   and n.func.id == 'pwm_off'
                   for node in nodes for n in ast.walk(node))

    assert any(calls_pwm_off(t.finalbody) for t in tries), \
        'no try/finally in chargetest.py calls pwm_off() in its finally'

    # The PWM must actually be started inside that try, not before it.
    def calls_pwm_on(nodes):
        return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                   and n.func.id == 'pwm_on'
                   for node in nodes for n in ast.walk(node))

    guarded = [t for t in tries if calls_pwm_off(t.finalbody) and calls_pwm_on(t.body)]
    assert guarded, \
        'pwm_on() is not called inside the try that stops it -- an exception ' \
        'between starting the PWM and entering the try would leave it running'


@pytest.mark.parametrize('script', [BRINGUP, CHARGETEST], ids=['bringup', 'chargetest'])
def test_charged_readers_configure_both_pads(script):
    """A script reading CHARGED must configure GP26 as well as GP18.

    CHARGED lands on two Pico pads -- GP18 (U1.24) and GP26/ADC0 (U1.31).
    The RP2040 resets every pad with its pull-down enabled (PADS_BANK0
    reset value 0x56, bit 2 PDE=1), so a script that configures only GP18
    leaves GP26's ~65k pull-down hanging on the net. Two pull-downs in
    parallel against R6's 22k pull-up divide the net to roughly 2 V, which
    sits inside the RP2040's indeterminate band (VIL 0.99 V, VIH 2.31 V).
    The digital read then returns 0 or 1 arbitrarily.

    Observed on board #1 on 2026-08-05: bringup.py read 1 at rest and
    chargetest.py read 0 at rest, twenty minutes apart, with nothing
    electrical having changed. Measuring the net through ADC0 showed
    3.20 V once GP26 was configured, confirming no charge was present.
    """
    consts = _constants(script)
    if 'PIN_CHARGED' not in consts:
        pytest.skip(f'{script.name} does not read CHARGED')
    assert 'PIN_CHARGED_ADC' in consts, \
        (f'{script.name} reads CHARGED on GP18 but never configures GP26, the '
         f'other pad on that net -- its default pull-down will drag the net '
         f'into the indeterminate input band')
    assert consts['PIN_CHARGED_ADC'] == 26, \
        f"PIN_CHARGED_ADC = {consts['PIN_CHARGED_ADC']}, expected 26 (ADC0)"


@pytest.mark.parametrize('script', [BRINGUP, CHARGETEST], ids=['bringup', 'chargetest'])
def test_charged_pads_are_on_one_net(node_to_net, script):
    """Both configured pads really are the same net on this board."""
    consts = _constants(script)
    if 'PIN_CHARGED' not in consts:
        pytest.skip(f'{script.name} does not read CHARGED')
    nets = set()
    for name in ('PIN_CHARGED', 'PIN_CHARGED_ADC'):
        gpio = consts[name]
        node = f'U1.{GPIO_TO_PAD[gpio]}'
        assert node in node_to_net, f'{name} = GP{gpio} ({node}) is not connected'
        nets.add(node_to_net[node])
    assert len(nets) == 1, \
        f'{script.name}: GP18 and GP26 are on different nets {nets} -- the ' \
        f'two-pad assumption behind this fix does not hold'


def test_chargetest_has_a_charge_timeout():
    """A charge attempt must be time-bounded, per the spec's Phase 3."""
    consts = _constants(CHARGETEST)
    assert 'CHARGE_TIMEOUT_MS' in consts, 'no CHARGE_TIMEOUT_MS in chargetest.py'
    assert 0 < consts['CHARGE_TIMEOUT_MS'] <= 30000, \
        f"CHARGE_TIMEOUT_MS = {consts['CHARGE_TIMEOUT_MS']} is not a sane bound"
