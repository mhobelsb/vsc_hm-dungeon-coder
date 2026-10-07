"""Replaying traces (trace.py): in the game, to watch what a program did, or in the simulator,
to list where the hero stood after every call.

    python -m dungeoncoder replay spur.json [--run N] [--pace 4]
    python -m dungeoncoder trace spur.json [--run N]
"""
import json
import os
import tempfile

# how a recorded call is made again: the Hero method and its arguments from the params
ARGUMENTS = {"configure": ("name", "typeNumber"), "set_pace": ("factor",), "pickup": ("name",), "drop": ("name",),
             "peek_item_value": ("distance",)}
GAME_CALLS = ("get_statistics", "reset_level")


def _level_file(run):
    path = os.path.join(tempfile.mkdtemp(prefix="dungeoncoder-replay-"), "level.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(run["level"], f)
    return path


def call(game, method, params):
    """Makes one recorded call again; returns what came back."""
    params = params or {}
    if method == "get_statistics":
        return game.get_statistics()
    if method == "reset_level":
        return game._Game__level.reset()
    heroes = game.get_heroes() if hasattr(game, "get_heroes") else [game.get_hero()]
    hero = heroes[params.get("hero", 0)] if params.get("hero", 0) < len(heroes) else heroes[0]
    args = [params[name] for name in ARGUMENTS.get(method, ()) if name in params]
    return getattr(hero, method)(*args)


def replay(run, pace=None, out=print):
    """Plays a run again on the game (or on the simulator, if it is switched on). Returns the
    number of the first call whose answer differs from the recording (1-based), or None."""
    from .dungeoncoder import Game
    game = Game(_level_file(run))
    if pace is not None:
        game.get_hero().set_pace(pace)
    for n, (method, params, recorded) in enumerate(run["calls"], start=1):
        if method == "set_pace" and pace is not None:
            continue
        now = call(game, method, params)
        if method not in GAME_CALLS and now != recorded:
            out(f"call {n} {method}: recorded {recorded!r}, now {now!r} - the run differs from here on")
            return n
    return None


def positions(run):
    """[(call number, method, params, result, (col, row), direction)] for every call of the run,
    replayed in a fresh simulator: where the hero stood after it."""
    from . import dungeoncoder as core
    from .sim import Simulator
    before = core._simulator
    core._simulator = Simulator(level_override="")
    rows = []
    try:
        from .dungeoncoder import Game
        game = Game(_level_file(run))
        sim = core._simulator
        for n, (method, params, recorded) in enumerate(run["calls"], start=1):
            result = call(game, method, params)
            hero = sim.level.character
            rows.append((n, method, params, result, sim.level.cell_of(hero), sim.direction()))
        rows.append(("end", "get_statistics", None, game.get_statistics(), sim.level.cell_of(sim.level.character),
                     sim.direction()))
    finally:
        core._simulator = before
    return rows


def describe(method, params):
    args = ", ".join(repr(v) for k, v in (params or {}).items() if k != "hero")
    who = f"hero {params['hero']}: " if params and params.get("hero") else ""
    return f"{who}{method}({args})"
