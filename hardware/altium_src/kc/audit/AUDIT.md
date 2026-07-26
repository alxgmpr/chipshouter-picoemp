# PicoEMP KiCad Port — Audit

Audited 2026-07-25 against upstream `chipshouter-picoemp` REV04 (Altium source, `BOM for ChipShouter-PicoEMP.xls`, and the "BOM explainer" in `hardware/README.md`).

Files audited:
- `ChipShouter-Pico.kicad_sch` (48 real components, flat sheet)
- `ChipShouter-Pico.kicad_pcb` (73 footprint instances, 53 unique refs, 2-layer)
- `chipshouter-pico-mcu.kicad_sch` (orphaned — not referenced by the project)
- `production/` (stale export from 2026-07-23, pre-migration)

---

## 1. Blocking issues — the board is not fabricable in its current state

### 1.1 The PCB carries two parallel copies of the design

20 reference designators have **two footprints each** on the board — the original
Altium-imported one and a new KiCad one placed on top of it:

`C1 C2 C5 R1 R2 R3 R4 R5 R6 R7 R9 R10 R11 R12 R13 MH1 MH2 MH3 J1 J2`

`J1` is the worst case: it holds **two different parts** — the original edge-mount
SMA (`CON-SMA-MALE-PCB-EDGE062`) and a new 1x7 pin header. The SMA was
simultaneously re-created as `J6`.

### 1.2 None of the new footprints are connected

All 384 routed segments sit on the legacy Altium net names (`NetC3_2`, `NetP1_1`,
`NetJ1_2`, `VCC`, …). Every KiCad-style net has **zero** copper:

```
+3V3  /CHARGED  /HVPULSE  /HVPWM  Net-(C1-Pad2)  Net-(C5-Pad2)  Net-(D1-A)
Net-(D1-K)  Net-(D2-K)  Net-(D3-K)  Net-(D4-K)  Net-(D5-K)  Net-(D7-A)
Net-(D7-K)  Net-(J1-Pin_1..6)  Net-(J3-Pin_2)  Net-(J6-Ext)  Net-(LED1-A)
Net-(LED2-A)  Net-(LED3-A)  Net-(R7-Pad2)  Net-(U1-GPIO6/7/11/27/28)
```

Each node now exists twice — once under its Altium name (with copper) and once
under its KiCad name (without). `VCC` (31 pads, routed) and `+3V3` (3 pads,
unrouted) are the same rail, split.

The new symbols have been placed and wired in the schematic, but no clean
"Update PCB from Schematic" has ever completed.

### 1.3 Every header footprint has the wrong pitch

All original headers are **2.54 mm**. Every replacement chosen is 1.00 mm or
1.27 mm — a 2–2.5× pitch error. Measured from the board file:

| Ref | Original footprint | Pitch | New footprint assigned | Pitch |
|---|---|---|---|---|
| P1 → J1 | `Miscellaneous Connectors:HDR1X7` | 2.54 | `PinHeader_1x07_P1.00mm_Vertical` | 1.00 |
| P2 → J4 | `Miscellaneous Connectors:HDR1X2` | 2.54 | `PinHeader_1x02_P1.27mm_Vertical` | 1.27 |
| P3 → J5 | `Miscellaneous Connectors:HDR1X4` | 2.54 | `PinHeader_1x04_P1.00mm_Vertical` | 1.00 |
| J2 | `22-23-2021` (Molex KK) | 2.54 | `PinHeader_1x02_P1.27mm_Vertical` | 1.27 |

J2 is the battery input and the actual part is a **JST XH (2.5 mm pitch)**
`S2B-XH-A(LF)(SN)` — a 1.27 mm header is wrong by 2×.

### 1.4 No project library tables

There is no `fp-lib-table` or `sym-lib-table` in the project directory, and the
global table contains only the stock KiCad libraries. **All 26** custom libraries
referenced by the design are unregistered:

```
main  SamacSys  NewAE_AltiumLib  CKG57N_2220  DSS13UTR  ATB322524  MOUNT_M3_TIGHT
CK_KSC7J  LED-0603-RED  LED-0603-GREEN  GCT_BG306  DPAK_TO-252AA_M  SOT95P245X110-3M
RESC1608X55N  RESC2012X70N  RESC5025X06N  RESC6432X06N  CAPC0805_M  CAPC0603_M
CON-SMA-MALE-PCB-EDGE062  DO-214AC  SOD323  22-23-2021  "Miscellaneous Connectors"
MODULE_SC0915_TH  C__Users_colin_Documents_AltiumLL_SamacSys.PcbLib
```

The board still renders because KiCad embeds full footprint geometry in
`.kicad_pcb`. But nothing can be edited, re-linked, or re-synced, and the project
is not portable to another machine.

---

## 2. Component-level gaps

Full per-reference table: `audit/bom-gap-analysis.csv`

### 2.1 Eight components have no footprint at all in the schematic

`D1  Q2  Q3  Q4  SW1  SW2  SW3  J3`

Q2 is the IGBT and Q3/Q4 are the gate-drive MOSFETs — the three most
layout-sensitive parts on the board.

### 2.2 Nine footprints have no library prefix (invalid in KiCad)

| Ref | Footprint field | Should be |
|---|---|---|
| C3 | `CKG57N_2220` | 2220 / EIA 5750 metric, height ≤5 mm for the shield |
| D2 | `SMA` | `Diode_SMD:D_SMA` (DO-214AC) |
| D3 D4 D5 | `DSS13UTR` | verify actual SM4005PL-TP package |
| D7 | `SOD323` | `Diode_SMD:D_SOD-323` |
| T1 T2 | `ATB322524` | custom — needs a real library entry |
| Q1 | `C__Users_colin_Documents_AltiumLL_SamacSys.PcbLib:SOP254P952X470-6N` | absolute Windows path from the original author's PC |

### 2.3 Two symbols have unresolvable `lib_id`s

- `Q1` → `*:root_0_mirrored_LDA111STR_*` — contains literal wildcards
- `T1`, `T2` → `NewAE_AltiumLib:root_0_xformer_2_2_hv_NewAE_AltiumLib.DBLib`

### 2.4 Wrong symbols chosen

| Ref | Part | Symbol used | Problem |
|---|---|---|---|
| Q2 | RGT16BM65DTL (IGBT) | `Device:Q_NMOS_Depletion` | It's an IGBT, not a depletion MOSFET |
| Q3 Q4 | AO3422 | `Device:Q_NMOS_Depletion` | Enhancement-mode, not depletion |
| D1 D3 D4 D5 | SM4005PL-TP | `Device:D_Schottky_Small` | Standard silicon rectifier |

D1/D3/D4/D5 is worth calling out: this is a **known upstream errata** that the port
inherited. `hardware/README.md` says explicitly that the schematic "claimed they
were Schottky diodes, but as @settinger caught this was never the case."

### 2.5 R9 carries R4's part data — real ordering bug

R9's `Value` is `2k`, but every sourcing field still says 75R:

```
PART NUMBER              RCHIP-75R-0805     (should be RCHIP-2K-0805)
MANUFACTURE PART NUMBER  RC0805FR-0775RL    (should be RC0805FR-072KL)
SUPPLIER PART NUMBER     311-75.0CRCT-ND    (should be 311-2.00KCRCT-ND)
ALTIUM_VALUE             75R                (should be 2k)
```

