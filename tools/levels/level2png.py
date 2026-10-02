"""Render a Dungeon Coder level (Tiled JSON) to a PNG, without a browser.

For exercise images, EduCode tasks and exam items. Draws the level the way the
engine does (tile layers bottom-anchored with the tiles' x/y offsets, objects in
their initial state), optionally with the engine's torch darkness, and can add
overlays: a coordinate grid, labelled markers and arrows along a path.

usage:
  python3 tools/levels/level2png.py LEVEL.json OUT.png [options]      (needs Pillow)

options:
  --scale N              pixel scale (default 3)
  --crop X0,Y0,X1,Y1     only cells X0..X1, Y0..Y1 (inclusive); "auto" = the level's content
  --grid                 thin cell grid with column/row numbers
  --mark X,Y[,TEXT[,COLOR]]   box around cell (X,Y) with an optional label; repeatable
  --path "X,Y X,Y ..."   arrows along the given cells (orthogonal steps); repeatable
  --path-color COLOR     colour for the following --path (default "#ffcc00")
  --lighting             darken like the game does when torches are off

Cells are 0-based (column, row), the same as in level2ascii.py. Tilesets: DC_ASSET_PACKS, then
the engine's game/assets (dclevel.py).
Example:
  DC_ASSET_PACKS=packs/demo python3 tools/levels/level2png.py packs/demo/levels/demo_raum.json /tmp/r.png \\
      --grid --mark 3,3,Start --path "3,3 3,6"
"""
import argparse
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from dclevel import ASSETS, asset_path  # noqa: E402,F401  (DC_ASSET_PACKS, then DC_ASSETS or the engine's game/assets)
FLIP_MASK = 0x1FFFFFFF


class Tileset:
    def __init__(self, source, firstgid):
        path = os.path.normpath(asset_path(source))
        with open(path) as f:
            data = json.load(f)
        self.firstgid = firstgid
        self.tile_w, self.tile_h = data["tilewidth"], data["tileheight"]
        self.columns = data["columns"]
        self.margin, self.spacing = data.get("margin", 0), data.get("spacing", 0)
        self.count = data["tilecount"]
        self.image = Image.open(os.path.normpath(os.path.join(os.path.dirname(path), data["image"]))).convert("RGBA")
        self.meta = {t["id"]: t for t in data.get("tiles", [])}
        self._cache = {}

    def props(self, local_id):
        return {p["name"]: p["value"] for p in self.meta.get(local_id, {}).get("properties", [])}

    def tile(self, local_id):
        """Returns (image, x_offset, y_offset) for a tile; animated tiles show their first frame."""
        if local_id not in self._cache:
            frame_id = local_id
            anim = self.meta.get(local_id, {}).get("animation")
            if anim:
                frame_id = anim[0]["tileid"]
            row, col = divmod(frame_id, self.columns)
            x = self.margin + col * (self.tile_w + self.spacing)
            y = self.margin + row * (self.tile_h + self.spacing)
            img = self.image.crop((x, y, x + self.tile_w, y + self.tile_h))
            props = self.props(local_id)
            self._cache[local_id] = (img, props.get("x_offset", 0) or 0, props.get("y_offset", 0) or 0)
        return self._cache[local_id]


def find_tileset(tilesets, gid):
    gid &= FLIP_MASK
    for ts in reversed(tilesets):
        if gid >= ts.firstgid:
            local = gid - ts.firstgid
            return (ts, local) if local < ts.count else (None, None)
    return None, None


def flip(img, gid):
    """The picture with Tiled's flip flags of the gid applied (diagonal, then horizontal, then vertical)."""
    if gid & 0x20000000:
        img = img.transpose(Image.TRANSPOSE)
    if gid & 0x80000000:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    if gid & 0x40000000:
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
    return img


def render(level_path, lighting=False):
    with open(level_path) as f:
        level = json.load(f)
    tw, th = level["tilewidth"], level["tileheight"]
    canvas = Image.new("RGBA", (level["width"] * tw, level["height"] * th), (21, 16, 38, 255))
    tilesets = sorted((Tileset(t["source"], t["firstgid"]) for t in level["tilesets"]), key=lambda t: t.firstgid)
    torches = burning = 0

    def paste(img, left, top, opacity=1.0):
        if opacity < 1.0:
            img = img.copy()
            img.putalpha(img.getchannel("A").point(lambda a: int(a * opacity)))
        canvas.alpha_composite(img, (int(left), int(top))) if left >= 0 and top >= 0 else canvas.paste(img, (int(left), int(top)), img)

    for layer in level["layers"]:
        if not layer.get("visible", True):
            continue
        if layer["type"] == "tilelayer":
            width = layer["width"]
            for i, gid in enumerate(layer["data"]):
                ts, local = find_tileset(tilesets, gid)
                if not ts:
                    continue
                row, col = divmod(i, width)
                img, xo, yo = ts.tile(local)
                img = flip(img, gid)
                paste(img, col * tw + xo, row * th + th - img.height + yo, layer.get("opacity", 1))
        elif layer["type"] == "objectgroup":
            for obj in layer["objects"]:
                ts, local = find_tileset(tilesets, obj.get("gid", 0))
                if not ts:
                    continue
                cls = ts.meta.get(local, {}).get("type") or obj.get("type")
                if cls == "Torch":
                    torches += 1
                    burning += ts.props(local).get("state") == "burning"
                if obj.get("visible", True) is False:
                    continue
                img, xo, yo = ts.tile(local)
                img = flip(img, obj.get("gid", 0))
                paste(img, obj["x"] + xo, obj["y"] - img.height + yo)

    if lighting and torches:
        darkness = int(255 * (1 - burning / torches))
        canvas.alpha_composite(Image.new("RGBA", canvas.size, (0, 0, 0, darkness)))
    return canvas, tw, th


