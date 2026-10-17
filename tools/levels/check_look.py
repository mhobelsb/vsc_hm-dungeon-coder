"""Hints on the look of a text map (not its logic: that is check_level.py), after the patterns of
good hand-built levels (the course workspace's docs/level-muster.md). Nothing is an error; every
hint names the fields.

    python3 tools/levels/check_look.py MAP.txt [MAP.txt ...]

Checks: torches without a partner in their row or column; a tall obstacle against a south wall
(it hides the wall); a floor tone ":" that ends in the open (not at a wall or door); a door or
gap in a one-row wall (an arch needs two rows, muster: bogen); a goal that gets no alcove (a dead
end three fields wide, entered northwards); decoration on the shortest way from the hero to the
goal; too many obstacles for the floor (over 40 %); "deko:" above 10; "muster:" missing on a map
that could use it. Messages are German, like check_level.py's.
"""
import collections
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
API = os.path.normpath(os.path.join(HERE, "..", "..", "api", "python", "dungeoncoder", "asciimap.py"))


def _asciimap():
    spec = importlib.util.spec_from_file_location("asciimap", API)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


am = _asciimap()
SOLID = (am.WALL, "T", "t", am.PROP, am.VOID)
PASSABLE_OBJECTS = "DGsCJ*KoW"           # the hero can reach these fields (doors counted as open)


def hints(text):
    """The hints for the text of a map file, as strings."""
    header, rows = am.parse_text(text)
    if "generate" in header:
        return ["eine erzeugte Karte (generate:): nichts zu prüfen"]
    h, w = len(rows), max((len(r) for r in rows), default=0)
    grid = [list(r.ljust(w)) for r in rows]
    out = []

    def at(x, y):
        return grid[y][x] if 0 <= x < w and 0 <= y < h else am.VOID

    def walkable(x, y):
        return at(x, y) not in SOLID and at(x, y) != am.ABYSS
    cells = {(x, y): ch for y in range(h) for x in range(w) for ch in [grid[y][x]]}
    floor = [p for p, ch in cells.items() if ch not in SOLID]
    muster = header.get("muster", [])
    arches = header.get("style", ["dungeon"])[0] in ("dungeon", "maze")     # only the dungeon styles have arches
    # torches in pairs
    torches = [p for p, ch in cells.items() if ch in "Tt"]
    lonely = [(x, y) for x, y in torches
              if not any((tx == x or ty == y) and (tx, ty) != (x, y) and 2 <= abs(tx - x) + abs(ty - y) <= 14
                         for tx, ty in torches)]
    if lonely:
        out.append("Fackeln ohne Paar (die Vorbilder hängen Fackeln paarweise in einer Reihe oder Spalte): "
                   + " ".join(f"({x},{y})" for x, y in lonely))
    # a tall obstacle against a south wall hides the wall band
    south = [(x, y) for (x, y), ch in cells.items() if ch == am.PROP and at(x, y + 1) in (am.WALL, "T", "t")
             and at(x, y - 1) not in SOLID]
    if south:
        out.append("Requisiten vor einer Südwand (sie verdecken das Wandband; besser an die Nordwand oder in eine Ecke): "
                   + " ".join(f"({x},{y})" for x, y in south))
    # a floor tone should end at a wall or door
    loose = [(x, y) for (x, y), ch in cells.items() if ch == am.ALT
             for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
             if at(x + dx, y + dy) in (am.FLOOR, am.PATH, am.DETAIL)
             and not any(at(x + dx + ex, y + dy + ey) in (am.WALL, "D", "G") for ex, ey in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    if loose:
        out.append("Bodenton ':' endet im freien Raum statt an einer Wand oder Tür (die Vorbilder wechseln den Boden an Wandlinien): "
                   + " ".join(f"({x},{y})" for x, y in sorted(set(loose))[:8]))
    # doorways in one-row walls: no arch possible
    thin = []
    for (x, y), ch in cells.items():
        if ch in "DG." and at(x - 1, y) == am.WALL and at(x + 1, y) == am.WALL and walkable(x, y - 1) and walkable(x, y + 1):
            above_wall = at(x - 1, y - 1) == am.WALL and at(x + 1, y - 1) == am.WALL
            below_wall = at(x - 1, y + 1) == am.WALL and at(x + 1, y + 1) == am.WALL
            if not above_wall and not below_wall and ch in "DG":
                thin.append((x, y))
    if thin and arches:
        out.append("Tür oder Gitter in einer einreihigen Wand: Ein Torbogen (muster: bogen) braucht zwei Wandreihen: "
                   + " ".join(f"({x},{y})" for x, y in thin))
    # the goal's alcove
    for (x, y), ch in cells.items():
        if ch != "Z":
            continue
        wallish = (am.WALL, "T", "t", am.VOID)
        alcove = (at(x - 1, y) == am.FLOOR and at(x + 1, y) == am.FLOOR and at(x - 2, y) in wallish
                  and at(x + 2, y) in wallish and all(at(x + dx, y - 1) in wallish for dx in (-1, 0, 1))
                  and walkable(x, y + 1))
        if not alcove and arches:
            out.append(f"Ziel ({x},{y}) ohne Nische: eine Sackgasse drei Felder breit, von Süden betreten, bekommt Treppe und "
                       "Torbogen (muster: bogen)")
    # decoration on the shortest way
    heroes = [p for p, ch in cells.items() if ch == "H"]
    goals = [p for p, ch in cells.items() if ch == "Z"]
    if heroes and goals:
        start, goal = heroes[0], goals[0]
        prev, todo, seen = {start: None}, collections.deque([start]), {start}
        while todo:
            p = todo.popleft()
            if p == goal:
                break
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (p[0] + dx, p[1] + dy)
                if q not in seen and (walkable(*q) or at(*q) in PASSABLE_OBJECTS) and 0 <= q[0] < w and 0 <= q[1] < h:
                    seen.add(q)
                    prev[q] = p
                    todo.append(q)
        if goal in prev:
            path, p = [], goal
            while p is not None:
                path.append(p)
                p = prev[p]
            on_path = [p for p in path if cells[p] == am.DETAIL]
            if on_path:
                out.append("Details '\"' auf dem kürzesten Weg von H nach Z (Bilder in Übungstexten bleiben lesbarer ohne): "
                           + " ".join(f"({x},{y})" for x, y in on_path[:8]))
    # density
    props = [p for p, ch in cells.items() if ch == am.PROP]
    if floor and len(props) / (len(floor) + len(props)) > 0.4:
        out.append(f"{len(props)} Hindernisse auf {len(floor) + len(props)} Feldern: die Vorbilder lassen etwa zwei Drittel "
                   "des Bodens frei")
    try:
        if int(header.get("deko", ["0"])[0]) > 10:
            out.append("deko: über 10 streut viel; die Vorbilder sammeln Details um Dinge und lassen den freien Boden ruhig")
    except ValueError:
        pass
    if not muster and (len(rows) >= 6):
        out.append("kein muster: (wandansicht, requisiten, bogen, aussen, gruben, flecken, vielfalt oder alle): "
                   "die Karte wird gebaut wie bisher")
    return out


def main(args):
    if not args:
        print(__doc__)
        return 2
    for path in args:
        with open(path, encoding="utf-8") as f:
            found = hints(f.read())
        print(f"== {path}: {len(found)} Hinweis(e)")
        for line in found:
            print("  " + line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