Ordering from this BOM gets a 75R where a 2k belongs. This is not cosmetic — the
upstream design notes identify the **2k shunt on R9 as the final validated gate-drive
choice**, arrived at after sweeping no-shunt / 2k / 10k / 22k.

### 2.6 C5's value renders literally

Eleven symbols use `${ALTIUM_VALUE}` as their `Value`, which KiCad resolves from a
companion `ALTIUM_VALUE` property. That works for R1–R13. **C5 has no
`ALTIUM_VALUE` property**, so its value displays and exports as the literal string
`${ALTIUM_VALUE}`. C5 should be 100 nF 0603.

All eleven should be flattened to real values regardless — the indirection breaks
any BOM tool that doesn't do variable substitution.

### 2.7 The `PART NUMBER` field is NewAE's internal code, not an MPN

`PART NUMBER` holds values like `RCHIP-1K-0603`, `ATB322524_PROTO`,
`MOUNT_M3_TIGHT`. The real MPN lives in `MANUFACTURE PART NUMBER 1`. Any BOM
export keyed on `PART NUMBER` — which is what the field name invites — produces
unorderable internal codes. The BOM analyzer made exactly this mistake.

Fields to normalize: `PART NUMBER` → `MPN`, `MANUFACTURE 1` → `Manufacturer`,
`MANUFACTURE PART NUMBER 1` → `MPN`, `SUPPLIER PART NUMBER 1` → `DigiKey`.

### 2.8 J1–J5 are all DNP and excluded from BOM

Defensible for J3 (HV calibration, upstream says optional) and arguably the debug
headers. **Not** defensible for J2 — that's the battery power input.

### 2.9 Zero LCSC part numbers

Not one component has an LCSC number. `production/bom.csv` has an empty
`LCSC Part #` column on all 28 lines. Nothing can be assembled by JLCPCB yet.

---

## 3. Not in the BOM at all (off-board, upstream Part 4)

| Item | Upstream PN | Note |
|---|---|---|
| Enclosure | Hammond `1551BTRD` | 3D-printable alternative in `hardware/shield/` |
| Battery holder | Sparkfun `PRT-09925` | 2×AA with switch, JST-XH pigtail → J2 |
| Probe SMA | `CONSMA013.062` | mates with J6 |
| Probe inductor | `PCV-0-472-03L` | |
| Ferrite | `744710603` | |
| USB isolator | Seeed `114991949` or Adafruit `2107` | **strongly recommended** in operation |

---

## 4. Design-rule observations

- Board is 2-layer — fine and cheap at JLCPCB.
- **There is no high-voltage net class.** A single netclass (`Default` / `All Nets`)
  applies 0.2 mm clearance to everything, and `min_clearance` is set to `0.0`
  (disabled). This board generates ~500 V and upstream hi-pot tests it at 1 kV.
  The existing copper inherits the Altium spacing, but nothing in the current rule
  set protects it — any re-route will silently close the isolation gap.
  Add an `HV` netclass covering `NetC3_2` / the transformer secondary / J3 / J6
  before touching the layout.
- `EXCLUDE DNP` is `false` in `fabrication-toolkit-options.json` while J1–J5 are
  marked DNP. Decide which behaviour you want before exporting.

## 4a. READ THIS FIRST — net state of the sourcing findings

Sections 4b–4g were written as research landed, and later passes corrected
earlier ones. **This table is the reconciled answer.** Where a later section
contradicts an earlier one, the later one wins.

### Lifecycle — the parts with no forward path

| Ref | Part | Status | Successor |
|---|---|---|---|
| T1 T2 | ATB322524-0110-T000 | **NRND** (§4b, §4e) | **None from any vendor, any package** |
| Q2 | RGT16BM65DTL | **NRND** (§4e — §4b said Active, wrong) | None at ROHM in DPAK → **STGD6M65DF2** |
| D6 D9 | APT1608SRCPRV | **Obsolete** (§4c, §4g) | KT-0603R / APT1608SURCK |

Everything else on the board is Active. Buy T1/T2 and Q2 in quantity now.

### Long lead times on Active parts

D7 MM3Z18VB **39 wk** · US1J-13-F **32 wk, currently out of stock** ·
LDA111STR **23 wk** · C1/C2 TDK **24 wk** · U1 SC0915 **18 wk** ·
R2 3522300KFT **17 wk** · C5 KEMET **12 wk**

### Traps that will bite you

1. **The LCSC SMA does not fit your footprint.** Molex `C841205` has 8.76 mm
   ground pitch + 2 drilled locating holes; your `SMA_Amphenol_132289_EdgeMount`
   has 8.50 mm and no holes. Respin or consign. (§4g — §4c was wrong.)
2. **D7's footprint field says `SOD323`; the part is SOD-323F.** Different land.
   (§4f)
3. **Pico W / Pico 2 W are not drop-ins** — GPIO23/24/25/29 are reassigned to the
   radio. Plain Pico 2 (SC1631) *is* a clean swap. (§4g)
4. **BG306 `-2-` is the R2 mirrored land pattern**; R1 is the stocked standard.
   And `-G` is bulk box, not reel. (§4d)
5. **TL3301 QJ vs QG is lead form**, not packaging — J-lead vs gull wing, not
   footprint-compatible. (§4c, §4d)
6. **SM4005PL is standard recovery (trr 1–3 µs)**, MURA160/US1J are 75 ns. Never
   treat them as alternates for each other. (§4f)
7. **Don't sub CRCW-HP or RCA for R1** — those are anti-surge families, not
   high-voltage. R1's schematic property claiming 400 V is wrong; the real
   CRMA2010 rating is 2000 V. (§4f)
8. **Green LED Vf matters** — an emerald-green 525 nm part at Vf 3.1 V gives
   ~0.2 mA through the existing 1 k and is invisible. (§4c)

### Corrections to my own earlier claims, for the record

| Claim | Where | Corrected to |
|---|---|---|
| Q2 RGT16BM65DTL is Active | §4b | **NRND at ROHM** (§4e) |
| AO3422 is 30 V | brief | **55 V**, and load-bearing (§4c) |
| PMV37ENEAR "don't design it in" | §4c | **Active at Nexperia** — fine by hand, not via JLC (§4d) |
| TL3301AF160QJ has no LCSC listing | §4c | **`C273520` exists**, Active, 11-wk lead (§4d) |
| All three SMAs interchangeable | §4c | **Molex is not** (§4g) |
| D7 is SOD-323, 300 mW | §4b | **SOD-323F, 200 mW** (§4f) |
| CRMA2010 is 400 V rated | §2.7 metadata | **2000 V** (§4f) |
| "Standardize all three switches" | §4c | Valid, but SW3's 5 mm height is deliberate (§4d) |

### Assembly reality at JLCPCB

Only **one** part on the board is a JLCPCB Basic part as-designed. Adopting the
§4c/§4b swaps (C5, D2, red LED) adds three more. Everything else is Extended →
per-line setup fee.

**Cannot be machine-placed regardless of part choice:** the edge-mount SMA
(wave/manual, $3.50 + $0.0173/joint, +1 day), the JST XH if added (through-hole),
and the HV output connector (absent from JLC's library, and specified in bulk
box packing).

