"""Generated levels: the same seed always gives the same level.

    from dungeoncoder import Game
    game = Game.generate(seed=7)                         # a 15x11 maze
    game = Game.generate(seed=7, width=21, height=15, loops=4, fog="dark")

    from dungeoncoder.generator import maze_text
    print(maze_text(seed=7))                             # the map as text (asciimap format)

Kinds: "maze" (corridors), "rooms" (rooms joined by doorways), "pillars" (an open
hall with free-standing pillars). In rooms and halls the exit lies inside, away
from the outer wall.

A maze is built with a randomised depth-first search ("recursive backtracker"):
every free field is reachable, and without `loops` there is exactly one way
between any two fields. `loops` knocks that many extra holes into inner walls;
that creates cycles, and walls that stand free like pillars, where the
right-hand rule can circle forever.
"""
import random

from .asciimap import GRID_H, GRID_W, MapError

KINDS = ("maze", "rooms", "pillars")


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


def _reachable(grid, start):
    seen, todo = {start}, [start]
    while todo:
        x, y = todo.pop()
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if grid[n[1]][n[0]] != "#" and n not in seen:
                seen.add(n)
                todo.append(n)
    return seen


def _inner_goal(rng, grid, start):
    """A free field not next to the outer wall, reachable from the start, far from it."""
    width, height = len(grid[0]), len(grid)
    reach = _reachable(grid, start)
    options = [(x, y) for (x, y) in reach if 2 <= x <= width - 3 and 2 <= y <= height - 3
               and abs(x - start[0]) + abs(y - start[1]) >= (width + height) // 3]
    return rng.choice(sorted(options)) if options else None


def rooms_grid(seed, width=15, height=11):
    """Rooms separated by walls one field thick, with one or two doorways per wall."""
    _check_size(width, height)
    rng = random.Random(seed)
    grid = [["#"] * width for _ in range(height)]
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            grid[y][x] = "."
    cols = sorted(rng.sample(range(4, width - 4), k=min(2, max(0, (width - 8) // 4))))
    rows = sorted(rng.sample(range(3, height - 3), k=min(1, max(0, (height - 6) // 3))))
    cols = [c for i, c in enumerate(cols) if i == 0 or c - cols[i - 1] >= 3]
    for c in cols:
        for y in range(1, height - 1):
            grid[y][c] = "#"
    for r in rows:
        for x in range(1, width - 1):
            grid[r][x] = "#"
    # doorways: every wall segment between two crossings gets one opening
    lines_x, lines_y = [0] + cols + [width - 1], [0] + rows + [height - 1]
    for c in cols:
        for a, b in zip(lines_y, lines_y[1:]):
            grid[rng.randrange(a + 1, b)][c] = "."
    for r in rows:
        for a, b in zip(lines_x, lines_x[1:]):
            grid[r][rng.randrange(a + 1, b)] = "."
    return grid


def pillars_grid(seed, width=15, height=11, pillars=None):
    """An open hall with free-standing pillars (1x1 or 2x2) that never touch each other or the wall."""
    _check_size(width, height)
    rng = random.Random(seed)
    grid = [["#"] * width for _ in range(height)]
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            grid[y][x] = "."
    count = pillars if pillars is not None else max(2, (width * height) // 30)
    placed, tries = 0, 0
    while placed < count and tries < 500:
        tries += 1
        size = rng.choice((1, 2))
        x, y = rng.randrange(2, width - 2 - size), rng.randrange(2, height - 2 - size)
        cells = [(x + dx, y + dy) for dx in range(size) for dy in range(size)]
        ring = [(cx + ex, cy + ey) for cx, cy in cells for ex in (-1, 0, 1) for ey in (-1, 0, 1)]
        if all(grid[ry][rx] == "." for rx, ry in ring):
            for cx, cy in cells:
                grid[cy][cx] = "#"
            placed += 1
    return grid


def _check_size(width, height):
    if not (7 <= width <= GRID_W and 7 <= height <= GRID_H):
        raise MapError(f"a level must be between 7x7 and {GRID_W}x{GRID_H}, got {width}x{height}")


def level_text(seed, kind="maze", width=15, height=11, loops=0, pillars=None, start="east", **properties):
    """The generated level as a map text (asciimap format). Keyword arguments that
    aren't options become map properties, e.g. fog="dark"."""
    if kind not in KINDS:
        raise MapError(f"unknown kind {kind!r}; available: {', '.join(KINDS)}")
    if kind == "maze":
        return maze_text(seed, width, height, loops, start, **properties)
    grid = rooms_grid(seed, width, height) if kind == "rooms" else pillars_grid(seed, width, height, pillars)
    goal = _inner_goal(random.Random(seed * 7919 + 1), grid, (1, 1))
    if goal is None:
        raise MapError(f"seed {seed}: no place for the exit")
    grid[1][1] = "H"
    grid[goal[1]][goal[0]] = "Z"
    header = [f"start: {start}", "style: maze", f"kind: {kind}", f"seed: {seed}"]
    header += [f"{key}: {str(value).lower() if isinstance(value, bool) else value}"
               for key, value in properties.items() if value is not None]
    return "\n".join(header + ["---"] + ["".join(row) for row in grid]) + "\n"


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
    return level_text(seed, kind, **options)
