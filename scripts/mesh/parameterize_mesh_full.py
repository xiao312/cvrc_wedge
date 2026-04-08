#!/usr/bin/env python3
"""
CVRC 2D Profile Mesh Parameterizer — Complete Constraint-Aware
==============================================================

Controls ALL mesh parameters in the CVRC 2D profile:
  A. Transfinite node counts (78 curves in 21 constraint chains)
  B. Transfinite grading (Progression/Bump per chain or per line)
  C. Unstructured sizing fields (4 Distance/Threshold pairs)
  D. Point characteristic lengths (cl__1 through cl__7)

MESH TOPOLOGY:
  29 total surfaces: 27 transfinite (structured), 2 unstructured.
  Surface 20 (unstructured): oxidizer plenum, x≈-128 to -10 mm
  Surface 29 (unstructured): combustion chamber + nozzle, x≈20 to 400 mm

TRANSITION INTERFACE SIZING (original):
  Structured radial cell ≈ 0.25 mm (thin), axial cell ≈ 9.8 mm (wide)
  Unstructured SizeMin = 0.7 mm, SizeMax = 3.0 mm
  → Radial mismatch: 0.25 → 0.7 mm (2.8× jump)
  → Axial mismatch:  9.8 → 0.7 mm (14× opposite jump)
  → Growth 0.7→3 mm over 45 mm is aggressive

SIZING FIELDS:
  Field 1-2 "inlet_axis":  Distance from Lines 36,39,41,44,46,49,51,54
                            (Surface 20 inner boundary — structured/unstructured seam)
  Field 3-4 "mid_vert":    Distance from Line 57
                            (mid vertical connector at x≈-10)
  Field 5-6 "chamber":     Distance from Lines 72,74,76,78
                            (Surface 29 inner boundary — chamber entrance)
  Field 7-8 "nozzle":      Distance from Lines 82,83,84
                            (nozzle BSpline walls)
  Field 9:                  Min of all → Background mesh

GRADING REFERENCE (Gmsh Transfinite Curve):
  "Progression r"  — geometric ratio between successive cells.
                     r=1 → uniform;  r>1 → cells grow toward end;
                     r<0 → cells grow toward start (|r| is ratio).
  "Bump c"         — cells cluster toward BOTH ends.
                     c=1 → uniform;  c<1 → stronger clustering.

Usage:
    1. Edit parameters below (set to None to keep original).
    2. Run:  python3 parameterize_mesh_full.py
    3. Run:  ./scripts/run_mesh_pipeline.sh --param --clean
"""

import re
import os
from collections import defaultdict

# #############################################################################
#
#  SECTION A — TRANSFINITE NODE COUNTS
#  Set to None to keep original value.
#
# #############################################################################

# ── Y-DIRECTION (radial) — 12 independent chains ──────────────────────

NY_LAYER_1    = None  # orig:  4,  y=3.0–3.8 mm,    Lines 2,4,24,39
NY_LAYER_2    = None  # orig:  9,  y=3.8–5.8 mm,    Lines 5,7,41,43
NY_LAYER_3    = None  # orig:  3,  y=5.8–6.3 mm,    Lines 8,10,27,44
NY_LAYER_4    = None  # orig:  8,  y=6.3–8.0 mm,    Lines 11,13,46,48
NY_LAYER_5    = None  # orig:  3,  y=8.0–8.3 mm,    Lines 14,16,30,49
NY_LAYER_6    = None  # orig:  7,  y=8.3–9.7 mm,    Lines 17,19,51,53
NY_LAYER_7    = None  # orig:  4,  y=9.7–10.2 mm,   Lines 20,22,33,54
NY_AXIS_H     = None  # orig: 13,  y=0–3 mm axis,   Lines 36,38
NY_MID_VERT   = None  # orig: 49,  mid→chamber,     Lines 57,64,72
NY_FUEL_OUTER = None  # orig:  4,  fuel ann outer,   Lines 60,62,69,76
NY_FUEL_INNER = None  # orig:  4,  fuel ann inner,   Lines 66,68,74
NY_UPPER      = 35  # orig: 21,  upper chamber,    Lines 78,80

# ── X-DIRECTION (axial) — 9 independent chains ───────────────────────

