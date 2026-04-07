#!/usr/bin/env python3
"""
CVRC 2D Profile Mesh Parameterizer - Full Per-Block Control
===========================================================

Complete parameterization: Each block has its own independent control.

Usage:
    Edit parameters below, then run:
    python3 parameterize_mesh_full.py
"""

import re
import os

# =============================================================================
# MESH PARAMETERS - EDIT THESE TO CHANGE MESH DENSITY
# =============================================================================

# X-DIRECTION (axial) NODE COUNTS - leave None to use original
# ---------------------------------------------------------------

NX_INLET = None       # Original: 17
NX_SLOT_STRIP = None   # Original: 7
NX_MID_LOW = None      # Original: 13
NX_MID_HIGH = None     # Original: 49
NX_CHAMBER = None      # Original: 17
NX_FUEL_STEP = None    # Original: 21
NX_UPPER = None        # Original: 17

# Y-DIRECTION - INLET BLOCKS (7 blocks at x = -160 to -140 mm)
# Set to None to use original, or specify new value
# ------------------------------------------------------------

NY_INLET_BLOCK_1 = None  # y=3.0-3.8mm, Original: 4
NY_INLET_BLOCK_2 = None  # y=3.8-5.8mm, Original: 9
NY_INLET_BLOCK_3 = None  # y=5.8-6.3mm, Original: 3
NY_INLET_BLOCK_4 = None  # y=6.3-8.0mm, Original: 8
NY_INLET_BLOCK_5 = None  # y=8.0-8.3mm, Original: 3
NY_INLET_BLOCK_6 = None  # y=8.3-9.7mm, Original: 7
NY_INLET_BLOCK_7 = None  # y=9.7-10.235mm, Original: 4

# =============================================================================
# FILES
# =============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(SCRIPT_DIR, "cvrc_2d_profile.geo_unrolled")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "cvrc_2d_profile_param.geo_unrolled")

# =============================================================================
# LINE MAPPING - DO NOT EDIT BELOW
# =============================================================================

