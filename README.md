# CVRC Combustor — dfHighSpeedFoam Simulation

Axisymmetric 2D-wedge simulation of the Continuously Variable Resonance
Combustor (CVRC) using DeepFlame's density-based compressible reacting solver.

## Quick Start

```bash
# 1. Environment
source /opt/openfoam7/etc/bashrc
conda activate agent
source /home/xk/deepflame/df_1be82b6/deepflame-dev/bashrc

# 2. Regenerate mesh (if needed)
./scripts/run_mesh_pipeline.sh --param --clean

# 3. Prepare fields
cp -r 0.orig 0

# 4. Decompose & run
decomposePar
mpirun -np 8 dfHighSpeedFoam -parallel > log.dfHighSpeedFoam 2>&1 &
```

## Directory Layout

```
.
├── 0/                    Working field files (copied from 0.orig)
├── 0.orig/               Canonical initial/boundary conditions
│   ├── U                 Velocity (ramped inlet: 0→100 m/s over 0.5 ms)
│   ├── T                 Temperature (300 K ambient, 1029 K oxidizer inlet)
│   ├── p                 Pressure (101325 Pa)
│   ├── CH4               Methane mass fraction (1.0 at fuel inlet)
│   ├── O2                Oxygen (0.42 at oxidizer inlet)
│   ├── H2O               Water (0.58 at oxidizer inlet)
│   ├── N2                Nitrogen (inert, Y=0 everywhere)
│   └── Ydefault          Default species BC (zeroGradient walls)
├── 0.00025/ … 0.001/    Reconstructed solution snapshots (inert flow)
├── constant/
│   ├── polyMesh/         72k-cell wedge mesh (extrudeMesh from Gmsh slab)
│   ├── CanteraTorchProperties   Chemistry config (off locally, on for server)
│   ├── combustionProperties     Laminar combustion model
│   ├── thermophysicalProperties Inviscid=false
│   └── turbulenceProperties     Laminar (no turbulence model)
├── system/
│   ├── controlDict       dt=5e-8, fixed, Tadmor flux
│   ├── fvSchemes         Tadmor + Minmod limiters
│   ├── fvSolution        PBiCGStab solvers
│   ├── decomposeParDict  scotch, 32 domains (local) / 128 (SCNET)
│   ├── extrudeMeshDict   Wedge 5° from slab back patch
│   └── setFieldsDict     (NOT used — creates instabilities)
├── scripts/
│   ├── run_mesh_pipeline.sh          Full mesh pipeline
│   └── mesh/
│       ├── parameterize_mesh_full.py Constraint-aware mesh parameteriser
│       ├── create_slab_mesh.py       Gmsh → 1-cell slab mesh
│       ├── cvrc_2d_profile.geo_unrolled        Original geometry
│       └── cvrc_2d_profile_param.geo_unrolled  Parameterised geometry
├── docs/
│   ├── stability_fixes.md   Crash analysis & fix log
│   └── mesh_pipeline.md     Mesh generation documentation
├── gri30.yaml               GRI-Mech 3.0 (53 species)
└── log.dfHighSpeedFoam      Inert-flow run log (1 ms, SCNET 32 cores)
```

## Mesh

- **72k cells**, 2D axisymmetric wedge (5°, ±2.5°)
- Generated via: Gmsh 2D → slab extrude → `gmshToFoam` → `extrudeMesh wedge`
- Structured transfinite blocks (inlet, slots, axis, fuel, chamber)
  + unstructured regions (oxidizer plenum, combustion chamber)
- Parameterised: edit `scripts/mesh/parameterize_mesh_full.py` for node counts,
  grading, sizing fields, and characteristic lengths
- See `docs/mesh_pipeline.md` for details

## Boundary Conditions

| Patch | Type | U | T | p | Species |
|-------|------|---|---|---|---------|
| oxidizer_inlet | inlet | ramp 0→100 m/s (0.5ms) | 1029 K | zeroGradient | O2=0.42, H2O=0.58 |
| fuel_inlet | inlet | ramp 0→33 m/s (0.5ms) | 300 K | zeroGradient | CH4=1.0 |
| outlet | outlet | zeroGradient | zeroGradient | 101325 Pa | zeroGradient |
| wall, slot_1/2/3 | wall | noSlip | zeroGradient | zeroGradient | zeroGradient |
| back, front | wedge | wedge | wedge | wedge | wedge |
| axis | empty | empty | empty | empty | empty |

## Key Decisions

- **Velocity ramping** (0→full over 0.5ms): prevents impulsive pressure
  waves through narrow slots — the single most important stability fix
- **Tadmor flux**: most dissipative, most stable for narrow-slot geometry
  (Kurganov tested and rejected — 32× less stable)
- **No setFields**: sharp T discontinuities (1029 vs 300 K) cause worse
  crashes than gradual startup from uniform cold field
- **dt = 5e-8 s** (fixed): gives max Co ≈ 0.15, stable through ramp

## SCNET HPC Runs

| Run | Cores | Chemistry | Time range | Status |
|-----|-------|-----------|------------|--------|
| Inert flow | 32 | off | 0→1 ms | ✅ Complete (4.7h) |
| Reacting flow | 128 | on (GRI-3.0) | 1→11 ms | 🔄 Running (job 111153724, ETA ~58h) |
