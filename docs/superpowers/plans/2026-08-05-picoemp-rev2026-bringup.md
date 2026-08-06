# PicoEMP Rev-2026 Bring-Up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Take the first hand-assembled Rev-2026 board from "just soldered" to a verified charge-and-discharge cycle, with every step gated on a cheaper test passing first.

**Architecture:** Two throwaway-safe MicroPython scripts plus a measurement log. `bringup.py` exercises LEDs, buttons and the CHARGED input and is *structurally incapable* of making high voltage — it never references GP20 or GP14, and a host-side AST test enforces that permanently. `chargetest.py` is the only file that touches GP20, and does so under a hard timeout in a `try/finally`. Bench phases are recorded in a log file so a failure is diagnosable later.

**Tech Stack:** MicroPython on RP2040/RP2350; `mpremote` over USB CDC (driven from Bash, no Thonny needed); pytest for host-side static checks; `kicad-cli` netlist export as the pin-map source of truth.

## Global Constraints

- **Spec:** `docs/superpowers/specs/2026-08-05-picoemp-rev2026-bringup-design.md`. All section references below are to it.
- **Pulsing is out of scope.** No task may configure GP14 (`HVPULSE`). No injection tip exists.
- **Phase order is a safety gate.** A failing phase stops the sequence; do not proceed to the next task.
- **Discharge before contact.** Hold `SW3` one second before touching the board any time it has been armed.
- **Never touch J1.** Its centre pin carries `HV_RAIL` continuously while charged, not only during a pulse.
- **Python via `uv` only** (`uv run --with pytest pytest`), per `hardware/rev2026/CLAUDE.md`. Never bare `pip`.
- Charge PWM parameters are fixed at **2500 Hz, `duty_u16(800)`** — the empirically tuned values from `firmware/micropython/cspico_simple.py`. Do not retune.
- Rail voltage is **never measured** (§7). `CHARGED` asserting proves the sense chain conducts, not that the rail is 250 V.

## File Structure

| File | Responsibility |
|---|---|
| `hardware/rev2026/BRINGUP-LOG.md` | Measured values and pass/fail per phase. Created Task 1, appended thereafter. |
| `firmware/micropython/bringup.py` | Phase 2 I/O self-test. Provably cannot charge. Never edited to add charging. |
| `firmware/micropython/chargetest.py` | Phase 3 commanded, timeout-bounded charge/discharge. The only file touching GP20. |
| `hardware/rev2026/tests/test_bringup_firmware.py` | Host-side: pin map matches netlist; safety invariants hold. |

Splitting the two scripts is deliberate. Keeping `bringup.py` permanently charge-free makes "Phase 2 cannot make high voltage" a checkable invariant rather than a claim about a code path.

---

### Task 1: Phase 0 — cold checks and the log

No power, no code. Deliverable is a completed measurement table.

**Files:**
- Create: `hardware/rev2026/BRINGUP-LOG.md`

**Interfaces:**
- Consumes: nothing.
- Produces: `BRINGUP-LOG.md` with a `## Phase 0` section. Later tasks append `## Phase N` sections in the same table format.

- [ ] **Step 1: Confirm the board has never been energized**

If it has been powered since assembly, hold `SW3` for one second before proceeding. C3 self-bleeds at τ ≈ 9.5 s but stalls at the opto LED knee, so time alone is not sufficient.

- [ ] **Step 2: Take the six readings**

DMM on resistance. Probe points per §4:

| # | Measurement | Expect | Failure means |
|---|---|---|---|
| 0.1 | J1 centre pin → J3.2 | 300 kΩ ±5 % | `R2` missing/bad — no fast discharge path |
| 0.2 | **Hold SW3**, J1 centre pin → J3.1 | 300 kΩ ±5 % | `SW3` not closing — no manual discharge |
| 0.3 | P3.3 (GND) → J3.1 | open, > 20 MΩ | Isolation barrier breached |
| 0.4 | J1 centre pin → J1 shell | not a short | IGBT `Q2` shorted collector-to-emitter |
| 0.5 | P3.2 (+3V3) → P3.3 (GND) | not a short | 3V3 rail fault |
| 0.6 | J2.1 → J2.2 | not a short | Input rail fault |

