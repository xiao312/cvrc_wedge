#!/usr/bin/env python3
"""
CVRC 2D Profile Mesh Parameterizer - Fully Parameterized
=========================================================

Modifies ALL transfinite curve parameters in the CVRC 2D profile geometry
to provide complete control over mesh node counts.

Block Structure (Y-direction from axis):
-----------------------------------------
Slot 1: y = 3.0 - 3.8 mm   (NY_SLOT_THIN nodes, ~3 cells)
Slot 2: y = 3.8 - 5.8 mm   (NY_SLOT_THICK nodes, ~8 cells)  
Slot 3: y = 5.8 - 6.3 mm   (NY_SLOT_THIN nodes, ~3 cells)
Slot 4: y = 6.3 - 8.0 mm   (NY_SLOT_THICK nodes, ~8 cells)
Slot 5: y = 8.0 - 8.3 mm   (NY_SLOT_THIN nodes, ~3 cells)
Slot 6: y = 8.3 - 9.7 mm   (NY_SLOT_THICK nodes, ~8 cells)
Slot 7: y = 9.7 - 10.235 mm (NY_SLOT_THIN nodes, ~3 cells)

X-direction blocks:
-------------------
Inlet section:     x = -160 to -140 mm (NX_INLET nodes)
Slot strip:        x = -140 to -128 mm (NX_SLOT_STRIP nodes)
Axis channel:      x = -128 to -10 mm  (NX_AXIS nodes)
Mid section:       x = -10 to 0 mm     (NX_MID nodes)
Combustion chamber: x = 0 to 20 mm    (NX_CHAMBER nodes)

Usage:
    python3 parameterize_mesh_full.py
    
Output:
    cvrc_2d_profile_param.geo_unrolled (parameterized geo file)
"""

import re
import os

# =============================================================================
# MESH CONTROL PARAMETERS - EDIT THESE TO CHANGE MESH DENSITY
# =============================================================================

# -----------------------------------------------------------------------------
# AXIAL DIRECTION (x-direction) NODE COUNTS
# Number of nodes = number of cells + 1
# -----------------------------------------------------------------------------

NX_INLET = 17          # Inlet blocks, x = -160 to -140 mm (cells: 16)
NX_SLOT_STRIP = 7      # Slot strip, x = -140 to -128 mm (cells: 6)
NX_AXIS = 13           # Axis channel, x = -128 to -10 mm (cells: 12)
NX_MID = 49            # Mid section, x = -10 to 0 mm (cells: 48)
NX_CHAMBER = 17        # Chamber, x = 0 to 20 mm (cells: 16)
NX_STEP = 11           # Step connections (cells: 10)
NX_FUEL = 21           # Fuel step axial (cells: 20)

# -----------------------------------------------------------------------------
# RADIAL DIRECTION (y-direction) NODE COUNTS  
# -----------------------------------------------------------------------------

# Thin slots (2 cells): y = 3.0-3.8, 5.8-6.3, 8.0-8.3, 9.7-10.235 mm
NY_SLOT_VERY_THIN = 3  # Original: 3 (2 cells)

# Thin slots (3 cells): used for slot connections and thin layers
NY_SLOT_THIN = 4       # Original: 4 (3 cells)

# Medium slots (6 cells): slot strip connections
NY_SLOT_MEDIUM = 7     # Original: 7 (6 cells)

# Thick slots (7 cells)
NY_SLOT_THICK_7 = 8    # Original: 8 (7 cells)

# Thick slots (8 cells): y = 3.8-5.8, 6.3-8.0, 8.3-9.7 mm
NY_SLOT_THICK = 9      # Original: 9 (8 cells)

# Axis radial (12 cells): main annulus y = 0 to 10.235 mm
NY_AXIS = 13           # Original: 13 (12 cells)

# Slot strip radial (12 cells): y = 0 to 3 mm
NY_SLOT_STRIP = 13     # Original: 13 (12 cells)

# Mid connections (10 cells)
NY_MID_CONN = 11       # Original: 11 (10 cells)

# Upper sections (20 cells): y > 11 mm
NY_UPPER = 21          # Original: 21 (20 cells)

