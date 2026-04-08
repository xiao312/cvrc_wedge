import gmsh
import os
import json

# CVRC axisymmetric profile with epsilon inner radius to avoid axis collapse.
# All y-coordinates (radius) that were 0 are shifted to epsilon.
# Units: mm.

EPSILON = 0.001  # mm, small inner radius to avoid zero-area faces in wedge

P = {
    "L_c": 381.0,
    "D_th": 20.8,
    "D_exit": 26.0,
    "L_conv": 40.0,
    "L_div": 24.0,

    "x_inj_face": -140.0,
    "x_slot_left": -146.0,
    "x_block_right": -128.0,
    "x_inj_box_left": -160.0,
    "x_fuel_start": -30.0,
    "x_recess_start": -10.16,

    "r_axis_offset": 3.0,
    "r_injector_box_top": 10.235,
    "r_recess_step": 11.0,
    "r_recess": 11.53,
    "r_chamber": 22.5,

    "slots_y": [
        (3.8, 5.8),
        (6.3, 8.0),
        (8.3, 9.7),
    ],

    "nx_left_block": 17,
    "nx_slot_strip": 7,
    "nx_right_local": 13,
    "nx_mid_upper": 21,
    "nx_xm10_to_0": 11,
    "nx_0_to_20": 17,
    "ny_0_10p235": 49,
    "ny_10p235_11": 4,
    "ny_11_11p53": 4,
    "ny_0_3": 13,
    "ny_3_3p8": 4,
    "ny_3p8_5p8": 9,
    "ny_5p8_6p3": 3,
    "ny_6p3_8p0": 8,
    "ny_8p0_8p3": 3,
    "ny_8p3_9p7": 7,
    "ny_9p7_10p235": 4,

    "lc_fine": 0.5,
    "lc_mid": 1.2,
    "lc_coarse": 4.0,
    "lc_plane20_left": 0.7,
    "lc_plane20_mid": 3.0,
    "lc_plane20_right": 0.7,
    "lc_plane29_left": 0.7,
    "lc_plane29_right": 3.0,
    "lc_nozzle_refine": 0.5,

    "nozzle_p51": (399.5, EPSILON),  # was (399.5, 0.0)
    "nozzle_p52": (397.5, 11.0),
    "nozzle_p53": (381.0, 20.0),
    "nozzle_c1_inside": (385.0, 8.0),
    "nozzle_c2_outside": (401.0, 6.5),
}

x10 = P["L_c"]
x11 = x10 + P["L_conv"]
x12 = x11 + P["L_div"]
r_th = 0.5 * P["D_th"]
r_exit = 0.5 * P["D_exit"]

outdir = os.path.dirname(__file__)
model_name = "cvrc_axisym_profile_slot_blocks_epsilon"

gmsh.initialize()
gmsh.option.setNumber("General.Terminal", 1)
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.model.add(model_name)
geo = gmsh.model.geo

point_cache = {}
line_cache = {}
surface_lines = {}  # track which lines belong to which surface for later classification
structured = []
all_surfaces = []

def point_lc(x, y):
    if -170 <= x <= -120 and EPSILON <= y <= 12:
        return P["lc_fine"]
    if -35 <= x <= 5 and EPSILON <= y <= 15:
        return P["lc_fine"]
    if 20 <= x <= x12 + 5 and EPSILON <= y <= 25:
        t = min(1.0, max(0.0, (x - 20.0) / (x12 - 20.0)))
        return P["lc_plane29_left"] * (1.0 - t) + P["lc_plane29_right"] * t
    if x10 - 10 <= x <= x12 + 5:
        return P["lc_mid"]
    return P["lc_coarse"]

def pt(x, y):
    # Apply epsilon offset for y=0 (axis)
    if abs(y) < 1e-12:
        y = EPSILON
    key = (round(x, 6), round(y, 6))
    if key not in point_cache:
        point_cache[key] = geo.addPoint(x, y, 0.0, point_lc(x, y))
    return point_cache[key]

def ln(pa, pb):
    key = (pa, pb)
    rev = (pb, pa)
    if key in line_cache:
        return line_cache[key]
    if rev in line_cache:
        return -line_cache[rev]
    tag = geo.addLine(pa, pb)
    line_cache[key] = tag
    return tag

