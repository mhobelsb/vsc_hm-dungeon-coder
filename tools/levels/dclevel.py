"""Shared model of a Dungeon Coder level (Tiled JSON) for the tools in this folder.

The rules come from the simulator (api/python/dungeoncoder/sim.py), the port of the engine's
rules that tests/conformance.py keeps equal to the game, so they exist once (gap G2):
  - a cell is a WALL if a tile layer with the bool property collision=true has a
    tile there whose local id is not 0 (Level.isCollision)
  - a cell is an ABYSS if its topmost tile has the class "Abyss" (Level.isAbyssAt);
    walking onto it means falling. A floor over an abyss background is solid
  - an object's type is the class of its tile, or its own `type`
  - tile objects are anchored bottom-left: cell = (x // tilewidth, (y - 1) // tileheight)

This module adds what the tools need beyond the rules: layer roles, the tile stacks of a
cell, and the learning views (visual_walls, ignore_bg_abyss, learning_abyss), which differ
from the engine on purpose.

Layer roles (used for learning and generating tiles): the first non-collision
layer named "Background" is `bg`; other non-collision layers before the first
collision layer are `floor`; collision layers are `wall`; non-collision layers
after it are `over` (arches and other decoration drawn above the hero).
"""
import importlib.util
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
# the engine's own assets (DC_ASSETS: another folder instead)
ASSETS = os.path.normpath(os.environ.get("DC_ASSETS") or os.path.join(HERE, "..", "..", "game", "assets"))
# asset packs, searched first (as in the game and the simulator): DC_ASSET_PACKS
PACKS = [os.path.normpath(p) for p in os.environ.get("DC_ASSET_PACKS", "").split(os.pathsep) if p]
FLIP_MASK = 0x1FFFFFFF

# ASCII legend shared by level2ascii and ascii2level
WALL, FLOOR, VOID, ABYSS = "#", ".", " ", "~"
OBJECT_SYMBOLS = {
    "Switch": "s", "Door": "D", "VerticalDoor": "D", "PatternDoor": "D", "Grille": "G", "VerticalGrille": "G",
    "Chest": "C", "Jug": "J", "Goal": "Z", "Sweets": "*", "Crystal": "K", "Pebble": "o",
    # the worlds' own items (tools/make_world_art.py): same symbols as in the dungeon
    "Bett": "K", "Probe": "*", "Markierung": "o", "Entwurf": "K", "Farbfolie": "*", "Klebepunkt": "o",
    "Teil": "K", "Kiste": "*", "Marke": "o", "Messpunkt": "K", "Bodenprobe": "*", "Pflock": "o",
}

_tileset_cache = {}
_sim_module = None


