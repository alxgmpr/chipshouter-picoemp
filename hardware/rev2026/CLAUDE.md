# PicoEMP Rev-2026 — KiCad project

A KiCad 10 port and rework of the ChipShouter-PicoEMP REV04 EM fault-injection
board. Two copper layers, 1.6 mm thick, **52 footprints** (45 SMD / 4 THT
(`J2`, `J4`, `J5`, `J6`) / 3 mounting holes), 52 schematic components across
64 nets (38 named, 26 `unconnected-*`).

The board makes ~250 V on a 0.47 µF capacitor and dumps it through an IGBT into
an injection coil. Treat every `HV_*` net as live — **except `HVPULSE` and
`HVPWM`, which are ≤4 V logic** despite the prefix and are deliberately not in
the `HV` netclass. That class is exactly `HV_RAIL`, `HV_RTN`, `HV_RECT`,
`HV_OUT`, `HV_SENSE`, `HV_SENSE_LED`, `HV_GATE`, `HV_GATE_DRV`.

---

## ⚠️ Two traps that will waste your time

**1. Designators were rewritten in commit `4b62ed2` ("Rev B").** The schematic
had been re-annotated with reset, which renumbers sequentially and destroys
correspondence with the PCB; 38 components ended up on the wrong designator. It
was repaired from footprint `(path "/uuid")` back-references. Roles that moved:

| Role | Was | Is now |
|---|---|---|
| HV calibration terminal block (Phoenix MKDSN) | `J3` | **`J4`** |
| Trigger input SMA | `J4` | **`J3`** |
| Three 2.54 mm headers | `P1` / `P2` / `P3` | **`J5`** (5-pin) + **`J6`** (7-pin) |

Any note, issue, or analysis written before 2026-08-05 uses the old names.
`J1` (HV output SMA) and `J2` (power input) did not move.

Note also that `kicad-cli pcb drc --schematic-parity` reported **0 issues
throughout**, while the design was fully scrambled. It is not a safety net for
this failure mode.

**2. All Y coordinates in older notes are 25.400 mm low.** The board sits at
y = 45.272 … 175.272 today. Anything quoting y ≈ 19.872 … 149.872 (including
earlier versions of this file) predates the shift — add 25.400. X is unchanged.
The `relayout-shifted-25mm` branch is *no longer* distinguished by this: both it
and `rev2026` now carry the same origin. It still differs substantially in
routing and is still not a merge candidate, but not for the reason older notes
give.

---

## Board outline

**40.010 × 130.000 mm overall** (x 104.390 … 144.400, y 45.272 … 175.272), but
that is not one rectangle. Three features:

- **Body**: 40.010 × 125.000, y 45.272 … **170.272**. Anything mechanical —
  enclosure fit, edge clearance — registers to the body edge at **y = 170.272**,
  not to the overall extent.
- **SMA tab**, south: projects 5.000 mm below the body, **15.780 mm wide** at
  the tip (x 116.500 … 132.280), tapering to 15.240 at the shoulder. Carries
  `J1`, the HV output.
- **USB access notch**, north: **12.000 mm wide × 13.928 mm deep**
  (x 118.390 … 130.390, y 45.272 … 59.200), open to the north edge and centred
  on x = 124.390. It clears the Pico's USB connector — `U1`'s courtyard starts
  at y = 58.897, 0.3 mm south of the notch floor.

`J2`'s courtyard (x 124.245 … 136.755) reaches 6.1 mm across the notch void.
The connector body is east of the notch wall; what overhangs is the wire-exit
envelope, so battery leads and the USB cable share the same north-end space.

---

## Where things are

Some of what you need is **outside this folder**:

| What | Path (from repo root) |
|---|---|
| Implementation plan | `docs/superpowers/plans/2026-07-25-picoemp-rev2026.md` |
| Design spec | `docs/superpowers/specs/2026-07-25-picoemp-rev2026-design.md` |
| Datasheets | `hardware/datasheets/` |
| **Upstream REV04 schematic (authoritative)** | `hardware/SCH-PICOEMP-REV04.PDF` |
| Upstream build drawing | `hardware/BUILD-DRAWING-REV04.PDF` |
| Firmware (charge voltage lives here) | `firmware/micropython/cspico_simple.py` |

⚠️ **The plan's checkboxes are all still unticked, including for work that is
finished.** Do not read `- [ ]` as "not done". Check the actual files.

