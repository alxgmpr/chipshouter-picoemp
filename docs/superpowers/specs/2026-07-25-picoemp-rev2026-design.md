# PicoEMP Rev-2026 — Design Spec

**Date:** 2026-07-25
**Status:** Approved
**Base:** NewAE ChipShouter-PicoEMP REV04

---

## 1. Goal

Produce a correct, buildable, 2026-sourceable KiCad revision of the PicoEMP. The
existing KiCad port is mid-migration and not fabricable: 20 duplicated footprints,
a netlist split between legacy Altium and new KiCad names with all copper on the
legacy side, five header footprints at the wrong pitch, and 26 unregistered
libraries. See `hardware/altium_src/kc/audit/AUDIT.md` for the full assessment.

This revision keeps the validated analog design and fixes everything around it.

## 2. Decisions

| Question | Decision |
|---|---|
| Scope | Modernize + targeted fixes |
| Layout | Fresh layout, replicating HV section geometry |
| Build route | **Full hand build. Bare PCB from JLC, no PCBA.** |
| Quantity | ~5 prototypes, personal use |
| Sourcing | **DigiKey** |
| J3 HV tap | Keep, wider pitch + milled creepage slot |
| Pico mount | SMD castellated reflow (hand-soldered) |
| Trigger I/O | Protect + Schmitt buffer, header + DNP SMA pads |
| Schematic strategy | Approach A — preserve verified connectivity, replace symbols/footprints/fields in place |

### Why approach A

The existing schematic's netlist was verified correct against the firmware pin
map, including the quirk where `CHARGED` routes to both GP18 and the ADC-capable
GP26:

| Firmware | Pico pad | Net |
|---|---|---|
| GP14 HVPULSE | 19 | `/HVPULSE` |
| GP18 CHARGED | 24 | `/CHARGED` |
| GP20 HVPWM | 26 | `/HVPWM` |
| GP26 ADC0 | 31 | `/CHARGED` (second tap) |
| GP0 trigger | 1 | to 1×7 header |
| GP6/7/11/27/28 | 9/10/15/32/34 | LEDs, buttons |
| VBUS | 40 | via D1 |
| 3V3 OUT | 36 | `+3V3` |

The hardest part of a schematic — correct connectivity — is already done and
independently confirmed. Redrawing risks it for no gain.

## 3. Frozen

Unchanged from REV04, because these were tuned empirically and documented in
`hardware/design_notes/`:

- **Topology**: T1 charge flyback → D2 rectifier → C3 storage → Q2 IGBT → coil,
  with T2 as the isolated gate-drive transformer.
- **Tuned values**: 2500 Hz at 1.22% duty for charging; 5 µs default pulse; 10 Ω
  gate series (R3/R7); 2 k shunt (R9); 18 V clamp (D7).
- **Pico pin assignment**, so existing firmware runs unmodified and serves as the
  bring-up reference.
- **40 × 116 mm outline, 2-layer**, Hammond 1551B half-shell fit.

## 4. Changes

1. BOM refreshed for 2026 DigiKey availability.
2. J3 moved to a wider-pitch connector with a milled creepage slot.
3. Trigger input protected and buffered.
4. Real HV netclass with enforced DRC.
5. Correct symbols and footprints, served from project-local libraries.
6. Reference designators restored to upstream's scheme.
7. Fresh layout, replicating HV geometry.

## 5. BOM

Sourced from DigiKey, hand-built. Because there is no JLC parts-library
constraint, **most of the upstream BOM is retained** — the substitutions
considered earlier existed only to satisfy JLC's library.

### 5.1 Must change

