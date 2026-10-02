"""Check a Tiled level by the engine's rules, and compare its game logic with another level.

    python3 tools/levels/check_level.py LEVEL.json                 # check one level, show its logic
    python3 tools/levels/check_level.py ORIGINAL.json EDITED.json  # did only the look change?

For level designers working in Tiled. The *logic* of
a level is everything the game and a student's program can notice: which field is wall, floor,
abyss or nothing; which objects lie where, in which state, with which properties (a switch's
`controls` compared by the field of its target, since Tiled's object ids may change); the hero's
start direction and figure; the map properties. Everything else (which picture a tile has, the
decoration layers, flips) is the *look* and may change freely.

Tilesets are looked up like the game does: DC_ASSET_PACKS, then the engine's game/assets (dclevel.py). Messages are German, for students.
Exit code 0 if no errors (and, comparing, if the logic is the same).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from dclevel import ABYSS, FLOOR, OBJECT_SYMBOLS, VOID, WALL, Level, asset_path  # noqa: E402

KNOWN = {"Torch", "Switch", "Door", "VerticalDoor", "PatternDoor", "Grille", "VerticalGrille", "Character",
         "Chest", "Jug", "Goal", "Crystal", "Pebble", "Guard", "Sweets", "Abyss"}
ON_WALL_OK = {"Torch"}                       # a torch hangs on a wall (or stands on a pedestal)
PROPERTY_TYPES = {"keyboard": "bool", "fernrohr": "bool", "orakel": "bool", "torch_light": "bool", "handmade": "bool",
                  "inventory_size": "int", "fog": "string", "win": "string", "world": "string",
                  "hero_inventory": "string"}
DIRECTIONS = ("north", "east", "south", "west")


class Report:
    def __init__(self):
        self.errors, self.warnings = [], []

    def error(self, text):
        self.errors.append(text)

    def warn(self, text):
        self.warnings.append(text)


def load(path):
    level = Level(path)
    with open(path, encoding="utf-8") as f:
        level.raw = json.load(f)
    return level


def objects(level):
    """The level's objects with class, field, state and properties (hero: direction and figure)."""
    out = []
    for o in level.objects():
        props = dict(o["props"])
        state = o["ts"].props(o["local"]).get("state") if o["ts"] else None
        if o["obj"].get("name") == "MainCharacter":
            o["cls"] = "Character"
        out.append(dict(o, id=o["obj"].get("id"), state=state, props=props))
    return out