NX_INLET        = None  # orig: 17,  Lines 1,3,6,9,12,15,18,21
NX_SLOT_1       = 11  # orig:  7,  Lines 23,25
NX_SLOT_2       = 11  # orig:  7,  Lines 26,28
NX_SLOT_3       = 11  # orig:  7,  Lines 29,31
NX_SLOT_4       = 11  # orig:  7,  Lines 32,34
NX_AXIS         = 50  # orig: 13,  Lines 35,37,40,42,45,47,50,52,55
NX_FUEL         = 31  # orig: 21,  Lines 59,61
NX_CHAMBER_CONN = 17  # orig: 11,  Lines 63,65,67,70
NX_CHAMBER      = 120  # orig: 17,  Lines 71,73,75,77,79


# #############################################################################
#
#  SECTION B — TRANSFINITE GRADING
#  Format: "Progression <r>" or "Bump <c>".  None = keep original.
#
# #############################################################################

# ── Y grading ─────────────────────────────────────────────────────────

NY_LAYER_1_GRAD    = None  # Lines 2,4,24,39
NY_LAYER_2_GRAD    = None  # Lines 5,7,41,43
NY_LAYER_3_GRAD    = None  # Lines 8,10,27,44
NY_LAYER_4_GRAD    = None  # Lines 11,13,46,48
NY_LAYER_5_GRAD    = None  # Lines 14,16,30,49
NY_LAYER_6_GRAD    = None  # Lines 17,19,51,53
NY_LAYER_7_GRAD    = None  # Lines 20,22,33,54
NY_AXIS_H_GRAD     = None  # Lines 36,38
NY_MID_VERT_GRAD   = None  # Lines 57,64,72
NY_FUEL_OUTER_GRAD = None  # Lines 60,62,69,76
NY_FUEL_INNER_GRAD = None  # Lines 66,68,74
NY_UPPER_GRAD      = None  # Lines 78,80

# ── X grading ─────────────────────────────────────────────────────────

NX_INLET_GRAD        = None  # Lines 1,3,6,9,12,15,18,21
NX_SLOT_1_GRAD       = None  # Lines 23,25
NX_SLOT_2_GRAD       = None  # Lines 26,28
NX_SLOT_3_GRAD       = None  # Lines 29,31
NX_SLOT_4_GRAD       = None  # Lines 32,34
NX_AXIS_GRAD         = None  # Lines 35,37,40,42,45,47,50,52,55
NX_FUEL_GRAD         = None  # Lines 59,61
NX_CHAMBER_CONN_GRAD = None  # Lines 63,65,67,70
NX_CHAMBER_GRAD      = None  # Lines 71,73,75,77,79

# ── Per-line grading overrides ────────────────────────────────────────
# Dict: { line_id: "Progression <r>" or "Bump <c>" }
# Overrides chain-level grading for individual lines.
LINE_GRAD_OVERRIDES = {}


# #############################################################################
#
#  SECTION C — UNSTRUCTURED SIZE FIELDS
#  4 Distance/Threshold pairs control cell size in Surfaces 20 & 29.
#  Set any to None to keep original.
#
#  Each pair: Distance field finds distance from boundary curves,
#             Threshold field maps distance → cell size:
#               dist < DistMin  → SizeMin
#               dist > DistMax  → SizeMax (or uncapped if StopAtDistMax=0)
#               between         → linear interpolation (or sigmoid)
#
# #############################################################################

# ── Field 1-2: "inlet_axis" ──────────────────────────────────────────
# Distance from structured block interface at Surface 20 inner edge.
# Lines: 36,39,41,44,46,49,51,54 (right edge of inlet/slot/axis blocks)
# Controls cell size in the oxidizer plenum unstructured region.
FIELD_INLET_AXIS_SIZE_MIN   = 0.25  # orig: 0.7   match structured radial cell
FIELD_INLET_AXIS_SIZE_MAX   = 1.8   # orig: 3.0   gentler ceiling
FIELD_INLET_AXIS_DIST_MIN   = 2     # orig: 0     keep SizeMin for 2 mm buffer zone
FIELD_INLET_AXIS_DIST_MAX   = 90    # orig: 45    2× distance for gradual growth
FIELD_INLET_AXIS_SIGMOID    = 1     # orig: 0     S-curve for smooth transition
FIELD_INLET_AXIS_STOP       = None  # orig: 0     1=cap at SizeMax beyond DistMax

# ── Field 3-4: "mid_vert" ────────────────────────────────────────────
# Distance from the mid vertical connector Line 57 (at x≈-10).
# Controls cell size near the transition column in Surface 20.
FIELD_MID_VERT_SIZE_MIN     = 0.25  # orig: 0.7
FIELD_MID_VERT_SIZE_MAX     = 1.8   # orig: 3.0
FIELD_MID_VERT_DIST_MIN     = 2     # orig: 0
FIELD_MID_VERT_DIST_MAX     = 60    # orig: 35
FIELD_MID_VERT_SIGMOID      = 1     # orig: 0
FIELD_MID_VERT_STOP         = None  # orig: 0

