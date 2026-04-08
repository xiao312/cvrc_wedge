#!/bin/bash
#
# CVRC Mesh Pipeline — 2D planar slab → extrudeMesh wedge
# ========================================================
#
# Workflow:
#   1. (optional) parameterize_mesh_full.py → custom mesh parameters
#   2. create_slab_mesh.py  → flat 1-cell slab .msh (Gmsh)
#   3. gmshToFoam            → import into OpenFOAM polyMesh
#   4. transformPoints        → scale mm → m
#   5. extrudeMesh            → rotate slab into 5° wedge
#   6. fix boundary types     → axis=empty, slots/wall=wall
#   7. checkMesh              → final quality check
#
# Usage:
#   ./scripts/run_mesh_pipeline.sh [--param] [--clean]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MESH_DIR="${SCRIPT_DIR}/mesh"
CASE_DIR="$(dirname "${SCRIPT_DIR}")"

SLAB_SCRIPT="${MESH_DIR}/create_slab_mesh.py"
PARAM_SCRIPT="${MESH_DIR}/parameterize_mesh_full.py"
GEO_ORIG="${MESH_DIR}/cvrc_2d_profile.geo_unrolled"
GEO_PARAM="${MESH_DIR}/cvrc_2d_profile_param.geo_unrolled"

MSH_FILE="${CASE_DIR}/cvrc_slab.msh"
POLY_MESH="${CASE_DIR}/constant/polyMesh"

# ── parse arguments ────────────────────────────────────────────────────
RUN_PARAM=0; CLEAN_MESH=0
while [[ $# -gt 0 ]]; do
    case $1 in
        --param) RUN_PARAM=1; shift;;
        --clean) CLEAN_MESH=1; shift;;
        --help)  sed -n '2,/^$/p' "$0"; exit 0;;
        *)       echo "Unknown: $1"; exit 1;;
    esac
done

echo ""
echo "============================================================"
echo "CVRC Mesh Pipeline  (slab → extrudeMesh wedge)"
echo "============================================================"
echo "  Case dir : ${CASE_DIR}"
echo "  Param    : ${RUN_PARAM}"
echo "  Clean    : ${CLEAN_MESH}"
echo "============================================================"

# ── step 0: clean ──────────────────────────────────────────────────────
if [[ ${CLEAN_MESH} -eq 1 ]]; then
    echo -e "\nStep 0  Cleaning …"
    rm -rf "${POLY_MESH}" "${MSH_FILE}"
fi

# ── step 1: parameterise (optional) ───────────────────────────────────
GEO_FILE="${GEO_ORIG}"
if [[ ${RUN_PARAM} -eq 1 ]]; then
    echo -e "\nStep 1  Parameterising mesh …"
    (cd "${MESH_DIR}" && python3 "${PARAM_SCRIPT}")
    GEO_FILE="${GEO_PARAM}"
fi

# ── step 2: generate slab mesh with Gmsh ──────────────────────────────
echo -e "\nStep 2  Generating slab mesh …"
python3 -c "import gmsh" 2>/dev/null || {
    echo "ERROR: gmsh python module not found – pip install gmsh"; exit 1; }

TMP="${MESH_DIR}/.create_slab_tmp.py"
sed "s|SOURCE_GEO.*=.*|SOURCE_GEO = \"${GEO_FILE}\"|" \
    "${SLAB_SCRIPT}" > "${TMP}"
(cd "${CASE_DIR}" && python3 "${TMP}")
rm -f "${TMP}"
[[ -f "${MSH_FILE}" ]] || { echo "ERROR: ${MSH_FILE} not created"; exit 1; }

# ── step 3: gmshToFoam ────────────────────────────────────────────────
echo -e "\nStep 3  gmshToFoam …"
cd "${CASE_DIR}"
gmshToFoam "${MSH_FILE}"
rm -f "${POLY_MESH}/faceZones" "${POLY_MESH}/cellZones" \
      "${POLY_MESH}/pointZones"
rm -rf "${POLY_MESH}/sets"

# ── step 4: scale mm → m ──────────────────────────────────────────────
echo -e "\nStep 4  Scale mm → m …"
transformPoints -scale "(0.001 0.001 0.001)"

# ── step 5: extrudeMesh (slab → wedge) ────────────────────────────────
echo -e "\nStep 5  extrudeMesh (slab → 5° wedge) …"
extrudeMesh

# ── step 6: fix boundary types ────────────────────────────────────────
echo -e "\nStep 6  Fixing boundary types …"
python3 << 'PYEOF'
import re

with open("constant/polyMesh/boundary") as f:
    txt = f.read()

def set_type(text, name, new_type, new_group=None):
    """Set 'type' field in a named patch block."""
    pat = re.compile(
        r'(' + re.escape(name) + r'\s*\{[^}]*?type\s+)\w+(\s*;)', re.DOTALL)
    text = pat.sub(r'\g<1>' + new_type + r'\2', text)
    if new_group:
        pat2 = re.compile(
            r'(' + re.escape(name) + r'\s*\{[^}]*?)physicalType\s+\w+;', re.DOTALL)
        text = pat2.sub(r'\1inGroups List<word> 1(' + new_group + ');', text)
    return text

# axis → empty
txt = set_type(txt, "axis", "empty", "empty")
# walls
for p in ("wall", "oxidizer_slot_1", "oxidizer_slot_2", "oxidizer_slot_3"):
    txt = set_type(txt, p, "wall", "wall")

with open("constant/polyMesh/boundary", "w") as f:
    f.write(txt)
print("  Boundary types updated.")
PYEOF

# ── step 7: checkMesh ─────────────────────────────────────────────────
echo -e "\nStep 7  checkMesh …"
checkMesh

echo ""
echo "============================================================"
echo "Mesh pipeline complete!"
echo "============================================================"
echo "  Output: ${POLY_MESH}"
echo ""
echo "Next:"
echo "  cp -r 0.orig 0"
echo "  decomposePar"
echo "  mpirun -np 8 dfHighSpeedFoam -parallel"
echo "============================================================"
