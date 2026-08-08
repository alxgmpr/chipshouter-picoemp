# PicoEMP Rev-2026 documentation

| Document | What's in it |
|---|---|
| [design-notes.md](design-notes.md) | Why the board is built this way — the isolation barrier, the shield, circuit topology, and the traps worth knowing before you edit anything |
| [bringup.md](bringup.md) | What was measured on the first assembled board, phase by phase, including two defects found along the way |
| [open-issues.md](open-issues.md) | What is still wrong or unverified |

Primary sources live outside this folder:

| What | Where |
|---|---|
| **Upstream REV04 schematic (authoritative for topology)** | [`hardware/SCH-PICOEMP-REV04.PDF`](../../SCH-PICOEMP-REV04.PDF) |
| Upstream build drawing | [`hardware/BUILD-DRAWING-REV04.PDF`](../../BUILD-DRAWING-REV04.PDF) |
| Design rules, heavily commented | [`../picoemp-rev2026.kicad_dru`](../picoemp-rev2026.kicad_dru) |
| Firmware (charge voltage is set here) | [`firmware/micropython/`](../../../firmware/micropython/) |
| Datasheets | [`hardware/datasheets/`](../../datasheets/) |

## Safety

This board charges a capacitor to roughly 250 V and discharges it through a
coil. Read the safety notes in the [root README](../../../README.md) before
building or powering one. Every `HV_*` net is live except `HVPULSE` and
`HVPWM`, which are ≤4 V logic despite the prefix.

The capacitor holds charge after power is removed. `SW3` discharges it through
`R2` with τ = 141 ms; confirm it is down before handling the board.
