# CVRC Wedge Mesh - Quick Reference

## Directory Structure

```
cvrc_wedge_epsilon/
├── README.md                 # This file - overview and quick start
├── WEDGE_MESH_JOURNEY.md     # Detailed development history
├── REMAINING_ISSUES.md       # Known issues and resolutions
├── create_wedge_v9.py        # Gmsh script to generate the mesh
├── cvrc_2d_profile.geo_unrolled  # Source 2D geometry
├── cvrc_2d_profile.msh       # Source 2D mesh
├── cvrc_wedge_v9.msh          # Final 3D wedge mesh (Gmsh format)
├── 0/
│   └── U                      # Velocity initial/boundary conditions
├── system/
│   ├── controlDict            # OpenFOAM control dictionary
│   ├── fvSchemes              # Finite volume schemes
│   └── fvSolution             # Solver settings
└── constant/
    └── polyMesh/               # OpenFOAM mesh files
        ├── boundary            # Boundary patch definitions
        ├── faces               # Face definitions
        ├── neighbour           # Cell neighbor indices
        ├── owner               # Cell owner indices
        └── points              # Vertex coordinates
```

## Quick Start

### 1. Convert Gmsh to OpenFOAM

```bash
source /opt/openfoam7/etc/bashrc
gmshToFoam cvrc_wedge_v9.msh

# Remove unnecessary zone files created by gmshToFoam
rm -f constant/polyMesh/faceZones
rm -f constant/polyMesh/cellZones  
rm -f constant/polyMesh/pointZones
rm -rf constant/polyMesh/sets
```

### 2. Verify Mesh Quality

```bash
checkMesh
```

Expected output: `Mesh OK.`

### 3. Run Simulation

Adjust `0/U` and other field files for your specific case, then run your solver.

## Mesh Statistics

| Property | Value |
|----------|-------|
| Wedge angle | 5° total (2.5° each side) |
| Cells | 16,285 |
| Points | 32,682 |
| Hexahedra | 15,026 |
| Prisms | 1,259 |

## Boundary Patches

| Patch | Faces | Type | Description |
|-------|-------|------|-------------|
| wedgeFront | 16,285 | wedge | Front wedge face |
| wedgeBack | 16,285 | wedge | Back wedge face |
| wall | 701 | wall | Combustor walls |
| oxidizer_inlet | 31 | patch | Oxidizer inlet |
| fuel_inlet | 3 | patch | Fuel inlet |
| oxidizer_slot_1 | 28 | patch | Injection slot 1 |
| oxidizer_slot_2 | 26 | patch | Injection slot 2 |
| oxidizer_slot_3 | 24 | patch | Injection slot 3 |
| axis | 538 | empty | Symmetry axis |
| outlet | 24 | patch | Outlet |

## Known Differences from blockMesh Wedges

- This mesh has `axis` with 538 faces (Gmsh revolve creates these)
- blockMesh wedges have `axis` with 0 faces (degenerate faces removed)
- Both configurations work for OpenFOAM simulations
- The `***empty patches not divisible` message is expected for Gmsh-revolved wedges

## Regenerating the Mesh

```bash
conda activate agent
python3 create_wedge_v9.py
```

## Files to Modify for Your Case

- `0/U` - Velocity boundary conditions
- `0/p` - Pressure boundary conditions (create if needed)
- `system/controlDict` - Simulation control
- `system/fvSchemes` - Discretization schemes
- `system/fvSolution` - Solver settings

## References

- `WEDGE_MESH_JOURNEY.md` - Full development history with lessons learned
- `REMAINING_ISSUES.md` - Documentation of resolved issues