"""Levels from ASCII maps: `Game("karte.txt")` builds the level from a text file.

A map file has an optional header, a line "---", and the map:

    start: north             # hero's start direction (default south)
    hero: 7                  # hero sprite 0-15 (default 7)
    style: dungeon           # tile style: dungeon (default), corridor, arena, bridge, maze;
                             # other worlds: station (a hospital ward), studio (a light studio),
                             # werkstatt (a production hall), gelaende (a survey area)
    controls: 8,8 -> 25,10   # switch/torch at (8,8) toggles the object at (25,10); repeatable
    pattern: 5,2 = 101 @ 2,0 3,0 4,0   # door at (5,2) is open exactly while these torches show 101
    values: 5 3 8            # weights of the crystals K, in reading order (never drawn)
    colors: weiss orange weiss  # optional: colour of each crystal (weiss or orange)
    guards: 5,2 patrol east  # guard W at (5,2) walks east and back; "x,y chase" follows the hero
    orakel: true             # the level has an oracle (hero.ask_oracle())
    view: fit                # show only the map, with larger fields (default: full, the 30x20 field)
    deko: 6                  # scatter small details on 6 % of the plain floor and walls (seeded, default 0)
    fog: dark                # any other key becomes a map property (bool/int/str)
    ---
    ##########
    #H..s....#
    #....D...Z
    ##########

Legend:  #  wall      .  floor     ~  abyss     (blank)  nothing
         H  hero      Z  goal      T/t  torch (burning/off, on a wall)
         s  switch    D  door      G  grille    C  chest    J  jug    *  sweets
         K  crystal   o  pebble    W  guard (see guards:)
Decoration (looks only; where a style has no pictures for it, x is a wall and , " are floor):
         x  an obstacle: furniture, crates, a rock, a tree (a wall for the rules)
         ,  a path or carpet; neighbouring fields join up       "  a small detail on the floor
         A block of touching x that is a rectangle of exactly the size of one of the style's large
         props becomes that prop (a 5 x 3 house, a 2 x 2 tank); any other block is filled with the
         style's filling props, largest first (trees, rocks, benches), the rest with small ones.
In another world the same symbols mean that world's things: in `station`, K is a bed
(class "Bett"), * a sample ("Probe"), o a floor mark ("Markierung"), T a lamp, ~ stairs;
in `studio`, K is a sketch ("Entwurf"), * a colour gel ("Farbfolie"), o a tape mark
("Klebepunkt"), T one lamp of the display, ~ the edge of the stage; in `werkstatt`, K is a
workpiece ("Teil"), * a load carrier ("Kiste"), o a floor mark ("Marke"), ~ a danger zone,
W a person; in `gelaende`, K is a survey point ("Messpunkt"), * a soil sample
("Bodenprobe"), o a stake ("Pflock"), # woods, ~ water.

Coordinates are 0-based (column, row) in the map as written. The map is placed
centred on the 30x20 game field (a larger map makes the field as large as the map);
with "view: fit" the level is then cut to the map and one field around it, so the
game shows it larger.

The goal Z is drawn facing the way the hero comes in, where the style has exits
for the four directions (stairs going down away from the hero).

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
HEADER_KEYS = ("start", "hero", "style", "controls", "pattern", "values", "colors", "guards", "view", "deko")
PROP, PATH, DETAIL = "x", ",", '"'      # decoration symbols
OFFSETS = {"north": (0, -1), "east": (1, 0), "south": (0, 1), "west": (-1, 0)}
VIEWS = ("full", "fit")
GUARD_SPRITE = 3            # the characters tileset's sprite number used for guards
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
    """Terrain under an ASCII symbol. Torches always stand on a wall or a pedestal; an
    obstacle x is a wall for the rules."""
    if ch in (WALL, "T", "t", PROP):
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
        self.abyss_tiles = []   # [(source, local)] tiles of class Abyss; the first is the plain fallback
        self.tile_size = 16     # pixels per field in the style's levels (their tilewidth)
        self.items = {}         # symbol -> (source, local, class): a world's own items for K, * and o
        self.world = None       # name of the world (not the dungeon): the game shows its end screens
        self.guard_sprite = GUARD_SPRITE    # the figure number of the agents "W"
        # decoration (optional; tiles are (source, local)):
        self.props = []         # obstacles x: [their tile, tile drawn into the field behind them or None]
        self.big_props = []     # large obstacles: {"w", "h", "fill", "parts": [(dx, dy, source, local)]}: a part
                                # per field of the w x h footprint (walls), parts outside it (a crown) are deko;
                                # "fill": may fill blocks of other sizes (trees), else only a block of its size
        self.paths = {}         # paths ",": 8-neighbour mask ("0"/"1" in NEIGHBOURS order) -> tile
        self.details = []       # small details '"' on the floor
        self.wall_variants = {}  # wall tile -> [decorated variants] (deko:)
        self.exits = {}         # walking direction into the goal -> (source, local, Tiled flip flags)

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
            "abyss_tiles": [list(t) for t in self.abyss_tiles],
            **({"tile_size": self.tile_size} if self.tile_size != 16 else {}),
            **({"items": {k: list(v) for k, v in self.items.items()}} if self.items else {}),
            **({"world": self.world} if self.world else {}),
            **({"guard_sprite": self.guard_sprite} if self.guard_sprite != GUARD_SPRITE else {}),
            **({"props": [[list(b), list(t) if t else None] for b, t in self.props]} if self.props else {}),
            **({"big_props": [{"w": p["w"], "h": p["h"], "fill": p["fill"], "parts": [list(t) for t in p["parts"]]}
                              for p in self.big_props]} if self.big_props else {}),
            **({"paths": {k: list(v) for k, v in self.paths.items()}} if self.paths else {}),
            **({"details": [list(t) for t in self.details]} if self.details else {}),
            **({"wall_variants": [[list(k), [list(t) for t in v]] for k, v in self.wall_variants.items()]}
               if self.wall_variants else {}),
            **({"exits": {k: list(v) for k, v in self.exits.items()}} if self.exits else {}),
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
        pack.abyss_tiles = [tuple(t) for t in data.get("abyss_tiles", [])]
        pack.tile_size = data.get("tile_size", 16)
        pack.items = {k: tuple(v) for k, v in data.get("items", {}).items()}
        pack.world = data.get("world")
        pack.guard_sprite = data.get("guard_sprite", GUARD_SPRITE)
        pack.props = [(tuple(b), tuple(t) if t else None) for b, t in data.get("props", [])]
        pack.big_props = [{"w": p["w"], "h": p["h"], "fill": p.get("fill", False), "parts": [tuple(t) for t in p["parts"]]}
                          for p in data.get("big_props", [])]
        pack.paths = {k: tuple(v) for k, v in data.get("paths", {}).items()}
        pack.details = [tuple(t) for t in data.get("details", [])]
        pack.wall_variants = {tuple(k): [tuple(t) for t in v] for k, v in data.get("wall_variants", [])}
        pack.exits = {k: tuple(v) for k, v in data.get("exits", {}).items()}
        return pack

    @classmethod
    def load(cls, style):
        """The pack of a style. An asset pack in DC_ASSET_PACKS may bring its own packs
        (styles/<style>.json, first pack wins, as for tilesets in the game): so a private
        pack can draw a style with other art than the one shipped here."""
        folders = [os.path.join(p, "styles") for p in os.environ.get("DC_ASSET_PACKS", "").split(os.pathsep) if p]
        path = next((os.path.join(d, f"{style}.json") for d in folders + [PACK_DIR]
                     if os.path.exists(os.path.join(d, f"{style}.json"))), None)
        if path is None:
            styles = sorted(f[:-5] for f in os.listdir(PACK_DIR) if f.endswith(".json") and f != "tilesets.json")
            raise MapError(f"unknown style {style!r}; available: {', '.join(styles)}")
        with open(path, encoding="utf-8") as f:
            return cls.from_json(json.load(f))


def _hash(c, r, salt=0):
    """A fixed pseudo-random number per field: the same map always gets the same decoration."""
    h = (c * 73856093) ^ (r * 19349663) ^ (salt * 83492791)
    return (h ^ (h >> 13)) & 0x7FFFFFFF


def exit_direction(grid, c, r):
    """The direction the hero walks into the goal at (c, r): from its one open neighbour;
    with several, the one whose opposite side is solid (stairs lead into the wall)."""
    h, w = len(grid), len(grid[0])

    def at(x, y):
        return grid[y][x] if 0 <= x < w and 0 <= y < h else VOID

    def open_(ch):
        return ch not in (WALL, "T", "t", PROP, VOID, ABYSS)
    options = [d for d, (dx, dy) in OFFSETS.items() if open_(at(c - dx, r - dy))]
    if not options:
        return None
    solid = [d for d in options if not open_(at(c + OFFSETS[d][0], r + OFFSETS[d][1]))]
    return (solid or options)[0]


def decorate(grid, terrain, layers, pack, header):
    """The decoration of a map (it changes no rule): obstacles x, paths ",", details '"',
    and with "deko: N" small details on N % of the plain floor and decorated walls."""
    try:
        density = int(header.get("deko", ["0"])[0])
    except ValueError:
        raise MapError(f"deko: a whole number (percent) expected, got {header['deko'][0]!r}") from None
    h, w = len(grid), len(grid[0])

    def is_path(x, y):
        return 0 <= x < w and 0 <= y < h and grid[y][x] == PATH
    # obstacles that touch form one group and get the same picture (a row of machines, of trees)
    group = {}
    for r in range(h):
        for c in range(w):
            if grid[r][c] == PROP and (c, r) not in group:
                todo = [(c, r)]
                while todo:
                    x, y = todo.pop()
                    if (x, y) in group or not (0 <= x < w and 0 <= y < h) or grid[y][x] != PROP:
                        continue
                    group[(x, y)] = (c, r)
                    todo += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    big = place_big_props(grid, terrain, layers, pack, group)
    for r in range(h):
        for c in range(w):
            ch = grid[r][c]
            if (c, r) in big:
                continue
            if ch == PROP and pack.props:
                bottom, top = pack.props[_hash(*group[(c, r)], 1) % len(pack.props)]
                layers["wall"][(c, r)] = bottom
                if top and r > 0 and terrain[r - 1][c] in (FLOOR, WALL):
                    layers["deko"][(c, r - 1)] = top
            elif ch == PATH and pack.paths:
                layers["floor2"][(c, r)] = pack.paths.get(path_mask(is_path, c, r), pack.paths.get("0" * 8))
            elif ch == DETAIL and pack.details:
                layers["floor2"][(c, r)] = pack.details[_hash(c, r, 2) % len(pack.details)]
            elif not density:
                continue
            elif ch == FLOOR and pack.details and (c, r) not in layers["floor2"] and _hash(c, r, 3) % 100 < density:
                layers["floor2"][(c, r)] = pack.details[_hash(c, r, 2) % len(pack.details)]
            elif ch == WALL and layers["wall"].get((c, r)) in pack.wall_variants and _hash(c, r, 4) % 100 < 2 * density:
                variants = pack.wall_variants[layers["wall"][(c, r)]]
                layers["wall"][(c, r)] = variants[_hash(c, r, 5) % len(variants)]


def deko_layer(n):
    """Name of the n-th deko layer (1: "deko"; more where large props overlap)."""
    return "deko" if n == 1 else f"deko{n}"


def place_big_props(grid, terrain, layers, pack, group):
    """Large obstacles. A block of touching x (two fields or more) that is a rectangle of a
    prop's footprint size becomes that prop (several of that size: chosen by position). Any other block is filled in
    reading order with the largest filling prop that still fits; what is left gets the small
    props. Every field of a footprint gets its own wall tile, so the rules see the same walls
    as with small props. Parts outside the footprint (above it, or a crown wider than the
    trunk) go into the deko layers (the later prop's on top). Returns the fields covered."""
    covered = set()
    if not pack.big_props:
        return covered
    h, w = len(grid), len(grid[0])
    blocks = collections.defaultdict(set)
    for cell, anchor in group.items():
        blocks[anchor].add(cell)

    def put(prop, c, r):
        for dx, dy, source, local in prop["parts"]:
            x, y = c + dx, r + dy
            if 0 <= dx < prop["w"] and 0 <= dy < prop["h"]:
                layers["wall"][(x, y)] = (source, local)
                covered.add((x, y))
            elif 0 <= y < h and 0 <= x < w and terrain[y][x] in (FLOOR, WALL):
                n = 1                       # the first deko layer that is free here; a new one if none
                while (x, y) in layers.setdefault(deko_layer(n), {}):
                    n += 1
                layers[deko_layer(n)][(x, y)] = (source, local)

    fillers = [p for p in pack.big_props if p["fill"]]
    for anchor in sorted(blocks, key=lambda a: (a[1], a[0])):
        cells = blocks[anchor]
        x0, y0 = min(c for c, _ in cells), min(r for _, r in cells)
        bw, bh = max(c for c, _ in cells) - x0 + 1, max(r for _, r in cells) - y0 + 1
        # a single field keeps the style's small props (their variety); a full rectangle of a prop's size is that prop
        exact = ([p for p in pack.big_props if (p["w"], p["h"]) == (bw, bh)]
                 if len(cells) == bw * bh > 1 else [])
        if exact:
            put(exact[_hash(x0, y0, 6) % len(exact)], x0, y0)
            continue
        for c, r in sorted(cells, key=lambda a: (a[1], a[0])):
            if (c, r) in covered:
                continue
            fitting = [p for p in fillers
                       if all((c + dx, r + dy) in cells and (c + dx, r + dy) not in covered
                              for dx in range(p["w"]) for dy in range(p["h"]))]
            if fitting:
                largest = max(p["w"] * p["h"] for p in fitting)
                options = [p for p in fitting if p["w"] * p["h"] == largest]
                put(options[_hash(c, r, 6) % len(options)], c, r)
    return covered


def path_mask(same, c, r):
    """The 8-neighbour mask of a path field ("1" = path there, NEIGHBOURS order); a diagonal
    counts only where both fields beside it are path too (it changes nothing otherwise)."""
    bits = {d: same(c + d[0], r + d[1]) for d in NEIGHBOURS}
    for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        bits[(dx, dy)] = bits[(dx, dy)] and bits[(dx, 0)] and bits[(0, dy)]
    return "".join("1" if bits[d] else "0" for d in NEIGHBOURS)


def build(header, rows, pack, seed=0, variety=0.0):
    """(level as a Tiled JSON dict, terrain grid) for a parsed map."""
    height, width = len(rows), max((len(r) for r in rows), default=0)
    if sum(row.count("H") for row in rows) != 1:
        raise MapError(f"the map needs exactly one hero H, it has {sum(row.count('H') for row in rows)}")
    grid_w, grid_h = max(GRID_W, width), max(GRID_H, height)       # a larger map, a larger field
    ox, oy = (grid_w - width) // 2, (grid_h - height) // 2
    grid = [[VOID] * grid_w for _ in range(grid_h)]
    for r, line in enumerate(rows):
        for c, ch in enumerate(line):
            grid[r + oy][c + ox] = ch

    terrain = [[base_terrain(ch) for ch in row] for row in grid]
    # an obstacle x stands on floor: its neighbours see floor, it gets the floor's tiles and the
    # obstacle's picture on the wall layer; without pictures for obstacles it is a wall
    looks = [[FLOOR if ch == PROP and pack.props else t for ch, t in zip(row, trow)]
             for row, trow in zip(grid, terrain)]

    rng = random.Random(seed)
    layers = {"bg": {}, "floor": {}, "floor2": {}, "wall": {}, "deko": {}}
    chosen = {}
    for r in range(grid_h):
        for c in range(grid_w):
            if pack.neighbour_fit:
                left, up = chosen.get((c - 1, r)), chosen.get((c, r - 1))
            else:
                left = up = None      # no constraint: the most frequent stack for the pattern
            stack = pack.choose(pattern(looks, c, r), left, up, rng, variety)
            if terrain[r][c] == ABYSS and pack.abyss_tiles and not (
                    stack and (stack[-1][1], stack[-1][2]) in {tuple(t) for t in pack.abyss_tiles}):
                # the game only sees an abyss where an Abyss tile is the topmost tile
                source, local = pack.abyss_tiles[0]
                stack = (("floor", source, local),)
            chosen[(c, r)] = stack
            floors = 0
            for role, source, local in stack:
                if role == "floor":
                    layers["floor" if floors == 0 else "floor2"][(c, r)] = (source, local)
                    floors += 1
                elif role in ("bg", "wall"):
                    layers[role][(c, r)] = (source, local)

    decorate(grid, terrain, layers, pack, header)

    # what the style draws under/above its goal (e.g. stairs in the bridge style);
    # the part above is only used where that field is floor as well
    if pack.goal_decor:
        decor = pack.goal_decor.most_common(1)[0][0]
        for r in range(grid_h):
            for c in range(grid_w):
                if grid[r][c] != "Z":
                    continue
                # the stairs climb eastwards: mirrored when the hero comes in walking west
                flags = 0x80000000 if exit_direction(grid, c, r) == "west" else 0
                for dx, dy, source, local in decor:
                    x, y = c + dx, r + dy
                    if dy == 0 or (0 <= y < grid_h and terrain[y][x] == FLOOR):
                        layers["floor2"][(x, y)] = (source, local, flags) if flags else (source, local)

    # objects
    objects, cell_to_id = [], {}
    number = header.get("hero", ["7"])[0]
    direction = header.get("start", ["south"])[0]
    if direction not in DIRECTIONS:
        raise MapError(f"start must be one of {', '.join(DIRECTIONS)}, not {direction!r}")
    for r in range(grid_h):
        for c in range(grid_w):
            ch, context = grid[r][c], terrain[r][c]
            name = ""
            if ch == "H":
                cls, name = "Character", "MainCharacter"
                tile = pack.hero.get(f"{direction}_{number}")
                if not tile:
                    raise MapError(f"no hero sprite {number!r} (hero: 0 to 15)")
            elif ch in pack.items:
                source, local, cls = pack.items[ch]       # the world's own item for this symbol
                tile = (source, local)
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
                vertical = (0 < r < grid_h - 1 and grid[r - 1][c] in solid and grid[r + 1][c] in solid)
                base = "Door" if ch == "D" else "Grille"
                cls = "Vertical" + base if vertical else base
                tile = pack.object_tile(cls, FLOOR) or pack.object_tile(base, FLOOR)
            elif ch == "*":
                cls, tile = "Sweets", pack.sweets
            elif ch == "K":
                cls, tile = "Crystal", (ICON_SHEET, CRYSTAL_TILES["weiss"])
            elif ch == "o":
                cls, tile = "Pebble", (ICON_SHEET, PEBBLE_TILE)
            elif ch == "W":
                cls, tile = "Guard", pack.hero.get(f"south_{pack.guard_sprite}")
            elif ch == "Z" and exit_direction(grid, c, r) in pack.exits:
                cls, tile = "Goal", pack.exits[exit_direction(grid, c, r)]   # facing the hero's way in
            elif ch in OBJECT_CLASSES:
                cls = OBJECT_CLASSES[ch]
                tile = pack.object_tile(cls, context)
            elif ch in (WALL, FLOOR, VOID, ABYSS, PROP, PATH, DETAIL):
                continue
            else:
                raise MapError(f"unknown symbol {ch!r} at ({c - ox},{r - oy})")
            if not tile:
                raise MapError(f"no tile known for {ch!r} at ({c - ox},{r - oy})")
            objects.append({"cell": (c, r), "tile": tile, "name": name, "cls": cls, "symbol": ch})

    crystals = [o for o in objects if o["symbol"] == "K"]        # the items that carry a value
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

    guard_specs = {}
    for spec in header.get("guards", []):
        parts = spec.replace(",", " ").split()
        try:
            x, y, behaviour = int(parts[0]), int(parts[1]), parts[2]
        except (ValueError, IndexError):
            raise MapError(f"guards: expected 'x,y patrol east' or 'x,y chase', got {spec!r}") from None
        direction = parts[3] if len(parts) > 3 else "east"
        if behaviour not in ("patrol", "chase") or direction not in DIRECTIONS:
            raise MapError(f"guards {spec!r}: behaviour patrol or chase, direction one of {', '.join(DIRECTIONS)}")
        guard_specs[(x + ox, y + oy)] = (behaviour, direction)
    for o in objects:
        if o["cls"] == "Guard":
            behaviour, direction = guard_specs.pop(o["cell"], ("patrol", "east"))
            o["properties"] = [{"name": "behaviour", "type": "string", "value": behaviour},
                               {"name": "direction", "type": "string", "value": direction}]
            o["tile"] = pack.hero.get(f"{direction if behaviour == 'patrol' else 'south'}_{pack.guard_sprite}") or o["tile"]
    if guard_specs:
        x, y = next(iter(guard_specs))
        raise MapError(f"guards: no guard W at ({x - ox},{y - oy})")

    # tilesets: every source used, in a stable order
    used = sorted({t[0] for layer in layers.values() for t in layer.values()} | {o["tile"][0] for o in objects})
    firstgid, tilesets = {}, []
    next_gid = 1
    for source in used:
        firstgid[source] = next_gid
        tilesets.append({"firstgid": next_gid, "source": source})
        next_gid += tileset_info(source)["count"]

    def gid(tile):
        """The global id; a third element are Tiled's flip flags (a mirrored exit)."""
        return firstgid[tile[0]] + tile[1] + (tile[2] if len(tile) > 2 else 0)

    def tile_layer(layer_id, name, cells, collision=False):
        data = [gid(cells[(c, r)]) if (c, r) in cells else 0 for r in range(grid_h) for c in range(grid_w)]
        layer = {"data": data, "height": grid_h, "id": layer_id, "name": name, "opacity": 1,
                 "type": "tilelayer", "visible": True, "width": grid_w, "x": 0, "y": 0}
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
                              "x": c * pack.tile_size, "y": (r + 1) * pack.tile_size})
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

    properties = [{"name": "world", "type": "string", "value": pack.world}] if pack.world else []
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

    # what reaches from obstacles into other fields (tops, crowns), in as many layers as overlap there
    deko_layers, n = [], 1
    while layers.get(deko_layer(n)):
        deko_layers.append(tile_layer(5 + n, "Deko" if n == 1 else f"Deko{n}", layers[deko_layer(n)]))
        n += 1
    level = {
        "compressionlevel": -1, "height": grid_h, "width": grid_w, "infinite": False,
        "layers": [
            tile_layer(1, "Background", layers["bg"]),
            tile_layer(2, "Floor", layers["floor"]),
            tile_layer(3, "Floor2", layers["floor2"]),
            tile_layer(4, "Walls", layers["wall"], collision=True),
        ] + deko_layers + [
            # what reaches from an obstacle into the field behind it: below the figures (a hero
            # behind a tree stays visible), above the walls
            {"draworder": "topdown", "id": 5, "name": "Objects", "objects": tiled_objects, "opacity": 1,
             "type": "objectgroup", "visible": True, "x": 0, "y": 0},
        ],
        "nextlayerid": 6 + len(deko_layers), "nextobjectid": len(tiled_objects) + 1, "orientation": "orthogonal",
        "renderorder": "right-down", "tiledversion": "1.11.2", "tileheight": pack.tile_size,
        "tilewidth": pack.tile_size,
        "tilesets": tilesets, "type": "map", "version": "1.10",
    }
    if properties:
        level["properties"] = properties
    view = header.get("view", ["full"])[0]
    if view not in VIEWS:
        raise MapError(f"view must be one of {', '.join(VIEWS)}, not {view!r}")
    if view == "fit":
        return fit_view(level, terrain)
    return level, terrain


