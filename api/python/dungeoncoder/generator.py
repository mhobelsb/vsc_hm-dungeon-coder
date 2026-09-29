"""Generated levels: the same seed always gives the same level.

    from dungeoncoder import Game
    game = Game.generate(seed=7)                         # a 15x11 maze
    game = Game.generate(seed=7, width=21, height=15, loops=4, fog="dark")

    from dungeoncoder.generator import maze_text
    print(maze_text(seed=7))                             # the map as text (asciimap format)

A maze is built with a randomised depth-first search ("recursive backtracker"):
every free field is reachable, and without `loops` there is exactly one way
between any two fields. `loops` knocks that many extra holes into inner walls;
that creates cycles, and walls that stand free like pillars, where the
right-hand rule can circle forever.
"""
import random

from .asciimap import GRID_H, GRID_W, MapError

KINDS = ("maze",)


def maze_grid(seed, width=15, height=11, loops=0):
    """The maze as a list of rows of "#" and "." (start top left, goal bottom right)."""
    if width % 2 == 0 or height % 2 == 0:
        raise MapError(f"width and height must be odd (walls between the paths), got {width}x{height}")
    if not (5 <= width <= GRID_W - 1 and 5 <= height <= GRID_H - 1):
        raise MapError(f"a maze must be between 5x5 and {GRID_W - 1}x{GRID_H - 1}, got {width}x{height}")
    rng = random.Random(seed)
    grid = [["#"] * width for _ in range(height)]
    cells_x, cells_y = range(1, width, 2), range(1, height, 2)
    start = (1, 1)
    grid[1][1] = "."
    stack, seen = [start], {start}
    while stack:
        x, y = stack[-1]
        options = [(x + dx, y + dy) for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2))
                   if x + dx in cells_x and y + dy in cells_y and (x + dx, y + dy) not in seen]
        if not options:
            stack.pop()
            continue
        nx, ny = rng.choice(options)
        grid[(y + ny) // 2][(x + nx) // 2] = "."
        grid[ny][nx] = "."
        seen.add((nx, ny))
        stack.append((nx, ny))
    # loops: open inner walls that separate two paths (never the outer wall)
    candidates = [(x, y) for y in range(1, height - 1) for x in range(1, width - 1)
                  if grid[y][x] == "#" and ((x % 2 == 0 and y % 2 == 1) or (x % 2 == 1 and y % 2 == 0))]
    rng.shuffle(candidates)
    for x, y in candidates[:loops]:
        grid[y][x] = "."
    return grid


def maze_text(seed, width=15, height=11, loops=0, start="east", **properties):
    """The maze as a map text for asciimap: hero top left, goal bottom right.
    Further keyword arguments become map properties, e.g. fog="dark"."""
    grid = maze_grid(seed, width, height, loops)
    grid[1][1] = "H"
    grid[height - 2][width - 2] = "Z"
    header = [f"start: {start}", "style: maze", f"seed: {seed}"]
    header += [f"{key}: {str(value).lower() if isinstance(value, bool) else value}"
               for key, value in properties.items() if value is not None]
    return "\n".join(header + ["---"] + ["".join(row) for row in grid]) + "\n"


def generate_text(seed, kind="maze", **options):
    if kind not in KINDS:
        raise MapError(f"unknown kind {kind!r}; available: {', '.join(KINDS)}")
    return maze_text(seed, **options)