def add_surface(coords, name, transfinite_counts=None):
    pts = [pt(x, y) for x, y in coords]
    curves = [ln(a, b) for a, b in zip(pts, pts[1:] + pts[:1])]
    loop = geo.addCurveLoop(curves)
    surf = geo.addPlaneSurface([loop])
    all_surfaces.append((surf, name))
    if transfinite_counts is not None:
        structured.append((surf, curves, transfinite_counts, name))
    return surf

# y-ranges for transfinite settings
ny_map = {
    (EPSILON, 3.0): P["ny_0_3"],
    (3.0, 3.8): P["ny_3_3p8"],
    (3.8, 5.8): P["ny_3p8_5p8"],
    (5.8, 6.3): P["ny_5p8_6p3"],
    (6.3, 8.0): P["ny_6p3_8p0"],
    (8.0, 8.3): P["ny_8p0_8p3"],
    (8.3, 9.7): P["ny_8p3_9p7"],
    (9.7, 10.235): P["ny_9p7_10p235"],
}

# 1) Left of the slot strip, split with the same y-levels as the slot region
left_bands = [(EPSILON, 3.0), (3.0, 3.8), (3.8, 5.8), (5.8, 6.3), (6.3, 8.0), (8.0, 8.3), (8.3, 9.7), (9.7, 10.235)]
for y0, y1 in left_bands:
    add_surface(
        [(-160.0, y0), (-146.0, y0), (-146.0, y1), (-160.0, y1)],
        f"left_slot_block_{y0}_{y1}",
        transfinite_counts=(P["nx_left_block"], ny_map[(y0, y1)]),
    )

# 2) Four fluid blocks in the slot strip x in [-146,-140]
for y0, y1 in [(EPSILON, 3.0), (5.8, 6.3), (8.0, 8.3), (9.7, 10.235)]:
    add_surface(
        [(-146.0, y0), (-140.0, y0), (-140.0, y1), (-146.0, y1)],
        f"slot_strip_{y0}_{y1}",
        transfinite_counts=(P["nx_slot_strip"], ny_map[(y0, y1)]),
    )

# 3) Local continuation blocks in x in [-140,-128]
right_local_bands = [
    (EPSILON, 3.0, P["ny_0_3"]),
    (3.0, 3.8, P["ny_3_3p8"]),
    (3.8, 5.8, P["ny_3p8_5p8"]),
    (5.8, 6.3, P["ny_5p8_6p3"]),
    (6.3, 8.0, P["ny_6p3_8p0"]),
    (8.0, 8.3, P["ny_8p0_8p3"]),
    (8.3, 9.7, P["ny_8p3_9p7"]),
    (9.7, 10.235, P["ny_9p7_10p235"]),
]
for y0, y1, ny in right_local_bands:
    add_surface(
        [(-140.0, y0), (-128.0, y0), (-128.0, y1), (-140.0, y1)],
        f"right_local_{y0}_{y1}",
        transfinite_counts=(P["nx_right_local"], ny),
    )

# 4) mid_block for -128 < x < -10.16 and EPSILON < y < 10.235
mid_block = add_surface(
    [
        (-128.0, EPSILON),
        (-10.16, EPSILON),
        (-10.16, 10.235),
        (-128.0, 10.235),
    ],
    "mid_block_-128_to_-10p16",
    transfinite_counts=None,
)

# 5) step_block for -30 < x < -10.16 and 11 < y < 11.53
add_surface(
    [(-30.0, 11.0), (-10.16, 11.0), (-10.16, 11.53), (-30.0, 11.53)],
    "step_block_-30_to_-10p16_11_to_11p53",
    transfinite_counts=(P["nx_mid_upper"], P["ny_11_11p53"]),
)

# 6) 3 structured blocks for -10.16 < x < 0
add_surface(
    [(-10.16, EPSILON), (0.0, EPSILON), (0.0, 10.235), (-10.16, 10.235)],
    "xneg10_to_0_low",
    transfinite_counts=(P["nx_xm10_to_0"], P["ny_0_10p235"]),
)
add_surface(
    [(-10.16, 10.235), (0.0, 10.235), (0.0, 11.0), (-10.16, 11.0)],
    "xneg10_to_0_mid",
    transfinite_counts=(P["nx_xm10_to_0"], P["ny_10p235_11"]),
)
add_surface(
    [(-10.16, 11.0), (0.0, 11.0), (0.0, 11.53), (-10.16, 11.53)],
    "xneg10_to_0_top",
    transfinite_counts=(P["nx_xm10_to_0"], P["ny_11_11p53"]),
)

