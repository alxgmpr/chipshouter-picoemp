# Fabrication outputs

Generated from `picoemp-rev2026.kicad_pcb` / `.kicad_sch` at the current
`rev2026` HEAD, **2026-08-08**, with KiCad 10 `kicad-cli`.

These outputs use **Rev B designators** — `J3` is the trigger SMA, `J4` is the
HV terminal block, `J5`/`J6` are the two headers. Anything labelled `P1`/`P2`/`P3`
predates Rev B and is wrong.

| File | What |
|---|---|
| `gerbers/` | 9 fab layers + PTH/NPTH Excellon drill and drill maps, plus the `.gbrjob` |
| `picoemp-rev2026-gerbers.zip` | the same, zipped for upload |
| `bom.csv` | 31 lines, 46 placed parts, with MPN / Manufacturer / DigiKey and a DNP column |
| `positions.csv` | 52 entries — 46 parts + 3 mounting holes + 3 fiducials |
| `netlist.ipc` | IPC-D-356 netlist for bare-board electrical test |

## ⚠️ Before ordering

- **`R16` is DNP** — a 0 Ω bypass across the trigger buffer. The `DNP` column in
  `bom.csv` flags it. Fitting it puts the unbuffered trigger node straight onto
  GP0.
- **Review the gerbers in KiCad's Gerber Viewer, including the drill file,
  before you order.** Nobody has fabbed from *these* files yet; board #1 was
  built from an earlier, different layout.
- **Read [`../docs/open-issues.md`](../docs/open-issues.md) first.** Several
  known-imperfect items are not DRC violations and will not show up in any
  automated check — in particular `MH1`'s screw head clearing `R5` by 0.090 mm,
  and three parts intruding on the shield's rim band.
- **`J5` and `J6` have no MPN.** Generic 2.54 mm headers, cut from a strip.
- **Mounting holes are `MountingHole_3.2mm_M3` but the 1551G shield takes #4
  screws.** Reconcile before ordering hardware.

## Regenerating

Run from `hardware/rev2026/`. `kicad-cli` must run **in place** — `${KIPRJMOD}`
stops resolving elsewhere and the footprint library goes missing.

```bash
KC=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
rm -rf production/gerbers && mkdir -p production/gerbers
$KC pcb export gerbers --layers F.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,Edge.Cuts --output production/gerbers/ picoemp-rev2026.kicad_pcb
$KC pcb export drill --format excellon --excellon-separate-th --generate-map --map-format gerberx2 --output production/gerbers/ picoemp-rev2026.kicad_pcb
$KC pcb export pos --format csv --units mm --side both --use-drill-file-origin --output production/positions.csv picoemp-rev2026.kicad_pcb
$KC sch export bom --fields 'Reference,Value,Footprint,MPN,Manufacturer,DigiKey,${DNP},${QUANTITY}' --labels 'Refs,Value,Footprint,MPN,Manufacturer,DigiKey,DNP,Qty' --group-by Value,Footprint,MPN --output production/bom.csv picoemp-rev2026.kicad_sch
$KC pcb export ipcd356 --output production/netlist.ipc picoemp-rev2026.kicad_pcb
(cd production && rm -f picoemp-rev2026-gerbers.zip && zip -qj picoemp-rev2026-gerbers.zip gerbers/*)
```

## Not generated here

- **JLCPCB-format BOM/CPL with an `LCSC Part #` column** come from the
  Fabrication Toolkit KiCad plugin, not `kicad-cli`. Its settings are in
  [`../fabrication-toolkit-options.json`](../fabrication-toolkit-options.json).
  Run it from the KiCad GUI if you want JLCPCB assembly.
- **`bom/ibom.html`**, the interactive HTML BOM, comes from the
  InteractiveHtmlBom plugin and is gitignored as a regenerable artifact.
  Regenerate it after any designator change — the copy that used to sit in this
  repo predated Rev B and showed the old `P1`/`P2`/`P3` names.