| # | Ref | Change | Reason |
|---|---|---|---|
| 1 | D6 D9 | `APT1608SRCPRV` → **`APT1608SURCK`** | Original is **obsolete and no longer manufactured**; DigiKey names this as the substitute |
| 2 | R9 | → **`RC0805FR-072KL`** (DK `311-2.00KCRCT-ND`) | Bug: value is 2 k but every part field said 75 R. Design notes confirm 2 k is the validated shunt |
| 3 | J3 | BG306 → **5.08 mm terminal block** + milled slot | Creepage; also drops the BG306's R1/R2 land ambiguity and bulk-only packaging |
| 4 | — | **New trigger front-end**: U2, R14, R15, R16, C6, J4 | Agreed robustness fix |

### 5.2 Retained

| Ref | Part | DigiKey | Status |
|---|---|---|---|
| C1 C2 | TDK C2012X5R1H475K125AB | `445-5980-1-ND` | Active |
| C3 | Murata KRM55TR72J474MH01K | `490-16845-1-ND` | Active |
| C5 | KEMET C0603C104K5RACTU | `399-5089-2-ND` | Active |
| D1 D3 D4 D5 | MCC SM4005PL-TP | `SM4005PL-TPMSCT-ND` | Active |
| D2 | onsemi MURA160T3G | — | Active |
| D7 | onsemi MM3Z18VB | `MM3Z18VBCT-ND` | Active, ±2% grade |
| D8 | Kingbright APT1608CGCK | `754-1116-1-ND` | Active |
| Q1 | IXYS LDA111STR | `212-LDA111SCT-ND` | Active, 23-wk lead |
| Q3 Q4 | AO3422 | — | Active; lowest Vgs(th) of the candidates |
| R1 | CRMA2010AF20M0FKEF | — | Active; 2000 V working, 4× margin |
| R3 R7 | RC0603FR-0710RL | `311-10.0HRCT-ND` | |
| R4 | RC0805FR-0775RL | `311-75.0CRCT-ND` | |
| R5 R10–R13 | RC0603FR-071KL | `311-1.00KHRCT-ND` | |
| R6 | RC0603FR-0722KL | `311-22.0KHRCT-ND` | |
| U1 | Raspberry Pi SC0915 | — | Active; guaranteed to Jan 2036 |
| J1 | Amphenol 132289 **or** Cinch 142-0701-801 | — | Interchangeable pair. **Not** Molex 73251-1150 — 8.76 mm vs 8.50 mm ground pitch plus two locating holes |
| J2 | JST S2B-XH-A(LF)(SN) | `455-2257-ND` | Side entry, 2.5 mm |

**R2 default: retain the TE `3522300KFT`** (DK `A121215CT-ND`), consistent with
the principle of keeping validated parts elsewhere in this revision. It sits below
the opto LED carrying ~24 µA and dissipating ~0.2 mW, so the 3 W / 250 V rating is
not required — if its 17-week lead time blocks the order, substitute any generic
300 k 2512 1% without further analysis.

### 5.2b Switches, headers, mechanical

| Ref | Part | Note |
|---|---|---|
| SW1 SW2 SW3 | C&K KSC7 series, J-bend, 6.2 × 6.2 mm | Actuator heights selected per §10. Upstream used `KSC741JLFS` (390 gf, 4.30 mm) for SW1/SW2 and `TL3301AF160QJ` (160 gf, 5.00 mm) for SW3 |
| P1 | 1×7 header, **2.54 mm** | Pitch corrected — the current port has 1.00 mm |
| P2 | 1×2 header, **2.54 mm** | Pitch corrected — currently 1.27 mm |
| P3 | 1×4 header, **2.54 mm** | Pitch corrected — currently 1.00 mm |
| MH1–MH3 | M3 mounting holes | `MountingHole:MountingHole_3.2mm_M3_Pad_Via` |
| — | Hammond **1551BTRD** shield | Or 1551BCLR / BTSK / BBK / BGY — all fit identically. 3D-printable alternative in `hardware/shield/` |

### 5.2c Off-board, order alongside

Not on the schematic but needed to actually use the tool:

