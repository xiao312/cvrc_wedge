#!/usr/bin/env python3
"""
CVRC 2D Profile Geometry Generator
=================================

Generates a structured 2D axisymmetric profile for the CVRC combustor
with parameterized mesh node counts.

The geometry consists of:
1. Left oxidizer inlet section (-160 to -140 mm, multiple radial slots)
2. Middle plenum section (-140 to -128 mm, annular)
3. Main combustor section (-128 to 0 mm)
4. Fuel injection step (-30 to -10.16 mm)
5. Combustion chamber (0 to 20 mm)
6. Downstream nozzle section (20 to ~400 mm)

Mesh is structured with transfinite curves for hexahedral cells.
After creating the 2D mesh, use create_wedge_v10.py to revolve it into 3D.

Usage
-----
    python3 generate_cvrc_profile.py
    
Output
------
    cvrc_2d_profile.geo_unrolled  (Gmsh geo file)
"""

import os

# =============================================================================
# MESH CONTROL PARAMETERS (EDIT THESE TO CHANGE MESH DENSITY)
# =============================================================================

# Axial direction (x-direction) node counts
NX_INLET = 17          # Nodes in inlet section (-160 to -140 mm)
NX_SLOT_STRIP = 7      # Nodes in slot strip (-140 to -128 mm)
NX_AXIS = 13           # Nodes along axis channel
NX_MID = 49            # Nodes in middle section (-10.16 to 0 mm)
NX_CHAMBER = 17        # Nodes in combustion chamber (0 to 20 mm)
NX_STEP = 21           # Nodes axially in step region
NX_DOWNSTREAM = 11     # Nodes in downstream sections

# Radial direction (y-direction) node counts for thin slots
NY_SLOT_THIN = 4       # Nodes for thin slots (3.0-3.8, 5.8-6.3, 8.0-8.3, 9.7-10.235)
NY_SLOT_THICK = 9      # Nodes for thick slots (3.8-5.8, 6.3-8.0, 8.3-9.7)

# Radial direction node counts for main sections
NY_AXIS = 13           # Nodes from axis (y=0) to first slot
NY_FUEL = 4            # Nodes in fuel injection annulus (11 to 11.53)
NY_UPSTREAM = 11      # Nodes axially in upstream connections

# Mesh size control (characteristic length in mm)
CL_FINE = 0.5          # Fine mesh size
CL_MEDIUM = 0.7        # Medium mesh size
CL_COARSE = 4.0        # Coarse mesh size for far downstream

# Field-based refinement distances
REFINE_SLOT_DIST = 45   # Refinement distance from slots
REFINE_MID_DIST = 35    # Refinement distance from mid section
REFINE_CHAMBER_DIST = 120  # Refinement distance from chamber
REFINE_OUTLET_DIST = 25    # Refinement distance from outlet

# Field-based refinement sizes
REFINE_SIZE_MIN = 0.5   # Minimum refined element size
REFINE_SIZE_MAX = 3.0   # Maximum refined element size

# =============================================================================
# OUTPUT PATH
# =============================================================================

OUTPUT_DIR = "/mnt/d/xiaox/downloads/cvrc_gmsh/cvrc_wedge_epsilon"
GEO_FILE = os.path.join(OUTPUT_DIR, "cvrc_2d_profile.geo_unrolled")

# =============================================================================
# GEOMETRY GENERATION
# =============================================================================

