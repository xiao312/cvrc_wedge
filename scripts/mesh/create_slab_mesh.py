#!/usr/bin/env python3
"""
CVRC Slab Mesh Generator — creates a 1-cell-thick flat slab for extrudeMesh.

Reads the parameterised 2D profile, meshes it, extrudes ONE layer in z,
and writes a Gmsh .msh file.  The "back" patch (z=0) will later be the
source for OpenFOAM's extrudeMesh wedge model.
"""

import os, math, gmsh

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
CASE_DIR    = os.path.dirname(os.path.dirname(SCRIPT_DIR))
SOURCE_GEO  = os.path.join(SCRIPT_DIR, "cvrc_2d_profile.geo_unrolled")
MSH_FILE    = os.path.join(CASE_DIR, "cvrc_slab.msh")
SLAB_DZ     = 1.0  # mm  (arbitrary; extrudeMesh replaces geometry)


def create_slab():
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 1)
    gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
    gmsh.option.setNumber("Mesh.Binary", 0)
    gmsh.option.setNumber("Mesh.SaveAll", 0)
    gmsh.option.setNumber("Mesh.Smoothing", 10)

    gmsh.model.add("cvrc_slab")
    gmsh.merge(SOURCE_GEO)
    gmsh.model.geo.synchronize()

    # ── original 2-D entities ──────────────────────────────────────────
    orig_surfs  = [t for _, t in gmsh.model.getEntities(2)]
    orig_curves = [t for _, t in gmsh.model.getEntities(1)]

    # remember original physical-group names for slot classification
    slot_curves = {1: set(), 2: set(), 3: set()}
    for d, p in gmsh.model.getPhysicalGroups(1):
        nm = gmsh.model.getPhysicalName(d, p)
        ents = gmsh.model.getEntitiesForPhysicalGroup(d, p)
        if "oxidizer_slot_1" in nm: slot_curves[1].update(ents)
        elif "oxidizer_slot_2" in nm: slot_curves[2].update(ents)
        elif "oxidizer_slot_3" in nm: slot_curves[3].update(ents)

    # ── classify original boundary curves by position ──────────────────
    def classify(ctag):
        if ctag in slot_curves[1]: return "oxidizer_slot_1"
        if ctag in slot_curves[2]: return "oxidizer_slot_2"
        if ctag in slot_curves[3]: return "oxidizer_slot_3"
        bb = gmsh.model.getBoundingBox(1, ctag)
        xmin, ymin, _, xmax, ymax, _ = bb[:6]
        vert = abs(xmax - xmin) < 0.5
        if ymin < 0.01 and ymax < 0.01:        return "axis"
        if xmin > 390:                          return "outlet"
        if xmin < -159 and vert and ymin > 2.5: return "oxidizer_inlet"
        if -31 < xmin < -29 and vert and ymin > 9.5: return "fuel_inlet"
        return "wall"

    curve_cls = {c: classify(c) for c in orig_curves}

    # ── mesh 2-D ───────────────────────────────────────────────────────
    print("Generating 2-D mesh …")
    gmsh.model.mesh.generate(2)

    # ── extrude every surface 1 layer in +z ────────────────────────────
    print(f"Extruding {len(orig_surfs)} surfaces by {SLAB_DZ} mm in z …")
    volumes   = []
    top_surfs = []
    lat_map   = {}  # orig_curve → [lateral_surface_tags]

    for stag in orig_surfs:
        bnd = gmsh.model.getBoundary([(2, stag)], combined=False, oriented=False)
        bnd_curves = [t for d, t in bnd if d == 1]

        res = gmsh.model.geo.extrude([(2, stag)], 0, 0, SLAB_DZ, [1], recombine=True)
        gmsh.model.geo.synchronize()

        for i, (ed, et) in enumerate(res):
            if ed == 3:
                volumes.append(et)
            elif ed == 2:
                if i == 0:          # top face (z = SLAB_DZ)
                    top_surfs.append(et)
                else:               # lateral face from a boundary curve
                    ci = i - 2
                    if 0 <= ci < len(bnd_curves):
                        lat_map.setdefault(bnd_curves[ci], []).append(et)

    # ── recombine + 3-D mesh ───────────────────────────────────────────
    print("Generating 3-D mesh …")
    for v in volumes:
        gmsh.model.mesh.setRecombine(3, v)
    gmsh.model.mesh.generate(3)

    # ── physical groups ────────────────────────────────────────────────
    # clear old
    for d in (1, 2, 3):
        for pd, pt in gmsh.model.getPhysicalGroups(d):
            gmsh.model.removePhysicalGroups([(pd, pt)])
    gmsh.model.geo.synchronize()

    pg = gmsh.model.addPhysicalGroup
    sn = gmsh.model.setPhysicalName

    g = pg(3, volumes);            sn(3, g, "fluid")
    g = pg(2, list(orig_surfs));   sn(2, g, "back")    # z = 0
    g = pg(2, top_surfs);          sn(2, g, "front")   # z = dz

    # lateral surfaces grouped by boundary name
    from collections import defaultdict
    lat_by_name = defaultdict(list)
    for c, name in curve_cls.items():
        lat_by_name[name].extend(lat_map.get(c, []))

    for name, tags in lat_by_name.items():
        if tags:
            g = pg(2, tags); sn(2, g, name)
            print(f"  {name:22s}  {len(tags)} lateral faces")

    # ── write ──────────────────────────────────────────────────────────
    gmsh.write(MSH_FILE)
    n_nodes = len(gmsh.model.mesh.getNodes()[0])
    n_cells = sum(len(e) for e in gmsh.model.mesh.getElements(3)[1])
    n_back  = sum(sum(len(e) for e in gmsh.model.mesh.getElements(2, s)[1])
                  for s in orig_surfs)
    n_front = sum(sum(len(e) for e in gmsh.model.mesh.getElements(2, s)[1])
                  for s in top_surfs)
    print(f"\n  Nodes:  {n_nodes:,}")
    print(f"  Cells:  {n_cells:,}")
    print(f"  back:   {n_back:,}  front: {n_front:,}  match: {n_back==n_front}")
    print(f"  Output: {MSH_FILE}")
    gmsh.finalize()
    return n_back == n_front


if __name__ == "__main__":
    ok = create_slab()
    exit(0 if ok else 1)
