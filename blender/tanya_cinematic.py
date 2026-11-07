"""
Tanya Cinematic Garden — Blender scene generator
Run: Blender > Scripting > New > paste this file > Run Script.
Creates a short romantic 3D animation and configures MP4 rendering.
No external assets or add-ons required.
"""

import bpy
import math
import random
from mathutils import Vector

# ----------------------------- CONFIG ---------------------------------
FPS = 30
DURATION_SECONDS = 12
RESOLUTION = (1920, 1080)
OUTPUT_PATH = "//tanya_cinematic.mp4"
SEED = 17
random.seed(SEED)

# ----------------------------- RESET ----------------------------------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.materials, bpy.data.curves, bpy.data.meshes, bpy.data.cameras, bpy.data.lights):
    # Keep datablocks cleanup conservative; Blender removes unused datablocks on save.
    pass

scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = FPS * DURATION_SECONDS
scene.render.fps = FPS
scene.render.resolution_x, scene.render.resolution_y = RESOLUTION
scene.render.resolution_percentage = 100
# Blender 5.2.2 LTS uses the legacy EEVEE identifier.
# (BLENDER_EEVEE_NEXT is not available in this Blender build.)
scene.render.engine = "BLENDER_EEVEE"
scene.render.image_settings.file_format = 'FFMPEG'
scene.render.ffmpeg.format = 'MPEG4'
scene.render.ffmpeg.codec = 'H264'
scene.render.ffmpeg.constant_rate_factor = 'HIGH'
scene.render.filepath = OUTPUT_PATH
scene.render.image_settings.color_mode = 'RGB'
scene.render.film_transparent = False

# Color management
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.world.color = (0.012, 0.008, 0.035)

# ----------------------------- HELPERS --------------------------------
def material(name, color, metallic=0.0, roughness=0.45, emission=None, emission_strength=0.0):
    """Create a Principled material safely across Blender versions/localizations."""
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1.0)
    m.use_nodes = True

    # Do not rely on the node's display name: it can differ by Blender version
    # or language. Identify it by its stable Blender node type instead.
    nodes = m.node_tree.nodes
    bs = next((node for node in nodes if node.bl_idname == "ShaderNodeBsdfPrincipled"), None)
    if bs is None:
        bs = nodes.new("ShaderNodeBsdfPrincipled")

    output = next((node for node in nodes if node.bl_idname == "ShaderNodeOutputMaterial"), None)
    if output is None:
        output = nodes.new("ShaderNodeOutputMaterial")
    if not output.inputs["Surface"].is_linked:
        m.node_tree.links.new(bs.outputs["BSDF"], output.inputs["Surface"])

    # Socket names changed between Blender releases; guard every optional socket.
    for socket_name, value in (
        ("Base Color", (*color, 1.0)),
        ("Metallic", metallic),
        ("Roughness", roughness),
    ):
        socket = bs.inputs.get(socket_name)
        if socket is not None:
            socket.default_value = value

    if emission:
        emission_socket = bs.inputs.get("Emission Color") or bs.inputs.get("Emission")
        strength_socket = bs.inputs.get("Emission Strength")
        if emission_socket is not None:
            emission_socket.default_value = (*emission, 1.0)
        if strength_socket is not None:
            strength_socket.default_value = emission_strength

    return m

def apply_mat(obj, mat):
    obj.data.materials.append(mat)
    return obj

def smooth(obj):
    if obj.type == 'MESH':
        for p in obj.data.polygons:
            p.use_smooth = True
    return obj

def uv_sphere(name, loc, scale, mat, segments=24, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    apply_mat(obj, mat)
    smooth(obj)
    return obj

def cylinder(name, loc, radius, depth, mat, vertices=48):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc)
    obj = bpy.context.object
    obj.name = name
    apply_mat(obj, mat)
    bevel = obj.modifiers.new("Soft rounded edges", 'BEVEL')
    bevel.width = min(radius * 0.12, 0.12)
    bevel.segments = 3
    obj.modifiers.new("Weighted corner normals", 'WEIGHTED_NORMAL')
    return obj

def animate_rotation(obj, axis, angle, frame_a=1, frame_b=None):
    if frame_b is None:
        frame_b = scene.frame_end
    obj.rotation_euler[axis] = 0
    obj.keyframe_insert(data_path="rotation_euler", frame=frame_a)
    obj.rotation_euler[axis] = angle
    obj.keyframe_insert(data_path="rotation_euler", frame=frame_b)
    if obj.animation_data and obj.animation_data.action:
        for fc in obj.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'

