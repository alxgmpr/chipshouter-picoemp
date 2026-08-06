# Rev-2026 Bring-Up Log — Board #1

Plan: `docs/superpowers/plans/2026-08-05-picoemp-rev2026-bringup.md`
Spec: `docs/superpowers/specs/2026-08-05-picoemp-rev2026-bringup-design.md`

Equipment: DMM; bench PSU with current limit. No scope, no HV probe.

---

## ⚠️ Designators below are board #1's, and rev B moved several

This log is a record of what was measured on the first assembled board. The
readings and conclusions stand. **The reference designators do not** — rev B
re-designated things, so a designator here may name a different part on a
later board.

**Follow this log by what each part is, not by what it is called.**

| What it is | Board #1 | Rev B |
|---|---|---|
| HV terminal block, the `HV_RTN` / `HV_SENSE` tap | `J3` | **`J4`** |
| Trigger input SMA | `J4` | **`J3`** |
| 7-pin header: `TRIG_IN`, `GP1`–`GP5`, `GND` | `P1` | **`J6`** |
| 2-pin header: `GND`, `HVPULSE` | `P2` | folded into the 5-pin |
| 4-pin header: `CHARGED`, `+3V3`, `GND`, `HVPWM` | `P3` | folded into the 5-pin |
| 5-pin header: `+3V3`, `CHARGED`, `HVPULSE`, `HVPWM`, `GND` | — | **`J5`** |

The HV output SMA, the JST power input, all three switches and the Pico keep
their designators.

**One functional change, not just a rename.** The arm switch now pulls its net
to `GND`; on board #1 it pulled up to `+3V3`. Both switches are now
pull-to-ground, which is why `firmware/micropython/bringup.py` configures both
with `PULL_UP` and treats a press as a low reading.

**Consequence: the current `bringup.py` will fail the ARM button check on
board #1.** With an internal pull-up on a pin that board #1's arm switch drives
to `+3V3`, the pin reads high whether or not the button is pressed, so the
press is never seen. That script now targets rev B. Board #1 needs the arm
switch read as `PULL_DOWN`, active high.

Everything electrical in the fault-injection path is unchanged — the charge
loop, the sense chain, the isolation barrier and the discharge path are the
same circuit.

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

Rail voltage measured in Phase 4 — see below.

---

## Phase 4 — stock firmware

Date: 2026-08-05
Firmware: `firmware/micropython/cspico_simple.py` copied to `:main.py`

| Check | Expected | Observed | Pass |
|---|---|---|---|
| ARM lights CHARGE LED | immediately | yes | ✅ |
| HV LED follows | ~2 s | yes | ✅ |
| SW3 drops HV LED | yes | yes | ✅ |
| 60 s auto-disarm | CHARGE LED off | yes | ✅ |

PULSE not exercised — no injection tip. See spec section 8.

**The upstream CHARGED defect did not manifest on this board.** Stock firmware
configures GP18 only and leaves GP26's pull-down on the net, but the HV LED
behaved correctly throughout — no spurious assert at rest, no flicker. This
supports the earlier claim that upstream "mostly works" despite the defect,
which had been asserted without observation. One board, one session; not a
strong result, but it is now an observation rather than a guess.

### Rail voltage — approximately 261 V

Measured with the DMM across J3, i.e. `HV_SENSE` to `HV_RTN`: **250 V** while
charged, decaying after auto-disarm.

That reading is loaded. The DMM's 10 MΩ input sits in parallel with R1 plus
the opto LED, so it is not a direct rail measurement:

```
HV_RAIL --[R2 300k]-- HV_SENSE --+--[R1 20M]--[LED]-- HV_RTN
                                 +--[DMM 10M]--------/
```

Solving the node at 250 V with the LED at ~1.2 V:

| Branch | Current |
|---|---|
| through R1 + LED | (250 − 1.2) / 20 M = 12.4 µA |
| through the DMM | 250 / 10 M = 25.0 µA |
| total through R2 | 37.4 µA → 11.2 V across R2 |

**V_rail ≈ 261 V.** This corroborates the ~250 V figure that previously came
only from the firmware's empirically tuned duty cycle, and leaves comfortable
headroom against C3's 630 V and Q2's 650 V.