Expected-but-not-a-fault: `J3.2 → J3.1` with SW3 **released** reads open, not 20 MΩ. The DMM's ohms source is under 1 V and will not forward-bias the opto LED in series with R1.

- [ ] **Step 3: Write the log**

Create `hardware/rev2026/BRINGUP-LOG.md`:

```markdown
# Rev-2026 Bring-Up Log — Board #1

Plan: `docs/superpowers/plans/2026-08-05-picoemp-rev2026-bringup.md`
Spec: `docs/superpowers/specs/2026-08-05-picoemp-rev2026-bringup-design.md`

Equipment: DMM; bench PSU with current limit. No scope, no HV probe.

---

## Phase 0 — cold checks

Date: YYYY-MM-DD

| # | Measurement | Expected | Measured | Pass |
|---|---|---|---|---|
| 0.1 | J1 centre → J3.2 | 300 kΩ ±5 % | | |
| 0.2 | Hold SW3, J1 centre → J3.1 | 300 kΩ ±5 % | | |
| 0.3 | GND → J3.1 | open > 20 MΩ | | |
| 0.4 | J1 centre → J1 shell | not a short | | |
| 0.5 | +3V3 → GND | not a short | | |
| 0.6 | J2.1 → J2.2 | not a short | | |

Notes:
```

Fill in the Measured and Pass columns with the actual readings. Replace `YYYY-MM-DD` with the real date.

- [ ] **Step 4: Gate**

If any row fails, stop. Do not start Task 2. Record what failed in Notes.

- [ ] **Step 5: Commit**

```bash
git add hardware/rev2026/BRINGUP-LOG.md
git commit -m "Phase 0 cold checks on board #1"
```

---

### Task 2: Phase 1 — first power, current-limited

**Files:**
- Modify: `hardware/rev2026/BRINGUP-LOG.md`

**Interfaces:**
- Consumes: Task 1's gate (Phase 0 all-pass).
- Produces: a powered board known free of assembly shorts.

- [ ] **Step 1: Set up the supply**

Bench PSU to **5.0 V, current limit 100 mA**, output OFF. USB unplugged. The Pico is unprogrammed at this point — that is intentional. GPIOs default high-Z and `R5`/`R10` hold Q3's and Q4's gates at GND, so HV-off is the passive state and no firmware bug can change it.

Connect to `J2` (S2B-XH-A, JST XH 2.50 mm): **pin 1 = `VEXT_IN`, pin 2 = `GND`**. Verify polarity with the DMM against P3.3 before enabling the output.

- [ ] **Step 2: Enable output and read**

| Reading | Expect |
|---|---|
| PSU current | well under 100 mA, not in limit |
| P3.2 → P3.3 | 3.3 V ±5 % |

If the PSU goes into current limit, switch off immediately and stop. That is the assembly-short screen doing its job.

- [ ] **Step 3: Append to the log**

```markdown
## Phase 1 — first power, current-limited

Date: YYYY-MM-DD
PSU: 5.0 V, limit 100 mA, into J2. USB unplugged. Pico unprogrammed.

| Reading | Expected | Measured | Pass |
|---|---|---|---|
| PSU current | < 100 mA, no limit | | |
| +3V3 (P3.2 → P3.3) | 3.3 V ±5 % | | |

Notes:
```

- [ ] **Step 4: Power down**

PSU output off, disconnect J2. Remaining phases run on USB.

- [ ] **Step 5: Commit**

```bash
git add hardware/rev2026/BRINGUP-LOG.md
git commit -m "Phase 1 first power on board #1"
```

---

### Task 3: `bringup.py` and its safety invariant

Host-side work. No hardware needed; can be done while the board sits unpowered.

**Files:**
- Create: `firmware/micropython/bringup.py`
- Create: `hardware/rev2026/tests/test_bringup_firmware.py`

