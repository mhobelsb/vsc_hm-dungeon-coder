"""Draw the art of the "worlds": other settings than the dungeon for the same game
(a hospital ward, a light studio). Every picture is drawn by this script, at 32 px per
field, so the art has no third-party licence (CC0, like the demo pack).

    python3 tools/make_world_art.py          # needs Pillow

A world is: a tileset with the object classes the engine knows (floor, wall, stairs as
"Abyss", lamp as "Torch", switch, doors, cabinet as "Chest", exit as "Goal"), three item
classes of its own (tile property `item`), a figure sheet (16 colours, four directions,
standing and walking), and one level that shows everything. The level is what the text-map
builder learns the world's style from (tools/ascii2level.py in the development workspace).

Written to game/assets/: tilesets/welt_<name>_tiles.json, tilesets/welt_<name>_figur.json,
images/welt_<name>_*.png (tiles, figures, and the end screens "geschafft" and "halt"),
levels/welt_<name>.json.
"""
import json
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "game", "assets")
T = 32
COLS = 8
DIRS = ["north", "east", "south", "west"]
FIGURE_COLOURS = [(200, 60, 60), (60, 120, 200), (60, 170, 90), (210, 170, 50), (150, 80, 190), (60, 180, 180),
                  (220, 120, 40), (40, 150, 60), (120, 130, 150), (130, 90, 60), (230, 110, 160), (90, 90, 90),
                  (30, 70, 140), (160, 30, 60), (110, 160, 40), (240, 200, 120)]

# local tile id -> (class, properties). The order is the same in every world.
FLOOR, WALL, STAIRS, LAMP_ON, LAMP_OFF, SWITCH_L, SWITCH_R = 1, 2, 3, 4, 5, 6, 7
DOOR, DOOR_OPEN, VDOOR, VDOOR_OPEN, CABINET, CABINET_OPEN, EXIT, ITEM_VALUE, ITEM_TAKE, ITEM_MARK = range(8, 18)


def tiles_of(world):
    items = world["items"]
    return [
        (None, {}), (None, {}), (None, {}),                 # 0 unused, 1 floor, 2 wall
        ("Abyss", {}),
        ("Torch", {"state": "burning", "collision": True}), ("Torch", {"state": "off", "collision": True}),
        ("Switch", {"state": "left", "collision": True}), ("Switch", {"state": "right", "collision": True}),
        ("Door", {"state": "closed", "collision": True}), ("Door", {"state": "open"}),
        ("VerticalDoor", {"state": "closed", "collision": True}), ("VerticalDoor", {"state": "open"}),
        ("Chest", {"state": "closed", "collision": True}), ("Chest", {"state": "open", "collision": True}),
        ("Goal", {"state": "default"}),
        (items[0], {"item": True}), (items[1], {"item": True}), (items[2], {"item": True}),
    ]


