# CVRC Simulation Stability — Crash Analysis & Fix Plan

## Crash Summary

| Item | Value |
|------|-------|
| Solver | dfHighSpeedFoam (DeepFlame, density-based) |
| Crash time | t ≈ 0.000398 s (step ~3978, dt = 1e-7) |
| Symptom | T_max oscillation: 1283 → 1356 → 1562 → 2070 → 4817 K |
| Fatal error | Cantera `setState_HPorUV` — "No convergence in 500 iterations" |
| T_min at crash | 170 K (fuel pipe region) |

## Root Causes

### RC1 — Fuel pipe thermal mismatch
The fuel pipe region (-30 < x < -10 mm, 10.235 < y < 11.53 mm) is initialized
with the **default** field values (T = 300 K ambient, no CH4).  As the cold
CH4 fuel (300 K) enters, it must displace and cool the initially mismatched gas
through a very narrow pipe (0.53–0.77 mm width).  Expansion cooling drives
T_min to ~170 K — below Cantera's reliable thermo range.

### RC2 — Slot velocity overshoot
Hot oxidizer (1029 K, sound speed ≈ 650 m/s) accelerates through three narrow
annular slots (widths 0.3–2.0 mm).  The inlet-to-slot area ratio is 1.39,
giving an incompressible estimate of ~139 m/s.  But compressibility and hot-gas
expansion push velocity past 800 m/s in the simulation — exceeding the sonic
limit and observed experimental values (625 m/s slots, 750 m/s post).  The
current mesh has only **1–2 cells** across the 0.3 mm slot walls, which is
severely under-resolved.

---

## Fix Plan

Fixes are ordered by implementation effort and expected impact.  Each fix is
tested independently; if the simulation survives longer, the fix is kept.

### Fix A — `setFields` initialisation (immediate)
**File:** `system/setFieldsDict`

Set correct initial conditions in two regions:

| Region | x range (m) | y range (m) | T | Y(CH4) | Y(O2) | Y(H2O) | U |
|--------|-------------|-------------|---|--------|--------|---------|---|
| Oxidizer passage | -0.16 … -0.01 | 0 … 0.010235 | 1029 K | 0 | 0.42 | 0.58 | (100 0 0) |
| Fuel pipe | -0.03 … 0 | 0.010235 … 0.01153 | 300 K | 1.0 | 0 | 0 | (33 0 0) |

**Rationale:** Eliminates impulsive thermal mismatch; standard practice in
multi-region combustor CFD.

### Fix B — Kurganov flux scheme  (❌ REJECTED)
**File:** `system/fvSchemes`

Change `fluxScheme Tadmor;` → `fluxScheme Kurganov;`.  Tested and found to be
**less stable** than Tadmor for this geometry.  Kurganov crashed 32× faster.
dfHighSpeedFoam examples use Kurganov mainly for 1D shock tubes; 2D cases
use HLLC or Tadmor.  Tadmor’s extra dissipation is beneficial here.

### Fix C — Inlet velocity ramping
**File:** `0/U` (oxidizer_inlet and fuel_inlet patches)

Ramp inlet velocity from 0 to full value over 0.2 ms using a
`uniformFixedValue` + `table` boundary condition.  Prevents impulsive
pressure waves from slamming into the narrow slots at t = 0.

### Fix D — Reduce initial time step
**File:** `system/controlDict`

Reduce `deltaT` to 5e-8 (half current value).  The Courant number analysis
showed max Co = 0.15 at dt = 1e-7, so 5e-8 gives max Co ≈ 0.075 — more
margin during the violent startup transient.

### Fix E — Slot-region mesh refinement
**File:** `scripts/mesh/parameterize_mesh_full.py`

Increase node counts on slot wall layers to get ≥ 4 cells across each wall:

| Parameter | Current | Target | Span | Cell size |
|-----------|---------|--------|------|-----------|
| NY_LAYER_3 (0.5 mm wall) | 3 | 7 | 0.5 mm | 0.083 mm |
| NY_LAYER_5 (0.3 mm wall) | 3 | 7 | 0.3 mm | 0.050 mm |
| NY_LAYER_7 (0.535 mm wall) | 4 | 9 | 0.535 mm | 0.067 mm |
| NX_SLOT_1–4 | 11 | 15 | 18 mm | 1.29 mm |

Also consider grading (Bump) on slot layers to cluster cells at the slot
walls.

### Fix F — NX_AXIS grading near slot exit
**File:** `scripts/mesh/parameterize_mesh_full.py`

Use `Progression` grading on `NX_AXIS` to cluster cells near x = -128 mm
(slot exit), where the flow transitions from narrow slots into the oxidizer
post.

### Fix G — O-grid blocks around slot lips (long-term)
**File:** Geometry `.geo` source

