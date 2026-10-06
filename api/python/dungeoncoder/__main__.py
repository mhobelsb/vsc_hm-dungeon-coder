"""Setup check: `python -m dungeoncoder` (in the exercise folder, with the Python that runs your programs).

Prints what a program of yours will use: the Python, this package, where the game is expected,
whether it answers and fits, the asset packs, and whether the simulator runs. Each line starts with
ok, note or PROBLEM; a PROBLEM line says what to do.
"""
import os
import sys


def line(state, text):
    print(f"{state:8} {text}")


def main():
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
                line("ok", f"asset pack {pack}")
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


if __name__ == "__main__":
    sys.exit(main())
