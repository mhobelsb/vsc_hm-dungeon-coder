"""Run a Dungeon Coder script in the pure-Python simulator (no VS Code, no browser).

usage: python3 tools/levels/run_sim.py <script.py> [args...]

Like run_headless.py: the script runs unmodified in its own folder, with the
`dungeoncoder` package of this repo (api/python), but DUNGEONCODER_SIM=1 switches
it to the simulator (dungeoncoder/sim.py). Prints the level's statistics at the end.
"""
import os
import runpy
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
API = os.path.join(HERE, "..", "..", "api", "python")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    script = os.path.abspath(sys.argv[1])
    os.environ["DUNGEONCODER_SIM"] = "1"
    sys.path.insert(0, API)
    sys.path.insert(0, os.path.dirname(script))
    os.chdir(os.path.dirname(script))
    sys.argv = sys.argv[1:]
    import dungeoncoder
    start = time.time()
    try:
        runpy.run_path(script, run_name="__main__")
    finally:
        game = object.__new__(dungeoncoder.Game)
        game._Game__level = dungeoncoder.Game.Level(dungeoncoder.Game.BASE_URL)
        print(f"--- simulator: {time.time() - start:.2f} s, statistics {game.get_statistics()}")


if __name__ == "__main__":
    main()