## 4b. Sourcing & lifecycle — HV path

Verified against LCSC/JLCPCB parts library and manufacturer pages, 2026-07-25.
Stock figures go stale; re-check before ordering.

### The one part that should change your plans

**T1/T2 — ATB322524-0110-T000 is Not For New Designs.** Digi-Key lists Product
Status "Not For New Designs"; other distributors report "PRODUCTION (NOT
RECOMMENDED FOR NEW DESIGN)". The series has exactly two members
(`ATB322524` and the 1.5 mm-tall `ATB322515`, `C415291`) and **both are NRND**.
There is no TDK successor series, and no equivalent 3.2×2.5 mm 1:10 SMD step-up
transformer from Würth, Coilcraft, Sumida or Murata.

Good news: contrary to its reputation it is currently **well stocked** —
`C249001`, LCSC retail 4,721 / JLCPCB library 973, $0.42 @1k. **Buy a lifetime
supply now.** This part is the single point of failure for the whole design.

Also note its withstanding voltage is **500 Vrms** on a ~500 V rail — essentially
zero margin. That's inherent to the original design, not something the port
introduced.

### JLCPCB assembly economics

**Only one part in the entire HV path is a JLCPCB Basic part** (US1M, and only if
you adopt it as the D2 substitute). Everything else is Extended, which means a
per-line setup fee. Budget for that, or accept hand-assembly on some lines.

### Per-part findings

| Ref | Part | Status | LCSC | Action |
|---|---|---|---|---|
| Q2 | RGT16BM65DTL | Active | `C3193927`, **retail stock 22** | Stock is the risk, not lifecycle |
| Q1 | LDA111STR | Active | `C17531663` | See note below |
| T1 T2 | ATB322524-0110-T000 | **NRND** | `C249001` | Buy lifetime supply |
| C3 | KRM55TR72J474MH01K | — | **not stocked** | Substitute required |
| D2 | MURA160T3G | Active | `C50432` **stock 0** | Substitute required |
| D1 D3 D4 D5 | SM4005PL-TP | Active | `C151774` retail only — **not in JLC assembly library** | Substitute required for PCBA |
| D7 | MM3Z18VB | Active | **not stocked** | Substitute required |
| R1 | CRMA2010AF20M0FKEF | Active | `C2091374` | Keep |
| R2 | 3522300KFT | Active | `C4262190` | Can downgrade — see below |

### Substitutions worth taking

- **D2 → US1M (`C412437`).** SMA, **1000 V** vs 600 V, same trr 75 ns, a
  **JLCPCB Basic part** with 503k in stock, and ~20× cheaper ($0.006 vs $0.10).
  Strictly better than both the original and upstream's `US1J-13-F` suggestion.
  600 V on a ~500 V rail plus flyback overshoot was always thin.
- **D1/D3/D4/D5 → ES1J (`C2892680`).** SOD-123FL, 600 V 1 A, JLC stock 53k,
  $0.005. Required anyway since the original isn't in the assembly library.
- **D7 → MM3Z18VST1G (`C236092`).** onsemi SOD-323, Vz 17.56–18.35 V (**±2%**) —
  the same tolerance grade as the "B" suffix original. Do **not** reach for
  `BZT52C18S` (±5%) unless you have to; upstream warns this zener "drastically
  affects the drive waveform," and a failed D7 destroys Q2.
- **C3 → FM55X474K631EFG (`C692326`).** 0.47 µF 630 V X7R 2220, $0.40 @1k.
  The board's `CKG57N_2220` land (8.0 mm span, 4.0 mm gap) accepts both
  metal-terminal and plain 2220 chips, so no footprint change.
  Two caveats: any 630 V class-2 MLCC loses a large fraction of its capacitance
  at 500 V DC bias (true of the original too), and the Murata KRM55 /TDK CKG57N
  metal terminals exist specifically for **board-flex crack protection** — a
  plain 2220 gives that up.
- **R2 → RC2512FK-07300KL (`C137027`), optional.** $0.036 vs $0.62. Safe because
  R2 is *not* a high-voltage position: it sits in series *below* the opto LED
  (HV → R1 20 M → Q1 LED → R2 300 k → GND), so at ~24 µA it drops only ~7.4 V and
  dissipates ~0.2 mW. R1 takes essentially the entire 490 V. Keep the TE part only
  if you want margin against R1 failing short.

### Substitutions to be careful with

- **Q2.** Any IGBT replacement **must** have a co-packed antiparallel diode.
  Best drop-in is **STGD6M65DF2 (`C472580`)** — ST, TO-252, 650 V, same G/C/E
  pinout, soft/fast antiparallel diode, JLC stock 808, $0.68.
  `AOD5B65MQ1E` (`C3193928`) is cheaper but has roughly half the current and
  power (52 W vs 94 W) and a lower Vge(th) of 4.2 V, so it turns on earlier —
  recheck gate drive and the D7 clamp if you use it.
  **Avoid** `ISL9V3040D3ST-F085C` (400 V clamped ignition IGBT — will avalanche)
  and `NCE07TD60BK` (no co-packed diode found in its datasheet).
- **Q1.** Correction to the audit above and to common description: LDA111STR is
  **not** a solid-state relay. It's a unidirectional-input optocoupler with a
  **Darlington output**, CTR min 300%, BVceo only 30 V. The isolation is the
  barrier, not the output rating. In circuit the LED is fed through R1 (20 M) off
  the ~500 V rail, so **LED current is only ~24 µA** — that is precisely why
  upstream says other optos won't work as-is. Candidate subs (`4N33SR2M`
  `C898962`, `TIL113SM` `C900043`) share the standard 6-pin opto pinout and fit
  `SOP254P952X470-6N`, but are all specified at **If = 10 mA**. Expect to drop R1
  to ~4.7 M for usable CTR, which quadruples bleeder current and shortens HV
  decay. Upstream notes the feedback circuit can simply be omitted.
- **R1.** Keep `CRMA2010AF20M0FKEF`. It is effectively the only 20 MΩ HV-rated
  2010 at LCSC, and its margin is comfortable (0.5 W, 2000 V working vs ~490 V
  actual — 4×). **Do not drop in a plain CRCW/RC 2010**: standard 2010 thick
  films are 200 V working and will drift or arc at ~490 V.

### Correction to §2.4 above

The agent's schematic read shows D1/D3/D4/D5 are **not** in the 500 V path.
D3/D4 sit on the HVPWM gate-drive line to Q3, D5 on HVPULSE to Q4, and D1 is
battery-input protection at J2. Their 600 V rating is safety margin against
isolation breakdown, not a working requirement — consistent with upstream's
"in circuit they will be exposed to 4V max ever." The wrong *symbol*
(`D_Schottky_Small`) is still worth fixing; the part choice is not urgent.

Also: the `DSS13UTR` footprint geometry (pads 1.15 × 1.30 mm at ±1.55 mm,
4.25 mm span) confirms **SOD-123FL** — not SMA/DO-214AC and not SMAF.

### Not independently verified

Digi-Key/Mouser "Product Status" flags for LDA111STR, CRMA2010AF20M0FKEF and
MM3Z18VB could not be surfaced directly. TDK's own product pages for both ATB
parts returned HTTP 403, so the NRND status rests on Digi-Key and secondary
distributors rather than TDK directly.

