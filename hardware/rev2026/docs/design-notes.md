# Rev-2026 design notes

Why this board is built the way it is. For measured results from a real board
see [bringup.md](bringup.md); for what is still wrong see
[open-issues.md](open-issues.md).

The authoritative reference for circuit topology is the upstream
[`SCH-PICOEMP-REV04.PDF`](../../SCH-PICOEMP-REV04.PDF). Where this document and
that PDF disagree, the PDF wins.

---

## What the board is

A KiCad 10 port and rework of the ChipShouter-PicoEMP REV04. Two copper layers,
1.6 mm thick, 52 footprints (45 SMD, 4 through-hole, 3 mounting holes),
52 schematic components across 64 nets.

It charges a 0.47 µF capacitor to roughly 250 V and dumps it through an IGBT
into an injection coil.

**Treat every `HV_*` net as live — except `HVPULSE` and `HVPWM`, which are ≤4 V
logic** despite the prefix, and are deliberately excluded from the `HV`
netclass. That class is exactly `HV_RAIL`, `HV_RTN`, `HV_RECT`, `HV_OUT`,
`HV_SENSE`, `HV_SENSE_LED`, `HV_GATE`, `HV_GATE_DRV`.

---

## Changes from upstream REV04

**Two genuine upstream bugs fixed:**

- **`R9` carried `R4`'s part data** — 75 Ω MPN, DigiKey PN and value on a part
  that is actually 2 k.
- **`C5` had no value.** Restored to 100 n.

**Corrections to the port itself:**

- All Altium metadata stripped; BOM fields normalised to `MPN` / `Manufacturer`
  / `DigiKey`.
- **Symbol classes corrected** — IGBT with its co-packed antiparallel diode,
  enhancement MOSFETs, non-Schottky rectifiers, a real Darlington opto, and a
  transformer symbol whose windings match this design's actual 1,4-primary /
  2,3-secondary grouping.
- **All header footprints moved from 1.00/1.27 mm to the correct 2.54 mm.**

**New in Rev-2026:**

- **A buffered trigger front-end** — `U2` 74LVC1G17 Schmitt buffer, `R14` 100 R
  series, `R15` 10 k pulldown, `C6` decoupling, `R16` 0 Ω bypass (DNP), and an
  optional SMA input at `J3`.
- **`J4` upgraded to a Phoenix `MKDSN 1,5/2-5,08`** — 5.08 mm pitch, for
  creepage across the HV calibration tap.
- **A different HV shield.** See below.

---

## The 1 mm isolation barrier

The value is **upstream's own design rule**, annotated on the REV04 schematic:

> `ISOLATION BARRIER, 400V MIN.  >1MM CLEARANCE PER 61010-1.`

Corroborated by measurement: pad geometry on the hi-pot-validated original board
gives ~1.002 mm across the barrier in routed copper.

Voltages, from primary sources — component ratings are headroom, not operating
points:

| | |
|---|---|
| HV capacitor charge | **~250 V**, from `firmware/micropython/cspico_simple.py` |
| Measured rail on board #1 | **~261 V** (loaded divider — see bringup.md) |
| Upstream barrier design rating | 400 V min |
| Hi-pot proof test | 1 kV |

**The barrier is enforced as a scoped DRC rule, not as netclass clearance.**
This is deliberate and easy to get wrong. As a plain netclass clearance, 1 mm
applies between any two nets touching the class, which makes 0603 parts
(0.70 mm between their own pads) and 0805 parts (0.80 mm) illegal on HV nets.
The `HV` class therefore carries 0.2 mm clearance / 0.5 mm track, and
[`picoemp-rev2026.kicad_dru`](../picoemp-rev2026.kicad_dru) scopes the barrier
correctly as HV-to-non-HV.

**Known exception:** `T1`'s own primary↔secondary pad spacing is 0.770 mm, below
the rule. That is the ATB3225 package's geometry, not a routing choice, and
upstream accepted it. Targeted exceptions for `T1` and `T2` are in the `.dru`.

**Exactly three parts cross the barrier** — `T1`, `T2` (transformers) and `Q1`
(optocoupler). Nothing on `HV_RTN` touches `GND`.

### Intra-HV spacing

A separate rule, `Intra-HV spacing at full rail voltage`, targets 0.8 mm and
reports **zero** violations.

Gaps below 0.4 mm do exist between other HV nets, but those pairs sit a few
volts apart rather than 250: `HV_SENSE` is ~1.5% below `HV_RAIL` across the
300 k / 20 M divider, and `HV_SENSE_LED` is one opto LED drop above `HV_RTN`.
That is why the rule is scoped to `HV_RTN` against `HV_SENSE`, `HV_RAIL` and
`HV_OUT`, and not to the class as a whole.

