"""Build the free demo asset pack (packs/demo/): every picture is drawn by this script,
so the pack has no third-party licence (CC0, see packs/demo/LICENSE.md).

    python3 tools/make_demo_pack.py          # needs Pillow

The pack has the object classes and states the engine knows (Torch burning/off,
Switch left/right, Door/VerticalDoor open/closed, Chest, Jug, Goal, Sweets, Abyss,
Character standing/walking in four directions and 16 colours) and two demo levels.
"""
import json
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.join(HERE, "..", "packs", "demo")
T = 16

# local id -> (class, properties); drawn by the functions below
TILES = [
    (None, {}),                                       # 0: unused (a collision layer ignores local id 0)
    (None, {}),                                       # 1: floor
    (None, {}),                                       # 2: wall
    ("Abyss", {}),                                    # 3
    ("Torch", {"state": "burning", "collision": True}),
    ("Torch", {"state": "off", "collision": True}),
    ("Switch", {"state": "left", "collision": True}),
    ("Switch", {"state": "right", "collision": True}),
    ("Door", {"state": "closed", "collision": True}),
    ("Door", {"state": "open"}),
    ("VerticalDoor", {"state": "closed", "collision": True}),
    ("VerticalDoor", {"state": "open"}),
    ("Chest", {"state": "closed", "collision": True}),
    ("Chest", {"state": "open", "collision": True}),
    ("Jug", {"state": "unbroken", "collision": True}),
    ("Jug", {"state": "broken"}),
    ("Goal", {"state": "default"}),                   # 16: stairs
    ("Sweets", {}),                                   # 17
    (None, {}),                                       # 18: crystal (white)
    (None, {}),                                       # 19: crystal (orange)
    (None, {}),                                       # 20: pebble
]
FLOOR, WALL, ABYSS = (86, 78, 70), (48, 44, 58), (8, 6, 14)


