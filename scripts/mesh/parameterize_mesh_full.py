#!/usr/bin/env python3
"""
CVRC 2D Profile Mesh Parameterizer - Full Per-Block Control
===========================================================

COMPLETE parameterization: Each block has its own independent control.

Y-DIRECTION BLOCKS at Inlet (7 blocks stacked):
----------------------------------------------
  y = 3.000 - 3.800 mm  →  NY_SLOT_1  (0.8 mm height)
  y = 3.800 - 5.800 mm  →  NY_SLOT_2  (2.0 mm height)  
  y = 5.800 - 6.300 mm  →  NY_SLOT_3  (0.5 mm height)
  y = 6.300 - 8.000 mm  →  NY_SLOT_4  (1.7 mm height)
  y = 8.000 - 8.300 mm  →  NY_SLOT_5  (0.3 mm height)
  y = 8.300 - 9.700 mm  →  NY_SLOT_6  (1.4 mm height)
  y = 9.700 - 10.235 mm →  NY_SLOT_7  (0.535 mm height)

Usage:
    Edit parameters below, then run:
    python3 parameterize_mesh_full.py
"""

import re
import os

# =============================================================================
# MESH PARAMETERS - EDIT THESE TO CHANGE MESH DENSITY
# =============================================================================

# X-DIRECTION (axial) NODE COUNTS
# Nodes = Cells + 1
#---------------------------------

# Inlet section: x = -160 to -140 mm (oxidizer inlet face)
# 7 blocks stacked vertically, same axial resolution
NX_INLET = 17           # Original: 17 → 16 cells

# Slot strip: x = -140 to -128 mm (thin connecting section)
NX_SLOT_STRIP = 7        # Original: 7 → 6 cells

# Mid section: x = -128 to -10.16 mm
NX_MID_LOW = 13          # Original: 13
NX_MID_HIGH = 49         # Original: 49

# Chamber: x = 0 to 20 mm
NX_CHAMBER = 17          # Original: 17 → 16 cells

# Upper/fuel section
NX_FUEL_STEP = 21        # Original: 21 (fuel step axial)
NX_UPPER = 17            # Original: 17

# Y-DIRECTION PARAMETERS FOR 7 INLET BLOCKS
# Each block can have independent y-resolution
# ------------------------------------------

# INLET BLOCKS (x = -160 to -140 mm): 7 blocks stacked vertically
# Block 1: y=3.0-3.8 mm (thin slot)
NY_INLET_BLOCK_1 = 4     # Original: 4 → 3 cells

# Block 2: y=3.8-5.8 mm (thick slot)
NY_INLET_BLOCK_2 = 9     # Original: 9 → 8 cells

# Block 3: y=5.8-6.3 mm (very thin)
NY_INLET_BLOCK_3 = 3     # Original: 3 → 2 cells

# Block 4: y=6.3-8.0 mm (thick)
NY_INLET_BLOCK_4 = 8     # Original: 8 → 7 cells

# Block 5: y=8.0-8.3 mm (very thin)
NY_INLET_BLOCK_5 = 3     # Original: 3 → 2 cells

# Block 6: y=8.3-9.7 mm (medium)
NY_INLET_BLOCK_6 = 7     # Original: 7 → 6 cells

# Block 7: y=9.7-10.235 mm (thin)
NY_INLET_BLOCK_7 = 4     # Original: 4 → 3 cells

# SLOT STRIP (x = -140 to -128 mm): radial connections
NY_SLOT_STRIP_AXIS = 13   # Original: 13 (y=0 to y=3)
NY_SLOT_STRIP_1 = 4       # Original: 4 (y=3.0-3.8)
NY_SLOT_STRIP_2 = 9       # Original: 9 (y=3.8-5.8)
NY_SLOT_STRIP_3 = 3       # Original: 3 (y=5.8-6.3)
NY_SLOT_STRIP_4 = 8       # Original: 8 (y=6.3-8.0)
NY_SLOT_STRIP_5 = 3       # Original: 3 (y=8.0-8.3)
NY_SLOT_STRIP_6 = 7       # Original: 7 (y=8.3-9.7)
NY_SLOT_STRIP_7 = 4       # Original: 4 (y=9.7-10.235)

# AXIS SECTION (x = -128 to -10.16 mm): main flow
NY_AXIS_3 = 13            # Original: 13 (y=0-3)
NY_AXIS_1 = 4             # Original: 4 (y=3.0-3.8)
NY_AXIS_2 = 9             # Original: 9 (y=3.8-5.8)

# MID SECTION (x = -10.16 to 0 mm)
NY_MID_LOW = 13           # Original: 13
NY_MID_HIGH = 49          # Original: 49

