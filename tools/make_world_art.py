"""Draw the art of the "worlds": other settings than the dungeon for the same game
(a hospital ward, a light studio, a production hall, a survey area). Every picture is drawn by this script, at 32 px per
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


def station_figure(d, x, y, colour, direction, walking, number=0):
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


def studio_figure(d, x, y, colour, direction, walking, number=0):
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


def person(d, x, y, colour, direction, walking, hat):
    """A person seen from the front/side: used for the people in the workshop and the surveyors."""
    skin, dark = (236, 196, 160), (50, 48, 56)
    step = 2 if walking else 0
    d.rectangle([x + 10, y + 26, x + 14, y + 30 - step], fill=dark)
    d.rectangle([x + 17, y + 26 - step, x + 21, y + 30], fill=dark)
    d.rectangle([x + 9, y + 14, x + 22, y + 26], fill=colour, outline=shade(colour, 0.6))
    d.ellipse([x + 10, y + 4, x + 21, y + 15], fill=skin)
    d.pieslice([x + 8, y + 1, x + 23, y + 13], 180, 360, fill=hat)
    d.rectangle([x + 7, y + 6, x + 24, y + 7], fill=hat)                        # the brim
    eyes = {"south": [(13, 10), (18, 10)], "north": [], "east": [(18, 10)], "west": [(13, 10)]}[direction]
    for ex, ey in eyes:
        d.point([(x + ex, y + ey), (x + ex, y + ey + 1)], fill=(30, 30, 30))
    if direction == "north":
        d.rectangle([x + 12, y + 16, x + 19, y + 24], fill=shade(colour, 0.75))   # seen from behind


# ------------------------------------------------------------------------------------------
# Werkstatt: a production hall. Concrete floor, machine enclosures, a transport robot;
# the figures 12 to 15 are people (the text maps use number 12 for the "W" agents).
# ------------------------------------------------------------------------------------------
def werkstatt_tiles(d):
    floor, joint, wall, frame = (186, 188, 192), (168, 170, 175), (72, 96, 128), (44, 62, 88)

    def ground(i):
        x, y = origin(i)
        d.rectangle([x, y, x + 31, y + 31], fill=floor)
        d.line([(x, y + 31), (x + 31, y + 31)], fill=joint)
        d.line([(x + 31, y), (x + 31, y + 31)], fill=joint)

    def machine(i):
        x, y = origin(i)
        d.rectangle([x, y, x + 31, y + 31], fill=wall, outline=frame)
        d.rectangle([x + 4, y + 4, x + 27, y + 12], fill=shade(wall, 1.25))        # a window strip
        for k in (8, 16, 24):
            d.point([(x + k, y + 22), (x + k, y + 23)], fill=(200, 206, 214))      # rivets

    ground(FLOOR)
    machine(WALL)
    x, y = origin(STAIRS)                                                # a danger zone: no entry
    d.rectangle([x, y, x + 31, y + 31], fill=(250, 214, 60))
    d.point([(x + px, y + py) for px in range(32) for py in range(32) if ((px + py) // 6) % 2 == 0],
            fill=(40, 40, 44))                                         # diagonal warning stripes
    d.rectangle([x, y, x + 31, y + 31], outline=(40, 40, 44))
    for i, on in ((LAMP_ON, True), (LAMP_OFF, False)):                   # a signal lamp on the machine
        x, y = origin(i)
        machine(i)
        d.rectangle([x + 13, y + 14, x + 18, y + 27], fill=(60, 62, 70))
        d.ellipse([x + 9, y + 3, x + 22, y + 16], fill=(90, 220, 110) if on else (70, 84, 76), outline=(30, 40, 34))
        if on:
            d.ellipse([x + 12, y + 5, x + 17, y + 10], fill=(210, 255, 220))
    for i, right in ((SWITCH_L, False), (SWITCH_R, True)):               # a control post with a key switch
        x, y = origin(i)
        ground(i)
        d.rectangle([x + 13, y + 14, x + 18, y + 29], fill=(120, 124, 132))
        d.rectangle([x + 7, y + 3, x + 24, y + 16], fill=(250, 214, 60), outline=(40, 40, 44))
        d.ellipse([x + 12, y + 6, x + 19, y + 13], fill=(60, 60, 66))
        d.line([(x + 15, y + 9), (x + (20 if right else 11), y + 6)], fill=(230, 230, 236), width=2)
    for i, vertical, is_open in ((DOOR, False, False), (DOOR_OPEN, False, True),
                                 (VDOOR, True, False), (VDOOR_OPEN, True, True)):
        x, y = origin(i)
        ground(i)
        bar, post = (250, 214, 60), (40, 40, 44)                          # a safety gate
        if vertical:
            d.rectangle([x + 13, y, x + 18, y + (6 if is_open else 31)], fill=bar, outline=post)
            for k in range(3, 7 if is_open else 32, 8):
                d.rectangle([x + 13, y + k, x + 18, y + k + 2], fill=post)
        else:
            d.rectangle([x, y + 13, x + (6 if is_open else 31), y + 18], fill=bar, outline=post)
            for k in range(3, 7 if is_open else 32, 8):
                d.rectangle([x + k, y + 13, x + k + 2, y + 18], fill=post)
    for i, is_open in ((CABINET, False), (CABINET_OPEN, True)):          # a tool cabinet
        x, y = origin(i)
        ground(i)
        d.rectangle([x + 4, y + 3, x + 27, y + 28], fill=(200, 70, 60), outline=(110, 30, 26))
        if is_open:
            d.rectangle([x + 7, y + 6, x + 24, y + 25], fill=(60, 56, 60))
            d.line([(x + 10, y + 10), (x + 21, y + 10)], fill=(200, 204, 210), width=2)
            d.line([(x + 10, y + 17), (x + 17, y + 17)], fill=(200, 204, 210), width=2)
        else:
            for k in (10, 16, 22):
                d.line([(x + 4, y + k), (x + 27, y + k)], fill=(110, 30, 26))
    x, y = origin(EXIT)                                                  # the hand-over station
    ground(EXIT)
    d.rectangle([x + 3, y + 3, x + 28, y + 28], fill=(60, 130, 200), outline=(30, 70, 120))
    d.rectangle([x + 9, y + 9, x + 22, y + 22], outline=(255, 255, 255), width=2)
    d.rectangle([x + 13, y + 13, x + 18, y + 18], fill=(255, 255, 255))
    x, y = origin(ITEM_VALUE)                                            # "Teil": a workpiece (a gear)
    ground(ITEM_VALUE)
    for k in range(0, 360, 45):
        d.pieslice([x + 4, y + 4, x + 27, y + 27], k, k + 22, fill=(150, 156, 168))
    d.ellipse([x + 8, y + 8, x + 23, y + 23], fill=(176, 182, 194), outline=(90, 96, 108))
    d.ellipse([x + 13, y + 13, x + 18, y + 18], fill=floor, outline=(90, 96, 108))
    x, y = origin(ITEM_TAKE)                                             # "Kiste": a small load carrier
    ground(ITEM_TAKE)
    d.rectangle([x + 6, y + 9, x + 25, y + 25], fill=(70, 120, 190), outline=(36, 66, 110))
    d.rectangle([x + 9, y + 12, x + 22, y + 16], fill=(36, 66, 110))
    x, y = origin(ITEM_MARK)                                             # "Marke": a floor mark
    ground(ITEM_MARK)
    d.polygon([(x + 16, y + 8), (x + 25, y + 24), (x + 7, y + 24)], fill=(250, 214, 60), outline=(40, 40, 44))


def werkstatt_figure(d, x, y, colour, direction, walking, number=0):
    """Numbers 0 to 11: a transport robot (a flat vehicle with a mast and a light that shows
    where it drives). Numbers 12 to 15: people in work clothes with a helmet."""
    if number >= 12:
        person(d, x, y, colour, direction, walking, (250, 214, 60))
        return
    dark = (44, 46, 54)
    shift = 1 if walking else 0
    for wx in (5, 22):
        d.rectangle([x + wx, y + 22 - shift, x + wx + 4, y + 29 - shift], fill=dark)
    d.rectangle([x + 5, y + 14, x + 26, y + 26], fill=colour, outline=shade(colour, 0.6))
    d.rectangle([x + 9, y + 9, x + 22, y + 15], fill=shade(colour, 1.2), outline=shade(colour, 0.6))
    d.rectangle([x + 14, y + 2, x + 17, y + 9], fill=dark)                               # the mast
    light = {"south": [12, 21, 19, 24], "north": [12, 10, 19, 12], "east": [22, 17, 25, 22],
             "west": [6, 17, 9, 22]}[direction]
    d.rectangle([x + light[0], y + light[1], x + light[2], y + light[3]], fill=(255, 250, 200))
    d.ellipse([x + 13, y + 1, x + 18, y + 5], fill=(250, 140, 40))                      # the beacon


# ------------------------------------------------------------------------------------------
# Gelaende: a survey area. Meadow, woods nobody gets through, water, a surveyor.
# ------------------------------------------------------------------------------------------
def gelaende_tiles(d):
    grass, tuft, wood, trunk = (132, 176, 96), (108, 154, 78), (44, 96, 60), (30, 70, 44)

    def ground(i):
        x, y = origin(i)
        d.rectangle([x, y, x + 31, y + 31], fill=grass)
        for tx, ty in ((6, 8), (20, 5), (13, 19), (25, 23), (4, 26)):
            d.line([(x + tx, y + ty), (x + tx, y + ty + 3)], fill=tuft)
            d.line([(x + tx + 2, y + ty + 1), (x + tx + 2, y + ty + 3)], fill=tuft)

    def trees(i):
        x, y = origin(i)
        d.rectangle([x, y, x + 31, y + 31], fill=wood)
        for cx, cy in ((8, 9), (23, 8), (15, 21), (27, 24), (4, 25)):
            d.ellipse([x + cx - 7, y + cy - 7, x + cx + 7, y + cy + 7], fill=shade(wood, 1.25), outline=trunk)
            d.ellipse([x + cx - 3, y + cy - 4, x + cx + 2, y + cy + 1], fill=shade(wood, 1.5))

    ground(FLOOR)
    trees(WALL)
    x, y = origin(STAIRS)                                                # water
    d.rectangle([x, y, x + 31, y + 31], fill=(70, 130, 200))
    for wy in (7, 17, 27):
        for wx in (2, 18):
            d.arc([x + wx, y + wy - 3, x + wx + 8, y + wy + 3], 180, 360, fill=(180, 214, 244))
    for i, on in ((LAMP_ON, True), (LAMP_OFF, False)):                   # a measuring mast with a beacon
        x, y = origin(i)
        trees(i)
        d.rectangle([x + 14, y + 8, x + 17, y + 29], fill=(200, 204, 210), outline=(80, 84, 92))
        d.ellipse([x + 10, y + 1, x + 21, y + 12], fill=(250, 90, 70) if on else (120, 80, 76), outline=(70, 30, 26))
        if on:
            d.ellipse([x + 13, y + 3, x + 17, y + 7], fill=(255, 220, 200))
    for i, right in ((SWITCH_L, False), (SWITCH_R, True)):               # a lever at a gate post
        x, y = origin(i)
        ground(i)
        d.rectangle([x + 12, y + 16, x + 19, y + 29], fill=(130, 96, 60), outline=(80, 56, 30))
        d.line([(x + 15, y + 17), (x + (25 if right else 6), y + 5)], fill=(60, 60, 66), width=3)
        d.ellipse([x + (22 if right else 3), y + 2, x + (28 if right else 9), y + 8], fill=(210, 70, 60))
    for i, vertical, is_open in ((DOOR, False, False), (DOOR_OPEN, False, True),
                                 (VDOOR, True, False), (VDOOR_OPEN, True, True)):
        x, y = origin(i)
        ground(i)
        rail, post = (170, 126, 80), (96, 66, 36)                         # a pasture gate
        if vertical:
            for gx in (12, 18):
                d.line([(x + gx, y), (x + gx, y + (6 if is_open else 31))], fill=rail, width=3)
            for gy in range(2, 7 if is_open else 32, 9):
                d.line([(x + 10, y + gy), (x + 21, y + gy)], fill=post, width=2)
        else:
            for gy in (12, 18):
                d.line([(x, y + gy), (x + (6 if is_open else 31), y + gy)], fill=rail, width=3)
            for gx in range(2, 7 if is_open else 32, 9):
                d.line([(x + gx, y + 10), (x + gx, y + 21)], fill=post, width=2)
    for i, is_open in ((CABINET, False), (CABINET_OPEN, True)):          # an equipment case
        x, y = origin(i)
        ground(i)
        d.rectangle([x + 4, y + 9, x + 27, y + 26], fill=(240, 150, 50), outline=(130, 70, 20))
        if is_open:
            d.rectangle([x + 7, y + 12, x + 24, y + 19], fill=(60, 56, 60))
            d.ellipse([x + 12, y + 13, x + 18, y + 19], fill=(200, 210, 220))
        else:
            d.line([(x + 4, y + 16), (x + 27, y + 16)], fill=(130, 70, 20))
            d.rectangle([x + 13, y + 5, x + 18, y + 9], outline=(130, 70, 20))
    x, y = origin(EXIT)                                                  # the base camp: a tent with a flag
    ground(EXIT)
    d.polygon([(x + 4, y + 27), (x + 15, y + 9), (x + 26, y + 27)], fill=(240, 236, 220), outline=(120, 110, 90))
    d.polygon([(x + 12, y + 27), (x + 15, y + 17), (x + 18, y + 27)], fill=(90, 80, 70))
    d.line([(x + 15, y + 9), (x + 15, y + 2)], fill=(90, 80, 70))
    d.polygon([(x + 16, y + 2), (x + 24, y + 4), (x + 16, y + 7)], fill=(220, 60, 60))
    x, y = origin(ITEM_VALUE)                                            # "Messpunkt": a survey point
    ground(ITEM_VALUE)
    d.ellipse([x + 7, y + 7, x + 24, y + 24], fill=(250, 250, 250), outline=(40, 40, 44))
    d.pieslice([x + 7, y + 7, x + 24, y + 24], 0, 90, fill=(40, 40, 44))
    d.pieslice([x + 7, y + 7, x + 24, y + 24], 180, 270, fill=(40, 40, 44))
    x, y = origin(ITEM_TAKE)                                             # "Bodenprobe": a sample bag
    ground(ITEM_TAKE)
    d.polygon([(x + 9, y + 10), (x + 22, y + 10), (x + 25, y + 26), (x + 6, y + 26)], fill=(196, 170, 130),
              outline=(110, 90, 60))
    d.rectangle([x + 12, y + 6, x + 19, y + 10], fill=(110, 90, 60))
    x, y = origin(ITEM_MARK)                                             # "Pflock": a stake with a ribbon
    ground(ITEM_MARK)
    d.rectangle([x + 14, y + 8, x + 17, y + 27], fill=(150, 110, 70), outline=(90, 62, 34))
    d.polygon([(x + 18, y + 8), (x + 27, y + 11), (x + 18, y + 15)], fill=(250, 120, 40))


def gelaende_figure(d, x, y, colour, direction, walking, number=0):
    """A surveyor with a sun hat and a backpack."""
    person(d, x, y, colour, direction, walking, (226, 206, 150))
    if direction == "north":
        d.rectangle([x + 11, y + 15, x + 20, y + 24], fill=(120, 90, 60), outline=(70, 50, 30))   # the backpack
    elif direction in ("east", "west"):
        bx = 7 if direction == "east" else 21
        d.rectangle([x + bx, y + 15, x + bx + 3, y + 23], fill=(120, 90, 60))


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
    "werkstatt": {"tiles": werkstatt_tiles, "figure": werkstatt_figure, "items": ("Teil", "Kiste", "Marke"),
                  "about": "a production hall: a transport robot, people, machines, safety gates, danger zones",
                  "geschafft": ("AUFTRAG ERLEDIGT", (226, 230, 236), (40, 100, 170)),
                  "halt": ("SICHERHEITSSTOPP", (250, 214, 60), (40, 40, 44))},
    "gelaende": {"tiles": gelaende_tiles, "figure": gelaende_figure, "items": ("Messpunkt", "Bodenprobe", "Pflock"),
                 "about": "a survey area: a surveyor, meadow, woods, water, measuring points",
                 "geschafft": ("GEBIET ERFASST", (226, 238, 214), (50, 110, 60)),
                 "halt": ("EINSATZ ABGEBROCHEN", (226, 238, 214), (180, 70, 50))},
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
                    world["figure"](d, (k * 2 + walking) * T, n * T, colour, direction, bool(walking), n)
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