def check(level, path, report):
    """The rules a level must follow so that the game can run it."""
    tw, th = level.tile_w, level.tile_h
    for ts in level.data["tilesets"]:
        if not os.path.exists(asset_path(ts["source"])):
            report.error(f"Tileset {ts['source']} nicht gefunden (die Quelle muss ../tilesets/<name>.json "
                         "heißen und in einem Asset-Pack liegen)")
    tile_layers = level.tile_layers
    if not any(Level.is_collision_layer(layer) for layer in tile_layers):
        report.warn("keine Kachelebene mit der Eigenschaft collision = true (bool): das Level hat keine Wände "
                    "(richtig für Brücken über dem Abgrund, sonst ein Fehler)")
    for layer in tile_layers:
        if Level.is_collision_layer(layer):
            zero = sum(1 for gid in layer["data"] if gid and level.resolve(gid)[1] == 0)
            if zero:
                report.warn(f"Ebene {layer['name']!r}: {zero} Kachel(n) mit der lokalen Nummer 0 – die zählen "
                            "im Spiel NICHT als Wand")
    objs = objects(level)
    heroes = [o for o in objs if o["cls"] == "Character"]
    if len(heroes) != 1:
        report.error(f"{len(heroes)} Figur(en) mit dem Namen MainCharacter, nötig ist genau eine")
    goals = [o for o in objs if o["cls"] == "Goal"]
    if not goals:
        report.warn("kein Ziel (Objekt der Klasse Goal): das Level kann nicht gewonnen werden")
    elif len(goals) > 1:
        report.warn(f"{len(goals)} Ziele: das Spiel nimmt nur das erste")
    ids = {o["id"]: o for o in objs}
    for o in objs:
        x, y = o["obj"]["x"], o["obj"]["y"]
        c, r = o["cell"]
        where = f"{o['cls'] or 'Objekt'} {o['obj'].get('name') or ''}(id {o['id']}) auf ({c},{r})".replace(" (", " (", 1)
        if x % tw or y % th:
            report.warn(f"{where}: liegt nicht genau auf dem Raster (x und y sollten Vielfache von {tw} sein; "
                        f"in Tiled: Einrasten am Raster); das Spiel rechnet es dem Feld ({c},{r}) zu")
        if not (0 <= c < level.width and 0 <= r < level.height):
            report.error(f"{where}: liegt außerhalb der Karte")
            continue
        if o["cls"] not in KNOWN and not (o["ts"] and o["ts"].props(o["local"]).get("item")):
            report.warn(f"{where}: Klasse {o['cls']!r} kennt das Spiel nicht (es zeigt das Objekt nur an)")
        ground = level.terrain(c, r)
        if ground == WALL and o["cls"] not in ON_WALL_OK:
            report.error(f"{where}: steht auf einem Wandfeld (die Figur kommt nicht heran)")
        if o["cls"] in ("Character", "Goal") and ground in (ABYSS, VOID):
            report.error(f"{where}: steht auf {'einem Abgrund' if ground == ABYSS else 'einem leeren Feld'}")
        if "controls" in o["props"] and o["props"]["controls"] not in ids:
            report.error(f"{where}: controls zeigt auf id {o['props']['controls']}, die es nicht gibt")
        if o["cls"] == "PatternDoor":
            for t in str(o["props"].get("torches", "")).split(","):
                if t.strip() and int(t) not in ids:
                    report.error(f"{where}: torches nennt id {t.strip()}, die es nicht gibt")
        if "value" in o["props"] and not isinstance(o["props"]["value"], int):
            report.error(f"{where}: value muss eine ganze Zahl sein (Typ int)")
        if o["cls"] == "Guard":
            if o["props"].get("behaviour", "patrol") not in ("patrol", "chase"):
                report.error(f"{where}: behaviour muss patrol oder chase sein")
            if o["props"].get("direction", "east") not in DIRECTIONS:
                report.error(f"{where}: direction muss north, east, south oder west sein")
    goal_cells = {o["cell"] for o in goals}
    open_void = sorted({(c + dc, r + dr) for c, r in walkable(level) if (c, r) not in goal_cells
                        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1))
                        if 0 <= c + dc < level.width and 0 <= r + dr < level.height
                        and level.terrain(c + dc, r + dr) == VOID})
    if open_void:
        shown = " ".join(f"({c},{r})" for c, r in open_void[:6]) + (" ..." if len(open_void) > 6 else "")
        report.warn(f"{len(open_void)} leere(s) Feld(er) ohne Kachel grenzen an begehbaren Boden: {shown}; im "
                    "Spiel kann man sie betreten (Wand oder Abgrund davor setzen)")
    props = {p["name"]: p for p in level.data.get("properties", [])}
    for name, wanted in PROPERTY_TYPES.items():
        if name in props and props[name].get("type") != wanted:
            report.error(f"Karteneigenschaft {name}: Typ {props[name].get('type')!r}, nötig ist {wanted!r}")
    return objs


def walkable(level):
    return [(c, r) for r in range(level.height) for c in range(level.width) if level.terrain(c, r) == FLOOR]


