"""Learn text-map style packs from hand-built levels, by recipes (P5, G1 in the course's docs).

    python3 tools/levels/learn_styles.py                 # the engine's own styles (packs/learn/)
    python3 tools/levels/learn_styles.py DIR [DIR ...]   # recipes in these folders too
    python3 tools/levels/learn_styles.py --check [DIR]   # exit 1 if a style pack is stale

A style pack (api/python/dungeoncoder/packs/<style>.json, or styles/<style>.json of an asset
pack) tells the text-map builder (dungeoncoder/asciimap.py, Game("karte.txt")) which tiles to
use for every 3x3 neighbourhood of terrain. It is *learned* from levels built by hand, and a
*recipe* says from which: a JSON file in a folder named learn/. The learned pack is written to
the folder above it, so the engine's recipes (api/python/dungeoncoder/packs/learn/) write into
the Python package and an asset pack's recipes (<pack>/styles/learn/) into that pack's styles/.

Recipe fields:
  style, about      the style's name (style: in a text map) and what it looks like
  levels            the folder of the source levels, relative to the recipe
  tiles             the levels to learn tiles from, each {"level": name} plus options:
                      visual_walls     layers named "Walls..." are walls even without collision
                      ignore_bg_abyss  abyss tiles on the background layer don't count
                      drop_bg_under_floor  don't copy background tiles under generated floors
                      skip_open_floor  don't learn plain interior floor here
                      keep_walls       {tileset_suffix, local_from, local_to}: learn only fields whose
                                       wall pieces are in that range (one construction system out of
                                       a level that mixes several)
  korpus            learn tiles also from <korpus>_korpus_0.json, _1, ... in the levels folder
  objects           the levels to learn object tiles from (single sprites, so from all levels of the look)
  neighbour_fit     prefer stacks that occur next to their neighbours (default true)
  hero, abyss       the figure sheet and the tileset with the abyss tiles
  sweets            [tileset, local id] of the sweets (*), unless the style's items name one
  items, guard      a world's item classes for K, *, o, and the figure number of the agents W
  pack              the asset pack the art comes from: levels built in this style name it (map
                    property pack), so a missing tileset's message can say which pack to get
  decor             decoration and exits as data (paths may be {"frame": {tileset, rows}}), or
  decor_file        a file in the levels folder with them
  big_props         large props for blocks of x, a file in the levels folder
Each style learns from levels of ONE construction system; mixing them cell by cell gives pieces
that don't fit together. Tilesets are looked up like the other tools do (dclevel: DC_ASSET_PACKS,
then the engine's assets).
"""
import glob
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from dclevel import ASSETS, FLOOR, Level, tileset  # noqa: E402

API = os.path.normpath(os.path.join(HERE, "..", "..", "api", "python", "dungeoncoder"))
ENGINE_RECIPES = os.path.join(API, "packs", "learn")
ENGINE_PACKS = os.path.normpath(os.path.join(HERE, "..", "..", "packs"))