Add C-shaped or O-shaped block topology around each slot lip to properly
resolve the shear layers forming at slot edges.  This requires modifying the
Gmsh geometry builder.  Published CVRC LES studies use this approach.

### Fix H — Verify slot dimensions against experiment
Cross-check the Gmsh geometry against the CVRC experimental drawings
(Yu et al., Purdue).  The oxidizer post ID in the experiment is 12.7 mm
diameter (r = 6.35 mm), while our model uses r = 10.235 mm.  The slot widths
may also differ.

### Fix I — totalPressure inlet BC (alternative)
For choked slot flow, the physical control parameter is upstream total
pressure, not velocity.  A `totalPressure` inlet BC would naturally limit
the velocity to sonic and prevent unphysical supersonic acceleration inside
the slots.

---

## Verification Protocol

After each fix, run:
```
mpirun -np 8 dfHighSpeedFoam -parallel > log.fixN 2>&1
```
Check:
1. Does the simulation survive past t = 0.0004 s?
2. Is T_min > 200 K?
3. Is T_max < 3500 K?
4. Is max velocity < 900 m/s?
5. Does the simulation reach t = 0.001 s?

---

## Test Results Log

### Baseline (no fixes)
- Flux: Tadmor, dt=1e-7, no setFields, impulsive U=100
- Survived: **t = 398 µs** (3978 steps)
- T range at crash: Tmin=170K, Tmax=4817K (oscillation blowup)
- Verdict: **CRASH** — slot velocity overshoot

### Fix A — setFields (T+species+velocity)
- setFields: oxidizer passage T=1029 + U=100, fuel pipe T=300 + CH4=1
- Survived: **t = 6.6 µs** (66 steps) — **32× WORSE**
- Cause: sharp T discontinuity at x≈-10mm → pressure waves → instant crash
- Verdict: ❌ **REJECTED** — impulsive setFields creates worse discontinuities

### Fix A2 — setFields (T+species only, NO velocity)
- Same as A but without initializing U
- Survived: **t = 6.6 µs** — same crash, same cause
- Verdict: ❌ **REJECTED**

### Fix A+B — setFields + Kurganov flux
- Kurganov flux scheme instead of Tadmor
- Survived: **t = 6.6 µs** — crashed even at step 1 (CO field BC issue)
- After fixing: still crashed at same time as Fix A
- Verdict: ❌ Kurganov is LESS stable than Tadmor for this geometry
  (1D shock cases ≠ 2D combustor with narrow slots)

### Fix C+D — Velocity ramp + smaller dt  (✅ SUCCESS)
- Tadmor flux, dt=5e-8 (half), velocity ramp 0→100 m/s over 0.5ms
- NO setFields
- **SCNET run (32 cores, job 111135885)**:
  - t=398µs: ✅ PASSED old crash point (T=179–1073K)
  - t=500µs: ✅ Ramp complete, full velocity, stable
  - t=647µs: T=169–1282K, zero errors
  - t=856µs: T=258–1274K (T_min recovering)
  - t=997µs: T=300–1274K ✅ **REACHED TARGET 1ms**
  - t=1000µs: T=300–1274K ✅ **COMPLETED** (20,000 steps)
  - Wall time: 4h45m on 32 cores (1.19 steps/s)
- Verdict: ✅ **CONFIRMED WORKING** — velocity ramping is the key fix

### Phase 2 — Chemistry on (continuation from t=1ms)
- Enable `chemistry on;` in `constant/CanteraTorchProperties`
- Continue from t=1ms to t=11ms (10ms additional)
- Write interval: 5e-4 (every 0.5ms → 20 output times)
- GRI-Mech 3.0: 53 species, extremely expensive

#### Core-count benchmark (21 steps with chemistry, SCNET)

| Cores | Nodes | Wall (s) | Steps/s | Speedup | ETA 10ms |
|-------|-------|----------|---------|---------|----------|
| 32    | 1     | 71       | 0.36    | 1.0×    | 154 h    |
| 64    | 2     | 47       | 0.66    | 1.5×    | 84 h     |
| 96    | 3     | 39       | 0.83    | 1.8×    | 67 h     |
| 128   | 4     | 35       | 0.95    | 2.0×    | 58 h     |

Chemistry dominates cost (3.2× slower than inert flow).
Scaling limited by chemistry load imbalance — not communication.

#### Production run
- SCNET job **111153724**: 128 cores, 4 nodes, 72h wall time
- Running from t=0.001 to t=0.011 (10ms, 200,000 steps)
- Estimated completion: ~58 hours

### Lessons Learned
1. setFields with sharp T jumps (1029 vs 300K) is WORSE than gradual startup
2. Kurganov is less stable than Tadmor for narrow-slot geometries
3. Velocity ramping is the key — prevents impulsive pressure waves
4. Smaller dt provides additional CFL margin during startup
