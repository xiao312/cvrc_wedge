# CVRC Wedge Mesh for OpenFOAM

## Overview

This directory contains the final mesh for the CVRC (Continuously Variable Resonance Combustor) axisymmetric combustor simulation in OpenFOAM.

## Quick Start

```bash
# Convert Gmsh mesh to OpenFOAM format
gmshToFoam cvrc_wedge_v9.msh

# Remove unnecessary zone files created by gmshToFoam
rm -f constant/polyMesh/faceZones constant/polyMesh/cellZones constant/polyMesh/pointZones
rm -rf constant/polyMesh/sets

# Update boundary types
# (boundary file is already configured with correct patch types)

# Check mesh quality
checkMesh
```

## Mesh Specifications

| Property | Value |
|----------|-------|
| Wedge angle | 5° total (2.5° each side) |
| Cells | 16,285 |
| Points | 32,682 |
| Mesh type | Hex-dominant with prisms near axis |

## Boundary Patches

| Patch | Faces | Type | Description |
|-------|-------|------|-------------|
| wedgeFront | 16,285 | wedge | Front wedge face (θ = -2.5°) |
| wedgeBack | 16,285 | wedge | Back wedge face (θ = +2.5°) |
| wall | 701 | wall | Combustor walls |
| oxidizer_inlet | 31 | patch | Oxidizer inlet at x = -160 mm |
| fuel_inlet | 3 | patch | Fuel inlet at x = -30 mm |
| oxidizer_slot_1/2/3 | 28/26/24 | patch | Oxidizer injection slots |
| axis | 538 | empty | Symmetry axis (y ≈ 0) |
| outlet | 24 | patch | Outlet at x ≈ 400 mm |

## Files

| File | Description |
|------|-------------|
| `create_wedge_v9.py` | Gmsh Python script to generate the wedge mesh |
| `cvrc_2d_profile.geo_unrolled` | Source 2D geometry (Gmsh geo format) |
| `cvrc_2d_profile.msh` | Source 2D mesh |
| `cvrc_wedge_v9.msh` | Final 3D wedge mesh (Gmsh format) |
| `constant/polyMesh/` | OpenFOAM mesh files |
| `system/` | OpenFOAM control dictionaries |
| `0/` | Initial conditions directory |
| `WEDGE_MESH_JOURNEY.md` | Detailed development history |
| `REMAINING_ISSUES.md` | Known issues and resolutions |

## Regenerating the Mesh

```bash
# Activate conda environment with Gmsh
conda activate agent

# Run the mesh generation script
python3 create_wedge_v9.py

# Convert to OpenFOAM format
source /opt/openfoam7/etc/bashrc
gmshToFoam cvrc_wedge_v9.msh

# Clean up zone files
rm -f constant/polyMesh/faceZones constant/polyMesh/cellZones constant/polyMesh/pointZones
rm -rf constant/polyMesh/sets
```

## Known Issues

### Axis Faces (Gmsh vs blockMesh)

Gmsh-revolved wedge meshes have axis faces (nFaces=538) while blockMesh wedges have nFaces=0.
This is expected behavior:
- Gmsh creates surfaces from axis curves during revolution
- These faces are degenerate (all points at y≈0)
- OpenFOAM handles them correctly with `type empty`

### checkMesh Warning

The message `"***Total number of faces on empty patches is not divisible by the number of cells"` is informational for wedge meshes. The mesh passes all checks with "Mesh OK."

## References

- See `WEDGE_MESH_JOURNEY.md` for detailed development history
- See `REMAINING_ISSUES.md` for resolved issues and known limitations

## License

Generated for CVRC combustor CFD research.