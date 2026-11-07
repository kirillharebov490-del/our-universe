"""
TANYA — CINEMATIC GARDEN
Blender scene generator. Tested for Python syntax before publishing.
Run in Blender: Scripting > Open > this file > Run Script.
Render animation: Ctrl+F12. Output: //tanya_cinematic.mp4

No add-ons or external assets required.
"""

import bpy
import math
import random
from mathutils import Vector

# ---------------------------------------------------------------------
# PROJECT SETTINGS
# ---------------------------------------------------------------------
FPS = 30
DURATION_SECONDS = 15
FRAME_START = 1
FRAME_END = FRAME_START + FPS * DURATION_SECONDS - 1
RESOLUTION_X = 1920
RESOLUTION_Y = 1080
OUTPUT_PATH = "//tanya_cinematic.mp4"
RANDOM_SEED = 52
random.seed(RANDOM_SEED)

# ---------------------------------------------------------------------
# COMPATIBILITY HELPERS
# ---------------------------------------------------------------------
def set_render_engine(scene):
    """Choose an EEVEE identifier actually exposed by this Blender build."""
    engine_items = bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items
    available = {item.identifier for item in engine_items}
    # Blender 5.2 LTS builds may expose BLENDER_EEVEE; other releases expose
    # BLENDER_EEVEE_NEXT. Try the advertised identifiers, never hard-fail
    # because a version-specific engine name is absent.
    for engine_id in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        if engine_id in available:
            try:
                scene.render.engine = engine_id
                return engine_id
            except (TypeError, ValueError):
                pass
    # Last-resort assignment gives Blender a chance to report its own error.
    for engine_id in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = engine_id
            return engine_id
        except (TypeError, ValueError):
            continue
    raise RuntimeError("This Blender installation does not expose an EEVEE render engine.")

def set_socket(node, socket_names, value):
    """Set the first available shader socket from a list of versioned names."""
    for name in socket_names:
        socket = node.inputs.get(name)
        if socket is not None:
            socket.default_value = value
            return True
    return False

def smooth_action(obj, interpolation="BEZIER"):
    """Apply consistent interpolation to all F-curves on an object."""
    anim = obj.animation_data
    if not anim or not anim.action:
        return
    # Blender 5.x may expose layered actions; legacy action.fcurves remains
    # available in common builds. Guard access for compatibility.
    try:
        curves = anim.action.fcurves
    except (AttributeError, TypeError):
        return
    for curve in curves:
        for point in curve.keyframe_points:
            point.interpolation = interpolation

# ---------------------------------------------------------------------
# SCENE RESET
# ---------------------------------------------------------------------
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

scene = bpy.context.scene
scene.frame_start = FRAME_START
scene.frame_end = FRAME_END
scene.render.fps = FPS
scene.render.fps_base = 1.0
scene.render.resolution_x = RESOLUTION_X
scene.render.resolution_y = RESOLUTION_Y
scene.render.resolution_percentage = 100
ACTIVE_ENGINE = set_render_engine(scene)

scene.render.image_settings.file_format = "FFMPEG"
scene.render.image_settings.color_mode = "RGB"
scene.render.ffmpeg.format = "MPEG4"
scene.render.ffmpeg.codec = "H264"
scene.render.ffmpeg.constant_rate_factor = "HIGH"
scene.render.ffmpeg.ffmpeg_preset = "GOOD"
scene.render.filepath = OUTPUT_PATH
scene.render.film_transparent = False

# Color pipeline: warm highlights, deep blue shadows.
try:
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
except (TypeError, ValueError):
    pass
scene.view_settings.exposure = 0.0
scene.view_settings.gamma = 1.0

# World background with a real node-based color.
world = scene.world or bpy.data.worlds.new("Midnight blue world")
scene.world = world
world.use_nodes = True
background = world.node_tree.nodes.get("Background")
if background:
    background.inputs["Color"].default_value = (0.006, 0.012, 0.045, 1.0)
    background.inputs["Strength"].default_value = 0.22
world.color = (0.006, 0.012, 0.045)

