#!/usr/bin/env python3
"""
CVRC Wedge Mesh Generator (v10)
================================

Creates a 3D wedge mesh for OpenFOAM from a 2D axisymmetric CVRC combustor profile.

Author: Generated for CVRC combustor CFD research
Version: 10 (Parameterized mesh control)

Background
----------
For axisymmetric (2D) CFD simulations in OpenFOAM, the mesh must be a 3D wedge:
- A small angular wedge (typically 5° total, 2.5° each side of x-axis)
- Front and back faces are 'wedge' boundary conditions
- The axis (y=0 line in 2D) becomes an 'empty' boundary

This script takes a 2D meridional profile and revolves it around the x-axis
to create this wedge geometry.

Mesh Size Control
-----------------
The mesh density is controlled by MESH_SIZE_FACTOR:
- 1.0 = default (coarse)
- 0.5 = medium (2x more cells)
- 0.25 = fine (4x more cells)
- 0.1 = very fine (10x more cells)

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
    python3 create_wedge_v10.py
    
    # Then convert to OpenFOAM:
    source /opt/openfoam7/etc/bashrc
    gmshToFoam cvrc_wedge_v10.msh
    rm -f constant/polyMesh/faceZones constant/polyMesh/cellZones constant/polyMesh/pointZones
    rm -rf constant/polyMesh/sets
    transformPoints -scale "(0.001 0.001 0.001)"
"""

import os
import math
import gmsh

# =============================================================================
# MESH CONTROL PARAMETERS (EDIT THESE TO CHANGE MESH DENSITY)
# =============================================================================

# Mesh density control
# MESH_SIZE_FACTOR: Multiplier for all mesh sizes
#   - 1.0  = coarse (default, ~16k cells)
#   - 0.5  = medium (~32k cells)
#   - 0.25 = fine (~64k cells)
#   - 0.1  = very fine (~160k cells)
MESH_SIZE_FACTOR = 1.0

# Minimum and maximum element sizes (in mm, will be scaled by MESH_SIZE_FACTOR)
# These should match the characteristic length scale of your geometry
MESH_SIZE_MIN = 0.1    # mm (prevents too small elements)
MESH_SIZE_MAX = 10.0   # mm (limits largest element size)

# Wedge angle (total angle, split equally on each side of x-axis)
WEDGE_ANGLE_DEG = 5.0  # Total 5° wedge, 2.5° each side

# Mesh quality settings
MESH_SMOOTHING_PASSES = 10    # Number of smoothing iterations
MESH_OPTIMIZER_PASSES = 1     # Number of optimization passes
MESH_RECOMBINE_3D = True      # Recombine 3D mesh (creates hexahedra)

# =============================================================================
# FILE PATHS
# =============================================================================

OUTPUT_DIR = "/mnt/d/xiaox/downloads/cvrc_gmsh/cvrc_wedge_epsilon"
SOURCE_GEO = os.path.join(OUTPUT_DIR, "cvrc_2d_profile.geo_unrolled")
MSH_FILE = os.path.join(OUTPUT_DIR, "cvrc_wedge_v10.msh")

# =============================================================================
# MESH GENERATION FUNCTION
# =============================================================================

