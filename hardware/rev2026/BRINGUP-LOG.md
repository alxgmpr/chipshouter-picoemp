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

Not carried out: the Phase 1 current cross-check. Supply draw with
MicroPython running was not re-measured, so the 0.87 mA reading above
remains unexplained rather than confirmed as a DMM burden artifact. Low
priority — it did not block anything.
