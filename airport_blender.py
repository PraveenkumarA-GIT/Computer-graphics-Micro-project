# =====================================================================
#  3D AIRPORT - GTA STYLE GAME (Blender 3.2+ / 4.x / 5.x)
#
#  HOW TO RUN
#    1. Blender -> "Scripting" workspace -> Text Editor -> Open this file
#    2. Alt+P (Run Script). The airport builds and the game starts.
#       (Restart later: 3D Viewport -> N panel -> "Airport" tab -> Play)
#
#  YOU PLAY A PASSENGER (orange jacket) in a third-person view:
#    W A S D ... move relative to the camera      Mouse .... camera
#    Shift ..... sprint     Space ... jump         Wheel .... camera distance
#    E ......... talk to the nearest person (agents, guards, passengers)
#    R ......... respawn    M ....... voices on/off    L ..... performance mode
#    ESC ....... exit
#
#  MISSION: talk to the check-in agent -> go to Security -> talk to the
#  officer -> walk to Gate B1 -> "MISSION PASSED".
#
#  NPCs: walk, stop for you, chat with each other's lines, react if you
#  run into them, and talk with SUBTITLES + VOICE. Voices come from your
#  computer's text-to-speech (Windows built-in, macOS "say", Linux:
#  sudo apt install espeak-ng). A PA system makes airport announcements.
#
#  Also included: START_MODE = "TOUR" (automatic guided walk, can be
#  rendered to MP4) and "WALK" (simple first-person).
# =====================================================================
import bpy, bmesh, math, random, time
from math import pi, sin, cos, atan2, sqrt

random.seed(7)
NPC_COUNT = 16               # lower this if your PC lags
HIGH_DETAIL_PEOPLE = True    # eyes, hands, noses (set False for fewer objects)
VOICE_ON = True              # NPC voices via your OS text-to-speech (M key toggles in game)
START_IN_SOLID_MODE = False  # True = fastest viewport
START_MODE = "PLAY"          # "PLAY" = GTA style game, "TOUR" = automatic walk, "WALK" = first person

scene = bpy.context.scene


# ---------------------------------------------------------------------
#  Scene cleanup
# ---------------------------------------------------------------------
def clear_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    for blk in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                bpy.data.lights, bpy.data.cameras):
        for b in list(blk):
            if b.users == 0:
                blk.remove(b)


clear_scene()
COLL = bpy.data.collections.new("Airport")
scene.collection.children.link(COLL)

# ---------------------------------------------------------------------
#  Materials
# ---------------------------------------------------------------------
M = {}


def mat(key, color, rough=0.5, metal=0.0, emit=0.0, alpha=1.0):
    m = bpy.data.materials.new(key)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit > 0:
        k = "Emission Color" if "Emission Color" in b.inputs else "Emission"
        b.inputs[k].default_value = (*color, 1)
        b.inputs["Emission Strength"].default_value = emit
    if alpha < 1.0:
        b.inputs["Alpha"].default_value = alpha
        for attr, val in (("blend_method", "BLEND"), ("surface_render_method", "BLENDED"),
                          ("shadow_method", "NONE")):
            try:
                setattr(m, attr, val)
            except Exception:
                pass
    # Hidden-surface removal helper: cull back faces of opaque objects
    m.use_backface_culling = alpha >= 1.0
    m.diffuse_color = (*color, alpha)
    M[key] = m
    return m


mat("fuse", (0.92, 0.92, 0.95), 0.35)
mat("tail", (0.04, 0.22, 0.85), 0.4)
mat("metal", (0.55, 0.55, 0.6), 0.3, 0.8)
mat("winstrip", (0.02, 0.04, 0.1), 0.3)
mat("dark", (0.03, 0.03, 0.04), 0.6)
mat("asphalt", (0.035, 0.035, 0.04), 0.9)
mat("grass", (0.03, 0.16, 0.05), 1.0)
mat("concrete", (0.32, 0.32, 0.34), 0.9)
mat("floor", (0.82, 0.82, 0.85), 0.12)
mat("wall", (0.75, 0.77, 0.8), 0.6)
mat("column", (0.85, 0.86, 0.9), 0.35)
mat("roof", (0.55, 0.58, 0.65), 0.5)
mat("glass", (0.55, 0.75, 0.95), 0.05, alpha=0.15)
mat("doorglass", (0.6, 0.8, 0.95), 0.05, alpha=0.28)
mat("signbg", (0.02, 0.03, 0.08), 0.4)
mat("t_white", (1, 1, 1), emit=3.0)
mat("t_cyan", (0.35, 0.75, 1.0), emit=4.0)
mat("t_yellow", (1.0, 0.8, 0.1), emit=4.0)
mat("t_orange", (1.0, 0.5, 0.1), emit=4.0)
mat("t_green", (0.2, 1.0, 0.3), emit=3.0)
mat("t_gray", (0.7, 0.7, 0.75), emit=2.0)
mat("seat", (0.05, 0.15, 0.6), 0.5)
mat("counter", (0.1, 0.25, 0.65), 0.4)
mat("countertop", (0.9, 0.9, 0.92), 0.3)
mat("screen", (0.2, 0.6, 1.0), emit=2.5)
mat("strip", (1.0, 0.95, 0.85), emit=6.0)
mat("lamp", (1.0, 0.8, 0.5), emit=8.0)
mat("headl", (1.0, 1.0, 0.9), emit=5.0)
mat("taill", (1.0, 0.05, 0.05), emit=4.0)
mat("leaf", (0.05, 0.35, 0.08), 0.8)
mat("trunk", (0.25, 0.17, 0.1), 0.9)
mat("pot", (0.1, 0.1, 0.12), 0.6)
mat("plant", (0.05, 0.3, 0.1), 0.8)
mat("skin", (0.8, 0.58, 0.45), 0.7)
mat("pants", (0.08, 0.08, 0.12), 0.8)
mat("luggage", (0.05, 0.05, 0.07), 0.5)
mat("marking", (0.9, 0.9, 0.9), emit=0.6)
mat("uniform", (0.1, 0.25, 0.75), 0.7)
mat("towerglass", (0.6, 0.85, 1.0), 0.1, emit=1.2, alpha=0.45)
mat("car0", (0.6, 0.05, 0.05), 0.3, 0.3)
mat("car1", (0.05, 0.05, 0.07), 0.3, 0.3)
mat("car2", (0.7, 0.7, 0.72), 0.3, 0.3)
SHIRTS = []
for i, c in enumerate([(0.7, 0.1, 0.1), (0.1, 0.4, 0.2), (0.9, 0.7, 0.1),
                       (0.3, 0.3, 0.35), (0.1, 0.3, 0.7), (0.8, 0.8, 0.8), (0.5, 0.15, 0.5)]):
    SHIRTS.append(mat("shirt%d" % i, c, 0.8))

# ---------------------------------------------------------------------
#  Mesh helpers (shared mesh data = light on memory / fast viewport)
# ---------------------------------------------------------------------
_mesh = {}


def get_mesh(kind, m):
    key = (kind, m.name)
    if key in _mesh:
        return _mesh[key]
    bm = bmesh.new()
    if kind == "cube":
        bmesh.ops.create_cube(bm, size=1.0)
    elif kind == "leg":      # cube whose origin is at the top (hip pivot)
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.translate(bm, vec=(0, 0, -0.5), verts=bm.verts)
    elif kind == "cyl":
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=16,
                              radius1=0.5, radius2=0.5, depth=1.0)
    elif kind == "cone":
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=16,
                              radius1=0.5, radius2=0.0, depth=1.0)
    elif kind == "sph":
        bmesh.ops.create_uvsphere(bm, u_segments=14, v_segments=8, radius=0.5)
    me = bpy.data.meshes.new("%s_%s" % (kind, m.name))
    bm.to_mesh(me)
    bm.free()
    if kind in ("sph", "cyl", "cone"):
        for p in me.polygons:
            p.use_smooth = True
    me.materials.append(m)
    _mesh[key] = me
    return me


def mk(kind, name, loc, size, m, rot=(0, 0, 0), parent=None):
    ob = bpy.data.objects.new(name, get_mesh(kind, m))
    ob.location = loc
    ob.scale = size
    ob.rotation_euler = rot
    if parent:
        ob.parent = parent
    COLL.objects.link(ob)
    return ob


def empty(name, loc, rot=(0, 0, 0), scale=1.0):
    e = bpy.data.objects.new(name, None)
    e.location = loc
    e.rotation_euler = rot
    e.scale = (scale, scale, scale)
    e.empty_display_size = 0.01
    COLL.objects.link(e)
    return e


def text(body, loc, size, m, align="CENTER", extrude=0.03):
    cu = bpy.data.curves.new("txt", "FONT")
    cu.body = body
    cu.size = size
    cu.align_x = align
    cu.align_y = "CENTER"
    cu.extrude = extrude
    cu.materials.append(m)
    ob = bpy.data.objects.new("txt_" + body[:10], cu)
    ob.location = loc
    ob.rotation_euler = (pi / 2, 0, 0)       # stands up, readable from -Y
    COLL.objects.link(ob)
    return ob


def sign(x, y, z, w, h, body, tmat, size, hang=True):
    mk("cube", "signbg", (x, y, z), (w, 0.25, h), M["signbg"])
    text(body, (x, y - 0.14, z), size, tmat)
    if hang:
        for sx in (-w * 0.4, w * 0.4):
            top = 11.8
            L = top - (z + h / 2)
            mk("cyl", "rod", (x + sx, y, z + h / 2 + L / 2), (0.08, 0.08, L), M["metal"])


