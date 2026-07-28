#!/usr/bin/env python3
"""Regenerate lib/models/Hammond_1551B_Top.step from Hammond's published STEP.

Hammond's 3D models are not covered by this project's licence, so the STEP is
gitignored rather than committed. Run this once after cloning if you want the
shield to appear in the 3D viewer:

    uv run --with cadquery tools/fetch_hammond_shield_model.py

The 1551B assembly ships as bottom half + top half + two screws. Only the top
half is used here -- it is the safety shield. The model is re-axed into KiCad's
3D-model frame so the footprint needs no offset or rotation:

    model X = Hammond Z   (across the board, the 25 mm axis)
    model Y = Hammond X   (along the board, the 50 mm axis; screw end at +Y)
    model Z = Hammond Y   (up; parting plane at Z = 0)
"""

import io
import pathlib
import sys
import urllib.request
import zipfile

URL = "https://www.hammfg.com/files/parts/stp/1551BTRD.zip"
DEST = pathlib.Path(__file__).resolve().parent.parent / "lib" / "models" / "Hammond_1551B_Top.step"


def main() -> int:
    try:
        from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
        from OCP.gp import gp_Trsf
        from OCP.STEPCAFControl import STEPCAFControl_Reader
        from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
        from OCP.TCollection import TCollection_ExtendedString
        from OCP.TDataStd import TDataStd_Name
        from OCP.TDF import TDF_LabelSequence
        from OCP.TDocStd import TDocStd_Document
        from OCP.XCAFApp import XCAFApp_Application
        from OCP.XCAFDoc import XCAFDoc_DocumentTool
    except ImportError:
        print("needs OCCT bindings; run with:  uv run --with cadquery " + __file__, file=sys.stderr)
        return 1

    print(f"fetching {URL}")
    # hammfg.com 403s the stock urllib agent string
    request = urllib.request.Request(URL, headers={"User-Agent": "curl/8.7.1"})
    with urllib.request.urlopen(request, timeout=60) as resp:
        archive = zipfile.ZipFile(io.BytesIO(resp.read()))
    (name,) = [n for n in archive.namelist() if n.lower().endswith((".stp", ".step"))]
    scratch = DEST.parent / "_1551BTRD_full.stp"
    scratch.write_bytes(archive.read(name))

    app = XCAFApp_Application.GetApplication_s()
    doc = TDocStd_Document(TCollection_ExtendedString("d"))
    app.NewDocument(TCollection_ExtendedString("MDTV-XCAF"), doc)
    reader = STEPCAFControl_Reader()
    reader.SetNameMode(True)
    reader.ReadFile(str(scratch))
    reader.Transfer(doc)

    tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    free = TDF_LabelSequence()
    tool.GetFreeShapes(free)
    parts = TDF_LabelSequence()
    tool.GetComponents_s(free.Value(1), parts)

    def label_name(label):
        attr = TDataStd_Name()
        if label.FindAttribute(TDataStd_Name.GetID_s(), attr):
            return attr.Get().ToExtString()
        return ""

    top = None
    for i in range(1, parts.Length() + 1):
        component = parts.Value(i)
        if "top" in label_name(component):
            top = tool.GetShape_s(component)
    if top is None:
        print("no '1551B top' component in the archive", file=sys.stderr)
        return 1

    trsf = gp_Trsf()
    trsf.SetValues(0, 0, 1, 0,
                   1, 0, 0, 0,
                   0, 1, 0, 0)
    shape = BRepBuilderAPI_Transform(top, trsf, True).Shape()

    writer = STEPControl_Writer()
    writer.Transfer(shape, STEPControl_AsIs)
    writer.Write(str(DEST))
    scratch.unlink()
    print(f"wrote {DEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
