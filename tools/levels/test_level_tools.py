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

print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