def sim():
    """The simulator module, loaded by path (no need for the dungeoncoder package and its
    dependencies), with tile rules from the same folders this module reads tilesets from:
    the simulator's bundled rules, then ASSETS, then the asset packs (first pack wins)."""
    global _sim_module
    if _sim_module is None:
        path = os.path.join(HERE, "..", "..", "api", "python", "dungeoncoder", "sim.py")
        spec = importlib.util.spec_from_file_location("dclevel_sim", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with open(os.path.join(module.PACK_DIR, "tilesets.json"), encoding="utf-8") as f:
            rules = json.load(f)
        for folder in [ASSETS] + list(reversed(PACKS)):
            rules.update(module._rules_from_folder(folder))
        module._rules_cache = rules
        _sim_module = module
    return _sim_module


def asset_path(source):
    """The file for a level-relative path like "../tilesets/x.json": from the first asset
    pack that has it, else from ASSETS."""
    inner = source.replace("../", "", 1)
    for folder in PACKS:
        path = os.path.join(folder, inner)
        if os.path.exists(path):
            return path
    return os.path.join(ASSETS, inner)


class Tileset:
    """A Tiled tileset from the engine's assets, addressed by its `source` path in a level."""

    def __init__(self, source):
        self.source = source                                   # e.g. "../tilesets/x.json"
        self.path = asset_path(source)
        with open(self.path) as f:
            data = json.load(f)
        self.data = data
        self.tile_w, self.tile_h = data["tilewidth"], data["tileheight"]
        self.count = data["tilecount"]
        self.meta = {t["id"]: t for t in data.get("tiles", [])}

    def cls(self, local_id):
        return self.meta.get(local_id, {}).get("type") or self.meta.get(local_id, {}).get("class") or ""

    def props(self, local_id):
        return {p["name"]: p["value"] for p in self.meta.get(local_id, {}).get("properties", [])}

    def find(self, cls, **props):
        """Local ids of tiles with the given class and property values."""
        return [tid for tid in self.meta
                if self.cls(tid) == cls and all(self.props(tid).get(k) == v for k, v in props.items())]


def tileset(source):
    if source not in _tileset_cache:
        _tileset_cache[source] = Tileset(source)
    return _tileset_cache[source]


class Level:
    def __init__(self, path, visual_walls=False, ignore_bg_abyss=False, learning_abyss=False):
        """visual_walls=True treats layers named "Walls..." as walls even without the
        collision property. That describes what the level *looks* like (for learning
        tiles, e.g. arena_1), not how the engine behaves; keep it False otherwise."""
        self.path = path
        self.visual_walls = visual_walls
        # ignore_bg_abyss=True: abyss tiles on the background layer don't count (for learning
        # from bit_corridor.json, whose whole background is abyss, bug B15). Not engine behaviour.
        self.ignore_bg_abyss = ignore_bg_abyss
        # learning_abyss=True: the pre-B21 view (any Abyss tile makes an abyss), used only to learn
        # tile styles, so the learned packs stay as they were
        self.learning_abyss = learning_abyss
        with open(path) as f:
            self.data = json.load(f)
        d = self.data
        self.width, self.height = d["width"], d["height"]
        self.tile_w, self.tile_h = d["tilewidth"], d["tileheight"]
        self.tilesets = sorted(((t["firstgid"], tileset(t["source"])) for t in d["tilesets"]), key=lambda t: t[0])
        self.tile_layers = [l for l in d["layers"] if l["type"] == "tilelayer"]
        self.object_layers = [l for l in d["layers"] if l["type"] == "objectgroup"]
        self.roles = self._layer_roles()
        self._sim_level = None

    def rules(self):
        """The simulator's model of this level (walls, abysses, objects by the engine's rules)."""
        if self._sim_level is None:
            self._sim_level = sim().Level(self.data)
        return self._sim_level

    # --- tiles -------------------------------------------------------------
    def resolve(self, gid):
        """gid -> (Tileset, local id), or (None, None) for empty/unknown."""
        gid &= FLIP_MASK
        if gid == 0:
            return None, None
        for firstgid, ts in reversed(self.tilesets):
            if gid >= firstgid:
                local = gid - firstgid
                return (ts, local) if local < ts.count else (None, None)
        return None, None

    @staticmethod
    def is_collision_layer(layer):
        return any(p["name"] == "collision" and p.get("type") == "bool" and p["value"]
                   for p in layer.get("properties", []))

    def _layer_roles(self):
        roles, seen_wall = [], False
        for i, layer in enumerate(self.tile_layers):
            name = layer.get("name", "").lower()
            if self.is_collision_layer(layer) or (self.visual_walls and name.startswith("wall")):
                roles.append("wall")
                seen_wall = True
            elif seen_wall:
                roles.append("over")
            elif name.startswith("background"):
                roles.append("bg")
            else:
                roles.append("floor")
        return roles

    def tiles_at(self, col, row):
        """[(role, Tileset, local id), ...] for all tile layers at a cell, bottom to top."""
        out = []
        for layer, role in zip(self.tile_layers, self.roles):
            ts, local = self.resolve(layer["data"][row * layer["width"] + col])
            if ts is not None:
                out.append((role, ts, local))
        return out

    def terrain(self, col, row):
        """WALL, ABYSS, FLOOR or VOID for a cell, by the engine's rules (asked from the simulator).
        An abyss whose topmost tile is on the background layer shows as VOID (nothing drawn
        there); for the rules it is an abyss as well."""
        tiles = self.tiles_at(col, row)
        if not (self.visual_walls or self.ignore_bg_abyss or self.learning_abyss):
            rules = self.rules()
            px, py = col * self.tile_w + self.tile_w / 2, row * self.tile_h + self.tile_h / 2
            if rules.wall_tile_at(px, py):
                return WALL
            if rules.abyss_tile_at(px, py):
                return ABYSS if tiles[-1][0] != "bg" else VOID
            return FLOOR if any(role in ("floor", "over") for role, _, _ in tiles) else VOID
        # the learning views (not engine behaviour, see the module docstring)
        if any(role == "wall" and local != 0 for role, _, local in tiles):
            return WALL
        has_floor = any(role in ("floor", "over") for role, _, _ in tiles)
        # engine (Level.isAbyssAt): an abyss only if an Abyss tile is the topmost tile;
        # a floor drawn over an abyss background is solid ground
        if self.learning_abyss:
            # style learning keeps the old view: those fields are special floor tiles
            # (entrances, door fields), not good examples of ordinary floor
            abyss = any(ts.cls(local) == "Abyss" for role, ts, local in tiles
                        if not (self.ignore_bg_abyss and role == "bg"))
            if abyss:
                return ABYSS if has_floor else VOID
            return FLOOR if has_floor else VOID
        if tiles:
            role, ts, local = tiles[-1]
            if ts.cls(local) == "Abyss" and not (self.ignore_bg_abyss and role == "bg"):
                return ABYSS if role != "bg" else VOID
        return FLOOR if has_floor else VOID

    # --- objects -----------------------------------------------------------
    def objects(self):
        """[dict(obj, cls, cell, ts, local, props)] for all tile objects."""
        out = []
        for layer in self.object_layers:
            for obj in layer["objects"]:
                ts, local = self.resolve(obj.get("gid", 0))
                cls = obj.get("type") or (ts.cls(local) if ts else "")
                if obj.get("name") == "MainCharacter":
                    cls = "Character"
                cell = (int(obj["x"] // self.tile_w), int((obj["y"] - 1) // self.tile_h))
                props = {p["name"]: p["value"] for p in obj.get("properties", [])}
                out.append({"obj": obj, "cls": cls, "cell": cell, "ts": ts, "local": local, "props": props})
        return out

    def properties(self):
        return {p["name"]: p["value"] for p in self.data.get("properties", [])}
