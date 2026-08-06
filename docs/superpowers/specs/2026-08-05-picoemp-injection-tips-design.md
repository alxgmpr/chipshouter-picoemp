# PicoEMP Injection Tips and Fault Detector — Design Spec

**Date:** 2026-08-05
**Status:** Approved
**Follows:** `2026-08-05-picoemp-rev2026-bringup-design.md`
**Board:** Rev-2026 #1, bring-up complete — ~261 V rail, 2.1 s charge, verified charge/discharge

---

## 1. Goal

Build a small set of EM injection tips and prove which of them actually produce
a usable field, using a target that doubles as the detector.

Pulsing has never been exercised on this board — there has been no tip. This
spec covers the first pulse.

## 2. The constraint that shapes everything

**No oscilloscope.** A tip that produces no useful field is indistinguishable
from one that works: the board charges, the pulse fires, and nothing observable
happens either way. Tip-building without a detector is unfalsifiable, and the
whole point of making several tips is to compare them.

The resolution is a target that reports on itself. A spare Pico runs a
deterministic self-checking loop and counts its own corruptions. A wrong answer
is unambiguous proof the tip did something.

## 3. Decisions

| Question | Decision |
|---|---|
| Scope | Tips + free-running target. No trigger, no delay sweep. |
| Detector | The target itself — self-checking loop, fault counter over serial |
| Timing | Manual pulse. See §5. |
| Tip count | 3–4, chosen to span a range rather than to be individually optimal |
| Rigid connector | Taoglas `EMPCB.SMAMST.A` |
| Cable connector | Linx `CONSMA007` — bought, but not built first |
| Standoff | Tip resting on the target package |
| Target firmware | MicroPython |

## 4. Why no trigger

The trigger front-end (`J4` → `R14`/`R15` → `U2` Schmitt → GP0) is the only
genuinely new circuitry in this revision and remains untested. Exercising it is
worth doing — but not here.

The target loops **continuously**, so a randomly-timed pulse always lands
somewhere inside the sensitive window. MicroPython's interpreted execution
makes that window milliseconds wide. Aiming in time is what you need to
characterise a target — to find *which* instruction is vulnerable — not to
answer "does this tip produce a field."

Adding triggering now would mean debugging tip geometry, trigger timing and
delay sweep simultaneously, with no known-good reference for any of them. It
also requires the C firmware, and therefore the Pico SDK and a CMake build.

Triggering is the right destination. It is the wrong next step.

## 5. Tip set

**Buy 3–4 cheap inductors and let the fault counter rank them.** Ferrite
inductors cost under $2; the SMA connectors dominate the bill. With a working
detector, empirical ranking is cheaper and more reliable than prediction.

Selection criteria, in priority order:

1. **Unshielded or open-core construction.** A shielded inductor exists to
   contain its field, which is precisely backwards for a tip. Würth's WE-TIS
   series is explicitly shielded. The repo's `744779068` example works because
   its ferrite cover was removed. Filter on unshielded or open-drum parts.
2. **Core diameter spanning a range** — roughly 6–8 mm for a coarse,
   high-energy tip and 3–4 mm for something more spatially selective.
3. **Low inductance.** Induced voltage in the target follows dB/dt. For a fixed
   core the field is roughly independent of turn count — B ∝ N·I and
   I = V·√(C/L) ∝ 1/N, so the two cancel — and what changes with fewer turns is
   *speed*. Lower L discharges faster and couples harder. Favour the low-µH end.

**No part numbers are specified here.** The repo README's `744710603` does not
appear in Würth's current catalogue, and the README predates 2025. Resolving
real MPNs against live distributor stock belongs in the implementation plan,
not baked into a spec.

### Connectors

`EMPCB.SMAMST.A` (SMA plug, male, board edge, end launch) at $3.83/1 and
$3.26/10, against Linx `CONSMA013.062` at $5.85 for the same function. The
inductor solders to a scrap of PCB carrying the connector, keeping loop area
small.

**Verify board thickness from the datasheet before ordering.** End-launch SMAs
have a fixed slot; the Linx part's `.062` suffix denotes 0.062 in (1.57 mm),
but the Taoglas listing does not state one. Standard scrap FR4 is 1.6 mm and
this is very likely fine, but a mismatched slot means the PCB scrap will not
seat.

`CONSMA007` ($2.35, male plug, crimps to RG-174) is worth owning for a
pigtailed probe when a target needs reaching into. Not built first — a Pico on
a bench needs no reach. When it is built, the fault counter measures what the
cable costs, as a lower fault rate at identical geometry.

## 6. Target and detector

A **spare** Pico — distinct from the PicoEMP's own — running MicroPython.

Required behaviour:

- A deterministic self-checking computation (nested counters reaching a known
  product), repeated forever.
- A running count of results that did not match.
- A heartbeat line carrying a monotonic sequence number.
- Output over USB serial.

Two distinguishable signals:

| Observation | Meaning |
|---|---|
| Mismatch count increments | Data fault — the computation was corrupted |
| Sequence number restarts at zero | The target reset or crashed |

Both count as the tip having done something.

## 7. The control

**Before pulsing, run the target with the PicoEMP charged but not pulsing, for
at least as long as the intended test run. Expect zero faults.**

Without this baseline a fault count is unattributable. MicroPython on a
breadboard can produce anomalies unaided, and a nonzero baseline means the
experiment is measuring the setup rather than the tip.

If the baseline is nonzero, fix that before continuing. Comparing tips against
a noisy floor produces rankings that are not real.

## 8. Standoff

Rest the tip on the target package.

Optimum standoff is approximately R/√2, where R is probe radius (Gaine et al.,
cited in `hardware/injection_tips/README.md`) — about 1 mm for a 3 mm core.
Package height above the die already sits in that range, so contact is both
near-optimal and exactly repeatable. **Repeatability matters more than
optimality when the goal is comparing tips**, since position variation between
trials would swamp the difference being measured.

**Insulate the tip face with Kapton.** With a coil fitted, the coil is a DC
short from `HV_RAIL` to `HV_OUT`, so the SMA shell and the whole tip body sit
at essentially the full rail relative to `HV_RTN`. That is isolated from earth
and will not shock through the target, but it is 261 V of floating metal and
must not rest on exposed target pins.

## 9. Success criteria

| # | Criterion |
|---|---|
| 1 | Baseline run produces zero faults |
| 2 | At least one tip produces a repeatable, nonzero fault count |
| 3 | Tips are ranked by faults per pulse at fixed position |

Criterion 2 is the real gate — it is the first evidence this board can inject a
fault at all. Criterion 3 is what justifies having built more than one tip.

## 10. Safety

1. The pulse is a strong EM transient at close range. It can reset or corrupt
   **the PicoEMP's own Pico**, and disturb USB on both boards. Keep the host
   and both USB cables away from the tip.
2. Expect the target to crash. Flash corruption is a plausible outcome of
   glitching a board — use a spare, not one that matters.
3. All Phase 3 rules from the bring-up spec still apply: shield in place, SW3
   before contact, hands clear of J1.

## 11. Out of scope

- **Triggered injection and delay sweeps.** See §4. The natural follow-on, and
  the point at which the trigger front-end finally gets exercised.
- **Hand-wound and shaped-ferrite tips.** Sub-millimetre probes need a shaped
  core; no shaping capability is available. Off-the-shelf inductors only.
- **Rail voltage qualification.** Still approximate — 261 V derived from a
  loaded divider measurement. Unchanged by this work.