# Fuel annulus (3 cells): y = 11 to 11.53 mm
NY_FUEL = 4           # Original: 4 (3 cells)

# -----------------------------------------------------------------------------
# REFINEMENT FIELD PARAMETERS
# -----------------------------------------------------------------------------

REFINE_SLOT_DIST = 45
REFINE_MID_DIST = 35
REFINE_CHAMBER_DIST = 120
REFINE_OUTLET_DIST = 25
REFINE_SIZE_MIN_SLOT = 0.7
REFINE_SIZE_MIN_OUTLET = 0.5
REFINE_SIZE_MAX = 3.0

# =============================================================================
# FILE PATHS
# =============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(SCRIPT_DIR, "cvrc_2d_profile.geo_unrolled")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "cvrc_2d_profile_param.geo_unrolled")

# =============================================================================
# LINE GROUP DEFINITIONS
# Based on analysis of the original geo file structure
# =============================================================================

# Lines are numbered based on their position in the geometry
# Each block has 4 lines forming a quad: L1 (bottom), L2 (left), L3 (top), L4 (right)

# =============================================================================
# MAIN FUNCTION
# =============================================================================

def parameterize_geo():
    """Read geo file and substitute all transfinite parameters."""
    
    print(f"\n{'='*70}")
    print("CVRC 2D Profile Mesh Parameterizer (Full)")
    print(f"{'='*70}")
    print(f"\nInput:  {INPUT_FILE}")
    print(f"Output: {OUTPUT_FILE}")
    print(f"\nMesh Parameters:")
    print(f"  AXIAL (X-direction, nodes = cells + 1):")
    print(f"    NX_INLET      = {NX_INLET:3d}  (inlet -160 to -140 mm)")
    print(f"    NX_SLOT_STRIP = {NX_SLOT_STRIP:3d}  (slot strip -140 to -128 mm)")
    print(f"    NX_AXIS       = {NX_AXIS:3d}  (axis channel -128 to -10 mm)")
    print(f"    NX_MID        = {NX_MID:3d}  (mid section -10 to 0 mm)")
    print(f"    NX_CHAMBER    = {NX_CHAMBER:3d}  (chamber 0 to 20 mm)")
    print(f"    NX_STEP       = {NX_STEP:3d}  (step connections)")
    print(f"    NX_FUEL       = {NX_FUEL:3d}  (fuel step axial)")
    print(f"  RADIAL (Y-direction, nodes = cells + 1):")
    print(f"    NY_SLOT_VERY_THIN = {NY_SLOT_VERY_THIN:3d}  (very thin slots, 2 cells)")
    print(f"    NY_SLOT_THIN      = {NY_SLOT_THIN:3d}  (thin slots, 3 cells)")
    print(f"    NY_SLOT_MEDIUM    = {NY_SLOT_MEDIUM:3d}  (medium slots, 6 cells)")
    print(f"    NY_SLOT_THICK_7   = {NY_SLOT_THICK_7:3d}  (thick slots, 7 cells)")
    print(f"    NY_SLOT_THICK     = {NY_SLOT_THICK:3d}  (thick slots, 8 cells)")
    print(f"    NY_AXIS           = {NY_AXIS:3d}  (axis radial, 12 cells)")
    print(f"    NY_SLOT_STRIP     = {NY_SLOT_STRIP:3d}  (slot strip radial, 12 cells)")
    print(f"    NY_MID_CONN       = {NY_MID_CONN:3d}  (mid connections, 10 cells)")
    print(f"    NY_UPPER          = {NY_UPPER:3d}  (upper sections, 20 cells)")
    print(f"    NY_FUEL           = {NY_FUEL:3d}  (fuel annulus, 3 cells)")
    print(f"{'='*70}\n")
    
    # Read original file
    with open(INPUT_FILE, 'r') as f:
        lines = f.readlines()
    
    output_lines = []
    changes = {}
    
    for line in lines:
        original = line
        
        # Skip comments
        if line.strip().startswith('//'):
            output_lines.append(line)
            continue
        
        # Match Transfinite Curve lines
        # Format: Transfinite Curve {N} = X Using Progression 1;
        match = re.match(r'Transfinite Curve \{(\d+)\} = (\d+)( Using Progression \d+;)?', line)
        
        if match:
            curve_id = int(match.group(1))
            old_count = int(match.group(2))
            progression = match.group(3) if match.group(3) else ' Using Progression 1;'
            
            # Determine which parameter to use based on curve ID
            new_count = old_count  # default: keep original
            
            # === INLET SECTION (x = -160 to -140 mm) ===
            # Block 1 (y=3.0-3.8): Lines 1,2,3,4
            # Block 2 (y=3.8-5.8): Lines 3,5,6,7
            # Block 3 (y=5.8-6.3): Lines 6,8,9,10
            # Block 4 (y=6.3-8.0): Lines 9,11,12,13
            # Block 5 (y=8.0-8.3): Lines 12,14,15,16
            # Block 6 (y=8.3-9.7): Lines 15,17,18,19
            # Block 7 (y=9.7-10.235): Lines 18,20,21,22
            
            # Axial lines in inlet (horizontal, x-direction): 1,3,6,9,12,15,18,21
            if curve_id in [1, 3, 6, 9, 12, 15, 18, 21]:
                new_count = NX_INLET
                changes[curve_id] = ('NX_INLET', old_count, new_count)
            
            # Radial lines (thin, y-direction): 2,4 for block 1
            elif curve_id in [2, 4]:
                new_count = NY_SLOT_THIN
                changes[curve_id] = ('NY_SLOT_THIN', old_count, new_count)
            
            # Radial lines (thick): 5,7 for block 2
            elif curve_id in [5, 7]:
                new_count = NY_SLOT_THICK
                changes[curve_id] = ('NY_SLOT_THICK', old_count, new_count)
            
            # Radial lines (thin, y-direction): 8,10 for block 3
            elif curve_id in [8, 10]:
                new_count = NY_SLOT_THIN
                changes[curve_id] = ('NY_SLOT_THIN', old_count, new_count)
            
            # Radial lines (thick): 11,13 for block 4
            elif curve_id in [11, 13]:
                new_count = NY_SLOT_THICK
                changes[curve_id] = ('NY_SLOT_THICK', old_count, new_count)
            
            # Radial lines (thin): 14,16 for block 5
            elif curve_id in [14, 16]:
                new_count = NY_SLOT_THIN
                changes[curve_id] = ('NY_SLOT_THIN', old_count, new_count)
            
            # Radial lines (thick): 17,19 for block 6
            elif curve_id in [17, 19]:
                new_count = NY_SLOT_THICK
                changes[curve_id] = ('NY_SLOT_THICK', old_count, new_count)
            
            # Radial lines (thin): 20,22 for block 7
            elif curve_id in [20, 22]:
                new_count = NY_SLOT_THIN
                changes[curve_id] = ('NY_SLOT_THIN', old_count, new_count)
            
            # === SLOT STRIP CONNECTION (x = -140 to -128 mm) ===
            # Lines 23-34, 8 horizontal strips connecting inlet to plenum
            
            # Axial lines in slot strip (x-direction): 23, 26, 29, 32
            elif curve_id in [23, 26, 29, 32]:
                new_count = NX_SLOT_STRIP
                changes[curve_id] = ('NX_SLOT_STRIP', old_count, new_count)
            
            # Slot strip outlet radial (y=0 to 3mm): 39,40,41,42,43,45,46,47,50,51,52,53,54,55
            # Actually 35-38 connect axis to first slot
            elif curve_id in [35, 36, 37, 38]:
                new_count = NY_SLOT_STRIP
                changes[curve_id] = ('NY_SLOT_STRIP', old_count, new_count)
            
            # === MID/CHAMBER SECTION ===
            # Horizontal lines with 49 nodes (long x-direction): 57, 64, 72
            elif curve_id in [57, 64, 72]:
                new_count = NX_MID
                changes[curve_id] = ('NX_MID', old_count, new_count)
            
            # Lines with 13 nodes (radial in mid section)
            elif old_count == 13:
                new_count = NY_AXIS
                changes[curve_id] = ('NY_AXIS', old_count, new_count)
            
            # Lines with 11 nodes (connections)
            elif old_count == 11:
                new_count = NY_MID_CONN
                changes[curve_id] = ('NY_MID_CONN', old_count, new_count)
            
            # Lines with 17 nodes (chamber axial or similar)
            elif old_count == 17:
                new_count = NX_CHAMBER
                changes[curve_id] = ('NX_CHAMBER', old_count, new_count)
            
            # Lines with 21 nodes (fuel step or upper)
            elif old_count == 21:
                new_count = NY_UPPER
                changes[curve_id] = ('NY_UPPER', old_count, new_count)
            
            # Lines with 3 nodes (very thin, 2 cells)
            elif old_count == 3:
                new_count = NY_SLOT_VERY_THIN
                changes[curve_id] = ('NY_SLOT_VERY_THIN', old_count, new_count)
            
            # Lines with 4 nodes (thin, 3 cells)
            elif old_count == 4:
                new_count = NY_SLOT_THIN
                changes[curve_id] = ('NY_SLOT_THIN', old_count, new_count)
            
            # Lines with 7 nodes (medium, 6 cells)
            elif old_count == 7:
                new_count = NY_SLOT_MEDIUM
                changes[curve_id] = ('NY_SLOT_MEDIUM', old_count, new_count)
            
            # Lines with 8 nodes (thick 7 cells)
            elif old_count == 8:
                new_count = NY_SLOT_THICK_7
                changes[curve_id] = ('NY_SLOT_THICK_7', old_count, new_count)
            
            # Lines with 9 nodes (thick, 8 cells)
            elif old_count == 9:
                new_count = NY_SLOT_THICK
                changes[curve_id] = ('NY_SLOT_THICK', old_count, new_count)
            
            # Replace count in line
            line = re.sub(r'= \d+', f'= {new_count}', line)
        
        # Field refinement parameters
        if 'Field[2].DistMax' in line:
            line = f'Field[2].DistMax = {REFINE_SLOT_DIST};\n'
        if 'Field[4].DistMax' in line:
            line = f'Field[4].DistMax = {REFINE_MID_DIST};\n'
        if 'Field[6].DistMax' in line:
            line = f'Field[6].DistMax = {REFINE_CHAMBER_DIST};\n'
        if 'Field[8].DistMax' in line:
            line = f'Field[8].DistMax = {REFINE_OUTLET_DIST};\n'
        if 'Field[2].SizeMin' in line:
            line = f'Field[2].SizeMin = {REFINE_SIZE_MIN_SLOT};\n'
        if 'Field[4].SizeMin' in line:
            line = f'Field[4].SizeMin = {REFINE_SIZE_MIN_SLOT};\n'
        if 'Field[6].SizeMin' in line:
            line = f'Field[6].SizeMin = {REFINE_SIZE_MIN_SLOT};\n'
        if 'Field[8].SizeMin' in line:
            line = f'Field[8].SizeMin = {REFINE_SIZE_MIN_OUTLET};\n'
        if 'Field[2].SizeMax' in line or 'Field[4].SizeMax' in line or \
           'Field[6].SizeMax' in line or 'Field[8].SizeMax' in line:
            line = re.sub(r'SizeMax = [\d.]+', f'SizeMax = {REFINE_SIZE_MAX}', line)
        
        output_lines.append(line)
    
    # Write output file
    with open(OUTPUT_FILE, 'w') as f:
        f.writelines(output_lines)
    
    # Print summary
    print(f"Substitutions made: {len(changes)}")
    print(f"\nChanges by category:")
    categories = {}
    for cid, (param, old, new) in changes.items():
        if param not in categories:
            categories[param] = []
        categories[param].append((cid, old, new))
    
    for param in sorted(categories.keys()):
        counts = categories[param]
        print(f"  {param}: {len(counts)} lines")
        if len(counts) <= 5:
            for cid, old, new in counts:
                print(f"    Line {cid}: {old} -> {new}")
    
    print(f"\nOutput written to: {OUTPUT_FILE}")
    print(f"\nTo use: Edit create_wedge_v10.py SOURCE_GEO path")
    print(f"        Then run: python3 create_wedge_v10.py")
    
    return True


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        print("Please ensure cvrc_2d_profile.geo_unrolled exists in the same directory.")
        exit(1)
    
    parameterize_geo()