| Item | Part | Note |
|---|---|---|
| Battery holder | Sparkfun `PRT-09925` | 2×AA with switch, JST-XH pigtail → J2 |
| Probe SMA | `CONSMA013.062` | Mates with J1 |
| Probe inductor | `PCV-0-472-03L` | |
| Ferrite | `744710603` | |
| USB isolator | Seeed `114991949` or Adafruit `2107` | **Strongly recommended** when communicating during operation |

### 5.3 New parts

| Ref | Part | Purpose |
|---|---|---|
| U2 | 74LVC1G17, SOT-23-5 | Non-inverting Schmitt buffer on trigger; 5.5 V tolerant input |
| R14 | 100 R 0603 | Trigger series limit |
| R15 | 10 k 0603 | Trigger pulldown — prevents a floating input self-triggering |
| R16 | 0 Ω 0603, **DNP** | Buffer bypass. Populate only with U2 removed |
| C6 | 100 nF 0603 | U2 decoupling |
| J4 | Edge-mount SMA pads, **DNP** | Optional trigger input, no commitment |

### 5.4 NRND — lifetime buy

| Ref | Part | DigiKey | Qty |
|---|---|---|---|
| T1 T2 | ATB322524-0110-T000 | `445-8636-1-ND`, 3,878 stock | **30** |
| Q2 | RGT16BM65DTL | 8,984 stock | **10** |

Both are NRND. The transformer has **no equivalent from any vendor in any
package** — the ATB3225 family has exactly two members and both are NRND. This is
the design's single point of failure.

Q2 is **retained rather than substituted**: it is the validated device, and
upstream warns that "gate charge may be different which will affect drive
waveform." ST `STGD6M65DF2` (650 V, TO-252, co-packed antiparallel diode, in full
production) is recorded as the forward path when ROHM stock is exhausted. Any
replacement must have a co-packed antiparallel diode.

Expected cost: ~$45–60 per board at qty 5, plus ~$45 one-time for the NRND
stockpile. Bare PCBs from JLC are a few dollars for five.

## 6. Schematic and libraries

### 6.1 Library strategy

Create **project-local** `sym-lib-table` and `fp-lib-table`, committed with the
design, so the project opens correctly on any machine.

Available from KiCad stock libraries:

| Need | Footprint |
|---|---|
| D1 D3 D4 D5 | `Diode_SMD:D_SOD-123F` |
| D7 | `Diode_SMD:D_SOD-323F` |
| D2 | `Diode_SMD:D_SMA` |
| Q2 | `Package_TO_SOT_SMD:TO-252-3_TabPin2` |
| Q3 Q4 | `Package_TO_SOT_SMD:SOT-23` |
| U2 | `Package_TO_SOT_SMD:SOT-23-5` |
| C3 | `Capacitor_SMD:C_2220_5750Metric` |
| J1 J4 | `Connector_Coaxial:SMA_Amphenol_132289_EdgeMount` |
| J2 | `Connector_JST:JST_XH_S2B-XH-A_1x02_P2.50mm_Horizontal` |
| U1 | `Module:RaspberryPi_Pico_SMD` |

To be created from manufacturer datasheets:

1. **T1/T2 — ATB322524**, 3.2 × 2.5 mm, 4 pads.
2. **Q1 — LDA111STR**, 6-pin gull-wing SMD, 2.54 mm pitch, 9.52 mm span. KiCad
   has no generic SOP-6 opto land.
3. **Tact switch** and **J3 terminal block**, once those parts are fixed.

### 6.2 Symbol corrections

| Ref | From | To |
|---|---|---|
| Q2 | `Device:Q_NMOS_Depletion` | Project-local IGBT **with antiparallel diode**. KiCad's `Q_NIGBT_*` family has no co-packed-diode variant |
| Q3 Q4 | `Device:Q_NMOS_Depletion` | `Device:Q_NMOS` (enhancement) |
| D1 D3 D4 D5 | `Device:D_Schottky_Small` | `Device:D_Small`. Fixes a documented upstream errata — these were never Schottky |
| Q1 | `*:root_0_mirrored_LDA111STR_*` | Project-local LDA111 symbol with **Darlington** output |
| T1 T2 | `NewAE_AltiumLib:root_0_xformer…` | `Device:Transformer_1P_1S` |