**Interfaces:**
- Consumes: `tests/test_netlist.py::_nets` (existing helper mapping a kicad-cli netlist to `{net_name: {"REF.PIN", ...}}`), `tests/conftest.py::SCH`.
- Produces: `firmware/micropython/bringup.py` exposing module-level int constants `PIN_STATUS_LED = 7`, `PIN_HV_DET_LED = 6`, `PIN_CHARGE_LED = 27`, `PIN_ARM_SW = 28`, `PIN_PULSE_SW = 11`, `PIN_CHARGED = 18`, and a `main()` taking no arguments. Task 6's test imports `GPIO_TO_PAD` from `tests/test_bringup_firmware.py`.

- [ ] **Step 1: Write the failing tests**

Create `hardware/rev2026/tests/test_bringup_firmware.py`:

```python
"""Host-side checks on the bring-up firmware.

Two things are enforced here. First, the scripts' pin numbers must match
the board -- a transposed digit would light the wrong LED at best and
drive HVPWM at worst. Second, bringup.py must remain structurally unable
to make high voltage: Phase 2 of the spec claims "there is no command, no
code path, and no button that can make high voltage", and that claim is
only worth anything if something checks it.
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
FORBIDDEN_IN_BRINGUP = {20: 'HVPWM -- would enable charging', 14: 'HVPULSE -- pulsing is out of scope'}


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


def test_bringup_never_imports_pwm():
    """No PWM import means no way to drive the transformer, whatever the pin."""
    source = BRINGUP.read_text()
    assert 'PWM' not in source, 'bringup.py references PWM'
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd hardware/rev2026 && uv run --with pytest pytest tests/test_bringup_firmware.py -v
```

Expected: all three FAIL — `bringup.py` does not exist yet, so `_constants` raises `FileNotFoundError`.

- [ ] **Step 3: Write `firmware/micropython/bringup.py`**

```python
# PicoEMP bring-up self-test -- Phase 2
#
# Exercises every LED, both buttons and the CHARGED input, and prints a
# structured result. It CANNOT make high voltage: GP20 (HVPWM) and GP14
# (HVPULSE) are never referenced, so both stay high-Z and R5/R10 hold the
# Q3/Q4 gates at GND. `tests/test_bringup_firmware.py` enforces that.
#
# Run with:  mpremote connect <port> run bringup.py
# Do not save this as main.py -- it is a test, not the firmware.

from machine import Pin
import utime

PIN_STATUS_LED = 7
PIN_HV_DET_LED = 6
PIN_CHARGE_LED = 27
PIN_ARM_SW = 28
PIN_PULSE_SW = 11
PIN_CHARGED = 18

LEDS = (
    ('STATUS', PIN_STATUS_LED),
    ('HV_DET', PIN_HV_DET_LED),
    ('CHARGE', PIN_CHARGE_LED),
)

BUTTON_TIMEOUT_MS = 15000


def led_walk():
    """Light each LED alone for a second, then all three together."""
    pins = [(name, Pin(gpio, Pin.OUT)) for name, gpio in LEDS]
    for _, pin in pins:
        pin.off()
    for name, pin in pins:
        print('LED %s: ON -- confirm it lit' % name)
        pin.on()
        utime.sleep_ms(1000)
        pin.off()
    print('LED ALL: ON')
    for _, pin in pins:
        pin.on()
    utime.sleep_ms(2000)
    for _, pin in pins:
        pin.off()
    print('LED ALL: OFF')


def wait_for_press(name, pin, pressed_level):
    """Block until `pin` reads `pressed_level`, or the timeout expires."""
    print('BUTTON %s: press it now (%d s)' % (name, BUTTON_TIMEOUT_MS // 1000))
    deadline = utime.ticks_add(utime.ticks_ms(), BUTTON_TIMEOUT_MS)
    while utime.ticks_diff(deadline, utime.ticks_ms()) > 0:
        if pin.value() == pressed_level:
            print('BUTTON %s: PASS' % name)
            return True
        utime.sleep_ms(10)
    print('BUTTON %s: FAIL -- no press seen' % name)
    return False


def main():
    print('=== PicoEMP bring-up self-test (Phase 2) ===')
    print('HVPWM and HVPULSE are not driven by this script.')

    led_walk()

    # SW1 pulls ARM_SW up to +3V3, so pressed reads high against a pulldown.
    arm = Pin(PIN_ARM_SW, Pin.IN, Pin.PULL_DOWN)
    # SW2 pulls PULSE_SW down to GND, so pressed reads low against a pullup.
    pulse = Pin(PIN_PULSE_SW, Pin.IN, Pin.PULL_UP)
    # R6 already pulls CHARGED up to +3V3; the opto pulls it low when the
    # rail is charged. No internal pull.
    charged = Pin(PIN_CHARGED, Pin.IN)

    print('CHARGED idle level: %d (1 = not charged, expected at rest)'
          % charged.value())

    ok_arm = wait_for_press('ARM', arm, 1)
    ok_pulse = wait_for_press('PULSE', pulse, 0)

    print('=== RESULT: %s ===' % ('PASS' if (ok_arm and ok_pulse) else 'FAIL'))


main()
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd hardware/rev2026 && uv run --with pytest pytest tests/test_bringup_firmware.py -v
```

