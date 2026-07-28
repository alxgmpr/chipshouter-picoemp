#!/usr/bin/env python3
"""Regenerate the Hammond shield 3D models from Hammond's published STEP files.

Hammond's 3D models are not covered by this project's licence, so the STEPs are
gitignored rather than committed. Run this after cloning if you want the shield
to appear in the 3D viewer:

    uv run --with cadquery tools/fetch_hammond_shield_model.py

Two candidate shields, built differently:

  1551B  two symmetric snap-together halves; the top half is the shield and is
         used as moulded. Interior clear height above the board 5.80 mm.
  1551G  box + lid held by two #4 screws; the deep box is the shield and is used
         upside down, lid discarded. Interior clear height 15.05 mm.

Both are re-axed into KiCad's 3D-model frame so the footprints need no offset or
rotation: model X runs across the board, model Y along it, model Z up, with the
face that meets the PCB at Z = 0.
"""

import io
import pathlib
import sys
import urllib.request
import zipfile

MODELS = pathlib.Path(__file__).resolve().parent.parent / "lib" / "models"

# output name: (archive url, component-name substring, axis matrix)
# The axis matrix maps the Hammond frame onto KiCad's. Both have determinant +1;
# a determinant of -1 would mirror the part rather than rotate it.
PARTS = {
    "Hammond_1551B_Top.step": (
        "https://www.hammfg.com/files/parts/stp/1551BTRD.zip", "top",
        (0, 0, 1, 1, 0, 0, 0, 1, 0),
    ),
    "Hammond_1551G_Box.step": (
        "https://www.hammfg.com/files/parts/stp/1551GTBU.zip", "box",
        (0, 1, 0, 1, 0, 0, 0, 0, -1),
    ),
}


def fetch(url):
    # hammfg.com 403s the stock urllib agent string
    request = urllib.request.Request(url, headers={"User-Agent": "curl/8.7.1"})
    with urllib.request.urlopen(request, timeout=60) as resp:
        archive = zipfile.ZipFile(io.BytesIO(resp.read()))
    (name,) = [n for n in archive.namelist() if n.lower().endswith((".stp", ".step"))]
    return archive.read(name)


def pick_shape(path, want):
    """Return the shield half, by assembly component name where the STEP has one."""
    from OCP.STEPCAFControl import STEPCAFControl_Reader
    from OCP.STEPControl import STEPControl_Reader
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.TDataStd import TDataStd_Name
    from OCP.TDF import TDF_Label, TDF_LabelSequence
    from OCP.TDocStd import TDocStd_Document
    from OCP.TopAbs import TopAbs_SOLID
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS
    from OCP.XCAFApp import XCAFApp_Application
    from OCP.XCAFDoc import XCAFDoc_DocumentTool

    app = XCAFApp_Application.GetApplication_s()
    doc = TDocStd_Document(TCollection_ExtendedString("d"))
    app.NewDocument(TCollection_ExtendedString("MDTV-XCAF"), doc)
    reader = STEPCAFControl_Reader()
    reader.SetNameMode(True)
    reader.ReadFile(str(path))
    reader.Transfer(doc)
    tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())

    def label_name(label):
        attr = TDataStd_Name()
        if label.FindAttribute(TDataStd_Name.GetID_s(), attr):
            return attr.Get().ToExtString().lower()
        return ""

    free = TDF_LabelSequence()
    tool.GetFreeShapes(free)
    for i in range(1, free.Length() + 1):
        parts = TDF_LabelSequence()
        tool.GetComponents_s(free.Value(i), parts)
        for j in range(1, parts.Length() + 1):
            component = parts.Value(j)
            referred = TDF_Label()
            if not tool.GetReferredShape_s(component, referred):
                continue
            if want in label_name(component):
                return tool.GetShape_s(component)

    # 1551F/G ship the halves as bare solids; the box is the first and largest
    reader = STEPControl_Reader()
    reader.ReadFile(str(path))
    reader.TransferRoots()
    explorer = TopExp_Explorer(reader.OneShape(), TopAbs_SOLID)
    if explorer.More():
        return TopoDS.Solid_s(explorer.Current())
    return None


def main() -> int:
    try:
        from OCP.Bnd import Bnd_Box
        from OCP.BRepBndLib import BRepBndLib
        from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
        from OCP.gp import gp_Trsf, gp_Vec
        from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
    except ImportError:
        print("needs OCCT bindings; run with:  uv run --with cadquery " + __file__, file=sys.stderr)
        return 1

    for name, (url, want, matrix) in PARTS.items():
        print(f"fetching {url}")
        scratch = MODELS / f"_{name}.tmp.stp"
        scratch.write_bytes(fetch(url))
        shape = pick_shape(scratch, want)
        if shape is None:
            print(f"  no '{want}' half in the archive", file=sys.stderr)
            scratch.unlink()
            return 1

        # Rotate first, then centre. Doing it the other way needs to know which
        # Hammond axis is "up", and that differs between the two parts -- the
        # 1551B's datum is its parting plane (Hammond Y = 0), the 1551G's is its
        # rim (box Z = 0). Both land on model Z = 0 once the matrix is applied,
        # so afterwards only X and Y need centring.
        axes = gp_Trsf()
        axes.SetValues(matrix[0], matrix[1], matrix[2], 0,
                       matrix[3], matrix[4], matrix[5], 0,
                       matrix[6], matrix[7], matrix[8], 0)
        shape = BRepBuilderAPI_Transform(shape, axes, True).Shape()

        # Draft-angled walls are cones, and the default bounding box takes their
        # untrimmed extent -- AddOptimal is needed or the box reads ~127 mm tall.
        bbox = Bnd_Box()
        BRepBndLib.AddOptimal_s(shape, bbox, True, False)
        cx = (bbox.CornerMin().X() + bbox.CornerMax().X()) / 2
        cy = (bbox.CornerMin().Y() + bbox.CornerMax().Y()) / 2

        centre = gp_Trsf()
        centre.SetTranslation(gp_Vec(-cx, -cy, 0))
        shape = BRepBuilderAPI_Transform(shape, centre, True).Shape()

        out = Bnd_Box()
        BRepBndLib.AddOptimal_s(shape, out, True, False)
        writer = STEPControl_Writer()
        writer.Transfer(shape, STEPControl_AsIs)
        writer.Write(str(MODELS / name))
        scratch.unlink()
        print(f"  wrote {name}  "
              f"X[{out.CornerMin().X():.2f},{out.CornerMax().X():.2f}] "
              f"Y[{out.CornerMin().Y():.2f},{out.CornerMax().Y():.2f}] "
              f"Z[{out.CornerMin().Z():.2f},{out.CornerMax().Z():.2f}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