# ---------------------------------------------------------------------
# MATERIALS
# ---------------------------------------------------------------------
def make_material(name, color, metallic=0.0, roughness=0.5,
                  emission=None, emission_strength=0.0, subsurface=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    shader = next(
        (node for node in nodes if node.bl_idname == "ShaderNodeBsdfPrincipled"),
        None,
    )
    if shader is None:
        shader = nodes.new("ShaderNodeBsdfPrincipled")
    output = next(
        (node for node in nodes if node.bl_idname == "ShaderNodeOutputMaterial"),
        None,
    )
    if output is None:
        output = nodes.new("ShaderNodeOutputMaterial")
    if not output.inputs["Surface"].is_linked:
        mat.node_tree.links.new(shader.outputs["BSDF"], output.inputs["Surface"])

    set_socket(shader, ("Base Color",), (*color, 1.0))
    set_socket(shader, ("Metallic",), metallic)
    set_socket(shader, ("Roughness",), roughness)
    set_socket(shader, ("Subsurface Weight", "Subsurface"), subsurface)
    if emission is not None:
        set_socket(shader, ("Emission Color", "Emission"), (*emission, 1.0))
        set_socket(shader, ("Emission Strength",), emission_strength)
    return mat

MAT = {
    "night": make_material("01 • Deep midnight", (0.008, 0.014, 0.045), roughness=0.92),
    "rock": make_material("02 • Amethyst stone", (0.105, 0.065, 0.17), roughness=0.82),
    "soil": make_material("03 • Velvet moss", (0.025, 0.105, 0.075), roughness=0.95),
    "gold": make_material("04 • Brushed champagne", (0.72, 0.39, 0.12), metallic=0.78, roughness=0.24),
    "pink": make_material("05 • Rose silk", (0.82, 0.12, 0.32), roughness=0.31, subsurface=0.08),
    "blush": make_material("06 • Blush silk", (1.0, 0.43, 0.61), roughness=0.28, subsurface=0.12),
    "ivory": make_material("07 • Warm ivory", (1.0, 0.78, 0.58), roughness=0.3, subsurface=0.1),
    "leaf": make_material("08 • Emerald leaves", (0.018, 0.16, 0.075), roughness=0.65),
    "cyan_glow": make_material("09 • Blue starlight", (0.24, 0.55, 1.0), roughness=0.25,
                               emission=(0.12, 0.38, 1.0), emission_strength=2.8),
    "warm_glow": make_material("10 • Golden firefly", (1.0, 0.52, 0.18), roughness=0.3,
                               emission=(1.0, 0.24, 0.055), emission_strength=2.2),
}

# ---------------------------------------------------------------------
# GEOMETRY HELPERS
# ---------------------------------------------------------------------
def assign_material(obj, material):
    if obj.data and hasattr(obj.data, "materials"):
        obj.data.materials.append(material)
    return obj

def shade_smooth(obj):
    if obj.type == "MESH":
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
    return obj

def uv_sphere(name, location, scale, material, segments=24, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments, ring_count=rings, radius=1.0, location=location
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    assign_material(obj, material)
    shade_smooth(obj)
    return obj

def cylinder(name, location, radius, depth, material, vertices=64, bevel=True):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices, radius=radius, depth=depth, location=location
    )
    obj = bpy.context.object
    obj.name = name
    assign_material(obj, material)
    if bevel:
        modifier = obj.modifiers.new("Soft machined edges", "BEVEL")
        modifier.width = min(radius * 0.08, depth * 0.12, 0.1)
        modifier.segments = 3
        obj.modifiers.new("Weighted normals", "WEIGHTED_NORMAL")
    return obj

def animate_float(obj, base_z, amplitude=0.12, phase=0.0):
    obj.location.z = base_z - amplitude
    obj.keyframe_insert(data_path="location", frame=FRAME_START)
    obj.location.z = base_z + amplitude
    obj.keyframe_insert(data_path="location", frame=FRAME_START + FPS * 4)
    obj.location.z = base_z - amplitude
    obj.keyframe_insert(data_path="location", frame=FRAME_END)
    smooth_action(obj, "BEZIER")

def add_area_light(name, location, target, power, color, size):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = power
    data.color = color
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    return obj

# ---------------------------------------------------------------------
# ENVIRONMENT — FLOATING GARDEN
# ---------------------------------------------------------------------
# Large dark cyclorama plane; the camera never sees a horizon line.
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -4.0))
backdrop = bpy.context.object
backdrop.name = "Infinite midnight backdrop"
assign_material(backdrop, MAT["night"])

foundation = cylinder("Floating island • amethyst rim", (0, 0, -0.25), 3.15, 0.9, MAT["rock"], 128)
garden_top = cylinder("Floating island • moss surface", (0, 0, 0.28), 2.92, 0.2, MAT["soil"], 128)