### 6.3 Field normalization

- `MANUFACTURE PART NUMBER 1` → `MPN`
- `MANUFACTURE 1` → `Manufacturer`
- `SUPPLIER PART NUMBER 1` → `DigiKey`
- `PART NUMBER` → **delete** (holds NewAE internal codes like `RCHIP-1K-0603`)
- Delete Altium cruft: `COMPONENT GROUP/KIND/TYPE`, `PIN COUNT`,
  `PP MATERIAL STACK`, `PP ROTATION`, `MOUNTING TECHNOLOGY`,
  `LATESTREVISIONDATE`, `PUBLISHER`, `SNAPEDA_LINK`, `CHECK_PRICES`,
  `AVAILABILITY`, `PRICE`
- Flatten `${ALTIUM_VALUE}` to literal values on all eleven affected symbols;
  give C5 its missing `100n`
- Populate `Datasheet` on every part

### 6.4 Trigger front-end

```
P1.1  ──┬── R14 100R ──┬── U2 74LVC1G17 ──── GP0 (U1 pad 1)
        │              │     (Schmitt)
J4 ─────┘           R15 10k          │
(DNP)                  │          C6 100n
                      GND            │
                                    GND

R16 (0R, DNP): trigger node ──────── GP0   [bypass; never fit with U2]
```

Non-inverting, preserving the firmware's `wait 1 PIN 0` polarity. Adds ~4.6 ns
propagation delay, negligible against the 8 ns PIO quantum and the ~95 ns IGBT
fall time. GP0 becomes input-only from the header's perspective, which matches
firmware usage.

### 6.5 Designators

Restore upstream's scheme so `BUILD-DRAWING-REV04.PDF` and the README BOM
explainer stay valid: `D6/D8/D9` LEDs, `P1/P2/P3` headers, `J1` = SMA,
`J2` = JST, `J3` = HV tap. New parts take `U2, R14, R15, R16, C6, J4`.

## 7. Layout and design rules

### 7.1 Board setup

2-layer, **1.6 mm thickness — must be stated explicitly on the fab order**. The
edge-mount SMA is specified for 0.062″ (1.57 mm) board and clamps the edge.
Outline stays 40 × 116 mm for 1551B shield fit.

### 7.2 Net classes

Replaces the current single 0.2 mm class with `min_clearance` disabled.

| Class | Nets | Clearance |
|---|---|---|
| HV | T1 secondary → D2 → C3 → Q2 collector → J1 centre; R1 top; J3 | Derived by measurement — see below |
| Default | all others | 0.2 mm |

The HV clearance value is **derived, not invented**: measure the existing board's
actual minimum HV-to-other clearance, then set the rule to that value. That copper
was hi-pot tested at 1 kV upstream, so a rule derived from it enforces "no worse
than the validated board." Open the geometry further wherever the fresh layout
allows it for free.

Restore `min_clearance` to a real value so DRC actually runs.

### 7.3 J3 creepage slot

Milled slot between the two HV pads to break the surface creepage path. The
original 2.07 mm pad gap passes IPC-2221B at ~600 V but fails IEC 60664-1
creepage (≈3.2 mm required), and the BG306's 500 VAC rating is a one-minute proof
test, not a working rating.

Fallback if the slot proves impractical: wider pad separation plus conformal
coating.

### 7.4 HV section

Replicate component placement and copper geometry for T1, T2, C1, C2, C3, D2,
D3–D5, Q1, Q2, R1, R2, J3 from the existing board. Route the logic side freely.
The analog layout is part of what was validated.

Transformer dot orientation must match the assembly drawing — upstream flags this
specifically, and reversing it produced the wrong-polarity spike on the original
prototype.

## 8. Verification gates

Each gate blocks the next.