⚠️ **`hardware/altium_src/kc/` is a separate, in-progress REV04 migration, not
this project.** Do not use it as a reference — its HV sense section is wired
wrong (`R1`'s lower lead lands on `HV_RTN` and `Q1` pin 1 floats, because the
Altium import flattened a wire hop into a junction). Its `audit/AUDIT.md` §4b
also states the sense chain as "HV → R1 → Q1 LED → R2 → GND"; the real order is
R2 first. When you need ground truth for topology, read the REV04 PDF.

---

## Gates

Both must pass before fab output.

```bash
cd hardware/rev2026 && uv run --with pytest pytest tests/
```

```bash
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli pcb drc --severity-error --schematic-parity --exit-code-violations -o /tmp/drc.rpt hardware/rev2026/picoemp-rev2026.kicad_pcb
```

Current state, verified **2026-08-05**: **85 tests pass**; DRC reports **0
violations, 0 unconnected, 0 schematic-parity issues**, exit code 0.

**DRC warnings are empty too.** Run the same command without `--severity-error`
and you still get zero — the `Intra-HV spacing at full rail voltage` rule passes
at its 0.8 mm target. If you see any DRC warning, you introduced it.

**ERC is not clean: 1 warning.** `unconnected_wire_endpoint` at
(318.77 mm, 236.22 mm) — a dangling 1.27 mm horizontal wire stub. Harmless but
real; it is the only thing standing between here and a clean ERC.

---

## Read `picoemp-rev2026.kicad_dru` before touching HV layout

It is the best documentation in the project. Every rule carries its reasoning,
its primary source, and a note on how it was confirmed to actually fire. Two
things from its header that will cost you time if you miss them:

- **Rule order matters.** KiCad applies the *last* matching rule. Broad rules
  first, documented exceptions at the bottom.
- **An unknown function in a condition is not an error.** It parses, reports
  nothing, and silently never matches — so the rule looks present while
  enforcing nothing. Confirm any new rule fires by temporarily setting an
  absurd constraint and checking that violations naming it appear.

The 1 mm isolation barrier is enforced by a scoped DRC rule, **not** by netclass
clearance. That is deliberate: as a plain netclass clearance it would apply
between any two HV nets and make 0603/0805 parts illegal on them. The `HV`
netclass carries 0.2 mm clearance / 0.5 mm track for that reason — it is not an
oversight.

---

## Open items

**MH1's screw head clears `R5` by 0.090 mm.** MH1 (136.140, 126.022); a #4 head
(≈2.75 mm radius) reaches to within 0.090 mm of `R5`'s nearest pad edge and
0.344 mm of `D4`'s. Measured pad-rectangle edge to hole centre, so these are
real geometry, not courtyard approximations. `R5` is the one to move. Not a DRC
violation — no rule models the screw head.

**Shield seating — three parts intrude on the rim band.** See "The HV shield"
below for the measurements. `Q2`, which older notes call the sole blocker, now
clears by 1.327 mm.

**`J5` / `J6` have no MPN.** Generic 2.54 mm headers, normally bought as a strip
and cut. The BOM export task needs a DigiKey line for them. (These are the parts
older notes call `P1`/`P2`/`P3`.)

**`J4` has no creepage slot.** The plan called for a routed slot between its two
HV pads. Not done — the 5.08 mm Phoenix MKDS part gives 2.480 mm pad-to-pad,
which is the documented fallback ("wider pad separation"). Adequate at 246 V.

**`SW3` stands off ~246 V on a switch rated 50 mA @ 12 VDC.** On the board this
is fine — its contacts are 3.100 mm apart in copper. The open question is the
TL3301's internal dielectric strength across open contacts, which is a part
spec. There is no TL3301 datasheet in the repo, only a STEP model, so this is
**unverified**. Inherited from upstream REV04, not introduced by this port.