bpy.ops.mesh.primitive_cone_add(
    vertices=128, radius1=0.12, radius2=2.78, depth=2.45, location=(0, 0, -1.72)
)
underside = bpy.context.object
underside.name = "Sculpted tapered island underside"
assign_material(underside, MAT["rock"])
shade_smooth(underside)

# Thin gold orbit and a second delicate inner ring.
for ring_index, (radius, thickness, z_value) in enumerate(((2.96, 0.035, 0.28), (2.72, 0.012, 0.39))):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=radius, minor_radius=thickness,
        major_segments=128, minor_segments=12, location=(0, 0, z_value)
    )
    orbit = bpy.context.object
    orbit.name = "Golden orbital ring %02d" % ring_index
    assign_material(orbit, MAT["gold"])
    orbit.rotation_euler[2] = 0.0
    orbit.keyframe_insert(data_path="rotation_euler", frame=FRAME_START)
    orbit.rotation_euler[2] = math.tau if ring_index == 0 else -math.tau
    orbit.keyframe_insert(data_path="rotation_euler", frame=FRAME_END)
    smooth_action(orbit, "LINEAR")

# Small rock facets around the underside give the island a designed silhouette.
for index in range(18):
    angle = index * math.tau / 18.0
    radius = random.uniform(2.35, 2.8)
    z = random.uniform(-1.7, -0.85)
    size = random.uniform(0.16, 0.34)
    shard = uv_sphere(
        "Amethyst rock facet",
        (math.cos(angle) * radius, math.sin(angle) * radius, z),
        (size, size * 0.8, size * 1.5),
        MAT["rock"], 12, 8,
    )
    shard.rotation_euler[1] = random.uniform(-0.5, 0.5)
    shard.rotation_euler[2] = angle

# ---------------------------------------------------------------------
# FLOWERS — CENTRAL BLOOM AND SMALLER GARDEN
# ---------------------------------------------------------------------
def make_flower(x, y, ground_z, size, petal_material, phase=0.0, name_prefix="Flower"):
    stem_height = size * 0.78
    stem = cylinder(
        name_prefix + " • stem",
        (x, y, ground_z + stem_height * 0.5),
        max(size * 0.025, 0.012), stem_height, MAT["leaf"], 12, bevel=False
    )
    stem.rotation_euler[1] = random.uniform(-0.07, 0.07)

    for side in (-1, 1):
        leaf_obj = uv_sphere(
            name_prefix + " • leaf",
            (x + side * size * 0.12, y, ground_z + size * 0.28),
            (size * 0.19, size * 0.065, size * 0.035),
            MAT["leaf"], 16, 10,
        )
        leaf_obj.rotation_euler[1] = side * 0.42
        leaf_obj.rotation_euler[2] = side * 0.25

    head_z = ground_z + stem_height
    center = uv_sphere(
        name_prefix + " • golden heart",
        (x, y, head_z), (size * 0.13,) * 3, MAT["gold"], 20, 12
    )
    petals = []
    for petal_index in range(8):
        angle = phase + petal_index * math.tau / 8.0
        petal = uv_sphere(
            name_prefix + " • petal",
            (x + math.cos(angle) * size * 0.22,
             y + math.sin(angle) * size * 0.22, head_z),
            (size * 0.23, size * 0.115, size * 0.055),
            petal_material, 20, 12,
        )
        petal.rotation_euler[2] = angle
        petal.rotation_euler[1] = math.cos(angle) * 0.16
        final_scale = petal.scale.copy()
        petal.scale = final_scale * 0.12
        petal.keyframe_insert(data_path="scale", frame=FRAME_START)
        petal.scale = final_scale
        petal.keyframe_insert(data_path="scale", frame=FRAME_START + FPS * 3)
        smooth_action(petal, "BEZIER")
        petals.append(petal)
    return center

cylinder("Central flower • gold pedestal", (0, 0, 0.53), 0.55, 0.26, MAT["gold"], 80)
hero_flower = make_flower(0, 0, 0.66, 1.52, MAT["ivory"], name_prefix="Hero flower")

for index in range(22):
    angle = random.random() * math.tau
    radius = random.uniform(1.05, 2.48)
    size = random.uniform(0.28, 0.68)
    petal_mat = random.choice((MAT["pink"], MAT["blush"], MAT["ivory"]))
    make_flower(
        math.cos(angle) * radius,
        math.sin(angle) * radius,
        0.43,
        size,
        petal_mat,
        phase=angle,
        name_prefix="Garden flower %02d" % index,
    )

