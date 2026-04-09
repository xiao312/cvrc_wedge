#!/usr/bin/env python3
"""
CVRC Mesh Generator (no slots) — single script: geometry → slab .msh

Builds the 2D CVRC profile, meshes it, extrudes to a 1-cell slab,
and writes a Gmsh .msh ready for gmshToFoam + extrudeMesh.

Usage:
    python3 generate_mesh.py
    # Then in OpenFOAM:
    gmshToFoam cvrc_slab.msh
    transformPoints -scale "(0.001 0.001 0.001)"
    extrudeMesh
"""

import gmsh
import os
import math
from collections import defaultdict

# ─── Parameters ───────────────────────────────────────────────────────
EPS = 0.001  # mm, axis offset

# Geometry (mm)
X_INLET    = -160.0   # oxidizer inlet face
X_INJ_FACE = -140.0   # injector face (step from axis to passage)
X_POST_END = -10.16   # end of oxidizer post / backstep
X_FUEL     = -30.0    # fuel pipe entrance
X_CHAM_0   = 0.0
X_CHAM_20  = 20.0
L_C        = 381.0    # chamber length

R_AXIS     = 3.0      # axis passage radius (below injector face step)
R_OX_TOP   = 10.235   # top of oxidizer passage
R_STEP     = 11.0     # fuel pipe outer radius
R_RECESS   = 11.53    # fuel pipe inner radius (recess)
R_CHAMBER  = 22.5     # chamber outer radius

# Nozzle
NOZZLE_P51 = (399.5, EPS)
NOZZLE_P52 = (397.5, 11.0)
NOZZLE_P53 = (381.0, 20.0)
NOZZLE_C1  = (385.0, 8.0)     # BSpline control point (inside)
NOZZLE_C2  = (401.0, 6.5)     # BSpline control point (outside)

# Mesh counts
NX_INLET       = 17    # x: -160 to -140
NX_PASSAGE     = 18    # x: -140 to -128 (merged old slot_strip + right_local)
NX_POST        = 50    # x: -128 to -10.16
NX_FUEL        = 31    # x: -30 to -10.16
NX_RECESS      = 17    # x: -10.16 to 0
NX_CONN        = 17    # x: 0 to 20
NX_CHAMBER     = 120   # x: 20 to 381

NY_AXIS        = 13    # y: eps to 3.0
NY_OX_PASSAGE  = 38    # y: 3.0 to 10.235
NY_MID_VERT    = 49    # y: eps to 10.235
NY_FUEL_OUTER  = 4     # y: 10.235 to 11.0
NY_FUEL_INNER  = 4     # y: 11.0 to 11.53
NY_UPPER       = 35    # y: 11.53 to 22.5

# Characteristic lengths
LC_FINE    = 0.25
LC_MID     = 0.5
LC_COARSE  = 2.5
LC_NOZZLE  = 1.2

SLAB_DZ = 1.0  # slab thickness (mm)

# ─── Output ───────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CASE_DIR   = os.path.dirname(os.path.dirname(SCRIPT_DIR))
MSH_FILE   = os.path.join(CASE_DIR, "cvrc_slab.msh")