# ---------------------------------------------------------------------
#  Object builders
# ---------------------------------------------------------------------
def build_plane(name, loc, rz=0.0, s=1.0, body=None, tail=None, ry=0.0):
    body = body or M["fuse"]
    tail = tail or M["tail"]
    r = empty(name, loc, (0, ry, rz), s)
    mk("cyl", name + "_f", (0, 0, 0), (3.4, 3.4, 34), body, (0, pi / 2, 0), r)
    mk("sph", name + "_n", (17, 0, 0), (5, 3.4, 3.4), body, parent=r)
    mk("sph", name + "_e", (-17, 0, 0.4), (6, 2.6, 2.6), body, parent=r)
    for sg in (1, -1):
        mk("cube", name + "_w", (1, sg * 9.5, -0.9), (6, 19, 0.35), body, (0, 0, sg * 0.5), r)
        mk("cyl", name + "_en", (2.5, sg * 7, -2.0), (2.2, 2.2, 4.5), M["metal"], (0, pi / 2, 0), r)
        mk("cube", name + "_st", (-16.5, sg * 4, 0.8), (3, 8, 0.25), body, (0, 0, sg * 0.4), r)
        mk("cube", name + "_ws", (6, sg * 1.72, 0.6), (18, 0.05, 0.35), M["winstrip"], parent=r)
    mk("cube", name + "_fin", (-15.5, 0, 4.2), (5, 0.35, 6.5), tail, parent=r)
    for gx in (9, -3):
        mk("cyl", name + "_g", (gx, 0, -2.0), (0.25, 0.25, 2.0), M["metal"], parent=r)
    return r


def build_palm(x, y, h=6.0):
    mk("cyl", "trunk", (x, y, h / 2), (0.4, 0.4, h), M["trunk"])
    for i in range(7):
        a = i * 2 * pi / 7
        mk("cube", "leaf", (x + 1.5 * cos(a), y + 1.5 * sin(a), h + 0.1),
           (0.5, 3.4, 0.06), M["leaf"], (-0.4, 0, a - pi / 2))


def build_lamp(x, y):
    mk("cyl", "lamp", (x, y, 3.5), (0.18, 0.18, 7), M["metal"])
    mk("sph", "bulb", (x, y, 7.1), (0.7, 0.7, 0.7), M["lamp"])


def build_plant(x, y):
    mk("cyl", "pot", (x, y, 0.35), (0.7, 0.7, 0.7), M["pot"])
    mk("sph", "foliage", (x, y, 1.5), (1.2, 1.2, 1.5), M["plant"])


def build_bench(x, y):
    mk("cube", "seat", (x, y, 0.45), (3.6, 0.8, 0.12), M["seat"])
    mk("cube", "back", (x, y - 0.38, 0.85), (3.6, 0.1, 0.6), M["seat"])
    for sx in (-1.6, 1.6):
        mk("cube", "leg", (x + sx, y, 0.22), (0.1, 0.6, 0.44), M["metal"])


CARS = []


def build_car(x, y, mkey, v):
    r = empty("car", (x, y, 0), (0, 0, 0 if v > 0 else pi))
    mk("cube", "body", (0, 0, 0.65), (4.4, 1.8, 0.7), M[mkey], parent=r)
    mk("cube", "cabin", (-0.2, 0, 1.25), (2.3, 1.6, 0.6), M["winstrip"], parent=r)
    mk("cube", "hl", (2.2, 0.6, 0.7), (0.05, 0.4, 0.2), M["headl"], parent=r)
    mk("cube", "hl", (2.2, -0.6, 0.7), (0.05, 0.4, 0.2), M["headl"], parent=r)
    mk("cube", "tl", (-2.2, 0.6, 0.7), (0.05, 0.4, 0.2), M["taill"], parent=r)
    mk("cube", "tl", (-2.2, -0.6, 0.7), (0.05, 0.4, 0.2), M["taill"], parent=r)
    for wx in (-1.4, 1.4):
        for wy in (-0.9, 0.9):
            mk("cyl", "wheel", (wx, wy, 0.35), (0.7, 0.7, 0.3), M["dark"], (pi / 2, 0, 0), r)
    CARS.append({"root": r, "v": v})


NAMES_F = ["Priya", "Anita", "Maya", "Sara", "Neha", "Emma", "Divya", "Lina"]
NAMES_M = ["Arjun", "Rahul", "Vikram", "John", "Omar", "Ravi", "Karan", "Leo"]
SKINS = [mat("skin%d" % i, c, 0.6) for i, c in enumerate(
    [(0.85, 0.65, 0.52), (0.72, 0.5, 0.36), (0.55, 0.36, 0.25), (0.38, 0.24, 0.17), (0.92, 0.75, 0.62)])]
HAIRS = [mat("hair%d" % i, c, 0.5) for i, c in enumerate(
    [(0.03, 0.03, 0.03), (0.15, 0.09, 0.05), (0.35, 0.2, 0.1), (0.55, 0.4, 0.2), (0.5, 0.5, 0.52)])]
PANTS_MATS = [mat("pants%d" % i, c, 0.8) for i, c in enumerate(
    [(0.08, 0.08, 0.12), (0.2, 0.2, 0.25), (0.25, 0.18, 0.1), (0.1, 0.15, 0.3)])]
mat("shoe", (0.05, 0.05, 0.05), 0.5)
mat("eye", (0.02, 0.02, 0.02), 0.2)
mat("player_jacket", (0.9, 0.35, 0.05), 0.6)
mat("bag", (0.5, 0.05, 0.05), 0.7)
mat("marker", (1.0, 0.8, 0.0), emit=6.0)

NPCS = []


def _pivot(name, loc, parent):
    e = bpy.data.objects.new(name, None)
    e.location = loc
    e.parent = parent
    e.empty_display_size = 0.01
    COLL.objects.link(e)
    return e


def build_person(name, pos, shirt, rz=0.0, seated=False, luggage=False, walker=False,
                 skin=None, hair=None, pants=None, register=True, gender=None, backpack=False):
    """Articulated low-poly human: hips/knees/shoulders/elbows/head can all be animated."""
    role = ("agent" if name.startswith("agent") else "guard" if name.startswith("guard")
            else "sitter" if name.startswith("sit") else "pax" if name.startswith("pax")
            else "walker" if name.startswith("walker") else "player")
    gender = gender or random.choice("MF")
    skin = skin or random.choice(SKINS)
    hair = hair or random.choice(HAIRS)
    pants = pants or random.choice(PANTS_MATS)
    r = empty(name, pos, (0, 0, rz))
    hips, knees, shoulders, elbows = [], [], [], []
    for sx in (-0.1, 0.1):
        h = _pivot(name + "_hip", (sx, 0, 0.92), r)
        mk("leg", name + "_th", (0, 0, 0), (0.17, 0.19, 0.46), pants, parent=h)
        k = _pivot(name + "_knee", (0, 0, -0.46), h)
        mk("leg", name + "_sh", (0, 0, 0), (0.14, 0.16, 0.44), pants, parent=k)
        mk("cube", name + "_shoe", (0, 0.05, -0.47), (0.14, 0.3, 0.09), M["shoe"], parent=k)
        hips.append(h)
        knees.append(k)
    mk("cube", name + "_pelvis", (0, 0, 0.95), (0.36, 0.21, 0.2), pants, parent=r)
    mk("cube", name + "_torso", (0, 0, 1.22), (0.40, 0.23, 0.55), shirt, parent=r)
    mk("cyl", name + "_neck", (0, 0, 1.53), (0.1, 0.1, 0.1), skin, parent=r)
    head = _pivot(name + "_headp", (0, 0, 1.58), r)
    mk("sph", name + "_head", (0, 0, 0.12), (0.2, 0.23, 0.25), skin, parent=head)
    mk("sph", name + "_hair", (0, -0.02, 0.17), (0.215, 0.245, 0.2), hair, parent=head)
    if gender == "F":
        mk("cube", name + "_hair2", (0, -0.1, 0.0), (0.2, 0.08, 0.28), hair, parent=head)
    if HIGH_DETAIL_PEOPLE:
        for ex in (-0.05, 0.05):
            mk("sph", name + "_eye", (ex, 0.105, 0.13), (0.035, 0.025, 0.035), M["eye"], parent=head)
        mk("cube", name + "_nose", (0, 0.12, 0.09), (0.03, 0.04, 0.04), skin, parent=head)
    for sx in (-0.26, 0.26):
        s = _pivot(name + "_shd", (sx, 0, 1.43), r)
        mk("leg", name + "_ua", (0, 0, 0), (0.1, 0.11, 0.28), shirt, parent=s)
        e = _pivot(name + "_elb", (0, 0, -0.28), s)
        mk("leg", name + "_fa", (0, 0, 0), (0.085, 0.09, 0.26), skin, parent=e)
        if HIGH_DETAIL_PEOPLE:
            mk("sph", name + "_hand", (0, 0, -0.27), (0.09, 0.09, 0.09), skin, parent=e)
        shoulders.append(s)
        elbows.append(e)
    if luggage:
        mk("cube", name + "_bag", (0.5, 0.12, 0.33), (0.4, 0.25, 0.65), M["luggage"], parent=r)
    if backpack:
        mk("cube", name + "_pack", (0, -0.2, 1.25), (0.32, 0.16, 0.42), M["bag"], parent=r)
    if seated:
        r.location.z = pos[2] - 0.40
        for h in hips:
            h.rotation_euler.x = pi / 2
        for k in knees:
            k.rotation_euler.x = -pi / 2
    nm = random.choice(NAMES_F if gender == "F" else NAMES_M)
    title = {"agent": "Agent ", "guard": "Officer "}.get(role, "")
    d = {"root": r, "hips": hips, "knees": knees, "shoulders": shoulders, "elbows": elbows,
         "head": head, "walker": walker, "target": None, "wait": random.uniform(0, 3),
         "speed": random.uniform(0.9, 1.5), "phase": random.uniform(0, 6), "role": role,
         "gender": gender, "dname": title + nm, "talk_t": 0.0, "face": None, "seated": seated,
         "base_z": r.location.z, "vrate": random.uniform(-1, 2), "vpitch": random.randint(35, 65),
         "li": -1, "last_say": 0.0}
    if register:
        NPCS.append(d)
    return d


