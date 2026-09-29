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
from .dungeoncoder import Game, Hero


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
    game = Game(path)
    return game, game.get_hero()


game_for = spiel     # English name
