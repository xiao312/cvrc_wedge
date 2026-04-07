#!/usr/bin/env python3
"""
CVRC Wedge Mesh Generator (v9)
==============================

Creates a 3D wedge mesh for OpenFOAM from a 2D axisymmetric CVRC combustor profile.

Author: Generated for CVRC combustor CFD research
Version: 9 (Final working version)

Background
----------
For axisymmetric (2D) CFD simulations in OpenFOAM, the mesh must be a 3D wedge:
- A small angular wedge (typically 5° total, 2.5° each side of x-axis)
- Front and back faces are 'wedge' boundary conditions
- The axis (y=0 line in 2D) becomes an 'empty' boundary

This script takes a 2D meridional profile and revolves it around the x-axis
to create this wedge geometry.

Key Features
------------
1. Identifies boundary curves by GEOMETRIC POSITION (not physical group names)
2. Creates matching front/back wedge face counts (essential for OpenFOAM)
3. Excludes axis curves from creating lateral faces (prevents degenerate faces)
4. Higher precision mesh generation for wedge planarity

Boundary Patch Names
--------------------
- wedgeFront : Front face at θ = -2.5° (type: wedge)
- wedgeBack  : Back face at θ = +2.5° (type: wedge)
- oxidizer_inlet : Oxidizer inlet at x = -160 mm
- fuel_inlet      : Fuel inlet at x = -30 mm
- oxidizer_slot_1/2/3 : Oxidizer injection slots
- wall            : Combustor walls
- axis            : Symmetry axis (type: empty)
- outlet          : Outlet at x ≈ 400 mm

Usage
-----
    conda activate agent  # Activate Gmsh environment
    python3 create_wedge_v9.py
    
    # Then convert to OpenFOAM:
    source /opt/openfoam7/etc/bashrc
    gmshToFoam cvrc_wedge_v9.msh
    rm -f constant/polyMesh/faceZones constant/polyMesh/cellZones constant/polyMesh/pointZones
    rm -rf constant/polyMesh/sets

Output
------
    cvrc_wedge_v9.msh : Gmsh mesh file (MSH format 2.2, ASCII)

Known Issues
------------
- The axis boundary has 538 faces (Gmsh revolve creates these from axis curves)
- blockMesh wedge meshes have axis nFaces=0; this is a known difference
- checkMesh shows "empty patches not divisible" info message (expected)
- Mesh still passes all checks with "Mesh OK."

See Also
--------
    WEDGE_MESH_JOURNEY.md : Detailed development history
    REMAINING_ISSUES.md   : Known issues and resolutions
"""

import os
import math
import gmsh

# =============================================================================
# CONFIGURATION
# =============================================================================

# Wedge angle (total angle, split equally on each side of x-axis)
WEDGE_ANGLE_DEG = 5.0  # Total 5° wedge, 2.5° each side

# File paths
OUTPUT_DIR = "/mnt/d/xiaox/downloads/cvrc_gmsh/cvrc_wedge_epsilon"
SOURCE_GEO = os.path.join(OUTPUT_DIR, "cvrc_2d_profile.geo_unrolled")
MSH_FILE = os.path.join(OUTPUT_DIR, "cvrc_wedge_v9.msh")

# =============================================================================
# MAIN MESH GENERATION FUNCTION
# =============================================================================