**Read the `.dru` before touching HV layout.** Every rule carries its reasoning,
its primary source, and a note on how it was confirmed to actually fire. Two
things from its header:

- **Rule order matters.** KiCad applies the *last* matching rule. Broad rules
  first, documented exceptions at the bottom.
- **An unknown function in a condition is not an error.** It parses, reports
  nothing, and silently never matches — so the rule looks present while
  enforcing nothing. Confirm any new rule fires by temporarily setting an absurd
  constraint and checking that violations naming it appear.

---

## Circuit topology worth knowing

**The HV sense chain is** `HV_RAIL → R2 (300K) → HV_SENSE → R1 (20M) → Q1 LED →
HV_RTN`.

`SW3` and `J4` are both in parallel across `HV_SENSE ↔ HV_RTN`, i.e. across `R1`
plus the opto LED. Pressing `SW3` shunts the LED — dropping `CHARGED` — and
discharges C3 through R2, with τ = 141 ms and a peak of 833 µA.

**`T1` and `T2` are two mirrored channels off one shared feed diode `D3`**, laid
out symmetrically about x = 124.4. The asymmetries are intentional: `T1` charges
C3 and needs bulk (`C1 ∥ C2` = 9.4 µF behind `R4` 75 R); `T2` only delivers gate
charge (`C5` 100 n behind `R3` 10 R).

**Everything runs off `+3V3` from the Pico's own regulator** (`U1.36`). `VBUS`
has exactly two nodes — `D1` and `U1.40` — and `VSYS` (`U1.39`) is unconnected.

**Input protection is one diode.** External power enters at `J2` (JST XH, pin 1
`VEXT_IN`, pin 2 `GND`) through `D1`, a series blocking SM4005PL-TP
(600 V / 1 A, anode to `VEXT_IN`). It gives full reverse-polarity blocking and
stops USB 5 V backfeeding out of `J2`. There is **no fuse, no TVS and no
overvoltage limit**, and because injection is on VBUS rather than VSYS, whatever
is on `J2` is presented directly to the USB connector's VBUS pin.

`R16` is the only DNP part. Everything else is populated.

---

## Board outline

**40.010 × 130.000 mm overall** (x 104.390 … 144.400, y 45.272 … 175.272), but
that is not one rectangle:

- **Body**: 40.010 × 125.000, y 45.272 … **170.272**. Anything mechanical —
  enclosure fit, edge clearance — registers to the body edge at y = 170.272, not
  to the overall extent.
- **SMA tab**, south: projects 5.000 mm below the body, 15.780 mm wide at the tip
  (x 116.500 … 132.280), tapering to 15.240 at the shoulder. Carries `J1`, the
  HV output.
- **USB access notch**, north: 12.000 mm wide × 13.928 mm deep
  (x 118.390 … 130.390, y 45.272 … 59.200), open to the north edge and centred on
  x = 124.390. It clears the Pico's USB connector — `U1`'s courtyard starts at
  y = 58.897, 0.3 mm south of the notch floor.

`J2`'s courtyard (x 124.245 … 136.755) reaches 6.1 mm across the notch void. The
connector body is east of the notch wall; what overhangs is the wire-exit
envelope, so battery leads and the USB cable share the same north-end space.

---

## The HV shield — Hammond 1551G, inverted

Upstream shields the HV end with the **top half of a 1551B**. This port cannot:
**`J4`'s Phoenix terminal block is 13.80 mm tall and a 1551B half-shell gives
5.80 mm of clear height.** The creepage upgrade to the 5.08 mm Phoenix part and
the shield were never checked against each other upstream.

The replacement is the **1551G box, inverted, lid discarded**. The larger 1551
sizes are box + lid rather than two symmetric halves, so the box is far deeper
than any half-shell.

| | 1551B top half | **1551G box, inverted** |
|---|---|---|
| Outer | 50 × 25 × 15 | **50.000 × 35.000 × 17.000** |
| Interior clear height | 5.80 | **15.050** |
| Interior L × W | 47.4 × 21.6 | **44.73 × 29.73** |
| Screws | 2 × #2, 19.000 pitch | **2 × #4 × ½″, diagonal** |

Wall thickness is 2.635 mm. Shell centre is **(124.390, 145.272)**; on the board
that is x 106.890 … 141.890, y 120.272 … 170.272, south edge flush with the board
body.