# 7) 4 structured blocks for 0 < x < 20
add_surface(
    [(0.0, EPSILON), (20.0, EPSILON), (20.0, 10.235), (0.0, 10.235)],
    "x0_to_20_low",
    transfinite_counts=(P["nx_0_to_20"], P["ny_0_10p235"]),
)
add_surface(
    [(0.0, 10.235), (20.0, 10.235), (20.0, 11.0), (0.0, 11.0)],
    "x0_to_20_mid",
    transfinite_counts=(P["nx_0_to_20"], P["ny_10p235_11"]),
)
add_surface(
    [(0.0, 11.0), (20.0, 11.0), (20.0, 11.53), (0.0, 11.53)],
    "x0_to_20_top",
    transfinite_counts=(P["nx_0_to_20"], P["ny_11_11p53"]),
)
add_surface(
    [(0.0, 11.53), (20.0, 11.53), (20.0, 22.5), (0.0, 22.5)],
    "x0_to_20_upper",
    transfinite_counts=(P["nx_0_to_20"], 21),
)

# 8) Nozzle / downstream remaining region
p_d0 = pt(20.0, EPSILON)
p_51 = pt(*P["nozzle_p51"])
p_52 = pt(*P["nozzle_p52"])
p_53 = pt(*P["nozzle_p53"])
p_c1 = pt(*P["nozzle_c1_inside"])
p_c2 = pt(*P["nozzle_c2_outside"])
p_54 = pt(P["L_c"], P["r_chamber"])
p_20_10235 = pt(20.0, 10.235)
p_20_11 = pt(20.0, 11.0)
p_20_1153 = pt(20.0, 11.53)
p_d5 = pt(20.0, 22.5)

c_d0 = ln(p_d0, p_51)
c_bs_52_51 = geo.addBSpline([p_52, p_c2, p_51])
c_bs_53_52 = geo.addBSpline([p_53, p_c1, p_52])
c_54_53 = ln(p_54, p_53)
c_20_54 = ln(p_d5, p_54)
c_20_left_3 = ln(p_20_1153, p_d5)
c_20_left_2 = ln(p_20_11, p_20_1153)
c_20_left_1 = ln(p_20_10235, p_20_11)
c_20_left_0 = ln(p_d0, p_20_10235)

loop_down = geo.addCurveLoop([
    c_d0,
    -c_bs_52_51,
    -c_bs_53_52,
    -c_54_53,
    -c_20_54,
    -c_20_left_3,
    -c_20_left_2,
    -c_20_left_1,
    -c_20_left_0,
])
downstream_remaining = geo.addPlaneSurface([loop_down])
all_surfaces.append((downstream_remaining, "downstream_remaining"))

geo.synchronize()

# Transfinite settings
for surf, curves, (nx, ny), _name in structured:
    gmsh.model.mesh.setTransfiniteCurve(abs(curves[0]), nx)
    gmsh.model.mesh.setTransfiniteCurve(abs(curves[2]), nx)
    gmsh.model.mesh.setTransfiniteCurve(abs(curves[1]), ny)
    gmsh.model.mesh.setTransfiniteCurve(abs(curves[3]), ny)
    gmsh.model.mesh.setTransfiniteSurface(surf)
    gmsh.model.mesh.setRecombine(2, surf)

# Match segmentation at x=-128
plane20_left_segments = []
for y0, y1, ny in right_local_bands:
    if y1 <= 10.235:
        seg = abs(ln(pt(-128.0, y0), pt(-128.0, y1)))
        gmsh.model.mesh.setTransfiniteCurve(seg, ny)
        plane20_left_segments.append(seg)

plane20_right = abs(ln(pt(-10.16, EPSILON), pt(-10.16, 10.235)))
field_distance_p20_left = gmsh.model.mesh.field.add("Distance")
gmsh.model.mesh.field.setNumbers(field_distance_p20_left, "CurvesList", plane20_left_segments)
gmsh.model.mesh.field.setNumber(field_distance_p20_left, "Sampling", 100)
field_threshold_p20_left = gmsh.model.mesh.field.add("Threshold")
gmsh.model.mesh.field.setNumber(field_threshold_p20_left, "InField", field_distance_p20_left)
gmsh.model.mesh.field.setNumber(field_threshold_p20_left, "SizeMin", P["lc_plane20_left"])
gmsh.model.mesh.field.setNumber(field_threshold_p20_left, "SizeMax", P["lc_plane20_mid"])
gmsh.model.mesh.field.setNumber(field_threshold_p20_left, "DistMin", 0.0)
gmsh.model.mesh.field.setNumber(field_threshold_p20_left, "DistMax", 45.0)