## 4c. Sourcing & lifecycle — logic, connectors, switches, LEDs

### Obsolete or unavailable

- **D6/D9 red LED `APT1608SRCPRV` is OBSOLETE** at Kingbright, and has no LCSC
  listing. Must be replaced. → **`C2286` KT-0603R**, JLCPCB **Basic**,
  7.8 M in stock, $0.0053. Clean drop-in.
- **SW3 `TL3301AF160QJ` — no LCSC listing**, and all QJ variants are dead stock
  (15 / 16 / 0 units across the family).
- **J3 `BG306-02-A-2-0400-L-G` — not on LCSC at all.** Consign or substitute.
- **C1/C2 `C2012X5R1H475K125AB`** — exact MPN not on LCSC (nearest TDK has 87 units).
- **`S2B-XH-A` was never ported.** Zero occurrences in the KiCad schematic —
  J2 carries the Molex KK-254 (`22-23-2021`) identity instead. If you want the
  JST XH battery input, it needs adding: `C157931`, 2.5 mm pitch, THT.

### AO3422 — the datasheet spec I gave you was wrong

Q3/Q4 are **55 V / 2.1 A**, not 30 V. That matters: tracing the schematic, Q3
(gate `HVPWM`) and Q4 (gate `HVPULSE`) each drain into an ATB322524 **flyback
primary**. The drain sees Vin + reflected voltage + leakage spike, so the 55 V is
deliberate headroom, not incidental. Vgs(th) is 0.6/1.3/2.0 V and the part is
characterized to 2.5 V gate drive, so 3.3 V RP2040 drive has ≥1.3 V worst-case
overdrive — fine.

Status: **Active** (Digi-Key, 608 k stock). One small distributor shows NRND —
an outlier. Note the **AO3422L** variant *is* obsolete; don't order that.
LCSC `C37130`, JLC assembly stock 28 k, Extended.

Upstream's suggested alternate **PMV37ENEAR is effectively unavailable**
(`C553095`, LCSC retail stock **1**). Do not design it in.

**There is no JLCPCB Basic equivalent at 55 V.** The only Basic SOT-23 N-channel
parts ≥30 V are 2N7002 (`C8545` — 115 mA, far too weak) and AO3400A (`C20917` —
only 30 V).

→ **CJ2310 (`C75882`)** is the best swap: 60 V, 3 A, identical Vgs(th) window
(0.5–2.0 V), *lower* Rds(on) (125 mΩ vs 160 mΩ @4.5 V), same SOT-23 pinout,
262 k in stock, $0.031 — 9× the stock at half the price of the AO3422.
AO3400A only if you add a primary snubber and scope the drain ringing to confirm
it stays under 30 V; chasing "Basic" here costs 25 V of avalanche margin on a
flyback switch.

### Switches — assembly stock is the blocker, and SW3 has a lead-form trap

**SW1/SW2 `KSC741JLFS`** is Active at C&K, LCSC retail 12,874 — but **JLC
assembly stock is only 39**. At two per board that's ~19 boards.
→ `C221750` **KSC441JST2LFS**, same C&K 6.2×6.2 mm J-lead family, IP67, 957 in
stock. Verify the J-lead pad pattern is identical before committing.

**SW3:** in the E-Switch TL3301 series the final letter is the **lead form** —
**QJ = J-lead, QG = gull-wing**. They are *not* footprint-interchangeable. The
available `C273519` TL3301AF160**QG** has the same actuator height and 160 gf
force but needs a gull-wing pad change.

This reconciles with upstream's note that "SW1 SW2: you can use the same PN as
SW3 (the footprint is the same)" — that holds for the J-lead QJ part against the
J-lead KSC741J, not for the QG.

⚠️ **Schematic/PCB mismatch on SW3**: the schematic says `TL3301AF160QJ` with no
footprint; the PCB places `CK_KSC7J` (the KSC741J footprint). Cleanest resolution
is to **standardize all three switches on one part** — which also fixes the SW1/SW2
stock problem.

Note the force change if you go cheap: `C318884` (Basic, 918 k stock, $0.018) is
**160 gf vs 390 gf**. These are the arm/trigger buttons; the heavy action is
arguably a deliberate safety feature. Treat that as a design decision, not a
substitution.

### J3 — the HV output connector is over-stressed ⚠️

C3 is a 0.47 µF / **630 V** storage cap, so this 0.1"-pitch connector carries
roughly **500–600 V**.

Measured J3 pad geometry from the board file: pads 1.02 × 1.9 mm, offset
(2.54, −3.3) mm → **closest corner-to-corner spacing ≈ 2.07 mm**.

| Standard | Requirement at ~600 V | Result |
|---|---|---|
| IPC-2221B, external uncoated | ≈0.50 mm | **passes** |
| IEC 60664-1 creepage, PD2, mat. group IIIa | ≈3.2 mm | **fails** |

But the binding constraint is the connector itself: the BG306's **500 VAC
dielectric withstanding voltage is a one-minute proof test, not a working
rating**. Good practice puts DWV at 2–3× working voltage. Running ~600 V against
a 500 V proof test leaves *negative* margin.

Options, in order:
1. **Go wider pitch** — `C25170858` PZ508V (5.08 mm, THT, $0.064) or JST VH
   3.96 mm (`C16728` VH-2A, 111 k stock, $0.023). 1.5–2× the creepage.
2. **Keep 2.54 mm but mill a slot between the two HV pads** to break the surface
   creepage path, plus conformal coating. Cheapest fix, keeps existing injection
   tips compatible.
3. If you must stay 2.54 mm SMD: `C5142235` or `C42381025` — but both are
   **right-angle** while the BG306 is top-entry vertical, so almost certainly not
   a drop-in.

### Edge-mount SMA

Amphenol **132289**, Cinch **142-0701-801** and Molex **73251-1150** are
cross-referenced as interchangeable, all 50 Ω edge-mount for 0.062" board — so
your `Connector_Coaxial:SMA_Amphenol_132289_EdgeMount` choice is sound. Caveat:
Molex describes theirs as right-angle vs end-launch for the other two; verify
ground-tab and center-pin geometry.

Only the Molex is on LCSC — `C841205`, JLC 2,684, **$4.19** (by far the most
expensive part on the board), Extended.

⚠️ **Avoid the cheap "SMA-KE" parts** (`C496549`, `C504007`, ~$0.40). Their
datasheets show **vertical PCB-mount jacks** — transmission perpendicular to the
board. Not edge-launch, not drop-ins, despite matching the search terms.

**JLC cannot machine-place this** — an edge-mount connector straddles the board
edge. Hand-solder regardless.

### Green LED — check Vf before substituting

D6/D8/D9 run from **+3V3 through 1 k** (R11/R12/R13). The original APT1608CGCK is
a 570 nm yellow-green at Vf ≈2.2–2.5 V → ~0.8–1.1 mA. An "emerald green" 525 nm
InGaN part at Vf ≈3.1 V gives **~0.2 mA — essentially invisible**.

There is **no JLCPCB Basic 0603 green LED**; the only Basic 0603 parts are red
and white. → **`C965805` XL-1608SYGC-06**, Vf 2.2 V, 570–575 nm, 730 k stock,
$0.006. If you want the Basic 0805 green (`C2297`) you must also drop R11–R13 to
~100–220 Ω.

