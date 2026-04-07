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

# Axis radial connections: y-direction node counts in slot strip
# These are the radial connections between inlet blocks
NY_SLOT_STRIP_AXIS = 13  # Original: 13 → 12 cells (y=0 to y=3)
NY_SLOT_STRIP_S1 = 4    # Original: 4 → 3 cells (y=3.0-3.8)
NY_SLOT_STRIP_S2 = 9    # Original: 9 → 8 cells (y=3.8-5.8)
NY_SLOT_STRIP_S3 = 3    # Original: 3 → 2 cells (y=5.8-6.3)
NY_SLOT_STRIP_S4 = 8    # Original: 8 → 7 cells (y=6.3-8.0)
NY_SLOT_STRIP_S5 = 3    # Original: 3 → 2 cells (y=8.0-8.3)
NY_SLOT_STRIP_S6 = 7    # Original: 7 → 6 cells (y=8.3-9.7)
NY_SLOT_STRIP_S7 = 4    # Original: 4 → 3 cells (y=9.7-10.235)

# Main axial channel: x = -128 to -10.16 mm (plenum before chamber)
NY_AXIS_LOW = 13        # Original: 13 → 12 cells (y=0 to y=3.0)
NY_AXIS_S1 = 4          # Original: 4 → 3 cells (y=3.0-3.8)
NY_AXIS_S2 = 9          # Original: 9 → 8 cells (y=3.8-5.8)
NY_AXIS_S3 = 3          # Original: 3 → 2 cells (y=5.8-6.3)
NY_AXIS_S4 = 8          # Original: 8 → 7 cells (y=6.3-8.0)
NY_AXIS_S5 = 3          # Original: 3 → 2 cells (y=8.0-8.3)
NY_AXIS_S6 = 7          # Original: 7 → 6 cells (y=8.3-9.7)
NY_AXIS_S7 = 4          # Original: 4 → 3 cells (y=9.7-10.235)

# Mid section: x = -10.16 to 0 mm
NX_MID = 49             # Original: 49 → 48 cells (main horizontal)
NY_MID_LOW = 13         # Original: 13 → 12 cells (y=0 to y=10.235)
NY_MID_SLOT_Y = 49      # Original: 49 → 48 cells (horizontal mid chamber)
NY_MID_Y43_44 = 11      # Original: 11 (fuel step connections)
NY_MID_Y42_36 = 11      # Original: 11

# Chamber: x = 0 to 20 mm
NX_CHAMBER = 17         # Original: 17 → 16 cells
NY_CHAMBER_LOW = 17     # Original: 17 (y=0 to y=10.235)
NY_CHAMBER_Y42 = 11    # Original: 11 (y=10.235 to y=11)
NY_CHAMBER_Y44 = 11    # Original: 11 (y=11 to y=11.53)

# Upper/fuel section
NX_FUEL_STEP = 21       # Original: 21 (fuel step axial)
NY_FUEL = 4             # Original: 4 (fuel annulus height)
NY_UPPER = 21          # Original: 21 (upper section)

# Y-DIRECTION PARAMETERS FOR 7 INLET BLOCKS
# ------------------------------------------
# Block 1: y=3.0-3.8 mm
NY_INLET_BLOCK_1 = 11    # Original: 4 → 3 cells

# Block 2: y=3.8-5.8 mm
NY_INLET_BLOCK_2 = 9    # Original: 9 → 8 cells

# Block 3: y=5.8-6.3 mm  
NY_INLET_BLOCK_3 = 6    # Original: 3 → 2 cells

# Block 4: y=6.3-8.0 mm
NY_INLET_BLOCK_4 = 8    # Original: 8 → 7 cells

# Block 5: y=8.0-8.3 mm
NY_INLET_BLOCK_5 = 7    # Original: 3 → 2 cells

# Block 6: y=8.3-9.7 mm
NY_INLET_BLOCK_6 = 7    # Original: 7 → 6 cells

# Block 7: y=9.7-10.235 mm
NY_INLET_BLOCK_7 = 4    # Original: 4 → 3 cells

# Slot strip inlet connections (x = -140 mm face)
NY_INLET_STRIP_1 = 7    # Original: 7 → 6 cells
NY_INLET_STRIP_2 = 7    # Original: 7 → 6 cells
NY_INLET_STRIP_3 = 7    # Original: 7 → 6 cells
NY_INLET_STRIP_4 = 7    # Original: 7 → 6 cells

# =============================================================================
# FILES
# =============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(SCRIPT_DIR, "cvrc_2d_profile.geo_unrolled")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "cvrc_2d_profile_param.geo_unrolled")

# =============================================================================
# ANALYZE ORIGINAL FILE
# =============================================================================

def analyze_original():
    """Analyze the original geo file to understand line counts."""
    with open(INPUT_FILE, 'r') as f:
        lines = f.readlines()
    
    # Find all Transfinite Curve lines
    counts = {}
    for line in lines:
        match = re.search(r'Transfinite Curve \{(\d+)\} = (\d+)', line)
        if match:
            line_id = int(match.group(1))
            node_count = int(match.group(2))
            if node_count not in counts:
                counts[node_count] = []
            counts[node_count].append(line_id)
    
    return counts