field_distance_p20_right = gmsh.model.mesh.field.add("Distance")
gmsh.model.mesh.field.setNumbers(field_distance_p20_right, "CurvesList", [plane20_right])
gmsh.model.mesh.field.setNumber(field_distance_p20_right, "Sampling", 100)
field_threshold_p20_right = gmsh.model.mesh.field.add("Threshold")
gmsh.model.mesh.field.setNumber(field_threshold_p20_right, "InField", field_distance_p20_right)
gmsh.model.mesh.field.setNumber(field_threshold_p20_right, "SizeMin", P["lc_plane20_right"])
gmsh.model.mesh.field.setNumber(field_threshold_p20_right, "SizeMax", P["lc_plane20_mid"])
gmsh.model.mesh.field.setNumber(field_threshold_p20_right, "DistMin", 0.0)
gmsh.model.mesh.field.setNumber(field_threshold_p20_right, "DistMax", 35.0)

# Match left edge of downstream surface
for c, n in ((abs(c_20_left_0), P["ny_0_10p235"]), (abs(c_20_left_1), P["ny_10p235_11"]), (abs(c_20_left_2), P["ny_11_11p53"]), (abs(c_20_left_3), 21)):
    gmsh.model.mesh.setTransfiniteCurve(c, n)

field_distance_left = gmsh.model.mesh.field.add("Distance")
gmsh.model.mesh.field.setNumbers(field_distance_left, "CurvesList", [abs(c_20_left_0), abs(c_20_left_1), abs(c_20_left_2), abs(c_20_left_3)])
gmsh.model.mesh.field.setNumber(field_distance_left, "Sampling", 100)
field_threshold_left = gmsh.model.mesh.field.add("Threshold")
gmsh.model.mesh.field.setNumber(field_threshold_left, "InField", field_distance_left)
gmsh.model.mesh.field.setNumber(field_threshold_left, "SizeMin", P["lc_plane29_left"])
gmsh.model.mesh.field.setNumber(field_threshold_left, "SizeMax", P["lc_plane29_right"])
gmsh.model.mesh.field.setNumber(field_threshold_left, "DistMin", 0.0)
gmsh.model.mesh.field.setNumber(field_threshold_left, "DistMax", 120.0)

field_distance_nozzle = gmsh.model.mesh.field.add("Distance")
gmsh.model.mesh.field.setNumbers(field_distance_nozzle, "CurvesList", [abs(c_bs_52_51), abs(c_bs_53_52), abs(c_54_53)])
gmsh.model.mesh.field.setNumber(field_distance_nozzle, "Sampling", 100)
field_threshold_nozzle = gmsh.model.mesh.field.add("Threshold")
gmsh.model.mesh.field.setNumber(field_threshold_nozzle, "InField", field_distance_nozzle)
gmsh.model.mesh.field.setNumber(field_threshold_nozzle, "SizeMin", P["lc_nozzle_refine"])
gmsh.model.mesh.field.setNumber(field_threshold_nozzle, "SizeMax", P["lc_plane29_right"])
gmsh.model.mesh.field.setNumber(field_threshold_nozzle, "DistMin", 0.0)
gmsh.model.mesh.field.setNumber(field_threshold_nozzle, "DistMax", 25.0)

field_min = gmsh.model.mesh.field.add("Min")
gmsh.model.mesh.field.setNumbers(field_min, "FieldsList", [field_threshold_p20_left, field_threshold_p20_right, field_threshold_left, field_threshold_nozzle])
gmsh.model.mesh.field.setAsBackgroundMesh(field_min)

for surf, name in all_surfaces:
    if name in ("mid_block_-128_to_-10p16", "downstream_remaining"):
        gmsh.model.mesh.setRecombine(2, surf)

# Physical groups for clean export
pg = gmsh.model.addPhysicalGroup

