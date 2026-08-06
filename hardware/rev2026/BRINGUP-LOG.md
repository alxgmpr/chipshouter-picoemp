# Rev-2026 Bring-Up Log — Board #1

Plan: `docs/superpowers/plans/2026-08-05-picoemp-rev2026-bringup.md`
Spec: `docs/superpowers/specs/2026-08-05-picoemp-rev2026-bringup-design.md`

Equipment: DMM; bench PSU with current limit. No scope, no HV probe.

---

## Phase 0 — cold checks

Date: 2026-08-05

Board had not been energized before these readings were taken.

| # | Measurement | Expected | Measured | Pass |
|---|---|---|---|---|
| 0.1 | J1 centre → J3.2 | 300 kΩ ±5 % | 299.5 kΩ | ✅ |
| 0.2 | Hold SW3, J1 centre → J3.1 | 300 kΩ ±5 % | 273 kΩ / 299.3 kΩ reversed (see note) | ✅ |
| 0.3 | GND (USB shell) → J3.1 | open > 20 MΩ | OL | ✅ |
| 0.4 | J1 centre → J1 shell | not a short | OL | ✅ |
| 0.5 | Pico 3V3(OUT) → GND | not a short | 36 kΩ | ✅ |
| 0.6 | J2.1 → J2.2 | not a short | 2.2 MΩ | ✅ |

### Note on 0.2 — 273 kΩ rather than 300 kΩ

`R2` is confirmed good by 0.1 at 299.5 kΩ, and SW3 is confirmed closing by
0.2 reading a finite value at all rather than OL. The 27 kΩ shortfall is a
second conduction path between the probe points, not a component fault:

```
J3.1 (HV_RTN) → T1 secondary (T1.3→T1.2) → HV_RECT → D2 anode→cathode → HV_RAIL (J1 centre)
```

`D2.1` is the cathode on `HV_RAIL` and `D2.2` the anode on `HV_RECT`, so this
path forward-biases when the DMM's **red** lead sits on J3.1, putting a
weakly-conducting diode branch in parallel with R2. Solving 273 ∥ 299.5 puts
that branch at ~3.0 MΩ, consistent with a silicon diode at sub-µA DMM test
current.

0.1 is unaffected because `HV_SENSE` never touches `HV_RTN`, so no D2 path
exists for that measurement — which is why it reads clean.

Reversed-polarity confirmation: **299.3 kΩ**, within 0.2 kΩ of 0.1's 299.5 kΩ.
D2 blocks in this direction and R2 is the only path, as predicted. Resolved.

**Practical consequence:** future resistance measurements between `HV_RAIL` and
`HV_RTN` must put the red lead on `HV_RAIL` (J1 centre). The other polarity
reads low through T1's secondary and D2 and does not indicate a fault.

Notes: Board had not been energized before these readings.

---

## Phase 1 — first power

Date: 2026-08-05
PSU: 5.0 V into J2. USB unplugged. Pico unprogrammed.

The PSU's current-limit function was unavailable (constant-voltage only), so
the DMM was used in series on its mA range instead — a direct current reading,
with the mA-jack fuse as the limit. Voltage was then read in a second pass with
the DMM back on volts.

| Reading | Expected | Measured | Pass |
|---|---|---|---|
| Supply current | < 100 mA, no limit | 0.87 mA | ✅ |
| Pico 3V3(OUT) → GND | 3.3 V ±5 % | 3.285 V (−0.45 %) | ✅ |

### Note on the 0.87 mA

Lower than an unprogrammed Pico normally idles at — the RP2040 bootrom's USB
device mode runs the core and usually draws tens of mA. The likely cause is
DMM burden voltage: on a low autoranged mA scale the shunt resistance drops
the input enough that the RP2040 never starts, and a core that isn't running
keeps the current low, which keeps the DMM on the low range.

Not a concern for what Phase 1 tests. Sub-mA draw with the 3V3 rail up means
no leakage path anywhere, which is the stronger version of the result we
wanted. Cross-check in Phase 2: with MicroPython flashed, draw should rise to
tens of mA. If it does not, revisit this.

---

## Phase 2 — I/O self-test

Date: 2026-08-05
MicroPython: v1.28.0, build `RPI_PICO`, `Raspberry Pi Pico with RP2040`
UF2: `RPI_PICO-20260406-v1.28.0.uf2`, familyID `0xe48bff56` (RP2040), header verified before flashing
Port: `/dev/tty.usbmodem212201`
Script: `firmware/micropython/bringup.py`

