# PicoEMP Rev-2026 — First-Article Bring-Up Spec

**Date:** 2026-08-05
**Status:** Approved
**Subject:** First assembled Rev-2026 board, serial #1
**Board branch:** `rev2026`

---

## 1. Goal

Take one hand-assembled Rev-2026 board from "just soldered" to "verified able to
charge and discharge its high-voltage rail," without ever putting the operator
or the board at risk of a fault that a cheaper test would have caught first.

Pulse output is explicitly **out of scope**. No injection tip exists yet, and an
open SMA is the wrong load for a first pulse. See §8.

## 2. Constraints

| Constraint | Value |
|---|---|
| Test equipment | DMM; bench PSU with adjustable current limit |
| No oscilloscope | Rail voltage is **inferred**, never measured (§7) |
| No HV probe | Same |
| Injection tip | None available |
| HV shield | Hot-glued in place — see §6 |

## 3. Established facts

These were verified against the netlist and board file, not assumed.

**Stock firmware runs unmodified.** Every GPIO in `cspico_simple.py` and
`firmware/c/` matches this board:

| Net | Pico pin | GPIO | Firmware |
|---|---|---|---|
| `ARM_SW` | 34 | GP28 | `Pin(28)` |
| `PULSE_SW` | 15 | GP11 | `Pin(11)` |
| `CHARGED` | 24, 31 | GP18, GP26/ADC0 | `Pin(18)` |
| `CHARGE_LED` | 32 | GP27 | `Pin(27)` |
| `HV_DET_LED` | 9 | GP6 | `Pin(6)` |
| `STATUS_LED` | 10 | GP7 | `Pin(7)` |
| `HVPULSE` | 19 | GP14 | `pulse_out_pin = 14` |
| `HVPWM` | 26 | GP20 | `Pin(20)` |
| `GP0` (trigger in) | 1 | GP0 | C fw `fast_trigger` |

**HV charging draws from the Pico's own 3V3 regulator**, not VBUS:
`+3V3 → D3 → R4 (75 R) / R3 (10 R) → T1 / T2 primaries`. USB alone powers the
whole board, and 3V3-rail current is therefore a direct charging indicator.

**An unprogrammed Pico cannot charge.** GPIOs default high-Z; `R5` and `R10`
pull Q3's and Q4's gates to `GND`. HV-off is the passive state.

**`SW3` is the discharge control.** It shorts `HV_SENSE ↔ HV_RTN`, shunting R1
and the opto LED and leaving `R2` (300 k) across C3 — τ = 141 ms, peak 833 µA.
Unattended, C3 also self-bleeds through R2 + R1 + opto at τ ≈ 9.5 s, down to the
opto LED knee.

**The SMA carries the rail continuously while charged.** `J1` pad 1 (centre pin)
is on `HV_RAIL`; pads 2 (shell tabs) are on `HV_OUT`. The centre pin sits at
approximately the full rail relative to the shell from the moment `CHARGED`
asserts until discharge — not only during a pulse. J1 is outside the shield by
design.

## 4. Probe points

The 2.54 mm headers make every signal reachable without clipping to fine-pitch
parts.

| Signal | Location |
|---|---|
| `GND` | P3.3, P2.1, P1.7, J2.2 |
| `+3V3` | P3.2 |
| `CHARGED` | P3.1 |
| `HVPWM` | P3.4 |
| `HVPULSE` | P2.2 |
| `TRIG_IN` | P1.1, J4 centre |
| `HV_RTN` | J3.1 |
| `HV_SENSE` | J3.2 |
| `HV_RAIL` | J1 centre pin |
| `HV_OUT` | J1 shell |

`J2` is an S2B-XH-A (JST XH, 2.50 mm): pin 1 = `VEXT_IN`, pin 2 = `GND`.

## 5. Phases

Each phase gates the next. A failure stops the sequence.

### Phase 0 — cold checks

Nothing powered. On the first run the board has never been energized, so C3
cannot hold charge. If Phase 0 is repeated after Phase 3, hold `SW3` for one
second first.

| # | Measurement | Expect | Meaning of failure |
|---|---|---|---|
| 0.1 | J1 centre → J3.2 | 300 kΩ ±5 % | `R2` missing or bad — no fast discharge path |
| 0.2 | **Hold SW3**, J1 centre → J3.1 | 300 kΩ ±5 % | `SW3` not closing — no manual discharge |
| 0.3 | Any GND → J3.1 | open (> 20 MΩ) | Isolation barrier breached |
| 0.4 | J1 centre → J1 shell | not a short | IGBT `Q2` shorted C-to-E |
| 0.5 | P3.2 → GND | not a short | 3V3 rail fault |
| 0.6 | J2.1 → GND | not a short | Input rail fault |

