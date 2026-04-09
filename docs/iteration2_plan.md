# CVRC Simulation Improvement Plan — Iteration 2

## Status After Iteration 1

| Run | Time reached | Crash cause |
|-----|-------------|-------------|
| Inert flow (no chemistry) | 1.0 ms ✅ | — |
| Chemistry ON (GRI-3.0) | 1.671 ms | T_min → 125K in fuel pipe, Cantera failed |

Chemistry ran for 671 µs (13,422 steps) before crashing. T_min was steadily
declining (~0.12 K/step) in the fuel pipe region due to expansion cooling of
CH4 through the narrow passage. T_max was stable at 1270K — no runaway.

---

## Improvement Areas

### 1. Corrected Boundary & Initial Conditions

**Problem:** Current setup uses ambient pressure (101.325 kPa) as outlet
backpressure and 300K/air as the internal field. The CVRC operates at elevated
chamber pressure (~1.4 MPa) and the combustion products fill the chamber.

**Corrections (from CVRC experimental conditions):**

| Field | Current | Corrected |
|-------|---------|-----------|
| p (outlet BC) | 101,325 Pa (fixedValue) | 1,400,000 Pa (fixedValue) |
| p (initial internal) | 101,325 Pa | 1,400,000 Pa |
| p (oxidizer/fuel inlet) | zeroGradient | zeroGradient (unchanged) |
| T (initial internal) | 300 K | 1500 K |
| T (oxidizer inlet BC) | 1029 K | 1029 K (unchanged) |
| T (fuel inlet BC) | 300 K | 300 K (unchanged) |
| Species (initial internal) | air (O2=0.233, N2=0.767) | 29% CO2, 71% H2O |
| Species (oxidizer inlet) | O2=0.42, H2O=0.58 | unchanged |
| Species (fuel inlet) | CH4=1.0 | unchanged |

**Rationale:** Initialising with hot combustion products at chamber pressure
means the flow develops from a physically realistic state. The solver doesn't
need to build up pressure from atmospheric — eliminating the huge density
mismatch that causes expansion cooling in the fuel pipe.

**Implementation:**
- Update `0.orig/p`: `internalField uniform 1400000;`, outlet `fixedValue 1400000;`
- Update `0.orig/T`: `internalField uniform 1500;`
- Create `0.orig/CO2` with `internalField uniform 0.29;`
- Update `0.orig/H2O`: `internalField uniform 0.71;`
- Update `0.orig/O2`: `internalField uniform 0;`
- Update `0.orig/CH4`: `internalField uniform 0;`
- Remove or zero out `0.orig/N2` internal field

### 2. Mesh Improvements — Boundary Layer Wrapping

**Problem:** Current mesh extends structured refinement radially from walls
into the core flow (simple layered blocks). This wastes cells in the core
where gradients are low, while under-resolving boundary layers at:
- Oxidizer slot walls (0.3–0.5 mm walls, only 1–2 cells)
- Fuel injector lip and backstep
- Oxidizer post step (x ≈ -10 mm)

**Solution:** Wrap structured boundary layer blocks **around** walls using
O-grid / C-grid topology, and use rounded corners (fillets) at sharp edges.

#### 2a. O-grid topology at oxidizer slots

Current geometry has 3 rectangular slots with sharp 90° corners.
Published CVRC LES studies use rounded corners (fillet radius ~0.1–0.2 mm)
and wrap the boundary layer mesh around the slot walls.

```
CURRENT:                     IMPROVED:
┌──────────┐                 ╭──────────╮
│ slot     │  ← sharp        │ slot     │  ← fillet radius
│ flow     │    corners      │ flow     │    r = 0.1mm
│          │                 │          │
├──────────┤                 │  BL mesh │  ← O-grid wraps
│ wall     │  ← 1-2 cells   ╰──┬───┬──╯    around walls
│ block    │    across wall     │   │
└──────────┘                    │   │
                              unstructured
                              core fill
```

For each slot passage, create:
- Inner O-grid ring: 4–6 cells normal to wall, Progression grading
- Core: either structured (mapped) or unstructured fill
- Fillet radius at all sharp corners (0.1–0.2 mm)

#### 2b. Boundary layer wrapping at fuel backstep

The fuel injector exits at x ≈ 0 with a backward-facing step into the
chamber. The recirculation zone here is critical for flame stabilisation.

```
        fuel pipe
     ─────────────┐
                   │ ← backstep corner, needs fillet + BL wrap
     ─────────────┘
     chamber
```

Add fillet (r ≈ 0.1 mm) and structured BL blocks wrapping around the corner.

#### 2c. Oxidizer post step

At x ≈ -10 mm, the oxidizer post terminates and flow expands into the
chamber. Similar treatment: fillet + wrapped BL blocks.

#### 2d. Remove excessive core refinement

Current unstructured sizing fields extend fine cells (SizeMin = 0.25 mm)
far into the core flow. With proper BL wrapping, the core can use much
coarser cells (1–2 mm), reducing total cell count while improving wall
resolution.

### 3. Implementation Strategy in Gmsh

**O-grid in Gmsh** is achieved by:
1. Define the wall curve
2. Offset the wall curve inward by BL thickness (e.g., 0.5 mm)
3. Create a structured surface between wall and offset curve
4. Apply Transfinite with Progression grading (cluster at wall)
5. Fill the remaining core with unstructured or mapped mesh

**Fillets in Gmsh:**
- Use `Fillet` operation on sharp points, or
- Replace sharp corner points with small arc segments (Circle arcs)
- Arc radius 0.1–0.2 mm at slot corners and step edges

**Gmsh Python API approach:**
```python
# Create offset curve for BL block
wall_pts = [p1, p2, p3, p4]  # wall corner points
offset_pts = []
for p in wall_pts:
    # offset normal to wall by BL_thickness
    op = gmsh.model.geo.addPoint(x + nx*BL, y + ny*BL, 0)
    offset_pts.append(op)

# Connect wall → offset curves to form BL quad block
# Apply Transfinite with grading
```

---

## Implementation Order

### Phase 1: BC/IC corrections (immediate, no mesh changes)
1. Update `0.orig/` field files with corrected pressures, temperatures, species
2. Test on current mesh — expect much better stability with 1.4 MPa chamber

### Phase 2: Geometry modifications (Gmsh builder script)
1. Add fillet radii to oxidizer slot corners
2. Add fillet to fuel backstep corner
3. Add fillet to oxidizer post step
4. Regenerate `.geo_unrolled` with `build_geometry.py` modifications

### Phase 3: Mesh topology changes
1. Add O-grid BL blocks around slot walls (4–6 cells, Progression grading)
2. Add BL blocks around fuel backstep
3. Reduce core refinement (increase SizeMin, reduce DistMax)
4. Update `parameterize_mesh_full.py` with new constraint chains
5. Regenerate mesh, verify quality

### Phase 4: Run with chemistry
1. Run inert flow to establish flow field (~1 ms)
2. Turn on chemistry, run to ~10 ms
3. Monitor stability, adjust dt if needed

---

## Key References

- GridPro blog: structured multi-block meshing for rocket nozzles
  (O-grid BL wrapping, corner treatment)
- ANSYS ICEM CFD: O-grid blocking strategy for cylindrical/slot geometries
- Gmsh GitLab #1236: O-grid / C-grid structured mesh techniques
- Gmsh `naca_boundary_layer_2d.py` example: BL mesh with transfinite
- Georgia Tech CCL: CVRC LES with grid sensitivity study
  (emphasis on injector/slot region mesh resolution)
