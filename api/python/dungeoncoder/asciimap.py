"""Levels from ASCII maps: `Game("karte.txt")` builds the level from a text file.

A map file has an optional header, a line "---", and the map:

    start: north             # hero's start direction (default south)
    hero: 7                  # hero sprite 0-15 (default 7)
    style: dungeon           # tile style: dungeon (default), corridor, arena, bridge
    controls: 8,8 -> 25,10   # switch/torch at (8,8) toggles the object at (25,10); repeatable
    pattern: 5,2 = 101 @ 2,0 3,0 4,0   # door at (5,2) is open exactly while these torches show 101
    values: 5 3 8            # weights of the crystals K, in reading order (never drawn)
    colors: weiss orange weiss  # optional: colour of each crystal (weiss or orange)
    fog: dark                # any other key becomes a map property (bool/int/str)
    ---
    ##########
    #H..s....#
    #....D...Z
    ##########

Legend:  #  wall      .  floor     ~  abyss     (blank)  nothing
         H  hero      Z  goal      T/t  torch (burning/off, on a wall)
         s  switch    D  door      G  grille    C  chest    J  jug    *  sweets
         K  crystal   o  pebble

Coordinates are 0-based (column, row) in the map as written. The map is placed
centred on the 30x20 game field.

Which tile goes where is decided by a *style pack* (packs/<style>.json): for every
3x3 neighbourhood of terrain it lists the tile stacks that good levels use there,
and which stacks fit next to each other. The packs are learned from the levels
that ship with the game (tools/ascii2level.py in the development workspace).
"""
import collections
import json
import os
import random

WALL, FLOOR, VOID, ABYSS = "#", ".", " ", "~"
GRID_W, GRID_H = 30, 20
OBJECT_CLASSES = {"s": "Switch", "C": "Chest", "J": "Jug", "Z": "Goal", "*": "Sweets"}
NEIGHBOURS = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
WEIGHTS = [1, 2, 1, 2, 2, 1, 2, 1]     # orthogonal neighbours matter more than diagonal ones
DIRECTIONS = ("north", "east", "south", "west")
HEADER_KEYS = ("start", "hero", "style", "controls", "pattern", "values", "colors")
# items that aren't learned from the levels: tiles from the icon sheet (the engine's ITEM_TILES)
ICON_SHEET = "../tilesets/Icon sheet (16x16).json"
ITEM_TILESETS = {ICON_SHEET: {"count": 420, "tile_w": 16, "tile_h": 16, "classes": {}}}
CRYSTAL_TILES = {"weiss": 109, "orange": 106}
PEBBLE_TILE = 155   # everything else: map properties
PACK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "packs")
PACK_VERSION = 1


class MapError(ValueError):
    """The map file can't be turned into a level; the message says why and where."""


def parse_text(text):
    """(header dict, map rows) from the text of a map file."""
    lines = text.split("\n")
    header, rows = {}, lines
    if "---" in [l.strip() for l in lines]:
        split = [l.strip() for l in lines].index("---")
        for line in lines[:split]:
            if ":" in line:
                key, value = line.split(":", 1)
                header.setdefault(key.strip(), []).append(value.strip())
        rows = lines[split + 1:]
    # only trailing blank lines go: leading ones are part of the map's coordinates
    while rows and not rows[-1].strip():
        rows.pop()
    return header, rows


def base_terrain(ch):
    """Terrain under an ASCII symbol. Torches always stand on a wall or a pedestal."""
    if ch in (WALL, "T", "t"):
        return WALL
    if ch in (VOID, ABYSS):
        return ch
    return FLOOR


def pattern(terrain, c, r):
    """(terrain of the cell, terrain of its 8 neighbours); outside the field is VOID."""
    h, w = len(terrain), len(terrain[0])

    def at(x, y):
        return terrain[y][x] if 0 <= x < w and 0 <= y < h else VOID
    return at(c, r), tuple(at(c + dx, r + dy) for dx, dy in NEIGHBOURS)


def similarity(a, b):
    return sum(w for w, x, y in zip(WEIGHTS, a, b) if x == y)