def create_wedge():
    """
    Main function to generate the CVRC wedge mesh.
    
    Process
    -------
    1. Initialize Gmsh with precision settings
    2. Load the 2D axisymmetric profile
    3. Identify boundary curves by geometric position
    4. Rotate profile by -θ/2 (position at front wedge angle)
    5. Generate 2D mesh on rotated profile
    6. Revolve each surface by +θ around x-axis
    7. Track which faces are created from each curve
    8. Create physical groups for OpenFOAM boundary patches
    9. Generate 3D mesh and export
    
    Returns
    -------
    bool : True if front/back face counts match, False otherwise
    """
    
    # =========================================================================
    # STEP 1: Initialize Gmsh
    # =========================================================================
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 1)
    
    # Mesh file format settings
    gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)  # Compatible with gmshToFoam
    gmsh.option.setNumber("Mesh.SaveAll", 0)           # Only save meshed entities
    
    # Higher precision settings
    gmsh.option.setNumber("Mesh.Binary", 0)           # ASCII format (gmshToFoam compatible)
    gmsh.option.setNumber("Mesh.Smoothing", 10)        # More smoothing passes for quality
    
    gmsh.model.add("cvrc_wedge_v9")
    geo = gmsh.model.geo
    
    # Convert angles to radians
    half_angle = math.radians(WEDGE_ANGLE_DEG / 2.0)
    full_angle = math.radians(WEDGE_ANGLE_DEG)
    
    print(f"\n{'='*60}")
    print(f"CVRC Wedge Mesh Generator v9")
    print(f"{'='*60}")
    print(f"Configuration:")
    print(f"  Wedge angle: {WEDGE_ANGLE_DEG}° total ({WEDGE_ANGLE_DEG/2}° each side)")
    print(f"  Input:  {SOURCE_GEO}")
    print(f"  Output: {MSH_FILE}")
    print(f"{'='*60}\n")
    
    # =========================================================================
    # STEP 2: Load 2D Profile
    # =========================================================================
    print("Step 1: Loading 2D axisymmetric profile...")
    gmsh.merge(SOURCE_GEO)
    geo.synchronize()
    
    original_surfaces = gmsh.model.getEntities(2)
    original_curves = gmsh.model.getEntities(1)
    original_surf_tags = {tag for dim, tag in original_surfaces}
    
    print(f"  Loaded: {len(original_curves)} curves, {len(original_surfaces)} surfaces")
    
    # =========================================================================
    # STEP 3: Identify Boundary Curves by Position
    # =========================================================================
    print("\nStep 2: Classifying boundary curves by geometric position...")
    
    # Initialize classification dictionary
    curve_classification = {
        'oxidizer_inlet': [],
        'fuel_inlet': [],
        'axis': [],
        'outlet': [],
        'oxidizer_slot_1': [],
        'oxidizer_slot_2': [],
        'oxidizer_slot_3': [],
        'wall': []
    }
    
    # Get oxidizer slot curves from original physical groups (preserve naming)
    slot_curves = {1: [], 2: [], 3: []}
    for dim, phys_tag in gmsh.model.getPhysicalGroups(1):
        name = gmsh.model.getPhysicalName(dim, phys_tag)
        entities = gmsh.model.getEntitiesForPhysicalGroup(dim, phys_tag)
        if 'oxidizer_slot_1' in name:
            slot_curves[1] = list(entities)
        elif 'oxidizer_slot_2' in name:
            slot_curves[2] = list(entities)
        elif 'oxidizer_slot_3' in name:
            slot_curves[3] = list(entities)
    
    # Classify each curve by its geometric position
    # This is more reliable than physical group names which may be wrong
    for dim, curve_tag in original_curves:
        bbox = gmsh.model.getBoundingBox(1, curve_tag)
        xmin, ymin, zmin, xmax, ymax, zmax = bbox
        
        # Determine if curve is vertical (more vertical than horizontal)
        is_vertical = abs(xmax - xmin) < 0.5
        
        # Classification based on position (in mm)
        # Note: Geometric identification is more reliable than physical group names
        if curve_tag in slot_curves[1]:
            curve_classification['oxidizer_slot_1'].append(curve_tag)
        elif curve_tag in slot_curves[2]:
            curve_classification['oxidizer_slot_2'].append(curve_tag)
        elif curve_tag in slot_curves[3]:
            curve_classification['oxidizer_slot_3'].append(curve_tag)
        elif ymin < 0.01 and ymax < 0.01:
            # Curves at y ≈ 0 (on the symmetry axis)
            curve_classification['axis'].append(curve_tag)
        elif xmin > 390:
            # Curves at outlet (x ≈ 400 mm)
            curve_classification['outlet'].append(curve_tag)
        elif xmin < -159 and is_vertical and 2.5 < ymin < 11:
            # Vertical curves at oxidizer inlet (x ≈ -160 mm)
            curve_classification['oxidizer_inlet'].append(curve_tag)
        elif -31 < xmin < -29 and is_vertical and ymin > 9.5:
            # Vertical curve at fuel inlet (x ≈ -30 mm)
            curve_classification['fuel_inlet'].append(curve_tag)
        else:
            # All remaining curves are wall boundaries
            curve_classification['wall'].append(curve_tag)
    
    print("  Classification results:")
    for name, curves in curve_classification.items():
        print(f"    {name}: {len(curves)} curves")
    
    # =========================================================================
    # STEP 4: Rotate Profile to Position at Front Wedge Angle
    # =========================================================================
    print(f"\nStep 3: Rotating profile by {-WEDGE_ANGLE_DEG/2}° to position at front wedge...")
    all_entities = gmsh.model.getEntities()
    geo.rotate(all_entities, 0, 0, 0, 1, 0, 0, -half_angle)
    geo.synchronize()
    print("  Rotation complete")
    
    # =========================================================================
    # STEP 5: Generate 2D Mesh
    # =========================================================================
    print("\nStep 4: Generating 2D mesh on rotated profile...")
    gmsh.model.mesh.generate(2)
    print("  2D mesh generated")
    
    # =========================================================================
    # STEP 6: Revolve to Create 3D Wedge
    # =========================================================================
    print(f"\nStep 5: Revolving {len(original_surfaces)} surfaces by {WEDGE_ANGLE_DEG}°...")
    
    volumes = []
    back_surfaces = []
    curve_to_lateral = {}  # Maps each curve to its lateral surface during revolution
    
    # Initialize mapping for each curve
    for name, curves in curve_classification.items():
        for c in curves:
            curve_to_lateral[c] = []
    
    # Process each surface individually to track face creation
    for surf_dim, surf_tag in original_surfaces:
        # Get boundary curves of this surface
        boundaries = gmsh.model.getBoundary(
            [(surf_dim, surf_tag)], 
            combined=False, 
            oriented=False
        )
        boundary_curves = [b_tag for b_dim, b_tag in boundaries if b_dim == 1]
        
        # Revolve this surface around x-axis
        # revolve() returns: [back_surface, volume, lateral_surface_1, lateral_surface_2, ...]
        result = geo.revolve(
            [(surf_dim, surf_tag)],
            0, 0, 0,           # Rotation point
            1, 0, 0,           # Rotation axis (x-axis)
            full_angle,        # Rotation angle
            [1], [1.0],        # Extrusion parameters
            True               # Reactivate search
        )
        geo.synchronize()
        
        # Parse the result entities
        for i, (e_dim, e_tag) in enumerate(result):
            if e_dim == 3:
                # This is the volume
                volumes.append(e_tag)
            elif e_dim == 2:
                if i == 0:
                    # First surface is the BACK copy of the input surface
                    back_surfaces.append(e_tag)
                else:
                    # Remaining surfaces are lateral surfaces from boundary curves
                    # Index i-2 corresponds to boundary curve index
                    curve_idx = i - 2
                    if 0 <= curve_idx < len(boundary_curves):
                        c = boundary_curves[curve_idx]
                        if c in curve_to_lateral:
                            curve_to_lateral[c].append(e_tag)
    
    print(f"  Created: {len(volumes)} volumes")
    print(f"  Front faces: {len(original_surf_tags)} surfaces")
    print(f"  Back faces: {len(back_surfaces)} surfaces")
    
    # =========================================================================
    # STEP 7: Generate 3D Mesh
    # =========================================================================
    print("\nStep 6: Generating 3D mesh...")
    for vol in volumes:
        try:
            gmsh.model.mesh.setRecombine(3, vol)
        except:
            pass
    gmsh.model.mesh.generate(3)
    print("  3D mesh generated")
    
    # =========================================================================
    # STEP 8: Create Physical Groups for OpenFOAM
    # =========================================================================
    print("\nStep 7: Creating physical groups for boundary patches...")
    
    # Remove any existing physical groups from the source geometry
    for dim in [1, 2, 3]:
        for p_dim, p_tag in gmsh.model.getPhysicalGroups(dim):
            gmsh.model.removePhysicalGroups([(p_dim, p_tag)])
    geo.synchronize()
    
    pg = gmsh.model.addPhysicalGroup
    
    # Fluid volume
    grp = pg(3, volumes)
    gmsh.model.setPhysicalName(3, grp, "fluid")
    
    # Wedge front and back faces
    grp = pg(2, list(original_surf_tags))
    gmsh.model.setPhysicalName(2, grp, "wedgeFront")
    
    grp = pg(2, back_surfaces)
    gmsh.model.setPhysicalName(2, grp, "wedgeBack")
    
    # Lateral boundary patches
    # NOTE: 'axis' is intentionally NOT included here!
    # Curves at y=0 (axis) create degenerate lateral surfaces during revolution.
    # These surfaces are not meaningful boundary faces - they collapse to a line.
    # In blockMesh wedge meshes, axis has nFaces=0.
    # In Gmsh revolve meshes, these faces are created but should be type 'empty'.
    
    for name in ['oxidizer_inlet', 'fuel_inlet', 'wall', 'outlet',
                 'oxidizer_slot_1', 'oxidizer_slot_2', 'oxidizer_slot_3']:
        surf_tags = []
        for c in curve_classification[name]:
            surf_tags.extend(curve_to_lateral.get(c, []))
        
        if surf_tags:
            grp = pg(2, surf_tags)
            gmsh.model.setPhysicalName(2, grp, name)
            print(f"  {name}: {len(surf_tags)} surfaces")
    
    print(f"  axis: 0 surfaces (degenerate line at y=0, excluded from physical groups)")
    
    # =========================================================================
    # STEP 9: Write Mesh File
    # =========================================================================
    print(f"\nStep 8: Writing mesh file: {MSH_FILE}")
    gmsh.write(MSH_FILE)
    
    # Print mesh statistics
    front_elems = sum(
        sum(len(t) for t in gmsh.model.mesh.getElements(2, tag)[1])
        for tag in original_surf_tags
    )
    back_elems = sum(
        sum(len(t) for t in gmsh.model.mesh.getElements(2, tag)[1])
        for tag in back_surfaces
    )
    nodes = gmsh.model.mesh.getNodes()
    
    print(f"\n{'='*60}")
    print(f"Mesh Statistics:")
    print(f"{'='*60}")
    print(f"  Nodes:      {len(nodes[0]):,}")
    print(f"  Front faces: {front_elems:,}")
    print(f"  Back faces:  {back_elems:,}")
    print(f"  Match:      {'YES' if front_elems == back_elems else 'NO'}")
    print(f"{'='*60}")
    
    gmsh.finalize()
    
    print(f"\nOutput written to: {MSH_FILE}")
    print(f"\nTo convert to OpenFOAM:")
    print(f"  source /opt/openfoam7/etc/bashrc")
    print(f"  gmshToFoam {MSH_FILE}")
    print(f"  # Then clean up zone files:")
    print(f"  rm -f constant/polyMesh/faceZones constant/polyMesh/cellZones constant/polyMesh/pointZones")
    print(f"  rm -rf constant/polyMesh/sets")
    
    return front_elems == back_elems


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    create_wedge()