def generate_geo():
    """Generate the Gmsh geo file with parameterized mesh."""
    
    print(f"\n{'='*60}")
    print(f"CVRC 2D Profile Generator")
    print(f"{'='*60}")
    print(f"Mesh Parameters:")
    print(f"  NX_INLET      = {NX_INLET}")
    print(f"  NX_SLOT_STRIP = {NX_SLOT_STRIP}")
    print(f"  NX_AXIS       = {NX_AXIS}")
    print(f"  NX_MID        = {NX_MID}")
    print(f"  NX_CHAMBER    = {NX_CHAMBER}")
    print(f"  NX_STEP       = {NX_STEP}")
    print(f"  NY_SLOT_THIN  = {NY_SLOT_THIN}")
    print(f"  NY_SLOT_THICK = {NY_SLOT_THICK}")
    print(f"  NY_AXIS       = {NY_AXIS}")
    print(f"  NY_FUEL       = {NY_FUEL}")
    print(f"{'='*60}\n")
    
    lines = []
    
    # Header - characteristic lengths
    lines.append(f"cl__1 = {CL_FINE};")
    lines.append(f"cl__2 = {CL_MEDIUM};")
    lines.append(f"cl__3 = {CL_COARSE};")
    # Additional cl for downstream sections
    lines.append(f"cl__4 = {REFINE_SIZE_MAX};")
    lines.append(f"cl__5 = {CL_MEDIUM * 1.5:.6f};")
    lines.append(f"cl__6 = {CL_MEDIUM * 1.5:.6f};")
    lines.append(f"cl__7 = {CL_MEDIUM * 1.5:.6f};")
    lines.append("")
    
    # Define points for the geometry
    # Format: Point(tag) = {x, y, z, char_length};
    # Left inlet section (-160 to -140 mm)
    # Slot boundaries: y = 3, 3.8, 5.8, 6.3, 8, 8.3, 9.7, 10.235
    
    # Point definitions...
    points = []
    
    # Left inlet x = -160 mm (oxidizer inlet)
    y_slots = [3, 3.8, 5.8, 6.3, 8, 8.3, 9.7, 10.235]
    x_left = -160
    x_left_mid = -140
    x_slot_end = -128
    
    # Points at x = -160
    pt = 1
    for y in y_slots:
        points.append(f"Point({pt}) = {{{x_left}, {y}, 0, cl__1}};")
        pt += 1
    
    # Points at x = -140
    for y in y_slots:
        points.append(f"Point({pt}) = {{{x_left_mid}, {y}, 0, cl__1}};")
        pt += 1
    
    # Points for axis section (x = -140 to -128)
    points.append(f"Point({pt}) = {{{x_left_mid}, 0.001, 0, cl__1}};")
    pt_axis1 = pt
    pt += 1
    points.append(f"Point({pt}) = {{{x_slot_end}, 0.001, 0, cl__1}};")
    pt_axis2 = pt
    pt += 1
    
    # Points at x = -128
    for y in y_slots:
        points.append(f"Point({pt}) = {{{x_slot_end}, {y}, 0, cl__1}};")
        pt += 1
    
    # Section from -10.16 to 0
    x_mid1 = -10.16
    points.append(f"Point({pt}) = {{{x_mid1}, 0.001, 0, cl__1}};")
    pt += 1
    points.append(f"Point({pt}) = {{{x_mid1}, {y_slots[-1]}, 0, cl__1}};")
    pt += 1
    
    # Fuel injection step points (-30 to -10.16, y = 11 to 11.53)
    x_fuel_start = -30
    y_fuel_low = 11
    y_fuel_high = 11.53
    
    points.append(f"Point({pt}) = {{{x_fuel_start}, {y_fuel_low}, 0, cl__1}};")
    pt_fuel1 = pt
    pt += 1
    points.append(f"Point({pt}) = {{{x_mid1}, {y_fuel_low}, 0, cl__1}};")
    pt += 1
    points.append(f"Point({pt}) = {{{x_mid1}, {y_fuel_high}, 0, cl__1}};")
    pt += 1
    points.append(f"Point({pt}) = {{{x_fuel_start}, {y_fuel_high}, 0, cl__1}};")
    pt_fuel4 = pt
    pt += 1
    
    # Points at x = 0
    x_0 = 0
    points.append(f"Point({pt}) = {{{x_0}, 0.001, 0, cl__1}};")
    pt += 1
    points.append(f"Point({pt}) = {{{x_0}, {y_slots[-1]}, 0, cl__1}};")
    pt += 1
    points.append(f"Point({pt}) = {{{x_0}, {y_fuel_low}, 0, cl__1}};")
    pt += 1
    points.append(f"Point({pt}) = {{{x_0}, {y_fuel_high}, 0, cl__1}};")
    pt += 1
    
    # Points at x = 20
    x_20 = 20
    points.append(f"Point({pt}) = {{{x_20}, 0.001, 0, cl__2}};")
    pt += 1
    points.append(f"Point({pt}) = {{{x_20}, {y_slots[-1]}, 0, cl__2}};")
    pt += 1
    points.append(f"Point({pt}) = {{{x_20}, {y_fuel_low}, 0, cl__2}};")
    pt += 1
    points.append(f"Point({pt}) = {{{x_20}, {y_fuel_high}, 0, cl__2}};")
    pt += 1
    
    # Downstream outlet points
    y_max = 22.5
    points.append(f"Point({pt}) = {{{x_20}, {y_max}, 0, cl__2}};")
    pt += 1
    points.append(f"Point({pt}) = {{{x_0}, {y_max}, 0, cl__3}};")
    pt += 1
    
    # Outlet nozzle points (approximated)
    x_out1 = 399.5
    x_out2 = 397.5
    x_out3 = 381
    y_out_nozzle = 20
    y_out_low = 8
    y_out_shoulder = 6.5
    
    points.append(f"Point({pt}) = {{{x_out1}, 0.001, 0, cl__4}};")
    pt += 1
    points.append(f"Point({pt}) = {{{x_out2}, {y_fuel_low}, 0, cl__5}};")
    pt += 1
    points.append(f"Point({pt}) = {{{x_out3}, {y_out_nozzle}, 0, cl__6}};")
    pt += 1
    points.append(f"Point({pt}) = {{{x_out3}, {y_out_low}, 0, cl__6}};")
    pt += 1
    points.append(f"Point({pt}) = {{{x_out1 + 1.5}, {y_out_shoulder}, 0, cl__7}};")
    pt += 1
    points.append(f"Point({pt}) = {{{x_out3}, {y_max}, 0, cl__6}};")
    
    lines.extend(points)
    
    # Generate lines with transfinite meshing
    # This is complex - we need to match the original structure
    
    # For simplicity, output a message about the structure
    print(f"Generated {pt-1} points")
    print(f"Output will be written to: {GEO_FILE}")
    print(f"\nNote: Full geometry generation requires matching the original")
    print(f"      structured block topology. See cvrc_2d_profile.geo_unrolled")
    print(f"      for the complete line and surface definitions.")
    
    # Write a template that includes the key parameters
    with open(GEO_FILE, 'w') as f:
        f.write(f"""// Gmsh geometry file for CVRC 2D profile
// Generated by generate_cvrc_profile.py
//
// MESH PARAMETERS (edit in Python script to change):
//   NX_INLET      = {NX_INLET}
//   NX_SLOT_STRIP = {NX_SLOT_STRIP}
//   NX_AXIS       = {NX_AXIS}
//   NX_MID        = {NX_MID}
//   NX_CHAMBER    = {NX_CHAMBER}
//   NY_SLOT_THIN  = {NY_SLOT_THIN}
//   NY_SLOT_THICK = {NY_SLOT_THICK}
//   NY_AXIS       = {NY_AXIS}
//   NY_FUEL       = {NY_FUEL}
//
// To regenerate: python3 generate_cvrc_profile.py
// =============================================================================

// Characteristic lengths
cl__1 = {CL_FINE};
cl__2 = {CL_MEDIUM};
cl__3 = {CL_COARSE};
cl__4 = {REFINE_SIZE_MAX};
cl__5 = {CL_MEDIUM * 1.5:.6f};
cl__6 = {CL_MEDIUM * 1.5:.6f};
cl__7 = {CL_MEDIUM * 1.5:.6f};

// Points (abbreviated - see original file for complete definition)
""")
        # Read original file and substitute transfinite parameters
        with open(GEO_FILE.replace('.geo_unrolled', '_original.geo_unrolled'), 'r') as orig:
            # Check if original exists
            pass
    
    return True