def create_line_mapping():
    """
    Map each line ID to its controlled parameter and original value.
    Lines are organized by geometry block.
    """
    
    # Read original file to get current values
    with open(INPUT_FILE, 'r') as f:
        content = f.read()
    
    # Extract current values for each line
    current_values = {}
    for match in re.finditer(r'Transfinite Curve \{(\d+)\} = (\d+)', content):
        line_id = int(match.group(1))
        node_count = int(match.group(2))
        current_values[line_id] = node_count
    
    # Build mapping of lines to user parameters
    # Format: (line_ids, param_name, param_value)
    # If param_value is None, keep original
    
    substitutions = {}
    
    # Inlet horizontal lines (x-direction) - NX_INLET
    nx_inlet = NX_INLET if NX_INLET is not None else current_values.get(1, 17)
    for lid in [1, 3, 6, 9, 12, 15, 18, 21]:
        substitutions[lid] = ('NX_INLET', nx_inlet)
    
    # Inlet Block 1 (y=3.0-3.8): Lines 2, 4
    ny_b1 = NY_INLET_BLOCK_1 if NY_INLET_BLOCK_1 is not None else current_values.get(2, 4)
    for lid in [2, 4]:
        substitutions[lid] = ('NY_INLET_BLOCK_1', ny_b1)
    
    # Inlet Block 2 (y=3.8-5.8): Lines 5, 7
    ny_b2 = NY_INLET_BLOCK_2 if NY_INLET_BLOCK_2 is not None else current_values.get(5, 9)
    for lid in [5, 7]:
        substitutions[lid] = ('NY_INLET_BLOCK_2', ny_b2)
    
    # Inlet Block 3 (y=5.8-6.3): Lines 8, 10
    ny_b3 = NY_INLET_BLOCK_3 if NY_INLET_BLOCK_3 is not None else current_values.get(8, 3)
    for lid in [8, 10]:
        substitutions[lid] = ('NY_INLET_BLOCK_3', ny_b3)
    
    # Inlet Block 4 (y=6.3-8.0): Lines 11, 13
    ny_b4 = NY_INLET_BLOCK_4 if NY_INLET_BLOCK_4 is not None else current_values.get(11, 8)
    for lid in [11, 13]:
        substitutions[lid] = ('NY_INLET_BLOCK_4', ny_b4)
    
    # Inlet Block 5 (y=8.0-8.3): Lines 14, 16
    ny_b5 = NY_INLET_BLOCK_5 if NY_INLET_BLOCK_5 is not None else current_values.get(14, 3)
    for lid in [14, 16]:
        substitutions[lid] = ('NY_INLET_BLOCK_5', ny_b5)
    
    # Inlet Block 6 (y=8.3-9.7): Lines 17, 19
    ny_b6 = NY_INLET_BLOCK_6 if NY_INLET_BLOCK_6 is not None else current_values.get(17, 7)
    for lid in [17, 19]:
        substitutions[lid] = ('NY_INLET_BLOCK_6', ny_b6)
    
    # Inlet Block 7 (y=9.7-10.235): Lines 20, 22
    ny_b7 = NY_INLET_BLOCK_7 if NY_INLET_BLOCK_7 is not None else current_values.get(20, 4)
    for lid in [20, 22]:
        substitutions[lid] = ('NY_INLET_BLOCK_7', ny_b7)
    
    return substitutions, current_values

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
    substitutions, current_values = create_line_mapping()
    
    print(f"\nParameters:")
    print(f"  NX_INLET = {NX_INLET if NX_INLET else 'original (' + str(current_values.get(1, 17)) + ')'}")
    print(f"\n  NY_INLET_BLOCK_1 = {NY_INLET_BLOCK_1 if NY_INLET_BLOCK_1 else 'original (' + str(current_values.get(2, 4)) + ')'}  (y=3.0-3.8mm)")
    print(f"  NY_INLET_BLOCK_2 = {NY_INLET_BLOCK_2 if NY_INLET_BLOCK_2 else 'original (' + str(current_values.get(5, 9)) + ')'}  (y=3.8-5.8mm)")
    print(f"  NY_INLET_BLOCK_3 = {NY_INLET_BLOCK_3 if NY_INLET_BLOCK_3 else 'original (' + str(current_values.get(8, 3)) + ')'}  (y=5.8-6.3mm)")
    print(f"  NY_INLET_BLOCK_4 = {NY_INLET_BLOCK_4 if NY_INLET_BLOCK_4 else 'original (' + str(current_values.get(11, 8)) + ')'}  (y=6.3-8.0mm)")
    print(f"  NY_INLET_BLOCK_5 = {NY_INLET_BLOCK_5 if NY_INLET_BLOCK_5 else 'original (' + str(current_values.get(14, 3)) + ')'}  (y=8.0-8.3mm)")
    print(f"  NY_INLET_BLOCK_6 = {NY_INLET_BLOCK_6 if NY_INLET_BLOCK_6 else 'original (' + str(current_values.get(17, 7)) + ')'}  (y=8.3-9.7mm)")
    print(f"  NY_INLET_BLOCK_7 = {NY_INLET_BLOCK_7 if NY_INLET_BLOCK_7 else 'original (' + str(current_values.get(20, 4)) + ')'}  (y=9.7-10.235mm)")
    print(f"{'='*70}\n")
    
    # Apply substitutions - handle "Using Progression 1" format
    changes = {}
    for line_id in sorted(substitutions.keys()):
        param, value = substitutions[line_id]
        patterns = [
            (f'Transfinite Curve \\{{{line_id}\\}} = \\d+ Using Progression \\d+',
             f'Transfinite Curve {{{line_id}}} = {value} Using Progression 1'),
            (f'Transfinite Curve \\{{{line_id}\\}} = \\d+',
             f'Transfinite Curve {{{line_id}}} = {value}'),
        ]
        for pattern, replacement in patterns:
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                old_value = current_values.get(line_id, '?')
                if value != old_value:
                    changes[line_id] = (param, old_value, value)
                content = new_content
                break
    
    # Write output
    with open(OUTPUT_FILE, 'w') as f:
        f.write(content)
    
    if changes:
        print(f"Substitutions made: {len(changes)}")
        print(f"\nChanges (only showing lines where value changed):")
        for lid in sorted(changes.keys()):
            param, old_val, new_val = changes[lid]
            print(f"  Line {lid:2d}: {param} = {new_val} (was {old_val})")
    else:
        print("No changes made (all values match original)")
    
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