def turn_toward(r, ang, rate, dt):
    cur = r.rotation_euler.z
    diff = (ang - cur + pi) % (2 * pi) - pi
    r.rotation_euler.z = cur + max(-rate * dt, min(rate * dt, diff))


def pose_walk(d, phase, amp):
    s, c = sin(phase), cos(phase)
    d["hips"][0].rotation_euler.x = s * 0.6 * amp
    d["hips"][1].rotation_euler.x = -s * 0.6 * amp
    d["knees"][0].rotation_euler.x = -max(0.0, c) * 0.9 * amp
    d["knees"][1].rotation_euler.x = -max(0.0, -c) * 0.9 * amp
    d["shoulders"][0].rotation_euler.x = -s * 0.5 * amp
    d["shoulders"][1].rotation_euler.x = s * 0.5 * amp
    d["elbows"][0].rotation_euler.x = 0.2 + 0.4 * amp * max(0.0, -s)
    d["elbows"][1].rotation_euler.x = 0.2 + 0.4 * amp * max(0.0, s)
    d["head"].rotation_euler.z = 0.0
    d["root"].location.z = d["base_z"] + abs(s) * 0.035 * amp


def pose_idle(d, t):
    ph = d["phase"]
    if not d["seated"]:
        for h in d["hips"]:
            h.rotation_euler.x = 0.0
        for k in d["knees"]:
            k.rotation_euler.x = 0.0
    for i, s in enumerate(d["shoulders"]):
        s.rotation_euler.x = 0.04 * sin(t * 1.3 + ph + i)
    for e in d["elbows"]:
        e.rotation_euler.x = 0.12
    d["head"].rotation_euler.z = 0.35 * sin(t * 0.4 + ph)
    d["head"].rotation_euler.x = 0.0
    d["root"].location.z = d["base_z"]


def pose_talk(d, t):
    pose_idle(d, t)
    d["shoulders"][1].rotation_euler.x = -0.9 + 0.3 * sin(t * 5.0 + d["phase"])
    d["elbows"][1].rotation_euler.x = 1.1
    d["head"].rotation_euler.z = 0.0
    d["head"].rotation_euler.x = 0.06 * sin(t * 7.0)


# ---------------------------------------------------------------------
#  Build the world
# ---------------------------------------------------------------------
# Ground, road, apron, runway
mk("cube", "ground", (0, 40, -0.3), (500, 500, 0.4), M["grass"])
mk("cube", "road", (0, -15, -0.05), (240, 16, 0.2), M["asphalt"])
mk("cube", "sidewalk", (0, -5, 0.0), (90, 4, 0.2), M["concrete"])
mk("cube", "apron", (0, 65, -0.05), (240, 70, 0.2), M["concrete"])
mk("cube", "runway", (0, 125, -0.05), (400, 28, 0.2), M["asphalt"])
for i in range(-19, 20):
    mk("cube", "rwy_mark", (i * 10, 125, 0.06), (4, 0.5, 0.02), M["marking"])
for i in range(-11, 12):
    mk("cube", "lane_mark", (i * 6, -15, 0.06), (3, 0.2, 0.02), M["marking"])
for i in range(-5, 6):
    mk("cube", "taxi_mark", (i * 16, 95, 0.06), (6, 0.3, 0.02), M["t_yellow"])

# Terminal shell
mk("cube", "floor", (0, 15, -0.1), (80, 30, 0.2), M["floor"])
mk("cube", "roof", (0, 15, 12.3), (83, 33, 0.6), M["roof"])
for sx in (-1, 1):
    mk("cube", "sidewall", (sx * 40.2, 15, 6), (0.5, 30.5, 12), M["wall"])


def facade(y, with_sign):
    for sx in (-1, 1):
        mk("cube", "glass", (sx * 21.75, y, 5), (36.5, 0.15, 10), M["glass"])
    mk("cube", "glass_header", (0, y, 6.8), (7, 0.15, 6.4), M["glass"])
    mk("cube", "beam", (0, y, 10.4), (81, 0.5, 0.8), M["metal"])
    mk("cube", "sill", (0, y, 0.15), (81, 0.5, 0.3), M["metal"])
    for i in range(-10, 11):
        x = i * 4
        if abs(x) < 3.7:
            continue
        mk("cube", "mullion", (x, y, 5), (0.25, 0.3, 10), M["metal"])
    for xx in (-3.6, 3.6):
        mk("cube", "doorframe", (xx, y, 1.9), (0.2, 0.35, 3.8), M["metal"])
    panels = []
    for sg in (-1, 1):
        p = mk("cube", "door", (sg * 1.75, y, 1.8), (3.4, 0.08, 3.6), M["doorglass"])
        panels.append((p, sg * 1.75, sg))
    DOORS.append({"y": y, "panels": panels, "open": 0.0})


DOORS = []
facade(0, True)
facade(30, False)

# Front sign + plane icon + canopy
mk("cube", "frontsign", (0, -0.6, 11.0), (27, 0.8, 2.6), M["signbg"])
text("INTERNATIONAL AIRPORT", (2.5, -1.05, 11.0), 1.55, M["t_cyan"], extrude=0.08)
build_plane("icon", (-11.5, -1.3, 11.0), rz=0, s=0.13, body=M["t_white"], tail=M["t_cyan"], ry=-0.35)
mk("cube", "canopy", (0, -3.5, 5.2), (84, 7, 0.3), M["roof"])
for i in range(-5, 6):
    mk("cyl", "canopy_col", (i * 8, -6.5, 2.6), (0.4, 0.4, 5.2), M["column"])
    mk("cube", "canopy_light", (i * 8, -3.5, 5.0), (0.4, 5, 0.06), M["strip"])

# Columns + ceiling strips
for ix in range(-4, 5):
    for yy in (6, 24):
        mk("cyl", "column", (ix * 9, yy, 6), (0.9, 0.9, 12), M["column"])
for i in range(10):
    mk("cube", "ceil_light", (-36 + i * 8, 15, 11.9), (0.5, 26, 0.1), M["strip"])

# Tower
mk("cyl", "tower", (30, 38, 11), (4, 4, 22), M["concrete"])
mk("cyl", "tower_cab", (30, 38, 24), (9, 9, 2.6), M["towerglass"])
mk("cyl", "tower_roof", (30, 38, 25.8), (10.4, 10.4, 0.8), M["metal"])
mk("cyl", "tower_mast", (30, 38, 28.5), (0.25, 0.25, 5), M["metal"])
mk("sph", "tower_beacon", (30, 38, 31), (0.6, 0.6, 0.6), M["taill"])

# Garden / front
for x in range(-36, 37, 12):
    mk("cube", "planter", (x, -8.5, 0.15), (9, 2.2, 0.4), M["grass"])
    build_palm(x + 3, -8.5, 6 + random.uniform(-0.5, 1.0))
for x in range(-40, 41, 10):
    build_lamp(x, -22)

# Interior - signs
sign(0, 4.5, 8.3, 6.5, 1.2, "Departures", M["t_orange"], 0.7)
sign(-20, 10.0, 6.2, 9.0, 2.0, "Check-in", M["t_white"], 1.2)
sign(14, 15.5, 6.0, 8.0, 1.6, "Security Check", M["t_white"], 0.85)
sign(0, 28.3, 6.5, 6.0, 1.6, "Gate B1", M["t_yellow"], 1.0)

# Flight information board
mk("cube", "board", (0, 9, 5.4), (7.6, 0.25, 4.0), M["signbg"])
for sx in (-3.0, 3.0):
    mk("cyl", "rod", (sx, 9, 9.0), (0.08, 0.08, 3.4), M["metal"])
yb = 8.86
text("Flight Information", (0, yb, 7.0), 0.42, M["t_yellow"])
for txt, x in (("Flight", -3.3), ("To", -0.9), ("Status", 1.7)):
    text(txt, (x, yb, 6.35), 0.28, M["t_gray"], "LEFT")
rows = [("AI101", "New York", "On Time", "t_green"), ("BA203", "London", "On Time", "t_green"),
        ("AF317", "Paris", "Boarding", "t_yellow"), ("LH729", "Dubai", "On Time", "t_green")]
for i, (f, to, st, c) in enumerate(rows):
    z = 5.8 - i * 0.5
    text(f, (-3.3, yb, z), 0.3, M["t_white"], "LEFT")
    text(to, (-0.9, yb, z), 0.3, M["t_white"], "LEFT")
    text(st, (1.7, yb, z), 0.3, M[c], "LEFT")

