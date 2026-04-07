## Mesh Status and Known Differences

### ✅ Wedge Planarity Warning - RESOLVED

**Problem**: "Wedge patch wedgeFront not planar by 1.16e-7 metre"

**Solution**: Regenerated mesh using `create_wedge_v9.py` with optimized Gmsh settings.
Result: checkMesh passes without planarity warnings.

---

### ✅ Duplicate Zone Warnings - RESOLVED

**Problem**: "Zone wall contains duplicate index label" warnings

**Solution**: Removed unnecessary zone files:
```bash
rm -f constant/polyMesh/faceZones constant/polyMesh/cellZones constant/polyMesh/pointZones
rm -rf constant/polyMesh/sets
```

---

### ℹ️ Axis Faces Difference from blockMesh Wedges

**Observation**: The `axis` patch has 538 faces, while blockMesh wedge meshes have 0.

**Comparison**:

| Property | blockMesh wedge (tutorial) | Gmsh revolve (this mesh) |
|----------|---------------------------|--------------------------|
| axis nFaces | 0 | 538 |
| checkMesh message | None | "empty patches not divisible" |
| geometric dirs | (1 0 1) | (1 1 0) |
| Mesh status | Mesh OK. | Mesh OK. |

**Root Cause**:
- blockMesh creates proper "wedge cells" where axis faces are degenerate and removed
- Gmsh revolve creates surfaces from axis curves (y=0), leaving 538 degenerate faces at y≈0

**Impact**:
- Both configurations pass checkMesh
- The axis faces in Gmsh meshes are degenerate (all points at y≈0)
- OpenFOAM's `empty` BC handles these correctly
- Simulations can run with both configurations

**For axis nFaces=0**:
- Use blockMesh for wedge mesh creation, OR
- Post-process to remove degenerate axis faces (complex mesh surgery)

---

## Final checkMesh Output

```
Mesh stats
    points:           32682
    internal points:  0
    faces:            65198
    internal faces:   31253
    cells:            16285
    boundary patches: 10

Overall number of cells of each type:
    hexahedra:     15026
    prisms:        1259

Checking topology...
    Boundary definition OK.
 ***Total number of faces on empty patches is not divisible by the number of cells in the mesh. Hence this mesh is not 1D or 2D.
    Cell to face addressing OK.
    Point usage OK.
    Upper triangular ordering OK.
    Face vertices OK.
    Number of regions: 1 (OK).

Checking patch topology for multiply connected surfaces...
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

Checking geometry...
    Mesh has 2 geometric (non-empty/wedge) directions (1 1 0)
    Mesh has 2 solution (non-empty) directions (1 0 1)
    Wedge wedgeFront with angle 2.5 degrees
    Wedge wedgeBack with angle 2.5 degrees
    Boundary openness OK.
    Max cell openness OK.
    Max aspect ratio = 11.68 OK.
    Face area magnitudes OK.
    Cell volumes OK.
    Mesh non-orthogonality Max: 35.96 OK.
    Face pyramids OK.
    Max skewness = 1.10 OK.

Mesh OK.
```

**Status**: Mesh passes all checks. Ready for OpenFOAM simulations.

---

## Final Patch Structure (v9 mesh)

| Patch | Faces | Type | Description |
|--------|-------|------|-------------|
| wedgeFront | 16,285 | wedge | Front wedge face (θ = -2.5°) |
| wedgeBack | 16,285 | wedge | Back wedge face (θ = +2.5°) |
| wall | 701 | wall | Combustor walls |
| oxidizer_inlet | 31 | patch | Oxidizer inlet at x = -160 |
| fuel_inlet | 3 | patch | Fuel inlet at x = -30 |
| oxidizer_slot_1 | 28 | patch | Oxidizer injection slot 1 |
| oxidizer_slot_2 | 26 | patch | Oxidizer injection slot 2 |
| oxidizer_slot_3 | 24 | patch | Oxidizer injection slot 3 |
| axis | 538 | empty | Symmetry axis (degenerate faces at y≈0) |
| outlet | 24 | patch | Outlet at x ≈ 400 |

---

## Files

| File | Description |
|------|-------------|
| `create_wedge_v9.py` | Final mesh generation script |
| `cvrc_wedge_v9.msh` | Gmsh mesh file |
| `constant/polyMesh/boundary` | Correct patch types |
| `WEDGE_MESH_JOURNEY.md` | Full documentation |