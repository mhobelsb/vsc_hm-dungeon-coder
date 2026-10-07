"""Level variants: one level file, many levels. `Game("schalter.json", seed=17)`.

A level marks what may move: a rectangle object of class `Region` (drawn in Tiled, or
`region:` in a text map) and objects whose property `region` names it. Loading the level
with a seed puts those objects on different free fields of their region; the same seed
always gives the same variant, and the map property `seed` carries it (the game shows it
on its end screen, so a failure can be reproduced).

    region: s 2,2 17,13          # text map: every switch s lies somewhere in this rectangle

Without a seed the level is loaded as drawn, unless its map property `variants` is
`random`: then every load is a new variant, and the seed is printed. The environment
variable DUNGEONCODER_SEED fixes such a random seed from outside (grading, tutors).

The variant is made here, in Python, before the level goes to the game or the simulator,
so both get exactly the same level.
"""
import copy
import os
import random

REGION = "Region"


def random_seed():
    """A seed for "random": DUNGEONCODER_SEED if set (grading, reproducing), else a new one."""
    fixed = os.environ.get("DUNGEONCODER_SEED", "").strip()
    if fixed.lstrip("-").isdigit():
        return int(fixed), False
    return random.SystemRandom().randrange(1, 1_000_000), True


def _prop(props, name):
    return next((p.get("value") for p in props or [] if p.get("name") == name), None)


def _set_prop(level, name, type_, value):
    props = [p for p in level.get("properties", []) or [] if p.get("name") != name]
    props.append({"name": name, "type": type_, "value": value})
    level["properties"] = props


def has_regions(level):
    return any(o.get("type") == REGION for layer in level.get("layers", []) for o in layer.get("objects", []) or [])


def strip_regions(level):
    """The level without its Region rectangles (they only describe variants)."""
    for layer in level.get("layers", []):
        if "objects" in layer:
            layer["objects"] = [o for o in layer["objects"] if o.get("type") != REGION]
    return level


def _walkable(level):
    """A function (col, row) -> walkable by the game's rules, or None if the tile rules aren't
    available here (then the region is trusted as drawn)."""
    try:
        from . import sim
        rules = sim.Level(strip_regions(copy.deepcopy(level)))
    except Exception:       # noqa: BLE001 - e.g. a missing asset pack: trust the region
        return None
    return rules.walkable


def apply(level, seed):
    """A copy of the level with every object of a region on a field of that region chosen by
    `seed` (no two on one field, never on a field another object occupies), map property
    `seed` set. Raises ValueError if a region has fewer free fields than objects."""
    level = copy.deepcopy(level)
    tw, th = level.get("tilewidth", 16), level.get("tileheight", 16)
    objects = [o for layer in level.get("layers", []) for o in layer.get("objects", []) or []]
    regions = {o.get("name", ""): o for o in objects if o.get("type") == REGION}
    walkable = _walkable(level)
    rng = random.Random(seed)

    def cell(o):
        return int(o["x"] // tw), int((o["y"] - 1) // th)

    movers = {name: [o for o in objects if o.get("type") != REGION and _prop(o.get("properties"), "region") == name]
              for name in sorted(regions)}
    moving = {id(o) for group in movers.values() for o in group}
    taken = {cell(o) for o in objects if o.get("type") != REGION and id(o) not in moving and o.get("gid")}
    for name, group in movers.items():
        if not group:
            continue
        r = regions[name]
        c0, r0 = int(r["x"] // tw), int(r["y"] // th)
        c1, r1 = int((r["x"] + r["width"] - 1) // tw), int((r["y"] + r["height"] - 1) // th)
        free = [(c, rr) for rr in range(r0, r1 + 1) for c in range(c0, c1 + 1)
                if (c, rr) not in taken and (walkable is None or walkable(c, rr))]
        if len(free) < len(group):
            raise ValueError(f"region {name!r} has {len(free)} free field(s) for {len(group)} object(s)")
        for o, (c, rr) in zip(group, rng.sample(free, len(group))):
            o["x"], o["y"] = c * tw, (rr + 1) * th
            taken.add((c, rr))
    _set_prop(level, "seed", "int", seed)
    return strip_regions(level)


def prepare(level, seed=None):
    """(level to load, seed or None, chosen at random?) for Game(path, seed). Levels without
    regions are returned unchanged (a seed given for them is ignored)."""
    if not has_regions(level):
        return level, None, False
    chosen = False
    if seed is None and str(_prop(level.get("properties"), "variants") or "").lower() == "random":
        seed, _ = random_seed()
        chosen = True
    if seed is None:
        return strip_regions(copy.deepcopy(level)), None, False
    return apply(level, seed), seed, chosen