def fit_view(level, terrain):
    """(level, terrain) cut to the map and one field around it (where the styles draw the
    fronts and edges of the outer walls). The game's view is as large as the level, so
    a smaller level has larger fields."""
    width, height, tw, th = level["width"], level["height"], level["tilewidth"], level["tileheight"]
    cells = {(c + dx, r + dy) for r, row in enumerate(terrain) for c, t in enumerate(row) if t != VOID
             for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    cells = {(c, r) for c, r in cells if 0 <= c < width and 0 <= r < height}
    if not cells:
        return level, terrain
    x0, x1 = min(c for c, _ in cells), max(c for c, _ in cells)
    y0, y1 = min(r for _, r in cells), max(r for _, r in cells)
    new_width, new_height = x1 - x0 + 1, y1 - y0 + 1
    for layer in level["layers"]:
        if "data" in layer:
            layer["data"] = [layer["data"][r * width + c] for r in range(y0, y1 + 1) for c in range(x0, x1 + 1)]
            layer["width"], layer["height"] = new_width, new_height
        for o in layer.get("objects", []):
            o["x"] -= x0 * tw
            o["y"] -= y0 * th
    level["width"], level["height"] = new_width, new_height
    return level, [row[x0:x1 + 1] for row in terrain[y0:y1 + 1]]


def level_from_text(text, style=None):
    """The level (Tiled JSON dict) for the text of a map file. The style comes from
    the argument, else from the header ("style: bridge"), else "dungeon"."""
    header, rows = parse_text(text)
    style = style or header.get("style", ["dungeon"])[0]
    return build(header, rows, Pack.load(style))[0]


def level_from_file(path, style=None):
    with open(path, encoding="utf-8") as f:
        return level_from_text(f.read(), style)
