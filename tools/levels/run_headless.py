"""Run a Dungeon Coder student script against the dev server in headless Chrome.

Prerequisite (in another terminal, in this repo):
    DC_PORT=3100 npm run dev:browser

usage: python3 tools/levels/run_headless.py <script.py> [screenshot.png]

The script runs unmodified: its working directory is its own folder (so
relative level paths work), and the `dungeoncoder` package of this repo
(api/python) is imported and pointed at DC_PORT (default 3100, so it can run
next to an installed Dungeon Coder extension that holds port 3000). Asset packs:
start the dev server and this tool with the same DC_ASSET_PACKS.
Needs `pip install httpx attrs playwright` and a local Google Chrome.
"""
import os
import runpy
import sys
import time

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("DC_PORT", "3100"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "api", "python"))
import dungeoncoder  # noqa: E402

dungeoncoder.Game.BASE_URL = f"http://127.0.0.1:{PORT}"


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    script = os.path.abspath(sys.argv[1])
    screenshot = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else None
    os.chdir(os.path.dirname(script))
    sys.path.insert(0, os.path.dirname(script))

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 960, "height": 640})
        logs = []
        page.on("console", lambda m: logs.append(f"[{m.type}] {m.text}"))
        page.goto(f"http://127.0.0.1:{PORT}/index.html")
        page.wait_for_timeout(800)  # let the page open its WebSocket

        start = time.time()
        try:
            runpy.run_path(script, run_name="__main__")
        except SystemExit:
            pass
        print(f"--- script finished in {time.time() - start:.1f}s")

        page.wait_for_timeout(700)  # let the last animation settle
        if screenshot:
            page.locator("#gameCanvas").screenshot(path=screenshot)
            print("screenshot:", screenshot)
        errors = [line for line in logs if line.startswith("[error]")]
        print(f"--- browser console: {len(logs)} lines, {len(errors)} errors")
        for line in errors[:15]:
            print("  ", line)
        browser.close()


if __name__ == "__main__":
    main()