**Assumption: 10 MΩ DMM input impedance.** The result is sensitive to it — the
same 250 V reading at 1 MΩ input would imply a 329 V rail. Confirm the meter's
spec before treating 261 V as settled.

The observed decay after auto-disarm is consistent: the DMM shortens the bleed
path from 20.3 MΩ to ~6.97 MΩ, so τ falls from 9.5 s to 3.3 s.

This measurement is repeatable and is now the documented way to check the rail
without an HV probe.

---

## Bring-up complete

All five phases pass. The board charges to roughly 261 V in ~2.1 s, asserts
CHARGED, and discharges on SW3. Stock firmware is installed as `main.py`.

## Open after bring-up

- **Rail voltage is approximate, not qualified.** 261 V is derived from a
  loaded divider measurement with an assumed 10 MΩ meter input, not read
  directly. A proper HV probe would settle it.
- **No injection tip, so pulsing has never been exercised.** Suggested parts:
  Würth `744710603` inductor plus a `CONSMA013.062` edge-mount SMA male. See
  `hardware/injection_tips/README.md`.
- **Mounting holes mirrored.** MH1/MH2 sit on the opposite diagonal to the
  1551G's screw bores; the shield is Kapton-taped rather than screwed. The
  proposed fix is to swap MH1's and MH2's Y coordinates — but see the next
  item before editing anything.
- **The shield seats flush, contradicting the layout record.** `CLAUDE.md` and
  `LAYOUT-HANDOFF.md` both state Q2 fouls the shield rim with 0.00 mm clear
  against 2.32 mm needed, and call it the last open item before the shield
  sits flat. It sits flat on the physical board. Either that note is stale or
  the fabbed board differs from the working copy — which is itself on the
  `+25.4 mm` shifted layout rather than the `rev2026` geometry. Establish
  which revision was actually fabbed before touching MH1/MH2.
- **Phase 1's 0.87 mA draw was never explained**, and the cross-check with
  MicroPython running was not taken.
- **Upstream `cspico_simple.py` has the CHARGED two-pad defect** described
  above. Not fixed here; did not manifest on this board.
- **The trigger front-end has never been exercised.** U2, R14, R15 and the
  input SMA went on the board in this port and no phase touched them. No
  firmware in the repo reads GP0 either — `bringup.py`, `chargetest.py` and
  `cspico_simple.py` all ignore it. Phase 5 below is written but not run.

---

## Phase 5 — trigger front-end

Date: **not yet run.** Everything below is the procedure and its expected
values; the Measured and Pass columns are blank on purpose.

Script: `firmware/micropython/trigtest.py`

The chain, from the netlist:

```
J3 SMA centre ──┬── TRIG_IN ── R14 100R ──┬── U2.2 (A) ──> U2.4 (Y) ── GP0 (U1.1)
J6.1 header ────┘        net "TRIG_BUF" ──┴── R15 10k ── GND

U2 = 74LVC1G17 Schmitt buffer, SOT-23-5, on +3V3 with C6 100n
R16 = 0R bypass across the buffer, DNP — must stay unfitted
```

Two naming traps. **`TRIG_BUF` is the buffer's input node, not its output** —
the output net is plain `GP0`. And `GP0` is not on any header, so the only
places to probe it are U2 pin 4 and the Pico's pin 1.

**Board #1 designators.** This is rev B naming. On board #1 the trigger SMA is
`J4`, and the 7-pin header is `P1` — so the loopback jumper described below is
`P1.1 ↔ P1.2` there, not `J6.1 ↔ J6.2`. `trigtest.py` prints the rev B names.

### 5.0 — cold checks

Unpowered. Confirm U2, R14, R15 and C6 are actually populated first, and that
R16 is not.

| # | Measurement | Expected | Measured | Pass |
|---|---|---|---|---|
| 5.0.1 | J3 centre → J6.1, probed at the far end of a mated cable | 0 Ω | | |
| 5.0.2 | J3 centre → U2.2 | 100 Ω (R14) | | |
| 5.0.3 | U2.2 → GND | 10 kΩ (R15) | | |
| 5.0.4 | J3 centre → GND | 10.1 kΩ | | |
| 5.0.5 | J3 shell → GND | 0 Ω | | |
| 5.0.6 | U2.5 → Pico 3V3 | 0 Ω | | |
| 5.0.7 | U2.3 → GND | 0 Ω | | |
| 5.0.8 | U2.5 → GND | not a short | | |
| 5.0.9 | U2.2 → Pico pin 1 | open — **not** 0 Ω | | |

