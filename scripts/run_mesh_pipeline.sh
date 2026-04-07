#!/bin/bash
#
# CVRC Wedge Mesh Pipeline
# ========================
# Generates a 3D wedge mesh for OpenFOAM from the 2D CVRC profile.
#
# Usage:
#   ./scripts/run_mesh_pipeline.sh [OPTIONS]
#
# Options:
#   --param    Run parameterize_mesh_full.py first (use custom mesh parameters)
#   --clean    Remove existing constant/polyMesh before generating
#   --help     Show this help message
#
# Environment Requirements:
#   - OpenFOAM 7: source /opt/openfoam7/etc/bashrc
#   - Gmsh Python API: conda activate agent

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MESH_DIR="${SCRIPT_DIR}/mesh"
CASE_DIR="$(dirname "${SCRIPT_DIR}")"

MESH_SCRIPT="${MESH_DIR}/create_wedge_v10.py"
PARAM_SCRIPT="${MESH_DIR}/parameterize_mesh_full.py"
GEO_ORIG="${MESH_DIR}/cvrc_2d_profile.geo_unrolled"
GEO_PARAM="${MESH_DIR}/cvrc_2d_profile_param.geo_unrolled"

MSH_FILE="${CASE_DIR}/cvrc_wedge.msh"
POLY_MESH="${CASE_DIR}/constant/polyMesh"
GEO_FILE="${GEO_ORIG}"

# =============================================================================
# PARSE ARGUMENTS
# =============================================================================

RUN_PARAM=0
CLEAN_MESH=0

while [[ $# -gt 0 ]]; do
    case $1 in
        --param) RUN_PARAM=1; shift ;;
        --clean) CLEAN_MESH=1; shift ;;
        --help)
            cat << 'EOF'
CVRC Wedge Mesh Pipeline
========================

Usage: ./scripts/run_mesh_pipeline.sh [OPTIONS]

Options:
  --param    Run parameterize_mesh_full.py to customize mesh density
  --clean    Remove existing polyMesh directory first
  --help     Show this help

Environment:
  - OpenFOAM 7: source /opt/openfoam7/etc/bashrc
  - Gmsh: conda activate agent OR pip install gmsh
EOF
            exit 0 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# =============================================================================
# CONFIGURATION OUTPUT
# =============================================================================

echo ""
echo "============================================================"
echo "CVRC Wedge Mesh Pipeline"
echo "============================================================"
echo "Case directory: ${CASE_DIR}"
echo "Mesh script:    ${MESH_SCRIPT}"
echo "Output mesh:    ${MSH_FILE}"
echo "PolyMesh:       ${POLY_MESH}"
echo ""
echo "Options:"
echo "  Parameterize: ${RUN_PARAM}"
echo "  Clean:        ${CLEAN_MESH}"
echo "============================================================"
echo ""

# =============================================================================
# STEP 0: CLEAN EXISTING MESH (OPTIONAL)
# =============================================================================

if [[ ${CLEAN_MESH} -eq 1 ]]; then
    echo "Step 0: Cleaning existing mesh..."
    rm -rf "${POLY_MESH}"
    rm -f "${MSH_FILE}"
    echo "  Done"
fi

# =============================================================================
# STEP 1: PARAMETERIZE MESH (OPTIONAL)
# =============================================================================

if [[ ${RUN_PARAM} -eq 1 ]]; then
    echo ""
    echo "Step 1: Parameterizing mesh..."
    if [[ ! -f "${PARAM_SCRIPT}" ]]; then
        echo "ERROR: Parameterize script not found: ${PARAM_SCRIPT}"
        exit 1
    fi
    cd "${MESH_DIR}"
    python3 "${PARAM_SCRIPT}"
    GEO_FILE="${GEO_PARAM}"
    echo "  Using parameterized geo: ${GEO_FILE}"
fi

# =============================================================================
# STEP 2: GENERATE GMSH MESH
# =============================================================================

echo ""
echo "Step 2: Generating Gmsh mesh..."
echo "  Script:  ${MESH_SCRIPT}"
echo "  Geo file: ${GEO_FILE}"

if [[ ! -f "${MESH_SCRIPT}" ]]; then
    echo "ERROR: Mesh script not found: ${MESH_SCRIPT}"
    exit 1
fi

if [[ ! -f "${GEO_FILE}" ]]; then
    echo "ERROR: Geo file not found: ${GEO_FILE}"
    exit 1
fi

if ! python3 -c "import gmsh" 2>/dev/null; then
    echo ""
    echo "ERROR: gmsh Python module not found!"
    echo ""
    echo "Please activate a conda environment with gmsh installed:"
    echo "  conda activate agent"
    echo ""
    echo "Or install gmsh:"
    echo "  pip install gmsh --user"
    echo ""
    exit 1
fi

# Create temp script with updated SOURCE_GEO path
TMP_SCRIPT="${MESH_DIR}/.create_wedge_tmp.py"
sed "s|SOURCE_GEO = os.path.join(SCRIPT_DIR, \"cvrc_2d_profile.geo_unrolled\")|SOURCE_GEO = \"${GEO_FILE}\"|" "${MESH_SCRIPT}" > "${TMP_SCRIPT}"

cd "${CASE_DIR}"
python3 "${TMP_SCRIPT}"
rm -f "${TMP_SCRIPT}"

if [[ ! -f "${MSH_FILE}" ]]; then
    echo "ERROR: Mesh file not created: ${MSH_FILE}"
    exit 1
fi
echo "  Created: ${MSH_FILE}"

# =============================================================================
# STEP 3: CONVERT TO OPENFOAM
# =============================================================================

echo ""
echo "Step 3: Converting to OpenFOAM format..."

if [[ -f "/opt/openfoam7/etc/bashrc" ]]; then
    source /opt/openfoam7/etc/bashrc
else
    echo "ERROR: OpenFOAM 7 not found at /opt/openfoam7/etc/bashrc"
    exit 1
fi

cd "${CASE_DIR}"
gmshToFoam "${MSH_FILE}"

# =============================================================================
# STEP 4: CLEAN UP ZONE FILES
# =============================================================================

echo ""
echo "Step 4: Cleaning up zone files..."
rm -f "${POLY_MESH}/faceZones"
rm -f "${POLY_MESH}/cellZones"
rm -f "${POLY_MESH}/pointZones"
rm -rf "${CASE_DIR}/constant/polyMesh/sets"
echo "  Done"

# =============================================================================
# STEP 5: SCALE MESH FROM MM TO METERS
# =============================================================================

echo ""
echo "Step 5: Scaling mesh (mm -> meters)..."
transformPoints -scale "(0.001 0.001 0.001)"
echo "  Done"

# =============================================================================
# STEP 6: CHECK MESH QUALITY
# =============================================================================

echo ""
echo "Step 6: Checking mesh quality..."
checkMesh

echo ""
echo "============================================================"
echo "Mesh Pipeline Complete!"
echo "============================================================"
echo "Output: ${POLY_MESH}"
echo ""
echo "Next steps:"
echo "  1. Copy field files:"
echo "     for f in U T p CH4 O2 H2O N2 Ydefault; do cp 0/\${f}.orig 0/\${f}; done"
echo "  2. Run solver: dfHighSpeedFoam"
echo "============================================================"