(Its *height* is no longer in question: `lib/models/TL3301AF160QJ.STEP` gives
4.64 mm, well under the shield's 15.05 mm cavity.)

**Two conflicting revision stamps on silk.** `"PicoEMP 2026 / Alex Gompper /
Rev B 3.8.2026"` at (143.2, 99.3) and `"… Rev B 28.7.2026"` at (123.9, 89.8).
Same rev, different dates. One of them should go.

---

## Resolved — do not re-investigate

**`HV_GATE` through MH2.** Was 0.000 mm off the hole. The current routing gives
**0.452 mm** hole-edge clearance on the nearest segment
(114.925, 164.241)→(114.925, 161.939), against a 0.250 mm rule. Passes.

**MH1/MH2 on the wrong diagonal.** Fixed 2026-08-05. They are now
MH1 (136.140, 126.022) and MH2 (112.640, 164.522), which are exactly the shield
screw axes: shell centre (124.390, 145.272) ± (11.75, ∓19.25). The re-axed
Hammond model is in **KiCad's 3D-model frame, where +Y runs opposite to board
Y** — the Ø2.50 bores measure as model (−11.75, −19.25) and (+11.75, +19.25),
and mapping through the Y negation is what produces the board numbers. Placing
them from raw model coordinates puts them on the opposite diagonal, and no
rotation fixes a diagonal — only a flip, so the box would screw on from the
underside. MH3 is at (108.390, 49.272) and is unrelated to the shield.

**The two 1.27 mm longitudinal slots.** Removed 2026-08-05; the Edge.Cuts layer
now holds nothing but the outline described above. They were inherited from
REV04, where they received the 1551B top half's protruding wall lip (model
X = ±11.63, ~0.8 mm deep) and its two locating posts (±10.66, 2.5 mm deep). The
1551G box has `zmin = -1e-07` — a dead flat rim, nothing below the PCB face — so
the slots received nothing, and at centres ±14.41 mm from board centre they
matched neither shell. No copper crossed either one. Removing them also freed
the channel west of the old MH1 that had forced `R10` to (116.900, 128.800)
rot 180 with `GND` jogged onto B.Cu.

**Intra-HV clearance at `SW3` — was 0.498 mm.** The
`Intra-HV spacing at full rail voltage` rule now reports **zero** violations at
its 0.8 mm target and `SW3` does not appear at all. Note the rule's own header
comment still says "As of this writing it reports 9 violations" — that predates
the fixes that cleared them, and is worth correcting next time the `.dru` is
touched. Gaps below 0.4 mm do exist between other HV nets, but those pairs sit a
few volts apart rather than 250: `HV_SENSE` is ~1.5% below `HV_RAIL` across the
300 k / 20 M divider, and `HV_SENSE_LED` is one opto LED drop above `HV_RTN`.
That is precisely why the rule is scoped to `HV_RTN` against `HV_SENSE`,
`HV_RAIL` and `HV_OUT` and not to the class as a whole.

**Teardrops are materialized zone objects**
(`(zone ... (attr (teardrop (type padvia))))` — **197 of the board's 198
zones**; the 198th is the `MCU GND Pour`). The `(teardrops ... (enabled ...))`
block inside each pad is only the regeneration parameters. Setting `enabled no`
does not remove existing teardrop copper; the zones have to go. When an earlier
clearance question was investigated, disabling teardrops on all HV pads and vias
left the measured number unchanged — they were not the cause.

---

## The HV shield — Hammond 1551G, inverted box

Upstream shields the HV end with the **top half of a 1551B**. This port cannot:
**`J4`'s Phoenix terminal block is 13.80 mm tall and a 1551B half-shell gives
5.80 mm of clear height.** The creepage upgrade to the 5.08 mm Phoenix part and
the shield were never checked against each other.

The replacement is the **1551G box, inverted, lid discarded** — the larger 1551
sizes are box + lid, not two symmetric halves, so the box is far deeper. Outer
50.000 × 35.000 × 17.000, **interior clear height 15.050 mm**, interior
44.73 × 29.73, so the wall is **2.635 mm** thick. Shell centre
**(124.390, 145.272)**; on the board that is x 106.890 … 141.890,
y 120.272 … 170.272 — south edge flush with the board body.