def _load_asciimap():
    """The builder of the Python API, loaded by file (the package folder on sys.path would shadow
    the `dungeoncoder` package with its inner module dungeoncoder.py)."""
    spec = importlib.util.spec_from_file_location("asciimap", os.path.join(API, "asciimap.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


asciimap = _load_asciimap()
DIRECTIONS = asciimap.DIRECTIONS


def recipes(dirs=None):
    """Every recipe in the folders (default: the engine's), with its source levels' folder
    (_levels), its file (_path) and the folder its pack is written to (_out)."""
    out = []
    for folder in dirs or [ENGINE_RECIPES]:
        for path in sorted(glob.glob(os.path.join(folder, "*.json"))):
            with open(path, encoding="utf-8") as f:
                recipe = json.load(f)
            recipe["_path"] = path
            recipe["_levels"] = os.path.normpath(os.path.join(folder, recipe["levels"]))
            recipe["_out"] = os.path.dirname(os.path.normpath(folder))
            out.append(recipe)
    return out


def available(recipe):
    """A recipe whose first source level exists (bought art may be missing on this machine)."""
    return os.path.exists(os.path.join(recipe["_levels"], recipe["tiles"][0]["level"] + ".json"))


def recipe_for(style, dirs=None):
    """The recipe of a style: the first folder that has one wins (as for packs in the game)."""
    found = [r for r in recipes(dirs) if r["style"] == style and available(r)]
    if not found:
        raise SystemExit(f"unknown style {style!r}; known: {', '.join(sorted({r['style'] for r in recipes(dirs)}))}")
    return found[0]


def tile_levels(recipe):
    """[(level name, options)] to learn tiles from, the corpus levels included."""
    levels = [(t["level"], {k: v for k, v in t.items() if k != "level"}) for t in recipe["tiles"]]
    if recipe.get("korpus"):
        main = recipe["korpus"]
        count = len(glob.glob(os.path.join(recipe["_levels"], f"{main}_korpus_*.json")))
        levels += [(f"{main}_korpus_{n}", {}) for n in range(count)]
    return levels


def keeps_wall(rule, source, local):
    """keep_walls: a wall piece is learned only from the given tileset and local id range."""
    return source.endswith(rule["tileset_suffix"]) and rule["local_from"] <= local < rule["local_to"]


def frame_paths(source, rows):
    """A path from a 3x3 frame of whole tiles (a carpet with a border): per 8-neighbour mask
    the corner, edge or middle piece. rows: the 3 x 3 local ids, top row first."""
    paths = {}
    for bits in range(256):
        mask = "".join("1" if bits >> i & 1 else "0" for i in range(8))
        n, w, e, s = (mask[i] == "1" for i in (1, 3, 4, 6))
        x = 1 if (w and e) or (not w and not e) else (0 if not w else 2)
        y = 1 if (n and s) or (not n and not s) else (0 if not n else 2)
        paths[mask] = (source, rows[y][x])
    return paths


def learn_decor(pack, recipe):
    """Decoration and exits of a style: from the recipe (the dungeon styles), or from the file
    tools/make_world_tiles.py writes next to a world's levels (decor_file: <world>_deko.json)."""
    decor = None
    data = recipe.get("decor")
    if recipe.get("decor_file"):
        path = os.path.join(recipe["_levels"], recipe["decor_file"])
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
    if data:
        paths = data["paths"]
        if "frame" in paths:                    # a 3x3 frame of whole tiles (a carpet with a border)
            paths = frame_paths(paths["frame"]["tileset"], paths["frame"]["rows"])
        decor = {"props": [tuple(p) for p in data["props"]], "details": [tuple(d) for d in data["details"]],
                 "paths": {k: tuple(v) for k, v in paths.items()},
                 "wall_variants": {tuple(k): [tuple(t) for t in v] for k, v in data.get("wall_variants", [])},
                 "tops": {tuple(k): tuple(v) for k, v in data.get("tops", [])},
                 "exits": {k: tuple(v) for k, v in data.get("exits", {}).items()}}
    if not decor:
        return set()
    tops = decor.get("tops", {})
    pack.props = [(p, tops.get(p)) for p in decor["props"]]
    pack.details = list(decor["details"])
    pack.paths = dict(decor["paths"])
    pack.wall_variants = dict(decor.get("wall_variants", {}))
    pack.exits = dict(decor.get("exits", {}))
    used = {t[0] for t in pack.details} | {t[0] for t in pack.paths.values()} | {t[0] for t in pack.exits.values()}
    used |= {t[0] for b, t in pack.props for t in (b, t) if t}
    used |= {t[0] for v in pack.wall_variants.values() for t in v}
    return used


def big_props_file(recipe):
    """The large props of a style cut from the bought art (tools/make_prop_tiles.py), or None."""
    if not recipe.get("big_props"):
        return None
    path = os.path.join(recipe["_levels"], recipe["big_props"])
    return path if os.path.exists(path) else None


def learn_big_props(pack, recipe):
    """Large props (asciimap.place_big_props) from the course pack; returns their tilesets."""
    with open(big_props_file(recipe), encoding="utf-8") as f:
        data = json.load(f)
    pack.big_props = [{"w": p["w"], "h": p["h"], "fill": p["fill"], "parts": [tuple(t) for t in p["parts"]]}
                      for p in data["big_props"]]
    return {data["tileset"]}


def learn(recipe, big=None):
    """The style pack for a recipe (or a style name: recipe_for): tile stacks per 3x3 terrain
    pattern, which stacks sit next to each other (horizontally and vertically), object tiles, and
    the tileset facts the builder needs (so it runs without the tilesets).
    big: add the large props (default: if the recipe has them)."""
    if isinstance(recipe, str):
        recipe = recipe_for(recipe)                        # the engine's recipes
    if big is None:
        big = big_props_file(recipe) is not None
    config, style = recipe, recipe["style"]
    levels = recipe["_levels"]
    pack = asciimap.Pack()
    pack.neighbour_fit = config.get("neighbour_fit", True)
    for name, options in tile_levels(recipe):
        level = Level(os.path.join(levels, name + ".json"), visual_walls=options.get("visual_walls", False),
                      ignore_bg_abyss=options.get("ignore_bg_abyss", False), learning_abyss=True)
        pack.tile_size = level.tile_w          # the builder places objects on this grid
        terrain = [[level.terrain(c, r) for c in range(level.width)] for r in range(level.height)]
        stack_at = {}
        for r in range(level.height):
            for c in range(level.width):
                key = asciimap.pattern(terrain, c, r)
                if options.get("skip_open_floor") and key == (FLOOR, (FLOOR,) * 8):
                    continue
                stack = tuple((role, ts.source, local) for role, ts, local in level.tiles_at(c, r)
                              if role != "over"
                              and not (options.get("drop_bg_under_floor") and role == "bg"
                                       and key[0] == FLOOR))
                keep = options.get("keep_walls")
                if keep and any(role == "wall" and not keeps_wall(keep, src, local) for role, src, local in stack):
                    continue
                pack.stacks[key][stack] += 1
                stack_at[(c, r)] = stack
        for (c, r), stack in stack_at.items():
            if (c + 1, r) in stack_at:
                pack.hpairs[(stack, stack_at[(c + 1, r)])] += 1
            if (c, r + 1) in stack_at:
                pack.vpairs[(stack, stack_at[(c, r + 1)])] += 1
        _learn_goal_decor(pack, level)
    for name in config["objects"]:
        level = Level(os.path.join(levels, name + ".json"), learning_abyss=True)
        terrain = [[level.terrain(c, r) for c in range(level.width)] for r in range(level.height)]
        for o in level.objects():
            if not o["ts"] or o["cls"] in ("Character", ""):
                continue
            if o["cls"] == "Goal" and o["ts"].props(o["local"]).get("collision"):
                continue    # the arenas' throne is a colliding "goal"
            c, r = o["cell"]
            context = terrain[r][c] if 0 <= r < level.height and 0 <= c < level.width else FLOOR
            pack.objects[(o["cls"], context)][(o["ts"].source, o["local"])] += 1

    source = config.get("hero", "../tilesets/characters_16x16_spritesheet_no_bkg.json")
    for direction in DIRECTIONS:
        for number in range(16):
            ids = tileset(source).find("Character", state=f"standing_{direction}_{number}")
            if ids:
                pack.hero[f"{direction}_{number}"] = (source, ids[0])
    # tiles of class Abyss, the plainest first (tiles_dungeon local 3, as in falling.json)
    dungeon = config.get("abyss", "../tilesets/tiles_dungeon_v1.2_16x16.json")
    pack.world = style if "items" in config else None
    pack.pack = config.get("pack")
    pack.guard_sprite = config.get("guard", pack.guard_sprite)
    for symbol, cls in config.get("items", {}).items():         # a world's own items
        pack.items[symbol] = (dungeon, tileset(dungeon).find(cls)[0], cls)
    pack.sweets = None if "*" in pack.items else (tuple(config["sweets"]) if config.get("sweets") else sweets_tile())
    abyss = tileset(dungeon).find("Abyss")
    pack.abyss_tiles = [(dungeon, local) for local in sorted(abyss, key=lambda t: (t != 3, t))]
    object_tiles = {t for counter in pack.objects.values() for t in counter} | set(pack.hero.values())
    object_tiles |= {(src, local) for src, local, _ in pack.items.values()}
    if pack.sweets:
        object_tiles.add(pack.sweets)
    for (cls, _), counter in pack.objects.items():
        if cls == "Torch":
            for source, _ in counter:
                pack.torch_off[source] = tileset(source).find("Torch", state="off")
    object_tiles |= {(s, i) for s, ids in pack.torch_off.items() for i in ids}
    decor_sources = learn_decor(pack, recipe)
    if big:
        decor_sources |= learn_big_props(pack, recipe)
    sources = ({src for stacks in pack.stacks.values() for stack in stacks for _, src, _ in stack}
               | decor_sources
               | {src for src, _ in pack.abyss_tiles}
               | {src for src, _ in object_tiles}
               | {d[2] for decor in pack.goal_decor for d in decor})
    for src in sorted(sources):
        ts = tileset(src)
        pack.tilesets[src] = {"count": ts.count, "tile_w": ts.tile_w, "tile_h": ts.tile_h,
                              "classes": {local: ts.cls(local) for s, local in sorted(object_tiles)
                                          if s == src and ts.cls(local)}}
    return pack


def _learn_goal_decor(pack, level):
    """What the level draws under and above its goal on the *extra* floor layers
    (e.g. the stairs on falling.json's Floor2 layer): (dx, dy, source, local) tiles."""
    floor_layers = [i for i, role in enumerate(level.roles) if role == "floor"]
    extra = floor_layers[1:]
    for o in level.objects():
        if o["cls"] != "Goal" or not o["ts"] or o["ts"].props(o["local"]).get("collision"):
            continue
        c, r = o["cell"]
        decor = []
        for dy in (0, -1):
            for i in extra:
                layer = level.tile_layers[i]
                ts, local = level.resolve(layer["data"][(r + dy) * layer["width"] + c])
                if ts is not None:
                    decor.append((0, dy, ts.source, local))
        if decor:
            pack.goal_decor[tuple(decor)] += 1


def sweets_tile():
    """The first tile of class Sweets in the engine's assets (a recipe can name its own)."""
    for name in sorted(os.listdir(os.path.join(ASSETS, "tilesets"))):
        ts = tileset("../tilesets/" + name)
        ids = [tid for tid in ts.meta if ts.cls(tid) == "Sweets"]
        if ids:
            return ts.source, ids[0]
    return None


def export(dirs=None, check=False):
    """Learn every available recipe and write its pack (or with check: compare it with the pack on
    disk). Returns the stale packs' paths."""
    stale = []
    for recipe in recipes(dirs):
        if not available(recipe):
            print(f"skip {os.path.relpath(recipe['_path'])}: its source levels are missing")
            continue
        path = os.path.join(recipe["_out"], f"{recipe['style']}.json")
        data = learn(recipe).to_json()
        if check:
            try:
                with open(path, encoding="utf-8") as f:
                    current = json.load(f)
            except (OSError, ValueError):
                current = None
            if current != json.loads(json.dumps(data)):
                stale.append(path)
            continue
        os.makedirs(recipe["_out"], exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, separators=(",", ":"), sort_keys=False)
            f.write("\n")
        print(f"{os.path.relpath(path)}: {os.path.getsize(path) // 1024} KiB")
    return stale


def export_tile_rules(directory=asciimap.PACK_DIR, exclude=()):
    """Write packs/tilesets.json: what the game needs to know about every tileset the engine
    bundles (game/assets and its own packs), without the images (the simulator dungeoncoder.sim
    plays levels with it; tilesets of other packs come from DC_ASSET_PACKS at run time).
    exclude: tileset file names to leave out (art that ships in another pack).
    Like the engine (game/src/tiles.js), a tile's class is read from its "type" key only."""
    rules = {}
    folders = [os.path.join(ASSETS, "tilesets")]           # the bundled assets, then the engine's own packs
    folders += ([os.path.join(ENGINE_PACKS, p, "tilesets") for p in sorted(os.listdir(ENGINE_PACKS))]
                if os.path.isdir(ENGINE_PACKS) else [])
    files = [(folder, name) for folder in folders if os.path.isdir(folder)
             for name in sorted(os.listdir(folder)) if name.endswith(".json") and name not in exclude]
    for folder, name in files:
        with open(os.path.join(folder, name), encoding="utf-8") as f:
            data = json.load(f)
        tiles = {}
        for tile in data.get("tiles", []):
            entry = {}
            if tile.get("type"):
                entry["type"] = tile["type"]
            props = {p["name"]: p["value"] for p in tile.get("properties", [])}
            if props:
                entry["props"] = props
            if entry:
                tiles[str(tile["id"])] = entry
        rules["../tilesets/" + name] = {"count": data["tilecount"], "tile_w": data["tilewidth"],
                                        "tile_h": data["tileheight"], "tiles": tiles}
    path = os.path.join(directory, "tilesets.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rules, f, separators=(",", ":"))
        f.write("\n")
    print(f"{os.path.relpath(path)}: {os.path.getsize(path) // 1024} KiB")


def main(args):
    check = "--check" in args
    dirs = [ENGINE_RECIPES] + [os.path.abspath(a) for a in args if not a.startswith("--")]
    stale = export(dirs, check=check)
    if check:
        for path in stale:
            print(f"stale: {os.path.relpath(path)} (run: python3 tools/levels/learn_styles.py)")
        print(f"{len(stale)} stale style pack(s)" if stale else "style packs up to date")
        return 1 if stale else 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