# Check-in counters
for i in range(8):
    x = -34 + i * 4.5
    mk("cube", "counter", (x, 12.5, 0.5), (3.2, 1.1, 1.0), M["counter"])
    mk("cube", "countertop", (x, 12.4, 1.03), (3.3, 1.3, 0.08), M["countertop"])
    mk("cube", "monitor", (x, 12.7, 1.5), (0.7, 0.06, 0.45), M["screen"], (-0.2, 0, 0))
    build_person("agent%d" % i, (x, 13.6, 0), M["uniform"], pi)
    if i % 2 == 0:
        build_person("pax%d" % i, (x, 10.7, 0), random.choice(SHIRTS), 0, luggage=True)
for i in range(4):
    mk("cyl", "post", (-34 + i * 9, 9.2, 0.5), (0.1, 0.1, 1.0), M["metal"])

# Security area
for i, x in enumerate((8, 12, 16)):
    for sx in (-0.7, 0.7):
        mk("cube", "arch_p", (x + sx, 17, 1.1), (0.15, 0.5, 2.2), M["metal"])
    mk("cube", "arch_t", (x, 17, 2.25), (1.55, 0.5, 0.2), M["metal"])
    mk("cube", "belt", (x + 2, 17, 0.5), (1.0, 2.2, 0.9), M["dark"])
for x in range(6, 21, 2):
    mk("cyl", "post", (x, 14.2, 0.5), (0.08, 0.08, 1.0), M["metal"])
build_person("guard0", (9.2, 15.0, 0), M["uniform"], pi)
build_person("guard1", (13.2, 15.0, 0), M["uniform"], pi)

# Waiting area
for row in range(3):
    for col in range(6):
        build_bench(6 + col * 5.2, 21 + row * 2.4)
build_plant(-38, 4)
build_plant(38, 4)
build_plant(-38, 26)
build_plant(38, 26)
build_plant(1.5, 26)
for r_, c_ in ((0, 1), (0, 4), (1, 2), (1, 5), (2, 0), (2, 3), (2, 4)):
    build_person("sit%d%d" % (r_, c_), (6 + c_ * 5.2 + random.choice((-0.8, 0.8)), 21 + r_ * 2.4, 0),
                 random.choice(SHIRTS), 0, seated=True)

# Walking passengers
for i in range(NPC_COUNT):
    build_person("walker%d" % i, (random.uniform(-34, 34), random.uniform(4, 27), 0),
                 random.choice(SHIRTS), random.uniform(0, 6.28),
                 luggage=(i % 2 == 0), walker=True)

# Aeroplanes on the apron
build_plane("plane_A", (-30, 50, 2.8), pi / 2)
build_plane("plane_B", (28, 58, 2.8), -pi / 2 - 0.4)
build_plane("plane_C", (-70, 75, 2.8), 0.3)
build_plane("plane_D", (75, 72, 2.8), pi)
TAXI = build_plane("plane_TAXI", (-120, 95, 2.8), 0.0)

# Cars
build_car(-30, -12, "car0", 6.0)
build_car(10, -12, "car2", 5.0)
build_car(40, -18, "car1", -6.5)
build_car(-20, -18, "car0", -5.5)

# ---------------------------------------------------------------------
#  Lights, world, camera, render settings
# ---------------------------------------------------------------------
w = bpy.data.worlds.new("Dusk")
w.use_nodes = True
bg = w.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.03, 0.05, 0.18, 1)
bg.inputs[1].default_value = 1.0
scene.world = w

sd = bpy.data.lights.new("Moon", "SUN")
sd.energy = 1.2
sd.color = (0.55, 0.65, 1.0)
sun = bpy.data.objects.new("Moon", sd)
sun.rotation_euler = (math.radians(55), 0, math.radians(30))
COLL.objects.link(sun)
for i, x in enumerate(range(-30, 31, 12)):
    ld = bpy.data.lights.new("hall%d" % i, "POINT")
    ld.energy = 1800
    ld.color = (1.0, 0.92, 0.8)
    ld.use_shadow = False       # big performance win
    lo = bpy.data.objects.new("hall%d" % i, ld)
    lo.location = (x, 15, 10.5)
    COLL.objects.link(lo)

cam_data = bpy.data.cameras.new("WalkCam")
cam_data.type = "PERSP"          # PERSPECTIVE PROJECTION
cam_data.lens = 24
cam_data.clip_start = 0.1
cam_data.clip_end = 600
CAM = bpy.data.objects.new("WalkCam", cam_data)
COLL.objects.link(CAM)
scene.camera = CAM

try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "BLENDER_EEVEE"
for attr, val in (("use_bloom", True), ("use_gtao", True), ("use_ssr", True), ("use_soft_shadows", True),
                  ("taa_samples", 16)):
    try:
        setattr(scene.eevee, attr, val)
    except Exception:
        pass
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080

# ---------------------------------------------------------------------
#  Navigation (first-person) + animation
# ---------------------------------------------------------------------
G = {"x": 0.0, "y": -42.0, "z": 1.7, "yaw": 0.0, "pitch": 0.03}
VIEWS = {
    "ONE": (0, -45, 1.7, 0.0, 0.05),
    "TWO": (0, -25, 60, 0.0, -0.85),
    "THREE": (0, 2.5, 1.7, 0.0, 0.0),
    "FOUR": (4, 19, 1.7, -0.9, 0.0),
    "FIVE": (0, 36, 1.7, 0.0, 0.0),
}
WALLS = [(-40, 0, -3.6, 0), (3.6, 0, 40, 0), (-40, 30, -3.6, 30), (3.6, 30, 40, 30),
         (-40, 0, -40, 30), (40, 0, 40, 30)]


def _ccw(p, q, r):
    return (r[1] - p[1]) * (q[0] - p[0]) > (q[1] - p[1]) * (r[0] - p[0])


def _hit(a, b, c, d):
    return _ccw(a, c, d) != _ccw(b, c, d) and _ccw(a, b, c) != _ccw(a, b, d)


def blocked(x0, y0, x1, y1):
    if G["z"] > 12.5:
        return False
    for (ax, ay, bx, by) in WALLS:
        if _hit((x0, y0), (x1, y1), (ax, ay), (bx, by)):
            return True
    return False


def move_player(dx, dy):
    x, y = G["x"], G["y"]
    if not blocked(x, y, x + dx, y + dy):
        G["x"], G["y"] = x + dx, y + dy
    elif not blocked(x, y, x + dx, y):
        G["x"] = x + dx
    elif not blocked(x, y, x, y + dy):
        G["y"] = y + dy
    G["x"] = max(-200, min(200, G["x"]))
    G["y"] = max(-60, min(200, G["y"]))


def pick_target():
    return (random.uniform(-36, 36), random.uniform(3.5, 28))


def animate(dt):
    """Moves cars / taxiing plane / NPCs / sliding doors. Called every frame."""
    t = time.time()
    for c in CARS:
        r = c["root"]
        r.location.x += c["v"] * dt
        if r.location.x > 75:
            r.location.x = -75
        if r.location.x < -75:
            r.location.x = 75
    TAXI.location.x += 4.0 * dt
    if TAXI.location.x > 130:
        TAXI.location.x = -130
    gx, gy = G["x"], G["y"]
    pts = [(gx, gy)]
    for n in NPCS:
        r = n["root"]
        if n["walker"]:
            pts.append((r.location.x, r.location.y))
        if n["talk_t"] > 0:                       # in a conversation
            n["talk_t"] -= dt
            f = n["face"]
            if f:
                turn_toward(r, atan2(f[1] - r.location.y, f[0] - r.location.x) - pi / 2, 6.0, dt)
            pose_talk(n, t)
            continue
        if not n["walker"]:
            pose_idle(n, t)
            continue
        if (r.location.x - gx) ** 2 + (r.location.y - gy) ** 2 < 1.7:
            n["wait"] = max(n["wait"], 0.6)       # stop for the player
        if n["wait"] > 0:
            n["wait"] -= dt
            pose_idle(n, t)
            continue
        if n["target"] is None:
            n["target"] = pick_target()
        tx, ty = n["target"]
        dx, dy = tx - r.location.x, ty - r.location.y
        dist = sqrt(dx * dx + dy * dy)
        if dist < 0.3:
            n["target"] = None
            n["wait"] = random.uniform(1.0, 5.0)
            continue
        step = n["speed"] * dt
        r.location.x += dx / dist * step
        r.location.y += dy / dist * step
        turn_toward(r, atan2(dy, dx) - pi / 2, 7.0, dt)
        n["phase"] += dt * 6.0 * n["speed"]
        pose_walk(n, n["phase"], 0.8)
    for d in DOORS:
        near = any(abs(py - d["y"]) < 5 and abs(px) < 8 for px, py in pts)
        tgt = 3.3 if near else 0.0
        d["open"] += max(-2.5 * dt, min(2.5 * dt, tgt - d["open"]))
        for ob, bx, dr in d["panels"]:
            ob.location.x = bx + dr * d["open"]


def apply_camera():
    CAM.location = (G["x"], G["y"], G["z"])
    CAM.rotation_euler = (pi / 2 + G["pitch"], 0, G["yaw"])


HELP = ("WASD move | Mouse look | Wheel zoom | Shift run | Q/E down-up | "
        "1 Front 2 Top 3 Inside 4 Waiting 5 Apron | L performance | ESC exit")


