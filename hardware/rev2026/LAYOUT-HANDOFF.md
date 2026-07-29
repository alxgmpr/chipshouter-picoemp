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
| `kicad-cli pcb drc --severity-error --schematic-parity --exit-code-violations` | **exit 0** |
| Same, **without** `--severity-error` (errors *and* warnings) | **0 violations, 0 unconnected, 0 footprint errors**, exit 0 |
| `kicad-cli sch erc --severity-error` | 0 violations |
| Routing | complete |
| Every symbol has a resolvable footprint | yes |

Board: 40.010 × 130.000 mm overall — the **body** is 40.010 × 125.000 and the
south **15.780 mm-wide SMA tab** carries the remaining 5.000 mm. 2 layers,
1.6 mm. **55 footprints** (45 SMD / 5 THT / 5 other — 3 mounting holes and the
2 HV warning marks), 245 track segments, **104 vias**, **81 zones** (80
teardrops + the `MCU GND Pour` spanning both layers). 53 schematic components,
64 nets. DNP: `R16`, plus both `REF**` HV warning marks.

**DRC warnings are now empty.** Earlier revisions said they were non-empty by
design — two cosmetic silk items and nine from the intra-HV rule. Neither is
still true: the silk was cleaned up and the intra-HV rule now passes. The
`Pad Keep Out TP7` keepouts are also gone, which is why the zone count dropped
from 83 to 81.

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
- **Intra-HV clearance.** Recorded as 0.498 mm at SW3, "the thinnest copper on
  the HV side". No longer true — the `Intra-HV spacing at full rail voltage`
  rule in the `.dru` now reports **zero** violations at its 0.8 mm target, and
  SW3 does not feature. The header comment in the `.dru` still says "As of this
  writing it reports 9 violations"; that predates the fixes that cleared them.
  Sub-0.4 mm gaps do exist between other HV nets, but those pairs sit a few
  volts apart, not 250 — `HV_SENSE` is ~1.5% below `HV_RAIL` across the
  300 k / 20 M divider, and `HV_SENSE_LED` is one opto LED drop above `HV_RTN`.
  That is exactly why the rule is scoped to the three pairs that matter.
- **SW3 clearance under the shield.** Previously unverifiable "for want of a
  3D model" — `lib/models/TL3301AF160QJ.STEP` exists and the part measures
  **4.64 mm**, clearing the 1551G's 15.05 mm cavity easily.
- **The two short Edge.Cuts slots at y 121.754–124.700.** These were the
  1551B's snap-tab pockets, not creepage features — nearest HV-netclass copper
  was 16.6 mm. Removed with the switch to the 1551G.
- **MH1/MH2's 32.000 mm spacing.** Recorded as "the dimension a shield keys
  off". It was not — it was 40.010 minus two 4.000 mm corner insets, and
  upstream REV04's fab drill has the identical pattern.

## The HV safety shield — Hammond 1551G, not the 1551B

Upstream uses the **top half of a 1551B** (50 × 25 × 15) as a see-through shield
over the HV end. This port cannot: **J3's Phoenix terminal block is 13.80 mm
tall and a 1551B half-shell gives 5.80 mm of clear height above the board.** The
creepage upgrade to the 5.08 mm Phoenix part and the shield were never checked
against each other.

The replacement is the **1551G box, inverted, lid discarded**. The larger 1551
sizes are box + lid rather than two symmetric halves, so the box is far deeper
than any half-shell. Every figure below is measured from Hammond's own STEP —
`tools/fetch_hammond_shield_model.py` re-downloads and re-axes both models, and
they are gitignored because Hammond's models are not under this project's
licence.

| | 1551B top half | **1551G box, inverted** |
|---|---|---|
| Outer | 50 × 25 × 15 | **50.000 × 35.000 × 17.000** |
| Interior clear height | 5.80 | **15.050** |
| Interior L × W | 47.4 × 21.6 | **44.73 × 29.73** |
| Screws | 2 × #2, 19.000 pitch | **2 × #4 × ½″, diagonal** |