Expected: `test_bringup_pin_map_matches_netlist`, `test_bringup_cannot_drive_hv` and `test_bringup_never_imports_pwm` all PASS.

- [ ] **Step 5: Run the full suite for regressions**

```bash
cd hardware/rev2026 && uv run --with pytest pytest tests/
```

Expected: 66 pre-existing tests still pass, plus the 3 new ones.

- [ ] **Step 6: Commit**

```bash
git add firmware/micropython/bringup.py hardware/rev2026/tests/test_bringup_firmware.py
git commit -m "Phase 2 bring-up self-test, with its no-HV invariant enforced"
```

---

### Task 4: Phase 2 — flash and run the self-test

**Files:**
- Modify: `hardware/rev2026/BRINGUP-LOG.md`

**Interfaces:**
- Consumes: `firmware/micropython/bringup.py` from Task 3; Task 2's gate.
- Produces: a Pico running MicroPython, with a verified I/O set.

- [ ] **Step 1: Identify the Pico variant**

Hold BOOTSEL, plug USB. A volume named `RPI-RP2` (RP2040) or `RP2350` mounts.

```bash
cat /Volumes/RPI-RP2/INFO_UF2.TXT 2>/dev/null || cat /Volumes/RP2350/INFO_UF2.TXT
```

The `Board-ID` line names the exact board — `RPI-RP2` for a Pico/Pico W, `RP2350` for a Pico 2/Pico 2 W. This determines which UF2 to fetch.

- [ ] **Step 2: Get the MicroPython UF2**

Downloading a file needs the operator's go-ahead. Ask before fetching; or the operator downloads the matching build from `micropython.org/download/` themselves. Do not guess the variant — flashing an RP2350 build to an RP2040 leaves a Pico that does not enumerate.

- [ ] **Step 3: Flash**

```bash
cp <micropython>.uf2 /Volumes/RPI-RP2/
```

The volume unmounts and the Pico reboots into MicroPython.

- [ ] **Step 4: Find the port**

```bash
ls /dev/tty.usbmodem*
```

- [ ] **Step 5: Run the self-test**

```bash
uv run --with mpremote mpremote connect /dev/tty.usbmodemXXXX run firmware/micropython/bringup.py
```

Watch the board through the LED walk, then press ARM and PULSE when prompted. Expected final line: `=== RESULT: PASS ===`.

- [ ] **Step 6: Append to the log**

```markdown
## Phase 2 — I/O self-test

Date: YYYY-MM-DD
MicroPython build:
Port:

| Check | Expected | Observed | Pass |
|---|---|---|---|
| STATUS LED | lights alone | | |
| HV_DET LED | lights alone | | |
| CHARGE LED | lights alone | | |
| All three together | all lit | | |
| CHARGED idle level | 1 | | |
| ARM button | PASS | | |
| PULSE button | PASS | | |

Notes:
```

- [ ] **Step 7: Gate**

Any LED that does not light, or either button not registering, stops the sequence. An LED failure is cosmetic but a button failure is not: `SW3` is a different switch from `SW1`/`SW2`, but a soldering problem on one tactile switch is reason to re-check all three, and `SW3` is the discharge control.