def create_wedge():
    """
    Main function to generate the CVRC wedge mesh.
    
    Returns
    -------
    bool : True if front/back face counts match, False otherwise
    """
    
    # Validate parameters
    if MESH_SIZE_FACTOR <= 0:
        raise ValueError(f"MESH_SIZE_FACTOR must be positive, got {MESH_SIZE_FACTOR}")
    
    print(f"\n{'='*70}")
    print(f"CVRC Wedge Mesh Generator v10")
    print(f"{'='*70}")
    print(f"Mesh Parameters:")
    print(f"  MESH_SIZE_FACTOR      = {MESH_SIZE_FACTOR}")
    print(f"  MESH_SIZE_MIN         = {MESH_SIZE_MIN} mm")
    print(f"  MESH_SIZE_MAX         = {MESH_SIZE_MAX} mm")
    print(f"  WEDGE_ANGLE_DEG       = {WEDGE_ANGLE_DEG}°")
    print(f"  MESH_SMOOTHING_PASSES = {MESH_SMOOTHING_PASSES}")
    print(f"  MESH_RECOMBINE_3D     = {MESH_RECOMBINE_3D}")
    print(f"  Input:  {SOURCE_GEO}")
    print(f"  Output: {MSH_FILE}")
    print(f"{'='*70}\n")
    
    # =========================================================================
    # STEP 1: Initialize Gmsh
    # =========================================================================
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 1)
    
    # Mesh file format settings
    gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)  # Compatible with gmshToFoam
    gmsh.option.setNumber("Mesh.SaveAll", 0)            # Only save meshed entities
    gmsh.option.setNumber("Mesh.Binary", 0)             # ASCII format
    
    # Apply global mesh size control
    # These settings control the characteristic length used by Gmsh
    base_size_min = MESH_SIZE_MIN * MESH_SIZE_FACTOR
    base_size_max = MESH_SIZE_MAX * MESH_SIZE_FACTOR
    
    gmsh.option.setNumber("Mesh.MeshSizeMin", base_size_min)
    gmsh.option.setNumber("Mesh.MeshSizeMax", base_size_max)
    gmsh.option.setNumber("Mesh.MeshSizeFactor", MESH_SIZE_FACTOR)
    
    # Mesh quality settings
    gmsh.option.setNumber("Mesh.Smoothing", MESH_SMOOTHING_PASSES)
    gmsh.option.setNumber("Mesh.Optimize", MESH_OPTIMIZER_PASSES)
    
    print(f"Applied mesh size settings:")
    print(f"  Mesh.MeshSizeMin    = {base_size_min:.4f} mm")
    print(f"  Mesh.MeshSizeMax    = {base_size_max:.4f} mm")
    print(f"  Mesh.MeshSizeFactor = {MESH_SIZE_FACTOR}")
    
    gmsh.model.add("cvrc_wedge_v10")
    geo = gmsh.model.geo
    
    # Convert angles to radians
    half_angle = math.radians(WEDGE_ANGLE_DEG / 2.0)
    full_angle = math.radians(WEDGE_ANGLE_DEG)
    
    # =========================================================================
    # STEP 2: Load 2D Profile
    # =========================================================================
    print("\nStep 1: Loading 2D axisymmetric profile...")
    gmsh.merge(SOURCE_GEO)
    geo.synchronize()
    
    original_surfaces = gmsh.model.getEntities(2)
    original_curves = gmsh.model.getEntities(1)
    original_surf_tags = {tag for dim, tag in original_surfaces}
    
    print(f"  Loaded: {len(original_curves)} curves, {len(original_surfaces)} surfaces")
    
    # Get all points and apply mesh size
    points = gmsh.model.getEntities(0)
    print(f"  Points: {len(points)}")
    
    # =========================================================================
    # STEP 3: Apply Mesh Size to Points
    # =========================================================================
    print("\nStep 2: Applying mesh size to geometry...")
    
    # Get all point coordinates and apply mesh size
    for dim, pt_tag in points:
        # Apply the mesh size to each point
        # This overrides any embedded mesh sizes in the geometry
        gmsh.model.mesh.setSize([(dim, pt_tag)], MESH_SIZE_FACTOR)
    
    # Also set mesh size for all curves
    for dim, curve_tag in original_curves:
        gmsh.model.mesh.setSize([(dim, curve_tag)], MESH_SIZE_FACTOR)
    
    print(f"  Applied mesh size factor {MESH_SIZE_FACTOR} to all geometry entities")
    
    # =========================================================================
    # STEP 4: Identify Boundary Curves by Position
    # =========================================================================
    print("\nStep 3: Classifying boundary curves by geometric position...")
    
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
    
    # Get oxidizer slot curves from original physical groups
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
    
    # Classify each curve by position
    for dim, curve_tag in original_curves:
        bbox = gmsh.model.getBoundingBox(1, curve_tag)
        xmin, ymin, zmin, xmax, ymax, zmax = bbox
        
        is_vertical = abs(xmax - xmin) < 0.5
        
        if curve_tag in slot_curves[1]:
            curve_classification['oxidizer_slot_1'].append(curve_tag)
        elif curve_tag in slot_curves[2]:
            curve_classification['oxidizer_slot_2'].append(curve_tag)
        elif curve_tag in slot_curves[3]:
            curve_classification['oxidizer_slot_3'].append(curve_tag)
        elif ymin < 0.01 and ymax < 0.01:
            curve_classification['axis'].append(curve_tag)
        elif xmin > 390:
            curve_classification['outlet'].append(curve_tag)
        elif xmin < -159 and is_vertical and 2.5 < ymin < 11:
            curve_classification['oxidizer_inlet'].append(curve_tag)
        elif -31 < xmin < -29 and is_vertical and ymin > 9.5:
            curve_classification['fuel_inlet'].append(curve_tag)
        else:
            curve_classification['wall'].append(curve_tag)
    
    print("  Classification results:")
    for name, curves in curve_classification.items():
        print(f"    {name}: {len(curves)} curves")
    
    # =========================================================================
    # STEP 5: Rotate Profile to Front Wedge Angle
    # =========================================================================
    print(f"\nStep 4: Rotating profile by {-WEDGE_ANGLE_DEG/2}°...")
    all_entities = gmsh.model.getEntities()
    geo.rotate(all_entities, 0, 0, 0, 1, 0, 0, -half_angle)
    geo.synchronize()
    print("  Rotation complete")
    
    # =========================================================================
    # STEP 6: Generate 2D Mesh
    # =========================================================================
    print("\nStep 5: Generating 2D mesh on rotated profile...")
    gmsh.model.mesh.generate(2)
    print("  2D mesh generated")
    
    # =========================================================================
    # STEP 7: Revolve to Create 3D Wedge
    # =========================================================================
    print(f"\nStep 6: Revolving {len(original_surfaces)} surfaces by {WEDGE_ANGLE_DEG}°...")
    
    volumes = []
    back_surfaces = []
    curve_to_lateral = {}
    
    for name, curves in curve_classification.items():
        for c in curves:
            curve_to_lateral[c] = []
    
    for surf_dim, surf_tag in original_surfaces:
        boundaries = gmsh.model.getBoundary(
            [(surf_dim, surf_tag)], 
            combined=False, 
            oriented=False
        )
        boundary_curves = [b_tag for b_dim, b_tag in boundaries if b_dim == 1]
        
        result = geo.revolve(
            [(surf_dim, surf_tag)],
            0, 0, 0,
            1, 0, 0,
            full_angle,
            [1], [1.0],
            True
        )
        geo.synchronize()
        
        for i, (e_dim, e_tag) in enumerate(result):
            if e_dim == 3:
                volumes.append(e_tag)
            elif e_dim == 2:
                if i == 0:
                    back_surfaces.append(e_tag)
                else:
                    curve_idx = i - 2
                    if 0 <= curve_idx < len(boundary_curves):
                        c = boundary_curves[curve_idx]
                        if c in curve_to_lateral:
                            curve_to_lateral[c].append(e_tag)
    
    print(f"  Created: {len(volumes)} volumes")
    print(f"  Front faces: {len(original_surf_tags)} surfaces")
    print(f"  Back faces: {len(back_surfaces)} surfaces")
    
    # =========================================================================
    # STEP 8: Generate 3D Mesh
    # =========================================================================
    print("\nStep 7: Generating 3D mesh...")
    
    if MESH_RECOMBINE_3D:
        for vol in volumes:
            try:
                gmsh.model.mesh.setRecombine(3, vol)
            except:
                pass
    
    gmsh.model.mesh.generate(3)
    
    # Additional smoothing for 3D mesh
    if MESH_SMOOTHING_PASSES > 0:
        gmsh.model.mesh.smooth()
    
    print("  3D mesh generated")
    
    # =========================================================================
    # STEP 9: Create Physical Groups
    # =========================================================================
    print("\nStep 8: Creating physical groups for boundary patches...")
    
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
    for name in ['oxidizer_inlet', 'fuel_inlet', 'wall', 'outlet',
                 'oxidizer_slot_1', 'oxidizer_slot_2', 'oxidizer_slot_3']:
        surf_tags = []
        for c in curve_classification[name]:
            surf_tags.extend(curve_to_lateral.get(c, []))
        
        if surf_tags:
            grp = pg(2, surf_tags)
            gmsh.model.setPhysicalName(2, grp, name)
            print(f"  {name}: {len(surf_tags)} surfaces")
    
    print(f"  axis: 0 surfaces (degenerate line at y=0)")
    
    # =========================================================================
    # STEP 10: Write Mesh File
    # =========================================================================
    print(f"\nStep 9: Writing mesh file: {MSH_FILE}")
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
    
    # Count cells by type
    elements = gmsh.model.mesh.getElements(3)
    total_cells = sum(len(elem_data) for elem_data in elements[1] if elem_data)
    
    print(f"\n{'='*70}")
    print(f"Mesh Statistics:")
    print(f"{'='*70}")
    print(f"  Nodes:       {len(nodes[0]):,}")
    print(f"  Cells:       {total_cells:,}")
    print(f"  Front faces:  {front_elems:,}")
    print(f"  Back faces:   {back_elems:,}")
    print(f"  Match:       {'YES' if front_elems == back_elems else 'NO'}")
    print(f"{'='*70}")
    
    gmsh.finalize()
    
    print(f"\nOutput written to: {MSH_FILE}")
    print(f"\nTo convert to OpenFOAM:")
    print(f"  source /opt/openfoam7/etc/bashrc")
    print(f"  gmshToFoam {MSH_FILE}")
    print(f"  rm -f constant/polyMesh/faceZones constant/polyMesh/cellZones constant/polyMesh/pointZones")
    print(f"  rm -rf constant/polyMesh/sets")
    print(f"  transformPoints -scale '(0.001 0.001 0.001)'")
    
    return front_elems == back_elems


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    create_wedge()