### Raspberry Pi Pico

`C7203002`, JLC stock **834**, $6.16, Extended. Low stock plus high price makes
this a common order-blocker; realistic options are consignment or hand-soldering.

**Pico 2 (SC1631) is pin-compatible** — same 40-pin castellated layout, same
51×21 mm outline, same BOOTSEL/USB/LED placement, and GPIO23/24/25/29 keep their
functions. Only physical difference is one extra underside test pad. But **the
plain Pico 2 is not on LCSC** (only Pico 2 W, `C42394205`).
*Unverified:* whether the RP2350 A2 GPIO input erratum affects any PicoEMP input
path — worth checking before switching, since this tool reads GPIO.

### Cheap wins

- **C5 → `C14663` CC0603KRX7R9BB104** (YAGEO 100 nF 50 V X7R 0603): JLCPCB
  **Basic**, 81 M stock, **$0.0022** vs $0.0186. No reason not to.
- **C1/C2 → `C98192` CL21A475KBQNNNE** (Samsung 4.7 µF 50 V X5R 0805), 1.18 M
  stock, $0.018. Keep 50 V — C1/C2 sit on the flyback primary rail where the
  designer wanted ringing headroom; the nearest Basic part is only 25 V.

### Cannot be machine-assembled by JLCPCB, whatever part you pick

The edge-mount SMA (J1/J6), the JST XH if you add it (through-hole), and the HV
output connector (absent from JLC's library). Budget for hand-soldering or
consignment on those three.

### Recommended swap summary

| Ref | From | To | LCSC | Why |
|---|---|---|---|---|
| Q3 Q4 | AO3422 | CJ2310 | `C75882` | 60 V, better Rds(on), 9× stock, ½ price |
| SW1 SW2 | KSC741JLFS | KSC441JST2LFS | `C221750` | JLC stock 39 → 957, same family |
| SW3 | TL3301AF160QJ | standardize with SW1/SW2 | — | QJ unavailable; QG is a different lead form |
| J3 | BG306 (2.54 mm) | wider pitch, or slot the PCB | `C16728` / `C25170858` | 600 V on a 500 V-DWV 0.1" connector |
| D6 D9 | APT1608SRCPRV | KT-0603R | `C2286` | **obsolete** → Basic, 7.8 M stock |
| D8 | APT1608CGCK | XL-1608SYGC-06 | `C965805` | Vf 2.2 V matches the 1k/3V3 drive |
| C1 C2 | TDK C2012X5R… | CL21A475KBQNNNE | `C98192` | not on LCSC → 1.18 M stock |
| C5 | KEMET C0603C104 | CC0603KRX7R9BB104 | `C14663` | Basic, 8× cheaper |
| D2 | MURA160T3G | US1M | `C412437` | Basic, 1000 V vs 600 V, 20× cheaper |
| D1 D3 D4 D5 | SM4005PL-TP | ES1J | `C2892680` | original absent from JLC library |
| D7 | MM3Z18VB | MM3Z18VST1G | `C236092` | not stocked; ±2% grade preserved |
| C3 | KRM55TR72J474MH01K | FM55X474K631EFG | `C692326` | not stocked |
| R2 | 3522300KFT | RC2512FK-07300KL | `C137027` | optional; 20× cheaper, not an HV position |

## 4d. Corrections — verified against manufacturer datasheets

A later lifecycle pass contradicted several claims in §4c. These supersede it.

### PMV37ENEAR is Active at Nexperia — I overstated the case against it

§4c said "effectively unavailable — do not design it in." That was based on LCSC
stock of 1, and it conflated *LCSC availability* with *lifecycle*.

Nexperia's product page states **"Product status: Production."** It is a good
part: 60 V, 3.5 A, Vgs(th) 1.3/1.7/2.7 V, Rds(on) 64 mΩ @4.5 V, AEC-Q101
qualified, Tj to 175 °C. The `R` suffix is just reel packaging — Nexperia's
ordering table lists the base type `PMV37ENEA`.

**Correct statement:** perfectly viable for a hand build ordered from
DigiKey/Mouser; not viable through LCSC/JLCPCB assembly. If you're going the
JLC-assembly route, CJ2310 is still the recommendation — but on threshold it's
worth noting the AO3422 (0.6–2.0 V) and CJ2310 (0.5–2.0 V) both have a *lower*
Vgs(th) window than the PMV37ENEA (1.3–2.7 V).

### TL3301AF160QJ is listed at LCSC and is Active at E-Switch

§4c said "no LCSC listing" and left lifecycle unverified. Both wrong:

- **Active** at E-Switch per Digi-Key, with an 11-week standard factory lead time.
  Also stocked at Newark, Future, Heisener.
- **It is on LCSC as `C273520`** — poorly stocked, but it exists. The
  well-stocked QG variant is `C273519`.

The QJ/QG distinction holds and is slightly richer than stated: in the TL3301
ordering scheme the two trailing characters are **contact material** (`Q` = silver,
`R` = gold) then **termination** (`J` = J-lead, `G` = gull wing). Same 6×6 mm
switch either way, but J-lead pads tuck under the body and gull-wing pads extend
outward — **not footprint-compatible**.

### "Standardize all three switches" needs a caveat — the height difference is deliberate

| | Body | Actuator height | Force |
|---|---|---|---|
| KSC741J LFS (SW1/SW2) | 6.2 × 6.2 mm | **4.30 mm** | **390 gf** |
| TL3301AF160QJ (SW3) | 6.0 × 6.0 mm | **5.00 mm** | 160 gf |

Upstream's README says SW3 "should be 5mm high to provide clearance," and
separately that "if you are mounting R-Pi Pico with pins you probably want higher
switches (like SW3)." So the taller actuator on SW3 is an intentional mechanical
choice, not an accident of sourcing.

Standardizing is still the cleanest fix for the schematic/PCB mismatch, but pick
the height against your actual build: 5 mm if the Pico is on pin headers or you
want discharge-button clearance through the shield, 4.3 mm if the Pico is
reflowed flat. Both parts are J-lead, so the land pattern is the compatible axis —
that is what upstream's "the footprint is the same" refers to.

Also note the feel difference is large (390 gf vs 160 gf). §4c flagged the heavy
action as a possible safety feature on the arm/trigger buttons; that reading is
supported by the fact that SW1/SW2 got the 390 gf part and the optional discharge
button got the 160 gf one.

### BG306 — two ordering-code details that affect your layout and assembly

Verified against GCT's factory drawing (Rev D3). The part is a **female socket**
(2.54 mm pitch, vertical top-entry, SMT, LCP, phosphor bronze, gold flash),
mating with GCT BG301/303/304/305 pins. 3 A, **500 VAC DWV** — confirming §4c.

Decoding `BG306-02-A-2-0400-L-G`:

- **`-2-` is the R2 land pattern**, not a mounting or gender option. R1 and R2
  differ only in the solder-pad offset relative to pin 1 (mirrored). **R1 is the
  more commonly stocked variant** and is what GCT treats as standard.
  ⚠️ **Verify your J3 pads match R2**, not R1 — this is exactly the kind of thing
  an Altium→KiCad footprint port gets backwards.
- **`-G` is plastic-box bulk packing** (1,000 pcs MOQ), *not* tape and reel.
  Tape-and-reel (`B`) is only offered for 3–8 contacts **and only on the standard
  R1 footprint**. So R2 + reel may not be a stocked combination at all — meaning
  this part cannot be machine-placed as specified regardless of who assembles it.

Both points reinforce §4c's recommendation to move J3 to a wider pitch: you'd be
solving the creepage problem and the packaging problem at the same time.

### S2B-XH-A is side-entry, not vertical

If you add the JST XH battery input: `S2B-XH-A` is **side-entry (right-angle)**
through-hole. **`B2B-XH-A` is the top-entry (vertical) counterpart** — same
family, same 2.5 mm pitch. The `S` vs `B` prefix is exactly this distinction.
3 A, 250 V, −25 to +85 °C.

Pick deliberately: the original board takes the battery pigtail off the edge,
which is what the side-entry part is for.

### Confirmed, no change

- **AO3422**: Active/Production, datasheet Rev 2.1 (March 2024). 55 V, 2.1 A,
  Vgs(th) 0.6/1.3/2.0 V, explicitly rated for 2.5–12 V gate drive. §4c's
  correction to the 30 V figure stands.
- **KSC741J LFS**: Active. SMT **J-bend** (the `J` in the part number is the
  termination option), IP67, 300k cycles, 50 mA @ 32 VDC.

*Caveats from this pass:* aosmd.com 404'd and C&K/Littelfuse returned 403 to
automated fetch, so AO3422 and KSC741J statuses rest on Digi-Key/Mouser plus
current-dated datasheets rather than manufacturer lifecycle pages.

## 4e. Correction — Q2 is also NRND. Two of three critical parts are now on notice.

### RGT16BM65DTL is NRND at ROHM

§4b said "Active — Rohm's product page lists it as Recommended." **That is wrong.**
ROHM's own product page states **"Not recommended for new designs."** Distributors
have not caught up — Digi-Key still shows Active with 8,984 in stock, which is
where the earlier reading came from.

The whole low-current RGT branch is NRND, not just this part:

| Part | Package | Status at rohm.com |
|---|---|---|
| RGT16BM65D | TO-252 / TO-252GE | Not recommended for new designs |
| RGT8BM65D | TO-252GE | Not recommended for new designs |
| RGT16NL65D | LPDL / TO-263L | Not recommended for new designs |
| RGT16NS65D | LPDS / TO-263S | Not recommended for new designs |

**There is no ROHM successor in DPAK.** Reading ROHM's 2024 shortform IGBT
catalog: the TO-252 column across the entire 650 V Field Stop Trench portfolio
contains exactly two parts — RGT8BM65D (4 A) and RGT16BM65D (8 A) — and both are
now NRND. Every newer 650 V family is large-package only and ≥20 A:

- RGTV (tsc 2 µs) — TO-220NFM, TO-247N/GE
- RGS (tsc 8 µs) — TO-220NFM, TO-3PFM
- RGTH / RGW / RGWS (high & ultra-high speed) — TO-247N, TO-247GE

ROHM publishes **no named replacement** — the product page offers only a generic
"Recommended Products Search." No PCN or cross-reference document was found.

Two spec corrections while we're here: **VGES is ±30 V**, not ±20 V (unusually
high, and useful headroom given D7 clamps the gate at 18 V). And RGT is *not* a
high-speed family in ROHM's own taxonomy — it's the 5 µs short-circuit-tolerant
general-inverter series (the fast families are RGW/RGWS/RGTH). At tf 95 ns it's
still fine for this flyback.

