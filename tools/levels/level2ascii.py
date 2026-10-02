"""Render Dungeon Coder levels (Tiled JSON) as ASCII maps.

usage:
  python3 tools/levels/level2ascii.py LEVEL.json [LEVEL.json ...]     # map + object notes
  python3 tools/levels/level2ascii.py --emit LEVEL.json > level.txt   # header + map, close to the text-map format

Tilesets are looked up like the game does: the asset packs in DC_ASSET_PACKS, then the
engine's game/assets. Walls and abysses follow the engine's rules (see dclevel.py).

Legend:
    #  wall (collision)          .  floor
    ~  abyss where a floor is drawn (the hero falls)
       (blank) void: only background outside the rooms (also deadly, but unreachable)
    H  hero        Z  goal
    T  torch burning   t  torch off     s  switch
    D  door            G  grille        C  chest     J  jug     *  sweets
    ?  any other object (listed below the map)

The --emit format has a header (start direction, hero type, `controls` wiring as
"x,y -> x,y", map properties) above a line "---", then the map. Coordinates are
0-based (column, row).
"""
import sys

from dclevel import FLOOR, OBJECT_SYMBOLS, Level


def to_ascii(level):
    grid = [[level.terrain(c, r) for c in range(level.width)] for r in range(level.height)]
    notes, header = [], {}
    objects = level.objects()
    by_id = {o["obj"]["id"]: o for o in objects}
    for o in objects:
        col, row = o["cell"]
        cls = o["cls"]
        state = o["ts"].props(o["local"]).get("state") if o["ts"] else None
        if cls == "Character":
            symbol = "H"
            if state:   # e.g. "standing_south_7"
                _, direction, number = state.split("_")
                header["start"], header["hero"] = direction, number
        elif cls == "Torch":
            symbol = "t" if state == "off" else "T"
        else:
            symbol = OBJECT_SYMBOLS.get(cls, "?")
        if symbol == "?":
            notes.append(f"  ? at ({col},{row}): class={cls!r} name={o['obj'].get('name')!r}")
        if cls == "PatternDoor":
            ids = [int(i) for i in str(o["props"].get("torches", "")).split(",") if i.strip()]
            cells = " ".join(f"{by_id[i]['cell'][0]},{by_id[i]['cell'][1]}" for i in ids if i in by_id)
            header.setdefault("pattern", []).append(f"{col},{row} = {o['props'].get('pattern', '')} @ {cells}")
            notes.append(f"  PatternDoor at ({col},{row}) opens at pattern {o['props'].get('pattern')} of torches {cells}")
        if "controls" in o["props"]:
            target = by_id.get(o["props"]["controls"])
            if target:
                tc, tr = target["cell"]
                header.setdefault("controls", []).append(f"{col},{row} -> {tc},{tr}")
                notes.append(f"  {cls} at ({col},{row}) controls {target['cls']} at ({tc},{tr})")
            else:
                notes.append(f"  {cls} at ({col},{row}) controls missing object id {o['props']['controls']}")
        if 0 <= row < level.height and 0 <= col < level.width:
            grid[row][col] = symbol
    for name, value in level.properties().items():
        header[name] = str(value).lower() if isinstance(value, bool) else value
    return ["".join(r) for r in grid], notes, header


def main(args):
    emit = "--emit" in args
    paths = [a for a in args if a != "--emit"]
    if not paths:
        sys.exit(__doc__)
    for path in paths:
        level = Level(path)
        rows, notes, header = to_ascii(level)
        if emit:
            for key, value in header.items():
                for v in (value if isinstance(value, list) else [value]):
                    print(f"{key}: {v}")
            print("---")
            print("\n".join(r.rstrip() for r in rows))
        else:
            print(f"== {path.split('/')[-1]} ({level.width}x{level.height})")
            print("\n".join(r.rstrip() for r in rows))
            for note in notes:
                print(note)


if __name__ == "__main__":
    main(sys.argv[1:])
