import bpy
import bmesh

from pathlib import Path
from datetime import datetime

def retreive_obj_tag(tag=''):
    return [obj for obj in bpy.context.scene.objects if tag in obj.name]

def select_object(obj, edit_mode=False):
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    if edit_mode:
        bpy.ops.object.mode_set(mode='EDIT')

def separate_object_by_parts(obj):
    # select the object to focus on
    select_object(obj, edit_mode=True)

    me = obj.data
    bm = bmesh.from_edit_mesh(me)

    # old seams
    old_seams = [e for e in bm.edges if e.seam]
    # unmark
    for e in old_seams:
        e.seam = False
        
    # mark seams from uv islands
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.seams_from_islands()
    seams = [e for e in bm.edges if e.seam]

    # split on seams
    bmesh.ops.split_edges(bm, edges=seams)
    bpy.ops.mesh.separate(type='LOOSE')
    
    print('Separation successful')
    
    bpy.ops.object.mode_set(mode='OBJECT')  # recover the mode
    return retreive_obj_tag(obj.name)

def mark_edges_to_render(objects):
    for obj in objects:
        print(obj.name)

        select_object(obj, edit_mode=True)
        
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.region_to_loop()  # boundary of our mesh subsection
        
        bpy.ops.mesh.mark_freestyle_edge(clear=False)
        
        
    bpy.ops.object.mode_set(mode='OBJECT')  # recover the mode    
    bpy.ops.object.select_all(action='DESELECT')
    print('Marking edges successful')

def render(path):
    filename = 'blender_render_' + datetime.now().strftime("%y%m%d-%H-%M-%S")
    
    cameras = [ob for ob in bpy.context.scene.objects if ob.type == 'CAMERA']
    print(cameras)

    # Save image
    for cam in cameras:
        bpy.context.scene.camera = cam  #https://tuxpool.blogspot.com/2020/02/how-to-set-active-camera-when-blender.html

        # https://stackoverflow.com/questions/14982836/rendering-and-saving-images-through-blender-python
        bpy.context.scene.render.filepath = str(path / (filename + f'_{cam.name}.png'))
        bpy.ops.render.render(write_still = True)


# TODO for multiple garments at once?
# ---- Preparation ---- 

# Body and garment scaling
garment = retreive_obj_tag('sim')[0]  # single one

# Prepare garment for rendering
# Separate by loose parts
garment_parts = separate_object_by_parts(garment)

# Mark US seams as freestyle edge marks 
mark_edges_to_render(garment_parts)

# ---- Colors -----
# Get the shader
    
# Define color list

# Go over UV shells and colors
    # Copy shader into a new one
    # Setup new color
    # Select all faces in the UV shell
    # assign the shader 

# ----- Rendering -----
# Run render for each camera in the scene
path = Path(r'C:\Users\MariaKo\Documents\Docs\GarmentCode SA23\Blender tries')
render(path)

# And wait.. =)
