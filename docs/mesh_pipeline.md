# CVRC Mesh Pipeline Documentation

## Overview

The mesh is a **2D axisymmetric wedge** (5° total, ±2.5°) for the CVRC combustor.
It uses a two-stage approach:

1. **Gmsh**: mesh 2D profile → extrude to 1-cell slab in z
2. **OpenFOAM `extrudeMesh`**: rotate the slab into a wedge

This produces a proper wedge mesh that OpenFOAM recognises as 2D axisymmetric
(max AR = 5.9, correct `Mesh has 2 geometric directions`).

## Pipeline

```
./scripts/run_mesh_pipeline.sh [--param] [--clean]
```

| Step | Tool | Description |
|------|------|-------------|
| 0 | — | Clean old mesh (if `--clean`) |
| 1 | `parameterize_mesh_full.py` | Apply custom parameters (if `--param`) |
| 2 | `create_slab_mesh.py` | Gmsh: 2D mesh → 1-cell slab → `.msh` |
| 3 | `gmshToFoam` | Import to OpenFOAM polyMesh |
| 4 | `transformPoints` | Scale mm → m |
| 5 | `extrudeMesh` | Rotate slab into 5° wedge |
| 6 | Python | Fix boundary types (axis→empty, walls→wall) |
| 7 | `checkMesh` | Verify mesh quality |

## Mesh Parameteriser

`scripts/mesh/parameterize_mesh_full.py` controls **all** mesh parameters:

### A. Transfinite node counts (21 constraint chains, 78 curves)

Opposite edges of each transfinite surface **must** have matching node counts.
The parameteriser enforces this via verified connectivity chains.

**Y-direction (radial) — 12 chains:**

| Parameter | Nodes | Span (mm) | Cell (mm) | Lines |
|-----------|-------|-----------|-----------|-------|
| NY_LAYER_1 | 4 | 0.80 | 0.27 | 2,4,24,39 |
| NY_LAYER_2 | 9 | 2.00 | 0.25 | 5,7,41,43 |
| NY_LAYER_3 | 3 | 0.50 | 0.25 | 8,10,27,44 |
| NY_LAYER_4 | 8 | 1.70 | 0.24 | 11,13,46,48 |
| NY_LAYER_5 | 3 | 0.30 | 0.15 | 14,16,30,49 |
| NY_LAYER_6 | 7 | 1.40 | 0.23 | 17,19,51,53 |
| NY_LAYER_7 | 4 | 0.54 | 0.18 | 20,22,33,54 |
| NY_AXIS_H | 13 | 3.00 | 0.25 | 36,38 |
| NY_MID_VERT | 49 | 10.24 | 0.21 | 57,64,72 |
| NY_FUEL_OUTER | 4 | 0.77 | 0.26 | 60,62,69,76 |
| NY_FUEL_INNER | 4 | 0.53 | 0.18 | 66,68,74 |
| NY_UPPER | 35 | 10.97 | 0.32 | 78,80 |

**X-direction (axial) — 9 chains:**

| Parameter | Nodes | Span (mm) | Cell (mm) | Lines |
|-----------|-------|-----------|-----------|-------|
| NX_INLET | 17 | 14 | 0.88 | 1,3,6,9,12,15,18,21 |
| NX_SLOT_1–4 | 11 | 18 | 1.80 | 23,25 / 26,28 / 29,31 / 32,34 |
| NX_AXIS | 50 | 117.8 | 2.40 | 35,37,40,42,45,47,50,52,55 |
| NX_FUEL | 31 | 30 | 1.00 | 59,61 |
| NX_CHAMBER_CONN | 17 | 20 | 1.25 | 63,65,67,70 |
| NX_CHAMBER | 120 | 361 | 3.03 | 71,73,75,77,79 |

### B. Transfinite grading

Each chain has a `_GRAD` companion for `Progression` or `Bump` control.
Per-line overrides via `LINE_GRAD_OVERRIDES` dict.

### C. Unstructured size fields

4 Distance/Threshold pairs control cell size in unstructured regions
(Surfaces 20 and 29).  Parameters: `SizeMin`, `SizeMax`, `DistMin`,
`DistMax`, `Sigmoid`, `StopAtDistMax`.

### D. Point characteristic lengths

`CL_STRUCTURED` (0.25), `CL_CHAMBER_ENTRANCE` (0.3),
`CL_FAR_FIELD` (2.5), `CL_OUTLET` (1.5), `CL_NOZZLE` (1.2).

## Mesh Quality (current)

| Metric | Value |
|--------|-------|
| Cells | 71,986 |
| Max aspect ratio | 5.93 |
| Max non-orthogonality | 35.7° |
| Max skewness | 0.93 |
| Geometric directions | 2 (correct 2D wedge) |
| Wedge angle | 2.5° each side |

## Previous Approach (superseded)

The earlier workflow used Gmsh's `revolve` to directly create the wedge in
Gmsh.  This produced a mesh with max AR = 67.6 (from thin z-cells at the
axis) that OpenFOAM misidentified as 3D.  The current slab → `extrudeMesh`
approach is superior in every metric.
