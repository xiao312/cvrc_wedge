#!/usr/bin/env python3
"""
CVRC 2D Profile Mesh Parameterizer - Constraint-Aware
=====================================================

TRANFINITE MESH CONSTRAINT:
For each rectangular surface, opposite edges must have MATCHING node counts!

Surface Definition (from Curve Loop analysis):
---------------------------------------------------------
Surface 1:  Lines {1, 2, 3, 4}
  - Lines 1, 3: horizontal (NX_INLET = 17)
  - Lines 2, 4: vertical (NY_LAYER_1 = 4)

Surface 8:  Lines {23, 24, 25, -2}
  - Lines 23, 25: horizontal (NX_SLOT_STRIP = 7)
  - Lines 24, 2: vertical → NY_LAYER_1 must apply to BOTH lines

...etc.

CONSTRAINT CHAIN:
- NY_LAYER_1 affects: lines 2, 4, 24, 39, 54, 74, 76
- NY_LAYER_2 affects: lines 5, 7, 40, 43
- NY_LAYER_3 affects: lines 8, 10, 44, 49
- NY_LAYER_4 affects: lines 11, 13, 46, 48
- NY_LAYER_5 affects: lines 14, 16, 50, 52
- NY_LAYER_6 affects: lines 17, 19, 51, 53
- NY_LAYER_7 affects: lines 20, 22, 27, 30

Usage:
    Edit parameters below, then run:
    python3 parameterize_mesh_full.py
"""

import re
import os

# =============================================================================
# MESH PARAMETERS - EDIT THESE TO CHANGE MESH DENSITY
# All parameters set to None will use original values
# =============================================================================

# X-DIRECTION (axial) NODE COUNTS
# These control horizontal edges of rectangular blocks

NX_INLET = None       # lines 1,3,6,9,12,15,18,21. Original: 17 cells
NX_SLOT_STRIP = None   # lines 23,25,26,28,29,31,32,34. Original: 7 cells
NX_AXIS = None         # Original: 13
NX_MID = None          # lines 57,64,72. Original: 49
NX_CHAMBER = None      # lines 71,73,75,77,79. Original: 17

# Y-DIRECTION (radial) NODE COUNTS
# Each layer corresponds to a y-range. ALL vertical edges in that layer must match!

# Layer 1: y = 3.0 - 3.8 mm (thin oxidizer slot - bottom slot)
NY_LAYER_1 = None  # Original: 4 nodes. Lines: 2, 4, 24, 39, 54, 74, 76

# Layer 2: y = 3.8 - 5.8 mm (thick oxidizer slot)
NY_LAYER_2 = None  # Original: 9 nodes. Lines: 5, 7, 40, 43

# Layer 3: y = 5.8 - 6.3 mm (thin slot)
NY_LAYER_3 = None  # Original: 3 nodes. Lines: 8, 10, 44, 49

# Layer 4: y = 6.3 - 8.0 mm (thick slot)
NY_LAYER_4 = None  # Original: 8 nodes. Lines: 11, 13, 46, 48

# Layer 5: y = 8.0 - 8.3 mm (very thin slot)
NY_LAYER_5 = None  # Original: 3 nodes. Lines: 14, 16, 50, 52

# Layer 6: y = 8.3 - 9.7 mm (medium slot)
NY_LAYER_6 = None  # Original: 7 nodes. Lines: 17, 19, 51, 53

# Layer 7: y = 9.7 - 10.235 mm (thin top slot)
NY_LAYER_7 = None  # Original: 4 nodes. Lines: 20, 22, 27, 30

# Axis layer: y = 0 - 3.0 mm (below oxidizer inlet)
NY_AXIS = None  # Original: 13 nodes. Lines: 35, 36, 37, 38

# =============================================================================
# CONSTRAINT MAPPING - DO NOT EDIT BELOW THIS LINE
# =============================================================================

# Each layer has vertical edges that MUST have matching node counts
# across all surfaces in that y-range
# IMPORTANT: Lines are connected ACROSS x-sections!
# For example: Line 2 (inlet) connects to Line 24 (slot strip)

# Complete constraint chain for each y-layer:
# Layer 1 (y=3.0-3.8mm):
#   - Lines 2, 4: inlet section
#   - Lines 24, 39: slot strip and axis connections (must match!)
# But lines 39 has different context, so only lines 2, 4, 24 must match

LAYER_CONSTRAINTS = {
    'NY_LAYER_1': [2, 4, 24],      # Inlet + slot strip connection
    'NY_LAYER_2': [5, 7],           # Inlet block 2
    'NY_LAYER_3': [8, 10],          # Inlet block 3
    'NY_LAYER_4': [11, 13],         # Inlet block 4
    'NY_LAYER_5': [14, 16],         # Inlet block 5
    'NY_LAYER_6': [17, 19],         # Inlet block 6
    'NY_LAYER_7': [20, 22],         # Inlet block 7 (lines 27,30 are in different section)
    'NY_AXIS': [35, 36, 37, 38],    # Axis section
}

# Axial lines (horizontal edges)
AXIAL_CONSTRAINTS = {
    'NX_INLET': [1, 3, 6, 9, 12, 15, 18, 21],
    'NX_SLOT_STRIP': [23, 25, 26, 28, 29, 31, 32, 34],
}

# =============================================================================
# FILES
# =============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(SCRIPT_DIR, "cvrc_2d_profile.geo_unrolled")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "cvrc_2d_profile_param.geo_unrolled")