- [ ] **Step 8: Commit**

```bash
git add hardware/rev2026/BRINGUP-LOG.md
git commit -m "Phase 2 I/O self-test on board #1"
```

---

### Task 5: `chargetest.py`

**Files:**
- Create: `firmware/micropython/chargetest.py`
- Modify: `hardware/rev2026/tests/test_bringup_firmware.py`

**Interfaces:**
- Consumes: `GPIO_TO_PAD`, `_constants`, `_int_literals`, `node_to_net` fixture, and the `CHARGETEST` path constant — all already defined in `tests/test_bringup_firmware.py` by Task 3.
- Produces: `firmware/micropython/chargetest.py` with `PIN_HVPWM = 20`, `PIN_CHARGED = 18`, `PIN_HV_DET_LED = 6`, `CHARGE_TIMEOUT_MS`, `pwm_on()`, `pwm_off()`, `main()`.

- [ ] **Step 1: Write the failing tests**

Append to `hardware/rev2026/tests/test_bringup_firmware.py`:

```python
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


def test_chargetest_has_a_charge_timeout():
    """A charge attempt must be time-bounded, per the spec's Phase 3."""
    consts = _constants(CHARGETEST)
    assert 'CHARGE_TIMEOUT_MS' in consts, 'no CHARGE_TIMEOUT_MS in chargetest.py'
    assert 0 < consts['CHARGE_TIMEOUT_MS'] <= 30000, \
        f"CHARGE_TIMEOUT_MS = {consts['CHARGE_TIMEOUT_MS']} is not a sane bound"
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd hardware/rev2026 && uv run --with pytest pytest tests/test_bringup_firmware.py -v
```

Expected: the four new tests FAIL (`chargetest.py` does not exist); the three from Task 3 still PASS.

- [ ] **Step 3: Write `firmware/micropython/chargetest.py`**

```python
# PicoEMP commanded charge test -- Phase 3
#
# The ONLY script in this set that drives GP20 (HVPWM). It charges for at
# most CHARGE_TIMEOUT_MS, reports whether CHARGED asserted, then stops the
# PWM unconditionally and waits for the operator to discharge with SW3.
#
# SAFETY: J1's centre pin carries HV_RAIL from the moment CHARGED asserts
# until discharge -- not only during a pulse. Cap it, keep the shield on,
# and hold SW3 for a second before touching anything.
#
# Run with:  mpremote connect <port> run chargetest.py

from machine import Pin, PWM
import utime

PIN_HVPWM = 20
PIN_CHARGED = 18
PIN_HV_DET_LED = 6

# Empirically tuned upstream; ~250 V on C3. Do not retune.
PWM_FREQ_HZ = 2500
PWM_DUTY_U16 = 800

CHARGE_TIMEOUT_MS = 10000
DISCHARGE_TIMEOUT_MS = 30000


def pwm_off():
    """Drive HVPWM actively low. Q3's gate then sits at GND through R5."""
    Pin(PIN_HVPWM, Pin.OUT).low()


def pwm_on():
    pwm = PWM(Pin(PIN_HVPWM))
    pwm.freq(PWM_FREQ_HZ)
    pwm.duty_u16(PWM_DUTY_U16)
    return pwm


def main():
    print('=== PicoEMP charge test (Phase 3) ===')
    print('Shield on. SMA capped. Hands clear of J1.')

    pwm_off()
    charged = Pin(PIN_CHARGED, Pin.IN)
    hv_led = Pin(PIN_HV_DET_LED, Pin.OUT)
    hv_led.off()

    if charged.value() == 0:
        print('ABORT: CHARGED already asserted before we started.')
        print('Hold SW3 for one second and re-run.')
        return

    print('Charging, up to %d ms...' % CHARGE_TIMEOUT_MS)
    start = utime.ticks_ms()
    elapsed = None
    try:
        pwm_on()
        deadline = utime.ticks_add(start, CHARGE_TIMEOUT_MS)
        while utime.ticks_diff(deadline, utime.ticks_ms()) > 0:
            if charged.value() == 0:
                elapsed = utime.ticks_diff(utime.ticks_ms(), start)
                break
            utime.sleep_ms(10)
    finally:
        pwm_off()
        print('PWM stopped.')

    if elapsed is None:
        print('=== RESULT: FAIL -- CHARGED never asserted in %d ms ==='
              % CHARGE_TIMEOUT_MS)
        print('Press SW3 anyway before touching the board.')
        return

    hv_led.on()
    print('CHARGED asserted after %d ms.' % elapsed)
    print('Now press and hold SW3 for one second to discharge.')

    start = utime.ticks_ms()
    deadline = utime.ticks_add(start, DISCHARGE_TIMEOUT_MS)
    while utime.ticks_diff(deadline, utime.ticks_ms()) > 0:
        if charged.value() == 1:
            hv_led.off()
            print('CHARGED released after %d ms.'
                  % utime.ticks_diff(utime.ticks_ms(), start))
            print('=== RESULT: PASS ===')
            return
        utime.sleep_ms(10)

    hv_led.off()
    print('=== RESULT: FAIL -- CHARGED still asserted after %d ms ==='
          % DISCHARGE_TIMEOUT_MS)
    print('The rail may still be live. Hold SW3 and do not touch J1.')


main()
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd hardware/rev2026 && uv run --with pytest pytest tests/test_bringup_firmware.py -v
```