class AIRPORT_OT_walk(bpy.types.Operator):
    bl_idname = "airport.walk"
    bl_label = "Start Walkthrough"

    def invoke(self, context, event):
        area = context.area
        if area is None or area.type != "VIEW_3D":
            self.report({"ERROR"}, "Run this from a 3D Viewport")
            return {"CANCELLED"}
        self.area = area
        self.space = area.spaces.active
        self.region = next(r for r in area.regions if r.type == "WINDOW")
        self.cx = self.region.x + self.region.width // 2
        self.cy = self.region.y + self.region.height // 2
        self.keys = set()
        self.last = time.time()
        G["tour"] = False
        try:
            if context.screen.is_animation_playing:
                bpy.ops.screen.animation_cancel(restore_frame=False)
        except Exception:
            pass
        self.old_overlay = self.space.overlay.show_overlays
        self.space.region_3d.view_perspective = "CAMERA"
        self.space.overlay.show_overlays = False
        self.set_shading(not START_IN_SOLID_MODE)
        scene.camera = CAM
        apply_camera()
        context.window.cursor_warp(self.cx, self.cy)
        context.window.cursor_modal_set("NONE")
        context.workspace.status_text_set(HELP)
        wm = context.window_manager
        self._timer = wm.event_timer_add(1 / 60, window=context.window)
        wm.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def set_shading(self, rich):
        sh = self.space.shading
        if rich:
            sh.type = "MATERIAL"
            for a in ("use_scene_lights", "use_scene_world"):
                try:
                    setattr(sh, a, True)
                except Exception:
                    pass
        else:
            sh.type = "SOLID"
            sh.color_type = "MATERIAL"
        self.rich = rich

    def modal(self, context, event):
        et, ev = event.type, event.value
        if et in {"ESC", "RIGHTMOUSE"}:
            return self.finish(context)
        if et == "TIMER":
            self.tick(context)
            return {"RUNNING_MODAL"}
        if et == "MOUSEMOVE":
            dx, dy = event.mouse_x - self.cx, event.mouse_y - self.cy
            if dx or dy:
                G["yaw"] -= dx * 0.0022
                G["pitch"] = max(-1.45, min(1.45, G["pitch"] + dy * 0.0022))
                context.window.cursor_warp(self.cx, self.cy)
            return {"RUNNING_MODAL"}
        if et in {"WHEELUPMOUSE", "WHEELINMOUSE"}:
            CAM.data.lens = min(80, CAM.data.lens + 2)
        elif et in {"WHEELDOWNMOUSE", "WHEELOUTMOUSE"}:
            CAM.data.lens = max(14, CAM.data.lens - 2)
        elif ev == "PRESS":
            if et in VIEWS:
                G["x"], G["y"], G["z"], G["yaw"], G["pitch"] = VIEWS[et]
            elif et == "L":
                self.set_shading(not self.rich)
            else:
                self.keys.add(et)
        elif ev == "RELEASE":
            self.keys.discard(et)
        return {"RUNNING_MODAL"}

    def tick(self, context):
        now = time.time()
        dt = min(now - self.last, 0.1)
        self.last = now
        k = self.keys
        spd = (13.0 if "LEFT_SHIFT" in k else 4.5) * dt
        fx, fy = -sin(G["yaw"]), cos(G["yaw"])
        rx, ry = cos(G["yaw"]), sin(G["yaw"])
        mx = my = 0.0
        if "W" in k: mx += fx; my += fy
        if "S" in k: mx -= fx; my -= fy
        if "D" in k: mx += rx; my += ry
        if "A" in k: mx -= rx; my -= ry
        n = sqrt(mx * mx + my * my)
        if n > 0:
            move_player(mx / n * spd, my / n * spd)
        if "E" in k: G["z"] = min(90, G["z"] + spd)
        if "Q" in k: G["z"] = max(1.7, G["z"] - spd)
        apply_camera()
        animate(dt)

    def finish(self, context):
        context.window_manager.event_timer_remove(self._timer)
        context.window.cursor_modal_restore()
        context.workspace.status_text_set(None)
        self.space.overlay.show_overlays = self.old_overlay
        return {"FINISHED"}


# ---------------------------------------------------------------------
#  GUIDED WALK: automatic first-person tour (keyframed camera)
#  Plays in the viewport and can also be rendered to an MP4 video.
# ---------------------------------------------------------------------
# (x, y, eye height, yaw, pitch)   yaw>0 turns left, yaw<0 turns right
TOUR_POINTS = [
    (0, -45, 1.7, 0.0, 0.05),     # outside, front view
    (0, -14, 1.7, 0.0, 0.08),     # walk toward the entrance
    (0, -2, 1.7, 0.0, 0.05),      # automatic doors open
    (0, 7, 1.7, 0.0, 0.0),        # inside the hall
    (-12, 9, 1.7, 0.55, 0.0),     # look at the check-in counters
    (-24, 9, 1.7, 0.25, 0.0),
    (-6, 10, 1.7, -0.35, 0.0),    # turn back to the flight board
    (8, 12, 1.7, -0.35, 0.0),     # toward security
    (14, 19, 1.7, -0.9, 0.0),     # waiting area
    (6, 19.5, 1.7, 0.1, 0.0),
    (0, 26, 1.7, 0.0, 0.0),       # boarding gate B1
    (0, 38, 1.7, 0.0, 0.0),       # out to the apron (back doors open)
    (0, 44, 1.7, -0.7, 0.03),     # look at the aeroplanes
]
TOUR_CAM = None


def build_tour():
    global TOUR_CAM
    if TOUR_CAM is None or TOUR_CAM.name not in bpy.data.objects:
        TOUR_CAM = bpy.data.objects.new("TourCam", cam_data)
        COLL.objects.link(TOUR_CAM)
    TOUR_CAM.animation_data_clear()
    ed = bpy.context.preferences.edit
    old = ed.keyframe_new_interpolation_type
    ed.keyframe_new_interpolation_type = "LINEAR"
    frame, prev = 1, None
    for p in TOUR_POINTS:
        if prev is not None:
            d = sqrt((p[0] - prev[0]) ** 2 + (p[1] - prev[1]) ** 2)
            frame += int(max(40, d / 1.6 * 24))      # about 1.6 m/s walking speed
        TOUR_CAM.location = (p[0], p[1], p[2])
        TOUR_CAM.rotation_euler = (pi / 2 + p[4], 0, p[3])
        TOUR_CAM.keyframe_insert("location", frame=frame)
        TOUR_CAM.keyframe_insert("rotation_euler", frame=frame)
        prev = p
    ed.keyframe_new_interpolation_type = old
    scene.frame_start, scene.frame_end = 1, frame
    r = scene.render
    r.fps = 24
    r.resolution_x, r.resolution_y = 1280, 720
    try:
        r.image_settings.file_format = "FFMPEG"
        r.ffmpeg.format = "MPEG4"
        r.ffmpeg.codec = "H264"
        r.filepath = "//airport_walk.mp4"
    except Exception:
        pass


def _tour_frame(scn, *args):
    """Runs on every frame (playback AND render): moves people, cars, doors."""
    if G.get("tour") and TOUR_CAM is not None:
        loc = TOUR_CAM.location
        G["x"], G["y"], G["z"] = loc.x, loc.y, loc.z
        animate(1 / 24)


bpy.app.handlers.frame_change_post[:] = [
    h for h in bpy.app.handlers.frame_change_post if getattr(h, "__name__", "") != "_tour_frame"]
bpy.app.handlers.frame_change_post.append(_tour_frame)


class AIRPORT_OT_tour(bpy.types.Operator):
    bl_idname = "airport.tour"
    bl_label = "Play Guided Walk"

    def execute(self, context):
        build_tour()
        G["tour"] = True
        scene.camera = TOUR_CAM
        area = context.area
        if area is not None and area.type == "VIEW_3D":
            sp = area.spaces.active
            sp.region_3d.view_perspective = "CAMERA"
            sp.overlay.show_overlays = False
            sp.shading.type = "SOLID" if START_IN_SOLID_MODE else "MATERIAL"
            if sp.shading.type == "MATERIAL":
                for a in ("use_scene_lights", "use_scene_world"):
                    try:
                        setattr(sp.shading, a, True)
                    except Exception:
                        pass
            else:
                sp.shading.color_type = "MATERIAL"
        scene.frame_set(1)
        if not context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()
        return {"FINISHED"}


# =====================================================================
#  GTA-STYLE GAME MODE: playable character, third-person camera,
#  talking NPCs with voice, PA announcements, radar, mission
# =====================================================================
import subprocess, shutil, sys, textwrap, re
import gpu, blf
from gpu_extras.batch import batch_for_shader

NPC_BY_NAME = {d["root"].name: d for d in NPCS}

# ---------------- collision obstacles (2D) ----------------
OBST_BOX = []      # (x0, y0, x1, y1)
OBST_CIRC = []     # (x, y, radius)
for _i in range(8):
    _x = -34 + _i * 4.5
    OBST_BOX.append((_x - 1.7, 11.8, _x + 1.7, 13.2))
for _row in range(3):
    for _col in range(6):
        _x, _y = 6 + _col * 5.2, 21 + _row * 2.4
        OBST_BOX.append((_x - 1.9, _y - 0.5, _x + 1.9, _y + 0.5))
for _ix in range(-4, 5):
    for _yy in (6, 24):
        OBST_CIRC.append((_ix * 9, _yy, 0.5))
for _x in (8, 12, 16):
    OBST_BOX.append((_x + 1.5, 15.8, _x + 2.5, 18.2))
    for _sx in (-0.7, 0.7):
        OBST_BOX.append((_x + _sx - 0.1, 16.7, _x + _sx + 0.1, 17.3))
