"""Checks for the level tools in this folder, on the demo pack only (no browser, no course art).

    python3 tools/levels/test_level_tools.py        (npm run test:tools; level2png needs Pillow)
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.normpath(os.path.join(HERE, "..", "..", "packs", "demo"))
ENV = dict(os.environ, DC_ASSET_PACKS=DEMO)
results = []


def check(what, ok, detail=""):
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {what}" + (f"  ({detail})" if detail and not ok else ""))


def tool(name, *args):
    return subprocess.run([sys.executable, os.path.join(HERE, name), *args], capture_output=True, text=True, env=ENV)


def level(name):
    return os.path.join(DEMO, "levels", name)


def ascii_map(name):
    """The map lines of level2ascii, without the empty margin around the map."""
    lines = [line for line in tool("level2ascii.py", level(name)).stdout.split("\n")[1:] if line.strip()]
    indent = min((len(line) - len(line.lstrip()) for line in lines), default=0)
    return [line[indent:].rstrip() for line in lines]


small, big = ascii_map("demo_raum.json"), ascii_map("demo32_raum.json")
check("level2ascii reads the demo level", any("H" in line for line in small) and any("#" in line for line in small),
      "\n".join(small))
check("level2ascii: the 32 px level reads as the same map", small == big, f"{small} vs {big}")

for name in ("demo_gang.json", "demo_raum.json", "demo32_raum.json"):
    run = tool("check_level.py", level(name))
    check(f"check_level: {name} has no errors", run.returncode == 0 and "FEHLER" not in run.stdout, run.stdout[-500:])
run = tool("check_level.py", level("demo_raum.json"), level("demo_gang.json"))
check("check_level: two different levels have different logic", run.returncode != 0 and "ANDERS" in run.stdout)

# a co-op hero and a variant region on the demo level: both tools know them
import json  # noqa: E402
with open(level("demo_raum.json"), encoding="utf-8") as f:
    data = json.load(f)
objects = next(layer for layer in data["layers"] if layer["type"] == "objectgroup")["objects"]
main = next(o for o in objects if o.get("name") == "MainCharacter")
tw = data["tilewidth"]
objects.append(dict(main, id=900, name="Hero2", x=main["x"] + tw))
objects.append({"id": 901, "name": "region1", "type": "Region", "x": main["x"], "y": main["y"] - 2 * tw,
                "width": 2 * tw, "height": tw, "visible": False})
extra = os.path.join(tempfile.mkdtemp(), "team.json")
with open(extra, "w", encoding="utf-8") as f:
    json.dump(data, f)
run = tool("check_level.py", extra)
check("check_level: a co-op hero is no second MainCharacter", "FEHLER" not in run.stdout and "Team-Level" in run.stdout,
      run.stdout[-500:])
check("check_level: a region nobody names is reported", "Region region1: kein Objekt" in run.stdout, run.stdout[-500:])
emitted = tool("level2ascii.py", "--emit", extra).stdout
check("level2ascii: the co-op hero is 2", any("2" in line and "H" in line for line in emitted.split("---")[1].split("\n")),
      emitted)

script = os.path.join(tempfile.mkdtemp(), "skript.py")
with open(script, "w", encoding="utf-8") as f:
    f.write(f"from dungeoncoder import Game\nhero = Game({level('demo_gang.json')!r}).get_hero()\n"
            "print('moved', hero.move())\n")
run = tool("run_sim.py", script)
check("run_sim runs a script in the simulator", "moved True" in run.stdout and "statistics" in run.stdout,
      run.stdout + run.stderr)

try:
    from PIL import Image
except ImportError:
    print("skip  level2png (no Pillow)")
else:
    out = os.path.join(tempfile.mkdtemp(), "raum.png")
    run = tool("level2png.py", level("demo32_raum.json"), out, "--scale", "1")
    size = None
    if run.returncode == 0:
        with Image.open(out) as img:
            size = img.size
    check("level2png: 15 x 10 cells of 32 px give 480 x 320", size == (480, 320), run.stdout + run.stderr)

# the engine rebuilds its own text-map styles from its recipes (api/python/dungeoncoder/packs/learn/:
# the CC0 worlds), and they come out as shipped
run = tool("learn_styles.py", "--check")
check("learn_styles: the engine's style packs are learned from its recipes as shipped",
      run.returncode == 0 and "style packs up to date" in run.stdout, run.stdout + run.stderr)

# asset packs without DC_ASSET_PACKS (api/python/dungeoncoder/sim.py, asset_pack_folders; like the extension's
# findAssetPacks): a dungeon-coder-assets with a pack.json in or above the current folder or the
# script's folder, nearest first; an explicitly set DC_ASSET_PACKS (also an empty one) wins
with tempfile.TemporaryDirectory() as root:
    root = os.path.realpath(root)
    def pack(folder, manifest=True):
        os.makedirs(folder, exist_ok=True)
        if manifest:
            with open(os.path.join(folder, "pack.json"), "w") as f:
                f.write('{"name": "x"}')
        return folder
    far = pack(os.path.join(root, "dungeon-coder-assets"))
    near = pack(os.path.join(root, "semester", "dungeon-coder-assets"))
    pack(os.path.join(root, "semester", "loesungen", "dungeon-coder-assets"), manifest=False)
    opened = os.path.join(root, "semester", "loesungen", "dc-03")
    os.makedirs(opened)
    script = os.path.join(opened, "zeige.py")
    with open(script, "w") as f:
        f.write("from dungeoncoder.sim import asset_pack_folders\nprint(asset_pack_folders())\n")
    api = os.path.normpath(os.path.join(HERE, "..", "..", "api", "python"))
    def packs(cwd, **env):
        e = {k: v for k, v in os.environ.items() if k != "DC_ASSET_PACKS"}
        e.update(env, PYTHONPATH=api)
        return subprocess.run([sys.executable, script], cwd=cwd, capture_output=True, text=True, env=e).stdout.strip()
    check("asset packs found in and above the current folder, nearest first", packs(opened) == str([near, far]), packs(opened))
    check("... and above the script's folder, from anywhere", packs(root + "/..") == str([near, far]), packs(root + "/.."))
    check("an empty DC_ASSET_PACKS means no packs, a set one is used as it is",
          packs(opened, DC_ASSET_PACKS="") == "[]" and packs(opened, DC_ASSET_PACKS=far) == str([far]))

# show_calls and show_sensing from the program: Game(..., show_calls=...) and the class variables
# Game.SHOW_CALLS / Game.SHOW_SENSING put them into the level the game gets (parameter before
# class variable before the level)
probe = r"""
import json, sys
import dungeoncoder
import dungeoncoder.dungeoncoder as dc
from dungeoncoder import Game
dungeoncoder.use_simulator()
sent, real = [], dc._simulated
def spy(client, fn, body=None, hero=None):
    if body is not None and fn.__module__.endswith('load_level'):
        sent.append({p['name']: p['value'] for p in body.to_dict().get('properties', []) or []
                     if p['name'] in ('show_calls', 'show_sensing')})
    return real(client, fn, body=body, hero=hero)