**The screw pattern is a diagonal pair on 38.500 × 23.500 mm** — *not* the
43.88 × 28.88 the drawing appears to give. That is the outside extent of the
Ø5.00 boss recesses: 43.88 − 5.00 and 28.88 − 5.00. The box's Ø2.50 bores and
the lid's Ø3.50 through-holes both sit at (±19.25, ∓11.75), which is what
"includes 2 cover screws" meant. Shell centre on this board is
**(124.390, 145.272)**, south edge flush with the board body, so the screws want
**(112.640, 126.022)** and **(136.140, 164.522)**.

`picoemp:Shield_Hammond_1551G_Box` carries the geometry. Silk marks the north
two corners at (106.890, 120.272) and (141.890, 120.272) plus a `1551G` label —
only the north edge is ambiguous, since the south edge is flush and the width is
centred.

**The lid is not waste.** Its two Ø3.50 holes are on the same diagonal, so the
stack is screw → lid → PCB → box bore, capturing an underside cover on the same
two screws. Its inner recess is 3.05 mm against J3's 3.50 mm pin protrusion, so
trim the pins.

### Still blocking a seat

The rim contacts the board across a solid ~2 mm band (|local Y| 23.0–25.0,
|local X| 15.4–17.5) with a chamfer inboard of it. Probing every part under the
shell against the real STEP, four still foul:

- **Q2** — 0.00 mm clear at local (−8.50, +23.29), needs 2.32. About **0.4 mm
  north**, 0.6 with margin. Beware: a scripted 0.6 mm move on the development
  branch shorted `HV_OUT` to the `HV_RTN` trunk beside it, so the trunk moves in
  the same operation.
- **D3 / D4 / D5** — 0.00 mm clear at local y −23.55, need 1.10. About
  **0.6 mm south** puts them under the chamfer.

Everything else clears: **J3 by 1.20 mm** (the whole point of the 1551G),
SW3 by 10.36, Q1 by 11.32, every passive by 13–14.5. Q4 and R10 sit under the
screw-boss recesses with 0.80 and 1.55 mm.

**MH1/MH2 have not been moved yet.** MH2's target is clear (+1.054 mm); MH1's is
not — `GND` tracks sit 0.677 mm inside the hole and R10 pad 1 sits 0.206 mm
inside. Nothing routes west of that hole either: the gap to the isolation slot
is 0.425 mm and a 0.25 mm track needs 0.65. Branch `shield-1551g-board-edits`
solved the same problem on the pre-shift geometry by rotating R10 to 180° and
dropping `GND` to B.Cu past the hole, but that layout has since diverged too far
to transplant.

## Still open

- Q2 and D3/D4/D5 foul the shield rim; MH1's screw position is occupied — above.
- TL3301 **internal** standoff at ~246 V across open contacts is unverified —
  no datasheet in repo, only a STEP model.
- P1/P2/P3 have no MPN.
- J3 has no routed creepage slot; the 5.08 mm part's 2.480 mm pad separation is
  the documented fallback. Its schematic `BOM Comments` field still says "Milled
  slot between pads" — stale.

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

**Beware "Update Footprints from Library."** It has already wiped DNP
attributes on this project once (commit 3b90f5e). After running it, check that
`R16` and the two `REF**` marks are still DNP and that `Q1` still has six pads.

**SW3 now has a 3D model** — `lib/models/TL3301AF160QJ.STEP`, measuring 4.64 mm
tall, so its clearance under the shield is verified rather than assumed. The
note below is kept only for the SW1/SW2 comparison. Check
clearance against the 1551B half-shell by hand: SW1/SW2 are 4.30 mm, SW3 is
5.00 mm.

---

## Next

Tasks 12 and 13 — fab outputs, the DigiKey BOM, and a full pre-fabrication
design review.

**Do not order without** reviewing the gerbers in KiCad's Gerber Viewer,
including the drill file.
