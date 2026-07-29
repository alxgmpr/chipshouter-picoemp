# Layout Record — PicoEMP Rev-2026

**Status: layout is done.** Board routed, DRC clean, both gates green. This
file records what was built and why. It was previously a set of instructions
for work not yet started; those instructions have been carried out and are kept
below only where the reasoning still matters.

For orientation in a fresh session, read `CLAUDE.md` in this directory first.

**Plan:** `docs/superpowers/plans/2026-07-25-picoemp-rev2026.md`
**Spec:** `docs/superpowers/specs/2026-07-25-picoemp-rev2026-design.md`
**Branch:** `rev2026`

---

## Verified state — 2026-07-28

| Gate | Result |
|---|---|
| `uv run --with pytest pytest tests/` | **66 passed**, 0 failed, 0 skipped |
| `kicad-cli pcb drc --severity-error --schematic-parity --exit-code-violations` | **0 errors, 0 unconnected, 0 parity issues**, exit 0 |
| Routing | complete |
| Every symbol has a resolvable footprint | yes |

Board: 40.01 × 130.00 mm, 2 layers, 1.6 mm, 55 footprints (45 SMD / 5 THT),
104 vias. 83 zones — 80 teardrops, 2 `Pad Keep Out TP7` keepouts, and the
`MCU GND Pour` spanning both layers. 53 schematic components, 64 nets, 1 DNP
(`R16`).

DRC warnings are non-empty by design — see `CLAUDE.md`.

---

## What changed from the as-received port

- **R9's part data corrected.** It carried R4's 75 Ω MPN, DigiKey PN and value
  while being a 2 k part. A genuine upstream schematic bug.
- **C5's missing value** restored to 100 n.
- All Altium metadata stripped; fields normalised to `MPN` / `Manufacturer` /
  `DigiKey`.
- **Symbol classes corrected** — IGBT (with its co-packed antiparallel diode),
  enhancement MOSFETs, non-Schottky rectifiers, a real Darlington opto, and a
  transformer symbol whose windings match this design's actual 1,4-primary /
  2,3-secondary grouping.
- **All five header footprints** moved from 1.00/1.27 mm to the correct 2.54 mm.
- **Designators restored to upstream's scheme** — `D6/D8/D9`, `P1/P2/P3`,
  `J1` = SMA — so `BUILD-DRAWING-REV04.PDF` and the README BOM explainer apply.
- **New trigger front-end:** `U2` 74LVC1G17 Schmitt buffer, `R14` 100 R series,
  `R15` 10 k pulldown, `C6` decoupling, `R16` 0 Ω bypass (DNP), `J4` optional
  SMA (populated).
- **J3** replaced with a Phoenix `MKDS 1,5/2-5.08` (5.08 mm, 300 V) for creepage.

---

## The 1 mm isolation barrier — how it was implemented

The value is **upstream's own design rule**, annotated on
`SCH-PICOEMP-REV04.PDF`:

> `ISOLATION BARRIER, 400V MIN.  >1MM CLEARANCE PER 61010-1.`

Corroborated by measurement — pad geometry on the hi-pot-validated original
board gives ~1.002 mm across the barrier in routed copper.

**Voltages, from primary sources** (component ratings are headroom, not
operating points):

| | |
|---|---|
| HV capacitor charge | **~250 V** — `firmware/micropython/cspico_simple.py` |
| Upstream barrier design rating | **400 V min** |
| Hi-pot proof test | 1 kV, "well beyond the voltages the device can generate" |

It is enforced as a **scoped DRC rule**, not as netclass clearance. An earlier
draft of this document instructed adding the 1 mm figure to the `HV` netclass;
that turned out to be wrong. As a plain netclass clearance it applies between
any two nets touching the class, which makes 0603 (0.70 mm between its own
pads) and 0805 (0.80 mm) parts illegal on HV nets. The `HV` class therefore
carries 0.2 mm clearance / 0.5 mm track, and `picoemp-rev2026.kicad_dru` scopes
the barrier correctly as HV-to-non-HV. Read that file before changing anything
here.

**Known exception:** T1's own primary↔secondary pad spacing is 0.770 mm, below
this rule. That is the ATB3225 package's geometry, not a routing choice, and
upstream accepted it. Targeted exceptions for T1 and T2 are in the `.dru`.

---

## Resolved — items that were open in the previous draft

- **`Q2` DPAK pad spacing.** Flagged as fab-blocking on a DRC reading of
  0.080 mm that could not be reconciled with geometry computing to 1.08 mm.
  Measured directly: **1.080 mm**. The reading was spurious; the footprint is
  fine at 250 V.
- **`LDA111` pad 3 parity.** The symbol has five pins, the footprint six pads,
  because pin 3's lead physically exists while being electrically NC.
  `--schematic-parity` now reports 0 issues. The pad was not deleted — doing so
  would leave a lead unsoldered.
- **Board setup.** Minimum clearance is 0.2 mm (was 0.0). Thickness 1.6 mm, as
  required by the edge-mount SMA which clamps the board edge and is specified
  for 0.062″.

## Still open

Carried in `CLAUDE.md` under "Open items", in short:

- Intra-HV clearance at SW3 is 0.498 mm — IPC-compliant, but the thinnest
  copper on the HV side. Not teardrop-related.
- TL3301 internal standoff at ~246 V is unverified — no datasheet in repo.
- P1/P2/P3 have no MPN.
- J3 has no routed creepage slot; the 5.08 mm part's 2.480 mm pad separation is
  the documented fallback.

---

## ⚠️ Still true: do not trust the old board's footprints

**The as-received board's imported footprints are not trustworthy.** At least
one — `SamacSys:SOP254P952X470-6N`, the optocoupler — has pads whose rotation
fuses them into two solid copper bars. It would have shorted pins 1‑2‑3 and
4‑5‑6 together.

- **The routed copper geometry is still a valid reference** — that is what was
  hi-pot tested.
- **The footprint definitions are not.** Render anything you take from that file
  before believing it (`kicad-cli fp export svg`).

Related: `hardware/altium_src/kc/` is a *different* in-progress REV04 migration
and its HV sense section is miswired. See `CLAUDE.md`.

---

## Other notes that remain relevant

**T1/T2 pin-1 dot must match `BUILD-DRAWING-REV04.PDF`.** Upstream reversed this
on the original prototype and got a wrong-polarity spike.

**Keep the trigger path short** — `P1.1 → R14 → U2 → GP0` — and away from the HV
section.

**SW3 silk-to-pad clearance is 0.05 mm.** Tight against typical fab guidance
(~0.15–0.2 mm), but it matches KiCad's own stock `TL3301NxxxxxG` precedent. If
your silk DRC rule is stricter, pull the silk notches wider rather than removing
them. This is the source of the two standing `silk_over_copper` warnings.

**SW3 has no 3D model**, so the 3D viewer won't show its actuator. Check
clearance against the 1551B half-shell by hand: SW1/SW2 are 4.30 mm, SW3 is
5.00 mm.

---

## Next

Tasks 12 and 13 — fab outputs, the DigiKey BOM, and a full pre-fabrication
design review.

**Do not order without** reviewing the gerbers in KiCad's Gerber Viewer,
including the drill file.
