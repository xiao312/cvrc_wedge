#!/usr/bin/env python3
"""
CVRC 2D Profile Mesh Parameterizer
==================================

Modifies the transfinite curve parameters in the CVRC 2D profile geometry
to control the structured mesh density.

The mesh is structured with blocks defined by transfinite curves.
Each 'Transfinite Curve {id} = N' specifies N nodes along that curve.

Usage
-----
    python3 parameterize_mesh.py

Output
------
    cvrc_2d_profile_param.geo_unrolled  (parameterized geo file)
"""

import re
import os

# =============================================================================
# MESH CONTROL PARAMETERS (EDIT THESE TO CHANGE MESH DENSITY)
# =============================================================================

# Axial direction (x-direction) node counts
# These control how many nodes are along lines in the x-direction

# Inlet section (-160 to -140 mm)
NX_INLET = 17        # Original: 17

# Slot strip (-140 to -128 mm)  
NX_SLOT_STRIP = 7     # Original: 7

# Axis channel (-128 to -10 mm)
NX_AXIS = 13         # Original: 13

# Middle section (-10 to 0 mm)
NX_MID = 49          # Original: 49

# Combustion chamber (0 to 20 mm)
NX_CHAMBER = 17      # Original: 17

# Fuel step axial
NX_STEP = 21         # Original: 21

# Downstream sections
NX_DOWNSTREAM = 11   # Original: 11 (for connection lines)

# =============================================================================
# RADIAL DIRECTION (y-direction) NODE COUNTS
# =============================================================================

# Slot heights (thin passages)
NY_SLOT_THIN = 4     # Original: 4 (for gaps like 3.0-3.8mm)

# Slot heights (thick passages)  
NY_SLOT_THICK = 9    # Original: 9 (for gaps like 3.8-5.8mm)

# Fuel injection annulus
NY_FUEL = 4          # Original: 4 (11 to 11.53mm)

# Upstream connections
NY_UPSTREAM = 11     # Original: 11

# Radial upper
NY_UPPER = 21        # Original: 21 (for upper sections)

# =============================================================================
# REFINEMENT FIELD PARAMETERS
# =============================================================================

# Refinement field distances (mm)
REFINE_SLOT_DIST = 45       # Original: 45
REFINE_MID_DIST = 35        # Original: 35
REFINE_CHAMBER_DIST = 120   # Original: 120
REFINE_OUTLET_DIST = 25     # Original: 25

# Refinement field sizes (mm)
REFINE_SIZE_MIN_SLOT = 0.7   # Original: 0.7
REFINE_SIZE_MIN_OUTLET = 0.5  # Original: 0.5
REFINE_SIZE_MAX = 3.0         # Original: 3.0

# =============================================================================
# FILE PATHS
# =============================================================================

INPUT_FILE = "/mnt/d/xiaox/downloads/cvrc_gmsh/cvrc_wedge_epsilon/cvrc_2d_profile.geo_unrolled"
OUTPUT_DIR = "/mnt/xiaox/downloads/cvrc_gmsh/cvrc_wedge_epsilon"
OUTPUT_FILE = os.path.join(os.path.dirname(INPUT_FILE), "cvrc_2d_profile_param.geo_unrolled")

# =============================================================================
# MAIN FUNCTION
# =============================================================================