for _p in ((-38, 4), (38, 4), (-38, 26), (38, 26), (1.5, 26)):
    OBST_CIRC.append((_p[0], _p[1], 0.7))
for _x in range(-36, 37, 12):
    OBST_CIRC.append((_x + 3, -8.5, 0.45))
OBST_CIRC.append((30, 38, 2.6))
for (_px, _py, _rz) in ((-30, 50, pi / 2), (28, 58, -pi / 2 - 0.4), (-70, 75, 0.3), (75, 72, pi)):
    for _k in range(-17, 18, 3):
        OBST_CIRC.append((_px + _k * cos(_rz), _py + _k * sin(_rz), 2.2))
for _n in NPCS:
    if not _n["walker"] and not _n["seated"]:
        OBST_CIRC.append((_n["root"].location.x, _n["root"].location.y, 0.4))


def hit_obstacle(x, y, r=0.35):
    for x0, y0, x1, y1 in OBST_BOX:
        if x0 - r < x < x1 + r and y0 - r < y < y1 + r:
            return True
    for cx, cy, cr in OBST_CIRC:
        if (x - cx) ** 2 + (y - cy) ** 2 < (cr + r) ** 2:
            return True
    return False


# ---------------- the playable character ----------------
START_POS = (0.0, -38.0)
P = {"x": START_POS[0], "y": START_POS[1], "z": 0.0, "vz": 0.0, "cyaw": 0.0, "cpitch": 0.22,
     "cdist": 4.2, "phase": 0.0, "speed": 0.0, "face": None, "face_t": 0.0}
PLAYER = build_person("Player", (P["x"], P["y"], 0), M["player_jacket"], 0.0, register=False,
                      skin=SKINS[1], hair=HAIRS[0], pants=PANTS_MATS[3], gender="M", backpack=True)
MARKER = mk("cone", "objective_marker", (0, 0, -50), (0.7, 0.7, 1.1), M["marker"], (pi, 0, 0))


def player_move(dx, dy):
    x, y = P["x"], P["y"]
    nx, ny = x + dx, y + dy
    if not blocked(x, y, nx, ny) and not hit_obstacle(nx, ny):
        P["x"], P["y"] = nx, ny
        return
    if not blocked(x, y, nx, y) and not hit_obstacle(nx, y):
        x = nx
    if not blocked(x, y, x, ny) and not hit_obstacle(x, ny):
        y = ny
    P["x"], P["y"] = x, y


def update_player_camera():
    yaw, pit, dist = P["cyaw"], P["cpitch"], P["cdist"]
    px = P["x"] + cos(yaw) * 0.5          # over-the-shoulder offset
    py = P["y"] + sin(yaw) * 0.5
    pz = P["z"] + 1.6
    bx, by = sin(yaw), -cos(yaw)           # unit vector pointing behind the camera
    d = dist
    cx = cy = 0.0
    for _ in range(8):                     # pull the camera in if a wall is behind us
        cx, cy = px + bx * d * cos(pit), py + by * d * cos(pit)
        if not blocked(px, py, cx, cy):
            break
        d *= 0.82
    CAM.location = (cx, cy, max(0.3, pz + sin(pit) * d))
    CAM.rotation_euler = (pi / 2 - pit, 0, yaw)


# ---------------- voice (text-to-speech) ----------------
VOICE = {"proc": None, "warned": False}
_SPEECH_FIX = [("AI101", "A I one oh one"), ("BA203", "B A two oh three"),
               ("AF317", "A F three one seven"), ("LH729", "L H seven two nine"),
               ("B1", "B one")]


def to_speech(t):
    for a, b in _SPEECH_FIX:
        t = t.replace(a, b)
    return re.sub(r'["`$]', "", t)


def voice_busy():
    p = VOICE["proc"]
    return p is not None and p.poll() is None


def stop_voice():
    p = VOICE["proc"]
    if p is not None and p.poll() is None:
        try:
            p.terminate()
        except Exception:
            pass


def speak(text, gender="F", rate=0.0, pitch=50, interrupt=False):
    """Speaks with the voices built into your operating system (no downloads needed)."""
    if not VOICE_ON:
        return False
    if voice_busy():
        if not interrupt:
            return False
        stop_voice()
    sp = to_speech(text)
    try:
        if sys.platform.startswith("win"):
            ps = ("Add-Type -AssemblyName System.Speech;"
                  "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
                  "$s.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::%s);"
                  "$s.Rate=%d;$s.Speak('%s')") % ("Female" if gender == "F" else "Male",
                                                  int(rate), sp.replace("'", "''"))
            VOICE["proc"] = subprocess.Popen(["powershell", "-NoProfile", "-Command", ps],
                                             creationflags=0x08000000)
        elif sys.platform == "darwin":
            VOICE["proc"] = subprocess.Popen(["say", "-v", "Samantha" if gender == "F" else "Alex",
                                              "-r", str(int(175 + rate * 8)), sp])
        else:
            exe = shutil.which("espeak-ng") or shutil.which("espeak")
            if exe:
                VOICE["proc"] = subprocess.Popen([exe, "-v", "en-us+" + ("f3" if gender == "F" else "m3"),
                                                  "-s", str(int(150 + rate * 8)), "-p", str(int(pitch)), sp])
            elif shutil.which("spd-say"):
                VOICE["proc"] = subprocess.Popen(["spd-say", "-w", sp])
            else:
                if not VOICE["warned"]:
                    print("No text-to-speech found. On Linux run: sudo apt install espeak-ng")
                    VOICE["warned"] = True
                return False
        return True
    except Exception as e:
        print("Voice error:", e)
        return False


SUB = {"who": "", "text": "", "until": 0.0, "col": (1.0, 0.85, 0.3, 1.0)}


def say_line(who, text, gender="F", rate=0.0, pitch=50, col=(1.0, 0.85, 0.3, 1.0), interrupt=False):
    speak(text, gender, rate, pitch, interrupt)
    SUB.update(who=who, text=text, until=time.time() + max(3.0, len(text) * 0.065), col=col)


LINES = {
    "agent": ["Next passenger, please.", "Please keep your luggage with you at all times.",
              "Have a pleasant flight!", "Your flight is on time. Boarding starts shortly."],
    "guard": ["Please keep moving.", "No liquids over one hundred millilitres, please.",
              "Have your boarding pass ready.", "Thank you. Move along, please."],
    "pax": ["Sorry, I am running late for my flight!", "Gate B1 is just past security.",
            "Nice airport, isn't it?", "I could not find my passport... oh, here it is!"],
    "sitter": ["Shh, I am on a call.", "I have been waiting for two hours.",
               "Could you keep it down, please?", "Is this the flight to London?"],
}
LINES["walker"] = LINES["pax"] + ["My flight to Dubai is delayed again.", "Sorry, I do not work here."]
AMBIENT = {
    "agent": ["Next passenger, please.", "Do you have any bags to check?"],
    "guard": ["Please step forward.", "Remove your belt and watch, please."],
    "pax": ["Where is my boarding pass?", "I hope the flight is on time."],
    "walker": ["Which way is the gate?", "I need a coffee before boarding.", "Excuse me, sorry!",
               "Are we late?"],
    "sitter": ["Yes, I am at the airport now.", "Yes, boarding soon. Love you, bye.",
               "The flight is delayed again."],
}
PA_MSGS = [
    "Attention please. Flight AI101 to New York is now boarding at Gate B1.",
    "Flight BA203 to London is on time. Passengers, please proceed to check-in.",
    "Passengers on flight AF317 to Paris, this is the final boarding call at Gate B1.",
    "Please do not leave your luggage unattended. Unattended bags will be removed.",
    "Flight LH729 to Dubai is on time and will depart on schedule.",
]
AGENT_FIRST = ("Good evening, and welcome to International Airport. Passport and ticket, please. "
               "Thank you. Here is your boarding pass for flight AI101 to New York, Gate B1. "
               "Please proceed to the Security Check.")
GUARD_FIRST = ("Please place your bag and laptop in the tray and remove your belt. "
               "Thank you, you are cleared. Gate B1 is straight ahead. Enjoy your flight!")

# ---------------- mission ----------------
MISSION = {"step": 0, "done_t": 0.0}
OBJ_TEXT = ["Talk to the check-in agent  [E]", "Go to the Security Check",
            "Talk to the security officer  [E]", "Walk to Gate B1 and board your flight",
            "Mission complete"]
HUD = {"help_until": 0.0, "msg": "", "msg_until": 0.0}
AMB = {"next": 0.0}
PA = {"next": 0.0, "i": 0}


def hud_msg(text, sec=3.5):
    HUD["msg"], HUD["msg_until"] = text, time.time() + sec


def objective_target():
    s = MISSION["step"]
    if s == 0:
        r = NPC_BY_NAME["agent3"]["root"]
        return (r.location.x, r.location.y)
    if s == 1:
        return (11.0, 11.5)
    if s == 2:
        r = NPC_BY_NAME["guard0"]["root"]
        return (r.location.x, r.location.y)
    if s == 3:
        return (0.0, 27.0)
    return None


def nearest_npc(maxd):
    best, bd = None, maxd
    for n in NPCS:
        r = n["root"]
        d = sqrt((r.location.x - P["x"]) ** 2 + (r.location.y - P["y"]) ** 2)
        if d < bd:
            best, bd = n, d
    return best


