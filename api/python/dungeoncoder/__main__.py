"""`python -m dungeoncoder` (in the exercise folder, with the Python that runs your programs).

    python -m dungeoncoder                          setup check (below)
    python -m dungeoncoder load LEVEL [--seed N]    load a level (.json or .txt) into the game
    python -m dungeoncoder variants PROG LEVEL...   run a program on every level in the simulator
                                                    (--traces DIR keeps a trace of every failed run)
    python -m dungeoncoder replay TRACE [--run N] [--pace X]   watch a trace in the game
    python -m dungeoncoder trace TRACE [--run N]    list a trace with the hero's field after each call

The setup check prints what a program of yours will use: the Python, this package, where the game
is expected, whether it answers and fits, the asset packs, and whether the simulator runs. Each line
starts with ok, note or PROBLEM; a PROBLEM line says what to do.
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import tempfile


def line(state, text):
    print(f"{state:8} {text}")


def _manifest(folder):
    """A pack's pack.json (name, version, engine: the oldest Dungeon Coder it needs, ...), or {}."""
    try:
        with open(os.path.join(folder, "pack.json"), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _at_least(have, need):
    """Version have >= need ("major.minor.patch", missing parts count as 0)."""
    def parts(version):
        return [int(p) if p.isdigit() else 0 for p in str(version).split(".")]
    a, b = parts(have), parts(need)
    width = max(len(a), len(b))
    return a + [0] * (width - len(a)) >= b + [0] * (width - len(b))


def check():
    problems = 0
    version = sys.version.split()[0]
    if sys.version_info >= (3, 10):
        line("ok", f"Python {version} ({sys.executable})")
    else:
        problems += 1
        line("PROBLEM", f"Python {version} is too old: install Python 3.15 from python.org ({sys.executable})")

    import dungeoncoder
    from dungeoncoder import dungeoncoder as core
    here = os.path.dirname(os.path.abspath(dungeoncoder.__file__))
    copied = os.path.dirname(here) == os.getcwd()
    line("ok", f"dungeoncoder {dungeoncoder.__version__}, {'copied into this folder' if copied else 'installed'}: {here}")

    import httpx
    url = core.DEFAULT_BASE_URL
    try:
        answer = httpx.get(url + "/version", timeout=2)
    except httpx.HTTPError:
        answer = None
    if answer is None:
        line("note", f"no game answers at {url}: start it in VS Code with \"Dungeon Coder: Enter the dungeon\" "
                     "(only needed for the game; the simulator works without)")
    elif answer.status_code == 404:
        problems += 1
        line("PROBLEM", f"the game at {url} is an older Dungeon Coder without versions: update the extension "
                        "(Extensions view), or close the other Dungeon Coder")
    else:
        extension = answer.json().get("result", {}).get("extension", "?")
        if extension.split(".")[:2] == dungeoncoder.__version__.split(".")[:2]:
            line("ok", f"the game answers at {url}: Dungeon Coder {extension}, fits")
        else:
            problems += 1
            line("PROBLEM", f"the game at {url} is Dungeon Coder {extension}, this package is "
                            f"{dungeoncoder.__version__}: run \"Dungeon Coder: Copy Python API to workspace\" again")

    packs = [p for p in os.environ.get("DC_ASSET_PACKS", "").split(os.pathsep) if p]
    if packs:
        for pack in packs:
            if os.path.isdir(pack):
                manifest = _manifest(pack)
                need = manifest.get("engine")
                if isinstance(need, str) and not _at_least(dungeoncoder.__version__, need):
                    problems += 1
                    line("PROBLEM", f"asset pack {pack} needs Dungeon Coder {need} or newer, this is "
                                    f"{dungeoncoder.__version__}: update the extension and the Python package")
                else:
                    about = ", ".join(f"{k} {manifest[k]}" for k in ("name", "version") if manifest.get(k))
                    line("ok", f"asset pack {pack}" + (f" ({about})" if about else ""))
            else:
                problems += 1
                line("PROBLEM", f"asset pack {pack} doesn't exist: clone it there (see the exercise sheet)")
    else:
        line("note", "no asset packs in this terminal (DC_ASSET_PACKS); only text maps of the course need them, "
                     "the game finds them through its settings")

    from dungeoncoder.testing import spiel
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        # a style that ships with the package (the course styles come with the course's asset pack)
        _, hero = spiel("start: east\nstyle: station\n---\n#####\n#H.Z#\n#####\n")
        ok = hero.move() and hero.move() and hero.is_at_goal()
    line("ok" if ok else "PROBLEM", "the simulator plays a small map" if ok else "the simulator failed on a small map")
    problems += not ok

    print()
    print("Everything is ready." if not problems else f"{problems} problem(s): see the lines above.")
    return 1 if problems else 0


def load(args):
    from dungeoncoder import Game
    Game(args.level, seed=args.seed)
    print(f"loaded {args.level}")
    return 0


def _runs(path, number):
    from dungeoncoder import trace
    try:
        runs = trace.read(path)
    except (OSError, ValueError) as err:
        print(f"Error: {err}")
        return None
    if not runs:
        print(f"Error: {path} holds no run")
        return None
    if number is None:
        return runs
    if not 1 <= number <= len(runs):
        print(f"Error: {path} has {len(runs)} run(s), not {number}")
        return None
    return [runs[number - 1]]


def replay_command(args):
    from dungeoncoder.replay import replay
    runs = _runs(args.trace, args.run)
    if runs is None:
        return 1
    differs = 0
    for n, run in enumerate(runs, start=1):
        print(f"run {n}: {run.get('level_file') or 'level'}, {len(run['calls'])} calls")
        differs += replay(run, args.pace) is not None
    return 1 if differs else 0


def trace_command(args):
    from dungeoncoder.replay import describe, positions
    runs = _runs(args.trace, args.run)
    if runs is None:
        return 1
    for n, run in enumerate(runs, start=1):
        print(f"run {n}: {run.get('level_file') or 'level'} (fields: column,row of the level)")
        for number, method, params, result, (col, row), direction in positions(run):
            if number == "end":
                stats = result
                print(f"     end   field {col},{row} facing {direction}: "
                      + ", ".join(f"{k} {stats[k]}" for k in ("moves", "turns", "bumps", "level_complete") if k in stats)
                      + (f", missing {', '.join(stats['missing'])}" if stats.get("missing") else ""))
            else:
                print(f"{number:>8}   {describe(method, params):32} -> {result!r:8}  field {col},{row} facing {direction}")
    return 0


def variants_command(args):
    """Runs the program once per level in the simulator: every level it loads is replaced by
    that one (DUNGEONCODER_LEVEL), so the program itself stays unchanged."""
    from dungeoncoder.replay import positions
    from dungeoncoder import trace
    levels = [p for pattern in args.levels for p in sorted(glob.glob(pattern)) or [pattern]]
    if args.traces:
        os.makedirs(args.traces, exist_ok=True)
    package = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    failed = 0
    for level in levels:
        record = os.path.join(tempfile.mkdtemp(prefix="dungeoncoder-variant-"), "trace.json")
        env = {**os.environ, "DUNGEONCODER_SIM": "1", "DUNGEONCODER_LEVEL": os.path.abspath(level),
               "DUNGEONCODER_TRACE": record,
               "PYTHONPATH": os.pathsep.join([package] + [p for p in [os.environ.get("PYTHONPATH")] if p])}
        process = subprocess.Popen([sys.executable, os.path.abspath(args.program)],
                                   cwd=os.path.dirname(os.path.abspath(args.program)) or ".", env=env,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            code = process.wait(timeout=args.timeout)
            note = "" if code == 0 else f"the program stopped with an error (exit {code})"
        except subprocess.TimeoutExpired:
            process.terminate()             # SIGTERM: the program still writes its trace
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
            note = f"no end after {args.timeout} s"
        try:
            run = trace.read(record)[-1]
            stats = positions(run)[-1][3]
        except (OSError, ValueError, IndexError):
            run, stats = None, {}
        ok = bool(stats.get("level_complete")) and not note
        failed += not ok
        detail = (f"{stats.get('moves', 0)} moves, {stats.get('turns', 0)} turns, {stats.get('bumps', 0)} bumps"
                  if stats else "no result")
        if stats.get("missing"):
            detail += ", missing " + ", ".join(stats["missing"])
        print(f"{'done' if ok else 'FAILED':7} {level}: {detail}" + (f"; {note}" if note else ""))
        if not ok and args.traces and run is not None:
            name = os.path.join(args.traces, os.path.splitext(os.path.basename(level))[0] + ".trace.json")
            trace.write(name, [run])
            print(f"        watch it: python -m dungeoncoder replay {name}")
    print(f"{len(levels) - failed} of {len(levels)} level(s) done")
    return 1 if failed else 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        return check()
    parser = argparse.ArgumentParser(prog="python -m dungeoncoder", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("check", help="setup check")
    p.set_defaults(func=lambda _: check())
    p = sub.add_parser("load", help="load a level into the game")
    p.add_argument("level")
    p.add_argument("--seed", type=int)
    p.set_defaults(func=load)
    p = sub.add_parser("variants", help="run a program on several levels in the simulator")
    p.add_argument("program")
    p.add_argument("levels", nargs="+")
    p.add_argument("--traces", help="folder for the traces of failed runs")
    p.add_argument("--timeout", type=int, default=60)
    p.set_defaults(func=variants_command)
    p = sub.add_parser("replay", help="watch a trace in the game")
    p.add_argument("trace")
    p.add_argument("--run", type=int)
    p.add_argument("--pace", type=float)
    p.set_defaults(func=replay_command)
    p = sub.add_parser("trace", help="list a trace")
    p.add_argument("trace")
    p.add_argument("--run", type=int)
    p.set_defaults(func=trace_command)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