def origin(i):
    return (i % COLS) * T, (i // COLS) * T


def shade(colour, factor):
    return tuple(max(0, min(255, int(c * factor))) for c in colour)


# ------------------------------------------------------------------------------------------
# Station: a hospital ward. Light floor, white walls with a blue rail, a care robot.
# ------------------------------------------------------------------------------------------
def station_tiles(d):
    floor, line, wall, rail = (214, 222, 216), (196, 206, 200), (244, 246, 248), (96, 150, 200)

    def ground(i):
        x, y = origin(i)
        d.rectangle([x, y, x + 31, y + 31], fill=floor)
        d.line([(x, y + 31), (x + 31, y + 31)], fill=line)
        d.line([(x + 31, y), (x + 31, y + 31)], fill=line)

    ground(FLOOR)
    x, y = origin(WALL)
    d.rectangle([x, y, x + 31, y + 31], fill=wall)
    d.rectangle([x, y + 20, x + 31, y + 24], fill=rail)                 # the handrail
    d.line([(x, y + 31), (x + 31, y + 31)], fill=(200, 204, 210))
    x, y = origin(STAIRS)                                               # stairs: no way for wheels
    for k in range(4):
        d.rectangle([x, y + k * 8, x + 31, y + k * 8 + 7], fill=shade((120, 124, 132), 1 - k * 0.17))
        d.line([(x, y + k * 8), (x + 31, y + k * 8)], fill=(60, 62, 70))
    for i, on in ((LAMP_ON, True), (LAMP_OFF, False)):                  # a wall lamp
        x, y = origin(i)
        d.rectangle([x, y, x + 31, y + 31], fill=wall)
        d.rectangle([x, y + 20, x + 31, y + 24], fill=rail)
        d.rectangle([x + 8, y + 5, x + 23, y + 13], fill=(255, 236, 140) if on else (150, 154, 160),
                    outline=(110, 114, 122))
        if on:
            d.polygon([(x + 6, y + 14), (x + 25, y + 14), (x + 29, y + 19), (x + 2, y + 19)], fill=(255, 246, 190))
    for i, right in ((SWITCH_L, False), (SWITCH_R, True)):              # a door opener on a post
        x, y = origin(i)
        ground(i)
        d.rectangle([x + 13, y + 12, x + 18, y + 29], fill=(150, 156, 164))
        d.rectangle([x + 7, y + 3, x + 24, y + 14], fill=(236, 238, 242), outline=(90, 96, 106))
        d.ellipse([x + 17, y + 5, x + 23, y + 11] if right else [x + 8, y + 5, x + 14, y + 11],
                  fill=(60, 180, 90) if right else (210, 70, 70))
    for i, vertical, is_open in ((DOOR, False, False), (DOOR_OPEN, False, True),
                                 (VDOOR, True, False), (VDOOR_OPEN, True, True)):
        x, y = origin(i)
        ground(i)
        leaf, frame = (150, 196, 224), (70, 110, 150)
        if vertical:
            d.rectangle([x + 12, y, x + 19, y + (7 if is_open else 31)], fill=leaf, outline=frame)
        else:
            d.rectangle([x, y + 12, x + (7 if is_open else 31), y + 19], fill=leaf, outline=frame)
    for i, is_open in ((CABINET, False), (CABINET_OPEN, True)):         # a medicine cabinet
        x, y = origin(i)
        ground(i)
        d.rectangle([x + 4, y + 4, x + 27, y + 28], fill=(238, 240, 244), outline=(110, 116, 126))
        if is_open:
            d.rectangle([x + 7, y + 7, x + 24, y + 25], fill=(70, 78, 92))
            d.rectangle([x + 9, y + 10, x + 13, y + 15], fill=(230, 120, 60))
            d.rectangle([x + 16, y + 17, x + 21, y + 22], fill=(90, 170, 220))
        else:
            d.line([(x + 15, y + 4), (x + 15, y + 28)], fill=(110, 116, 126))
            d.rectangle([x + 12, y + 11, x + 19, y + 20], fill=(210, 60, 60))
            d.rectangle([x + 14, y + 13, x + 17, y + 18], fill=(255, 255, 255))
    x, y = origin(EXIT)                                                 # the nurses' station: a green sign
    ground(EXIT)
    d.rectangle([x + 3, y + 7, x + 28, y + 24], fill=(40, 150, 90), outline=(20, 90, 50))
    d.polygon([(x + 9, y + 15), (x + 16, y + 10), (x + 16, y + 13), (x + 23, y + 13), (x + 23, y + 18),
               (x + 16, y + 18), (x + 16, y + 21)], fill=(255, 255, 255))
    x, y = origin(ITEM_VALUE)                                           # "Bett": a bed with a patient
    ground(ITEM_VALUE)
    d.rectangle([x + 3, y + 6, x + 28, y + 27], fill=(250, 250, 252), outline=(120, 126, 136))
    d.rectangle([x + 5, y + 8, x + 12, y + 25], fill=(224, 232, 244))                 # pillow
    d.ellipse([x + 6, y + 12, x + 12, y + 20], fill=(236, 196, 160))                  # head
    d.rectangle([x + 13, y + 8, x + 26, y + 25], fill=(120, 170, 220))                # blanket
    x, y = origin(ITEM_TAKE)                                            # "Probe": a sample tube
    ground(ITEM_TAKE)
    d.rectangle([x + 13, y + 6, x + 18, y + 25], fill=(235, 240, 248), outline=(100, 108, 120))
    d.rectangle([x + 14, y + 15, x + 17, y + 24], fill=(200, 60, 70))
    d.rectangle([x + 12, y + 4, x + 19, y + 7], fill=(60, 110, 190))
    x, y = origin(ITEM_MARK)                                            # "Markierung": a floor sticker
    ground(ITEM_MARK)
    d.ellipse([x + 9, y + 9, x + 22, y + 22], fill=(250, 200, 60), outline=(180, 130, 20))


def station_figure(d, x, y, colour, direction, walking):
    """A care robot: a box on wheels with a screen; the screen's eyes show where it looks."""
    dark = (52, 56, 66)
    shift = 1 if walking else 0
    d.rectangle([x + 6, y + 25 - shift, x + 11, y + 29 - shift], fill=dark)       # wheels
    d.rectangle([x + 20, y + 25 + shift, x + 25, y + 29 + shift], fill=dark)
    d.rectangle([x + 6, y + 11, x + 25, y + 26], fill=colour, outline=shade(colour, 0.6))
    d.rectangle([x + 9, y + 4, x + 22, y + 13], fill=(236, 240, 246), outline=(90, 96, 108))
    d.line([(x + 15, y + 1), (x + 15, y + 4)], fill=dark, width=2)                 # antenna
    eyes = {"south": [(12, 8), (18, 8)], "north": [], "east": [(19, 8)], "west": [(12, 8)]}[direction]
    for ex, ey in eyes:
        d.rectangle([x + ex, y + ey, x + ex + 2, y + ey + 2], fill=(30, 120, 210))
    if direction == "north":
        d.rectangle([x + 11, y + 6, x + 20, y + 11], fill=(190, 196, 206))        # the back of the screen
    d.rectangle([x + 13, y + 16, x + 18, y + 21], fill=(255, 255, 255))           # a white cross
    d.rectangle([x + 15, y + 17, x + 16, y + 20], fill=(210, 60, 60))
    d.rectangle([x + 14, y + 18, x + 17, y + 19], fill=(210, 60, 60))


# ------------------------------------------------------------------------------------------
# Studio: a dark stage with a wall of lamps (a display), a technician.
# ------------------------------------------------------------------------------------------
def studio_tiles(d):
    floor, seam, wall, edge = (58, 52, 60), (48, 43, 50), (34, 32, 40), (70, 66, 80)

    def ground(i):
        x, y = origin(i)
        d.rectangle([x, y, x + 31, y + 31], fill=floor)
        d.line([(x, y + 15), (x + 31, y + 15)], fill=seam)                # stage boards
        d.line([(x, y + 31), (x + 31, y + 31)], fill=seam)

    def panel(i):
        x, y = origin(i)
        d.rectangle([x, y, x + 31, y + 31], fill=wall)
        d.rectangle([x, y, x + 31, y + 31], outline=edge)

    ground(FLOOR)
    panel(WALL)
    x, y = origin(STAIRS)                                                # the edge of the stage
    d.rectangle([x, y, x + 31, y + 31], fill=(8, 7, 12))
    for k in range(0, 32, 8):
        d.polygon([(x + k, y), (x + k + 4, y), (x + k - 4 + 8, y + 5), (x + k, y + 5)], fill=(230, 190, 40))
    for i, on in ((LAMP_ON, True), (LAMP_OFF, False)):                   # one pixel of the display
        x, y = origin(i)
        panel(i)
        if on:
            d.rectangle([x + 3, y + 3, x + 28, y + 28], fill=(255, 214, 90))
            d.rectangle([x + 7, y + 7, x + 24, y + 24], fill=(255, 244, 190))
        else:
            d.rectangle([x + 3, y + 3, x + 28, y + 28], fill=(24, 22, 30), outline=(60, 56, 70))
    for i, right in ((SWITCH_L, False), (SWITCH_R, True)):               # a fader on a desk
        x, y = origin(i)
        ground(i)
        d.rectangle([x + 4, y + 10, x + 27, y + 24], fill=(90, 94, 110), outline=(30, 30, 38))
        d.line([(x + 8, y + 17), (x + 23, y + 17)], fill=(30, 30, 38), width=2)
        knob = x + (20 if right else 8)
        d.rectangle([knob, y + 13, knob + 3, y + 21], fill=(240, 120, 60))
    for i, vertical, is_open in ((DOOR, False, False), (DOOR_OPEN, False, True),
                                 (VDOOR, True, False), (VDOOR_OPEN, True, True)):
        x, y = origin(i)
        ground(i)
        cloth, fold = (150, 40, 60), (110, 26, 44)                       # a curtain
        if vertical:
            d.rectangle([x + 11, y, x + 20, y + (8 if is_open else 31)], fill=cloth)
            for k in range(0, 9 if is_open else 32, 6):
                d.line([(x + 11, y + k), (x + 20, y + k)], fill=fold)
        else:
            d.rectangle([x, y + 11, x + (8 if is_open else 31), y + 20], fill=cloth)
            for k in range(0, 9 if is_open else 32, 6):
                d.line([(x + k, y + 11), (x + k, y + 20)], fill=fold)
    for i, is_open in ((CABINET, False), (CABINET_OPEN, True)):          # a flight case
        x, y = origin(i)
        ground(i)
        d.rectangle([x + 4, y + 8, x + 27, y + 27], fill=(40, 42, 52), outline=(170, 174, 186))
        if is_open:
            d.rectangle([x + 7, y + 11, x + 24, y + 18], fill=(255, 214, 90))
        else:
            d.line([(x + 4, y + 16), (x + 27, y + 16)], fill=(170, 174, 186))
            d.rectangle([x + 14, y + 14, x + 17, y + 18], fill=(170, 174, 186))
    x, y = origin(EXIT)                                                  # the way out: a lit doorway
    ground(EXIT)
    d.rectangle([x + 7, y + 3, x + 24, y + 28], fill=(250, 244, 220), outline=(120, 110, 80))
    d.rectangle([x + 10, y + 6, x + 21, y + 28], fill=(255, 252, 240))
    x, y = origin(ITEM_VALUE)                                            # "Entwurf": a sheet with a sketch
    ground(ITEM_VALUE)
    d.rectangle([x + 6, y + 4, x + 25, y + 27], fill=(246, 244, 236), outline=(120, 116, 104))
    for k, colour in enumerate(((220, 80, 70), (70, 140, 210), (240, 190, 60))):
        d.rectangle([x + 9, y + 8 + k * 6, x + 22, y + 11 + k * 6], fill=colour)
    x, y = origin(ITEM_TAKE)                                             # "Farbfolie": a colour gel
    ground(ITEM_TAKE)
    d.rectangle([x + 6, y + 8, x + 25, y + 23], fill=(80, 190, 200), outline=(230, 232, 240))
    d.rectangle([x + 9, y + 11, x + 22, y + 20], fill=(130, 220, 228))
    x, y = origin(ITEM_MARK)                                             # "Klebepunkt": a tape mark
    ground(ITEM_MARK)
    d.line([(x + 9, y + 9), (x + 22, y + 22)], fill=(250, 250, 250), width=3)
    d.line([(x + 22, y + 9), (x + 9, y + 22)], fill=(250, 250, 250), width=3)


def studio_figure(d, x, y, colour, direction, walking):
    """A technician in overalls with a cap; the cap's peak shows where they look."""
    skin, dark = (236, 196, 160), (40, 40, 50)
    d.rectangle([x + 10, y + 13, x + 21, y + 25], fill=colour, outline=shade(colour, 0.6))   # overalls
    step = 2 if walking else 0
    d.rectangle([x + 10, y + 26, x + 14, y + 30 - step], fill=dark)                           # legs
    d.rectangle([x + 17, y + 26 - step, x + 21, y + 30], fill=dark)
    d.ellipse([x + 10, y + 3, x + 21, y + 14], fill=skin)                                     # head
    d.pieslice([x + 9, y + 1, x + 22, y + 12], 180, 360, fill=dark)                           # cap
    peak = {"south": [x + 11, y + 6, x + 20, y + 8], "north": [x + 11, y + 1, x + 20, y + 2],
            "east": [x + 19, y + 5, x + 26, y + 7], "west": [x + 5, y + 5, x + 12, y + 7]}[direction]
    d.rectangle(peak, fill=dark)
    eyes = {"south": [(13, 9), (18, 9)], "north": [], "east": [(18, 9)], "west": [(13, 9)]}[direction]
    for ex, ey in eyes:
        d.point([(x + ex, y + ey), (x + ex, y + ey + 1)], fill=(30, 30, 30))


WORLDS = {
    "station": {"tiles": station_tiles, "figure": station_figure, "items": ("Bett", "Probe", "Markierung"),
                "about": "a hospital ward: a care robot, beds, samples, a lift door, stairs it can't take",
                # end screens: (title, background, colour); the game writes its numbers in the middle
                "geschafft": ("RUNDE GESCHAFFT", (232, 240, 236), (40, 130, 90)),
                "halt": ("SICHERHEITSSTOPP", (240, 236, 232), (200, 70, 60))},
    "studio": {"tiles": studio_tiles, "figure": studio_figure, "items": ("Entwurf", "Farbfolie", "Klebepunkt"),
               "about": "a light studio: a technician, a wall of lamps as a display, the stage edge",
               "geschafft": ("VORHANG AUF", (30, 28, 36), (255, 214, 90)),
               "halt": ("PROBE ABGEBROCHEN", (30, 28, 36), (220, 90, 90))},
}


def screen(title, background, colour, path):
    """An end screen in the game's reference size; the title sits above the centre,
    because the game writes moves, turns and the countdown into the middle."""
    img = Image.new("RGB", (480, 320), background)
    d = ImageDraw.Draw(img)
    d.rectangle([14, 14, 465, 305], outline=colour, width=5)
    d.text((240, 84), title, fill=colour, anchor="mm", font=ImageFont.load_default(size=30))
    img.save(path)


def tileset(name, image, tiles, count):
    return {"columns": COLS, "image": f"../images/{image}", "imageheight": ((count + COLS - 1) // COLS) * T,
            "imagewidth": COLS * T, "margin": 0, "name": name, "spacing": 0, "tilecount": count,
            "tiledversion": "1.11.2", "tileheight": T, "tilewidth": T, "type": "tileset", "version": "1.10",
            "tiles": tiles}


def show_level(name):
    """One level with every tile and object of the world: a demo, and the source the
    text-map builder learns the style from (wall, floor, stairs; every object on the floor,
    lamps in the wall)."""
    rows = ["####Tt##########",
            "#H.....#.......#",
            "#.s.C..D..K.*.o#",
            "#......#.......#",
            "###d####..~~..Z#",
            "#......#..~~...#",
            "################"]
    width, height = 30, 20
    ox, oy = (width - len(rows[0])) // 2, (height - len(rows)) // 2
    objects_at = {"T": LAMP_ON, "t": LAMP_OFF, "s": SWITCH_L, "C": CABINET, "D": VDOOR, "d": DOOR, "Z": EXIT,
                  "K": ITEM_VALUE, "*": ITEM_TAKE, "o": ITEM_MARK}
    floor, walls, objects = [0] * (width * height), [0] * (width * height), []
    figure_first = 1 + 24
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            x, y = c + ox, r + oy
            i = y * width + x
            wall = ch in "#Tt"
            floor[i] = 1 + (STAIRS if ch == "~" else FLOOR) if not wall else 0
            walls[i] = 1 + WALL if wall else 0
            base = {"height": T, "width": T, "rotation": 0, "type": "", "visible": True, "x": x * T, "y": (y + 1) * T}
            if ch == "H":
                objects.append(dict(base, id=len(objects) + 1, name="MainCharacter",
                                    gid=figure_first + 7 * 8 + DIRS.index("east") * 2))
            elif ch in objects_at:
                objects.append(dict(base, id=len(objects) + 1, name="", gid=1 + objects_at[ch]))
                if ch == "K":
                    objects[-1]["properties"] = [{"name": "value", "type": "int", "value": 1}]

    def layer(layer_id, layer_name, data, collision=False):
        out = {"data": data, "height": height, "id": layer_id, "name": layer_name, "opacity": 1, "type": "tilelayer",
               "visible": True, "width": width, "x": 0, "y": 0}
        if collision:
            out["properties"] = [{"name": "collision", "type": "bool", "value": True}]
        return out

    return {"compressionlevel": -1, "height": height, "width": width, "infinite": False, "orientation": "orthogonal",
            "renderorder": "right-down", "tiledversion": "1.11.2", "tileheight": T, "tilewidth": T, "type": "map",
            "version": "1.10", "nextlayerid": 4, "nextobjectid": len(objects) + 1,
            "tilesets": [{"firstgid": 1, "source": f"../tilesets/welt_{name}_tiles.json"},
                         {"firstgid": figure_first, "source": f"../tilesets/welt_{name}_figur.json"}],
            "layers": [layer(1, "Floor", floor), layer(2, "Walls", walls, collision=True),
                       {"draworder": "topdown", "id": 3, "name": "Objects", "objects": objects, "opacity": 1,
                        "type": "objectgroup", "visible": True, "x": 0, "y": 0}]}


def main():
    for name, world in WORLDS.items():
        classes = tiles_of(world)
        img = Image.new("RGBA", (COLS * T, ((len(classes) + COLS - 1) // COLS) * T), (0, 0, 0, 0))
        world["tiles"](ImageDraw.Draw(img))
        img.save(os.path.join(ASSETS, "images", f"welt_{name}_tiles.png"))
        tiles = []
        for i, (cls, props) in enumerate(classes):
            entry = {"id": i}
            if cls:
                entry["type"] = cls
            if props:
                entry["properties"] = [{"name": k, "type": "bool" if isinstance(v, bool) else "string", "value": v}
                                       for k, v in props.items()]
            if len(entry) > 1:
                tiles.append(entry)
        with open(os.path.join(ASSETS, "tilesets", f"welt_{name}_tiles.json"), "w") as f:
            json.dump(tileset(f"welt_{name}_tiles", f"welt_{name}_tiles.png", tiles, len(classes)), f, indent=1)

        sheet = Image.new("RGBA", (8 * T, 16 * T), (0, 0, 0, 0))
        d = ImageDraw.Draw(sheet)
        for n, colour in enumerate(FIGURE_COLOURS):
            for k, direction in enumerate(DIRS):
                for walking in (0, 1):
                    world["figure"](d, (k * 2 + walking) * T, n * T, colour, direction, bool(walking))
        sheet.save(os.path.join(ASSETS, "images", f"welt_{name}_figur.png"))
        figures = [{"id": n * 8 + k * 2 + w, "type": "Character",
                    "properties": [{"name": "state", "type": "string",
                                    "value": f"{'walking' if w else 'standing'}_{direction}_{n}"}]}
                   for n in range(16) for k, direction in enumerate(DIRS) for w in (0, 1)]
        with open(os.path.join(ASSETS, "tilesets", f"welt_{name}_figur.json"), "w") as f:
            json.dump(tileset(f"welt_{name}_figur", f"welt_{name}_figur.png", figures, 128), f, indent=1)
        with open(os.path.join(ASSETS, "levels", f"welt_{name}.json"), "w") as f:
            json.dump(show_level(name), f)
        for kind in ("geschafft", "halt"):
            screen(*world[kind], os.path.join(ASSETS, "images", f"welt_{name}_{kind}.png"))
        print(f"world {name}: {world['about']}")


if __name__ == "__main__":
    main()