Expected: all seven PASS. Note that `test_bringup_cannot_drive_hv` still passes — it checks `bringup.py`, which is untouched.

- [ ] **Step 5: Run the full suite**

```bash
cd hardware/rev2026 && uv run --with pytest pytest tests/
```

Expected: 66 pre-existing + 7 new, all passing.

- [ ] **Step 6: Commit**

```bash
git add firmware/micropython/chargetest.py hardware/rev2026/tests/test_bringup_firmware.py
git commit -m "Phase 3 charge test, bounded by timeout and try/finally"
```

---

### Task 6: Phase 3 — first charge

**Files:**
- Modify: `hardware/rev2026/BRINGUP-LOG.md`

**Interfaces:**
- Consumes: `firmware/micropython/chargetest.py` from Task 5; Task 4's gate.
- Produces: a board with a verified charge and discharge cycle.

- [ ] **Step 1: Physical setup**

- HV shield hot-glued over the HV section. Expect it to rock rather than sit flush — `Q2` is a known rim fouler (0.00 mm clear against 2.32 mm needed); the glue takes up the gap.
- Plastic dust cap fitted on `J1`.
- Board flat on the bench, nothing resting on it, nothing to reach over.
- USB power. Phase 1 already cleared shorts and the console is needed here.
- One hand behind your back for the whole phase.

- [ ] **Step 2: Run the charge test**

```bash
uv run --with mpremote mpremote connect /dev/tty.usbmodemXXXX run firmware/micropython/chargetest.py
```

Expected sequence: `Charging...` → `CHARGED asserted after NNNN ms.` → press SW3 → `CHARGED released after NNN ms.` → `=== RESULT: PASS ===`.

- [ ] **Step 3: Note the charge time**

A few seconds is normal. Substantially longer, or a `FAIL -- CHARGED never asserted`, points at the T1 channel (`D3`, `R4`, `C1`/`C2`, `Q3`, `T1`, `D2`) or the sense chain (`R2`, `R1`, `Q1`). Phase 0's 0.1 reading already cleared `R2`.

- [ ] **Step 4: Append to the log**

```markdown
## Phase 3 — first charge

Date: YYYY-MM-DD
Shield: hot-glued. J1: dust cap fitted.

| Check | Expected | Observed | Pass |
|---|---|---|---|
| CHARGED asserts | within 10 s | | |
| Time to assert | few seconds | | |
| SW3 releases CHARGED | yes | | |
| Time to release | < 1 s | | |

Notes:
```

- [ ] **Step 5: Gate**

If `CHARGED` never releases after SW3, the rail may still be live. Do not touch J1. Leave the board for a minute — C3 self-bleeds at τ ≈ 9.5 s — then re-measure 0.2 from Task 1 cold.