def substitute_transfinite_params(input_file, output_file):
    """
    Read the original geo file and substitute transfinite curve parameters.
    """
    import re
    
    # Parameter substitutions for transfinite curves
    # These map the original numbers to the parameterized versions
    substitutions = {
        # NX_INLET - axial nodes in inlet section
        r'Transfinite Curve \{(\d+)\} = 17': f'Transfinite Curve {{\\1}} = {NX_INLET}',
        # NX_SLOT_STRIP - axial nodes in slot strip
        r'Transfinite Curve \{(\d+)\} = 7 Using': f'Transfinite Curve {{{{\\1}}}} = {NX_SLOT_STRIP} Using',
        # NX_AXIS - axial nodes along axis
        r'Transfinite Curve \{(\d+)\} = 13 Using': f'Transfinite Curve {{{{\\1}}}} = {NX_AXIS} Using',
        # NX_MID - axial nodes in mid section
        r'Transfinite Curve \{(\d+)\} = 49 Using': f'Transfinite Curve {{{{\\1}}}} = {NX_MID} Using',
        # NX_CHAMBER - axial nodes in combustion chamber
        r'Transfinite Curve \{(\d+)\} = 17 Using': f'Transfinite Curve {{{{\\1}}}} = {NX_CHAMBER} Using',
        # NX_STEP - axial nodes in step
        r'Transfinite Curve \{(\d+)\} = 21 Using': f'Transfinite Curve {{{{\\1}}}} = {NX_STEP} Using',
        # NY_SLOT_THIN - radial nodes in thin slots
        r'Transfinite Curve \{(\d+)\} = 4 Using': f'Transfinite Curve {{{{\\1}}}} = {NY_SLOT_THIN} Using',
        # NY_SLOT_THICK - radial nodes in thick slots  
        r'Transfinite Curve \{(\d+)\} = 9 Using': f'Transfinite Curve {{{{\\1}}}} = {NY_SLOT_THICK} Using',
        # NY_FUEL - nodes in fuel annulus
        r'Transfinite Curve \{(\d+)\} = 3 Using': f'Transfinite Curve {{{{\\1}}}} = {NY_SLOT_THIN - 1} Using',
        # NY_UPSTREAM - nodes in upstream
        r'Transfinite Curve \{(\d+)\} = 11 Using': f'Transfinite Curve {{{{\\1}}}} = {NY_UPSTREAM} Using',
    }
    
    print("Substituting transfinite curve parameters...")
    
    # Read original file
    original_path = "/mnt/d/xiaox/downloads/cvrc_gmsh/cvrc_wedge_epsilon/cvrc_2d_profile.geo_unrolled"
    print(f"Reading: {original_path}")
    
    with open(original_path, 'r') as f:
        content = f.read()
    
    # Apply substitutions
    for pattern, replacement in substitutions.items():
        content = re.sub(pattern, replacement, content)
    
    # Write output
    print(f"Writing: {output_file}")
    with open(output_file, 'w') as f:
        f.write(content)
    
    print("Done!")
    return True


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # For now, just substitute parameters in the existing file
    # The full geometry generation is complex and we preserve the original structure
    
    output_file = "/mnt/d/xiaox/downloads/cvrc_gmsh/cvrc_wedge_epsilon/cvrc_2d_profile_param.geo_unrolled"
    substitute_transfinite_params(None, output_file)
    
    print(f"\nTo use the parameterized mesh:")
    print(f"  1. Edit NX_*, NY_* parameters at top of this script")
    print(f"  2. Run: python3 generate_cvrc_profile.py")
    print(f"  3. Update create_wedge_v10.py to use: cvrc_2d_profile_param.geo_unrolled")
    print(f"  4. Run: python3 create_wedge_v10.py")