### What this means

The upstream README names five parts as "very hard to sub and core to the
design." **Two of them are now NRND**, and they are the two with no drop-in
replacement anywhere:

| Part | Role | Status | Successor |
|---|---|---|---|
| **T1/T2 ATB322524** | HV flyback transformer, ×2 per board | NRND | **none — no vendor, any package** |
| **Q2 RGT16BM65DTL** | Main pulse switch | NRND | none at ROHM in DPAK; other vendors only |
| Q1 LDA111STR | HV sense opto | Active | n/a — but **23-week lead time** |
| D7 MM3Z18VB | Gate clamp | Active | MM3Z18VST1G |
| U1 SC0915 | Pico | Active | Pico 2 pin-compatible |

Both NRND parts still have healthy distributor stock today. Neither is EOL. But
the design has no forward path on either without a vendor change, and one of
them (the transformer) has no equivalent from *anyone* in that footprint.

**Practical stance:** buy Q2 and T1/T2 in quantity now, same as the transformer
advice in §4b. For Q2 specifically, §4b's recommendation to move to
**STGD6M65DF2 (`C472580`)** is now more than a stock workaround — it's the
lifecycle answer too, since ST's part is in full production and ROHM has no DPAK
path forward. Confirm the co-packed antiparallel diode requirement holds.