class Pack:
    """What a style's good levels contain. A stack is a tuple of (role, source, local id)
    per tile layer; roles are bg, floor and wall."""

    def __init__(self):
        self.stacks = collections.defaultdict(collections.Counter)   # (center, neighbours) -> Counter(stack)
        self.hpairs = collections.Counter()                          # (left stack, right stack)
        self.vpairs = collections.Counter()                          # (upper stack, lower stack)
        self.objects = collections.defaultdict(collections.Counter)  # (class, context) -> Counter((source, local))
        self.goal_decor = collections.Counter()                      # ((dx, dy, source, local), ...) -> count
        self.neighbour_fit = True
        self.tilesets = {}      # source -> {"count", "tile_w", "tile_h", "classes": {local: class}}
        self.hero = {}          # "north_7" -> (source, local)
        self.torch_off = {}     # source -> [local ids of "off" torches]
        self.sweets = None      # (source, local)

    # --- choosing tiles ----------------------------------------------------
    def candidates(self, key):
        """Stacks seen for this exact pattern; otherwise those of the most similar patterns."""
        if key in self.stacks:
            return self.stacks[key]
        center, neigh = key
        keys = [k for k in self.stacks if k[0] == center]
        if not keys:
            return collections.Counter({(): 1})
        best = max(similarity(k[1], neigh) for k in keys)
        merged = collections.Counter()
        for k in keys:
            if similarity(k[1], neigh) == best:
                merged.update(self.stacks[k])
        return merged

    def choose(self, key, left, up, rng, variety):
        """Pick a stack for a cell: first of all it must *fit* the already chosen
        neighbours on the left and above (that pair occurs in the corpus), then it
        should be frequent for this neighbourhood. If no candidate of the pattern fits,
        look at stacks of patterns with the same orthogonal neighbours."""
        def fit(stack):
            return ((left is None or self.hpairs[(left, stack)] > 0)
                    + (up is None or self.vpairs[(up, stack)] > 0))

        counter = self.candidates(key)
        ranked = sorted(counter, key=lambda s: (fit(s), counter[s]), reverse=True)
        if fit(ranked[0]) < 2:
            center, neigh = key
            ortho = [neigh[i] for i in (1, 3, 4, 6)]
            pool = collections.Counter()
            for k, stacks in self.stacks.items():
                if k[0] == center and [k[1][i] for i in (1, 3, 4, 6)] == ortho:
                    pool.update(stacks)
            fitting = [s for s in pool if fit(s) == 2]
            if fitting:
                ranked = sorted(fitting, key=lambda s: pool[s], reverse=True)
        if variety > 0 and len(ranked) > 1 and rng.random() < variety:
            best_fit = fit(ranked[0])
            same = [s for s in ranked[:4] if fit(s) == best_fit]
            return rng.choice(same)
        return ranked[0]

    def object_tile(self, cls, context):
        for ctx in (context, FLOOR, WALL):
            if self.objects[(cls, ctx)]:
                return self.objects[(cls, ctx)].most_common(1)[0][0]
        return None

    def tile_class(self, tile):
        return self.tilesets[tile[0]]["classes"].get(tile[1], "")

    def wall_tiles(self):
        """Tiles that are wall pieces in the style's levels."""
        return {(source, local) for stacks in self.stacks.values() for stack in stacks
                for role, source, local in stack if role == "wall"}

    # --- storage -----------------------------------------------------------
    def to_json(self):
        """A JSON-ready dict. Orders are kept: ties are broken by first occurrence."""
        table, index = [], {}

        def ref(stack):
            if stack not in index:
                index[stack] = len(table)
                table.append([list(t) for t in stack])
            return index[stack]
        stacks = {k[0] + "".join(k[1]): [[ref(s), n] for s, n in counter.items()]
                  for k, counter in self.stacks.items()}
        return {
            "version": PACK_VERSION,
            "neighbour_fit": self.neighbour_fit,
            "stacks": stacks,
            "stack_table": table,
            "hpairs": [[ref(a), ref(b)] for (a, b), n in self.hpairs.items() if n > 0],
            "vpairs": [[ref(a), ref(b)] for (a, b), n in self.vpairs.items() if n > 0],
            "objects": [[cls, ctx, [[s, l, n] for (s, l), n in counter.items()]]
                        for (cls, ctx), counter in self.objects.items() if counter],
            "goal_decor": [[[list(d) for d in decor], n] for decor, n in self.goal_decor.items()],
            "tilesets": {s: dict(info, classes={str(k): v for k, v in info["classes"].items()})
                         for s, info in self.tilesets.items()},
            "hero": {k: list(v) for k, v in self.hero.items()},
            "torch_off": self.torch_off,
            "sweets": list(self.sweets) if self.sweets else None,
        }

    @classmethod
    def from_json(cls, data):
        if data.get("version") != PACK_VERSION:
            raise MapError(f"style pack version {data.get('version')}, expected {PACK_VERSION}")
        pack = cls()
        table = [tuple(tuple(t) for t in stack) for stack in data["stack_table"]]
        for key, entries in data["stacks"].items():
            pack.stacks[(key[0], tuple(key[1:]))] = collections.Counter({table[i]: n for i, n in entries})
        for a, b in data["hpairs"]:
            pack.hpairs[(table[a], table[b])] = 1
        for a, b in data["vpairs"]:
            pack.vpairs[(table[a], table[b])] = 1
        for obj_cls, ctx, entries in data["objects"]:
            pack.objects[(obj_cls, ctx)] = collections.Counter({(s, l): n for s, l, n in entries})
        for decor, n in data["goal_decor"]:
            pack.goal_decor[tuple(tuple(d) for d in decor)] = n
        pack.neighbour_fit = data["neighbour_fit"]
        pack.tilesets = {s: dict(info, classes={int(k): v for k, v in info["classes"].items()})
                         for s, info in data["tilesets"].items()}
        pack.hero = {k: tuple(v) for k, v in data["hero"].items()}
        pack.torch_off = data["torch_off"]
        pack.sweets = tuple(data["sweets"]) if data["sweets"] else None
        return pack

    @classmethod
    def load(cls, style):
        path = os.path.join(PACK_DIR, f"{style}.json")
        if not os.path.exists(path):
            styles = sorted(f[:-5] for f in os.listdir(PACK_DIR) if f.endswith(".json"))
            raise MapError(f"unknown style {style!r}; available: {', '.join(styles)}")
        with open(path, encoding="utf-8") as f:
            return cls.from_json(json.load(f))