def interact(now):
    n = nearest_npc(3.2)
    if n is None:
        return
    name = n["root"].name
    step = MISSION["step"]
    if name == "agent3" and step == 0:
        text = AGENT_FIRST
        MISSION["step"] = 1
        hud_msg("Boarding pass received  -  Objective updated")
    elif name == "guard0" and step == 2:
        text = GUARD_FIRST
        MISSION["step"] = 3
        hud_msg("Security cleared  -  Objective updated")
    else:
        pool = LINES[n["role"]]
        n["li"] = (n["li"] + 1) % len(pool)
        text = pool[n["li"]]
    say_line(n["dname"], text, n["gender"], n["vrate"], n["vpitch"], interrupt=True)
    n["face"] = (P["x"], P["y"])
    n["talk_t"] = max(5.0, SUB["until"] - now)
    r = n["root"]
    P["face"] = (r.location.x, r.location.y)
    P["face_t"] = 1.5


def game_update(dt, keys, now):
    # ---- player movement relative to the camera (like GTA) ----
    yaw = P["cyaw"]
    fx, fy = -sin(yaw), cos(yaw)
    rx, ry = cos(yaw), sin(yaw)
    mx = my = 0.0
    if "W" in keys: mx += fx; my += fy
    if "S" in keys: mx -= fx; my -= fy
    if "D" in keys: mx += rx; my += ry
    if "A" in keys: mx -= rx; my -= ry
    n = sqrt(mx * mx + my * my)
    sprint = "LEFT_SHIFT" in keys or "RIGHT_SHIFT" in keys
    root = PLAYER["root"]
    if n > 0:
        mx, my = mx / n, my / n
        target = 6.0 if sprint else 2.4
        P["speed"] += (target - P["speed"]) * min(1.0, dt * 10)
        player_move(mx * P["speed"] * dt, my * P["speed"] * dt)
        turn_toward(root, atan2(my, mx) - pi / 2, 14.0, dt)
    else:
        P["speed"] *= max(0.0, 1 - dt * 12)
    if P["face_t"] > 0:
        P["face_t"] -= dt
        f = P["face"]
        if f and n == 0:
            turn_toward(root, atan2(f[1] - P["y"], f[0] - P["x"]) - pi / 2, 8.0, dt)
    P["vz"] -= 12.0 * dt
    P["z"] += P["vz"] * dt
    if P["z"] <= 0:
        P["z"], P["vz"] = 0.0, 0.0
    root.location.x, root.location.y = P["x"], P["y"]
    PLAYER["base_z"] = P["z"]
    root.location.z = P["z"]
    if P["speed"] > 0.15:
        P["phase"] += dt * (2.0 + P["speed"] * 1.5)
        pose_walk(PLAYER, P["phase"], min(1.5, 0.35 + P["speed"] * 0.2))
    else:
        pose_idle(PLAYER, now)
    update_player_camera()
    G["x"], G["y"], G["z"] = P["x"], P["y"], 0.0
    animate(dt)

    # ---- mission logic ----
    step = MISSION["step"]
    if step == 1 and (P["x"] - 11.0) ** 2 + (P["y"] - 11.5) ** 2 < 16:
        MISSION["step"] = 2
        hud_msg("Objective updated")
    elif step == 3 and (P["x"]) ** 2 + (P["y"] - 27.0) ** 2 < 12:
        MISSION["step"] = 4
        MISSION["done_t"] = now + 6.0
        say_line("PA Announcement", "Boarding complete. Have a pleasant flight with us!", "F",
                 col=(0.6, 0.85, 1.0, 1.0), interrupt=True)
    tg = objective_target()
    if tg:
        MARKER.location = (tg[0], tg[1], 2.7 + 0.2 * sin(now * 3.0))
        MARKER.rotation_euler = (pi, 0, now * 2.0)
    else:
        MARKER.location = (0, 0, -50)

    # ---- ambient chatter, "watch it!" reactions, PA announcements ----
    free = now > SUB["until"] and not voice_busy()
    for nn in NPCS:
        r = nn["root"]
        if (nn["walker"] and P["speed"] > 4.0 and now > nn["last_say"] + 8 and free
                and (r.location.x - P["x"]) ** 2 + (r.location.y - P["y"]) ** 2 < 2.0):
            nn["last_say"] = now
            nn["face"] = (P["x"], P["y"])
            nn["talk_t"] = 2.5
            say_line(nn["dname"], "Hey! Watch where you are going!", nn["gender"], nn["vrate"],
                     nn["vpitch"], col=(1.0, 0.45, 0.35, 1.0), interrupt=True)
            free = False
            break
    if free and now > AMB["next"]:
        AMB["next"] = now + random.uniform(4, 8)
        near = [nn for nn in NPCS if nn["talk_t"] <= 0 and
                (nn["root"].location.x - P["x"]) ** 2 + (nn["root"].location.y - P["y"]) ** 2 < 49]
        if near:
            nn = random.choice(near)
            nn["talk_t"] = 3.0
            nn["face"] = None
            say_line(nn["dname"], random.choice(AMBIENT[nn["role"]]), nn["gender"], nn["vrate"],
                     nn["vpitch"], col=(0.85, 0.85, 0.85, 1.0))
            free = False
    if free and now > PA["next"]:
        PA["next"] = now + 45.0
        say_line("PA Announcement", PA_MSGS[PA["i"] % len(PA_MSGS)], "F", -1, 50, col=(0.6, 0.85, 1.0, 1.0))
        PA["i"] += 1


# ---------------- HUD (drawn on top of the 3D view) ----------------
def _font(size):
    try:
        blf.size(0, size)
    except TypeError:
        blf.size(0, size, 72)


def hud_text(txt, x, y, size=18, col=(1, 1, 1, 1), center=False):
    _font(size)
    w, h = blf.dimensions(0, txt)
    if center:
        x -= w / 2
    blf.color(0, 0, 0, 0, 0.85)
    blf.position(0, x + 1.5, y - 1.5, 0)
    blf.draw(0, txt)
    blf.color(0, *col)
    blf.position(0, x, y, 0)
    blf.draw(0, txt)
    return w, h


def _shader():
    try:
        return gpu.shader.from_builtin("UNIFORM_COLOR")
    except Exception:
        return gpu.shader.from_builtin("2D_UNIFORM_COLOR")


def _draw(sh, prim, pts, col, size=None, width=None):
    batch = batch_for_shader(sh, prim, {"pos": pts})
    sh.bind()
    sh.uniform_float("color", col)
    if size:
        gpu.state.point_size_set(size)
    if width:
        gpu.state.line_width_set(width)
    batch.draw(sh)


def _rect(sh, x0, y0, x1, y1, col):
    _draw(sh, "TRIS", [(x0, y0), (x1, y0), (x1, y1), (x0, y0), (x1, y1), (x0, y1)], col)


def _clip(x0, y0, x1, y1, xmin, ymin, xmax, ymax):
    dx, dy = x1 - x0, y1 - y0
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x0 - xmin), (dx, xmax - x0), (-dy, y0 - ymin), (dy, ymax - y0)):
        if p == 0:
            if q < 0:
                return None
        else:
            r = q / p
            if p < 0:
                if r > t1:
                    return None
                t0 = max(t0, r)
            else:
                if r < t0:
                    return None
                t1 = min(t1, r)
    return (x0 + t0 * dx, y0 + t0 * dy, x0 + t1 * dx, y0 + t1 * dy)