If you ever do consider a MOSFET instead (upstream says "in theory you can use a
MOSFET, pinout should be compatible"), a 650 V DPAK superjunction part like ROHM
**R6507END3** exists — but that's a real circuit change, not a drop-in: no
co-packed FRD, different tail-current behaviour, different gate drive.

### LDA111STR — confirmed Active, with a supply caveat

Digi-Key: Active, 1,515 in stock, 7,000 factory stock, **23-week manufacturer
lead time**. That lead time is worth treating as a soft supply warning even
though the lifecycle is clean.

Corroborates §4b: it is a **Darlington-output optocoupler**, not an SSR —
Littelfuse files it under Optocouplers → Single Optocouplers. VCEO **30 V**,
100 mA, CTR 300–30,000% @ IF = 1 mA, isolation 3750 Vrms.

New and useful: **turn-on 8 µs, turn-off 345 µs.** That is slow — fine for the
enable/interlock/HV-sense role it actually has, and conclusively useless for
pulse timing. Anyone tempted to repurpose it should know that.

Suffixes: `LDA111` = 6-DIP, `LDA111S` = 6-SMD gull-wing, `LDA111STR` = same on
tape and reel. Littelfuse does **not** cross-reference the OptoMOS SSRs
(CPC1017N, CPC1002N, LCA110) as replacements — those are MOSFET-output relays
with entirely different characteristics.

### ATB322524 — confirmed, with the full family table

| Part | Ratio | L @100 kHz | DCR pri/sec | Leakage | Withstand | Rated I | Size (mm) |
|---|---|---|---|---|---|---|---|
| ATB322515-0110-T000 | 1:10 | 7.0 µH ±20% | 0.5 Ω / 60 Ω | 0.4 µH | 500 Vrms | 0.6 A | 3.2 × 2.5 × **1.55** |
| ATB322524-0110-T000 | **1:10.2** | 7.0 µH ±20% | 0.5 Ω / 60 Ω | 0.4 µH | 500 Vrms | 0.7 A | 3.2 × 2.5 × **2.4** |

That is the entire ATB3225 step-up family — two parts, both NRND. Decode:
`ATB` + `322524` (L×W×T) + `-0110` (turn ratio) + `-T` (taping) + `000`.
No other ratio codes exist.

A Digi-Key forum thread asking this exact question got the reply from Digi-Key
tech support that they could not find an alternative. Nearest functional
relatives are much larger and pin-incompatible: Coilcraft **LPR6235**
(6.2 × 3.5 mm, 1:20/1:50/1:100) and Würth **74488540070/120/250**
(1:100/1:50/1:20) — both need a new footprint and a reworked flyback ratio.

### Verification caveats for this pass

rohm.com was read directly, so the Q2 NRND call is first-hand. But
littelfuse.com and product.tdk.com both returned HTTP 403 to automated fetch, so
the LDA111 and ATB322524 statuses still rest on Digi-Key plus TTI/Octopart
mirroring the manufacturer-declared status, not on manufacturer lifecycle pages.
No TDK PCN or last-time-buy date was found — that needs a direct query to TDK or
a franchised distributor.

## 4f. Corrections — D7 package, diode recovery class, R1 voltage rating

### D7 is SOD-323**F**, 200 mW — your footprint field says `SOD323` ⚠️

Read from the onsemi B-series datasheet: MM3Z18VB is **SOD-323F (SC-90)**, the
**flat-lead** variant, at **200 mW** — not plain SOD-323 at 300 mW. Several
distributor listings state "SOD-323 / 300 mW" sloppily, which is where the wrong
figure in §4b came from.

**SOD-323F and SOD-323 are different land patterns.** Your schematic's Footprint
field is the bare string `SOD323` (already flagged in §2.2 as having no library
prefix) — when you give it a real library reference, make sure it resolves to
**SOD-323F**, not SOD-323.

This also affects the §4b substitute: `MM3Z18VST1G` was described as
"SOD-323, 300 mW." Verify the package of whatever you pick actually matches the
land you draw. Note there is a near-identical Diotec part **MM3Z18** (no `VB`) at
300 mW / ±5% — easy to order by mistake.

Manufacturer is **onsemi**, originally **Fairchild** (onsemi absorbed them in
2016). No genuine alternate manufacturer for this exact MPN was found in
distributor catalogs. **39-week factory lead time** at Digi-Key despite ~369 k in
stock.

### SM4005PL-TP is STANDARD recovery — trr 1000–3000 ns

From MCC's own datasheet: **trr = 1000 ns min / 3000 ns max**. That is
**~15–40× slower** than MURA160T3G or US1J (both 75 ns).

**These are not interchangeable.** If SM4005PL and MURA160/US1J ever end up on
the same BOM line or listed as alternates for each other, that substitution is
only valid for 50/60 Hz line rectification — not in any switching, snubber or
flyback role.

In this design that's tolerable, because §4b established D1/D3/D4/D5 sit on gate
drive lines and battery input rather than the HV path. But it does mean §4b's
suggested **ES1J (trr 35 ns)** is a *faster* part than the original, not an
equivalent one — the closest true functional twin is **S1JFL (`C894229`)**,
standard recovery, SOD-123FL. Either works here; know which you're choosing.

Package confirmed **SOD-123FL** from MCC's package drawing (3.30–3.85 mm overall,
land pattern 0.91 × 1.22 mm on 2.36 mm span). SOD-123FL = DO-219AB = SMF =
S-Flat = "SMAF" are the same flat-lead family.

Nice detail that explains the whole `D_Schottky_Small` confusion in §2.4:
**DSS13U is a real part — an SMC Diode Solutions 30 V 1 A Schottky in SOD-123FL.**
The Altium footprint got its name from a Schottky part that shares the package,
which is very likely how the wrong symbol class propagated into the schematic.

Also: MCC does **not** make a non-PL "SM4005." The `PL` suffix *is* the SOD-123FL
variant. Bare "SM4005" is a generic industry number whose package varies by
vendor — Rectron/Weitron/CDIL ship SMA, but **Diotec's SM4005 is a MELF
(DO-213AB)**. Don't order by the short number.

### R1's `RATED VOLTAGE` property says 400 VDC — the real figure is 2000 V

§2.7 flagged the Altium metadata fields as low-quality. Here's a concrete case:
the `RATED VOLTAGE` property on R1 reads **400VDC**. Vishay's current datasheet
(doc 68043, rev Oct 2024) gives CRMA2010 a **2000 V** maximum working voltage.

At 20 MΩ / 0.5 W the √(P×R) limit is 3162 V, so the part is bound by the 2000 V
ceiling — roughly **4× margin** over the ~490 V it actually sees. §4b's "keep it"
call stands, with even more headroom than stated.

Manufacturer is **Vishay** (sold as Vishay Dale), not Bourns. Active at Digi-Key.
Decode: `CRMA|2010|A` 3-sided term `|F` Ni-barrier `|20M0` `|F` ±1% `|K` 100 ppm
`|E` Sn100 `|F` full reel.

**Correction to §4b's fallback list:** Bourns **CHV2010A** at 20 MΩ is available
**only at ±5%** — its ±1% range stops at 10 MΩ. The §4b suggestion of two 10 MΩ
CHV2010 in series is unaffected (10 MΩ is inside the ±1% range), but don't expect
a single 20 MΩ 1% Bourns part.

Better 1:1 alternates if you ever need one, both 2000 V at 2010:
**Vishay CRHV** (the non-automotive twin of CRMA — same family) and
**KOA Speer HV73** (2000 VDC, 10 kΩ–100 MΩ, ±0.5/1/2/5%).

⚠️ **Do not sub CRCW-HP or RCA.** Those are *anti-surge / high-power* families,
not high-voltage families. CRCW2010's limiting element voltage is 400 V — which
is almost certainly the source of the wrong number in the schematic property.

### Lead times worth planning around

Lifecycle is clean on these, but the factory lead times are long enough to matter
if you order at the wrong moment:

| Part | Ref | Lead time | Note |
|---|---|---|---|
| MM3Z18VB | D7 | **39 weeks** | ~369 k in stock now |
| US1J-13-F | D2 alt | **32 weeks** | **currently out of stock at Digi-Key** |
| LDA111STR | Q1 | 23 weeks | §4e |
| 3522300KFT | R2 | 17 weeks | §4b suggests a cheaper sub anyway |

The US1J stock-out reinforces §4b's recommendation to use **US1M** for D2
instead — it's a Basic part with 503 k in JLC stock, and 1000 V rather than 600 V.

### Confirmed, no change

- **MURA160T3G** — Active, 600 V / 1 A / trr 75 ns / DO-214AC.
- **3522300KFT** — Active, TE/CGS Type 3522 (formerly Holsworthy), 250 V working
  / 500 V max overload. §4b's figures stand.

### Verification caveats for this pass

onsemi.com, mccsemi.com (HTML) and te.com all return HTTP 403 to automated
fetch, so lifecycle status for MURA160T3G, MM3Z18VB, SM4005PL-TP and 3522300KFT
rests on Digi-Key's Active field rather than manufacturer pages. The MCC and
Vishay *datasheets* were read directly, so the package and electrical corrections
above are first-hand. TE's Type 3522 datasheet was never retrieved — the 250 V /
500 V figures come from element14/Newark parametric data, so give that a browser
check if it becomes load-bearing.

## 4g. Corrections — the SMA sub does not fit your footprint; Pico W is not a drop-in

### ⚠️ The only LCSC-stocked SMA is incompatible with the footprint you chose