def cell_center(x, y, tw, th, scale):
    return ((x + 0.5) * tw * scale, (y + 0.5) * th * scale)


def draw_arrow(draw, start, end, color, width):
    draw.line([start, end], fill=color, width=width)
    # arrowhead
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = max((dx * dx + dy * dy) ** 0.5, 1)
    ux, uy = dx / length, dy / length
    size = width * 3
    left = (end[0] - ux * size - uy * size * 0.6, end[1] - uy * size + ux * size * 0.6)
    right = (end[0] - ux * size + uy * size * 0.6, end[1] - uy * size - ux * size * 0.6)
    draw.polygon([end, left, right], fill=color)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("level")
    parser.add_argument("out")
    parser.add_argument("--scale", type=int, default=3)
    parser.add_argument("--crop")
    parser.add_argument("--grid", action="store_true")
    parser.add_argument("--mark", action="append", default=[])
    parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--path-color", default="#ffcc00")
    parser.add_argument("--lighting", action="store_true")
    args = parser.parse_args()

    img, tw, th = render(args.level, args.lighting)
    s = args.scale
    img = img.resize((img.width * s, img.height * s), Image.NEAREST)
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=max(10, 5 * s))
    small = ImageFont.load_default(size=max(8, 3 * s))

    if args.grid:
        cols, rows = img.width // (tw * s), img.height // (th * s)
        for c in range(cols + 1):
            draw.line([(c * tw * s, 0), (c * tw * s, img.height)], fill=(255, 255, 255, 60), width=1)
        for r in range(rows + 1):
            draw.line([(0, r * th * s), (img.width, r * th * s)], fill=(255, 255, 255, 60), width=1)
        for c in range(cols):
            draw.text((c * tw * s + 2, 1), str(c), fill="white", font=small, stroke_width=1, stroke_fill="black")
        for r in range(1, rows):
            draw.text((2, r * th * s + 1), str(r), fill="white", font=small, stroke_width=1, stroke_fill="black")

    for path in args.path:
        cells = [tuple(int(v) for v in p.split(",")) for p in path.split()]
        points = [cell_center(x, y, tw, th, s) for x, y in cells]
        for a, b in zip(points, points[1:]):
            draw_arrow(draw, a, b, args.path_color, max(2, s))

    for mark in args.mark:
        parts = mark.split(",")
        x, y = int(parts[0]), int(parts[1])
        text = parts[2] if len(parts) > 2 else ""
        color = parts[3] if len(parts) > 3 else "#ff3333"
        box = [x * tw * s, y * th * s, (x + 1) * tw * s - 1, (y + 1) * th * s - 1]
        draw.rectangle(box, outline=color, width=max(2, s))
        if text:
            draw.text((box[0], box[1] - 6 * s), text, fill=color, font=font, stroke_width=2, stroke_fill="black")

    if args.crop == "auto":
        # the bounding box of everything that isn't plain void, plus a margin of one cell
        sys.path.insert(0, HERE)
        from dclevel import VOID, Level
        level = Level(args.level)
        cells = [(c, r) for r in range(level.height) for c in range(level.width)
                 if level.terrain(c, r) != VOID] + [o["cell"] for o in level.objects()]
        x0, y0 = max(min(c for c, _ in cells) - 1, 0), max(min(r for _, r in cells) - 1, 0)
        x1 = min(max(c for c, _ in cells) + 1, level.width - 1)
        y1 = min(max(r for _, r in cells) + 1, level.height - 1)
        img = img.crop((x0 * tw * s, y0 * th * s, (x1 + 1) * tw * s, (y1 + 1) * th * s))
    elif args.crop:
        x0, y0, x1, y1 = (int(v) for v in args.crop.split(","))
        img = img.crop((x0 * tw * s, y0 * th * s, (x1 + 1) * tw * s, (y1 + 1) * th * s))
    img.save(args.out)
    print(f"{args.out}: {img.width}x{img.height}")


if __name__ == "__main__":
    main()
