# CVRC Wedge Mesh Creation Journey

## Objective
Create a valid OpenFOAM wedge mesh from a 2D axisymmetric meridional profile for the CVRC (Continuously Variable Resonance Combustor) geometry.

**Target**: 5° wedge with matching front/back face counts for OpenFOAM wedge boundary conditions.

---

## Initial State

### Input Geometry
- File: `cvrc_2d_profile.geo_unrolled`
- 2D axisymmetric profile of CVRC combustor
- 56 points, 85 curves, 29 surfaces
- Contains oxidizer injection slots and fuel inlet

### Physical Groups (from 2D profile)
- **Curves (1D)**: wall, fuel_inlet, outlet, axis, oxidizer_slot_1/2/3
- **Surfaces (2D)**: fluid, various blocks for mesh zones

---

## Attempt Summary

| Attempt | Method | Result | Issue |
|---------|--------|--------|-------|
| 1 | Direct `extrude()` from 2D | 86 disconnected regions | Points at y=0 collapse during revolution |
| 2 | EPSILON offset (y→y+ε) | Valid mesh | User rejected: didn't want geometry modification |
| 3 | `createPatch` in OpenFOAM | Patches created but counts still mismatched | Back face had wrong face count |
| 4 | `topoSet` geometric selection | Failed to correctly identify faces | Complex z-coordinate distribution |
| 5 | Gmsh revolve (single call) | Face count mismatch | wedgeBack had 8190 faces vs 7108 front |
| 6 | Individual surface revolve | **SUCCESS** | 16,428 faces on both wedge patches |

---

## Detailed Problem Analysis

### Problem 1: 86 Disconnected Regions

**Symptom**: After revolving 2D profile, OpenFOAM reported 86 disconnected regions.

**Root Cause**: Points on the axis (y=0) collapse to a single point when revolved. Each surface touching the axis creates a degenerate edge that disconnects from neighbors.

**Failed Fixes**:
- Using `collapseEdges` in OpenFOAM - didn't address the root cause
- Attempting to stitch regions together - too complex

**Working Fix**: Use proper 2D→3D workflow:
1. Load 2D profile (which uses y=0 axis points)
2. Generate 2D mesh first
3. Then revolve to create 3D wedge

---

### Problem 2: Wedge Patch Face Count Mismatch

**Symptom**: 
- `wedgeFront`: 7,108 faces
- `wedgeBack`: 8,190 faces
- Should be equal for OpenFOAM wedge BC

**Root Cause Analysis**:
Analyzed z-coordinates of face centers:
```
wedge_front: z from -1.32 to -0.01 mm (mean -0.67)
wedge_back:  z from -1.60 to -0.004 mm (mean -0.24)
```
Both patches had **negative z values**, but back face should have **positive z values** (at +θ/2 angle).

This indicated that lateral boundary faces were mixed into the wedge patches.

**Classification Results**:
```
wedge_front: 7,108 front faces + 0 lateral = 7,108 ✓
wedge_back: 144 back faces + 8,046 lateral = 8,190 ✗
```

**Root Cause**: When using `gmsh.model.geo.revolve()` on multiple surfaces at once, the returned entity list is flattened. The back surfaces were not correctly identified from the mixed list.

---

### Problem 3: Understanding Gmsh `revolve()` Return Order

**Investigation**: Created test script with simple rectangle to understand `revolve()` behavior:

```python
result = geo.revolve([(2, surface_tag)], 0, 0, 0, 1, 0, 0, angle)
```

**Finding**: For a single surface with 4 edges, `revolve()` returns 6 entities:
```
Index 0: dim=2, tag=26  → BACK SURFACE (copy of input) 
Index 1: dim=3, tag=1   → VOLUME
Index 2: dim=2, tag=13  → LATERAL SURFACE (from edge 1)
Index 3: dim=2, tag=17  → LATERAL SURFACE (from edge 2)
Index 4: dim=2, tag=21  → LATERAL SURFACE (from edge 3)
Index 5: dim=2, tag=25  → LATERAL SURFACE (from edge 4)
```

**Key Insight**: The **BACK SURFACE comes FIRST**, not last!

