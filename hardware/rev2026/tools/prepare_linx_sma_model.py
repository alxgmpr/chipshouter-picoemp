#!/usr/bin/env python3
"""Re-axe TE/Linx CONSMA020.062-G's STEP into KiCad's 3D-model frame.

TE ships L9000279-01.STEP with the connector axis along Z, tail tip at Z=0 and
the coupling nut at Z=-14.2, flange 9.52 (X) x 7.92 (Y). KiCad wants X across
the board, Y = minus the footprint Y, Z up from the board's top surface.

    model X = STEP Z + 4.700   (flange face -> footprint origin at the board edge)
    model Y = STEP X
    model Z = STEP Y - 0.785   (connector axis sits at mid-thickness of a 1.57 mm board)

Determinant is +1, so this rotates rather than mirrors.

KNOWN GAP: the transform below is not quite right -- the connector comes out
reversed along its own axis and 0.5 mm high. The footprint compensates in its
(model ...) block with offset (-5, 0, -0.5) and 180 degrees about Y, verified in
KiCad's 3D viewer. If you correct the maths here, zero those out at the same
time or the correction will apply twice.

Run with the vendor zip already unpacked somewhere and pass the .STEP path:

    uv run --with cadquery tools/prepare_linx_sma_model.py L9000279-01.STEP
"""
import pathlib
import sys

DEST = pathlib.Path(__file__).resolve().parent.parent / "lib" / "models" / "SMA_Linx_CONSMA020_062_G.step"
TAIL_TO_FLANGE = 4.700
HALF_BOARD = 0.785


def main() -> int:
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    from OCP.gp import gp_Trsf, gp_Vec
    from OCP.STEPControl import STEPControl_AsIs, STEPControl_Reader, STEPControl_Writer

    src = sys.argv[1]
    reader = STEPControl_Reader()
    reader.ReadFile(src)
    reader.TransferRoots()
    shape = reader.OneShape()

    axes = gp_Trsf()
    axes.SetValues(0, 0, 1, 0,
                   1, 0, 0, 0,
                   0, 1, 0, 0)
    shape = BRepBuilderAPI_Transform(shape, axes, True).Shape()
    move = gp_Trsf()
    move.SetTranslation(gp_Vec(TAIL_TO_FLANGE, 0, -HALF_BOARD))
    shape = BRepBuilderAPI_Transform(shape, move, True).Shape()

    box = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape, box, True, False)
    writer = STEPControl_Writer()
    writer.Transfer(shape, STEPControl_AsIs)
    writer.Write(str(DEST))
    print(f"wrote {DEST.name}  "
          f"X[{box.CornerMin().X():.2f},{box.CornerMax().X():.2f}] "
          f"Y[{box.CornerMin().Y():.2f},{box.CornerMax().Y():.2f}] "
          f"Z[{box.CornerMin().Z():.2f},{box.CornerMax().Z():.2f}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