§4c said Amphenol 132289, Cinch 142-0701-801 and Molex 73251-1150 are "cross-
referenced as interchangeable." **That is wrong for the Molex** — which is a
problem, because the Molex is the *only* one of the three on LCSC (`C841205`),
and your schematic/PCB uses `Connector_Coaxial:SMA_Amphenol_132289_EdgeMount`.

Measured from the KiCad 10 libraries on this machine:

| | Amphenol 132289 | Molex 73251-1150 |
|---|---|---|
| Ground-pad pitch | **8.50 mm** (Y = ±4.25) | **8.76 mm** (Y = ±4.38) |
| Signal pad | 1.5 × 5.08 mm, on centerline | 5.08 × 2.29 mm at X = −1.72 |
| Drilled holes | **none** — pure SMD land | **2 × Ø0.46 mm locating posts** |

Two hard blockers: the ground pitch is 0.26 mm off, and the Molex needs two
drilled locating holes near the board edge that the Amphenol pattern doesn't
have. **Swapping to the Molex requires a board respin**, not just a BOM edit.

**Amphenol 132289 ↔ Cinch 142-0701-801 remains a valid second-source pair** —
both are the classic .375" square-flange end-launch jack for .062" board, and
TE/Linx's own cross-reference guide lists both as equivalents of Linx
`CONSMA003.062-L`. Neither is on LCSC.

All three accept 1.57 mm / .062" board, so PCB thickness is not the
differentiator — the land pattern is.

**Practical consequence:** you have three options, none of which is "order
`C841205` and move on":
1. Keep the Amphenol/Cinch footprint and **consign** the connector (it's
   hand-soldered either way — see below).
2. Use **JLCPCB's own in-house SMA `C9900107125`** (package TH-5P, wave
   soldering, Economic + Standard tiers) and draw its footprint.
3. Respin the J6 land for the Molex, accepting the two extra drill hits.

*Caveat:* Amphenol's and Molex's own drawing PDFs both 403'd, so these
dimensions come from the KiCad library footprints (which cite those drawings)
plus the Cinch drawing, which was read directly. **Verify against manufacturer
drawings before committing to fab** if you plan to second-source across them.

### JLCPCB cannot machine-place any edge-mount SMA — confirmed as far as it can be

JLC's own SMA (`C9900107125`) is listed as package **TH-5P, assembly method
"Wave Soldering."** `CON-SMA-EDGE-S` (`C5356059`) is Standard-PCBA only. No
official statement says any edge-mount SMA is machine-placed, and all evidence
points to the manual path.

Concrete cost of the through-hole/manual path: **$3.50 hand-soldering fee +
$0.0173 per joint**, and **+1 day** on SMT time. JLC's T&Cs warn that "there will
be some risk since the secondary processing is all carried out manually."

Also relevant if you consign: consigned parts "will not be tested regarding
quality or function before or after PCBA production," and JLC disclaims
responsibility for defects traced to them. And JLC only assembles boards it also
fabricated.

### ⚠️ Pico W / Pico 2 W are footprint-compatible but NOT pin-function compatible

§4c listed Pico 2 W (`C42394205`) among the LCSC options without qualification.
**Do not treat a W board as a drop-in.** On the wireless variants the four
housekeeping GPIOs are reassigned to the CYW43439 radio:

| GPIO | Pico / Pico 2 | Pico W / Pico 2 W |
|---|---|---|
| 23 | SMPS power-save control | **WL_ON** |
| 24 | VBUS sense | **WL_D** |
| 25 | user LED | **WL_CS** |
| 29 | ADC3 / VSYS÷3 | **WL_CLK** (shared) |

The user LED moves to the radio chip (WL_GPIO0), and reading VSYS requires
cooperating with the SPI bus to the radio. Part numbers: Pico W = SC0918,
Pico 2 W = SC1633.

### Pico 2 (SC1631) confirmed a genuine drop-in — my §4c flag resolved

Verified against the official Pico 2 datasheet: same 51 × 21 mm × 1 mm board,
same 40-pin castellated + 2.54 mm THT layout, same 4 × 2.1 mm mounting holes,
same 26 exposed GPIO with 3 ADC — and critically **GPIO23/24/25/29 keep their
Pico 1 functions**, which is the thing that usually breaks these swaps.
Raspberry Pi lists "Hardware and software compatibility with Raspberry Pi Pico 1"
as a Pico 2 feature.

**Longevity commitments, verbatim from the datasheets:**
- Pico 1 series (SC0915, SC0918): **"will remain in production until at least
  January 2036"**
- Pico 2: **"guarantee availability … until at least January 2040"**

SC0915 is Active at Digi-Key (~45.8 k stock, 18-week lead). So there's no
lifecycle pressure to move — but if you do, SC1631 is clean.

Two caveats carried forward: **no JLCPCB part number was found for the plain
Pico 2 (SC1631)** — Pico, Pico H, Pico W and Pico 2 W all have C-numbers, but the
non-W Pico 2 didn't surface. And the **RP2350 GPIO-input errata** remains
unverified — a firmware concern, not a footprint one, but worth checking for a
tool that reads GPIO.

### Red LED obsolescence confirmed, with the manufacturer's own substitute

Digi-Key status on APT1608SRCPRV: **"Obsolete and no longer manufactured,"** and
Digi-Key names **APT1608SURCK** as the substitute. §4c's finding stands.

Useful for matching the replacement: the original is Vf **1.85 V typ / 2.5 V max**
at 20 mA, λdom 640 nm, 150° viewing angle. The `C2286` KT-0603R recommended in
§4c (Vf 1.8–2.4 V) is a good electrical match.

Green APT1608CGCK is **Active** (7-week lead), Vf **2.1 V typ**, λdom 570 nm — so
§4c's Vf-matching argument for `C965805` (2.2 V) is sound.

### Both capacitors are Active — the §4c swaps are for stock, not lifecycle

- **TDK C2012X5R1H475K125AB**: Active, 24-week lead. Not an EOL problem — §4c's
  substitution is purely because LCSC doesn't stock it.
- **KEMET C0603C104K5RACTU**: Active, ~6.7 M in stock, 12-week lead. Lowest-risk
  part on the board.

⚠️ **DC bias on C1/C2 is worth taking seriously.** A 4.7 µF 50 V X5R in an 0805
at ~1.25 mm thickness is near the physical limit for that dielectric volume, and
Class-II ceramics lose capacitance steeply under DC bias. TDK publishes a DC Bias
curve for this exact P/N, but **product.tdk.com 403'd, so no numeric derating was
obtained — do not accept a percentage figure without pulling that curve
yourself** (TDK's MLCC product centre / SEAT tool has it interactively). If you
need real 4.7 µF at working voltage, measure at bias, move to 1206, or
overspecify. This applies equally to the Samsung substitute in §4c.

## 5. Housekeeping

- `chipshouter-pico-mcu.kicad_sch` (1.1 MB) is orphaned — the project references
  only the flat top sheet. It still contains stale duplicates of D1, R11–R13,
  SW1, SW2, U1. Delete it or it will be mistaken for live design data.
- `production/` is a stale 2026-07-23 export of the pre-migration board.
- **The project is not under version control.** `.history/` is VS Code local
  history, not a repo. A migration of this scope without git is the single
  highest-risk thing here.