def cell(img, i, cols=8):
    return (i % cols) * T, (i // cols) * T


def draw_tiles():
    cols = 8
    img = Image.new("RGBA", (cols * T, ((len(TILES) + cols - 1) // cols) * T), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def box(i):
        x, y = cell(img, i, cols)
        return x, y, x + T - 1, y + T - 1

    def floor(i):
        x0, y0, x1, y1 = box(i)
        d.rectangle(box(i), fill=FLOOR)
        d.point([(x0 + 3, y0 + 4), (x0 + 11, y0 + 9), (x0 + 6, y0 + 13)], fill=(96, 88, 80))

    floor(1)
    x0, y0, x1, y1 = box(2)
    d.rectangle(box(2), fill=WALL)
    for yy in (y0 + 5, y0 + 11):
        d.line([(x0, yy), (x1, yy)], fill=(34, 30, 42))
    d.line([(x0 + 7, y0), (x0 + 7, y0 + 5)], fill=(34, 30, 42))
    d.line([(x0 + 3, y0 + 5), (x0 + 3, y0 + 11)], fill=(34, 30, 42))
    d.line([(x0 + 11, y0 + 5), (x0 + 11, y0 + 11)], fill=(34, 30, 42))
    d.rectangle(box(3), fill=ABYSS)
    for i, burning in ((4, True), (5, False)):
        x0, y0, _, _ = box(i)
        d.rectangle([x0 + 7, y0 + 7, x0 + 8, y0 + 14], fill=(110, 70, 40))
        if burning:
            d.ellipse([x0 + 5, y0 + 1, x0 + 10, y0 + 7], fill=(250, 170, 40))
            d.ellipse([x0 + 6, y0 + 3, x0 + 9, y0 + 6], fill=(255, 240, 120))
        else:
            d.rectangle([x0 + 6, y0 + 5, x0 + 9, y0 + 7], fill=(60, 50, 45))
    for i, right in ((6, False), (7, True)):
        x0, y0, _, _ = box(i)
        d.rectangle([x0 + 3, y0 + 10, x0 + 12, y0 + 14], fill=(120, 120, 130))
        tip = (x0 + 12, y0 + 3) if right else (x0 + 3, y0 + 3)
        d.line([(x0 + 7, y0 + 10), tip], fill=(200, 60, 60), width=2)
    for i, vertical, open_ in ((8, False, False), (9, False, True), (10, True, False), (11, True, True)):
        x0, y0, x1, y1 = box(i)
        if open_:
            d.rectangle(box(i), fill=FLOOR)
            if vertical:
                d.rectangle([x0 + 6, y0, x0 + 9, y0 + 2], fill=(130, 90, 50))
            else:
                d.rectangle([x0, y0 + 6, x0 + 2, y0 + 9], fill=(130, 90, 50))
        elif vertical:
            d.rectangle([x0 + 5, y0, x0 + 10, y1], fill=(130, 90, 50))
            d.line([(x0 + 7, y0), (x0 + 7, y1)], fill=(90, 60, 30))
        else:
            d.rectangle([x0, y0 + 5, x1, y0 + 10], fill=(130, 90, 50))
            d.line([(x0, y0 + 7), (x1, y0 + 7)], fill=(90, 60, 30))
    for i, open_ in ((12, False), (13, True)):
        x0, y0, _, _ = box(i)
        d.rectangle([x0 + 2, y0 + 6, x0 + 13, y0 + 14], fill=(150, 100, 40), outline=(90, 60, 20))
        if open_:
            d.rectangle([x0 + 3, y0 + 7, x0 + 12, y0 + 9], fill=(250, 210, 60))
        else:
            d.line([(x0 + 2, y0 + 9), (x0 + 13, y0 + 9)], fill=(90, 60, 20))
    x0, y0, _, _ = box(14)
    d.ellipse([x0 + 4, y0 + 4, x0 + 11, y0 + 14], fill=(180, 110, 70))
    d.rectangle([x0 + 6, y0 + 2, x0 + 9, y0 + 5], fill=(180, 110, 70))
    x0, y0, _, _ = box(15)
    d.polygon([(x0 + 3, y0 + 14), (x0 + 7, y0 + 10), (x0 + 12, y0 + 14)], fill=(180, 110, 70))
    x0, y0, _, _ = box(16)
    d.rectangle(box(16), fill=FLOOR)
    for k in range(4):
        d.rectangle([x0 + 2 + k * 3, y0 + 2 + k * 3, x0 + 13, y0 + 4 + k * 3], fill=(40 + 30 * k, 40 + 30 * k, 50 + 30 * k))
    x0, y0, _, _ = box(17)
    d.ellipse([x0 + 4, y0 + 5, x0 + 11, y0 + 11], fill=(230, 80, 150))
    d.polygon([(x0 + 4, y0 + 8), (x0 + 1, y0 + 5), (x0 + 1, y0 + 11)], fill=(230, 80, 150))
    d.polygon([(x0 + 11, y0 + 8), (x0 + 14, y0 + 5), (x0 + 14, y0 + 11)], fill=(230, 80, 150))
    for i, colour in ((18, (220, 225, 240)), (19, (240, 150, 40))):
        x0, y0, _, _ = box(i)
        d.polygon([(x0 + 8, y0 + 2), (x0 + 13, y0 + 7), (x0 + 8, y0 + 14), (x0 + 3, y0 + 7)], fill=colour,
                  outline=(60, 60, 80))
    x0, y0, _, _ = box(20)
    for dx, dy in ((4, 9), (8, 6), (10, 11)):
        d.ellipse([x0 + dx, y0 + dy, x0 + dx + 3, y0 + dy + 2], fill=(150, 140, 130))
    return img, cols


HERO_COLOURS = [(200, 60, 60), (60, 120, 200), (60, 170, 90), (200, 170, 50), (150, 80, 190), (60, 180, 180),
                (220, 120, 40), (40, 150, 60), (180, 180, 190), (120, 80, 50), (230, 110, 160), (90, 90, 90),
                (30, 70, 140), (160, 30, 60), (110, 160, 40), (240, 220, 180)]
DIRS = ["north", "east", "south", "west"]


def draw_heroes():
    """Rows: one per colour (16); columns: standing and walking for each direction (8)."""
    img = Image.new("RGBA", (8 * T, 16 * T), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for n, colour in enumerate(HERO_COLOURS):
        for k, direction in enumerate(DIRS):
            for w in (0, 1):
                x0, y0 = (k * 2 + w) * T, n * T
                d.rectangle([x0 + 5, y0 + 6, x0 + 10, y0 + 12], fill=colour)                  # body
                d.ellipse([x0 + 5, y0 + 1, x0 + 10, y0 + 6], fill=(240, 200, 160))             # head
                legs = [(x0 + 5, y0 + 13, x0 + 6, y0 + 15), (x0 + 9, y0 + 13, x0 + 10, y0 + 15)]
                if w:
                    legs = [(x0 + 4, y0 + 13, x0 + 5, y0 + 15), (x0 + 10, y0 + 13, x0 + 11, y0 + 15)]
                for leg in legs:
                    d.rectangle(leg, fill=(50, 40, 40))
                eyes = {"north": [], "south": [(x0 + 6, y0 + 3), (x0 + 9, y0 + 3)],
                        "east": [(x0 + 9, y0 + 3)], "west": [(x0 + 6, y0 + 3)]}[direction]
                d.point(eyes, fill=(20, 20, 20))
    return img


def tileset(name, image, cols, tiles, count):
    return {"columns": cols, "image": f"../images/{image}", "imageheight": ((count + cols - 1) // cols) * T,
            "imagewidth": cols * T, "margin": 0, "name": name, "spacing": 0, "tilecount": count,
            "tiledversion": "1.11.2", "tileheight": T, "tilewidth": T, "type": "tileset", "version": "1.10",
            "tiles": tiles}


def screen(text, colour, path):
    img = Image.new("RGB", (480, 320), (20, 18, 28))
    d = ImageDraw.Draw(img)
    d.rectangle([20, 20, 459, 299], outline=colour, width=4)
    d.text((240, 150), text, fill=colour, anchor="mm")
    img.save(path)


def level(rows, start="east", props=None):
    """A small Tiled level on the demo tiles (no auto-tiling: one tile per symbol)."""
    width, height = 30, 20
    h, w = len(rows), max(len(r) for r in rows)
    ox, oy = (width - w) // 2, (height - h) // 2
    grid = [[" "] * width for _ in range(height)]
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            grid[y + oy][x + ox] = c
    floor_gid, hero_first = 1, 1 + 24
    floor, walls, objects = [], [], []
    oid = 1
    for y in range(height):
        for x in range(width):
            c = grid[y][x]
            floor.append(0 if c == " " else floor_gid + (3 if c == "~" else 1))
            walls.append(floor_gid + 2 if c == "#" else 0)
            obj = {"Z": 16, "T": 4, "t": 5, "s": 6, "D": 10, "C": 12, "J": 14, "*": 17}.get(c)
            if c == "H":
                n, k = 7, DIRS.index(start)
                objects.append({"gid": hero_first + n * 8 + k * 2, "height": T, "id": oid, "name": "MainCharacter",
                                "rotation": 0, "type": "", "visible": True, "width": T, "x": x * T, "y": (y + 1) * T})
                oid += 1
            elif obj is not None:
                objects.append({"gid": floor_gid + obj, "height": T, "id": oid, "name": "", "rotation": 0, "type": "",
                                "visible": True, "width": T, "x": x * T, "y": (y + 1) * T})
                oid += 1
    lvl = {"compressionlevel": -1, "height": height, "width": width, "infinite": False, "orientation": "orthogonal",
           "renderorder": "right-down", "tiledversion": "1.11.2", "tileheight": T, "tilewidth": T, "type": "map",
           "version": "1.10", "nextlayerid": 4, "nextobjectid": oid,
           "tilesets": [{"firstgid": 1, "source": "../tilesets/demo_tiles.json"},
                        {"firstgid": 25, "source": "../tilesets/demo_hero.json"}],
           "layers": [
               {"data": floor, "height": height, "id": 1, "name": "Floor", "opacity": 1, "type": "tilelayer",
                "visible": True, "width": width, "x": 0, "y": 0},
               {"data": walls, "height": height, "id": 2, "name": "Walls", "opacity": 1, "type": "tilelayer",
                "visible": True, "width": width, "x": 0, "y": 0,
                "properties": [{"name": "collision", "type": "bool", "value": True}]},
               {"draworder": "topdown", "id": 3, "name": "Objects", "objects": objects, "opacity": 1,
                "type": "objectgroup", "visible": True, "x": 0, "y": 0}]}
    if props:
        lvl["properties"] = props
    return lvl


def main():
    for sub in ("tilesets", "images", "levels"):
        os.makedirs(os.path.join(PACK, sub), exist_ok=True)
    img, cols = draw_tiles()
    img.save(os.path.join(PACK, "images", "demo_tiles.png"))
    tiles = []
    for i, (cls, props) in enumerate(TILES):
        entry = {"id": i}
        if cls:
            entry["type"] = cls
        if props:
            entry["properties"] = [{"name": k, "type": "bool" if isinstance(v, bool) else "string", "value": v}
                                   for k, v in props.items()]
        if len(entry) > 1:
            tiles.append(entry)
    with open(os.path.join(PACK, "tilesets", "demo_tiles.json"), "w") as f:
        json.dump(tileset("demo_tiles", "demo_tiles.png", cols, tiles, len(TILES)), f, indent=1)
    draw_heroes().save(os.path.join(PACK, "images", "demo_hero.png"))
    hero_tiles = [{"id": n * 8 + k * 2 + w, "type": "Character",
                   "properties": [{"name": "state", "type": "string",
                                   "value": f"{'walking' if w else 'standing'}_{d}_{n}"}]}
                  for n in range(16) for k, d in enumerate(DIRS) for w in (0, 1)]
    with open(os.path.join(PACK, "tilesets", "demo_hero.json"), "w") as f:
        json.dump(tileset("demo_hero", "demo_hero.png", 8, hero_tiles, 128), f, indent=1)
    screen("DUNGEON CODER (demo pack)", (120, 200, 120), os.path.join(PACK, "images", "dungeon_coder.png"))
    screen("GAME OVER", (220, 80, 80), os.path.join(PACK, "images", "game_over.jpeg"))
    screen("DUNGEON COMPLETE", (230, 200, 80), os.path.join(PACK, "images", "dungeon_complete.jpeg"))
    levels = {
        "demo_gang.json": level(["########", "#H....Z#", "########"]),
        "demo_raum.json": level(["##########", "#H...#...#", "#.##.T...#", "#........#", "#..~~...Z#", "##########"]),
    }
    for name, data in levels.items():
        with open(os.path.join(PACK, "levels", name), "w") as f:
            json.dump(data, f)
    with open(os.path.join(PACK, "pack.json"), "w") as f:
        json.dump({"name": "demo", "version": "1.0", "licence": "CC0-1.0",
                   "description": "Free demo pack for Dungeon Coder; every picture drawn by tools/make_demo_pack.py"},
                  f, indent=1)
    with open(os.path.join(PACK, "LICENSE.md"), "w") as f:
        f.write("# Demo asset pack: CC0 1.0\n\nEvery picture in this pack was drawn by `tools/make_demo_pack.py`.\n"
                "To the extent possible under law, the authors waive all copyright and related rights to it\n"
                "(https://creativecommons.org/publicdomain/zero/1.0/).\n")
    print("demo pack written to", os.path.relpath(PACK))


if __name__ == "__main__":
    main()