dc._simulated = spy
level = sys.argv[1]
Game(level)
Game(level, show_calls=True)
Game.SHOW_SENSING = False
Game(level)
Game(level, show_sensing=True)
print(json.dumps(sent))
"""
api = os.path.normpath(os.path.join(HERE, "..", "..", "api", "python"))
run = subprocess.run([sys.executable, "-c", probe, level("demo_raum.json")], capture_output=True, text=True,
                     env=dict(ENV, PYTHONPATH=api))
expected = [{}, {"show_calls": True}, {"show_sensing": False}, {"show_sensing": True}]
check("Game: show_calls/show_sensing as parameters and as Game.SHOW_CALLS/SHOW_SENSING reach the level",
      run.stdout.strip() == json.dumps(expected), run.stdout + run.stderr)

# the builder's look rules (T1q): free-standing wall blocks, the outer rim, details gathered around things
import learn_styles  # noqa: E402
am = learn_styles.asciimap
grid = [list(row) for row in ["#######", "#.....#", "#.##..#", "#.##..#", "#....##", "#######"]]
keep = [row[:] for row in grid]
changed = am.free_standing_blocks(grid, {(2, 2)})
check("builder: a free-standing 2 x 2 wall block becomes an obstacle, walls touching others stay",
      changed == [(2, 2), (2, 3), (3, 2), (3, 3)] and grid[4][5] == "#", f"{changed}")
check("builder: ... but only where the style has an obstacle picture of that size (a pillar stays a pillar)",
      am.free_standing_blocks(keep, {(3, 2)}) == [] and keep[2][2] == "#")
check("builder: the rim is a wall next to the outside, not an inner wall",
      am.is_rim(am.pattern([list("##"), list("#.")], 0, 0)) and not am.is_rim(am.pattern(
          [list("###"), list("###"), list("###")], 1, 1)))
pack = am.Pack()
pack.stacks[am.pattern([list("###")] * 3, 1, 1)][(("wall", "a.json", 1),)] = 1
rim_key = am.pattern([list("##"), list("#.")], 0, 0)
pack.rim[rim_key][(("wall", "a.json", 2),)] = 1
again = am.Pack.from_json(json.loads(json.dumps(pack.to_json())))
check("builder: a pack keeps its rim through JSON, and the rim field gets the rim's stack",
      again.rim == pack.rim and again.choose(rim_key, None, None, None, 0, rim=True) == (("wall", "a.json", 2),))
rows = ["#" * 22] + ["#" + "." * 20 + "#" for _ in range(10)] + ["#" * 22]
rows[5] = rows[5][:3] + "C" + rows[5][4:]
grid = [list(r) for r in rows]
terrain = [[am.base_terrain(ch) for ch in row] for row in grid]
layers = {"bg": {}, "floor": {}, "floor2": {}, "wall": {}, "deko": {}}
deco = am.Pack()
deco.details = [("d.json", 1)]
am.decorate(grid, terrain, layers, deco, {"deko": ["20"]})
near = sum(1 for (c, r) in layers["floor2"] if abs(c - 3) <= 2 and abs(r - 5) <= 2)
far = len(layers["floor2"]) - near
check("builder: with deko, details gather around objects (a chest) and the open floor stays calm",
      near >= 5 and far <= 0.1 * (200 - 25), f"near {near}, far {far}")

# the looks of "muster:" (facade, props, alcove, outside, pits) and the second floor tone ":", with the
# free style and made-up pictures: every look only changes pictures, except "aussen", which makes the void a wall
look = am.Pack.load("demo")
src = next(iter(look.tilesets))
look.facade = {"left": (src, 501), "mid": (src, 502), "right": (src, 503), "opening": (src, 504)}
look.floor_alt = [(src, 510)]
look.props = [((src, 520), None)]
look.big_props = []
look.props_by_place = {"tall": [(src, 521)], "corner": [(src, 522)], "flat": [(src, 523)]}
look.arch = {"tile": (src, 530), "stairs": [(src, 531), (src, 532), (src, 531, 0x80000000)]}
look.outside = [(src, 540)]
look.pits = {"frame": {"".join(bits): (src, 550 + i) for i, bits in enumerate(
    __import__("itertools").product("01", repeat=8))}, "details": [(src, 560)]}
text = ("muster: alle\nview: fit\n---\n"
        "##########\n##########\n####.Z.###\n#Hx.....:#\n#..x.~~.:#\n#x...~~.:#\n##########\n")
header, rows = am.parse_text(text)
level, terrain = am.build(header, rows, look)
first = next(t["firstgid"] for t in level["tilesets"] if t["source"] == src)
data = {ly["name"]: ly for ly in level["layers"]}
W = level["width"]


def local(layer, c, r):
    """Local id and flip flags of the tile at map cell (c, r); the view is the map plus one field."""
    gid = data.get(layer, {"data": []})["data"][(r + 1) * W + c + 1] if layer in data else 0
    return ((gid & 0x0FFFFFFF) - first if gid else None), gid >> 28


fronts = [local("Walls", c, r)[0] for c, r in ((1, 2), (7, 2), (8, 2))]
check("builder, wandansicht: a two-row wall shows its front where floor lies below, with end pieces; an obstacle "
      "below it keeps the top", fronts == [502, 501, 503] and local("Walls", 2, 2)[0] not in (501, 502, 503, 504),
      f"{fronts}, above the obstacle {local('Walls', 2, 2)}")
check("builder, bogen: stairs over the three fields, mirrored on the right, the arch on a layer Over, the opening "
      "dark, the goal unseen",
      [local("Floor2", c, 2)[0] for c in (4, 5, 6)] == [531, 532, 531] and local("Floor2", 6, 2)[1] == 8
      and local("Over", 4, 1)[0] == 530 and [local("Walls", c, 1)[0] for c in (4, 5, 6)] == [504] * 3
      and [(o["x"], o["y"]) for o in data["Objects"]["objects"] if not o["visible"]] == [(6 * 16, 4 * 16)],
      f"{[local('Floor2', c, 2) for c in (4, 5, 6)]} {local('Over', 4, 1)} {local('Walls', 5, 1)} "
      f"{[(o['x'], o['y'], o['visible']) for o in data['Objects']['objects']]}")
check("builder, requisiten: an obstacle under a wall is tall, in a corner a pot, elsewhere flat",
      (local("Walls", 2, 3)[0], local("Walls", 1, 5)[0], local("Walls", 3, 4)[0]) == (521, 522, 523),
      f"{[local('Walls', c, r)[0] for c, r in ((2, 3), (1, 5), (3, 4))]}")
check("builder, ':' is a second floor tone on Floor2 and floor for the rules",
      local("Floor2", 8, 3)[0] == 510 and terrain[4][9] == am.FLOOR)
pit = [local("Floor", c, r)[0] for c, r in ((5, 4), (6, 4), (5, 5), (6, 5))]
want = [550 + int(m, 2) for m in ("00001011", "00010110", "01101000", "11010000")]
bones = {(c, r) for c in range(10) for r in range(7) if local("Floor2", c, r)[0] == 560}
next_to_pit = all(any(abs(c - x) <= 1 and abs(r - y) <= 1 for x, y in ((5, 4), (6, 4), (5, 5), (6, 5))) for c, r in bones)
check("builder, gruben: a pit's four fields get the frame's four corners, bones lie only on the floor around it",
      pit == want and bones and next_to_pit, f"{pit} vs {want}, bones {sorted(bones)}")
check("builder, aussen: the void beyond the walls is rock on the wall layer and a wall for the rules; the view "
      "still fits the map", local("Walls", -1, -1)[0] == 540 and terrain[0][0] == am.WALL
      and (level["width"], level["height"]) == (12, 9) and terrain[4][2] == am.FLOOR,
      f"{local('Walls', -1, -1)} {terrain[0][0]} {(level['width'], level['height'])}")
door = am.build(*am.parse_text("muster: bogen\n---\n#######\n#H....#\n###D###\n###.###\n#....Z#\n#######\n"), look)[0]
over = next((ly for ly in door["layers"] if ly["name"] == "Over"), None)
cells = [] if over is None else [(i % door["width"], i // door["width"]) for i, g in enumerate(over["data"]) if g]
ox, oy = (door["width"] - 7) // 2, (door["height"] - 6) // 2
check("builder, bogen: a doorway through a wall two rows deep gets one arch, anchored left of the gap on the front row",
      cells == [(2 + ox, 3 + oy)], f"{cells}")
plain = am.build(*am.parse_text(text.replace("muster: alle\n", "")), look)[0]
check("builder: without the header muster the same map is built as before (no Over layer, no rock, plain pit)",
      [ly["name"] for ly in plain["layers"]][-1] == "Objects" and plain["layers"][3]["data"][0] == 0)
try:
    am.looks_on({"muster": ["wandansicht", "turm"]})
    check("builder: an unknown look is an error", False)
except am.MapError as err:
    check("builder: an unknown look is an error", "turm" in str(err), str(err))

# furnishing by room type ("raum:"), patches and variety, with the same made-up pictures
look.rooms = {"lager": {"north": [(src, 601), [(src, 602), (src, 603)]], "corner": [(src, 604)]},
              "thron": {"focal": [3, 3], "flank": [(src, 605)], "floor": ":"}}
text = ("raum: lager 1,1 9,5\nraum: thron 12,1 20,6\n---\n"
        "######################\n#.........##.........#\n#.........##.........#\n#.........D..........#\n"
        "#.........##.........#\n#H........##.........#\n###.######.###########\n")
header, rows = am.parse_text(text)
level, terrain = am.build(header, rows, look)
W = level["width"]
first = next(t["firstgid"] for t in level["tilesets"] if t["source"] == src)
ox, oy = (W - 22) // 2, (level["height"] - 7) // 2
walls = {ly["name"]: ly for ly in level["layers"]}["Walls"]["data"]


def wall_local(c, r):
    gid = walls[(r + oy) * W + c + ox]
    return gid - first if gid else None


north = [wall_local(c, 1) for c in range(1, 10)]
pinned = [v for v in north if v in (601, 602, 603)]
check("builder, raum: pieces with pinned pictures stand along the north wall, every other field, a wide piece on two",
      len(pinned) >= 2 and all(north[i + 1] not in (601, 602, 603) or north[i] == 602 for i in range(8)
                              if north[i] in (601, 603)), f"{north}")
check("builder, raum: the fields next to the door and the gap stay free, objects are untouched",
      all(terrain[r + oy][c + ox] == am.FLOOR for c, r in ((9, 2), (9, 3), (9, 4), (2, 5), (3, 5), (4, 5)))
      and terrain[5 + oy][1 + ox] == am.FLOOR, f"{[terrain[r + oy][c + ox] for c, r in ((9, 2), (9, 3), (9, 4), (2, 5), (3, 5), (4, 5))]}")
look.glass = (src, 599)
level = am.build(header, rows, look)[0]
walls = {ly["name"]: ly for ly in level["layers"]}["Walls"]["data"]
deko = {ly["name"]: ly for ly in level["layers"]}.get("Deko", {"data": [0] * len(walls)})["data"]
look.rooms["lager"]["north"] = [[(src, 0), (src, 599)]]
level = am.build(header, rows, look)[0]
walls = {ly["name"]: ly for ly in level["layers"]}["Walls"]["data"]
deko = {ly["name"]: ly for ly in level["layers"]}["Deko"]["data"]
beds = [(c, walls[(1 + oy) * W + c + ox] - first, deko[(1 + oy) * W + c + ox] - first) for c in range(1, 10)
        if deko[(1 + oy) * W + c + ox]]
check("builder, raum: a piece whose picture has local id 0 (never a wall) goes on the Deko layer over a glass wall",
      beds and all(w == 599 and d == 0 for _, w, d in beds), f"{beds}")
corner = [wall_local(c, 5) for c in (8, 9)] + [wall_local(c, 5) for c in (1, 2)]
check("builder, raum: pots in the far corners", 604 in corner, f"{corner}")
floor2 = {ly["name"]: ly for ly in level["layers"]}["Floor2"]["data"]
focal = sum(1 for r in range(1, 7) for c in range(12, 21) if floor2[(r + oy) * W + c + ox])
flank = [wall_local(c, r) for r in range(1, 7) for c in range(12, 21) if wall_local(c, r) == 605]
check("builder, raum: a framed focal area with two flanking pieces, the room's floor in the second tone",
      focal >= 9 + 20 and len(flank) == 2, f"framed/toned fields {focal}, flank {flank}")
try:
    am.build(*am.parse_text("raum: bad 1,1 2,2\n---\n####\n#HZ#\n####\n"), look)
    check("builder, raum: an unknown room type is an error", False)
except am.MapError as err:
    check("builder, raum: an unknown room type is an error", "bad" in str(err) and "lager" in str(err), str(err))
look.details = [(src, 570)]
open_key = am.pattern([list("...")] * 3, 1, 1)
open_stacks = list(look.stacks[open_key])
look.stacks[open_key][(("floor", src, 700),)] += max(look.stacks[open_key].values())
for a in open_stacks + [(("floor", src, 700),)]:
    for b in open_stacks + [(("floor", src, 700),)]:
        look.hpairs[(a, b)] += 1
        look.vpairs[(a, b)] += 1
open_room = "deko: 20\n---\n" + "#" * 24 + "\n" + "\n".join("#H" + "." * 21 + "#" if i == 0 else "#" + "." * 22 + "#" for i in range(12)) + "\n" + "#" * 24 + "\n"
even = am.build(*am.parse_text(open_room), look)[0]
patchy = am.build(*am.parse_text("muster: flecken\n" + open_room), look)[0]


def detail_cells(level):
    ly = {ly["name"]: ly for ly in level["layers"]}["Floor2"]
    return {(i % ly["width"], i // ly["width"]) for i, g in enumerate(ly["data"]) if g}


def in_patches(cells):
    """The share of details that lie in the noise's patches (flecken: all of them; an even sprinkle: some)."""
    return sum(1 for c, r in cells if am._noise(c, r, 5) > 0.55) / max(1, len(cells))


