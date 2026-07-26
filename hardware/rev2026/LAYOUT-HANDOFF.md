# Layout Handoff — PicoEMP Rev-2026

The schematic is complete and gated. PCB layout is interactive work that needs
you in KiCad; this is everything required to do it.

**Plan:** `docs/superpowers/plans/2026-07-25-picoemp-rev2026.md` (Tasks 10 & 11)
**Spec:** `docs/superpowers/specs/2026-07-25-picoemp-rev2026-design.md`
**Branch:** `rev2026`

---

## Where the design stands

24 commits on `rev2026`. All gates green:

| Gate | State |
|---|---|
| `kicad-cli sch erc --severity-error --exit-code-violations` | **exit 0** |
| `cd hardware/rev2026 && uv run --with pytest pytest tests/` | **49 passed**, 0 failed, 0 skipped |
| Every symbol has a resolvable footprint | yes — 47 refs, 0 broken |
| Connectivity vs. the as-received design | verified identical at every step, by net membership |

### What changed from the as-received port

- **R9's part data corrected.** It carried R4's 75 Ω MPN, DigiKey PN and value while
  being a 2 k part. This is a genuine upstream schematic bug.
- **C5's missing value** restored to 100 n.
- All Altium metadata stripped; fields normalised to `MPN` / `Manufacturer` / `DigiKey`.
- **Symbol classes corrected** — IGBT (with its co-packed antiparallel diode), enhancement
  MOSFETs, non-Schottky rectifiers, a real Darlington opto, and a transformer symbol whose
  windings match this design's actual 1,4-primary / 2,3-secondary grouping.
- **All five header footprints** moved from 1.00/1.27 mm to the correct **2.54 mm**.
- **Designators restored to upstream's scheme** — `D6/D8/D9`, `P1/P2/P3`, `J1` = SMA — so
  `BUILD-DRAWING-REV04.PDF` and the README BOM explainer apply again.
- **New trigger front-end:** `U2` 74LVC1G17 Schmitt buffer, `R14` 100 R series, `R15` 10 k
  pulldown, `C6` decoupling, `R16` 0 Ω bypass (DNP), `J4` optional SMA (DNP).
- **J3** replaced with a Phoenix `MKDS 1,5/2-5.08` (5.08 mm, 300 V) for creepage.

---

## ⚠️ Read this before you open the old board

**The as-received board's imported footprints are not trustworthy.** At least one —
`SamacSys:SOP254P952X470-6N`, the optocoupler — has pads whose rotation fuses them into
two solid copper bars. It would have shorted pins 1‑2‑3 and 4‑5‑6 together.

This matters for how you use the old board as a reference:

- **The routed copper geometry is still a valid reference** — that's what was hi-pot tested.
- **The footprint definitions are not.** Render anything you take from that file before
  believing it (`kicad-cli fp export svg`).

---

## Task 10 — Board setup and HV layout

### Step 1: Measure the reference HV clearance

The HV netclass value is **derived, not invented**. Open
`hardware/altium_src/kc/ChipShouter-Pico.kicad_pcb` and use
**Inspect → Clearance Resolution**.

These are the HV-rail net names on that board:

| Net | Extent |
|---|---|
| `NetC3_2` | 53 — the main HV node |
| `NetJ3_2` | 20 |
| `NetC3_1` | 18 |
| `NetD4_K` | 17 |
| `NetJ1_2` | 14 — SMA centre |
| `NetD5_K` | 12 |
| `NetD2_A` | 5 |

Find the three visually tightest places where HV copper approaches non-HV copper or the
board edge, measure each, and **take the minimum**. Write it down — it becomes the DRC rule.

### Step 2: Board Setup

- **Board thickness 1.6 mm — not optional.** The edge-mount SMA is specified for 0.062″
  (1.57 mm) and clamps the board edge. Get this wrong and J1 won't seat.
- 2 copper layers.
- Constraints → set **minimum clearance to 0.2 mm**. It is currently `0.0`, i.e. DRC
  enforcing nothing on a board that makes ~500 V.
- Net classes → add **`HV`** with the clearance from Step 1. Assign: the T1/T2 secondaries,
  D2, C3 both nodes, Q2's collector, J1's centre pin, R1's high side, and J3.
- Import `Edge.Cuts` from the old board — 40 × 116 mm with its slots and arcs.

### Step 3: Place and route the HV section

Update PCB from Schematic, then replicate placement and copper for
`T1, T2, C1, C2, C3, D2, D3, D4, D5, Q1, Q2, R1, R2, J3` from the old board, side by side.
This geometry is what was hi-pot tested at 1 kV.

**Match the T1/T2 pin-1 dot to `BUILD-DRAWING-REV04.PDF`.** Upstream reversed this on the
original prototype and got a wrong-polarity spike.

---

## Task 11 — Logic layout, creepage slot, DRC

### Step 4: Route the logic side

Place `U1, U2, D6, D8, D9, SW1-3, P1-P3, R5, R10-R16, C5, C6, D1, J2, MH1-3, FID1-3`.
No special constraints beyond the 0.2 mm default class.

Keep the trigger path — `P1.1 → R14 → U2 → GP0` — short and away from the HV section.

### Step 5: The J3 creepage slot

Draw a slot on `Edge.Cuts` between J3's two HV pads. **Check JLCPCB's current minimum
routed slot width first** — it's router-bit limited, typically around 1.0 mm, and the
`kicad-happy:jlcpcb` skill does not document it.

Fallback if impractical: wider pad separation plus conformal coating.

### Step 6: Gates

```bash
cd hardware/rev2026
uv run --with pytest pytest tests/ -v
```

```bash
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli pcb drc --severity-error --schematic-parity --exit-code-violations -o /tmp/drc.rpt hardware/rev2026/picoemp-rev2026.kicad_pcb
```

Both must pass before fab output.

---

## Contingencies — known things that may surface in DRC

**LDA111 pad 3 parity.** The `picoemp:LDA111` symbol has five pins (no pin 3); the
footprint has six pads, because pin 3's lead physically exists even though it's
electrically NC. Pad 3 will carry no net. If `--schematic-parity` objects, restore pin 3 to
the symbol as an `unconnected`-type pin plus a no-connect flag — which is what the original
Altium design did. **Do not delete the pad**; that would leave a lead unsoldered.

**SW3 silk-to-pad clearance is 0.05 mm.** Tight against typical fab guidance (~0.15–0.2 mm),
but it matches KiCad's own stock `TL3301NxxxxxG` precedent. If your silk DRC rule is
stricter, pull the silk notches wider rather than removing them.

**SW3 has no 3D model.** So the 3D viewer won't show its actuator. Check clearance against
the 1551B half-shell by hand: SW1/SW2 are 4.30 mm, SW3 is 5.00 mm.

**P1/P2/P3 have no MPN.** Generic 2.54 mm headers, normally bought as a strip and cut. Task
12's BOM export needs a DigiKey line for them.

---

## When layout is done

Tasks 12 and 13 are automatable again — fab outputs, the DigiKey BOM, and a full
pre-fabrication design review. Say the word and I'll run them.

**Do not order without** reviewing the gerbers in KiCad's Gerber Viewer, including the J3
slot and the drill file.