| Check | Expected | Observed | Pass |
|---|---|---|---|
| STATUS LED | lights alone | lit | ✅ |
| HV_DET LED | lights alone | lit | ✅ |
| CHARGE LED | lights alone | lit | ✅ |
| All three together | all lit | all lit | ✅ |
| CHARGED idle level | 1 | 1 | ✅ |
| ARM button | PASS | PASS | ✅ |
| PULSE button | PASS | PASS | ✅ |

The script's own `RESULT: PASS` covers only the two button presses — it
cannot sense the LEDs. The four LED rows above are operator-confirmed.

`U1` is `SC0915`, a plain Pico, so the non-W `RPI_PICO` build is correct.
Two other `/dev/tty.usbmodem*` ports on this host belong to an unrelated
device and do not respond to mpremote.

### Firmware defect found at the start of Phase 3 — CHARGED misread

`chargetest.py` aborted with "CHARGED already asserted" on its first run,
having read the same pin as 1 in Phase 2 twenty minutes earlier with nothing
electrical changed in between.

**No high voltage was involved.** Measured through ADC0, the `CHARGED` net sat
at a steady 3.20 V for 20 s including an SW3 press. A charged rail would have
had the LDA111 sinking current and holding the net near 0, and SW3 would have
produced a visible step. Neither happened.

Root cause: the RP2040 resets every GPIO pad with its pull-down enabled
(`PADS_BANK0` reset value `0x56`, bit 2 `PDE=1`), and `CHARGED` reaches **two**
pads — GP18 (U1.24) and GP26/ADC0 (U1.31). Both scripts configured only GP18,
leaving GP26's ~65 kΩ pull-down on the net. Two pull-downs in parallel against
R6's 22 kΩ pull-up divide the net to roughly 2 V, inside the RP2040's
indeterminate band (VIL 0.99 V, VIH 2.31 V). The digital read was arbitrary.

Diagnostic evidence — the level flipped on the exact line that reconfigured
GP26:

```
Pin(18, IN)             = 1
Pin(18, IN, PULL_DOWN)  = 0
Pin(18, IN, None)       = 0
-- configuring ADC0 on GP26 --
GP26 net voltage        = 2.767 V  -> settles 3.20 V
Pin(18, IN, None) now   = 1
```

Fix: configure both pads. `ADC(26)` disables that pad's digital pull, leaving
R6 as the only pull-up. `chargetest.py` now also reads `CHARGED` as a voltage
rather than a logic level, and refuses to charge if the net sits between 1.0
and 2.9 V rather than guessing. Verified on the board: 3.20–3.22 V steady,
GP18 = 1 on every sample.

**Upstream `cspico_simple.py` has the same defect** — `Signal(Pin(18, Pin.IN),
invert=True)` with GP26 never touched. It mostly works because a genuinely
charged rail pulls the net hard to near 0 V, which reads correctly; the failure
mode is a spurious "charged" at rest, which is what was seen here. Not fixed —
this port does not modify upstream firmware.

Not carried out: the Phase 1 current cross-check. Supply draw with
MicroPython running was not re-measured, so the 0.87 mA reading above
remains unexplained rather than confirmed as a DMM burden artifact. Low
priority — it did not block anything.

---

## Phase 3 — first charge

Date: 2026-08-05
Shield: Kapton-taped, **sits flush** (see open items). J1: dust cap fitted.
Power: USB. Script: `firmware/micropython/chargetest.py`

Three consecutive runs:

| Run | At rest | Time to assert | Result |
|---|---|---|---|
| 1 | 3.21 V | 2165 ms | PASS |
| 2 | 3.21 V | 2110 ms | PASS |
| 3 | 3.19 V | 2101 ms | PASS |

| Check | Expected | Observed | Pass |
|---|---|---|---|
| CHARGED asserts | within 10 s | 2.1 s | ✅ |
| Repeatability | — | 2101–2165 ms, 3 % spread | ✅ |
| SW3 releases CHARGED | yes | yes, all three runs | ✅ |

**What these numbers do and do not mean.** The charge time and its
repeatability are real: the T1 channel charges consistently, not marginally.

The "asserted at 0.99 V" the script prints is tautological — the poll loop
exits the moment the net crosses `CHARGED_MAX_V = 1.0`, so it reports the
threshold, not a measurement. Worth changing to sample after a short settle
if that number is ever wanted.

The discharge times (5899 / 3046 / 1101 ms) are dominated by operator reaction
time between the prompt and pressing SW3. τ is 141 ms, so the circuit's share
of each is small. These are not a measurement of discharge speed, and the
downward trend across runs is the operator getting quicker.

Rail voltage remains unverified — see "Open after bring-up".