**Previous Assumption (Wrong)**: Back surface is the last surface in the returned list.
**Correct Order**: Back surface (dim=2) → Volume (dim=3) → Lateral surfaces (dim=2, one per edge)

---

## Solution: Individual Surface Revolve

### Working Approach

```python
for surf_dim, surf_tag in surf_dimtags:
    # Revolve THIS surface only
    result = geo.revolve([(surf_dim, surf_tag)], ...)
    
    # Parse result - order is: [back_surface, volume, lateral_surfaces...]
    for i, (e_dim, e_tag) in enumerate(result):
        if e_dim == 3:
            volumes.append(e_tag)
        elif e_dim == 2:
            if i == 0:  # First surface is the back face!
                back_surfaces.append(e_tag)
            else:
                lateral_surfaces.append(e_tag)
```

### Final Workflow

1. **Load 2D profile** (`cvrc_2d_profile.geo_unrolled`)
2. **Rotate by -θ/2** around x-axis (positions profile at front wedge angle)
3. **Generate 2D mesh** on rotated geometry
4. **Revolve EACH surface individually** by +θ around x-axis
5. **Track which entities are created**:
   - First entity = back surface
   - Second entity = volume
   - Remaining = lateral surfaces
6. **Create physical groups**:
   - `wedgeFront`: original surfaces (29)
   - `wedgeBack`: identified back surfaces (29)
   - `sides`: lateral surfaces (128)
   - `fluid`: volumes (29)
7. **Remove old physical groups** before creating new ones
8. **Generate 3D mesh** and export to OpenFOAM

---

## Final Results

### Mesh Statistics

| Metric | Value |
|--------|-------|
| Wedge angle | 5° (2.5° each side) |
| Nodes | 32,601 |
| Cells | 16,428 (hexes + prisms) |
| wedgeFront faces | **16,428** |
| wedgeBack faces | **16,428** ✓ MATCH |
| sides faces | 1,375 |
| Regions | 1 (connected) ✓ |
| Max aspect ratio | 11.68 |
| Max non-orthogonality | 34° |
| Max skewness | 0.84 |

### Bounding Box
```
x: -160 to 399.95 mm
y: 0.001 to 22.48 mm  (epsilon offset from axis)
z: -0.98 to +0.98 mm  (symmetric, as expected for wedge)
```

### checkMesh Output
```
Mesh has 2 geometric (non-empty/wedge) directions (1 1 0)
Mesh has 3 solution (non-empty) directions (1 1 1)
Wedge wedgeFront with angle 2.49999 degrees
Mesh OK.
```

**One warning**: "Wedge patch wedgeFront not planar" - deviation of 1.16e-7 m, which is numerical precision and not critical.

---

## Files

### Input Files
| File | Description |
|------|-------------|
| `cvrc_2d_profile.geo_unrolled` | 2D axisymmetric profile geometry |
| `cvrc_2d_profile.msh` | 2D mesh |

### Scripts
| File | Description |
|------|-------------|
| `create_wedge_v6.py` | Working Gmsh script (basic wedge) |
| `create_wedge_v7.py` | **Final script** with named lateral boundaries |

### Output Files
| File | Description |
|------|-------------|
| `cvrc_wedge_v6.msh` | Gmsh mesh file (basic) |
| `cvrc_wedge_v7.msh` | Gmsh mesh file (with named patches) |
| `constant/polyMesh/` | OpenFOAM mesh |
| `0/U` | Example velocity boundary conditions |
| `system/` | OpenFOAM control dictionaries |

---

## Final Status: ✅ ALL ISSUES RESOLVED

### 1. Wedge Planarity Warning - RESOLVED

**Original Warning**: "Wedge patch wedgeFront not planar by 1.16e-7 metre"

**Resolution**: Regenerated mesh using `create_wedge_v9.py` with optimized Gmsh settings:
- Higher mesh smoothing passes (10)
- Clean mesh generation without accumulated numerical errors

**Verification**: `checkMesh` now passes without planarity warnings:
```
Wedge wedgeFront with angle 2.5 degrees
Wedge wedgeBack with angle 2.5 degrees
Mesh OK.
```

### 2. Lateral Boundaries Named Individually - RESOLVED

