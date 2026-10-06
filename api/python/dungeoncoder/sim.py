"""A pure-Python simulator of the Dungeon Coder game, for running scripts without
VS Code or a browser: grading, tests (pytest), experiments on many levels.

    DUNGEONCODER_SIM=1 python mein_programm.py        # any script, unchanged

    import dungeoncoder
    dungeoncoder.use_simulator()                       # or switch in code

It replaces only the connection to the game: the Hero and Game classes stay the
same, so every message and return value goes through the same code as with the
real game. The simulator is a port of the game's rules (game/src: level.js,
character.js, game-objects.js, script.js); tests/conformance.py checks that it
behaves like the real engine. Steps take no time, and there is no picture.

Tile rules (classes, collision, states) come from packs/tilesets.json, which is
exported from the game's tilesets (tools/ascii2level.py --export-packs), and from the asset
packs in DC_ASSET_PACKS. The tiles of the start inventory's items come from the packs'
manifests (pack.json "items"), then packs/items.json (the bundled assets' items).
Differences on purpose: none known. Fog only changes the picture, so it has no
effect here.
"""
import json
import os

TILE = 16
PACK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "packs")
DIRECTIONS_LEFT = {"north": "west", "west": "south", "south": "east", "east": "north"}

_rules_cache = None
_items_cache = None


def _rules_from_folder(folder):
    """Tile rules read directly from a pack's tilesets/*.json (like the game reads them)."""
    rules = {}
    tilesets = os.path.join(folder, "tilesets")
    for name in sorted(os.listdir(tilesets)) if os.path.isdir(tilesets) else []:
        if name.endswith(".json"):
            with open(os.path.join(tilesets, name), encoding="utf-8") as f:
                data = json.load(f)
            tiles = {}
            for tile in data.get("tiles", []):
                entry = {"type": tile["type"]} if tile.get("type") else {}
                props = {p["name"]: p["value"] for p in tile.get("properties", [])}
                if props:
                    entry["props"] = props
                if entry:
                    tiles[str(tile["id"])] = entry
            rules["../tilesets/" + name] = {"count": data["tilecount"], "tiles": tiles}
    return rules


def _rules():
    """packs/tilesets.json, overridden by the asset packs in DC_ASSET_PACKS (first pack wins,
    as in the game): so a private course pack works without its rules in this package."""
    global _rules_cache
    if _rules_cache is None:
        with open(os.path.join(PACK_DIR, "tilesets.json"), encoding="utf-8") as f:
            _rules_cache = json.load(f)
        for folder in reversed([p for p in os.environ.get("DC_ASSET_PACKS", "").split(os.pathsep) if p]):
            _rules_cache.update(_rules_from_folder(folder))
    return _rules_cache


def _items_from_manifest(manifest):
    out = {}
    for type_, spec in (manifest or {}).get("items", {}).items():
        if isinstance(spec, dict) and isinstance(spec.get("tileset"), str) and isinstance(spec.get("tile"), int):
            out[type_] = ("../tilesets/" + spec["tileset"], spec["tile"])
    return out


def item_tiles():
    """{item type: (tileset source, local id)} for the items the engine creates itself (the
    start inventory): from the manifests (pack.json "items") of the packs in DC_ASSET_PACKS,
    first pack wins, then packs/items.json, the items of the engine's bundled assets
    (engine: game/src/assets.js, loadItemTiles)."""
    global _items_cache
    if _items_cache is None:
        manifests = [os.path.join(p, "pack.json") for p in os.environ.get("DC_ASSET_PACKS", "").split(os.pathsep) if p]
        manifests.append(os.path.join(PACK_DIR, "items.json"))
        _items_cache = {}
        for path in manifests:
            try:
                with open(path, encoding="utf-8") as f:
                    found = _items_from_manifest(json.load(f))
            except (OSError, ValueError):
                continue
            for type_, tile in found.items():
                _items_cache.setdefault(type_, tile)
    return _items_cache