# ── Field 5-6: "chamber" ─────────────────────────────────────────────
# Distance from chamber entrance Lines 72,74,76,78.
# Controls cell size in the main combustion chamber (Surface 29).
FIELD_CHAMBER_SIZE_MIN      = 0.3   # orig: 0.7
FIELD_CHAMBER_SIZE_MAX      = 2.0   # orig: 3.0
FIELD_CHAMBER_DIST_MIN      = 2     # orig: 0
FIELD_CHAMBER_DIST_MAX      = 160   # orig: 120
FIELD_CHAMBER_SIGMOID       = 1     # orig: 0
FIELD_CHAMBER_STOP          = None  # orig: 0

# ── Field 7-8: "nozzle" ──────────────────────────────────────────────
# Distance from nozzle BSpline walls Lines 82,83,84.
# Controls cell size near the converging nozzle section.
FIELD_NOZZLE_SIZE_MIN       = 0.3   # orig: 0.5
FIELD_NOZZLE_SIZE_MAX       = 1.8   # orig: 3.0
FIELD_NOZZLE_DIST_MIN       = 1     # orig: 0
FIELD_NOZZLE_DIST_MAX       = 50    # orig: 25
FIELD_NOZZLE_SIGMOID        = 1     # orig: 0
FIELD_NOZZLE_STOP           = None  # orig: 0


# #############################################################################
#
#  SECTION D — POINT CHARACTERISTIC LENGTHS
#  Control base cell size at geometry vertices (affects nearby unstructured
#  cells before fields override).  Set to None to keep original.
#
# #############################################################################

CL_STRUCTURED = 0.25  # cl__1, orig: 0.5   match field SizeMin
CL_CHAMBER_ENTRANCE = 0.3   # cl__2, orig: 0.7   match chamber SizeMin
CL_FAR_FIELD  = 2.5   # cl__3, orig: 4.0   tighter far field
CL_OUTLET_1   = 1.5   # cl__4, orig: 2.754  refine outlet
CL_OUTLET_2   = 1.5   # cl__5, orig: 2.743  refine outlet
CL_NOZZLE_1   = 1.2   # cl__6, orig: 2.654  refine nozzle
CL_NOZZLE_2   = 1.2   # cl__7, orig: 2.762  refine nozzle


# #############################################################################
#  CONSTRAINT MAPS — DO NOT EDIT
# #############################################################################

Y_CHAINS = {
    "NY_LAYER_1":     [2, 4, 24, 39],
    "NY_LAYER_2":     [5, 7, 41, 43],
    "NY_LAYER_3":     [8, 10, 27, 44],
    "NY_LAYER_4":     [11, 13, 46, 48],
    "NY_LAYER_5":     [14, 16, 30, 49],
    "NY_LAYER_6":     [17, 19, 51, 53],
    "NY_LAYER_7":     [20, 22, 33, 54],
    "NY_AXIS_H":      [36, 38],
    "NY_MID_VERT":    [57, 64, 72],
    "NY_FUEL_OUTER":  [60, 62, 69, 76],
    "NY_FUEL_INNER":  [66, 68, 74],
    "NY_UPPER":       [78, 80],
}
X_CHAINS = {
    "NX_INLET":         [1, 3, 6, 9, 12, 15, 18, 21],
    "NX_SLOT_1":        [23, 25],
    "NX_SLOT_2":        [26, 28],
    "NX_SLOT_3":        [29, 31],
    "NX_SLOT_4":        [32, 34],
    "NX_AXIS":          [35, 37, 40, 42, 45, 47, 50, 52, 55],
    "NX_FUEL":          [59, 61],
    "NX_CHAMBER_CONN":  [63, 65, 67, 70],
    "NX_CHAMBER":       [71, 73, 75, 77, 79],
}
ALL_CHAINS = {**Y_CHAINS, **X_CHAINS}

# Field parameter map: (field_pair_index, threshold_field_attr, param_name)
FIELD_MAP = [
    # (Distance field#, Threshold field#, prefix)
    (1, 2, "FIELD_INLET_AXIS"),
    (3, 4, "FIELD_MID_VERT"),
    (5, 6, "FIELD_CHAMBER"),
    (7, 8, "FIELD_NOZZLE"),
]
# Threshold attributes → param suffix
THRESH_ATTRS = [
    ("SizeMin",       "_SIZE_MIN"),
    ("SizeMax",       "_SIZE_MAX"),
    ("DistMin",       "_DIST_MIN"),
    ("DistMax",       "_DIST_MAX"),
    ("Sigmoid",       "_SIGMOID"),
    ("StopAtDistMax", "_STOP"),
]