check("builder, flecken: details lie only in the patches of the noise, the map is unchanged otherwise",
      bool(detail_cells(patchy)) and in_patches(detail_cells(patchy)) == 1.0 and in_patches(detail_cells(even)) < 1.0
      and {ly["name"]: ly for ly in patchy["layers"]}["Walls"]["data"] == {ly["name"]: ly for ly in even["layers"]}["Walls"]["data"],
      f"{in_patches(detail_cells(patchy)):.2f} vs {in_patches(detail_cells(even)):.2f}, {len(detail_cells(patchy))} details")
varied = am.build(*am.parse_text("muster: vielfalt\n" + open_room), look)[0]
floors = lambda lv: {ly["name"]: ly for ly in lv["layers"]}["Floor"]["data"]      # noqa: E731
plain_kinds = len({g for g in floors(even) if g})
check("builder, vielfalt: the open floor uses more different tiles than before; walls stay as they are",
      len({g for g in floors(varied) if g}) > plain_kinds
      and {ly["name"]: ly for ly in varied["layers"]}["Walls"]["data"] == {ly["name"]: ly for ly in even["layers"]}["Walls"]["data"],
      f"{len({g for g in floors(varied) if g})} vs {plain_kinds}")
with tempfile.TemporaryDirectory() as folder:
    path = os.path.join(folder, "k.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("deko: 12\n---\n#######\n#T....#\n#H....#\n###D###\n#....x#\n#x...Z#\n#######\n")
    run = tool("check_look.py", path)
    want = ("Fackeln ohne Paar", "Südwand", "einreihigen Wand", "ohne Nische", "deko: über 10", "kein muster")
    check("check_look: hints on lone torches, a prop at the south wall, a door in a one-row wall, a goal without alcove, "
          "deko and muster", run.returncode == 0 and all(w in run.stdout for w in want), run.stdout + run.stderr)
    with open(path, "w", encoding="utf-8") as f:
        f.write("muster: alle\n---\n#######\n#######\n#T.Z.T#\n#..:..#\n#.H...#\n#######\n")
    run = tool("check_look.py", path)
    check("check_look: a map after the patterns gets no hints but the loose floor tone", run.returncode == 0
          and run.stdout.count("\n  ") == 1 and "Bodenton" in run.stdout, run.stdout + run.stderr)

# blueprints with blocks (large props by size), beds in a grid and fences as the room's walls
look.big_props = [{"w": 2, "h": 1, "fill": False, "parts": [(0, 0, src, 701), (1, 0, src, 702)]},
                  {"w": 3, "h": 2, "fill": False, "parts": [(dx, dy, src, 710 + 3 * dy + dx) for dx in range(3) for dy in range(2)]}]
look.fences = {"h": (src, 720), "left": (src, 721), "right": (src, 722), "post": (src, 723)}
look.rooms = {"garten": {"walls": "zaun", "beds": {"w": 2, "h": 2, "tiles": [(src, 730)]}},
              "halle": {"north": [{"block": [2, 1]}], "focal_block": [3, 2]}}
text = ("raum: garten 1,1 6,6\nraum: halle 9,1 17,7\n---\n"
        "###################\n#......##.........#\n#......##.........#\n#......D..........#\n#......##.........#\n"
        "#......##.........#\n#......##.........#\n#H.....##.........#\n###################\n")
header, rows = am.parse_text(text)
level, terrain = am.build(header, rows, look)
W = level["width"]
ox, oy = (W - 19) // 2, (level["height"] - 9) // 2
walls = {ly["name"]: ly for ly in level["layers"]}["Walls"]["data"]


def wl(c, r):
    gid = walls[(r + oy) * W + c + ox]
    return gid - first if gid else None


beds = [(c, r) for r in range(1, 7) for c in range(1, 7) if wl(c, r) == 730]
fence = {wl(c, 0) for c in range(1, 7)} | {wl(0, r) for r in range(1, 7)}
check("builder, raum: beds fill the room in a grid with a gap, the room's walls are fence rails and posts",
      beds == [(2, 2), (3, 2), (2, 3), (3, 3)] and all(terrain[r + oy][c + ox] == am.WALL for c, r in beds) and 720 in fence and 723 in fence
      and wl(0, 0) == 723, f"beds {len(beds)}, fence {fence}, corner {wl(0, 0)}")
north = [wl(c, 1) for c in range(9, 18)]
focal = [wl(c, r) for r in range(2, 7) for c in range(9, 18) if wl(c, r) in range(710, 716)]
check("builder, raum: a block along the north wall becomes the large prop of its size, a focal block the large piece",
      701 in north and 702 in north and sorted(focal) == list(range(710, 716)), f"north {north}, focal {sorted(focal)}")

# the free default style (7a): without an asset pack that brings the course's "dungeon" and "maze", a map
# without a style and a generated level use "demo" (the demo pack's dungeon), with every symbol; a pack
# that has styles/dungeon.json keeps "dungeon" the default
probe = r"""
import os, sys
import dungeoncoder
from dungeoncoder import Game, asciimap, generator
dungeoncoder.use_simulator()
rows = ["controls: 4,1 -> 8,2", "values: 5", "guards: 6,5 patrol east", "---",
        "##############",
        "#H..s...#..J.#",
        "#.......D...C#",
        "#.*..K..#..~~#",
        "###T##D####t##",
        "#.o.G.W.....Z#",
        "##############"]
path = os.path.join(sys.argv[1], "alles.txt")
with open(path, "w") as f:
    f.write("\n".join(rows) + "\n")
level = asciimap.level_from_file(path)
hero = Game(path).get_hero()
print(sorted({t["source"] for t in level["tilesets"]}), hero.move(), asciimap.default_style("dungeon"),
      generator.maze_text(3).splitlines()[1], generator.from_recipe({"generate": ["rooms"]}).splitlines()[1])
"""
with tempfile.TemporaryDirectory() as root:
    def default(packs):
        return subprocess.run([sys.executable, "-c", probe, root], capture_output=True, text=True, cwd=root,
                              env=dict(os.environ, PYTHONPATH=api, DC_ASSET_PACKS=packs))
    run = default("")
    check("free default style: a map without a style, with every symbol, builds and plays without any asset pack",
          run.returncode == 0 and run.stdout.strip().endswith(
              "['../tilesets/demo_hero.json', '../tilesets/demo_tiles.json'] True demo style: demo style: demo"),
          run.stdout + run.stderr)
    course = os.path.join(root, "kurs")
    os.makedirs(os.path.join(course, "styles"))
    with open(am.style_path("demo"), encoding="utf-8") as f, \
            open(os.path.join(course, "styles", "dungeon.json"), "w", encoding="utf-8") as g:
        g.write(f.read())
    run = default(course)
    check("... and a pack that brings dungeon keeps it the default (maze still falls back)",
          run.returncode == 0 and run.stdout.strip().endswith("True dungeon style: demo style: demo"),
          run.stdout + run.stderr)

# the game builds an object only if its tileset has a tile for every state of its class (game-objects.js);
# the demo pack, the fallback of every text map, must have them all (a VerticalGrille once had none)
sys.path.insert(0, api)
from dungeoncoder.sim import STATES  # noqa: E402
with open(os.path.join(DEMO, "tilesets", "demo_tiles.json"), encoding="utf-8") as f:
    have = {(t.get("type"), p["value"]) for t in json.load(f)["tiles"] for p in t.get("properties", [])
            if p["name"] == "state"}
missing = [f"{cls} {state}" for cls, states in STATES.items() for state in states if (cls, state) not in have]
check("demo pack: a tile for every state of every object class", not missing, ", ".join(missing))

print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
