# ⚠️ Incomplete REV04 → KiCad migration — do not use as a reference

This directory is an **abandoned, in-progress** import of the upstream REV04
Altium design into KiCad. It is kept for history only.

**It has at least one known wiring error.** In the HV sense section, `R1`'s
lower lead lands on `HV_RTN` and `Q1` pin 1 floats, because the Altium import
flattened a wire hop into a junction. The sense chain is therefore wrong.

Its `audit/AUDIT.md` §4b also states the sense chain as "HV → R1 → Q1 LED → R2 →
GND". That is wrong too — the real order puts `R2` first.

## Where to look instead

| For | Use |
|---|---|
| **Ground truth on circuit topology** | [`../../SCH-PICOEMP-REV04.PDF`](../../SCH-PICOEMP-REV04.PDF) |
| A working KiCad version of this board | [`../../rev2026/`](../../rev2026/) |
| The original Altium sources | [`../`](../) |

The correct sense chain is:

```
HV_RAIL → R2 (300K) → HV_SENSE → R1 (20M) → Q1 LED → HV_RTN
```