1. **Git initialised, baseline committed.** *(Done — commit `154c225`.)*
2. **ERC clean** — zero errors.
3. **Netlist diff** against the current board. Every difference must be
   intentional: the trigger front-end, J3, and the designator renames.
4. **DRC clean** under the new HV rules.
5. **3D view + shield fit**, particularly switch actuator heights against the
   1551B half-shell.
6. **Fab output review** — gerbers, drill, slot — before ordering.

## 9. Bring-up

Staged, because the board generates ~500 V.

1. Logic only — omit T1, T2, C3, Q2. Verify 3V3, LEDs, buttons, USB enumeration,
   stock firmware runs.
2. Scope the trigger front-end: feed an edge into P1.1, confirm clean output at
   GP0, measure actual buffer delay.
3. Populate HV section. Arm with **no coil and no probe fitted**; confirm CHARGED
   asserts and the 60 s timeout disarms.
4. First pulses into a resistive test jig, not a coil, with the shield fitted.
5. Compare gate-drive waveform against the scope traces in
   `hardware/design_notes/`. This is the acceptance test for the analog path.

## 10. Items to resolve during implementation

These have defined resolution methods, not open questions:

| Item | Resolution |
|---|---|
| Switch actuator height | Measure the 1551B half-shell clearance with the Pico reflowed flat, then select heights from the C&K KSC7 catalogue. SW3 needs to clear the shield; SW1/SW2 are ergonomic only |
| Switch actuation force | Upstream used 390 gf for SW1/SW2, plausibly a deliberate safety choice. Confirm against the chosen part's datasheet |
| D7 land: SOD-323 vs SOD-323F | Datasheet says SOD-323**F**, 200 mW; the current schematic field says only `SOD323`. Verify against the onsemi datasheet and draw to match |
| D1/D3/D4/D5 land: SOD-123F vs SOD-123FL | MCC's drawing gives a 2.36 mm land span. Verify KiCad's `D_SOD-123F` matches before using it |
| JLC minimum routed slot width | Check JLC's current capability page before committing the J3 slot geometry |

## 11. Out of scope

No FPGA, no on-board ADC or comparator trigger front-end, no change to energy
storage or switch topology, no firmware rewrite. Each is defensible later; none is
needed for a correct 2026 board, and each would require re-validation.

Rationale for deferring the FPGA specifically: the PIO trigger path already runs
at the full 125 MHz, giving an 8 ns quantum. The IGBT's 95 ns fall time and the
gate-drive transformer's 0.4 µH leakage dominate that by an order of magnitude, so
faster digital timing buys nothing. What a ChipWhisperer/Husky actually offers —
clock-synchronous glitching and SAD/pattern triggering — is reachable through the
existing external-trigger path (`picoemp_configure_pulse_external()` sets GP14 to
an input), which this revision improves rather than replaces.

## 12. Provenance and licensing

This repository is grafted onto upstream `newaetech/chipshouter-picoemp` history.
Upstream HEAD is `eb2284d` (2024-08-28) and has not moved since; the working copy
was verified byte-identical to it apart from local additions.

Upstream is licensed **CC BY-SA 3.0**. This revision is a derivative work, so if
published it must carry the same licence and attribute NewAE Technology.

Two defects found during the audit are genuine **upstream** bugs worth reporting:

- **R9** carries R4's part data throughout the Altium source (`RCHIP-75R-0805`,
  `RC0805FR-0775RL`, DK `311-75.0CRCT-ND`) despite a value of 2 k. The published
  `.xls` BOM has the correct `RC0805FR-072KL`, so only the schematic is wrong.
- **APT1608SRCPRV** (D6/D9) is obsolete and no longer manufactured, so the
  published BOM can no longer be ordered as-is.

## 13. Deliverables

- Clean `.kicad_sch` and `.kicad_pcb`
- Project-local symbol and footprint libraries
- DigiKey CSV BOM, cart-ready
- Gerbers and drill files for JLC bare-PCB fabrication
- Build note documenting what changed from REV04