# ----------------------------- MATERIALS ------------------------------
midnight = material("Midnight violet", (0.018, 0.012, 0.055), roughness=0.8)
island_mat = material("Velvet lavender stone", (0.12, 0.075, 0.20), roughness=0.82)
top_mat = material("Moss in moonlight", (0.035, 0.16, 0.12), roughness=0.9)
gold = material("Warm champagne gold", (0.8, 0.48, 0.16), metallic=0.72, roughness=0.25)
pink = material("Rose petal", (0.95, 0.22, 0.48), roughness=0.34, emission=(0.35, 0.025, 0.12), emission_strength=0.22)
pale = material("Blush petal", (1.0, 0.62, 0.76), roughness=0.3)
cream = material("Pearl petal", (1.0, 0.84, 0.67), roughness=0.32)
leaf = material("Deep emerald leaves", (0.025, 0.22, 0.12), roughness=0.58)
glow = material("Starlight", (0.55, 0.75, 1.0), roughness=0.22, emission=(0.35, 0.55, 1.0), emission_strength=3.0)

# ----------------------------- BACKDROP -------------------------------
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -4.2))
backdrop = bpy.context.object
backdrop.name = "Endless night"
apply_mat(backdrop, midnight)

# ----------------------------- FLOATING ISLAND -----------------------
island = cylinder("Floating island foundation", (0, 0, -0.2), 3.0, 1.0, island_mat, 96)
island.scale.z = 1.0
top = cylinder("Garden surface", (0, 0, 0.34), 2.72, 0.22, top_mat, 96)
# Tapered rocky underside
bpy.ops.mesh.primitive_cone_add(vertices=96, radius1=0.18, radius2=2.65, depth=2.2, location=(0, 0, -1.72))
rock = bpy.context.object
rock.name = "Tapered floating rock"
apply_mat(rock, island_mat)
smooth(rock)

# Gold ring around the island
bpy.ops.mesh.primitive_torus_add(major_radius=2.78, minor_radius=0.035, major_segments=96, minor_segments=12, location=(0, 0, 0.28))
ring = bpy.context.object
ring.name = "Golden orbit around the garden"
apply_mat(ring, gold)
animate_rotation(ring, 2, math.tau, 1, scene.frame_end)

# ----------------------------- FLOWERS --------------------------------
def make_flower(x, y, z, size, petal_mat, phase=0.0):
    stem = cylinder("Flower stem", (x, y, z + size * 0.42), size * 0.035, size * 0.85, leaf, 12)
    stem.rotation_euler[0] = random.uniform(-0.12, 0.12)
    # Leaves
    for side in (-1, 1):
        l = uv_sphere("Small leaf", (x + side * size * 0.16, y, z + size * 0.30), (size * 0.19, size * 0.07, size * 0.045), leaf, 16, 10)
        l.rotation_euler[1] = side * 0.45
    head_z = z + size * 0.86
    center = uv_sphere("Flower heart", (x, y, head_z), (size * 0.14,) * 3, gold, 20, 12)
    petals = []
    for i in range(7):
        a = phase + i * math.tau / 7
        px = x + math.cos(a) * size * 0.23
        py = y + math.sin(a) * size * 0.23
        p = uv_sphere("Silken flower petal", (px, py, head_z), (size * 0.23, size * 0.12, size * 0.055), petal_mat, 20, 12)
        p.rotation_euler[2] = a
        p.rotation_euler[1] = math.cos(a) * 0.18
        petals.append(p)
    # Gentle opening animation
    for p in petals:
        final_scale = p.scale.copy()
        p.scale = (final_scale.x * 0.18, final_scale.y * 0.18, final_scale.z * 0.18)
        p.keyframe_insert(data_path="scale", frame=1)
        p.scale = final_scale
        p.keyframe_insert(data_path="scale", frame=FPS * 4)
    return center

# Main central flower on a small pedestal
cylinder("Flower pedestal", (0, 0, 0.58), 0.52, 0.28, gold, 64)
main_heart = make_flower(0, 0, 0.74, 1.5, pale)
for i in range(17):
    a = random.random() * math.tau
    r = random.uniform(1.15, 2.35)
    s = random.uniform(0.35, 0.72)
    make_flower(math.cos(a) * r, math.sin(a) * r, 0.48, s, random.choice([pink, pale, cream]), a)

# ----------------------------- CRYSTALS -------------------------------
for i in range(11):
    a = i * math.tau / 11 + 0.2
    r = random.uniform(1.8, 2.55)
    loc = (math.cos(a) * r, math.sin(a) * r, 0.72)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=random.uniform(0.12, 0.25), location=loc)
    crystal = bpy.context.object
    crystal.name = "Moon crystal"
    crystal.scale.z = random.uniform(1.4, 2.2)
    apply_mat(crystal, glow)
    animate_rotation(crystal, 2, math.tau, 1, scene.frame_end)