def missing_tileset_message(sources):
    """Same wording as the game (game/src/tiles.js, missingTilesetMessage)."""
    return (f"Missing tileset {', '.join(sources)}: no asset pack has it. "
            "Add the asset pack to the setting dungeonCoder.assetPacks (outside VS Code: DC_ASSET_PACKS).")


class MissingTileset(Exception):
    """A level names tilesets that no asset pack has."""

    def __init__(self, sources):
        super().__init__(missing_tileset_message(sources))
        self.sources = sources


class Tile:
    """A tile's class ("type") and properties; the picture doesn't matter here."""

    def __init__(self, local, entry):
        self.local = local
        self.type = entry.get("type") or ""
        self.props = entry.get("props", {})

    def get(self, name):
        """Like Tile.getProperty in the engine: the value, or None."""
        value = self.props.get(name)
        return value if value else None


class Tilesets:
    """The level's tilesets, in the level's order, like the engine's TileFactory."""

    def __init__(self, descriptions):
        self.sets = []
        missing = [d["source"] for d in descriptions if d["source"] not in _rules()]
        if missing:
            # without its rules a wall would be floor: refuse the level like the game (bug B24)
            raise MissingTileset(missing)
        for d in descriptions:
            rules = _rules()[d["source"]]
            tiles = {int(k): Tile(int(k), v) for k, v in rules["tiles"].items()}
            self.sets.append((d["firstgid"], rules["count"], tiles, d["source"]))

    def tile(self, gid):
        """The tile of a global id, or None (gid 0, or no tileset has it). Tiled's flip flags
        (the top three bits) only change the picture."""
        gid &= 0x1FFFFFFF
        if not gid:
            return None
        for firstgid, count, tiles, _ in self.sets:
            local = gid - firstgid
            if 0 <= local < count:
                return tiles.get(local) or Tile(local, {})
        return None

    def tile_by_type_and_state(self, type_, state):
        for _, _, tiles, _ in self.sets:
            for local in sorted(tiles):
                t = tiles[local]
                if t.type == type_ and t.props.get("state") == state:
                    return t
        return None

    def firstgid(self, source):
        return next((f for f, _, _, s in self.sets if s == source), None)


# --- objects -------------------------------------------------------------------------
STATES = {
    "Torch": ["burning", "off"], "Switch": ["left", "right"],
    "Door": ["open", "closed"], "VerticalDoor": ["open", "closed"], "Grille": ["open", "closed"],
    "VerticalGrille": ["open", "closed"], "Chest": ["open", "closed"], "Jug": ["unbroken", "broken"],
}
PROPAGATES = {"Torch", "Switch"}          # interact() also triggers what they `controls`


class Obj:
    """A game object (engine: GameObject and its subclasses)."""

    def __init__(self, d, tilesets):
        self.id = d.get("id")
        self.name = d.get("name", "")
        self.x, self.y = d.get("x", 0), d.get("y", 0)
        self.width, self.height = d.get("width", TILE), d.get("height", TILE)
        self.visible = d.get("visible", True)
        self.props = {p["name"]: p for p in d.get("properties", []) or []}
        self.tile = tilesets.tile(d.get("gid", 0)) or Tile(0, {})
        type_ = d.get("type") or self.tile.type
        self.type = type_
        self.kind = type_
        if type_ == "PatternDoor":
            self.type = self.tile.type or "Door"           # it looks like the door tile it was placed with
        elif type_ == "Character":
            self.type = "Character"
        self.state = self.tile.get("state")
        self.tiles = {"default": self.tile}
        for state in STATES.get(self.type, []) if self.kind != "PatternDoor" else ["open", "closed"]:
            t = tilesets.tile_by_type_and_state(self.type, state)
            if t:
                self.tiles[state] = t
        self.initial_state = self.state                    # switches: for "all_switches"
        # items: Crystal, Pebble, and a pack's own item classes (tile property `item`)
        self.is_item = self.kind in ("Crystal", "Pebble") or bool(self.tile.get("item"))
        value = self.props.get("value", {}).get("value") if self.is_item else None
        self.value = value if isinstance(value, int) and not isinstance(value, bool) else None
        if self.kind == "Guard":
            self.behaviour = str(self.props.get("behaviour", {}).get("value", "patrol") or "patrol")
            self.direction = str(self.props.get("direction", {}).get("value", "east") or "east")
        if self.kind == "PatternDoor":
            self.pattern = str(self.props.get("pattern", {}).get("value", "") or "")
            self.torch_ids = [int(s) for s in str(self.props.get("torches", {}).get("value", "") or "").split(",")
                              if s.strip().lstrip("-").isdigit()]

    def set_state(self, state):
        if state in self.tiles:
            self.tile = self.tiles[state]
            self.state = state

    def is_collision(self):
        if self.is_item or self.kind == "Guard":
            return False
        return bool(self.tile.get("collision"))

    def at(self, px, py):
        return self.x <= px < self.x + self.width and self.y - self.height <= py < self.y

    def interact(self, level):
        if self.kind in ("PatternDoor", "Goal"):
            return False
        if self.type in STATES and self.kind != "Character":
            before = self.state
            a, b = STATES[self.type]
            if self.type == "Jug":
                if self.state != "broken":
                    self.set_state("broken")
            else:
                self.set_state(b if self.state == a else a)
            changed = self.state != before
            propagated = self._controls(level) if self.type in PROPAGATES else False
            return changed or propagated
        return self._controls(level)

    def _controls(self, level):
        prop = self.props.get("controls")                  # only object properties carry an id
        if prop:
            target = level.object_by_id(prop.get("value"))
            if target:
                return target.interact(level)
        return False