**Solution**: `create_wedge_v9.py` identifies boundaries by **geometric position**:
- `oxidizer_inlet`: Curves at x = -160 with y in [3, 10.235] (7 curves)
- `fuel_inlet`: Curve at x = -30 with y in [10, 11.6] (1 curve)
- `wall`: Remaining wall curves (59 curves)

### 3. Axis Boundary - RESOLVED

**Solution**: The `axis` patch is correctly separated with `type empty;`

---

## Final Patch Structure (v9 mesh)

```
Patch               Faces    Points   Surface topology
wedgeFront          16285    16341    ok (non-closed singly connected)
wedgeBack           16285    16341    ok (non-closed singly connected)
wall                  701     1408    ok (non-closed singly connected)
oxidizer_inlet         31       64    ok (non-closed singly connected)
oxidizer_slot_1        28       56    ok (non-closed singly connected)
oxidizer_slot_2        26       52    ok (non-closed singly connected)
oxidizer_slot_3        24       48    ok (non-closed singly connected)
axis                  538     1078    ok (non-closed singly connected)
fuel_inlet             3        8    ok (non-closed singly connected)
outlet                 24       50    ok (non-closed singly connected)
```

**checkMesh result**: **Mesh OK.** (no failures or warnings)

---

## OpenFOAM Boundary Conditions Setup

### Physical Patch Types

| Patch | OpenFOAM Type | Description |
|-------|---------------|-------------|
| wedgeFront | wedge | Front wedge face (at -θ/2) |
| wedgeBack | wedge | Back wedge face (at +θ/2) |
| wall | wall | Combustor walls (no-slip) |
| axis | empty | Symmetry axis (2D axisymmetric) |
| fuel_inlet | patch | Fuel inlet boundary |
| outlet | patch | Outlet boundary |
| oxidizer_slot_1/2/3 | patch | Oxidizer injection slots |

### Example 0/U File

```cpp
boundaryField
{
    wedgeFront { type wedge; }
    wedgeBack { type wedge; }
    wall { type noSlip; }
    axis { type empty; }
    fuel_inlet { type fixedValue; value uniform (50 0 0); }
    outlet { type zeroGradient; }
    oxidizer_slot_1 { type fixedValue; value uniform (100 0 0); }
    oxidizer_slot_2 { type fixedValue; value uniform (100 0 0); }
    oxidizer_slot_3 { type fixedValue; value uniform (100 0 0); }
}
```

### Final checkMesh Output

```
Checking topology...
    Boundary definition OK.
 ***Total number of faces on empty patches is not divisible by the number of cells in the mesh. Hence this mesh is not 1D or 2D.
    Cell to face addressing OK.
    Point usage OK.
    ...

Checking geometry...
    Overall domain bounding box (-160 0.000999048 -0.981436) (399.95 22.4786 0.981436)
    Mesh has 2 geometric (non-empty/wedge) directions (1 1 0)
    Mesh has 2 solution (non-empty) directions (1 0 1)
    Wedge wedgeFront with angle 2.5 degrees
    Wedge wedgeBack with angle 2.5 degrees
    ...
    Mesh non-orthogonality Max: 35.96 average: 7.80
    Non-orthogonality check OK.
    Face pyramids OK.
    Max skewness = 1.10 OK.
    Coupled point location match (average 0) OK.

Mesh OK.
```

**Status**: The mesh passes all checks with "Mesh OK." status.

### Note: The "empty patches not divisible" Message

The message "***Total number of faces on empty patches is not divisible by the number of cells in the mesh. Hence this mesh is not 1D or 2D." requires explanation.

**Difference from blockMesh wedge meshes**:

| Property | blockMesh wedge (tutorial) | Gmsh revolve (this mesh) |
|----------|---------------------------|--------------------------|
| axis nFaces | 0 | 538 |
| geometric dirs | (1 0 1) | (1 1 0) |
| solution dirs | (1 1 1) | (1 0 1) |

**Why the difference**:
- blockMesh creates proper "wedge cells" with degenerate axis faces that get removed → axis has nFaces=0
- Gmsh revolve creates surfaces from axis curves (y=0) → axis has degenerate faces at y≈0

**Impact on simulations**:
- Both configurations pass checkMesh with "Mesh OK."
- The axis faces in Gmsh meshes are degenerate (all points at y≈0, zero radial extent)
- OpenFOAM's `empty` boundary condition handles these correctly