# ----------------------------- FLOATING LIGHTS ------------------------
for i in range(85):
    a = random.random() * math.tau
    r = random.uniform(0.5, 4.4)
    z = random.uniform(-0.2, 3.4)
    s = random.uniform(0.018, 0.055)
    orb = uv_sphere("Floating firefly", (math.cos(a) * r, math.sin(a) * r, z), (s, s, s), glow, 12, 8)
    start = orb.location.copy()
    orb.location.z = start.z - random.uniform(0.2, 0.8)
    orb.keyframe_insert(data_path="location", frame=1)
    orb.location = start
    orb.keyframe_insert(data_path="location", frame=scene.frame_end)
    orb.scale = (s * 0.4,) * 3
    orb.keyframe_insert(data_path="scale", frame=1)
    orb.scale = (s * 1.4,) * 3
    orb.keyframe_insert(data_path="scale", frame=FPS * 2)

# ----------------------------- TEXT -----------------------------------
def text_object(body, name, loc, size, mat, extrude=0.008):
    curve = bpy.data.curves.new(name, 'FONT')
    curve.body = body
    curve.align_x = 'CENTER'
    curve.align_y = 'CENTER'
    curve.size = size
    curve.extrude = extrude
    obj = bpy.data.objects.new(name, curve)
    scene.collection.objects.link(obj)
    obj.location = loc
    apply_mat(obj, mat)
    return obj

title = text_object("ТАНЯ", "Тanya title", (0, -3.85, 1.2), 0.72, pale)
title.rotation_euler[0] = math.radians(72)
title.keyframe_insert(data_path="scale", frame=1)
title.scale = (1, 1, 1)
title.keyframe_insert(data_path="scale", frame=FPS * 7)

subtitle = text_object("ты — целая вселенная", "Love subtitle", (0, -3.78, 0.62), 0.25, cream)
subtitle.rotation_euler[0] = math.radians(72)

# ----------------------------- LIGHTING --------------------------------
def area_light(name, loc, power, color, size, target=(0, 0, 0)):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = power
    data.color = color
    data.shape = 'DISK'
    data.size = size
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()
    return obj

area_light("Soft pink key", (1, -4, 7), 1100, (1.0, 0.48, 0.68), 5)
area_light("Cool moon rim", (-5, 2, 5), 1500, (0.28, 0.42, 1.0), 4)
area_light("Golden flower glow", (3, 3, 3), 850, (1.0, 0.68, 0.32), 3)

# ----------------------------- CAMERA ----------------------------------
cam_data = bpy.data.cameras.new("Cinematic camera")
cam = bpy.data.objects.new("Cinematic camera", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam_data.lens = 48
cam_data.dof.use_dof = True
cam_data.dof.focus_object = main_heart
cam_data.dof.aperture_fstop = 4.0

def camera_key(frame, loc, target):
    cam.location = loc
    direction = Vector(target) - cam.location
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    cam.keyframe_insert(data_path="location", frame=frame)
    cam.keyframe_insert(data_path="rotation_euler", frame=frame)

camera_key(1, (8, -11, 6.5), (0, 0, 0.2))
camera_key(FPS * 4, (5.5, -9, 4.4), (0, 0, 0.45))
camera_key(FPS * 8, (1.8, -8.5, 3.5), (0, 0, 0.65))
camera_key(scene.frame_end, (0.2, -7.6, 3.0), (0, 0, 0.7))

# Smooth camera movement
if cam.animation_data and cam.animation_data.action:
    for fc in cam.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'BEZIER'

# Gentle global motion for island
for obj in (island, top, rock):
    obj.keyframe_insert(data_path="location", frame=1)
    obj.location.z += 0.12
    obj.keyframe_insert(data_path="location", frame=FPS * 6)
    obj.location.z -= 0.12
    obj.keyframe_insert(data_path="location", frame=scene.frame_end)

# ----------------------------- COMPOSITING -----------------------------
scene.use_nodes = True
nodes = scene.node_tree.nodes
nodes.clear()
rl = nodes.new("CompositorNodeRLayers")
glare = nodes.new("CompositorNodeGlare")
glare.glare_type = 'FOG_GLOW'
glare.threshold = 1.2
glare.quality = 'HIGH'
comp = nodes.new("CompositorNodeComposite")
scene.node_tree.links.new(rl.outputs["Image"], glare.inputs["Image"])
scene.node_tree.links.new(glare.outputs["Image"], comp.inputs["Image"])

# Render quality / preview
# EEVEE settings vary across Blender versions; keep rendering usable if the API moved.
if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
    scene.eevee.taa_render_samples = 128
scene.render.image_settings.file_format = 'FFMPEG'
scene.render.filepath = OUTPUT_PATH
scene.frame_set(1)

# Select camera for a useful opening view
bpy.ops.object.select_all(action='DESELECT')
cam.select_set(True)
bpy.context.view_layer.objects.active = cam

print("Tanya Cinematic Garden is ready.")
print("Render Animation: Ctrl+F12. Output:", bpy.path.abspath(OUTPUT_PATH))