# =============================================================================
# MAIN FUNCTION
# =============================================================================

def parameterize_geo():
    """Apply parameter substitutions with constraint checking."""

    print(f"\n{'='*70}")
    print("CVRC 2D Profile Mesh Parameterizer (Constraint-Aware)")
    print(f"{'='*70}")
    print(f"\nInput:  {INPUT_FILE}")
    print(f"Output: {OUTPUT_FILE}")

    # Read original file
    with open(INPUT_FILE, 'r') as f:
        content = f.read()

    # Extract current values
    current_values = {}
    for match in re.finditer(r'Transfinite Curve \{(\d+)\} = (\d+)', content):
        line_id = int(match.group(1))
        node_count = int(match.group(2))
        current_values[line_id] = node_count

    # Collect all changes
    changes = {}

    # Helper to apply changes to a group of lines
    def apply_constraint(param_name, param_value, line_ids):
        if param_value is None:
            return  # Use original
        for lid in line_ids:
            if lid in current_values:
                old_val = current_values[lid]
                changes[lid] = (param_name, param_value, old_val)

    # Print header
    print("\n📊 Current mesh density parameters:")
    print(f"{'='*70}")

    # Apply Y-direction (radial layer) parameters
    y_params = {
        'NY_LAYER_1': (NY_LAYER_1, 'y=3.0-3.8mm (thin slot 1)'),
        'NY_LAYER_2': (NY_LAYER_2, 'y=3.8-5.8mm (thick slot 2)'),
        'NY_LAYER_3': (NY_LAYER_3, 'y=5.8-6.3mm (thin slot 3)'),
        'NY_LAYER_4': (NY_LAYER_4, 'y=6.3-8.0mm (thick slot 4)'),
        'NY_LAYER_5': (NY_LAYER_5, 'y=8.0-8.3mm (very thin slot 5)'),
        'NY_LAYER_6': (NY_LAYER_6, 'y=8.3-9.7mm (medium slot 6)'),
        'NY_LAYER_7': (NY_LAYER_7, 'y=9.7-10.235mm (thin slot 7)'),
        'NY_AXIS': (NY_AXIS, 'y=0-3.0mm (axis region)'),
    }

    print("\n🔄 Y-DIRECTION (radial layers):")
    for param_name, (value, desc) in y_params.items():
        line_ids = LAYER_CONSTRAINTS[param_name]
        current = current_values.get(line_ids[0], '?')
        if value is not None:
            print(f"  {param_name}: {value} nodes (was {current}) - {desc}")
            apply_constraint(param_name, value, line_ids)
        else:
            print(f"  {param_name}: {current} nodes (original) - {desc}")

    # Apply X-direction (axial) parameters
    print("\n➡️ X-DIRECTION (axial):")
    x_params = {
        'NX_INLET': (NX_INLET, 'inlet section'),
        'NX_SLOT_STRIP': (NX_SLOT_STRIP, 'slot strip'),
    }

    for param_name, (value, desc) in x_params.items():
        line_ids = AXIAL_CONSTRAINTS[param_name]
        current = current_values.get(line_ids[0], '?')
        if value is not None:
            print(f"  {param_name}: {value} nodes (was {current}) - {desc}")
            apply_constraint(param_name, value, line_ids)
        else:
            print(f"  {param_name}: {current} nodes (original) - {desc}")

    print(f"\n{'='*70}")

    # If no changes, skip file modification
    if not changes:
        print("i️  No changes specified - output will be identical to input")
        with open(OUTPUT_FILE, 'w') as f:
            f.write(content)
        return True

    # Verify constraints before applying
    print("\n✅ Constraint verification:")
    all_valid = True
    for param_name, line_ids in LAYER_CONSTRAINTS.items():
        values = [changes.get(lid, (None, current_values.get(lid)))[1] for lid in line_ids if lid in current_values]
        if len(set(values)) != 1:
            print(f"  ❌ {param_name}: INCONSISTENT values {values}")
            all_valid = False
        else:
            print(f"  ✓ {param_name}: all {values[0]} nodes")

    for param_name, line_ids in AXIAL_CONSTRAINTS.items():
        values = [changes.get(lid, (None, current_values.get(lid)))[1] for lid in line_ids if lid in current_values]
        if len(set(values)) != 1:
            print(f"  ❌ {param_name}: INCONSISTENT values {values}")
            all_valid = False
        else:
            print(f"  ✓ {param_name}: all {values[0]} nodes")

    if not all_valid:
        print("\n⚠️  WARNING: Some constraints are not satisfied!")
        print("   The mesh may fail to generate or have poor quality.")

    # Apply changes
    print(f"\n📝 Applying {len(changes)} line changes...")
    for line_id in sorted(changes.keys()):
        param_name, new_val, old_val = changes[line_id]
        pattern = f'Transfinite Curve \\{{{line_id}\\}} = \\d+'
        replacement = f'Transfinite Curve {{{line_id}}} = {new_val}'
        content = re.sub(pattern, replacement, content)

    # Write output
    with open(OUTPUT_FILE, 'w') as f:
        f.write(content)

    print(f"\n✅ Output written to: {OUTPUT_FILE}")
    print(f"\n📋 To use:")
    print(f"   1. Verify parameters above are correct")
    print(f"   2. Run: ./scripts/run_mesh_pipeline.sh --param --clean")
    print(f"{'='*70}\n")

    return True


if __name__ == "__main__":
    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        exit(1)

    parameterize_geo()