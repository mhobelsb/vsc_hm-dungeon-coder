"""Checks for the level tools in this folder, on the demo pack only (no browser, no course art).

    python3 tools/levels/test_level_tools.py        (npm run test:tools; level2png needs Pillow)
"""
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

print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