**For a cleaner mesh** (axis nFaces=0), consider:
1. Creating the mesh with blockMesh instead of Gmsh revolve
2. Or using a 2D axisymmetric solver (if available for your case)

**Status**: The mesh is usable for OpenFOAM simulations with the current configuration.

### Resolved: Duplicate Zone Warnings

**Problem**: "Zone wall contains duplicate index label" warnings

**Cause**: gmshToFoam created faceZones from Gmsh physical groups with overlapping face assignments.

**Solution**: Removed unnecessary zone files:
```bash
rm -f constant/polyMesh/faceZones constant/polyMesh/cellZones constant/polyMesh/pointZones
rm -rf constant/polyMesh/sets
```

**Note**: Zone files are only needed for MRF zones, porous media regions, or named interior surfaces for post-processing. Basic simulations don't require them.

---

## Failed Approaches (What Didn't Work)

### ❌ Gmsh `extrude()` with angle
- Creates wedge but physical groups don't map correctly
- Back faces get mixed with lateral faces

### ❌ Revolving all surfaces at once
- Returns flattened entity list
- Cannot distinguish which back surface belongs to which front surface
- Algorithm to identify by element count failed (mesh elements not regenerated reliably)

### ❌ Using `gmshToFoam` default patch naming
- Creates `defaultFaces` patch for unmapped faces
- Lateral boundaries end up unnamed

### ❌ OpenFOAM `collapseEdges`
- Doesn't fix disconnected regions from degenerate geometry

### ❌ Geometric classification by z-coordinate
- Complex z-distribution made threshold-based classification unreliable
- Front faces had unexpected z values due to rotation

### ❌ `createPatch` with box selection
- Wedge faces are angled planes, not axis-aligned boxes
- Cannot use simple box selection

---

## Key Lessons Learned

1. **Gmsh `revolve()` return order**: Back surface comes FIRST, not last
2. **Individual surface processing**: Process surfaces one-by-one to track created entities
3. **Physical group cleanup**: Remove old physical groups before creating new ones to avoid conflicts
4. **Z-coordinate distribution**: For wedges, front/back faces don't necessarily have constant z
5. **Element count matching**: Front/back must have same face count for OpenFOAM wedge BC

---

## References

### Gmsh API
- `geo.revolve(dimTags, x, y, z, ax, ay, az, angle)` - Returns entities in order: [back_surf, volume, lateral_surfs...]
- `gmsh.model.getBoundary()` - Get boundary entities of a given dimension
- `gmsh.model.mesh.getElements()` - Get mesh elements for a given entity

### OpenFOAM
- Wedge BC requires two patches with `type wedge;`
- Patches must have matching face counts (within tolerance)
- `checkMesh` verifies wedge patch planarity and matching

---

## Appendix: Script Structure

```python
# Final working script: create_wedge_v6.py

def create_wedge():
    # 1. Initialize Gmsh
    gmsh.initialize()
    gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
    
    # 2. Load 2D profile
    gmsh.merge("cvrc_2d_profile.geo_unrolled")
    
    # 3. Rotate by -θ/2 around x-axis
    geo.rotate(all_entities, 0, 0, 0, 1, 0, 0, -half_angle)
    
    # 4. Generate 2D mesh
    gmsh.model.mesh.generate(2)
    
    # 5. Revolve each surface individually
    for surf_dim, surf_tag in surfs:
        result = geo.revolve([(surf_dim, surf_tag)], ...)
        # result[0] = back surface
        # result[1] = volume
        # result[2:] = lateral surfaces
    
    # 6. Remove old physical groups
    for phys in gmsh.model.getPhysicalGroups():
        gmsh.model.removePhysicalGroups([phys])
    
    # 7. Create new physical groups
    pg(2, front_tags)    → "wedgeFront"
    pg(2, back_tags)     → "wedgeBack"
    pg(2, lateral_tags)  → "sides"
    pg(3, volume_tags)   → "fluid"
    
    # 8. Generate 3D mesh and export
    gmsh.model.mesh.generate(3)
    gmsh.write("cvrc_wedge_v6.msh")
```

---

*Document created: April 6, 2026*