def draw_hud():
    ctx = bpy.context
    region = ctx.region
    if region is None or not G.get("play") or ctx.area != G.get("play_area"):
        return
    W, H = region.width, region.height
    now = time.time()
    sh = _shader()
    gpu.state.blend_set("ALPHA")

    # --- radar (rotates with the camera, like GTA) ---
    S, R = 170, 45.0
    cx0, cy0 = W - 30 - S / 2, H - 70 - S / 2
    _rect(sh, cx0 - S / 2, cy0 - S / 2, cx0 + S / 2, cy0 + S / 2, (0, 0, 0, 0.55))
    yaw = P["cyaw"]
    fx, fy, rx, ry = -sin(yaw), cos(yaw), cos(yaw), sin(yaw)
    sc = (S / 2) / R

    def to_r(wx, wy):
        dx, dy = wx - P["x"], wy - P["y"]
        return cx0 + (dx * rx + dy * ry) * sc, cy0 + (dx * fx + dy * fy) * sc

    lines = []
    for (ax, ay, bx, by) in WALLS:
        p0, p1 = to_r(ax, ay), to_r(bx, by)
        c = _clip(p0[0], p0[1], p1[0], p1[1], cx0 - S / 2, cy0 - S / 2, cx0 + S / 2, cy0 + S / 2)
        if c:
            lines += [(c[0], c[1]), (c[2], c[3])]
    if lines:
        _draw(sh, "LINES", lines, (0.8, 0.8, 0.85, 0.9), width=2.0)
    half = S / 2 - 4
    dots = []
    for nn in NPCS:
        r = nn["root"]
        x, y = to_r(r.location.x, r.location.y)
        if abs(x - cx0) < half and abs(y - cy0) < half:
            dots.append((x, y))
    if dots:
        _draw(sh, "POINTS", dots, (1, 1, 1, 0.9), size=4)
    tg = objective_target()
    if tg:
        x, y = to_r(*tg)
        x = max(cx0 - half, min(cx0 + half, x))
        y = max(cy0 - half, min(cy0 + half, y))
        _draw(sh, "POINTS", [(x, y)], (1.0, 0.8, 0.0, 1.0), size=11)
    a = root_angle = PLAYER["root"].rotation_euler.z - yaw
    hx, hy = -sin(a), cos(a)
    tri = [(cx0 + 10 * hx, cy0 + 10 * hy),
           (cx0 - 4 * hx + 6 * hy, cy0 - 4 * hy - 6 * hx),
           (cx0 - 4 * hx - 6 * hy, cy0 - 4 * hy + 6 * hx)]
    _draw(sh, "TRIS", tri, (0.3, 1.0, 0.4, 1.0))
    _draw(sh, "LINE_LOOP", [(cx0 - S / 2, cy0 - S / 2), (cx0 + S / 2, cy0 - S / 2),
                            (cx0 + S / 2, cy0 + S / 2), (cx0 - S / 2, cy0 + S / 2)],
          (1, 1, 1, 0.9), width=2.0)

    # --- objective (top left) ---
    s = MISSION["step"]
    hud_text("OBJECTIVE", 30, H - 80, 14, (1.0, 0.8, 0.0, 1.0))
    hud_text(OBJ_TEXT[s], 30, H - 105, 22)
    if tg:
        d = sqrt((tg[0] - P["x"]) ** 2 + (tg[1] - P["y"]) ** 2)
        hud_text("%d m" % d, 30, H - 130, 16, (1.0, 0.8, 0.0, 1.0))
    if now < HUD["msg_until"]:
        hud_text(HUD["msg"], W / 2, H - 120, 24, (1.0, 0.9, 0.4, 1.0), center=True)

    # --- interaction prompt ---
    nn = nearest_npc(3.2)
    if nn is not None and now > SUB["until"]:
        hud_text("[E]  Talk to " + nn["dname"], W / 2, 150, 22, center=True)

    # --- subtitles ---
    if now < SUB["until"]:
        wrapped = textwrap.wrap(SUB["text"], 70)
        top = 70 + 26 * len(wrapped)
        _rect(sh, W / 2 - 440, 55, W / 2 + 440, top + 34, (0, 0, 0, 0.45))
        hud_text(SUB["who"], W / 2, top + 8, 20, SUB["col"], center=True)
        for i, ln in enumerate(wrapped):
            hud_text(ln, W / 2, top - 22 - 26 * i + 26, 20, center=True)

    # --- mission passed banner ---
    if s == 4 and now < MISSION["done_t"]:
        hud_text("MISSION PASSED", W / 2, H / 2 + 40, 72, (1.0, 0.8, 0.1, 1.0), center=True)
        hud_text("Flight AI101 to New York - boarding complete", W / 2, H / 2 - 10, 26, center=True)

    # --- controls help ---
    if now < HUD["help_until"]:
        for i, ln in enumerate(["WASD move   Mouse camera   Wheel zoom   Shift sprint   Space jump",
                                "E talk   R respawn   M mute voices   L performance mode   ESC exit"]):
            hud_text(ln, 30, 60 - 24 * i, 16, (0.9, 0.9, 0.9, 1.0))
    gpu.state.blend_set("NONE")


class AIRPORT_OT_play(bpy.types.Operator):
    bl_idname = "airport.play"
    bl_label = "Play (GTA style)"

    def invoke(self, context, event):
        area = context.area
        if area is None or area.type != "VIEW_3D":
            self.report({"ERROR"}, "Run this from a 3D Viewport")
            return {"CANCELLED"}
        self.area = area
        self.space = area.spaces.active
        self.region = next(r for r in area.regions if r.type == "WINDOW")
        self.cx = self.region.x + self.region.width // 2
        self.cy = self.region.y + self.region.height // 2
        self.keys = set()
        self.last = time.time()
        G["tour"] = False
        try:
            if context.screen.is_animation_playing:
                bpy.ops.screen.animation_cancel(restore_frame=False)
        except Exception:
            pass
        sp = self.space
        self.saved = {}
        for f in ("show_floor", "show_axis_x", "show_axis_y", "show_axis_z", "show_cursor",
                  "show_extras", "show_relationship_lines", "show_object_origins",
                  "show_outline_selected", "show_stats", "show_text"):
            if hasattr(sp.overlay, f):
                self.saved[("o", f)] = getattr(sp.overlay, f)
                setattr(sp.overlay, f, False)
        for f in ("show_gizmo", "show_region_ui", "show_region_toolbar"):
            if hasattr(sp, f):
                self.saved[("s", f)] = getattr(sp, f)
                setattr(sp, f, False)
        sp.region_3d.view_perspective = "CAMERA"
        self.set_shading(not START_IN_SOLID_MODE)
        scene.camera = CAM
        CAM.data.lens = 30
        G["play"], G["play_area"] = True, area
        now = time.time()
        HUD["help_until"] = now + 25
        PA["next"] = now + 20
        AMB["next"] = now + 6
        update_player_camera()
        context.window.cursor_warp(self.cx, self.cy)
        context.window.cursor_modal_set("NONE")
        context.workspace.status_text_set("ESC = exit")
        wm = context.window_manager
        self._timer = wm.event_timer_add(1 / 60, window=context.window)
        self._hud = bpy.types.SpaceView3D.draw_handler_add(draw_hud, (), "WINDOW", "POST_PIXEL")
        wm.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def set_shading(self, rich):
        sh = self.space.shading
        if rich:
            sh.type = "MATERIAL"
            for a in ("use_scene_lights", "use_scene_world"):
                try:
                    setattr(sh, a, True)
                except Exception:
                    pass
        else:
            sh.type = "SOLID"
            sh.color_type = "MATERIAL"
        self.rich = rich

    def modal(self, context, event):
        et, ev = event.type, event.value
        if et == "ESC" and ev == "PRESS":
            return self.finish(context)
        if et == "TIMER":
            now = time.time()
            dt = min(now - self.last, 0.1)
            self.last = now
            game_update(dt, self.keys, now)
            self.area.tag_redraw()
            return {"RUNNING_MODAL"}
        if et == "MOUSEMOVE":
            dx, dy = event.mouse_x - self.cx, event.mouse_y - self.cy
            if dx or dy:
                P["cyaw"] -= dx * 0.0025
                P["cpitch"] = max(-0.25, min(1.2, P["cpitch"] + dy * 0.0025))
                context.window.cursor_warp(self.cx, self.cy)
            return {"RUNNING_MODAL"}
        if et in {"WHEELUPMOUSE", "WHEELINMOUSE"}:
            P["cdist"] = max(1.5, P["cdist"] - 0.4)
        elif et in {"WHEELDOWNMOUSE", "WHEELOUTMOUSE"}:
            P["cdist"] = min(9.0, P["cdist"] + 0.4)
        elif ev == "PRESS":
            if et == "SPACE":
                if P["z"] <= 0.001:
                    P["vz"] = 4.5
            elif et == "E":
                if not event.is_repeat:
                    interact(time.time())
            elif et == "L":
                self.set_shading(not self.rich)
            elif et == "M":
                global VOICE_ON
                VOICE_ON = not VOICE_ON
                stop_voice()
                hud_msg("Voices ON" if VOICE_ON else "Voices OFF (subtitles only)", 2.0)
            elif et == "R":
                P["x"], P["y"], P["z"], P["vz"] = START_POS[0], START_POS[1], 0.0, 0.0
                P["cyaw"] = 0.0
            else:
                self.keys.add(et)
        elif ev == "RELEASE":
            self.keys.discard(et)
        return {"RUNNING_MODAL"}

    def finish(self, context):
        context.window_manager.event_timer_remove(self._timer)
        try:
            bpy.types.SpaceView3D.draw_handler_remove(self._hud, "WINDOW")
        except Exception:
            pass
        stop_voice()
        G["play"] = False
        context.window.cursor_modal_restore()
        context.workspace.status_text_set(None)
        for (kind, f), v in self.saved.items():
            try:
                setattr(self.space.overlay if kind == "o" else self.space, f, v)
            except Exception:
                pass
        self.area.tag_redraw()
        return {"FINISHED"}


class AIRPORT_PT_panel(bpy.types.Panel):
    bl_label = "Airport Walkthrough"
    bl_idname = "AIRPORT_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Airport"

    def draw(self, context):
        self.layout.operator("airport.play", icon="PLAY")
        self.layout.operator("airport.tour", icon="CAMERA_DATA")
        self.layout.operator("airport.walk", icon="VIEW_CAMERA")
        self.layout.label(text="Guided: Space = pause/play")
        self.layout.label(text="WASD move, mouse look")
        self.layout.label(text="Wheel zoom, Shift run")
        self.layout.label(text="1-5 viewpoints, L performance")
        self.layout.label(text="ESC to exit")


for cls in (AIRPORT_OT_walk, AIRPORT_OT_tour, AIRPORT_OT_play, AIRPORT_PT_panel):
    try:
        bpy.utils.register_class(cls)
    except Exception as e:
        print("register:", e)

apply_camera()


def _autostart():
    try:
        for win in bpy.context.window_manager.windows:
            for area in win.screen.areas:
                if area.type == "VIEW_3D":
                    region = next(r for r in area.regions if r.type == "WINDOW")
                    with bpy.context.temp_override(window=win, area=area, region=region):
                        if START_MODE == "PLAY":
                            bpy.ops.airport.play("INVOKE_DEFAULT")
                        elif START_MODE == "TOUR":
                            bpy.ops.airport.tour()
                        else:
                            bpy.ops.airport.walk("INVOKE_DEFAULT")
                    return None
    except Exception as e:
        print("Autostart failed - use N panel > Airport > Start Walkthrough:", e)
    return None


bpy.app.timers.register(_autostart, first_interval=0.6)
print("Airport terminal built. Walkthrough starting...")
