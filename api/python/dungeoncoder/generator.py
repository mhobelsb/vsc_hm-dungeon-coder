"""Generated levels: the same seed always gives the same level.

    from dungeoncoder import Game
    game = Game.generate(seed=7)                         # a 15x11 maze
    game = Game.generate(seed=7, width=21, height=15, loops=4, fog="dark")

    from dungeoncoder.generator import maze_text
    print(maze_text(seed=7))                             # the map as text (asciimap format)

Kinds: "maze" (corridors), "rooms" (rooms joined by doorways), "pillars" (an open
hall with free-standing pillars), "arena" (a live game for several teams: a maze with
one start niche per team along the edge and a hall with pillars and valued crystals
in the middle; `teams`, `items`, `loops`; the heroes' ways to the middle are of similar
length, checked by breadth-first search, or the seed is skipped for the next one).
In rooms and halls the exit lies inside, away from the outer wall.

A maze is built with a randomised depth-first search ("recursive backtracker"):
every free field is reachable, and without `loops` there is exactly one way
between any two fields. `loops` knocks that many extra holes into inner walls;
that creates cycles, and walls that stand free like pillars, where the
right-hand rule can circle forever.
"""
import random

from .asciimap import MapError, default_style

KINDS = ("maze", "rooms", "pillars", "arena")
# a level larger than the game's default view (30 x 20) gets a larger view (the view follows the level)
MAX_SIZE = 99


def maze_grid(seed, width=15, height=11, loops=0):
    """The maze as a list of rows of "#" and "." (start top left, goal bottom right)."""
    if width % 2 == 0 or height % 2 == 0:
        raise MapError(f"width and height must be odd (walls between the paths), got {width}x{height}")
    if not (5 <= width <= MAX_SIZE and 5 <= height <= MAX_SIZE):
        raise MapError(f"a maze must be between 5x5 and {MAX_SIZE}x{MAX_SIZE}, got {width}x{height}")
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


def _distances(grid, start):
    """Breadth-first: the number of steps from start to every reachable field."""
    dist, todo = {start: 0}, [start]
    while todo:
        x, y = todo.pop(0)
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if grid[n[1]][n[0]] != "#" and n not in dist:
                dist[n] = dist[(x, y)] + 1
                todo.append(n)
    return dist


def _ring(width, height):
    """The maze's edge ring (odd coordinates), walked clockwise from the top left."""
    return ([(x, 1) for x in range(1, width - 1, 2)]
            + [(width - 2, y) for y in range(3, height - 1, 2)]
            + [(x, height - 2) for x in range(width - 4, 0, -2)]
            + [(1, y) for y in range(height - 4, 2, -2)])


