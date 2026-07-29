# PicoEMP Rev-2026 — KiCad project

A KiCad 10 port and rework of the ChipShouter-PicoEMP REV04 EM fault-injection
board. Two copper layers, 1.6 mm thick, **53 footprints** (45 SMD / 5 THT /
3 other — the mounting holes), 53 schematic components across 64 nets.

**40.010 × 130.000 mm overall**, but that is not one rectangle: the **body** is
40.010 × 125.000 and a **15.780 mm-wide SMA tab** projects 5.000 mm south of it.
Anything mechanical — enclosure fit, edge clearance — registers to the body edge
at y = 144.872, not to the overall extent.

The board makes ~250 V on a 0.47 µF capacitor and dumps it through an IGBT into
an injection coil. Treat every `HV_*` net as live — **except `HVPULSE` and
`HVPWM`, which are ≤4 V logic** despite the prefix and are deliberately not in
the `HV` netclass. That class is exactly `HV_RAIL`, `HV_RTN`, `HV_RECT`,
`HV_OUT`, `HV_SENSE`, `HV_SENSE_LED`, `HV_GATE`, `HV_GATE_DRV`.

Branch: `rev2026`. **A second, incompatible board exists on branch
`relayout-shifted-25mm`** — the whole layout translated +25.400 mm in Y with 21
footprints moved, two HV warning marks and ~150 tracks different. It is not
mergeable with this one; see "The HV shield" below.

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

Current state, verified 2026-07-28: **66 tests pass**; DRC reports **0
violations, 0 unconnected, 0 schematic-parity issues**, exit code 0. ERC clean.

**Warnings are empty too.** Run the same command without `--severity-error` and
you still get zero — the `Intra-HV spacing at full rail voltage` rule passes at
its 0.8 mm target, and the two cosmetic silk items older revisions mention are
gone. If you see any warning, you introduced it.

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

**The HV shield does not seat yet — Q2 only.** It has 0.00 mm clear at local
(−8.50, +23.29) against the 2.32 mm it needs, so about 0.4 mm north (0.6 with
margin), moving the `HV_RTN` trunk beside it in the same operation — a scripted
move without that shorted `HV_OUT` to `HV_RTN`. D3/D4/D5 used to foul as well
and no longer do. This is the last thing between here and a shield that sits
flat.

**MH1/MH2 are on the shield screw axes** — (112.640, 100.622) and
(136.140, 139.122). They used to sit at the HV-end corners, which the box covers,
making them unreachable. Getting MH1 there needed R10 moved to
(116.900, 103.400) rot 180 with `GND` jogged onto B.Cu past the hole, because
nothing routes west of that hole: 0.425 mm to the isolation slot against the
0.65 mm a 0.25 mm track needs. Nearest copper to MH1 is now +2.210 mm from the
hole edge.

**~~Intra-HV clearance at SW3 — 0.498 mm.~~ Resolved.** The
`Intra-HV spacing at full rail voltage` rule now reports **zero** violations at
its 0.8 mm target and SW3 does not appear at all. Note the rule's own header
comment still says "As of this writing it reports 9 violations" — that predates
the fixes that cleared them, and is worth correcting next time the `.dru` is
touched. Gaps below 0.4 mm do exist between other HV nets, but those pairs sit a
few volts apart rather than 250: `HV_SENSE` is ~1.5% below `HV_RAIL` across the
300 k / 20 M divider, and `HV_SENSE_LED` is one opto LED drop above `HV_RTN`.
That is precisely why the rule is scoped to `HV_RTN` against `HV_SENSE`,
`HV_RAIL` and `HV_OUT` and not to the class as a whole.

**Teardrops are materialized zone objects**
(`(zone ... (attr (teardrop (type padvia))))` — 77 of the board's 78 zones; the
78th is the `MCU GND Pour`). The `(teardrops ... (enabled ...))` block inside
each pad is only the regeneration parameters. Setting `enabled no` does not
remove existing teardrop copper; the zones have to go. When an earlier
clearance question was investigated, disabling teardrops on all 33 HV pads and
vias left the measured number unchanged — they were not the cause.

**SW3 stands off ~246 V on a switch rated 50 mA @ 12 VDC.** On the board this is
fine — its contacts are 3.100 mm apart in copper. The open question is the
TL3301's internal dielectric strength across open contacts, which is a part
spec. There is no TL3301 datasheet in the repo, only a STEP model, so this is
**unverified**. Inherited from upstream REV04, not introduced by this port.