def logic(level, objs):
    """Everything the game logic can notice, in a comparable form."""
    cell_of = {o["id"]: o["cell"] for o in objs}
    items = []
    for o in objs:
        props = dict(o["props"])
        if "controls" in props:
            props["controls"] = ("Feld",) + tuple(cell_of.get(props["controls"], ("?",)))
        if "torches" in props:
            props["torches"] = tuple(cell_of.get(int(t), "?") for t in str(props["torches"]).split(",") if t.strip())
        cls = o["cls"]
        if o["obj"].get("type"):
            cls = o["obj"]["type"]
        items.append((o["cell"], cls, o["state"], tuple(sorted((k, str(v)) for k, v in props.items())),
                      o["obj"].get("visible", True)))
    props = {p["name"]: p["value"] for p in level.data.get("properties", []) if p["name"] != "handmade"}
    terrain = [[level.terrain(c, r) for c in range(level.width)] for r in range(level.height)]
    return {"size": (level.width, level.height), "terrain": terrain, "objects": sorted(items, key=str),
            "properties": props}


def show(level, objs):
    """The level as a text map (the logic, not the look)."""
    grid = [[level.terrain(c, r) for c in range(level.width)] for r in range(level.height)]
    for o in objs:
        c, r = o["cell"]
        if 0 <= c < level.width and 0 <= r < level.height:
            symbol = "H" if o["cls"] == "Character" else OBJECT_SYMBOLS.get(o["cls"], "?")
            if o["cls"] == "Torch":
                symbol = "T" if o["state"] == "burning" else "t"
            grid[r][c] = symbol
    print("\n".join("".join(row).rstrip() for row in grid))


def compare(a, b, report):
    if a["size"] != b["size"]:
        report.error(f"Kartengröße {a['size']} -> {b['size']}: alle Koordinaten verschieben sich")
        return
    for r, (ra, rb) in enumerate(zip(a["terrain"], b["terrain"])):
        for c, (x, y) in enumerate(zip(ra, rb)):
            if x != y:
                names = {WALL: "Wand", FLOOR: "Boden", ABYSS: "Abgrund", VOID: "nichts"}
                report.error(f"Feld ({c},{r}): {names[x]} -> {names[y]}")
    sa, sb = set(a["objects"]), set(b["objects"])
    for o in sorted(sa - sb, key=str):
        report.error(f"Objekt fehlt oder geändert: {describe(o)}")
    for o in sorted(sb - sa, key=str):
        report.error(f"Objekt neu oder geändert:   {describe(o)}")
    for key in sorted(set(a["properties"]) | set(b["properties"])):
        if a["properties"].get(key) != b["properties"].get(key):
            report.error(f"Karteneigenschaft {key}: {a['properties'].get(key)!r} -> {b['properties'].get(key)!r}")


def describe(o):
    cell, cls, state, props, visible = o
    extra = ", ".join(f"{k}={v}" for k, v in props)
    return f"{cls} auf {cell}" + (f", Zustand {state}" if state else "") + (f", {extra}" if extra else "") \
        + ("" if visible else ", unsichtbar")


def main(args):
    if len(args) not in (1, 2):
        sys.exit(__doc__)
    reports = []
    logics = []
    for path in args:
        report = Report()
        level = load(path)
        objs = check(level, path, report)
        logics.append(logic(level, objs))
        reports.append((path, report))
        print(f"== {path}: {level.width} x {level.height} Felder zu {level.tile_w} px")
        if len(args) == 1:
            show(level, objs)
    ok = True
    for path, report in reports:
        for e in report.errors:
            print(f"FEHLER  {os.path.basename(path)}: {e}")
        for w in report.warnings:
            print(f"Hinweis {os.path.basename(path)}: {w}")
        ok &= not report.errors
    if len(args) == 2:
        diff = Report()
        compare(logics[0], logics[1], diff)
        for e in diff.errors:
            print(f"ANDERS  {e}")
        if diff.errors:
            print(f"Die Spiellogik hat sich geändert ({len(diff.errors)} Unterschied(e)): die Übung kann jetzt "
                  "anders funktionieren.")
            ok = False
        else:
            print("Gleiche Spiellogik: nur das Aussehen hat sich geändert.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main(sys.argv[1:])