# FUEL STEP
NY_FUEL_Y = 4             # Original: 4

# UPPER SECTION
NY_UPPER_Y = 21           # Original: 21

# Miscellaneous y-direction counts
NY_3 = 3                  # Very thin (2 cells)
NY_4 = 4                  # Thin (3 cells)
NY_7 = 7                  # Medium (6 cells)
NY_8 = 8                  # Thick (7 cells)
NY_9 = 9                  # Thick (8 cells)
NY_11 = 11                # Connect
NY_13 = 13                # Axis
NY_17 = 17                # Chamber
NY_21 = 21                # Upper
NY_49 = 49                # Mid

# =============================================================================
# FILES
# =============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(SCRIPT_DIR, "cvrc_2d_profile.geo_unrolled")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "cvrc_2d_profile_param.geo_unrolled")

# =============================================================================
# LINE MAPPING - Based on geometry analysis
# =============================================================================

def create_line_mapping():
    """
    Map each line ID to its controlled parameter.
    
    Line assignments based on block structure:
    
    INLET BLOCKS (x = -160 to -140 mm):
    - Lines 1,3,6,9,12,15,18,21: horizontal (axial) → NX_INLET = 17
    - Lines 2,4: Block 1 vertical → NY_INLET_BLOCK_1
    - Lines 5,7: Block 2 vertical → NY_INLET_BLOCK_2
    - Lines 8,10: Block 3 vertical → NY_INLET_BLOCK_3
    - Lines 11,13: Block 4 vertical → NY_INLET_BLOCK_4
    - Lines 14,16: Block 5 vertical → NY_INLET_BLOCK_5
    - Lines 17,19: Block 6 vertical → NY_INLET_BLOCK_6
    - Lines 20,22: Block 7 vertical → NY_INLET_BLOCK_7
    """
    
    mapping = {}
    
    # =================================================================
    # GENERIC MAPPINGS (will be overridden by block-specific below)
    # =================================================================
    
    # Lines with 3 nodes (very thin)
    for lid in [27, 30, 44, 49, 60, 62, 66, 68, 69, 74, 76]:
        mapping[lid] = ('NY_3', NY_3)
    
    # Lines with 4 nodes (thin)
    for lid in [24, 28, 33, 54]:
        mapping[lid] = ('NY_4', NY_4)
    
    # Lines with 7 nodes (medium)
    for lid in [25, 29, 31, 34, 51, 53]:
        mapping[lid] = ('NY_7', NY_7)
    
    # Lines with 8 nodes
    for lid in [46, 48]:
        mapping[lid] = ('NY_8', NY_8)
    
    # Lines with 9 nodes
    for lid in [41, 43]:
        mapping[lid] = ('NY_9', NY_9)
    
    # Lines with 11 nodes
    for lid in [59, 61, 63, 65, 67, 70, 78, 80]:
        mapping[lid] = ('NY_11', NY_11)
    
    # Lines with 13 nodes (axis radial)
    for lid in [35, 36, 37, 38, 39, 40, 42, 45, 47, 50, 52, 56]:
        mapping[lid] = ('NY_13', NY_13)
    
    # Lines with 17 nodes (chamber axial)
    for lid in [71, 73, 75, 77, 79]:
        mapping[lid] = ('NX_CHAMBER', NX_CHAMBER)
    
    # Lines with 49 nodes (mid horizontal)
    for lid in [57, 64, 72]:
        mapping[lid] = ('NY_49', NY_49)
    
    # Lines with 21 nodes
    for lid in [55]:
        mapping[lid] = ('NY_21', NY_21)
    
    # =================================================================
    # BLOCK-SPECIFIC MAPPINGS (override generic above)
    # =================================================================
    
    # Inlet horizontal lines (x-direction) - NX_INLET = 17
    for lid in [1, 3, 6, 9, 12, 15, 18, 21]:
        mapping[lid] = ('NX_INLET', NX_INLET)
    
    # Inlet Block 1 (y=3.0-3.8): Lines 2, 4 → NY_INLET_BLOCK_1
    for lid in [2, 4]:
        mapping[lid] = ('NY_INLET_BLOCK_1', NY_INLET_BLOCK_1)
    
    # Inlet Block 2 (y=3.8-5.8): Lines 5, 7 → NY_INLET_BLOCK_2
    for lid in [5, 7]:
        mapping[lid] = ('NY_INLET_BLOCK_2', NY_INLET_BLOCK_2)
    
    # Inlet Block 3 (y=5.8-6.3): Lines 8, 10 → NY_INLET_BLOCK_3
    for lid in [8, 10]:
        mapping[lid] = ('NY_INLET_BLOCK_3', NY_INLET_BLOCK_3)
    
    # Inlet Block 4 (y=6.3-8.0): Lines 11, 13 → NY_INLET_BLOCK_4
    for lid in [11, 13]:
        mapping[lid] = ('NY_INLET_BLOCK_4', NY_INLET_BLOCK_4)
    
    # Inlet Block 5 (y=8.0-8.3): Lines 14, 16 → NY_INLET_BLOCK_5
    for lid in [14, 16]:
        mapping[lid] = ('NY_INLET_BLOCK_5', NY_INLET_BLOCK_5)
    
    # Inlet Block 6 (y=8.3-9.7): Lines 17, 19 → NY_INLET_BLOCK_6
    for lid in [17, 19]:
        mapping[lid] = ('NY_INLET_BLOCK_6', NY_INLET_BLOCK_6)
    
    # Inlet Block 7 (y=9.7-10.235): Lines 20, 22 → NY_INLET_BLOCK_7
    for lid in [20, 22]:
        mapping[lid] = ('NY_INLET_BLOCK_7', NY_INLET_BLOCK_7)
    
    # Slot strip horizontal (x-direction) - NX_SLOT_STRIP = 7
    for lid in [23, 25, 26, 28, 29, 31, 32, 34]:
        mapping[lid] = ('NX_SLOT_STRIP', NX_SLOT_STRIP)
    
    return mapping