(Its *height* is no longer in question: `lib/models/TL3301AF160QJ.STEP` gives
4.64 mm, well under the shield's 15.05 mm cavity.)

---

## The HV shield — Hammond 1551G, inverted box

Upstream shields the HV end with the **top half of a 1551B**. This port cannot:
**J3's Phoenix terminal block is 13.80 mm tall and a 1551B half-shell gives
5.80 mm of clear height.** The creepage upgrade to the 5.08 mm Phoenix part and
the shield were never checked against each other.

The replacement is the **1551G box, inverted, lid discarded** — the larger 1551
sizes are box + lid, not two symmetric halves, so the box is far deeper. Outer
50.000 × 35.000 × 17.000, **interior clear height 15.050 mm**, interior
44.73 × 29.73. Shell centre (124.390, 119.872), south edge flush with the board
body.

**Screws are a diagonal pair on 38.500 × 23.500 mm**, not the 43.88 × 28.88 the
drawing seems to give — that is the outside extent of the Ø5.00 boss recesses.
Both the box's Ø2.50 bores and the lid's Ø3.50 holes sit at (±19.25, ∓11.75).
Two #4 × ½″ screws, so the stack **screw → lid → PCB → box bore** captures an
underside cover for free; the lid's 3.05 mm recess needs J3's 3.50 mm pins
trimmed.

Silk marks the **north** two corners only, (106.890, 94.872) and
(141.890, 94.872), plus a `1551G` label — the south edge is flush and the
width is centred, so the north edge is the only ambiguous dimension. A full
witness rectangle was tried and produced 25 silk violations against the
HIGH VOLTAGE legend, the HV warning marks and the D3/D4/D5 designators.

**Blocking a seat:** the rim contacts across a solid ~2 mm band with a chamfer
inboard. **Q2 is the only part still fouling** — 0.00 mm clear at local
(−8.50, +23.29) against 2.32 needed. D3/D4/D5 were the other offenders and were
moved +1.5 mm south, now clearing by 12.75 mm. Everything else clears too:
J3 by 1.20 mm, SW3 by 10.36, Q1 by 11.32.

Models are gitignored (Hammond's are not under this project's licence);
`tools/fetch_hammond_shield_model.py` re-downloads and re-axes both.

---

## Open items, continued

**P1/P2/P3 have no MPN.** Generic 2.54 mm headers, normally bought as a strip
and cut. The BOM export task needs a DigiKey line for them.

**J3 has no creepage slot.** The plan called for a routed slot between its two
HV pads. Not done — the 5.08 mm Phoenix MKDS part gives 2.480 mm pad-to-pad,
which is the documented fallback ("wider pad separation"). Adequate at 246 V.

---

## Facts worth not re-deriving

- **Charge voltage is ~250 V**, from the firmware, not from component ratings.
  C3 is 630 V rated and Q2 650 V; those are headroom. The upstream barrier
  design rating is 400 V and the hi-pot proof test was 1 kV.
- **The isolation barrier is crossed by exactly three parts** — `T1`, `T2`
  (transformers) and `Q1` (optocoupler). Nothing on `HV_RTN` touches `GND`.
- **The HV sense chain is** `HV_RAIL → R2 (300K) → HV_SENSE → R1 (20M) →
  Q1 LED → HV_RTN`. `SW3` and `J3` are both in parallel across
  `HV_SENSE ↔ HV_RTN`, i.e. across `R1` + the opto LED. Pressing SW3 shunts the
  LED (dropping `CHARGED`) and discharges C3 through R2 — τ = 141 ms, peak
  833 µA. This matches the REV04 PDF exactly.
- **T1 and T2 are two mirrored channels off one shared feed diode `D3`**, laid
  out symmetrically about x = 124.4. The asymmetries are intentional: T1 charges
  C3 and needs bulk (`C1 ∥ C2` = 9.4 µF behind `R4` 75 R); T2 only delivers gate
  charge (`C5` 100 n behind `R3` 10 R).
- **`Q2`'s DPAK pad spacing is 1.080 mm.** An older note in the `.dru` flagged a
  0.080 mm DRC reading as unresolved and fab-blocking; it was spurious. Measured
  directly, the geometry is 1.080 mm and fine at 250 V.
- **`R16` is the only DNP part.** `J4` is populated despite older notes saying
  otherwise.
- **MH1/MH2's 32.000 mm spacing was never a shield dimension.** It is 40.010
  minus two 4.000 mm corner insets, and upstream REV04's fab drill has the
  identical pattern. Do not treat it as keying to anything.
- **`kicad-cli pcb drc` run on a copy outside this directory reports nonsense** —
  `${KIPRJMOD}` stops resolving, so the `picoemp` footprint library goes missing
  and edge-clearance results change. Always run it in place.
- **Beware "Update Footprints from Library."** It wiped DNP attributes here once
  (commit 3b90f5e). Afterwards, check `R16` is still DNP and that `Q1`
  still has six pads.

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
