# Open issues — Rev-2026

Known-imperfect things in the current design. Both gates pass
(90 tests; DRC 0 violations, 0 unconnected, 0 schematic-parity issues), so
nothing here is a DRC failure — these are the problems no rule models.

Last reviewed 2026-08-08.

---

## Layout

**`MH1`'s screw head clears `R5` by 0.090 mm.** MH1 is at (136.140, 126.022); a
#4 head (≈2.75 mm radius) reaches to within 0.090 mm of `R5`'s nearest pad edge
and 0.344 mm of `D4`'s. Measured pad-rectangle edge to hole centre, so this is
real geometry, not a courtyard approximation. `R5` is the one to move. No DRC
rule models a screw head.

**Three parts intrude on the shield's rim band.** The rim contacts across the
2.635 mm wall band with a chamfer inboard. Measured as courtyard bounding box
against the nominal interior rectangle — **the chamfer is not modelled**, so
intrusions under ~0.6 mm may well clear in reality:

| Part | Side | Intrusion |
|---|---|---|
| `R6` | north | 0.912 mm |
| `C3` | south | 0.803 mm |
| `D3` / `D4` / `D5` | north | 0.257 mm each |
| `J5` | north | grazes the outer face by 0.148 mm |
| `J1` | south | full wall depth — the intended SMA pass-through, matching the silk gap |

`R6` and `C3` are the two worth moving. Everything else clears, including `Q2`
(1.327 mm), `J4` (1.095), `Q1` (2.243) and `SW3` (6.717).

**Mounting-hole size mismatch.** The MH footprints are `MountingHole_3.2mm_M3`,
sized for M3, but the 1551G takes #4 screws. Reconcile before ordering hardware.

**Two conflicting revision stamps on silk.** `"PicoEMP 2026 / Alex Gompper /
Rev B 3.8.2026"` at (143.2, 99.3) and `"… Rev B 28.7.2026"` at (123.9, 89.8).
Same revision, different dates. One should go.

---

## Parts

**`SW3` stands off ~246 V on a switch rated 50 mA @ 12 VDC.** On the board this
is fine — its contacts are 3.100 mm apart in copper. The open question is the
TL3301's *internal* dielectric strength across open contacts, which is a part
spec. There is no TL3301 datasheet in this repo, only a STEP model, so this is
**unverified**. Inherited from upstream REV04, not introduced by this port.

**`J5` / `J6` have no MPN.** Generic 2.54 mm headers, normally bought as a strip
and cut. A BOM export needs a distributor line for them.

**`J4` has no creepage slot.** The plan called for a routed slot between its two
HV pads. Not done — the 5.08 mm Phoenix MKDSN part gives 2.480 mm pad-to-pad,
which is the documented fallback ("wider pad separation"). Adequate at 246 V.
Its schematic `BOM Comments` field may still say "Milled slot between pads",
which is stale.

---

## Verification gaps

**The rail voltage is approximate, not qualified.** ~261 V is derived from a
loaded divider measurement with an assumed 10 MΩ meter input, not read directly.
The result is sensitive to that assumption — the same 250 V reading at 1 MΩ
input would imply a 329 V rail. A proper HV probe would settle it. See
[bringup.md](bringup.md), Phase 4.

**Pulsing has never been exercised.** No injection tip was available during
bring-up. Suggested parts: Würth `744710603` inductor plus a `CONSMA013.062`
edge-mount SMA male — see [`hardware/injection_tips/`](../../injection_tips/).

**The trigger front-end is only half tested.** §5.3 passes on board #1: the
buffered path from the header through `R14` and `U2` to GP0 carries DC, slow
edges and short pulses. Everything entering through the **SMA** is untested, as
are the DC levels (§5.1) and the Schmitt trip points (§5.2).

**No shipped firmware reads GP0.** `cspico_simple.py`, `bringup.py` and
`chargetest.py` all ignore it, so the trigger does nothing on a board running
stock firmware.

**Phase 1's 0.87 mA supply draw was never explained.** The cross-check with
MicroPython running was not taken. Probably DMM burden voltage; unconfirmed.

---

## Upstream defects, not fixed here

**`cspico_simple.py` misreads `CHARGED`.** The net reaches two RP2040 pads —
GP18 (U1.24) and GP26/ADC0 (U1.31) — and the RP2040 resets every pad with its
pull-down enabled. Upstream configures GP18 only, leaving GP26's ~65 kΩ
pull-down on the net; two pull-downs against `R6`'s 22 kΩ pull-up divide it to
roughly 2 V, inside the indeterminate band (VIL 0.99 V, VIH 2.31 V). The failure
mode is a spurious "charged" at rest.

This port does not modify upstream firmware. `bringup.py` and `chargetest.py`
configure both pads and read `CHARGED` as a voltage rather than a logic level.
The defect did not manifest on board #1 under stock firmware.

---

## ERC

**1 warning:** `unconnected_wire_endpoint` at (318.77 mm, 236.22 mm) — a
dangling 1.27 mm horizontal wire stub. Harmless, but it is the only thing
between here and a clean ERC.