**The screw pattern is a diagonal pair on 38.500 × 23.500 mm** — *not* the
43.88 × 28.88 the drawing appears to give, which is the outside extent of the
Ø5.00 boss recesses. Both the box's Ø2.50 bores and the lid's Ø3.50 holes sit at
(±19.25, ∓11.75).

**The lid is not waste.** Its holes are on the same diagonal, so the stack
screw → lid → PCB → box bore captures an underside cover on the same two screws.
Its 3.05 mm recess needs `J4`'s 3.50 mm pins trimmed.

> **Mounting-hole trap.** The re-axed Hammond model is in KiCad's 3D-model frame,
> where +Y runs opposite to board Y. The bores measure as model (−11.75, −19.25)
> and (+11.75, +19.25); mapping through the Y negation is what produces the board
> coordinates MH1 (136.140, 126.022) and MH2 (112.640, 164.522). Placing them
> from raw model coordinates puts them on the opposite diagonal, and **no
> rotation fixes a diagonal** — only a flip, so the box would screw on from the
> underside. MH3 (108.390, 49.272) is unrelated to the shield.
>
> The MH footprints are `MountingHole_3.2mm_M3`, sized for M3, not #4. Reconcile
> before ordering hardware.

Silk carries a full witness outline: a rounded rectangle from (107.14, 120.522)
to (141.64, 170.022) with 2.75 mm corners, plus a deliberate gap in the south
edge between x = 118.2 and x = 130.6 where `J1` passes through the wall.

Hammond's 3D models are gitignored — they are not under this project's licence.
[`tools/fetch_hammond_shield_model.py`](../tools/fetch_hammond_shield_model.py)
re-downloads and re-axes both.

---

## Cautions

**Do not trust the as-received board's imported footprints.** At least one —
`SamacSys:SOP254P952X470-6N`, the optocoupler — has pads whose rotation fuses
them into two solid copper bars, shorting pins 1-2-3 and 4-5-6 together. The
*routed copper geometry* on that board is still a valid reference, because that
is what was hi-pot tested. The *footprint definitions* are not. Render anything
you take from it before believing it (`kicad-cli fp export svg`).

**`T1`/`T2` pin-1 dot must match `BUILD-DRAWING-REV04.PDF`.** Upstream reversed
this on the original prototype and got a wrong-polarity spike.

**Keep the trigger path short** — `J6.1 → R14 → U2 → GP0` — and away from the HV
section.

**Beware "Update Footprints from Library."** It wiped DNP attributes on this
project once (commit `3b90f5e`). Afterwards, check that `R16` is still DNP and
that `Q1` still has six pads.

**Beware "Annotate Schematic" with reset.** It renumbers sequentially and
destroys correspondence with the PCB — it once put 38 components on the wrong
designator here. Footprint `(path "/uuid")` back-references are the only thing
that survives it and the only reliable way to repair it. Note that
`kicad-cli pcb drc --schematic-parity` reported 0 issues throughout that
episode; it is not a safety net for this failure mode.

**Teardrops are materialized zone objects** — `(zone ... (attr (teardrop ...)))`,
197 of the board's 198 zones. The `(teardrops ... (enabled ...))` block inside
each pad is only the regeneration parameters; setting `enabled no` does not
remove existing teardrop copper.

**`kicad-cli pcb drc` run on a copy outside this directory reports nonsense** —
`${KIPRJMOD}` stops resolving, the `picoemp` footprint library goes missing, and
edge-clearance results change. Always run it in place.

---

## Settled — don't re-derive these

- **`Q2`'s DPAK pad spacing is 1.080 mm.** An older note flagged a 0.080 mm DRC
  reading as fab-blocking; it was spurious.
- **`LDA111` pad 3 parity.** The symbol has five pins and the footprint six pads,
  because pin 3's lead physically exists while being electrically NC. Do not
  delete the pad — that would leave a lead unsoldered.
- **`SW3`'s height is not a problem.** `lib/models/TL3301AF160QJ.STEP` gives
  4.64 mm against the shield's 15.05 mm cavity.
- **`HV_GATE` through MH2** clears by 0.452 mm against a 0.250 mm rule.
- **MH1/MH2's old 32.000 mm spacing was never a shield dimension.** It was
  40.010 minus two 4.000 mm corner insets; upstream REV04's fab drill has the
  identical pattern.
- **The two 1.27 mm longitudinal slots are gone.** They were inherited from
  REV04, where they received the 1551B top half's wall lip and locating posts.
  The 1551G has a dead flat rim, so they received nothing, and their centres
  matched neither shell. No copper crossed either one.