**Screws are a diagonal pair on 38.500 × 23.500 mm**, not the 43.88 × 28.88 the
drawing seems to give — that is the outside extent of the Ø5.00 boss recesses.
Both the box's Ø2.50 bores and the lid's Ø3.50 holes sit at (±19.25, ∓11.75).
Two #4 × ½″ screws, so the stack **screw → lid → PCB → box bore** captures an
underside cover for free; the lid's 3.05 mm recess needs `J4`'s 3.50 mm pins
trimmed. (Note the MH footprints are `MountingHole_3.2mm_M3`, sized for M3, not
#4 — reconcile before ordering hardware.)

**Silk carries a full witness outline**, a rounded rectangle from
(107.14, 120.522) to (141.64, 170.022) with 2.75 mm corners, plus a deliberate
gap in the south edge between x = 118.2 and x = 130.6 where `J1` passes through
the wall. There is **no `1551G` text label** on the board. Older notes describing
"north two corners only, plus a label" and "a full rectangle produced 25 silk
violations" are both out of date — the full outline is present and DRC silk
checks are clean.

**Blocking a seat.** The rim contacts across the 2.635 mm wall band with a
chamfer inboard. Measured as courtyard bbox against the nominal interior
rectangle — the chamfer is *not* modelled, so intrusions under ~0.6 mm may well
clear in reality:

| Part | Side | Intrusion |
|---|---|---|
| `R6` | north | 0.912 mm |
| `C3` | south | 0.803 mm |
| `D3` / `D4` / `D5` | north | 0.257 mm each |
| `J5` | north | grazes the outer face by 0.148 mm |
| `J1` | south | full wall depth — this is the intended SMA pass-through, matching the silk gap |

Everything else clears, including `Q2` (by 1.327 mm), `J4` (1.095), `Q1`
(2.243) and `SW3` (6.717). `R6` and `C3` are the two worth moving.

Models are gitignored (Hammond's are not under this project's licence);
`tools/fetch_hammond_shield_model.py` re-downloads and re-axes both.

---

## Facts worth not re-deriving

- **Charge voltage is ~250 V**, from the firmware, not from component ratings.
  C3 is 630 V rated and Q2 650 V; those are headroom. The upstream barrier
  design rating is 400 V and the hi-pot proof test was 1 kV.
- **The isolation barrier is crossed by exactly three parts** — `T1`, `T2`
  (transformers) and `Q1` (optocoupler). Nothing on `HV_RTN` touches `GND`.
- **The HV sense chain is** `HV_RAIL → R2 (300K) → HV_SENSE → R1 (20M) →
  Q1 LED → HV_RTN`. `SW3` and **`J4`** are both in parallel across
  `HV_SENSE ↔ HV_RTN`, i.e. across `R1` + the opto LED. Pressing SW3 shunts the
  LED (dropping `CHARGED`) and discharges C3 through R2 — τ = 141 ms, peak
  833 µA. This matches the REV04 PDF exactly.
- **Everything on the board runs off `+3V3` from the Pico's own regulator**
  (`U1.36`). The `VBUS` net has exactly two nodes — `D1` and `U1.40` — and
  `VSYS` (`U1.39`) is unconnected. External power enters at `J2` (JST XH, pin 1
  `VEXT_IN`, pin 2 `GND`) through **`D1`, a series blocking diode**
  (SM4005PL-TP, 600 V / 1 A, anode to `VEXT_IN`). That diode is the entire input
  protection scheme: it gives full reverse-polarity blocking and stops USB 5 V
  backfeeding out of `J2`. There is no fuse, no TVS and no overvoltage limit,
  and because injection is on VBUS rather than VSYS, whatever is on `J2` is
  presented directly to the USB connector's VBUS pin.
- **T1 and T2 are two mirrored channels off one shared feed diode `D3`**, laid
  out symmetrically about x = 124.4. The asymmetries are intentional: T1 charges
  C3 and needs bulk (`C1 ∥ C2` = 9.4 µF behind `R4` 75 R); T2 only delivers gate
  charge (`C5` 100 n behind `R3` 10 R).
- **`Q2`'s DPAK pad spacing is 1.080 mm.** An older note in the `.dru` flagged a
  0.080 mm DRC reading as unresolved and fab-blocking; it was spurious. Measured
  directly, the geometry is 1.080 mm and fine at 250 V.
- **`R16` is the only DNP part.** Everything else is populated.
- **MH1/MH2's old 32.000 mm spacing was never a shield dimension.** It was
  40.010 minus two 4.000 mm corner insets, and upstream REV04's fab drill has
  the identical pattern. Do not treat it as keying to anything. They are on the
  shield screw axes now and that spacing no longer applies.
- **`kicad-cli pcb drc` run on a copy outside this directory reports nonsense** —
  `${KIPRJMOD}` stops resolving, so the `picoemp` footprint library goes missing
  and edge-clearance results change. Always run it in place.
- **Beware "Update Footprints from Library."** It wiped DNP attributes here once
  (commit 3b90f5e). Afterwards, check `R16` is still DNP and that `Q1`
  still has six pads.
- **Beware "Annotate Schematic" with reset.** It is what caused the Rev B
  scramble. Footprint `(path "/uuid")` back-references are the only thing that
  survives it and the only reliable way to repair it.

---

## Conventions

- Python via `uv` only (`uv run --with pytest pytest`), never bare `pip`.
- Symbols and footprints resolve as `picoemp:<name>` from `lib/` via
  `${KIPRJMOD}`. Keep project-local; do not depend on system libraries.
- BOM fields are normalised to `MPN` / `Manufacturer` / `DigiKey`.
  `tools/normalize_fields.py` sets and adds properties but does not delete them.
- `out/`, `__pycache__/` and `.pytest_cache/` are gitignored. Analysis output
  from the `kicad-happy` skills lands in `analysis/` and is regenerable — safe
  to delete, not worth committing.