def generate():
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 1)
    gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
    gmsh.option.setNumber("Mesh.Binary", 0)
    gmsh.option.setNumber("Mesh.SaveAll", 0)
    gmsh.option.setNumber("Mesh.Smoothing", 10)
    gmsh.option.setNumber("Mesh.MeshSizeMin", 0.1)
    gmsh.option.setNumber("Mesh.MeshSizeMax", LC_COARSE)
    gmsh.model.add("cvrc_noslots")
    geo = gmsh.model.geo

    # ── helpers ────────────────────────────────────────────────────
    _pts = {}
    _lns = {}

    def pt(x, y, lc=LC_FINE):
        if abs(y) < 1e-12:
            y = EPS
        key = (round(x, 6), round(y, 6))
        if key not in _pts:
            _pts[key] = geo.addPoint(x, y, 0, lc)
        return _pts[key]

    def ln(a, b):
        key = (a, b)
        if key in _lns: return _lns[key]
        rev = (b, a)
        if rev in _lns: return -_lns[rev]
        t = geo.addLine(a, b)
        _lns[key] = t
        return t

    surfaces = []       # (tag, name)
    struct = []         # (tag, [curves], (nx, ny))

    def quad(x0, y0, x1, y1, name, nx, ny, lc=LC_FINE):
        """Create a structured quad block."""
        p = [pt(x0, y0, lc), pt(x1, y0, lc), pt(x1, y1, lc), pt(x0, y1, lc)]
        c = [ln(p[0], p[1]), ln(p[1], p[2]), ln(p[2], p[3]), ln(p[3], p[0])]
        loop = geo.addCurveLoop(c)
        s = geo.addPlaneSurface([loop])
        surfaces.append((s, name))
        struct.append((s, c, (nx, ny)))
        return s

    # ── Oxidizer inlet profile ────────────────────────────────────
    # Profile: (-140,eps)→(-140,3)→(-160,3)→(-160,10.235)→(-10.16,10.235)
    # This creates an L-shaped inlet region.

    # Block 1: axis channel, x=-140 to -128, y=eps to 3
    #          (between injector face step and post)
    # But first we need the inlet blocks at x=-160 to -140

    # Inlet face blocks (x=-160 to -140)
    # Only one band here: y=3 to 10.235 (the inlet opening)
    # The region y=eps to 3 at x<-140 is SOLID (no flow)
    quad(X_INLET, R_AXIS, X_INJ_FACE, R_OX_TOP,
         "inlet_passage", NX_INLET, NY_OX_PASSAGE)

    # Passage continuation (x=-140 to -128): 2 bands
    X_POST_START = -128.0
    quad(X_INJ_FACE, EPS, X_POST_START, R_AXIS,
         "passage_axis", NX_PASSAGE, NY_AXIS)
    quad(X_INJ_FACE, R_AXIS, X_POST_START, R_OX_TOP,
         "passage_ox", NX_PASSAGE, NY_OX_PASSAGE)

    # ── Oxidizer plenum (x=-128 to -10.16) — unstructured ────────
    p_mid = [
        pt(X_POST_START, EPS, LC_MID),
        pt(X_POST_END, EPS, LC_MID),
        pt(X_POST_END, R_OX_TOP, LC_MID),
        pt(X_POST_START, R_OX_TOP, LC_MID),
    ]
    c_mid = [ln(p_mid[0], p_mid[1]), ln(p_mid[1], p_mid[2]),
             ln(p_mid[2], p_mid[3]), ln(p_mid[3], p_mid[0])]
    loop = geo.addCurveLoop(c_mid)
    s_mid = geo.addPlaneSurface([loop])
    surfaces.append((s_mid, "plenum"))

    # ── Fuel pipe ─────────────────────────────────────────────────
    quad(X_FUEL, R_STEP, X_POST_END, R_RECESS,
         "fuel_inner", NX_FUEL, NY_FUEL_INNER)
    quad(X_FUEL, R_OX_TOP, X_POST_END, R_STEP,
         "fuel_outer", NX_FUEL, NY_FUEL_OUTER)

    # ── Recess blocks (x=-10.16 to 0) ────────────────────────────
    quad(X_POST_END, EPS, X_CHAM_0, R_OX_TOP,
         "recess_low", NX_RECESS, NY_MID_VERT)
    quad(X_POST_END, R_OX_TOP, X_CHAM_0, R_STEP,
         "recess_mid", NX_RECESS, NY_FUEL_OUTER)
    quad(X_POST_END, R_STEP, X_CHAM_0, R_RECESS,
         "recess_top", NX_RECESS, NY_FUEL_INNER)

    # ── Chamber connection (x=0 to 20) ───────────────────────────
    quad(X_CHAM_0, EPS, X_CHAM_20, R_OX_TOP,
         "conn_low", NX_CONN, NY_MID_VERT)
    quad(X_CHAM_0, R_OX_TOP, X_CHAM_20, R_STEP,
         "conn_mid", NX_CONN, NY_FUEL_OUTER)
    quad(X_CHAM_0, R_STEP, X_CHAM_20, R_RECESS,
         "conn_top", NX_CONN, NY_FUEL_INNER)
    quad(X_CHAM_0, R_RECESS, X_CHAM_20, R_CHAMBER,
         "conn_upper", NX_CONN, NY_UPPER)

    # ── Nozzle / downstream (unstructured) ────────────────────────
    p51 = pt(*NOZZLE_P51, LC_NOZZLE)
    p52 = pt(*NOZZLE_P52, LC_NOZZLE)
    p53 = pt(*NOZZLE_P53, LC_NOZZLE)
    pc1 = pt(*NOZZLE_C1, LC_NOZZLE)
    pc2 = pt(*NOZZLE_C2, LC_NOZZLE)
    pLc = pt(L_C, R_CHAMBER, LC_NOZZLE)

    bs1 = geo.addBSpline([p52, pc2, p51])  # 397.5,11 → 399.5,eps
    bs2 = geo.addBSpline([p53, pc1, p52])  # 381,20   → 397.5,11

    p20e = pt(X_CHAM_20, EPS, LC_MID)
    p20a = pt(X_CHAM_20, R_OX_TOP, LC_MID)
    p20b = pt(X_CHAM_20, R_STEP, LC_MID)
    p20c = pt(X_CHAM_20, R_RECESS, LC_MID)
    p20d = pt(X_CHAM_20, R_CHAMBER, LC_MID)

    noz_curves = [
        ln(p20e, p51),           # bottom axis
        -bs1,                    # nozzle wall lower
        -bs2,                    # nozzle wall upper
        ln(p53, pLc),            # 381,20 → 381,22.5
        ln(pLc, p20d),           # top wall
        ln(p20d, p20c),          # left edge down
        ln(p20c, p20b),
        ln(p20b, p20a),
        ln(p20a, p20e),
    ]
    loop = geo.addCurveLoop(noz_curves)
    s_noz = geo.addPlaneSurface([loop])
    surfaces.append((s_noz, "nozzle"))

    # ── Synchronize ───────────────────────────────────────────────
    geo.synchronize()

    # ── Apply transfinite ─────────────────────────────────────────
    for s, c, (nx, ny) in struct:
        for ci in [c[0], c[2]]:
            gmsh.model.mesh.setTransfiniteCurve(abs(ci), nx)
        for ci in [c[1], c[3]]:
            gmsh.model.mesh.setTransfiniteCurve(abs(ci), ny)
        gmsh.model.mesh.setTransfiniteSurface(s)
        gmsh.model.mesh.setRecombine(2, s)

    # Recombine unstructured surfaces too (for all-quad)
    for s, _ in surfaces:
        gmsh.model.mesh.setRecombine(2, s)

    # ── Size fields for plenum + nozzle ───────────────────────────
    # Distance from structured boundaries into plenum
    plenum_bnd = [abs(c_mid[i]) for i in range(4)]
    f1 = gmsh.model.mesh.field.add("Distance")
    gmsh.model.mesh.field.setNumbers(f1, "CurvesList", plenum_bnd)
    gmsh.model.mesh.field.setNumber(f1, "Sampling", 100)
    f2 = gmsh.model.mesh.field.add("Threshold")
    gmsh.model.mesh.field.setNumber(f2, "InField", f1)
    gmsh.model.mesh.field.setNumber(f2, "SizeMin", LC_MID)
    gmsh.model.mesh.field.setNumber(f2, "SizeMax", LC_COARSE)
    gmsh.model.mesh.field.setNumber(f2, "DistMin", 0)
    gmsh.model.mesh.field.setNumber(f2, "DistMax", 80)
    gmsh.model.mesh.field.setNumber(f2, "Sigmoid", 1)

    f9 = gmsh.model.mesh.field.add("Min")
    gmsh.model.mesh.field.setNumbers(f9, "FieldsList", [f2])
    gmsh.model.mesh.field.setAsBackgroundMesh(f9)

    # ── Mesh 2D ───────────────────────────────────────────────────
    print("Meshing 2D...")
    gmsh.model.mesh.generate(2)

    # ── Classify boundary curves ──────────────────────────────────
    orig_surfs = [s for s, _ in surfaces]

    # ── Extrude to slab ───────────────────────────────────────────
    print(f"Extruding {len(orig_surfs)} surfaces → slab (dz={SLAB_DZ} mm)...")
    volumes = []
    top_surfs = []
    lat_map = {}  # orig_curve → [lateral_surf_tags]

    for stag in orig_surfs:
        bnd = gmsh.model.getBoundary([(2, stag)], combined=False, oriented=False)
        bnd_curves = [t for d, t in bnd if d == 1]
        res = gmsh.model.geo.extrude([(2, stag)], 0, 0, SLAB_DZ, [1], recombine=True)
        gmsh.model.geo.synchronize()
        for i, (ed, et) in enumerate(res):
            if ed == 3:
                volumes.append(et)
            elif ed == 2:
                if i == 0:
                    top_surfs.append(et)
                else:
                    ci = i - 2
                    if 0 <= ci < len(bnd_curves):
                        lat_map.setdefault(bnd_curves[ci], []).append(et)

    # ── 3D mesh ───────────────────────────────────────────────────
    print("Meshing 3D...")
    for v in volumes:
        gmsh.model.mesh.setRecombine(3, v)
    gmsh.model.mesh.generate(3)

    # ── Classify lateral surfaces by position → physical groups ───
    def classify_curve(ctag):
        bb = gmsh.model.getBoundingBox(1, ctag)
        xmin, ymin, _, xmax, ymax, _ = bb[:6]
        if ymin < 0.01 and ymax < 0.01:
            return "axis"
        if xmin > 390:
            return "outlet"
        if xmin < X_INLET + 1 and abs(xmax - xmin) < 0.5 and ymin > R_AXIS - 0.5:
            return "oxidizer_inlet"
        if abs(xmin - X_FUEL) < 1 and abs(xmax - xmin) < 0.5 and ymin > R_STEP - 0.5:
            return "fuel_inlet"
        return "wall"

    # Clear old physical groups
    for d in (1, 2, 3):
        for pd, pt_tag in gmsh.model.getPhysicalGroups(d):
            gmsh.model.removePhysicalGroups([(pd, pt_tag)])
    gmsh.model.geo.synchronize()

    pg = gmsh.model.addPhysicalGroup
    sn = gmsh.model.setPhysicalName

    g = pg(3, volumes);         sn(3, g, "fluid")
    g = pg(2, orig_surfs);      sn(2, g, "back")
    g = pg(2, top_surfs);       sn(2, g, "front")

    lat_by_name = defaultdict(list)
    orig_curves = [t for _, t in gmsh.model.getEntities(1)
                   if abs(gmsh.model.getBoundingBox(1, t)[2]) < 0.01]  # z≈0
    for ctag in orig_curves:
        name = classify_curve(ctag)
        lat_by_name[name].extend(lat_map.get(ctag, []))

    for name, tags in lat_by_name.items():
        if tags:
            g = pg(2, tags); sn(2, g, name)
            print(f"  {name:22s}  {len(tags)} faces")

    # ── Write ─────────────────────────────────────────────────────
    gmsh.write(MSH_FILE)
    n_nodes = len(gmsh.model.mesh.getNodes()[0])
    n_back = sum(sum(len(e) for e in gmsh.model.mesh.getElements(2, s)[1]) for s in orig_surfs)
    n_front = sum(sum(len(e) for e in gmsh.model.mesh.getElements(2, s)[1]) for s in top_surfs)
    n_cells = sum(len(e) for e in gmsh.model.mesh.getElements(3)[1])
    print(f"\n  Nodes:  {n_nodes:,}")
    print(f"  Cells:  {n_cells:,}")
    print(f"  back:   {n_back:,}  front: {n_front:,}  match: {n_back == n_front}")
    print(f"  Output: {MSH_FILE}")

    gmsh.finalize()
    return n_back == n_front


if __name__ == "__main__":
    ok = generate()
    exit(0 if ok else 1)