5.0.1 through the mated cable rather than the pad, because the edge-launch
SMA's centre-pin joint is the thing most likely to be bad. 5.0.9 catches R16
fitted, which would put the unbuffered node straight onto GP0.

### 5.1 — powered, static

USB power, nothing connected to the trigger.

| # | Measurement | Expected | Measured | Pass |
|---|---|---|---|---|
| 5.1.1 | U2.2 at rest | 0 V (R15 pulls it down) | | |
| 5.1.2 | U2.4 at rest | 0 V | | |
| 5.1.3 | U2.2 with TRIG_IN jumpered to J5.1 (+3V3) | 3.3 V | | |
| 5.1.4 | U2.4, same | 3.3 V | | |
| 5.1.5 | both, jumper removed | back to 0 V | | |

### 5.2 — threshold and hysteresis

Bench PSU into `TRIG_IN`, current limit 10 mA, swept slowly 0 → 2 V and back
while watching U2.4 with the DMM. Datasheet numbers are the VCC = 3.0 V column
of the Nexperia 74LVC1G17, rev 16.1; the rail here is 3.3 V, so the real trip
points sit a little above these.

| # | Measurement | Expected | Measured | Pass |
|---|---|---|---|---|
| 5.2.1 | Rising trip point (V_T+) | 1.29 – 1.71 V | | |
| 5.2.2 | Falling trip point (V_T−) | 0.88 – 1.24 V | | |
| 5.2.3 | Gap between them (V_H) | 0.31 – 0.64 V | | |

Two distinct trip points is the point of the measurement — it is what
distinguishes a real Schmitt part from a plain buffer fitted by mistake.
Input leakage is ≤ 1 µA, so R14 drops nothing and the applied voltage is the
node voltage.

### 5.3 — firmware

```
mpremote connect <port> run trigtest.py
```

Needs one jumper, `J6.1 ↔ J6.2` (`P1.1 ↔ P1.2` on board #1), and **nothing
else on TRIG_IN or the SMA** — GP1 would be fighting it. The script drives its
own trigger through the whole chain and checks GP0 follows, so it is
self-checking rather than operator-judged.

| Check | Expected | Observed | Pass |
|---|---|---|---|
| `IDLE` | PASS — GP0 low and steady, trigger open | | |
| `DC` | PASS — GP0 follows 0/1/0 | | |
| `EDGES` | PASS — 50 sent, 50 counted | | |
| `NARROW 100/10/1 us, back-to-back` | PASS on all four | | |
| `RESULT` | PASS | | |

Then remove the jumper. The script's `WATCH` phase mirrors GP0 onto the STATUS
LED for 15 s and counts rising edges, which is how the SMA gets tested — the
jumper cannot reach it.

It cannot make high voltage: GP20 and GP14 are never referenced, enforced by
`tests/test_bringup_firmware.py::test_cannot_drive_hv`.

### 5.4 — before plugging a pulse generator into the SMA

**There is no 50 Ω on this input.** R15 is a 10 k pulldown, not a terminator.
A generator whose amplitude is calibrated into 50 Ω delivers twice that into
an open end, so a 5 V setting arrives at the buffer as ~10 V — against a
5.5 V tolerant input with a 6.5 V absolute maximum. Set the generator to
high-Z, or fit a 50 Ω feedthrough terminator at the board, or measure the
amplitude at the SMA before connecting it.

The same reflection is why long unterminated coax with fast edges can produce
extra counted edges. The Schmitt's 0.3 – 0.6 V of hysteresis absorbs small
overshoot, not a 2 V reflection.

`J3`'s shell is board `GND`, so the coax bonds the target's ground to the
PicoEMP's low-voltage ground and hence to USB. It does not touch the HV
isolation barrier, but it is a ground loop with whatever is being glitched.

Propagation delay through U2 is 3.0 ns typ / 5.5 ns max at 3.0 – 3.6 V —
below what a logic analyser resolves, and far below the RP2040's response.
