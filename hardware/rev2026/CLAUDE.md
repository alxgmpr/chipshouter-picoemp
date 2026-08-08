# PicoEMP Rev-2026 — KiCad project

A KiCad 10 port and rework of the ChipShouter-PicoEMP REV04 EM fault-injection
board. Two layers, 1.6 mm, 52 footprints, 52 schematic components, 64 nets.

The board makes ~250 V on a 0.47 µF capacitor and dumps it through an IGBT into
an injection coil. Treat every `HV_*` net as live — **except `HVPULSE` and
`HVPWM`, which are ≤4 V logic** despite the prefix and are deliberately not in
the `HV` netclass.

**Read [`docs/`](docs/) before doing design work.** This file is orientation and
process; the engineering content lives there.

| | |
|---|---|
| [`docs/design-notes.md`](docs/design-notes.md) | Isolation barrier, shield, topology, layout traps |
| [`docs/bringup.md`](docs/bringup.md) | Measured results from board #1 |
| [`docs/open-issues.md`](docs/open-issues.md) | What's still wrong — check here before reporting a problem |
| **[`../SCH-PICOEMP-REV04.PDF`](../SCH-PICOEMP-REV04.PDF)** | **Authoritative for topology.** When in doubt, read the PDF |

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

Any note or analysis written before 2026-08-05 uses the old names. `J1` (HV
output SMA) and `J2` (power input) did not move.

`kicad-cli pcb drc --schematic-parity` reported **0 issues throughout** while the
design was fully scrambled. It is not a safety net for this failure mode.

**2. All Y coordinates in notes older than 2026-08-05 are 25.400 mm low.** The
board sits at y = 45.272 … 175.272 today. Anything quoting y ≈ 19.872 … 149.872
predates the shift — add 25.400. X is unchanged.

---

## Gates

Both must pass before fab output. Run them from this directory.

```bash
uv run --with pytest pytest tests/
```

```bash
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli pcb drc --severity-error --schematic-parity --exit-code-violations -o /tmp/drc.rpt picoemp-rev2026.kicad_pcb
```

Verified **2026-08-08**: **90 tests pass**; DRC reports **0 violations, 0
unconnected, 0 schematic-parity issues**, exit code 0.

**DRC warnings are empty too.** Run the same command without `--severity-error`
and you still get zero. If you see any DRC warning, you introduced it.

**ERC is not clean: 1 warning** — see [`docs/open-issues.md`](docs/open-issues.md).

`kicad-cli pcb drc` run on a copy outside this directory reports nonsense —
`${KIPRJMOD}` stops resolving. Always run it in place.

---

## Conventions

- Python via `uv` only (`uv run --with pytest pytest`), never bare `pip`.
- Symbols and footprints resolve as `picoemp:<name>` from `lib/` via
  `${KIPRJMOD}`. Keep project-local; do not depend on system libraries.
- BOM fields are normalised to `MPN` / `Manufacturer` / `DigiKey`.
  `tools/normalize_fields.py` sets and adds properties but does not delete them.
- `out/`, `analysis/`, `__pycache__/` and `.pytest_cache/` are gitignored.
  Analysis output is regenerable — safe to delete, not worth committing.
- Hammond's 3D models are gitignored (not under this project's licence);
  `tools/fetch_hammond_shield_model.py` re-downloads and re-axes them.

## Related work in this repo

Two branches carry work that is deliberately not on `rev2026`. Neither passes
the gates; both are parked rather than abandoned.

- **`feat/isolated-hv-sense`** — an AMC3336 + TLP170J block for calibrated
  isolated rail measurement, 16 parts. `U4` has no footprint and nothing is
  placed on the PCB.
- **`feat/hv-loop-return-plane`** — a solid `HV_RTN` pour on B.Cu (~142 mm²)
  under the C3/Q2/J1 forward traces, to cut discharge-loop inductance by letting
  the return current image the go current across the dielectric instead of
  enclosing a large coplanar loop. The current board has **no** such pour: its
  200 zones are 197 teardrops, the `MCU GND Pour`, and two `Pad Keep Out TP7`
  keepouts. Branched off before Rev B, so it needs rebasing.

**`../altium_src/kc/` is a separate, incomplete REV04 migration, not this
project.** Its HV sense section is wired wrong. Do not use it as a reference —
see its README.