wall_lines = sorted(set([
    abs(ln(pt(-140.0, EPSILON), pt(-140.0, 3.0))),
    abs(ln(pt(-160.0, 3.0), pt(-160.0, 3.8))),
    abs(ln(pt(-160.0, 3.8), pt(-160.0, 5.8))),
    abs(ln(pt(-160.0, 5.8), pt(-160.0, 6.3))),
    abs(ln(pt(-160.0, 6.3), pt(-160.0, 8.0))),
    abs(ln(pt(-160.0, 8.0), pt(-160.0, 8.3))),
    abs(ln(pt(-160.0, 8.3), pt(-160.0, 9.7))),
    abs(ln(pt(-160.0, 9.7), pt(-160.0, 10.235))),
    abs(ln(pt(-160.0, 10.235), pt(-146.0, 10.235))),
    abs(ln(pt(-146.0, 10.235), pt(-140.0, 10.235))),
    abs(ln(pt(-140.0, 10.235), pt(-128.0, 10.235))),
    abs(ln(pt(-128.0, 10.235), pt(-10.16, 10.235))),
    abs(ln(pt(-10.16, 10.235), pt(-10.16, 11.0))),
    abs(ln(pt(-10.16, 11.0), pt(-30.0, 11.0))),
    abs(ln(pt(-30.0, 11.0), pt(-30.0, 11.53))),
    abs(ln(pt(0.0, 11.53), pt(0.0, 22.5))),
    abs(ln(pt(0.0, 22.5), pt(20.0, 22.5))),
    abs(ln(pt(20.0, 22.5), pt(P["L_c"], 22.5))),
    abs(ln(pt(P["L_c"], 22.5), pt(*P["nozzle_p53"]))),
]))

fuel_inlet_lines = sorted(set([
    abs(ln(pt(-30.0, 11.53), pt(-10.16, 11.53))),
    abs(ln(pt(-10.16, 11.53), pt(0.0, 11.53))),
]))
outlet_lines = [abs(c_bs_52_51)]
# Note: axis line is now at y=EPSILON, treated as inner wall
axis_lines = sorted(set([
    abs(ln(pt(-140.0, EPSILON), pt(-128.0, EPSILON))),
    abs(ln(pt(-128.0, EPSILON), pt(-10.16, EPSILON))),
    abs(ln(pt(-10.16, EPSILON), pt(0.0, EPSILON))),
    abs(ln(pt(0.0, EPSILON), pt(20.0, EPSILON))),
    abs(ln(pt(20.0, EPSILON), pt(*P["nozzle_p51"]))),
]))

slot_phys = []
for i, (y0, y1) in enumerate(P["slots_y"], start=1):
    lines = [
        abs(ln(pt(-146.0, y0), pt(-140.0, y0))),
        abs(ln(pt(-140.0, y0), pt(-140.0, y1))),
        abs(ln(pt(-140.0, y1), pt(-146.0, y1))),
        abs(ln(pt(-146.0, y1), pt(-146.0, y0))),
    ]
    slot_phys.append((i, lines))

if wall_lines:
    gmsh.model.setPhysicalName(1, pg(1, wall_lines), "wall")
if fuel_inlet_lines:
    gmsh.model.setPhysicalName(1, pg(1, fuel_inlet_lines), "fuel_inlet")
if outlet_lines:
    gmsh.model.setPhysicalName(1, pg(1, outlet_lines), "outlet")
if axis_lines:
    gmsh.model.setPhysicalName(1, pg(1, axis_lines), "axis")
for i, lines in slot_phys:
    gmsh.model.setPhysicalName(1, pg(1, lines), f"oxidizer_slot_{i}")

gmsh.model.setPhysicalName(2, pg(2, [s for s, _ in all_surfaces]), "fluid")
for surf, name in all_surfaces:
    gmsh.model.setPhysicalName(2, pg(2, [surf]), name)

json_path = os.path.join(outdir, model_name + "_params.json")
with open(json_path, "w") as f:
    json.dump(P, f, indent=2)

geo_path = os.path.join(outdir, model_name + ".geo_unrolled")
msh_path = os.path.join(outdir, model_name + ".msh")
gmsh.model.mesh.generate(2)
gmsh.write(geo_path)
gmsh.write(msh_path)

print("Wrote:")
print(" ", geo_path)
print(" ", msh_path)
print(" ", json_path)
print("Surfaces:")
for surf, name in all_surfaces:
    print(f"  {surf}: {name}")

gmsh.finalize()