0.1 and 0.2 together validate the complete discharge loop **before anything can
charge**. This is the single highest-value phase.

One reading to expect but not to trust: `J3.2 → J3.1` with SW3 **released**
runs through R1 plus the opto LED. A DMM's ohms source is typically under 1 V
and will not forward-bias the LED, so it reads open rather than 20 MΩ. That is
normal and is why 0.2 holds SW3 instead.

### Phase 1 — first power, current-limited, no firmware

Bench PSU **5.0 V, limit 100 mA**, into J2. USB unplugged. Pico unprogrammed.

- PSU must not enter current limit.
- `+3V3` at P3.2 reads 3.3 V ±5 %.

Pass criterion: rail up, no current limit. This is the assembly-short screen; it
is the only phase where current limiting is load-bearing.

### Phase 2 — bring-up firmware over USB

Flash MicroPython, then a purpose-written bring-up script — **not** stock
firmware.

The script's defining property: **it never configures GP20.** `HVPWM` stays
high-Z, so charging is impossible for as long as it runs. There is no command,
no code path, and no button that can make high voltage in Phase 2.

It must:
- drive `STATUS_LED`, `HV_DET_LED` and `CHARGE_LED` individually on command
- report `ARM_SW`, `PULSE_SW` and `CHARGED` state
- print over USB serial, drivable through the serial MCP tools

Pass criterion: all three LEDs light on command; both buttons read correctly;
`CHARGED` reads its idle state.

### Phase 3 — first charge

Shield glued down. Plastic dust cap on J1. USB power (Phase 1 already cleared
shorts, and the console is needed here).

Add a **time-limited, explicitly commanded** charge routine to the script:
enable HVPWM at the tuned 2500 Hz / 1.22 % duty, with a hard timeout.

Expected sequence:
1. 3V3-rail current steps up.
2. After a few seconds, `CHARGED` asserts and the HV LED lights.
3. Stop PWM.
4. Press `SW3`. `CHARGED` de-asserts.

Pass criterion: charge asserts, and discharge drops it. Hands clear of J1 for
the whole phase.

### Phase 4 — stock firmware

`cspico_simple.py` as `main.py`, or the C firmware for its serial console.
Confirm ARM and the HV LED behave as in Phase 3. **Still no pulsing.**

## 6. HV shield

The 1551G box seats only from the underside: the board's `MH1`/`MH2` pattern is
the mirror of the box's screw diagonal.

For this article the box is **hot-glued** over the HV section. This is accepted
as adequate for Phases 3–4 — the box is captive, the operator's hands stay clear
of it, and J1 (the actual exposed hazard) is outside the shield either way.

Expect the box to rock rather than sit flush: `Q2` is a known rim fouler
(0.00 mm clear against 2.32 mm needed) and was the last open layout item. Glue
takes up the gap.

**Root cause, for the next revision.** The re-axed `Hammond_1551G_Box.step`
places its two Ø2.50 bores at (−11.75, −19.25) and (+11.75, +19.25) from shell
centre — exactly where MH1/MH2 sit. But KiCad negates Y when placing a 3D model
at a footprint, so model-frame Y runs opposite to board-frame Y. Positions read
off the model and used directly as board coordinates come out mirrored, which
flips a diagonal pair onto the other diagonal.

Fix: **swap MH1's and MH2's Y coordinates.** They already sit at shell-centre
∓19.25, so the swap mirrors the pair without moving anything else. To be
confirmed against the physical box before the file is edited. Not part of this
bring-up.

## 7. What is not being measured

With no HV probe, rail voltage is never read directly. `CHARGED` asserting means
enough voltage to drive the sense chain's opto through R2 + R1 — it does **not**
confirm ~250 V. The firmware's tuned duty cycle is the only basis for that
figure.

Consequence: Phase 3 proves the charge and discharge *mechanisms* work. It does
not qualify the rail voltage. Anything depending on a known rail — pulse energy,
repeatability — waits for a probe.

## 8. Out of scope

**Pulsing.** With no tip the SMA is an open circuit, so a pulse dumps nothing
and leaves the rail standing on an exposed centre pin. Pulse bring-up needs a
tip or dummy load and is a separate session.

Suggested tip parts, per `hardware/injection_tips/README.md`: Würth `744710603`
ferrite-core inductor plus a `CONSMA013.062` edge-mount SMA male.

## 9. Safety rules for every phase

1. `SW3` for one second before touching the board, whenever it has been armed.
2. Never touch J1. Keep a plastic dust cap fitted from Phase 3 on.
3. Shield stays glued down from Phase 3 on.
4. One hand behind your back while any phase can charge — no path across the
   chest.