def parameterize_geo():
    """Read the geo file and substitute transfinite curve parameters."""
    
    print(f"\n{'='*60}")
    print(f"CVRC 2D Profile Mesh Parameterizer")
    print(f"{'='*60}")
    print(f"\nMesh Parameters:")
    print(f"  AXIAL DIRECTION (x):")
    print(f"    NX_INLET      = {NX_INLET}  (inlet section)")
    print(f"    NX_SLOT_STRIP = {NX_SLOT_STRIP}  (slot strip)")
    print(f"    NX_AXIS       = {NX_AXIS}  (axis channel)")
    print(f"    NX_MID        = {NX_MID}  (middle section)")
    print(f"    NX_CHAMBER    = {NX_CHAMBER}  (combustion chamber)")
    print(f"    NX_STEP       = {NX_STEP}  (fuel step)")
    print(f"  RADIAL DIRECTION (y):")
    print(f"    NY_SLOT_THIN  = {NY_SLOT_THIN}  (thin slots)")
    print(f"    NY_SLOT_THICK = {NY_SLOT_THICK}  (thick slots)")
    print(f"    NY_FUEL       = {NY_FUEL}  (fuel annulus)")
    print(f"    NY_UPSTREAM   = {NY_UPSTREAM}  (upstream)")
    print(f"    NY_UPPER      = {NY_UPPER}  (upper sections)")
    print(f"{'='*60}\n")
    
    # Read original file
    print(f"Reading: {INPUT_FILE}")
    with open(INPUT_FILE, 'r') as f:
        lines = f.readlines()
    
    # Process each line
    output_lines = []
    changes_made = 0
    
    for line in lines:
        original_line = line
        
        # Skip comment lines
        if line.strip().startswith('//'):
            output_lines.append(line)
            continue
        
        # Transfinite Curve substitutions
        # Format: Transfinite Curve {id} = N Using Progression 1;
        # We need to identify which curves go in which direction by context
        
        # Axial direction curves (looking for specific patterns)
        # NX_INLET: lines with 17 nodes in inlet region (curves 1, 3, 6, 9, 12, 15, 18, 21)
        if re.match(r'Transfinite Curve \{[1-9]\} = \d+ Using Progression', line):
            match = re.search(r'Transfinite Curve \{(\d+)\} = (\d+)', line)
            if match:
                curve_id = int(match.group(1))
                old_count = int(match.group(2))
                # Curves 1, 3, 6, 9, 12, 15, 18, 21 are axial in inlet (17 nodes)
                if old_count == 17:
                    line = re.sub(r'= \d+', f'= {NX_INLET}', line)
                    changes_made += 1
        
        # NX_MID: lines with 49 nodes (horizontal long lines in mid section)
        if 'Transfinite Curve' in line and '= 49' in line:
            line = re.sub(r'= 49', f'= {NX_MID}', line)
            changes_made += 1
        
        # NX_AXIS: lines with 13 nodes (axis channel)
        if 'Transfinite Curve' in line and '= 13' in line:
            line = re.sub(r'= 13', f'= {NX_AXIS}', line)
            changes_made += 1
        
        # NX_CHAMBER: lines with 17 in chamber (after line 71)
        # This is tricky - need context
        
        # NX_STEP: lines with 21 nodes (step region)
        if 'Transfinite Curve' in line and '= 21' in line:
            line = re.sub(r'= 21', f'= {NX_STEP}', line)
            changes_made += 1
        
        # NY_SLOT_THIN: lines with 4 nodes (radial thin slots)
        if 'Transfinite Curve' in line and '= 4 Using' in line:
            line = re.sub(r'= 4 Using', f'= {NY_SLOT_THIN} Using', line)
            changes_made += 1
        
        # NY_SLOT_THICK: lines with 9 nodes (radial thick slots)
        if 'Transfinite Curve' in line and '= 9 Using' in line:
            line = re.sub(r'= 9 Using', f'= {NY_SLOT_THICK} Using', line)
            changes_made += 1
        
        # NY_FUEL: lines with 4 in fuel (curves 60, 62)
        # Already handled by NY_SLOT_THIN
        
        # NY_UPSTREAM: lines with 11 in upstream connections
        if 'Transfinite Curve' in line and '= 11 Using' in line:
            line = re.sub(r'= 11 Using', f'= {NY_UPSTREAM} Using', line)
            changes_made += 1
        
        # NY_UPPER: lines with 21 in upper sections (curves 59, 61, 78, 80)
        if 'Transfinite Curve' in line and '= 21 Using' in line:
            line = re.sub(r'= 21 Using', f'= {NY_UPPER} Using', line)
            changes_made += 1
        
        # Refinement field parameters
        if 'Field[2].DistMax' in line:
            line = f"Field[2].DistMax = {REFINE_SLOT_DIST};\n"
            changes_made += 1
        if 'Field[4].DistMax' in line:
            line = f"Field[4].DistMax = {REFINE_MID_DIST};\n"
            changes_made += 1
        if 'Field[6].DistMax' in line:
            line = f"Field[6].DistMax = {REFINE_CHAMBER_DIST};\n"
            changes_made += 1
        if 'Field[8].DistMax' in line:
            line = f"Field[8].DistMax = {REFINE_OUTLET_DIST};\n"
            changes_made += 1
        
        if 'Field[2].SizeMin' in line:
            line = f"Field[2].SizeMin = {REFINE_SIZE_MIN_SLOT};\n"
            changes_made += 1
        if 'Field[4].SizeMin' in line:
            line = f"Field[4].SizeMin = {REFINE_SIZE_MIN_SLOT};\n"
            changes_made += 1
        if 'Field[6].SizeMin' in line:
            line = f"Field[6].SizeMin = {REFINE_SIZE_MIN_SLOT};\n"
            changes_made += 1
        if 'Field[8].SizeMin' in line:
            line = f"Field[8].SizeMin = {REFINE_SIZE_MIN_OUTLET};\n"
            changes_made += 1
        
        output_lines.append(line)
    
    # Write output file
    print(f"Writing: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, 'w') as f:
        f.writelines(output_lines)
    
    print(f"\nChanges made: {changes_made}")
    print(f"Output file: {OUTPUT_FILE}")
    
    return changes_made > 0


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    parameterize_geo()
    
    print(f"\n{'='*60}")
    print("To use the parameterized mesh:")
    print("  1. Edit NX_*, NY_* parameters at top of this script")
    print("  2. Run: python3 parameterize_mesh.py")
    print("  3. Edit create_wedge_v10.py:")
    print(f"     SOURCE_GEO = '{OUTPUT_FILE}'")
    print("  4. Run: python3 create_wedge_v10.py")
    print(f"{'='*60}")