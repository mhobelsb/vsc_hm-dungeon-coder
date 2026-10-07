"""Traces: every call a program made, with what came back, per loaded level.

    game.save_trace("spur.json")                   # in a program: the current level so far
    DUNGEONCODER_TRACE=spur.json python prog.py    # every level the program loads, written at the end

A trace holds the level itself (also a generated level or a variant) and the calls in
order, so it can be replayed exactly: `python -m dungeoncoder replay spur.json` shows it
in the game, `python -m dungeoncoder trace spur.json` lists it with the hero's field after
every call (computed in the simulator). Positions are not recorded while the program runs:
the program itself never learns where the hero stands.

Format (JSON):
    {"format": "dungeoncoder-trace", "version": 1,
     "runs": [{"level_file": "levels/x.json", "level": {...Tiled JSON...},
               "calls": [["move", null, true], ["is_switch_in_front", null, false], ...],
               "statistics": {...}}]}
"""
import atexit
import json
import os
import signal
import sys
import threading

FORMAT, VERSION = "dungeoncoder-trace", 1
# calls that only the host/tools make, or that don't belong in a replay
NOT_RECORDED = ("load_level", "get_version")
MAX_CALLS = 50_000         # per run: a program in an endless loop still gives a trace of its start

runs = []                  # one entry per loaded level: {"level_file", "level", "calls", "statistics"}
_level_file = None         # the path the next load_level comes from (set by Game)


def loading(path):
    """Game is about to load the level from `path`."""
    global _level_file
    _level_file = path


def record(method, params, result):
    """Called by dungeoncoder._call for every call (cheap: one list append)."""
    if method == "load_level":
        if result:
            runs.append({"level_file": _level_file, "level": params, "calls": []})
        return
    if method in NOT_RECORDED or not runs:
        return
    if len(runs[-1]["calls"]) >= MAX_CALLS:
        runs[-1]["truncated"] = True
        return
    shown = result.to_dict() if hasattr(result, "to_dict") else result
    if method == "get_statistics":
        runs[-1]["statistics"] = shown
    runs[-1]["calls"].append([method, params, shown])


def document(which=None):
    """The trace as a JSON-ready dict: all runs, or only the run objects in `which`."""
    chosen = runs if which is None else which
    return {"format": FORMAT, "version": VERSION, "runs": chosen}


def write(path, which=None):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(document(which), f, ensure_ascii=False)


def read(path):
    """The runs of a trace file; raises ValueError if it isn't one."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise ValueError(f"{path} is not a Dungeon Coder trace")
    return data["runs"]


def _write_at_exit():
    path = os.environ.get("DUNGEONCODER_TRACE", "").strip()
    if path and runs:
        write(path)


atexit.register(_write_at_exit)


def _stop(signum, frame):
    sys.exit(128 + signum)          # runs the atexit hooks, so the trace is written


# a stopped program (e.g. `variants` ends one in an endless loop) still writes its trace
if os.environ.get("DUNGEONCODER_TRACE", "").strip() and threading.current_thread() is threading.main_thread():
    signal.signal(signal.SIGTERM, _stop)