# ---------------------------------------------------------------------
# CRYSTALS AND FIREFLIES
# ---------------------------------------------------------------------
for index in range(13):
    angle = index * math.tau / 13.0 + 0.17
    radius = random.uniform(1.85, 2.62)
    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=1, radius=random.uniform(0.12, 0.24),
        location=(math.cos(angle) * radius, math.sin(angle) * radius, 0.76)
    )
    crystal = bpy.context.object
    crystal.name = "Floating moon crystal"
    crystal.scale.z = random.uniform(1.5, 2.4)
    assign_material(crystal, MAT["cyan_glow"])
    crystal.rotation_euler[2] = angle
    crystal.keyframe_insert(data_path="rotation_euler", frame=FRAME_START)
    crystal.rotation_euler[2] = angle + math.tau
    crystal.keyframe_insert(data_path="rotation_euler", frame=FRAME_END)
    smooth_action(crystal, "LINEAR")
    animate_float(crystal, crystal.location.z, 0.08, angle)

for index in range(95):
    angle = random.random() * math.tau
    radius = random.uniform(0.45, 4.15)
    base_z = random.uniform(-0.05, 3.7)
    size = random.uniform(0.014, 0.043)
    glow_mat = MAT["warm_glow"] if index % 3 else MAT["cyan_glow"]
    orb = uv_sphere(
        "Firefly %03d" % index,
        (math.cos(angle) * radius, math.sin(angle) * radius, base_z),
        (size, size, size), glow_mat, 12, 8,
    )
    animate_float(orb, base_z, random.uniform(0.12, 0.48), angle)
    orb.scale = (size * 0.55,) * 3
    orb.keyframe_insert(data_path="scale", frame=FRAME_START)
    orb.scale = (size * 1.35,) * 3
    orb.keyframe_insert(data_path="scale", frame=FRAME_START + random.randint(18, 55))
    orb.scale = (size * 0.7,) * 3
    orb.keyframe_insert(data_path="scale", frame=FRAME_END)
    smooth_action(orb, "BEZIER")

# Sparse distant stars add depth without filling the frame with noise.
for index in range(120):
    x = random.uniform(-15.0, 15.0)
    y = random.uniform(5.0, 14.0)
    z = random.uniform(2.0, 12.0)
    size = random.uniform(0.008, 0.022)
    uv_sphere("Distant star %03d" % index, (x, y, z), (size,) * 3, MAT["cyan_glow"], 8, 6)

# ---------------------------------------------------------------------
# TYPOGRAPHY
# ---------------------------------------------------------------------
def make_text(body, name, location, size, material, extrude=0.002):
    font_curve = bpy.data.curves.new(name, "FONT")
    font_curve.body = body
    font_curve.align_x = "CENTER"
    font_curve.align_y = "CENTER"
    font_curve.size = size
    font_curve.extrude = extrude
    font_curve.bevel_depth = 0.001
    font_curve.bevel_resolution = 2
    text_obj = bpy.data.objects.new(name, font_curve)
    scene.collection.objects.link(text_obj)
    text_obj.location = location
    assign_material(text_obj, material)
    return text_obj

title = make_text("ТАНЯ", "Title • ТАНЯ", (0.0, -3.45, 1.0), 0.78, MAT["ivory"])
title.rotation_euler[0] = math.radians(90)
title.scale = (0.75, 0.75, 0.75)
title.keyframe_insert(data_path="scale", frame=FRAME_START)
title.scale = (1.0, 1.0, 1.0)
title.keyframe_insert(data_path="scale", frame=FRAME_START + FPS * 5)
smooth_action(title)

subtitle = make_text(
    "ты — целая вселенная",
    "Subtitle • dedication",
    (0.0, -3.42, 0.43),
    0.25,
    MAT["blush"],
    extrude=0.001,
)
subtitle.rotation_euler[0] = math.radians(90)