def parameterize_geo():
    """Apply all parameter substitutions."""
    
    print(f"\n{'='*70}")
    print("CVRC 2D Profile Mesh Parameterizer (Per-Block)")
    print(f"{'='*70}")
    print(f"\nInput:  {INPUT_FILE}")
    print(f"Output: {OUTPUT_FILE}")
    
    # Analyze original
    counts = analyze_original()
    print(f"\nOriginal file has {sum(len(v) for v in counts.values())} transfinite curves")
    print(f"Node count distribution:")
    for nc in sorted(counts.keys()):
        print(f"  {nc:3d} nodes: {len(counts[nc]):3d} lines")
    
    print(f"\nParameters to apply:")
    print(f"  X-DIRECTION (axial):")
    print(f"    NX_INLET      = {NX_INLET:3d}  (inlet, 7 blocks)")
    print(f"    NX_SLOT_STRIP = {NX_SLOT_STRIP:3d}  (slot strip)")
    print(f"    NX_MID        = {NX_MID:3d}  (mid section)")
    print(f"    NX_CHAMBER    = {NX_CHAMBER:3d}  (chamber)")
    print(f"    NX_FUEL_STEP  = {NX_FUEL_STEP:3d}  (fuel step)")
    print(f"\n  Y-DIRECTION (radial) at inlet:")
    print(f"    NY_INLET_BLOCK_1 = {NY_INLET_BLOCK_1:3d}  (y=3.0-3.8mm)")
    print(f"    NY_INLET_BLOCK_2 = {NY_INLET_BLOCK_2:3d}  (y=3.8-5.8mm)")
    print(f"    NY_INLET_BLOCK_3 = {NY_INLET_BLOCK_3:3d}  (y=5.8-6.3mm)")
    print(f"    NY_INLET_BLOCK_4 = {NY_INLET_BLOCK_4:3d}  (y=6.3-8.0mm)")
    print(f"    NY_INLET_BLOCK_5 = {NY_INLET_BLOCK_5:3d}  (y=8.0-8.3mm)")
    print(f"    NY_INLET_BLOCK_6 = {NY_INLET_BLOCK_6:3d}  (y=8.3-9.7mm)")
    print(f"    NY_INLET_BLOCK_7 = {NY_INLET_BLOCK_7:3d}  (y=9.7-10.235mm)")
    print(f"\n  Y-DIRECTION elsewhere:")
    print(f"    NY_AXIS = {NY_AXIS_LOW:3d} (axis radial)")
    print(f"    NY_MID  = {NY_MID_LOW:3d} (mid section radial)")
    print(f"    NY_UPPER = {NY_UPPER:3d} (upper sections)")
    print(f"{'='*70}\n")
    
    # Read original
    with open(INPUT_FILE, 'r') as f:
        content = f.read()
    
    substitutions = {}
    
    # Map node counts to parameters based on line position
    # This is the critical part - need to know which lines map to which blocks
    
    # Lines with 3 nodes - very thin slots (2 cells)
    # These are lines 8,10,14,16,27,30,44,49,60,62,66,68,69,74,76
    for lid in [8, 10, 14, 16, 27, 30, 44, 49, 60, 62, 66, 68, 69, 74, 76]:
        substitutions[lid] = 3  # NY_VERY_THIN
    
    # Lines with 4 nodes - thin slots (3 cells)
    # These are: 2,4,20,22,24,28,33,54 and others
    for lid in [2, 4, 20, 22, 24, 28, 33, 54]:
        substitutions[lid] = 4  # NY_THIN
    
    # Lines with 7 nodes - medium (6 cells)
    for lid in [23, 25, 26, 29, 31, 32, 34, 51, 53]:
        substitutions[lid] = 7  # NY_MEDIUM
    
    # Lines with 8 nodes - thick 7 cells
    for lid in [11, 13, 46, 48]:
        substitutions[lid] = 8  # NY_THICK_7
    
    # Lines with 9 nodes - thick (8 cells)
    for lid in [5, 7, 41, 43]:
        substitutions[lid] = 9  # NY_SLOT_THICK
    
    # Lines with 11 nodes
    for lid in [59, 61, 63, 65, 67, 70, 78, 80]:
        substitutions[lid] = 11  # NY_CONN or NY_FUEL
    
    # Lines with 13 nodes - axis radial
    for lid in [35, 36, 37, 38, 39, 40, 42, 45, 47, 50, 52, 54, 55]:
        substitutions[lid] = 13  # NY_AXIS
    
    # Lines with 17 nodes - chamber/step
    for lid in [1, 3, 6, 9, 12, 15, 18, 21, 71, 73, 75, 77, 79]:
        substitutions[lid] = 17  # NX_INLET or NX_CHAMBER
    
    # Lines with 49 nodes - mid horizontal
    for lid in [57, 64, 72]:
        substitutions[lid] = 49  # NX_MID
    
    # Lines with 21 nodes - upper
    for lid in [59, 61, 78, 80]:
        substitutions[lid] = 21  # NY_UPPER
    
    # Apply substitutions
    changes = 0
    for line_id, node_count in substitutions.items():
        pattern = f'Transfinite Curve \\{{{line_id}\\}} = \\d+'
        replacement = f'Transfinite Curve {{{line_id}}} = {node_count}'
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            changes += 1
            content = new_content
    
    # Write output
    with open(OUTPUT_FILE, 'w') as f:
        f.write(content)
    
    print(f"Substitutions attempted: {len(substitutions)}")
    print(f"Changes made: {changes}")
    print(f"Output: {OUTPUT_FILE}")
    
    return True


if __name__ == "__main__":
    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        exit(1)
    
    parameterize_geo()