def build(header, rows, pack, seed=0, variety=0.0):
    """(level as a Tiled JSON dict, terrain grid) for a parsed map."""
    height, width = len(rows), max((len(r) for r in rows), default=0)
    if width > GRID_W or height > GRID_H:
        raise MapError(f"the map is {width}x{height}; the game field is {GRID_W}x{GRID_H}")
    ox, oy = (GRID_W - width) // 2, (GRID_H - height) // 2
    grid = [[VOID] * GRID_W for _ in range(GRID_H)]
    for r, line in enumerate(rows):
        for c, ch in enumerate(line):
            grid[r + oy][c + ox] = ch

    terrain = [[base_terrain(ch) for ch in row] for row in grid]

    rng = random.Random(seed)
    layers = {"bg": {}, "floor": {}, "floor2": {}, "wall": {}}
    chosen = {}
    for r in range(GRID_H):
        for c in range(GRID_W):
            if pack.neighbour_fit:
                left, up = chosen.get((c - 1, r)), chosen.get((c, r - 1))
            else:
                left = up = None      # no constraint: the most frequent stack for the pattern
            stack = pack.choose(pattern(terrain, c, r), left, up, rng, variety)
            chosen[(c, r)] = stack
            floors = 0
            for role, source, local in stack:
                if role == "floor":
                    layers["floor" if floors == 0 else "floor2"][(c, r)] = (source, local)
                    floors += 1
                elif role in ("bg", "wall"):
                    layers[role][(c, r)] = (source, local)

    # what the style draws under/above its goal (e.g. stairs in the bridge style);
    # the part above is only used where that field is floor as well
    if pack.goal_decor:
        decor = pack.goal_decor.most_common(1)[0][0]
        for r in range(GRID_H):
            for c in range(GRID_W):
                if grid[r][c] != "Z":
                    continue
                for dx, dy, source, local in decor:
                    x, y = c + dx, r + dy
                    if dy == 0 or (0 <= y < GRID_H and terrain[y][x] == FLOOR):
                        layers["floor2"][(x, y)] = (source, local)

    # objects
    objects, cell_to_id = [], {}
    number = header.get("hero", ["7"])[0]
    direction = header.get("start", ["south"])[0]
    if direction not in DIRECTIONS:
        raise MapError(f"start must be one of {', '.join(DIRECTIONS)}, not {direction!r}")
    for r in range(GRID_H):
        for c in range(GRID_W):
            ch, context = grid[r][c], terrain[r][c]
            name = ""
            if ch == "H":
                cls, name = "Character", "MainCharacter"
                tile = pack.hero.get(f"{direction}_{number}")
                if not tile:
                    raise MapError(f"no hero sprite {number!r} (hero: 0 to 15)")
            elif ch in ("T", "t"):
                cls, tile = "Torch", pack.object_tile("Torch", context)
                if tile and ch == "t":
                    # the "off" tile of the same torch kind: the nearest "off" id in its tileset
                    off = pack.torch_off.get(tile[0])
                    if off:
                        tile = (tile[0], min(off, key=lambda tid: abs(tid - tile[1])))
            elif ch in ("D", "G"):
                # a door in a vertical wall line (walls above and below) blocks an east-west passage
                solid = (WALL, "T", "t")
                vertical = (0 < r < GRID_H - 1 and grid[r - 1][c] in solid and grid[r + 1][c] in solid)
                base = "Door" if ch == "D" else "Grille"
                cls = "Vertical" + base if vertical else base
                tile = pack.object_tile(cls, FLOOR) or pack.object_tile(base, FLOOR)
            elif ch == "*":
                cls, tile = "Sweets", pack.sweets
            elif ch == "K":
                cls, tile = "Crystal", (ICON_SHEET, CRYSTAL_TILES["weiss"])
            elif ch == "o":
                cls, tile = "Pebble", (ICON_SHEET, PEBBLE_TILE)
            elif ch in OBJECT_CLASSES:
                cls = OBJECT_CLASSES[ch]
                tile = pack.object_tile(cls, context)
            elif ch in (WALL, FLOOR, VOID, ABYSS):
                continue
            else:
                raise MapError(f"unknown symbol {ch!r} at ({c - ox},{r - oy})")
            if not tile:
                raise MapError(f"no tile known for {ch!r} at ({c - ox},{r - oy})")
            objects.append({"cell": (c, r), "tile": tile, "name": name, "cls": cls})

    crystals = [o for o in objects if o["cls"] == "Crystal"]
    values = " ".join(header.get("values", [])).replace(",", " ").split()
    colors = " ".join(header.get("colors", [])).replace(",", " ").split()
    if crystals or values:
        if len(values) != len(crystals):
            raise MapError(f"values: {len(values)} value(s) for {len(crystals)} crystal(s) K")
        try:
            values = [int(v) for v in values]
        except ValueError:
            raise MapError(f"values: whole numbers expected, got {' '.join(values)!r}") from None
    if colors:
        if len(colors) != len(crystals) or set(colors) - set(CRYSTAL_TILES):
            raise MapError(f"colors: one of {', '.join(CRYSTAL_TILES)} per crystal K")
        for o, color in zip(crystals, colors):
            o["tile"] = (ICON_SHEET, CRYSTAL_TILES[color])
    for o, value in zip(crystals, values):
        o["properties"] = [{"name": "value", "type": "int", "value": value}]

    def tileset_info(source):
        return pack.tilesets.get(source) or ITEM_TILESETS[source]

    # tilesets: every source used, in a stable order
    used = sorted({t[0] for layer in layers.values() for t in layer.values()} | {o["tile"][0] for o in objects})
    firstgid, tilesets = {}, []
    next_gid = 1
    for source in used:
        firstgid[source] = next_gid
        tilesets.append({"firstgid": next_gid, "source": source})
        next_gid += tileset_info(source)["count"]

    def gid(tile):
        return firstgid[tile[0]] + tile[1]

    def tile_layer(layer_id, name, cells, collision=False):
        data = [gid(cells[(c, r)]) if (c, r) in cells else 0 for r in range(GRID_H) for c in range(GRID_W)]
        layer = {"data": data, "height": GRID_H, "id": layer_id, "name": name, "opacity": 1,
                 "type": "tilelayer", "visible": True, "width": GRID_W, "x": 0, "y": 0}
        if collision:
            layer["properties"] = [{"name": "collision", "type": "bool", "value": True}]
        return layer

    tiled_objects = []
    for i, o in enumerate(objects, start=1):
        info = tileset_info(o["tile"][0])
        c, r = o["cell"]
        # the engine takes the class from the object's `type`, else from its tile;
        # some tiles (e.g. goals) carry no class, so set it explicitly then
        tile_cls = info["classes"].get(o["tile"][1], "")
        obj_type = "" if tile_cls == o["cls"] or o["cls"] == "Character" else o["cls"]
        # where the style draws its goal as decoration (e.g. stairs), the goal object is
        # an invisible marker; the engine only needs its position
        visible = not (o["cls"] == "Goal" and pack.goal_decor)
        tiled_objects.append({"gid": gid(o["tile"]), "height": info["tile_h"], "id": i, "name": o["name"],
                              "rotation": 0, "type": obj_type, "visible": visible, "width": info["tile_w"],
                              "x": c * 16, "y": (r + 1) * 16})
        if o.get("properties"):
            tiled_objects[-1]["properties"] = o["properties"]
        cell_to_id[(c - ox, r - oy)] = i
    # pattern doors: "pattern: X,Y = 101 @ x1,y1 x2,y2 x3,y3" (door, bits, torches in bit order)
    for spec in header.get("pattern", []):
        try:
            door_part, rest = spec.split("=", 1)
            bits, torch_part = rest.split("@", 1)
            door = tuple(int(v) for v in door_part.split(","))
            torches = [tuple(int(v) for v in t.split(",")) for t in torch_part.split()]
            bits = bits.strip()
        except ValueError:
            raise MapError(f"pattern: expected 'X,Y = 101 @ x1,y1 x2,y2 x3,y3', got {spec!r}") from None
        if len(bits) != len(torches) or set(bits) - {"0", "1"}:
            raise MapError(f"pattern {spec!r}: need one 0/1 per torch")
        for cell in [door] + torches:
            if cell not in cell_to_id:
                raise MapError(f"pattern {spec!r}: no object at {cell}")
        obj = tiled_objects[cell_to_id[door] - 1]
        obj["type"] = "PatternDoor"
        obj["properties"] = [{"name": "pattern", "type": "string", "value": bits},
                             {"name": "torches", "type": "string",
                              "value": ",".join(str(cell_to_id[t]) for t in torches)}]

    for wiring in header.get("controls", []):
        try:
            src, dst = (tuple(int(v) for v in part.split(",")) for part in wiring.split("->"))
        except ValueError:
            raise MapError(f"controls: expected 'x,y -> x,y', got {wiring!r}") from None
        if src not in cell_to_id or dst not in cell_to_id:
            raise MapError(f"controls {wiring}: no object at {src if src not in cell_to_id else dst}")
        obj = tiled_objects[cell_to_id[src] - 1]
        obj["properties"] = [{"name": "controls", "type": "object", "value": cell_to_id[dst]}]

    properties = []
    for key, values in header.items():
        if key in HEADER_KEYS:
            continue
        value = values[0]
        if value.lower() in ("true", "false"):
            properties.append({"name": key, "type": "bool", "value": value.lower() == "true"})
        elif value.lstrip("-").isdigit():
            properties.append({"name": key, "type": "int", "value": int(value)})
        else:
            properties.append({"name": key, "type": "string", "value": value})

    level = {
        "compressionlevel": -1, "height": GRID_H, "width": GRID_W, "infinite": False,
        "layers": [
            tile_layer(1, "Background", layers["bg"]),
            tile_layer(2, "Floor", layers["floor"]),
            tile_layer(3, "Floor2", layers["floor2"]),
            tile_layer(4, "Walls", layers["wall"], collision=True),
            {"draworder": "topdown", "id": 5, "name": "Objects", "objects": tiled_objects, "opacity": 1,
             "type": "objectgroup", "visible": True, "x": 0, "y": 0},
        ],
        "nextlayerid": 6, "nextobjectid": len(tiled_objects) + 1, "orientation": "orthogonal",
        "renderorder": "right-down", "tiledversion": "1.11.2", "tileheight": 16, "tilewidth": 16,
        "tilesets": tilesets, "type": "map", "version": "1.10",
    }
    if properties:
        level["properties"] = properties
    return level, terrain


def level_from_text(text, style=None):
    """The level (Tiled JSON dict) for the text of a map file. The style comes from
    the argument, else from the header ("style: bridge"), else "dungeon"."""
    header, rows = parse_text(text)
    style = style or header.get("style", ["dungeon"])[0]
    return build(header, rows, Pack.load(style))[0]


def level_from_file(path, style=None):
    with open(path, encoding="utf-8") as f:
        return level_from_text(f.read(), style)