# Characteristic length map: (cl_var, param_name)
CL_MAP = [
    ("cl__1", "CL_STRUCTURED"),
    ("cl__2", "CL_CHAMBER_ENTRANCE"),
    ("cl__3", "CL_FAR_FIELD"),
    ("cl__4", "CL_OUTLET_1"),
    ("cl__5", "CL_OUTLET_2"),
    ("cl__6", "CL_NOZZLE_1"),
    ("cl__7", "CL_NOZZLE_2"),
]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE  = os.path.join(SCRIPT_DIR, "cvrc_2d_profile.geo_unrolled")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "cvrc_2d_profile_param.geo_unrolled")


# #############################################################################
#  MAIN
# #############################################################################

def parameterize_geo():
    """Read original geo, apply all parameter changes, write output."""

    print(f"\n{'=' * 70}")
    print("CVRC Mesh Parameterizer — Complete")
    print(f"{'=' * 70}")
    print(f"Input:  {INPUT_FILE}")
    print(f"Output: {OUTPUT_FILE}")

    with open(INPUT_FILE) as f:
        content = f.read()

    any_change = False
    g = globals()

    # =====================================================================
    # A+B  TRANSFINITE CURVES (node counts + grading)
    # =====================================================================

    tc_pat = re.compile(
        r'Transfinite Curve \{(\d+)\} = (\d+) Using (\w+) ([0-9.eE+-]+);'
    )
    cur_nodes = {}
    cur_expr  = {}
    for m in tc_pat.finditer(content):
        lid = int(m.group(1))
        cur_nodes[lid] = int(m.group(2))
        cur_expr[lid]  = f"{m.group(3)} {m.group(4)}"

    node_changes = {}
    grad_changes = {}
    all_covered = set()

    def process_chains(chain_map, label):
        print(f"\n{'─' * 70}")
        print(label)
        print(f"{'─' * 70}")
        for name, lines in chain_map.items():
            n_val = g.get(name)
            g_val = g.get(name + "_GRAD")
            orig_n = cur_nodes.get(lines[0], "?")
            orig_g = cur_expr.get(lines[0], "?")
            all_covered.update(lines)
            if n_val is not None:
                n_tag = f"{orig_n} → {n_val}"
                for lid in lines:
                    node_changes[lid] = (name, n_val)
            else:
                n_tag = str(orig_n)
            if g_val is not None:
                g_tag = f"  grad: {orig_g} → {g_val}"
                for lid in lines:
                    grad_changes[lid] = (name + "_GRAD", g_val)
            else:
                g_tag = ""
            print(f"  {name:18s}  nodes={n_tag:>8s}  lines {lines}{g_tag}")

    process_chains(Y_CHAINS, "A. TRANSFINITE — Y-DIRECTION (radial):")
    process_chains(X_CHAINS, "A. TRANSFINITE — X-DIRECTION (axial):")

    if LINE_GRAD_OVERRIDES:
        print(f"\n{'─' * 70}")
        print("B. PER-LINE GRADING OVERRIDES:")
        print(f"{'─' * 70}")
        for lid, expr in sorted(LINE_GRAD_OVERRIDES.items()):
            old = cur_expr.get(lid, "?")
            grad_changes[lid] = ("LINE_OVERRIDE", expr)
            print(f"  Line {lid:3d}:  {old} → {expr}")

    # Coverage check
    missing = sorted(set(cur_nodes.keys()) - all_covered)
    print(f"\n{'─' * 70}")
    if missing:
        print(f"⚠  UNCOVERED lines: {missing}")
    else:
        print(f"✓ All {len(cur_nodes)} transfinite curves covered")
    errors = []
    for name, lines in ALL_CHAINS.items():
        vals = {cur_nodes.get(lid) for lid in lines}
        if len(vals) > 1:
            errors.append(f"{name}: {list(zip(lines, [cur_nodes.get(l) for l in lines]))}")
    if errors:
        print("⚠  CONSTRAINT ERRORS:")
        for e in errors:
            print(f"    {e}")
    else:
        print("✓ All constraint chains consistent")

    # Apply transfinite changes
    tc_count = 0
    for lid in cur_nodes:
        new_n = node_changes[lid][1] if lid in node_changes else cur_nodes[lid]
        new_g = grad_changes[lid][1] if lid in grad_changes else cur_expr[lid]
        old_line = f"Transfinite Curve {{{lid}}} = {cur_nodes[lid]} Using {cur_expr[lid]};"
        new_line = f"Transfinite Curve {{{lid}}} = {new_n} Using {new_g};"
        if old_line != new_line:
            content = content.replace(old_line, new_line)
            tc_count += 1

    if tc_count:
        any_change = True
        print(f"\n📝 {tc_count} transfinite curve(s) modified")
        by_p = defaultdict(list)
        for lid in sorted(node_changes):
            pn, nv = node_changes[lid]
            by_p[pn].append((lid, cur_nodes.get(lid), nv))
        for pn, items in by_p.items():
            print(f"  {pn:18s}  lines {[i[0] for i in items]}  {items[0][1]} → {items[0][2]}")
        by_p2 = defaultdict(list)
        for lid in sorted(grad_changes):
            pn, nv = grad_changes[lid]
            by_p2[pn].append((lid, cur_expr.get(lid), nv))
        for pn, items in by_p2.items():
            print(f"  {pn:18s}  lines {[i[0] for i in items]}  {items[0][1]} → {items[0][2]}")

    # =====================================================================
    # C  UNSTRUCTURED SIZE FIELDS
    # =====================================================================

    print(f"\n{'─' * 70}")
    print("C. UNSTRUCTURED SIZE FIELDS:")
    print(f"{'─' * 70}")

    field_count = 0
    for dist_id, thresh_id, prefix in FIELD_MAP:
        label = prefix.replace("FIELD_", "").lower()
        changes_here = []
        for attr, suffix in THRESH_ATTRS:
            param_name = prefix + suffix
            val = g.get(param_name)
            if val is None:
                continue

            # Match:  Field[N].Attr = <value>;
            pat = re.compile(
                rf"(Field\[{thresh_id}\]\.{attr}\s*=\s*)([0-9.eE+-]+)(;)"
            )
            m = pat.search(content)
            if m:
                old_val = m.group(2)
                new_val = str(val)
                if old_val != new_val:
                    content = pat.sub(rf"\g<1>{new_val}\3", content)
                    changes_here.append((attr, old_val, new_val))
                    field_count += 1

        if changes_here:
            print(f"  {label} (Field {thresh_id}):")
            for attr, old, new in changes_here:
                print(f"    {attr:16s}  {old} → {new}")
        else:
            # Show current values
            vals = []
            for attr, suffix in THRESH_ATTRS[:4]:  # show main 4
                pat = re.compile(rf"Field\[{thresh_id}\]\.{attr}\s*=\s*([0-9.eE+-]+);")
                m = pat.search(content)
                if m:
                    vals.append(f"{attr}={m.group(1)}")
            print(f"  {label} (Field {thresh_id}):  {', '.join(vals)}  (original)")

    if field_count:
        any_change = True
        print(f"\n📝 {field_count} field parameter(s) modified")

    # =====================================================================
    # D  POINT CHARACTERISTIC LENGTHS
    # =====================================================================

    print(f"\n{'─' * 70}")
    print("D. POINT CHARACTERISTIC LENGTHS:")
    print(f"{'─' * 70}")

    cl_count = 0
    for cl_var, param_name in CL_MAP:
        val = g.get(param_name)
        # Read current value
        pat = re.compile(rf"({re.escape(cl_var)}\s*=\s*)([0-9.eE+-]+)(;)")
        m = pat.search(content)
        if not m:
            continue
        old_val = m.group(2)
        if val is not None:
            new_val = str(val)
            if old_val != new_val:
                content = pat.sub(rf"\g<1>{new_val}\3", content)
                print(f"  {param_name:22s}  ({cl_var})  {old_val} → {new_val}")
                cl_count += 1
            else:
                print(f"  {param_name:22s}  ({cl_var})  {old_val} (unchanged)")
        else:
            print(f"  {param_name:22s}  ({cl_var})  {old_val} (original)")

    if cl_count:
        any_change = True
        print(f"\n📝 {cl_count} characteristic length(s) modified")

    # =====================================================================
    # WRITE OUTPUT
    # =====================================================================

    if not any_change:
        print(f"\n{'─' * 70}")
        print("ℹ  No parameters changed — output identical to input")

    with open(OUTPUT_FILE, "w") as f:
        f.write(content)

    print(f"\n✓ Output: {OUTPUT_FILE}")
    print(f"  To generate mesh:  ./scripts/run_mesh_pipeline.sh --param --clean")
    print(f"{'=' * 70}\n")
    return True


if __name__ == "__main__":
    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: {INPUT_FILE} not found")
        exit(1)
    parameterize_geo()
