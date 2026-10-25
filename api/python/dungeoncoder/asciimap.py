"""Levels from ASCII maps: `Game("karte.txt")` builds the level from a text file.

A map file has an optional header, a line "---", and the map:

    start: north             # hero's start direction (default south); several heroes: one each
                             # in order (H, 2, 3, ...), e.g. "start: east south west"
    hero: 7                  # hero sprite 0-15 (default 7); a co-op map: one per hero, "hero: 7 13 1"
    style: dungeon           # tile style: dungeon (default), corridor, arena, bridge, maze
                             # (these five come with the course's asset pack; without it the
                             # default is demo, the free demo pack's dungeon);
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
    muster: alle             # the looks of good hand-built levels (looks only, see below): wandansicht,
                             # requisiten, bogen, aussen, gruben, knochen, flecken, vielfalt, or alle for all
    raum: lager 1,1 8,6      # furnish the room whose floor is this rectangle (both corners inclusive)
                             # after the style's blueprint for that room type (see below); repeatable
    region: s 2,2 17,13      # variants: the switches s in this rectangle may lie on any of its
                             # free fields; Game("karte.txt", seed=17) picks one (variants.py)
    fog: dark                # any other key becomes a map property (bool/int/str)
    ---
    ##########
    #H..s....#
    #....D...Z
    ##########

A header with "generate: maze" (or rooms, pillars) makes the file a recipe: the level is generated,
with "size: 15x11", "loops: 2" and "seed: random" (a new level per load) or a number (generator.py).

Legend:  #  wall      .  floor     ~  abyss     (blank)  nothing
         H  hero      Z  goal      T/t  torch (burning/off, on a wall)
         2 … 9  more heroes (a co-op level: Game.get_heroes(), win: all_heroes)
         s  switch    D  door      G  grille    C  chest    J  jug    *  sweets
         K  crystal   o  pebble    W  guard (see guards:)
Decoration (looks only; where a style has no pictures for it, x is a wall and , " are floor):
         x  an obstacle: furniture, crates, a rock, a tree (a wall for the rules)
         ,  a path or carpet; neighbouring fields join up       "  a small detail on the floor
         :  a second floor tone (an earth floor in a stone room; neighbouring rooms differ)
         A block of touching x that is a rectangle of exactly the size of one of the style's large
         props becomes that prop (a 5 x 3 house, a 2 x 2 tank); any other block is filled with the
         style's filling props, largest first (trees, rocks, benches), the rest with small ones.
The looks of "muster:" (each needs the style to bring the pictures; a map without the header is
built exactly as before):
         wandansicht  a wall at least two rows deep shows its front (bricks) in the row that faces
                      the hero, as the hand-built levels do; torches keep their wall top
         requisiten   an obstacle x under a wall gets a tall picture (barrels, crates, chains), in a
                      corner or beside another obstacle pots, elsewhere flat things (rubble, wood)
         bogen        an arch (layer Over, above the figures) over every doorway through a wall two
                      rows deep: a gap one field wide, with or without a door or grille, the arch's
                      legs on the walls beside it; and over a goal Z at the end of a dead end three
                      fields wide, reached walking north, which also gets a broad staircase
         aussen       the void beyond the walls is solid rock (a wall for the rules, instead of
                      walkable darkness)
         gruben       a pit ~ gets its rim (edges and corners) for any shape, also one field wide
         knochen      with gruben: bones on the floor around a pit
         flecken      "deko:" details gather in patches (smooth noise) instead of an even sprinkle
         vielfalt     floor tiles vary among the pieces the style uses (no two identical runs)
Room types for "raum:" (a style brings blueprints for some of: lager, thron, kerker, schlafsaal,
waffenkammer, arena, kammer in the dungeon; labor, buero, lager, pause in the station; halle,
lager, leitstand in the workshop; regie, buehne, lager in the studio; garten, hof, obstgarten,
weide in the survey area): furnishing puts obstacles x with fitting pictures along the north wall
and into corners (single pieces, wide pieces, or blocks that become the style's large props of
that size), a framed focal area or a large piece opposite the entrance with flanking pieces,
beds of crops or trees in a grid, a floor tone, and in the survey area fences for the room's
walls. Only plain floor fields change; fields next to an entrance stay free, so every door stays
usable; objects of the task are never touched. The obstacles are walls for the rules, so look at
the result (level2ascii) before writing a task on the map.
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
import importlib.util
import json
import os
import random

WALL, FLOOR, VOID, ABYSS = "#", ".", " ", "~"
GRID_W, GRID_H = 30, 20
OBJECT_CLASSES = {"s": "Switch", "C": "Chest", "J": "Jug", "Z": "Goal", "*": "Sweets"}
NEIGHBOURS = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
WEIGHTS = [1, 2, 1, 2, 2, 1, 2, 1]     # orthogonal neighbours matter more than diagonal ones
DIRECTIONS = ("north", "east", "south", "west")
HEADER_KEYS = ("start", "hero", "style", "controls", "pattern", "values", "colors", "guards", "view", "deko",
               "region", "generate", "size", "muster", "raum")
PROP, PATH, DETAIL = "x", ",", '"'      # decoration symbols
ALT = ":"                               # a second floor tone (an earth floor in a stone room): floor for the rules
DECORATION = (PROP, PATH, DETAIL, ALT)
# "muster:": the looks of good hand-built levels, switched on by their German names (docs/level-muster.md
# in the course workspace); a style brings the pictures for them in its recipe (learn_styles.py, decor)
LOOKS = {"wandansicht": "facade", "requisiten": "props", "bogen": "arch", "aussen": "outside", "gruben": "pits",
         "knochen": "bones", "flecken": "patches", "vielfalt": "variety"}
MUSTER_VARIETY = 0.25           # how often "vielfalt" takes another fitting floor tile
OFFSETS = {"north": (0, -1), "east": (1, 0), "south": (0, 1), "west": (-1, 0)}
VIEWS = ("full", "fit")
GUARD_SPRITE = 3            # the characters tileset's sprite number used for guards
EXTRA_HEROES = tuple("23456789")            # co-op heroes, after H (up to nine heroes in a level)
EXTRA_HERO_SPRITES = ["13", "1", "10", "3", "5", "8", "11", "14"]    # their sprites unless "hero:" names them
# items that aren't learned from the levels: K a crystal, o a pebble. Their tiles come from the
# asset packs' manifests (pack.json "items", as the engine's start inventory: sim.item_tiles);
# the colour of a crystal (header colors:) picks the item "Crystal" or "Crystal:<colour>"
CRYSTAL_ITEMS = {"weiss": "Crystal", "orange": "Crystal:orange"}
PACK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "packs")
NOT_STYLES = ("tilesets.json", "items.json")     # files in packs/ that aren't style packs
FREE_STYLE = "demo"     # the free demo pack's dungeon: the default when no asset pack has "dungeon"/"maze"


def _sim():
    """The simulator module (its tile rules and item tiles). This file is also loaded on its
    own (tools/ascii2level.py), so the sibling sim.py is loaded by path then."""
    try:
        from . import sim
    except ImportError:
        spec = importlib.util.spec_from_file_location(
            "dungeoncoder_sim", os.path.join(os.path.dirname(os.path.abspath(__file__)), "sim.py"))
        sim = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sim)
    return sim


def item_tile(item, symbol):
    """(tileset source, local id) of an item the builder places (K, o), from the packs."""
    tile = _sim().item_tiles().get(item)
    if tile is None:
        raise MapError(f"no tile for {symbol} ({item}): no asset pack names one (pack.json, \"items\")")
    return tile
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
        self.pack = None        # the asset pack the style's art comes from (map property pack, G5)
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
        self.rim = collections.defaultdict(collections.Counter)      # like stacks, for the outer rim (is_rim)
        # the looks of "muster:" (optional; tiles are (source, local), stairs may carry Tiled flip flags):
        self.facade = {}        # "left"/"mid"/"right": the front of a wall seen from the south; "opening": under an arch
        self.floor_alt = []     # tiles of the second floor tone ":"
        self.props_by_place = {}  # "tall" (an obstacle under a wall), "corner", "flat" -> [tiles]
        self.arch = {}          # "tile": the arch over doorways and a goal's alcove (3 fields wide, 2 high);
                                # "stairs": [left, mid, right] of the alcove's staircase
        self.outside = []       # tiles that fill the void beyond the walls (solid rock: a wall for the rules)
        self.pits = {}          # "frame": 8-neighbour mask -> abyss tile (like paths); "details": bones around a pit
        self.glass = None       # a fully transparent tile without class: the wall tile under a pinned picture whose
                                # local id is 0 (local 0 never counts as a wall), and the second field of a wide piece
        self.rooms = {}         # room type -> blueprint for "raum:": {"north": [piece], "corner": [piece],
                                # "focal": [w, h] (0, 0: the room minus a border), "focal_block": [w, h],
                                # "flank": [piece], "floor": ":" or ",", "beds": {"w", "h", "tiles"}, "walls": "zaun"};
                                # a piece is a tile, a list of tiles for consecutive fields (a bed two fields wide),
                                # or {"block": [w, h]}: a block of obstacles that becomes a large prop of that size
        self.fences = {}        # "h", "v", "left", "right", "post": wall tiles of a fence (blueprint "walls": "zaun")

    # --- choosing tiles ----------------------------------------------------
    def candidates(self, key, table=None):
        """Stacks seen for this exact pattern; otherwise those of the most similar patterns.
        table: where to look (default: the stacks; the rim's for a rim field)."""
        table = self.stacks if table is None else table
        if key in table:
            return table[key]
        center, neigh = key
        keys = [k for k in table if k[0] == center]
        if not keys:
            return collections.Counter({(): 1})
        best = max(similarity(k[1], neigh) for k in keys)
        merged = collections.Counter()
        for k in keys:
            if similarity(k[1], neigh) == best:
                merged.update(table[k])
        return merged

    def choose(self, key, left, up, rng, variety, rim=False):
        """Pick a stack for a cell: first of all it must *fit* the already chosen
        neighbours on the left and above (that pair occurs in the corpus), then it
        should be frequent for this neighbourhood. If no candidate of the pattern fits,
        look at stacks of patterns with the same orthogonal neighbours."""
        def fit(stack):
            return ((left is None or self.hpairs[(left, stack)] > 0)
                    + (up is None or self.vpairs[(up, stack)] > 0))

        if rim and self.rim:        # the outer rim drawn as the style's rim levels draw it (a shore, not a hedge)
            counter = self.candidates(key, self.rim)
            return sorted(counter, key=lambda s: (fit(s), counter[s]), reverse=True)[0]
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
            **({"pack": self.pack} if self.pack else {}),
            **({"guard_sprite": self.guard_sprite} if self.guard_sprite != GUARD_SPRITE else {}),
            **({"props": [[list(b), list(t) if t else None] for b, t in self.props]} if self.props else {}),
            **({"big_props": [{"w": p["w"], "h": p["h"], "fill": p["fill"], "parts": [list(t) for t in p["parts"]]}
                              for p in self.big_props]} if self.big_props else {}),
            **({"paths": {k: list(v) for k, v in self.paths.items()}} if self.paths else {}),
            **({"details": [list(t) for t in self.details]} if self.details else {}),
            **({"wall_variants": [[list(k), [list(t) for t in v]] for k, v in self.wall_variants.items()]}
               if self.wall_variants else {}),
            **({"exits": {k: list(v) for k, v in self.exits.items()}} if self.exits else {}),
            **({"rim": {k[0] + "".join(k[1]): [[ref(s), n] for s, n in counter.items()]
                        for k, counter in self.rim.items()}} if self.rim else {}),
            **({"facade": {k: list(v) for k, v in self.facade.items()}} if self.facade else {}),
            **({"floor_alt": [list(t) for t in self.floor_alt]} if self.floor_alt else {}),
            **({"props_by_place": {k: [list(t) for t in v] for k, v in self.props_by_place.items()}}
               if self.props_by_place else {}),
            **({"arch": {k: list(v) if k == "tile" else [list(t) for t in v] for k, v in self.arch.items()}}
               if self.arch else {}),
            **({"outside": [list(t) for t in self.outside]} if self.outside else {}),
            **({"pits": {"frame": {k: list(v) for k, v in self.pits.get("frame", {}).items()},
                         "details": [list(t) for t in self.pits.get("details", [])]}} if self.pits else {}),
            **({"glass": list(self.glass)} if self.glass else {}),
            **({"fences": {k: list(v) for k, v in self.fences.items()}} if self.fences else {}),
            **({"rooms": {name: {k: (v if k in BLUEPRINT_DATA else [piece_json(piece) for piece in v])
                                 for k, v in bp.items()} for name, bp in self.rooms.items()}} if self.rooms else {}),
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
        pack.pack = data.get("pack")
        pack.guard_sprite = data.get("guard_sprite", GUARD_SPRITE)
        pack.props = [(tuple(b), tuple(t) if t else None) for b, t in data.get("props", [])]
        pack.big_props = [{"w": p["w"], "h": p["h"], "fill": p.get("fill", False), "parts": [tuple(t) for t in p["parts"]]}
                          for p in data.get("big_props", [])]
        pack.paths = {k: tuple(v) for k, v in data.get("paths", {}).items()}
        pack.details = [tuple(t) for t in data.get("details", [])]
        pack.wall_variants = {tuple(k): [tuple(t) for t in v] for k, v in data.get("wall_variants", [])}
        pack.exits = {k: tuple(v) for k, v in data.get("exits", {}).items()}
        for key, entries in data.get("rim", {}).items():
            pack.rim[(key[0], tuple(key[1:]))] = collections.Counter({table[i]: n for i, n in entries})
        pack.facade = {k: tuple(v) for k, v in data.get("facade", {}).items()}
        pack.floor_alt = [tuple(t) for t in data.get("floor_alt", [])]
        pack.props_by_place = {k: [tuple(t) for t in v] for k, v in data.get("props_by_place", {}).items()}
        pack.arch = {k: tuple(v) if k == "tile" else [tuple(t) for t in v] for k, v in data.get("arch", {}).items()}
        pack.outside = [tuple(t) for t in data.get("outside", [])]
        pits = data.get("pits")
        if pits:
            pack.pits = {"frame": {k: tuple(v) for k, v in pits.get("frame", {}).items()},
                         "details": [tuple(t) for t in pits.get("details", [])]}
        pack.glass = tuple(data["glass"]) if data.get("glass") else None
        pack.fences = {k: tuple(v) for k, v in data.get("fences", {}).items()}
        pack.rooms = {name: {k: (v if k in BLUEPRINT_DATA else [piece_from_json(piece) for piece in v])
                             for k, v in bp.items()} for name, bp in data.get("rooms", {}).items()}
        return pack

    @classmethod
    def load(cls, style):
        """The pack of a style. An asset pack in DC_ASSET_PACKS may bring its own packs
        (styles/<style>.json, first pack wins, as for tilesets in the game): so a private
        pack can draw a style with other art than the one shipped here."""
        path = style_path(style)
        if path is None:
            styles = sorted(f[:-5] for f in os.listdir(PACK_DIR) if f.endswith(".json") and f not in NOT_STYLES)
            raise MapError(f"unknown style {style!r}; available: {', '.join(styles)} (more styles come with "
                           "asset packs: setting dungeonCoder.assetPacks, outside VS Code DC_ASSET_PACKS)")
        with open(path, encoding="utf-8") as f:
            return cls.from_json(json.load(f))


def piece_json(piece):
    """A furnishing piece for JSON: a tile [source, local], a list of tiles for consecutive fields, or a
    {"block": [w, h]} that the large props fill."""
    if isinstance(piece, dict):
        return dict(piece)
    return [list(t) for t in piece] if isinstance(piece[0], (list, tuple)) else list(piece)


def piece_from_json(piece):
    if isinstance(piece, dict):
        return dict(piece)
    return [tuple(t) for t in piece] if isinstance(piece[0], list) else tuple(piece)


BLUEPRINT_DATA = ("focal", "focal_block", "floor", "beds", "walls")      # blueprint keys that hold no pieces


def style_path(style):
    """The file of a style pack: from an asset pack in DC_ASSET_PACKS (first pack wins),
    else from the ones shipped here; None if there is none."""
    folders = [os.path.join(p, "styles") for p in _sim().asset_pack_folders()]
    return next((os.path.join(d, f"{style}.json") for d in folders + [PACK_DIR]
                 if f"{style}.json" not in NOT_STYLES and os.path.exists(os.path.join(d, f"{style}.json"))), None)


def default_style(style):
    """The style for a map that names none ("dungeon") or a generated level ("maze"): that one
    if an asset pack brings it (the course's pack does), else the free style "demo" shipped here,
    so a map without a style works without any asset pack."""
    return style if style_path(style) else FREE_STYLE


def is_rim(key):
    """A wall field of the outer rim: a neighbour lies outside the map (VOID)."""
    return key[0] == WALL and VOID in key[1]


def free_standing_blocks(grid, sizes, keep=frozenset()):
    """Small rectangular blocks of wall (2 to 4 fields, at most 2 x 2) that touch no other wall look
    like a building error; where the style has a large obstacle of exactly that size (sizes: {(w, h)}),
    they become an obstacle x and get its picture (rubble, a rock). A block without such a picture
    stays a wall (a pillar hall keeps its pillars), as does a block with a field in keep (a fence
    between two gates). The rules don't change (an obstacle is a wall); the grid is changed in place,
    the fields are returned."""
    h, w = len(grid), len(grid[0])
    solid = (WALL, "T", "t", PROP)
    seen, changed = set(), []
    for r in range(h):
        for c in range(w):
            if grid[r][c] != WALL or (c, r) in seen:
                continue
            block, todo = set(), [(c, r)]
            while todo:
                x, y = todo.pop()
                if (x, y) in block or not (0 <= x < w and 0 <= y < h) or grid[y][x] != WALL:
                    continue
                block.add((x, y))
                todo += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
            seen |= block
            xs, ys = [x for x, _ in block], [y for _, y in block]
            bw, bh = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
            if not (2 <= len(block) <= 4 and bw <= 2 and bh <= 2 and len(block) == bw * bh and (bw, bh) in sizes):
                continue
            if block & keep:
                continue
            around = {(x + dx, y + dy) for x, y in block for dx, dy in NEIGHBOURS} - block
            if any(not (0 <= x < w and 0 <= y < h) or grid[y][x] in solid + (VOID,) for x, y in around):
                continue
            for x, y in block:
                grid[y][x] = PROP
            changed += sorted(block)
    return changed


def _hash(c, r, salt=0):
    """A fixed pseudo-random number per field: the same map always gets the same decoration."""
    h = (c * 73856093) ^ (r * 19349663) ^ (salt * 83492791)
    return (h ^ (h >> 13)) & 0x7FFFFFFF


def _noise(c, r, scale=4):
    """Smooth value noise in [0, 1) over the field, the same for the same map (muster: flecken):
    details then gather in patches instead of an even sprinkle."""
    x0, y0 = c // scale, r // scale
    fx, fy = (c % scale) / scale, (r % scale) / scale

    def value(x, y):
        return (_hash(x, y, 11) % 1000) / 1000

    def lerp(a, b, t):
        t = t * t * (3 - 2 * t)
        return a + (b - a) * t
    return lerp(lerp(value(x0, y0), value(x0 + 1, y0), fx), lerp(value(x0, y0 + 1), value(x0 + 1, y0 + 1), fx), fy)


ROOM_PLAIN = (FLOOR, ALT)       # fields furnishing may use


def piece_size(piece):
    """(w, h) of a furnishing piece."""
    if isinstance(piece, dict):
        return tuple(piece["block"])
    return (len(piece), 1) if isinstance(piece[0], tuple) else (1, 1)


def fence_tiles(fences, is_fence, c, r):
    """The fence piece for a wall field by its fence neighbours: a rail between left and right, a post
    where the fence runs up or down (corners, junctions, single posts), end pieces where a rail stops."""
    left, right = is_fence(c - 1, r), is_fence(c + 1, r)
    up, down = is_fence(c, r - 1), is_fence(c, r + 1)
    if up or down or not (left or right):
        return fences.get("post") or fences.get("v")
    if left and right:
        return fences["h"]
    return (fences.get("left") if right else fences.get("right")) or fences["h"]


def furnish(grid, header, pack, ox, oy):
    """"raum: TYPE x1,y1 x2,y2": furnish the room whose floor is that rectangle (map coordinates, both
    corners inclusive) after the style's blueprint for the room type (pack.rooms). Obstacles x go along
    the north wall (every other field, with the blueprint's pictures, or blocks for the style's large
    props), into the corners farthest from the entrances, as flanking pieces beside a framed focal area
    (",") or a large piece that lies opposite the entrance; beds (blocks in a grid, crops or trees) fill
    the room; a floor tone (":" or ",") may cover it; with "walls": "zaun" the room's walls become
    fences. Only plain floor fields change; fields next to an entrance (a non-wall field on the room's
    border) or next to a torch stay free, objects are never touched. Returns ({field: tile} for the
    obstacles whose picture the blueprint pins, {field: tile} for walls drawn as fences)."""
    h, w = len(grid), len(grid[0])
    pinned, fence_walls = {}, {}

    def at(x, y):
        return grid[y][x] if 0 <= x < w and 0 <= y < h else VOID

    def solid(x, y):
        return at(x, y) in (WALL, "T", "t", PROP, VOID)
    for spec in header.get("raum", []):
        try:
            kind, a, b = spec.split()
            (x0, y0), (x1, y1) = (tuple(int(v) for v in corner.split(",")) for corner in (a, b))
        except ValueError:
            raise MapError(f"raum: expected 'TYPE x1,y1 x2,y2', got {spec!r}") from None
        if kind not in pack.rooms:
            raise MapError(f"raum {spec!r}: this style knows no room type {kind!r}; known: "
                           + ", ".join(sorted(pack.rooms)))
        x0, x1, y0, y1 = min(x0, x1) + ox, max(x0, x1) + ox, min(y0, y1) + oy, max(y0, y1) + oy
        if not (0 <= x0 <= x1 < w and 0 <= y0 <= y1 < h):
            raise MapError(f"raum {spec!r}: the rectangle lies outside the map")
        plan = pack.rooms[kind]
        width, height = x1 - x0 + 1, y1 - y0 + 1
        plain = ROOM_PLAIN + ((plan["floor"],) if plan.get("floor") else ())     # the room's own floor tone counts
        # entrances: non-wall fields on the ring just outside the rectangle; their neighbours stay free
        ring = ([(x, y0 - 1) for x in range(x0, x1 + 1)] + [(x, y1 + 1) for x in range(x0, x1 + 1)]
                + [(x0 - 1, y) for y in range(y0, y1 + 1)] + [(x1 + 1, y) for y in range(y0, y1 + 1)])
        entrances = [(x, y) for x, y in ring if not solid(x, y)]
        keep = {(x + dx, y + dy) for x, y in entrances for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
        sides = {"north" if y < y0 else "south" if y > y1 else "west" if x < x0 else "east" for x, y in entrances}

        def free(x, y):
            return (x0 <= x <= x1 and y0 <= y <= y1 and grid[y][x] in plain and (x, y) not in keep
                    and not any(at(x + dx, y + dy) in "Tt" for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))))

        def put(x, y, piece):
            """The piece with its top-left field at (x, y), if every field of it is free."""
            pw, ph = piece_size(piece)
            cells = [(x + i, y + j) for j in range(ph) for i in range(pw)]
            if not all(free(cx, cy) for cx, cy in cells):
                return False
            tiles = None if isinstance(piece, dict) else (piece if isinstance(piece[0], tuple) else [piece])
            for n, (cx, cy) in enumerate(cells):
                grid[cy][cx] = PROP
                if tiles:
                    pinned[(cx, cy)] = tiles[n]
            return True
        if plan.get("floor"):
            for y in range(y0, y1 + 1):
                for x in range(x0, x1 + 1):
                    if grid[y][x] == FLOOR:
                        grid[y][x] = plan["floor"]
        if plan.get("walls") == "zaun" and pack.fences:
            corners = [(x0 - 1, y0 - 1), (x1 + 1, y0 - 1), (x0 - 1, y1 + 1), (x1 + 1, y1 + 1)]
            fence_cells = {(x, y) for x, y in ring + corners if at(x, y) == WALL}

            def is_fence(x, y):
                return (x, y) in fence_cells
            for x, y in fence_cells:
                fence_walls[(x, y)] = fence_tiles(pack.fences, is_fence, x, y)
        north = plan.get("north") or []
        if north and height >= 3 and solid(x0, y0 - 1):          # pieces along the north wall, every other field
            n, x = 0, x0
            while x <= x1 and n < max(1, width // 3):
                piece = north[_hash(x, y0, 12) % len(north)]
                if put(x, y0, piece):
                    n += 1
                    x += piece_size(piece)[0] + 1
                else:
                    x += 1
        focal, block = plan.get("focal"), plan.get("focal_block")
        if (focal or block) and width >= 5 and height >= 4:
            fw, fh = block or (focal if focal != [0, 0] else [max(3, width - 4), max(3, height - 4)])
            fw, fh = min(fw, width - 2), min(fh, height - 3)
            fx = x0 + (width - fw) // 2
            fy = (y0 + 1 if "south" in sides and "north" not in sides else y1 - fh
                  if "north" in sides and "south" not in sides else y0 + (height - fh) // 2)
            fy = max(y0 + 1, min(fy, y1 - fh))
            if block:
                put(fx, fy, {"block": [fw, fh]})
            else:
                for y in range(fy, fy + fh):
                    for x in range(fx, fx + fw):
                        if grid[y][x] == FLOOR:
                            grid[y][x] = PATH
            for i, x in enumerate((fx - 1, fx + fw)):
                flank = plan.get("flank") or []
                if flank:
                    put(x, fy, flank[(i + _hash(fx, fy, 13)) % len(flank)])
        beds = plan.get("beds")
        if beds:
            bw, bh, tiles = beds["w"], beds["h"], [tuple(t) for t in beds.get("tiles") or []]
            y = y0 + 1
            while y + bh - 1 < y1:
                x = x0 + 1
                while x + bw - 1 < x1:
                    piece = ({"block": [bw, bh]} if not tiles
                             else [tiles[_hash(x, y, 16) % len(tiles)]] * bw)
                    if tiles:                     # the same crop on every field of the bed
                        cells = [(x + i, y + j) for j in range(bh) for i in range(bw)]
                        if all(free(cx, cy) for cx, cy in cells):
                            for cx, cy in cells:
                                grid[cy][cx] = PROP
                                pinned[(cx, cy)] = piece[0]
                    else:
                        put(x, y, piece)
                    x += bw + 1
                y += bh + 1
        corner = plan.get("corner") or []
        if corner:
            spots = [(x1, y1, -1, -1), (x0, y1, 1, -1), (x1, y0, -1, 1), (x0, y0, 1, 1)]   # the far (south) corners first
            placed = 0
            for cx, cy, dx, dy in spots:
                if placed >= 2 or not free(cx, cy):
                    continue
                piece = corner[_hash(cx, cy, 14) % len(corner)]
                pw, ph = piece_size(piece)
                px, py = (cx if dx > 0 else cx - pw + 1), (cy if dy > 0 else cy - ph + 1)
                if not put(px, py, piece):
                    continue
                if pw == ph == 1 and free(cx + dx, cy) and _hash(cx, cy, 15) % 2:
                    put(cx + dx, cy, corner[_hash(cx + dx, cy, 14) % len(corner)])
                placed += 1
    return pinned, fence_walls


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


def looks_on(header):
    """The looks switched on by "muster: wandansicht nische ..." (or "alle"), as their code names."""
    words = " ".join(header.get("muster", [])).replace(",", " ").split()
    unknown = [w for w in words if w not in LOOKS and w != "alle"]
    if unknown:
        raise MapError(f"muster: unknown look {unknown[0]!r}; known: alle, {', '.join(LOOKS)}")
    return set(LOOKS.values()) if "alle" in words else {LOOKS[w] for w in words}


def facades(grid, terrain, layers, pack):
    """muster: wandansicht. In a wall at least two rows deep, the row that faces the hero (a wall above,
    floor below) shows the wall's front instead of its top, with end pieces where the front stops; a
    torch keeps its wall top. Returns the fields that show a front."""
    h, w = len(grid), len(grid[0])
    cells = {(c, r) for r in range(1, h - 1) for c in range(w)
             if grid[r][c] == WALL and terrain[r - 1][c] == WALL and terrain[r + 1][c] == FLOOR}
    for c, r in cells:
        if (c - 1, r) not in cells and (c + 1, r) in cells:
            which = "left"
        elif (c + 1, r) not in cells and (c - 1, r) in cells:
            which = "right"
        else:
            which = "mid"
        layers["wall"][(c, r)] = pack.facade.get(which) or pack.facade["mid"]
    return cells


def pit_frames(grid, terrain, layers, pack, bones=False):
    """muster: gruben. A pit gets its rim: the frame's edges and corners by which neighbours are pit too
    (the frame's tiles are abyss tiles, so the pit stays an abyss); with muster: knochen, bones lie
    on the floor around it."""
    h, w = len(grid), len(grid[0])
    frame, details = pack.pits.get("frame", {}), pack.pits.get("details", [])

    def is_pit(x, y):
        return 0 <= x < w and 0 <= y < h and terrain[y][x] == ABYSS
    for r in range(h):
        for c in range(w):
            if terrain[r][c] == ABYSS and frame:
                layers["floor"][(c, r)] = frame.get(path_mask(is_pit, c, r), frame.get("1" * 8))
                layers["floor2"].pop((c, r), None)
            elif (bones and terrain[r][c] == FLOOR and grid[r][c] == FLOOR and details and _hash(c, r, 8) % 100 < 30
                  and any(is_pit(c + dx, r + dy) for dx, dy in NEIGHBOURS)):
                layers["floor2"][(c, r)] = details[_hash(c, r, 9) % len(details)]


def arches(grid, terrain, layers, pack, fronts):
    """muster: bogen. An arch (3 fields wide, 2 high, on the layer Over above the figures) over
    (1) every doorway through a wall two rows deep: a gap one field wide (floor, a door or a grille)
    that leads from room to room, with wall beside it in both rows; the arch's legs stand on those walls,
    and (2) a goal at the end of a dead end three fields wide, walked into northwards, which also gets a
    broad staircase over the three fields; where the wall behind it is two rows deep (or the map ends)
    the arch spans the opening and a wall front under it becomes the dark opening.
    Returns the goals that got stairs (their goal object becomes an invisible marker)."""
    h, w = len(grid), len(grid[0])
    done = set()
    arch, stairs = pack.arch.get("tile"), pack.arch.get("stairs")

    def t(x, y):
        return terrain[y][x] if 0 <= x < w and 0 <= y < h else VOID
    if arch:
        for r in range(1, h - 2):
            for c in range(1, w - 1):
                # (c, r) the upper and (c, r + 1) the lower (front) field of the gap, rooms above and below
                if not (t(c, r) == FLOOR and t(c, r + 1) == FLOOR and t(c, r - 1) == FLOOR and t(c, r + 2) == FLOOR
                        and all(t(x, y) == WALL for x in (c - 1, c + 1) for y in (r, r + 1))
                        and any(t(x, r + 2) == FLOOR for x in (c - 1, c + 1))        # the wall ends below the gap
                        and all(grid[y][c] not in (PROP,) for y in (r, r + 1))):
                    continue
                layers.setdefault("over", {})[(c - 1, r + 1)] = arch
    for r in range(h):
        for c in range(w):
            if grid[r][c] != "Z" or exit_direction(grid, c, r) != "north" or not 1 <= c < w - 1:
                continue
            plain = all(grid[r][x] in (FLOOR, PATH, DETAIL, ALT) for x in (c - 1, c + 1))
            if not (plain and t(c - 2, r) in (WALL, VOID) and t(c + 2, r) in (WALL, VOID)
                    and all(t(x, r - 1) == WALL for x in (c - 1, c, c + 1))):
                continue
            if stairs:
                for x, tile in zip((c - 1, c, c + 1), stairs):
                    layers["floor2"][(x, r)] = tile
                done.add((c, r))
            if arch and all(t(x, y) in (WALL, VOID) for x in (c - 1, c, c + 1) for y in (r - 1, r - 2)):
                layers.setdefault("over", {})[(c - 1, r - 1)] = arch     # 3 fields wide, 2 high, drawn upwards
                if pack.facade.get("opening"):
                    for x in (c - 1, c, c + 1):
                        if (x, r - 1) in fronts:
                            layers["wall"][(x, r - 1)] = pack.facade["opening"]
    return done


def fill_outside(grid, terrain, layers, pack):
    """muster: aussen. Every field beyond the walls that nothing is drawn on becomes solid rock: a tile
    on the wall layer, so the field is a wall for the rules instead of walkable darkness. Returns them."""
    h, w = len(grid), len(grid[0])
    drawn = set().union(*(set(layer) for layer in layers.values()))
    filled = set()
    for r in range(h):
        for c in range(w):
            if terrain[r][c] == VOID and (c, r) not in drawn:
                layers["wall"][(c, r)] = pack.outside[_hash(c, r, 10) % len(pack.outside)]
                filled.add((c, r))
    return filled


def prop_place(grid, terrain, c, r):
    """Where an obstacle stands: "tall" under a wall (shelves, barrels and chains stand there), "corner"
    in a corner of the room or beside another obstacle (pots), else "flat" (rubble, wood)."""
    h, w = len(grid), len(grid[0])

    def t(x, y):
        return terrain[y][x] if 0 <= x < w and 0 <= y < h else VOID
    if t(c, r - 1) in (WALL, VOID):
        return "tall"
    beside_wall = any(t(x, r) == WALL and not (0 <= x < w and grid[r][x] == PROP) for x in (c - 1, c + 1))
    beside_prop = any(0 <= x < w and grid[r][x] == PROP for x in (c - 1, c + 1))
    if (beside_wall and t(c, r + 1) == WALL) or beside_prop:
        return "corner"
    return "flat"


def decorate(grid, terrain, layers, pack, header, muster=frozenset(), pinned=None):
    """The decoration of a map (it changes no rule): obstacles x, paths ",", details '"', the second
    floor tone ":", and with "deko: N" small details on N % of the plain floor and decorated walls.
    pinned: {field: tile} obstacles whose picture a room's blueprint chose (furnish)."""
    pinned = pinned or {}
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
            if grid[r][c] == PROP and (c, r) not in group and (c, r) not in pinned:
                todo = [(c, r)]
                while todo:
                    x, y = todo.pop()
                    if (x, y) in group or not (0 <= x < w and 0 <= y < h) or grid[y][x] != PROP or (x, y) in pinned:
                        continue
                    group[(x, y)] = (c, r)
                    todo += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    big = place_big_props(grid, terrain, layers, pack, group)
    # small details gather around obstacles and objects (a chest, a switch, rubble); the open floor stays calm
    anchors = {(c, r) for r in range(h) for c in range(w)
               if grid[r][c] == PROP or grid[r][c] in OBJECT_CLASSES or grid[r][c] in "DGTKo"}
    near = {(c + dx, r + dy) for c, r in anchors for dx in range(-2, 3) for dy in range(-2, 3)}
    for r in range(h):
        for c in range(w):
            ch = grid[r][c]
            if (c, r) in big:
                continue
            if ch == PROP and (c, r) in pinned:
                tile = pinned[(c, r)]
                if tile[1] == 0 and pack.glass:         # local 0 never counts as a wall: picture above a glass wall
                    layers["wall"][(c, r)] = pack.glass
                    layers["deko"][(c, r)] = tile
                else:
                    layers["wall"][(c, r)] = tile
                top = dict(pack.props).get(tile)        # a piece's part that reaches into the field behind it
                if top and r > 0 and terrain[r - 1][c] in (FLOOR, WALL):
                    layers["deko"][(c, r - 1)] = top
            elif ch == PROP and pack.props:
                by_place = pack.props_by_place.get(prop_place(grid, terrain, c, r)) if "props" in muster else None
                if by_place:
                    bottom, top = by_place[_hash(*group[(c, r)], 1) % len(by_place)], None
                else:
                    bottom, top = pack.props[_hash(*group[(c, r)], 1) % len(pack.props)]
                layers["wall"][(c, r)] = bottom
                if top and r > 0 and terrain[r - 1][c] in (FLOOR, WALL):
                    layers["deko"][(c, r - 1)] = top
            elif ch == PATH and pack.paths:
                layers["floor2"][(c, r)] = pack.paths.get(path_mask(is_path, c, r), pack.paths.get("0" * 8))
            elif ch == DETAIL and pack.details:
                layers["floor2"][(c, r)] = pack.details[_hash(c, r, 2) % len(pack.details)]
            elif ch == ALT and pack.floor_alt:
                layers["floor2"][(c, r)] = pack.floor_alt[_hash(c, r, 7) % len(pack.floor_alt)]
            elif not density:
                continue
            elif ch == FLOOR and pack.details and (c, r) not in layers["floor2"] and _hash(c, r, 3) % 100 < (
                    patchy(min(3 * density, 60) if (c, r) in near else density // 4, c, r, muster)):
                layers["floor2"][(c, r)] = pack.details[_hash(c, r, 2) % len(pack.details)]
            elif ch == WALL and layers["wall"].get((c, r)) in pack.wall_variants and _hash(c, r, 4) % 100 < 2 * density:
                variants = pack.wall_variants[layers["wall"][(c, r)]]
                layers["wall"][(c, r)] = variants[_hash(c, r, 5) % len(variants)]


def patchy(chance, c, r, muster):
    """The chance of a detail on a field: with "flecken" details gather in patches of the noise."""
    if "patches" not in muster:
        return chance
    return min(40, chance * 2) if _noise(c, r, 5) > 0.55 else 0


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
    muster = looks_on(header)                                   # the looks switched on
    grid_w, grid_h = max(GRID_W, width), max(GRID_H, height)       # a larger map, a larger field
    ox, oy = (grid_w - width) // 2, (grid_h - height) // 2
    grid = [[VOID] * grid_w for _ in range(grid_h)]
    for r, line in enumerate(rows):
        for c, ch in enumerate(line):
            grid[r + oy][c + ox] = ch

    pinned, fence_walls = furnish(grid, header, pack, ox, oy) if header.get("raum") else ({}, {})
    if pack.big_props:
        free_standing_blocks(grid, {(p["w"], p["h"]) for p in pack.big_props}, keep=set(fence_walls))
    terrain = [[base_terrain(ch) for ch in row] for row in grid]
    floor_variety = max(variety, MUSTER_VARIETY) if "variety" in muster else variety
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
            key = pattern(looks, c, r)
            stack = pack.choose(key, left, up, rng, floor_variety if terrain[r][c] == FLOOR else variety, rim=is_rim(key))
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

    for cell, tile in fence_walls.items():      # a room's walls as fences (blueprint "walls": "zaun")
        layers["wall"][cell] = tile
    fronts = facades(grid, terrain, layers, pack) if "facade" in muster and pack.facade else set()
    if "pits" in muster and pack.pits:
        pit_frames(grid, terrain, layers, pack, bones="bones" in muster)
    decorate(grid, terrain, layers, pack, header, muster, pinned)

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

    alcove_goals = arches(grid, terrain, layers, pack, fronts) if "arch" in muster and pack.arch else set()
    filled = fill_outside(grid, terrain, layers, pack) if "outside" in muster and pack.outside else set()

    # objects
    objects, cell_to_id = [], {}
    numbers = header.get("hero", ["7"])[0].replace(",", " ").split() or ["7"]
    numbers += EXTRA_HERO_SPRITES[len(numbers) - 1:]
    number = numbers[0]
    # start: one direction for every hero, or one per hero (H, 2, 3, ...; the last one for the rest)
    directions = " ".join(header.get("start", ["south"])).replace(",", " ").split() or ["south"]
    for d in directions:
        if d not in DIRECTIONS:
            raise MapError(f"start must be one of {', '.join(DIRECTIONS)}, not {d!r}")
    direction = directions[0]
    for r in range(grid_h):
        for c in range(grid_w):
            ch, context = grid[r][c], terrain[r][c]
            name = ""
            if ch == "H":
                cls, name = "Character", "MainCharacter"
                tile = pack.hero.get(f"{direction}_{number}")
                if not tile:
                    raise MapError(f"no hero sprite {number!r} (hero: 0 to 15)")
            elif ch in EXTRA_HEROES:
                cls, name = "Character", f"Hero{ch}"     # the engine finds co-op heroes by name
                own = directions[min(int(ch) - 1, len(directions) - 1)]
                tile = pack.hero.get(f"{own}_{numbers[int(ch) - 1]}")
                if not tile:
                    raise MapError(f"no hero sprite {numbers[int(ch) - 1]!r} for hero {ch} (hero: 0 to 15)")
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
                cls, tile = "Crystal", item_tile("Crystal", "K")
            elif ch == "o":
                cls, tile = "Pebble", item_tile("Pebble", "o")
            elif ch == "W":
                cls, tile = "Guard", pack.hero.get(f"south_{pack.guard_sprite}")
            elif ch == "Z" and exit_direction(grid, c, r) in pack.exits:
                cls, tile = "Goal", pack.exits[exit_direction(grid, c, r)]   # facing the hero's way in
            elif ch in OBJECT_CLASSES:
                cls = OBJECT_CLASSES[ch]
                tile = pack.object_tile(cls, context)
            elif ch in (WALL, FLOOR, VOID, ABYSS) or ch in DECORATION:
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
        if len(colors) != len(crystals) or set(colors) - set(CRYSTAL_ITEMS):
            raise MapError(f"colors: one of {', '.join(CRYSTAL_ITEMS)} per crystal K")
        for o, color in zip(crystals, colors):
            o["tile"] = item_tile(CRYSTAL_ITEMS[color], "K")
    for o, value in zip(crystals, values):
        o["properties"] = [{"name": "value", "type": "int", "value": value}]

    def tileset_info(source):
        """What the style knows about a tileset; for an item tileset (not learned with the style)
        the tile count from the simulator's rules, one field per tile, no classes (the object
        gets its class as its type)."""
        if source in pack.tilesets:
            return pack.tilesets[source]
        rules = _sim()._rules().get(source)
        if rules is None:
            raise MapError(f"{source}: no asset pack has this tileset")
        return {"count": rules["count"], "tile_w": pack.tile_size, "tile_h": pack.tile_size, "classes": {}}

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
        visible = not (o["cls"] == "Goal" and (pack.goal_decor or o["cell"] in alcove_goals))
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

    # variants: "region: s 2,2 17,13" - the objects s inside the rectangle may lie on any of its
    # free fields (Game(path, seed=17), variants.py): a Region rectangle and a property per object
    for n, spec in enumerate(header.get("region", []), start=1):
        try:
            symbol, a, b = spec.split()
            (c0, r0), (c1, r1) = (tuple(int(v) for v in corner.split(",")) for corner in (a, b))
        except ValueError:
            raise MapError(f"region: expected 'SYMBOL x1,y1 x2,y2', got {spec!r}") from None
        c0, c1, r0, r1 = min(c0, c1), max(c0, c1), min(r0, r1), max(r0, r1)
        inside = [i for i, o in enumerate(objects) if o["symbol"] == symbol
                  and c0 <= o["cell"][0] - ox <= c1 and r0 <= o["cell"][1] - oy <= r1]
        if not inside:
            raise MapError(f"region {spec!r}: no {symbol!r} inside the rectangle")
        name = f"region{n}"
        for i in inside:
            tiled_objects[i].setdefault("properties", []).append({"name": "region", "type": "string", "value": name})
        tiled_objects.append({"height": (r1 - r0 + 1) * pack.tile_size, "id": len(tiled_objects) + 1, "name": name,
                              "rotation": 0, "type": "Region", "visible": False,
                              "width": (c1 - c0 + 1) * pack.tile_size,
                              "x": (c0 + ox) * pack.tile_size, "y": (r0 + oy) * pack.tile_size})

    properties = [{"name": "world", "type": "string", "value": pack.world}] if pack.world else []
    if pack.pack:                   # which asset pack the art needs: named in "missing tileset" (G5)
        properties.append({"name": "pack", "type": "string", "value": pack.pack})
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
    # what lies above the figures (an arch over a goal's alcove), after the objects
    over = [tile_layer(6 + len(deko_layers), "Over", layers["over"])] if layers.get("over") else []
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
        ] + over,
        "nextlayerid": 6 + len(deko_layers) + len(over), "nextobjectid": len(tiled_objects) + 1,
        "orientation": "orthogonal",
        "renderorder": "right-down", "tiledversion": "1.11.2", "tileheight": pack.tile_size,
        "tilewidth": pack.tile_size,
        "tilesets": tilesets, "type": "map", "version": "1.10",
    }
    if properties:
        level["properties"] = properties
    view = header.get("view", ["full"])[0]
    if view not in VIEWS:
        raise MapError(f"view must be one of {', '.join(VIEWS)}, not {view!r}")
    x0 = y0 = 0
    if view == "fit":
        level, terrain, (x0, y0) = fit_view(level, terrain)
    for c, r in filled:             # the rock beyond the walls: a wall for the rules (self-checks compare this)
        if 0 <= r - y0 < len(terrain) and 0 <= c - x0 < len(terrain[0]):
            terrain[r - y0][c - x0] = WALL
    return level, terrain


def fit_view(level, terrain):
    """(level, terrain, offset of the cut) cut to the map and one field around it (where the styles
    draw the fronts and edges of the outer walls). The game's view is as large as the level, so
    a smaller level has larger fields."""
    width, height, tw, th = level["width"], level["height"], level["tilewidth"], level["tileheight"]
    cells = {(c + dx, r + dy) for r, row in enumerate(terrain) for c, t in enumerate(row) if t != VOID
             for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    cells = {(c, r) for c, r in cells if 0 <= c < width and 0 <= r < height}
    if not cells:
        return level, terrain, (0, 0)
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
    return level, [row[x0:x1 + 1] for row in terrain[y0:y1 + 1]], (x0, y0)


def level_from_text(text, style=None):
    """The level (Tiled JSON dict) for the text of a map file. The style comes from
    the argument, else from the header ("style: bridge"), else "dungeon" (or "demo" if no
    asset pack brings "dungeon": default_style).
    A map with the header "generate: maze" is a recipe: the level is generated (generator.py),
    a new one per load with "seed: random" (the seed is in the map property `seed`)."""
    header, rows = parse_text(text)
    if "generate" in header:
        try:
            from . import generator       # noqa: PLC0415 - generator imports this module
        except ImportError:               # this file loaded on its own (tools/ascii2level.py)
            raise MapError("a recipe (generate:) needs the dungeoncoder package") from None
        text = generator.from_recipe(header)
        header, rows = parse_text(text)
    style = style or header.get("style", [None])[0] or default_style("dungeon")
    return build(header, rows, Pack.load(style))[0]


def level_from_file(path, style=None):
    with open(path, encoding="utf-8") as f:
        return level_from_text(f.read(), style)