def _niches(width, height, teams, dist, tolerance=0.07):
    """`teams` start fields on the edge ring whose ways to the middle are equally long (within
    `tolerance` of a common length), spread around the ring; None if no length has enough."""
    ring = [c for c in _ring(width, height) if c in dist]
    if len(ring) < teams:
        return None
    gap = len(ring) // (teams * 2)
    lengths = sorted(set(dist[c] for c in ring), key=lambda d: abs(d - sorted(dist[c] for c in ring)[len(ring) // 2]))
    for target in lengths:
        fitting = [i for i, c in enumerate(ring) if abs(dist[c] - target) <= tolerance * target]
        chosen = []
        for i in fitting:
            if all(min(abs(i - j), len(ring) - abs(i - j)) > gap for j in chosen):
                chosen.append(i)
        if len(chosen) >= teams:
            chosen = [chosen[(k * len(chosen)) // teams] for k in range(teams)]
            return [ring[i] for i in chosen]
    return None


def arena_grid(seed, width=39, height=23, teams=6, loops=6, items=18, room=(11, 7), exits=False):
    """A live game's level, as rows of symbols: a maze from maze_grid, a hall with pillars in the
    middle (`room`: its size, (0, 0) for none), one hero per team on the edge, crystals K (values in
    reading order: the dearest in the hall; without a hall spread evenly), with `exits` an exit Z on the
    first field out of every niche (a team's way home). Returns (grid, values, used_seed, directions):
    the seed is advanced by 1000 until the teams' starts can be chosen with ways to the middle of the
    same length (within 7 percent of a common length, so the longest is at most 15 percent longer
    than the shortest): every start is fair."""
    if not (2 <= teams <= 9):
        raise MapError(f"teams: 2 to 9, got {teams}")
    if width % 2 == 0 or height % 2 == 0:
        raise MapError(f"width and height must be odd, got {width}x{height}")
    rw, rh = room or (0, 0)
    if rw and (rw % 2 == 0 or rh % 2 == 0 or rw > width - 8 or rh > height - 8):
        raise MapError(f"room: odd and at most {width - 8}x{height - 8}, got {rw}x{rh}")
    used = seed
    for _ in range(50):
        grid = maze_grid(used, width, height, loops)
        rng = random.Random(used * 31 + 7)
        # the hall: an open rectangle in the middle with a few pillars
        x0, y0 = (width - rw) // 2, (height - rh) // 2
        for y in range(y0, y0 + rh):
            for x in range(x0, x0 + rw):
                grid[y][x] = "."
        hall = [(x, y) for y in range(y0 + 1, y0 + rh - 1) for x in range(x0 + 1, x0 + rw - 1)]
        for x, y in rng.sample(hall, k=max(1, len(hall) // 12)) if hall else []:
            if all(grid[y + dy][x + dx] == "." for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                grid[y][x] = "#"
        # the middle: the hall's centre, or without a hall the nearest maze cell (odd coordinates)
        centre = (width // 2, height // 2) if rw else (width // 2 | 1, height // 2 | 1)
        dist = _distances(grid, centre)
        starts = _niches(width, height, teams, dist)
        if starts:
            break
        used += 1000
    else:
        raise MapError(f"seed {seed}: no fair arena found")
    directions = []
    exit_cells = []
    for i, (x, y) in enumerate(starts):
        grid[y][x] = "H" if i == 0 else str(i + 1)
        # every hero faces the way out of its niche (the open neighbour nearest the hall)
        open_ = [(d, (x + dx, y + dy)) for d, (dx, dy) in (("north", (0, -1)), ("east", (1, 0)), ("south", (0, 1)), ("west", (-1, 0)))
                 if grid[y + dy][x + dx] == "."]
        best = min(open_, key=lambda o: dist.get(o[1], 10 ** 6)) if open_ else ("south", None)
        directions.append(best[0])
        if exits and best[1]:
            exit_cells.append(best[1])
    for (x, y) in exit_cells:
        grid[y][x] = "Z"
    # crystals: the dearest in the hall, the cheap ones along the ways; values 1 to 5
    free = [(x, y) for y in range(1, height - 1) for x in range(1, width - 1) if grid[y][x] == "."]
    in_hall = [c for c in free if rw and x0 <= c[0] < x0 + rw and y0 <= c[1] < y0 + rh]
    outside = [c for c in free if c not in set(in_hall) and dist.get(c, 0) >= 3]
    dear = rng.sample(in_hall, k=min(len(in_hall), items // 3)) if rw else []
    cheap = rng.sample(outside, k=min(len(outside), items - len(dear)))
    placed = []
    for c in dear:
        placed.append((c, rng.choice((4, 5))))
    for c in cheap:
        placed.append((c, rng.choice((1, 1, 2, 2, 3)) if rw else rng.choice((1, 2, 3, 4, 5))))
    for (x, y), _ in placed:
        grid[y][x] = "K"
    values = [v for (x, y), v in sorted(placed, key=lambda p: (p[0][1], p[0][0]))]
    return grid, values, used, directions


def arena_text(seed, width=39, height=23, teams=6, loops=6, items=18, start="east", style=None, room=(11, 7),
               exits=False, **properties):
    """A live game's level as a map text: arena: true, max_moves 300 and inventory_size 6 unless the
    recipe says otherwise; `codes` (the teams' codes) come from the recipe or the referee's tool.
    room: the hall's size, (0, 0) for none; exits: an exit in every niche."""
    style = style or default_style("maze")
    grid, values, used, directions = arena_grid(seed, width, height, teams, loops, items, room, exits)
    props = {"arena": True, "max_moves": 300, "inventory_size": 6, **properties}
    header = [f"start: {' '.join(directions)}", f"style: {style}", "kind: arena", f"seed: {seed}",
              f"values: {' '.join(map(str, values))}"]
    header += [f"{key}: {str(value).lower() if isinstance(value, bool) else value}"
               for key, value in props.items() if value is not None]
    return "\n".join(header + ["---"] + ["".join(row) for row in grid]) + "\n"


def _check_size(width, height):
    if not (7 <= width <= MAX_SIZE and 7 <= height <= MAX_SIZE):
        raise MapError(f"a level must be between 7x7 and {MAX_SIZE}x{MAX_SIZE}, got {width}x{height}")


def level_text(seed, kind="maze", width=None, height=None, loops=0, pillars=None, start="east", style=None,
               **properties):
    """The generated level as a map text (asciimap format). Keyword arguments that
    aren't options become map properties, e.g. fog="dark". style: the text-map style it is
    drawn in (default maze, which comes with the course's asset pack; without it demo).
    Default size 15x11; an arena 39x23."""
    style = style or default_style("maze")
    width = width or (39 if kind == "arena" else 15)
    height = height or (23 if kind == "arena" else 11)
    if kind not in KINDS:
        raise MapError(f"unknown kind {kind!r}; available: {', '.join(KINDS)}")
    if kind == "maze":
        return maze_text(seed, width, height, loops, start, style=style, **properties)
    if kind == "arena":
        return arena_text(seed, width, height, start=start, style=style, loops=loops, **properties)
    grid = rooms_grid(seed, width, height) if kind == "rooms" else pillars_grid(seed, width, height, pillars)
    goal = _inner_goal(random.Random(seed * 7919 + 1), grid, (1, 1))
    if goal is None:
        raise MapError(f"seed {seed}: no place for the exit")
    grid[1][1] = "H"
    grid[goal[1]][goal[0]] = "Z"
    header = [f"start: {start}", f"style: {style}", f"kind: {kind}", f"seed: {seed}"]
    header += [f"{key}: {str(value).lower() if isinstance(value, bool) else value}"
               for key, value in properties.items() if value is not None]
    return "\n".join(header + ["---"] + ["".join(row) for row in grid]) + "\n"


def maze_text(seed, width=15, height=11, loops=0, start="east", style=None, **properties):
    """The maze as a map text for asciimap: hero top left, goal bottom right.
    Further keyword arguments become map properties, e.g. fog="dark"."""
    style = style or default_style("maze")
    grid = maze_grid(seed, width, height, loops)
    grid[1][1] = "H"
    grid[height - 2][width - 2] = "Z"
    header = [f"start: {start}", f"style: {style}", f"seed: {seed}"]
    header += [f"{key}: {str(value).lower() if isinstance(value, bool) else value}"
               for key, value in properties.items() if value is not None]
    return "\n".join(header + ["---"] + ["".join(row) for row in grid]) + "\n"


def generate_text(seed, kind="maze", **options):
    return level_text(seed, kind, **options)


RECIPE_KEYS = ("generate", "size", "loops", "seed", "start", "style", "pillars", "teams", "items", "room", "exits")


def from_recipe(header):
    """The map text for a recipe, a map file whose header says what to generate:

        generate: maze          # maze, rooms or pillars
        size: 15x11             # width x height (a maze: both odd)
        loops: 2                # a maze: extra openings
        seed: random            # a new level per load (DUNGEONCODER_SEED fixes it), or a number
        fog: explored           # any other key becomes a map property, as in every map

    The map below the header ("---") is ignored. The level's map property `seed` says which
    level it was."""
    from .variants import random_seed

    def one(key, default=None):
        return header.get(key, [default])[0]

    kind = one("generate")
    size = one("size", "39x23" if kind == "arena" else "15x11")
    try:
        width, height = (int(v) for v in size.lower().split("x"))
    except ValueError:
        raise MapError(f"size: expected WIDTHxHEIGHT, e.g. 15x11, got {size!r}") from None
    seed = one("seed", "random")
    if str(seed).lower() == "random":
        seed, _ = random_seed()
    elif str(seed).lstrip("-").isdigit():
        seed = int(seed)
    else:
        raise MapError(f"seed: a whole number or random, got {seed!r}")
    options = {"width": width, "height": height, "start": one("start", "east"), "style": one("style")}
    if kind == "maze":
        options["loops"] = int(one("loops", "0"))
    elif kind == "arena":
        options["loops"] = int(one("loops", "6"))
        options["teams"] = int(one("teams", "6"))
        options["items"] = int(one("items", "18"))
        room = one("room", "11x7")                  # "0" for a maze without a hall
        options["room"] = (0, 0) if room == "0" else tuple(int(v) for v in room.lower().split("x"))
        options["exits"] = one("exits", "") == "niches"
    elif "loops" in header:
        raise MapError("loops: only for generate: maze or arena")
    if "pillars" in header:
        options["pillars"] = int(one("pillars"))
    extra = {key: values[0] for key, values in header.items() if key not in RECIPE_KEYS}
    return level_text(seed, kind, **options, **extra)