# =============================================================================
# MAIN FUNCTION
# =============================================================================

def parameterize_geo():
    """Apply all parameter substitutions."""
    
    print(f"\n{'='*70}")
    print("CVRC 2D Profile Mesh Parameterizer (Per-Block)")
    print(f"{'='*70}")
    print(f"\nInput:  {INPUT_FILE}")
    print(f"Output: {OUTPUT_FILE}")
    
    # Read original file
    with open(INPUT_FILE, 'r') as f:
        content = f.read()
    
    # Get line mapping
    mapping = create_line_mapping()
    
    print(f"\nParameters:")
    print(f"  NX_INLET = {NX_INLET}")
    print(f"  NX_SLOT_STRIP = {NX_SLOT_STRIP}")
    print(f"  NX_MID_LOW = {NX_MID_LOW}")
    print(f"  NX_CHAMBER = {NX_CHAMBER}")
    print(f"\n  NY_INLET_BLOCK_1 = {NY_INLET_BLOCK_1}  (y=3.0-3.8mm)")
    print(f"  NY_INLET_BLOCK_2 = {NY_INLET_BLOCK_2}  (y=3.8-5.8mm)")
    print(f"  NY_INLET_BLOCK_3 = {NY_INLET_BLOCK_3}  (y=5.8-6.3mm)")
    print(f"  NY_INLET_BLOCK_4 = {NY_INLET_BLOCK_4}  (y=6.3-8.0mm)")
    print(f"  NY_INLET_BLOCK_5 = {NY_INLET_BLOCK_5}  (y=8.0-8.3mm)")
    print(f"  NY_INLET_BLOCK_6 = {NY_INLET_BLOCK_6}  (y=8.3-9.7mm)")
    print(f"  NY_INLET_BLOCK_7 = {NY_INLET_BLOCK_7}  (y=9.7-10.235mm)")
    print(f"{'='*70}\n")
    
    # Apply substitutions - handle "Using Progression 1" format
    changes = {}
    for line_id, (param, value) in mapping.items():
        # Match both with and without "Using Progression"
        patterns = [
            (f'Transfinite Curve \\{{{line_id}\\}} = \\d+ Using Progression \\d+',
             f'Transfinite Curve {{{line_id}}} = {value} Using Progression 1'),
            (f'Transfinite Curve \\{{{line_id}\\}} = \\d+',
             f'Transfinite Curve {{{line_id}}} = {value}'),
        ]
        for pattern, replacement in patterns:
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                changes[line_id] = (param, value)
                content = new_content
                break
    
    # Write output
    with open(OUTPUT_FILE, 'w') as f:
        f.write(content)
    
    print(f"Substitutions made: {len(changes)}")
    print(f"\nChanges by line:")
    for lid in sorted(changes.keys()):
        param, value = changes[lid]
        print(f"  Line {lid}: {param} = {value}")
    
    print(f"\nOutput: {OUTPUT_FILE}")
    print(f"\nTo use:")
    print(f"  1. Edit parameters at top of this script")
    print(f"  2. Run: python3 {os.path.basename(__file__)}")
    print(f"  3. Run: ./scripts/run_mesh_pipeline.sh --param --clean")
    
    return True


if __name__ == "__main__":
    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        exit(1)
    
    parameterize_geo()