# ---------------------------------------------------------------------
# CINEMATIC LIGHTING
# ---------------------------------------------------------------------
add_area_light("Key • warm softbox", (1.5, -4.5, 7.0), (0, 0, 0), 1250, (1.0, 0.58, 0.48), 5.0)
add_area_light("Rim • moon blue", (-5.0, 1.5, 5.5), (0, 0, 0), 1750, (0.28, 0.43, 1.0), 4.0)
add_area_light("Fill • rose", (4.0, 3.0, 3.0), (0, 0, 0.4), 950, (1.0, 0.32, 0.53), 3.5)
add_area_light("Top • flower sheen", (0.0, 0.0, 8.0), (0, 0, 0), 800, (1.0, 0.82, 0.62), 3.0)

# ---------------------------------------------------------------------
# CAMERA — SLOW DOLLY IN WITH A GENTLE ORBIT
# ---------------------------------------------------------------------
camera_data = bpy.data.cameras.new("Camera • cinematic 50mm")
camera = bpy.data.objects.new("Camera • cinematic", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.lens = 50
camera_data.sensor_width = 36
camera_data.dof.use_dof = True
camera_data.dof.focus_object = hero_flower
camera_data.dof.aperture_fstop = 3.2
camera_data.dof.aperture_blades = 7

def camera_key(frame, location, target):
    camera.location = Vector(location)
    direction = Vector(target) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera.keyframe_insert(data_path="location", frame=frame)
    camera.keyframe_insert(data_path="rotation_euler", frame=frame)

camera_key(FRAME_START, (8.8, -12.8, 7.1), (0.0, 0.0, 0.1))
camera_key(FRAME_START + FPS * 5, (5.4, -10.6, 5.0), (0.0, 0.0, 0.45))
camera_key(FRAME_START + FPS * 10, (2.5, -9.1, 3.8), (0.0, 0.0, 0.62))
camera_key(FRAME_END, (0.8, -8.2, 3.2), (0.0, 0.0, 0.68))
smooth_action(camera, "BEZIER")

# Gentle vertical drift of the whole island cluster.
for obj in (foundation, garden_top, underside):
    base_z = obj.location.z
    obj.location.z = base_z - 0.07
    obj.keyframe_insert(data_path="location", frame=FRAME_START)
    obj.location.z = base_z + 0.07
    obj.keyframe_insert(data_path="location", frame=FRAME_START + FPS * 7)
    obj.location.z = base_z - 0.07
    obj.keyframe_insert(data_path="location", frame=FRAME_END)
    smooth_action(obj)

# ---------------------------------------------------------------------
# COMPOSITING — SUBTLE HALATION, NOT AN OVERPOWERED GLOW
# ---------------------------------------------------------------------
scene.use_nodes = True
compositor = scene.node_tree
compositor.nodes.clear()
render_layers = compositor.nodes.new("CompositorNodeRLayers")
render_layers.location = (-320, 40)
glare = compositor.nodes.new("CompositorNodeGlare")
glare.location = (-60, 40)
glare.glare_type = "FOG_GLOW"
glare.quality = "HIGH"
glare.threshold = 1.35
glare.size = 7
composite = compositor.nodes.new("CompositorNodeComposite")
composite.location = (200, 40)
compositor.links.new(render_layers.outputs["Image"], glare.inputs["Image"])
compositor.links.new(glare.outputs["Image"], composite.inputs["Image"])

# ---------------------------------------------------------------------
# RENDER QUALITY — SAFE OPTIONAL SETTINGS
# ---------------------------------------------------------------------
eevee_settings = getattr(scene, "eevee", None)
if eevee_settings is not None:
    for property_name, value in (
        ("taa_render_samples", 96),
        ("taa_samples", 64),
    ):
        if hasattr(eevee_settings, property_name):
            try:
                setattr(eevee_settings, property_name, value)
            except (AttributeError, TypeError, ValueError):
                pass

# Prefer high-quality shadows when the active engine exposes the setting.
for owner, property_name, value in (
    (getattr(scene, "eevee", None), "use_shadow_high_bitdepth", True),
):
    if owner is not None and hasattr(owner, property_name):
        try:
            setattr(owner, property_name, value)
        except (AttributeError, TypeError, ValueError):
            pass

scene.frame_set(FRAME_START)
bpy.ops.object.select_all(action="DESELECT")
camera.select_set(True)
bpy.context.view_layer.objects.active = camera

print("TANYA CINEMATIC GARDEN — scene successfully created.")
print("Render engine:", ACTIVE_ENGINE)
print("Frames:", FRAME_START, "-", FRAME_END, "| FPS:", FPS)
print("Output:", bpy.path.abspath(OUTPUT_PATH))
print("Render animation with Ctrl+F12.")