- [ ] **Step 6: Commit**

```bash
git add hardware/rev2026/BRINGUP-LOG.md
git commit -m "Phase 3 first charge on board #1"
```

---

### Task 7: Phase 4 — stock firmware

**Files:**
- Modify: `hardware/rev2026/BRINGUP-LOG.md`

**Interfaces:**
- Consumes: Task 6's gate.
- Produces: a board running the shipping firmware, ready for tip work in a later session.

- [ ] **Step 1: Install the stock firmware**

```bash
uv run --with mpremote mpremote connect /dev/tty.usbmodemXXXX fs cp firmware/micropython/cspico_simple.py :main.py
```

The verified pin map in Task 3 is exactly this firmware's map, so no edits are needed. Reset the board to start it.

- [ ] **Step 2: Confirm behaviour**

Press ARM. The CHARGE LED lights immediately; the HV LED follows after a few seconds. Press SW3 — the HV LED drops. Leave it 60 seconds and confirm the auto-disarm turns the CHARGE LED off.

**Do not press PULSE.** The SMA is open and there is no tip.

- [ ] **Step 3: Append to the log**

```markdown
## Phase 4 — stock firmware

Date: YYYY-MM-DD
Firmware: firmware/micropython/cspico_simple.py as main.py

| Check | Expected | Observed | Pass |
|---|---|---|---|
| ARM lights CHARGE LED | immediately | | |
| HV LED follows | few seconds | | |
| SW3 drops HV LED | yes | | |
| 60 s auto-disarm | CHARGE LED off | | |

PULSE not exercised -- no injection tip. See spec section 8.

Notes:
```

- [ ] **Step 4: Record what remains**

Append to the log:

```markdown
---

## Open after bring-up

- **Rail voltage unverified.** CHARGED asserting proves the sense chain
  conducts, not that the rail is 250 V. Needs an HV probe. See spec section 7.
- **No injection tip.** Suggested: Würth `744710603` inductor plus a
  `CONSMA013.062` edge-mount SMA male. See `hardware/injection_tips/README.md`.
- **Mounting holes mirrored.** MH1/MH2 sit on the opposite diagonal to the
  1551G's screw bores. Fix for the next revision is to swap MH1's and MH2's Y
  coordinates. See spec section 6. Confirm against the physical box first.
- **Q2 fouls the shield rim.** Pre-existing open layout item.
```

- [ ] **Step 5: Commit**

```bash
git add hardware/rev2026/BRINGUP-LOG.md
git commit -m "Phase 4 stock firmware on board #1; bring-up complete"
```

---

## Self-Review

**Spec coverage.** §1 goal → Tasks 1–7. §2 constraints → Global Constraints. §3 facts → Task 3's pin-map test makes the firmware claim executable; the 3V3 and SMA facts appear in Tasks 2 and 6. §4 probe points → Task 1 table. §5 Phases 0–4 → Tasks 1, 2, 3+4, 5+6, 7. §6 shield → Task 6 Step 1; root cause carried to Task 7 Step 4. §7 not-measured → Global Constraints and Task 7 Step 4. §8 out of scope → Global Constraints, enforced by `test_bringup_cannot_drive_hv` and `test_chargetest_does_not_pulse`. §9 safety rules → distributed across the phases that need them.

**Placeholders.** `YYYY-MM-DD` and the empty Measured columns are intentional — they are the forms the operator fills at the bench. `/dev/tty.usbmodemXXXX` is resolved by Task 4 Step 4. The MicroPython UF2 filename is resolved by Task 4 Steps 1–2, deliberately not guessed.

**Type consistency.** `pwm_off` is the name asserted by `test_chargetest_pwm_is_bounded` and defined in `chargetest.py`. `CHARGE_TIMEOUT_MS` matches between test and script. `GPIO_TO_PAD`, `_constants`, `_int_literals` and the `node_to_net` fixture are defined once in Task 3 and reused in Task 5. `PIN_CHARGED = 18` appears in both scripts and is checked against the netlist in both.
