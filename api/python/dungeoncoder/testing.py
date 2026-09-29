"""Helpers for testing Dungeon Coder programs with pytest, in the simulator.

    from dungeoncoder.testing import spiel

    def test_umdrehen_zweimal_ist_wie_vorher():
        game, hero = spiel(\"\"\"
            start: east
            ---
            #####
            #H..#
            #####
        \"\"\")
        umdrehen(hero)
        umdrehen(hero)
        assert not hero.is_facing_north() and hero.move()

spiel(...) switches to the simulator (no VS Code needed, steps take no time) and
loads a level: a map text (see asciimap.py), a .txt map file, or a .json level.
"""
import os
import tempfile
import textwrap

from . import dungeoncoder as _core
from .asciimap import GRID_H, GRID_W, parse_text
from .dungeoncoder import Game, Hero

_versatz = (0, 0)       # where the last map text was placed on the 30x20 field


def spiel(level: str) -> tuple[Game, Hero]:
    """(game, hero) for a level in the simulator. `level` is a map text or a file path."""
    if _core._simulator is None:
        _core.use_simulator()
    if "\n" in level:
        path = os.path.join(tempfile.mkdtemp(prefix="dungeoncoder-test-"), "level.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(textwrap.dedent(level).strip("\n") + "\n")
    else:
        path = level
    global _versatz
    if path.endswith(".txt"):
        with open(path, encoding="utf-8") as f:
            _, rows = parse_text(f.read())
        _versatz = ((GRID_W - max((len(r) for r in rows), default=0)) // 2, (GRID_H - len(rows)) // 2)
    else:
        _versatz = (0, 0)
    game = Game(path)
    return game, game.get_hero()


def wachen() -> list[tuple[int, int]]:
    """Nur für Tests im Simulator: wo die Wächter gerade stehen, (x, y) in den Koordinaten
    der Karte, wie sie geschrieben ist. Im echten Spiel gibt es das nicht: dort sieht die
    Heldin einen Wächter nur mit is_enemy_in_front()."""
    if _core._simulator is None or _core._simulator.level is None:
        raise RuntimeError("wachen() gibt es nur im Simulator, nach spiel(...)")
    level = _core._simulator.level
    ox, oy = _versatz
    return [(c - ox, r - oy) for c, r in (level.cell_of(o) for o in level.objects if o.kind == "Guard")]


game_for = spiel     # English name