# --- the level -------------------------------------------------------------------------
class Level:
    def __init__(self, data):
        props = data.get("properties", []) or []
        self.properties = props
        tilesets = list(data.get("tilesets", []))
        inventory = self.prop("hero_inventory")
        next_gid = max([1] + [t["firstgid"] for t in tilesets]) + 10000
        for type_, _ in parse_start_inventory(inventory):
            spec = item_tiles().get(type_)
            if spec and not any(t["source"] == spec[0] for t in tilesets):
                tilesets.append({"firstgid": next_gid, "source": spec[0]})
                next_gid += 10000
        self.tilesets = Tilesets(tilesets)
        self.width, self.height = data.get("width", 30), data.get("height", 20)
        self.tw, self.th = data.get("tilewidth", TILE), data.get("tileheight", TILE)
        self.layers = []            # (data, collision) of the tile layers
        self.objects = []
        for layer in data.get("layers", []):
            if layer.get("type") == "tilelayer":
                collision = any(p.get("name") == "collision" and p.get("type") == "bool" and p.get("value")
                                for p in layer.get("properties", []) or [])
                self.layers.append((layer.get("data", []), collision))
            elif layer.get("type") == "objectgroup":
                for d in layer.get("objects", []):
                    self.objects.append(Obj(d, self.tilesets))
        self.character = next((o for o in self.objects if o.name == "MainCharacter"), None)
        self.goal = next((o for o in self.objects if o.type == "Goal"), None)
        self.slots = self._find_slots()
        self.inventory = []
        self.caught = False
        self._give_start_inventory(inventory)
        self.update()

    def prop(self, name):
        return next((p.get("value") for p in self.properties if p.get("name") == name), None)

    def bool_prop(self, name, default=False):
        p = next((p for p in self.properties if p.get("name") == name), None)
        return p["value"] if p and p.get("type") == "bool" else default

    def _find_slots(self):
        def cell(o):
            return (o.x // self.tw, (o.y - 1) // self.th)
        items = sorted((o for o in self.objects if o.value is not None), key=lambda o: (cell(o)[1], cell(o)[0]))
        for rank, o in enumerate(items):
            o.start_rank = rank
        return [cell(o) for o in items]

    def _give_start_inventory(self, text):
        if not self.character:
            return
        next_id = 1 + max([0] + [o.id or 0 for o in self.objects])
        for type_, count in parse_start_inventory(text):
            spec = item_tiles().get(type_)
            firstgid = spec and self.tilesets.firstgid(spec[0])
            if firstgid is None:
                continue
            for _ in range(count):
                o = Obj({"gid": firstgid + spec[1], "id": next_id, "name": "", "type": type_, "visible": False,
                         "x": -100, "y": -100, "width": self.tw, "height": self.th}, self.tilesets)
                next_id += 1
                self.objects.append(o)
                self.inventory.append(o)

    # -- queries like the engine's Level
    def object_by_id(self, id_):
        return next((o for o in self.objects if o.id == id_), None)

    def objects_at(self, px, py):
        return [o for o in self.objects if o.at(px, py)]

    def tiles_at(self, px, py):
        col, row = int(px // self.tw), int(py // self.th)
        if not (0 <= col < self.width and 0 <= row < self.height):
            return []
        out = []
        for data, _ in self.layers:
            t = self.tilesets.tile(data[row * self.width + col]) if row * self.width + col < len(data) else None
            if t:
                out.append(t)
        return out

    def wall_tile_at(self, px, py):
        """A wall by the tiles alone: outside the map, or a tile with a local id other than 0 on a
        tile layer with collision=true (engine: Level.isCollision without the objects)."""
        col, row = int(px // self.tw), int(py // self.th)
        if not (0 <= col < self.width and 0 <= row < self.height):
            return True
        for data, collision in self.layers:
            if collision:
                t = self.tilesets.tile(data[row * self.width + col])
                if t and t.local != 0:
                    return True
        return False

    def is_collision(self, px, py):
        return self.wall_tile_at(px, py) or any(o.is_collision() for o in self.objects_at(px, py))

    def update(self):
        """What the engine does every frame: pattern doors follow their torches."""
        for o in self.objects:
            if o.kind == "PatternDoor":
                bits = "".join("1" if (t := self.object_by_id(i)) and t.type == "Torch" and t.state == "burning"
                               else "0" for i in o.torch_ids)
                should_open = o.pattern != "" and bits == o.pattern
                if should_open != (o.state == "open"):
                    o.set_state("open" if should_open else "closed")

    # -- guards and the oracle (engine: Level.stepGuards, Level.oracleDirection)
    def cell_of(self, o):
        return (int(o.x // self.tw), int((o.y - 1) // self.th))

    def walkable(self, col, row):
        if not (0 <= col < self.width and 0 <= row < self.height):
            return False
        px, py = col * self.tw + self.tw / 2, row * self.th + self.th / 2
        if self.is_collision(px, py):
            return False
        return not self.abyss_at(px, py)

    def abyss_tile_at(self, px, py):
        """An Abyss tile as the topmost tile of the field (B21: a floor over an abyss is floor)."""
        tiles = self.tiles_at(px, py)
        return bool(tiles) and tiles[-1].type == "Abyss"

    def abyss_at(self, px, py):
        """An Abyss object, or an Abyss tile as the topmost tile of the field (engine: Level.isAbyssAt)."""
        return self.abyss_tile_at(px, py) or any(o.type == "Abyss" for o in self.objects_at(px, py))

    def step_guards(self, hero_from, hero_to):
        guards = [o for o in self.objects if o.kind == "Guard"]
        caught = any(self.cell_of(g) == hero_to for g in guards)
        for guard in guards:
            col, row = self.cell_of(guard)
            def free(c, r, guard=guard):
                return self.walkable(c, r) and not any(o is not guard and self.cell_of(o) == (c, r) for o in guards)
            if guard.behaviour == "chase":
                dx, dy = hero_to[0] - col, hero_to[1] - row
                h = "east" if dx > 0 else "west" if dx < 0 else None
                v = "south" if dy > 0 else "north" if dy < 0 else None
                options = [d for d in ((h, v) if abs(dx) >= abs(dy) else (v, h)) if d]
            else:
                options = [guard.direction, OPPOSITE[guard.direction]]
            for d in options:
                nc, nr = col + OFFSETS[d][0], row + OFFSETS[d][1]
                if free(nc, nr):
                    guard.x += OFFSETS[d][0] * self.tw
                    guard.y += OFFSETS[d][1] * self.th
                    if guard.behaviour != "chase":
                        guard.direction = d
                    swapped = (col, row) == hero_to and (nc, nr) == hero_from
                    caught = caught or (nc, nr) == hero_to or swapped
                    break
        return caught

    def oracle_direction(self, col, row):
        if not self.goal:
            return None
        goal = self.cell_of(self.goal)
        if (col, row) == goal:
            return None
        first = {(col, row): None}
        queue = [(col, row)]
        while queue:
            c, r = queue.pop(0)
            for d, dx, dy in (("north", 0, -1), ("east", 1, 0), ("south", 0, 1), ("west", -1, 0)):
                n = (c + dx, r + dy)
                if n in first or not self.walkable(*n):
                    continue
                step = first[(c, r)] or d
                if n == goal:
                    return step
                first[n] = step
                queue.append(n)
        return None

    # -- win conditions
    def hero_on_goal(self):
        return bool(self.character and self.goal and self.character.x == self.goal.x
                    and self.character.y == self.goal.y)

    def items_on_slots(self):
        return [[o for o in self.objects_at(c * self.tw + self.tw / 2, r * self.th + self.th / 2)
                 if o.value is not None and o.visible is not False] for c, r in self.slots]

    def row_sorted(self):
        slots = self.items_on_slots()
        if any(len(items) != 1 for items in slots):
            return False
        values = [items[0].value for items in slots]
        return all(values[i - 1] <= values[i] for i in range(1, len(values)))

    def row_stable(self):
        if not self.row_sorted():
            return False
        items = [s[0] for s in self.items_on_slots()]
        return all(items[i - 1].value < items[i].value or items[i - 1].start_rank < items[i].start_rank
                   for i in range(1, len(items)))

    def unmet(self):
        wanted = [s.strip() for s in str(self.prop("win") or "").split(",") if s.strip()]
        missing = []
        if "all_sweets" in wanted:
            left = sum(1 for o in self.objects if o.type == "Sweets" and o.visible is not False)
            if left:
                missing.append(f"{left} sweets")
        if "all_switches" in wanted:
            unflipped = sum(1 for o in self.objects if o.type == "Switch" and o.state == o.initial_state)
            if unflipped:
                missing.append(f"{unflipped} switches")
        if "sorted" in wanted and not self.row_sorted():
            missing.append("sorted row")
        if "stable" in wanted and not self.row_stable():
            missing.append("equal values in start order")
        return missing

    def complete(self):
        if self.caught:
            return False                    # caught by a guard on the goal field
        return self.hero_on_goal() and not self.unmet()


def parse_start_inventory(text):
    out = []
    for entry in str(text or "").split(","):
        entry = entry.strip()
        if entry:
            type_, _, count = entry.partition("*")
            try:
                n = max(0, int(count.strip() or "1"))
            except ValueError:
                n = 0
            out.append((type_.strip(), n))
    return out


# --- the hero and the commands ------------------------------------------------------------
OFFSETS = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}


class Simulator:
    """Answers the same commands as the game in the browser (game/src/script.js)."""

    def __init__(self, level_override=None):
        self.level = None
        self.last_level_data = None
        self.running = False
        self.falling = False
        # grading: every level the script loads is replaced by this file (DUNGEONCODER_LEVEL)
        self.level_override = level_override if level_override is not None else os.environ.get("DUNGEONCODER_LEVEL") or None

    # -- the hero's state lives in the character object: x, y (bottom-left) and its tile state
    @property
    def hero(self):
        return self.level.character

    def direction(self):
        parts = str(self.hero.state or "").split("_")
        return parts[1] if len(parts) >= 3 else "south"

    def _set_direction(self, direction):
        parts = str(self.hero.state or "standing_south_7").split("_")
        number = parts[2] if len(parts) >= 3 else "7"
        self.hero.state = f"standing_{direction}_{number}"

    def _centre(self):
        return self.hero.x + self.level.tw / 2, self.hero.y - self.level.th / 2

    def _front(self, distance=1):
        cx, cy = self._centre()
        dx, dy = OFFSETS[self.direction()]
        return cx + dx * self.level.tw * distance, cy + dy * self.level.th * distance

    def _in_front(self, name):
        px, py = self._front()
        return (any(o.type == name for o in self.level.objects_at(px, py))
                or any(t.type == name for t in self.level.tiles_at(px, py)))

    def _tick(self):
        """After every command: pattern doors, then falling, being caught or completion end the level."""
        self.level.update()
        if self.falling or self.level.caught or self.level.complete():
            self.running = False

    def _count(self, name):
        self.stats[name] += 1

    # -- commands
    def load_level(self, data):
        if self.level_override:
            data = self._read_level(self.level_override)
        try:
            self.level = Level(data)
        except MissingTileset:
            raise                   # the game keeps the old level and refuses with a message
        except Exception as err:    # noqa: BLE001 - the game answers a broken level with an error
            self.level = None
            raise RuntimeError(f"Parsing level failed: {err}") from err
        self.last_level_data = data
        self.stats = dict.fromkeys(["moves", "turns", "bumps", "keyboard_moves", "interactions", "pickups",
                                    "drops", "sensor_calls", "reads", "questions"], 0)
        self.falling = False
        self.running = True
        self._tick()
        return True

    @staticmethod
    def _read_level(path):
        if path.endswith(".txt"):
            from .asciimap import level_from_file
            return level_from_file(path)
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def handle(self, method, params):
        """(success, message, result) like the webview's handlers."""
        if method == "load_level":
            try:
                return (True, "Parsing level successful.", self.load_level(params))
            except MissingTileset as err:
                return (False, str(err), False)
        if method == "reset_level":
            if self.last_level_data is None:
                return (False, "No level loaded.", False)
            return (True, "Level reset.", self.load_level(self.last_level_data))
        if self.level is None or self.hero is None:
            raise RuntimeError("No level loaded.")
        if method in ("move", "turn_left", "interact", "pickup", "drop") and not self.running:
            return (False, "The level is over (goal reached or game over). Load a level to continue.", False)
        result = getattr(self, "cmd_" + method)(params or {})
        if method in ("move", "turn_left", "interact", "pickup", "drop"):
            self._tick()
        return result

    def cmd_move(self, _):
        px, py = self._front()
        start = self.level.cell_of(self.hero)
        if self.level.is_collision(px, py):
            if self.level.step_guards(start, start):
                self.level.caught = True
            self._count("bumps")
            return (False, "Moving failed. Way is blocked.", False)
        target = (int(px // self.level.tw), int(py // self.level.th))
        if self.level.step_guards(start, target):
            self.level.caught = True
        abyss = self.level.abyss_at(px, py)
        dx, dy = OFFSETS[self.direction()]
        self.hero.x += dx * self.level.tw
        self.hero.y += dy * self.level.th
        if abyss:
            self.falling = True
        self._count("moves")
        return (True, "Hero moved successfully.", True)

    def cmd_turn_left(self, _):
        self._set_direction(DIRECTIONS_LEFT[self.direction()])
        self._count("turns")
        return (True, "Hero turned left successfully.", True)

    def cmd_interact(self, _):
        self._count("interactions")
        reacted = False
        for o in self.level.objects_at(*self._front()):
            reacted = o.interact(self.level) or reacted
        return (reacted, "Hero interacted successfully." if reacted else "Hero could not interact.", reacted)

    def cmd_configure(self, params):
        number = params.get("typeNumber")
        ok = isinstance(number, int) and 0 <= number <= 15
        if ok:
            self._set_direction(self.direction())
            self.hero.state = "_".join(self.hero.state.split("_")[:2] + [str(number)])
        return (ok, "Hero configured successfully." if ok else "Unable to configure hero.", ok)

    def cmd_set_pace(self, params):
        factor = params.get("factor")
        ok = isinstance(factor, (int, float)) and not isinstance(factor, bool) and factor > 0
        return (ok, "Pace changed." if ok else "Could not change pace.", ok)

    def _sensor(self, value):
        self._count("sensor_calls")
        return (True, "", value)

    def cmd_is_facing_north(self, _):
        return self._sensor(self.direction() == "north")

    def cmd_is_at_goal(self, _):
        return self._sensor(self.level.hero_on_goal())

    def cmd_is_collision_in_front(self, _):
        return self._sensor(self.level.is_collision(*self._front()))

    def cmd_is_abyss_in_front(self, _):
        return self._sensor(self.level.abyss_at(*self._front()))

    def cmd_is_torch_in_front(self, _):
        return self._sensor(self._in_front("Torch"))

    def cmd_is_switch_in_front(self, _):
        return self._sensor(self._in_front("Switch"))

    def cmd_is_enemy_in_front(self, _):
        return self._sensor(self._in_front("Guard"))

    def cmd_ask_oracle(self, _):
        if not self.level.bool_prop("orakel"):
            return (False, "There is no oracle in this level (map property orakel).", None)
        self._count("questions")
        return (True, "", self.level.oracle_direction(*self.level.cell_of(self.hero)))

    def cmd_get_items_at_position(self, _):
        self._count("sensor_calls")
        return (True, "", [o.type for o in self.level.objects_at(*self._centre()) if o.type != "Character"])

    def cmd_get_inventory(self, _):
        return (True, "", [o.type for o in self.level.inventory])

    def cmd_get_statistics(self, _):
        return (True, "Statistics of the current level.",
                {**self.stats, "at_goal": self.level.hero_on_goal(), "game_over": self.falling or self.level.caught,
                 "level_complete": self.level.complete(),
                 "missing": self.level.unmet()})

    def _inventory_full(self):
        size = self.level.prop("inventory_size")
        return isinstance(size, int) and not isinstance(size, bool) and len(self.level.inventory) >= size

    def cmd_pickup(self, params):
        name = params.get("name")
        if self._inventory_full():
            return (False, f"The inventory is full (the level allows {self.level.prop('inventory_size')} item(s)). "
                           "Drop something first.", False)
        for o in self.level.objects_at(*self._centre()):
            if o.type == name:
                self.level.inventory.append(o)
                o.x, o.y, o.visible = -100, -100, False
                self._count("pickups")
                return (True, f'Picked up item "{name}".', True)
        return (False, f'Item "{name}" not found at current location.', False)

    def cmd_drop(self, params):
        name = params.get("name")
        for i, o in enumerate(self.level.inventory):
            if o.type == name:
                o.x, o.y, o.visible = self.hero.x, self.hero.y, True
                del self.level.inventory[i]
                self._count("drops")
                return (True, f'Successfully dropped item "{name}".', True)
        return (False, f'Item "{name}" not in inventory.', False)

    def _value_at(self, px, py):
        for o in self.level.objects_at(px, py):
            if o.type != "Character" and o.visible is not False and o.value is not None:
                return o.value
        return None

    def cmd_read_item_value(self, _):
        self._count("reads")
        return (True, "", self._value_at(*self._centre()))

    def cmd_peek_item_value(self, params):
        if not self.level.bool_prop("fernrohr"):
            return (False, "This level has no Fernrohr (map property fernrohr), so values can only be read on "
                           "the hero's own field.", None)
        distance = params.get("distance")
        if not isinstance(distance, int) or isinstance(distance, bool) or distance < 1:
            return (False, f"distance must be a whole number of at least 1, not {distance!r}.", None)
        self._count("reads")
        px, py = self._front(distance)
        col, row = int(px // self.level.tw), int(py // self.level.th)
        if not (0 <= col < self.level.width and 0 <= row < self.level.height):
            return (True, "", None)
        return (True, "", self._value_at(px, py))

    # -- the HTTP answer the extension host would send (src/extension.ts)
    def request(self, method, params):
        """(HTTP status, JSON body) for a command, like the extension host."""
        if method == "configure" and not (isinstance(params.get("typeNumber"), int)
                                          and 0 <= params["typeNumber"] <= 15):
            return 400, {"message": "request/body/typeNumber must be between 0 and 15"}
        try:
            success, message, result = self.handle(method, params)
        except Exception as err:    # noqa: BLE001 - the game reports any failure as an error
            return 500, {"status": "error", "message": str(err)}
        if success:
            return 200, {"status": "success", "message": message, "result": result}
        return 500, {"status": "error", "message": message}
