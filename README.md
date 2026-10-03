# Dungeon Coder

A VS Code extension in which you steer a hero through a pixel-art dungeon **with a Python program**. The game runs in a VS Code tab; your script sends it commands such as `hero.move()` over a local REST API and gets answers such as `True` or `False`. It was built for a first-semester course on computational thinking at Munich University of Applied Sciences, where the exercises train both programming and critical thinking: predict before you run, test on levels you haven't seen, measure instead of believing.

![](game/assets/images/dungeon_coder.png)

## Using it

**Install:** Python 3.10+ (developed on 3.15), VS Code 1.102+, this extension, and the VS Code Python extension.

**First program**, in a folder opened in VS Code:

1. Command palette (`Ctrl/Cmd+Shift+P`) → **Dungeon Coder: Copy Python API to workspace**. This creates the folder `dungeoncoder/`; then `pip install -r dungeoncoder/requirements.txt` (in a virtual environment).
2. Command palette → **Dungeon Coder: Enter the dungeon**. The game opens in a tab and listens on `http://127.0.0.1:3000`.
3. Write a level as text (`karte.txt`; `#` wall, `.` floor, `H` hero, `Z` exit) and a script, and run it:

```text
start: east
---
######
#H...#
#...Z#
######
```

```python
from dungeoncoder import Game

game = Game("karte.txt")          # a text map, or a Tiled level (.json)
hero = game.get_hero()
while not hero.is_collision_in_front():
    hero.move()
print(game.get_statistics()["moves"])
```

**The hero only senses the field in front of it** (`is_collision_in_front()`, `is_abyss_in_front()`, `is_switch_in_front()`, `is_torch_in_front()`, `is_enemy_in_front()`, `is_at_goal()`, `get_items_at_position()`, …) and acts with `move()`, `turn_left()`, `interact()`, `pickup(name)`, `drop(name)`. There is deliberately no `turn_right()` and no `get_position()`: building those yourself is part of the learning. Every method has a docstring; `help(hero)` lists them. Business outcomes never raise: a blocked step returns `False`.

**Without VS Code:** `dungeoncoder.use_simulator()` (or `DUNGEONCODER_SIM=1`) runs the same script in a pure-Python simulator of the game's rules: no window, no waiting, the same answers. That is what automatic grading and `pytest` use (`dungeoncoder.testing.spiel(map_text)` gives `(game, hero)` for a test).

**Settings:**

| Setting | Default | Meaning |
|---|---|---|
| `dungeonCoder.assetPacks` | `[]` | folders with asset packs (tilesets, images, text-map styles), searched before the extension's own pictures; relative paths start at the workspace folder |
| `dungeonCoder.port` | `3000` | the API port; scripts in the workspace find it through `.dungeoncoder-port` (or `DUNGEONCODER_PORT`) |

## Levels and asset packs

- **Levels** are [Tiled](https://www.mapeditor.org/) maps (JSON), or text maps that `Game("x.txt")` turns into one. Map properties switch on the game's mechanics: `fog` (`explored`/`dark`), `keyboard: false`, `win` (`all_sweets`, `all_switches`, `sorted`, `stable`), `inventory_size`, `hero_inventory`, `fernrohr`, `orakel`, and more; text maps write them as header lines. `Game.generate(seed, kind="maze")` builds a seeded maze.
- **Asset packs** hold the pictures: a folder with `tilesets/`, `images/`, optionally `styles/` (text-map styles) and a `pack.json`. A tile's class (`Torch`, `Switch`, `Door`, `Goal`, `Abyss`, …) and its properties (`collision`, `state`, `item`) give it its rules, so a pack can redraw the whole game without touching levels or code. The free **demo pack** in `packs/demo/` (CC0, drawn by `tools/make_demo_pack.py`, 16 px and 32 px tiles) shows the format. A level whose tilesets no pack has is refused with a message naming the missing tileset.

## Developing

**Prerequisites:** Node.js 18+ and npm, VS Code 1.102+, Python 3.

```bash
npm install
npm run compile         # development build -> dist/extension.js (also: watch, package)
npm run lint            # eslint on src, game/src, game/test, tools
npm run test:engine     # unit tests of the game's rules in Node (no browser, demo pack)
npm run compile-tests   # type check
npm run check:version   # package.json, dungeoncoder.__version__ and openapi.yaml agree
npm run build:wheel     # the Python package dungeoncoder as a wheel -> out/wheel/
npm run test:download   # once: VS Code for the integration tests -> ~/.cache/vscode-test
npm test                # integration tests in a real VS Code (src/test/)
```

`compile`, `watch` and `package` first run `npm run generate`, which derives from **`api/openapi.yaml`, the single source of truth for the REST API**: `game/src/commands.js` (command registry and route table for both servers), `src/generated/api-types.d.ts`, `game/src/api-config.js` and `api/python/dungeoncoder/_api_config.py`. Only the last one is committed (a `pip install` from git can't run the generator). The low-level Python client `api/python/dungeoncoder/_generated/` is committed (students need no code generator); regenerate it after changing the spec with `npm run generate:python-client` (creates its own venv in `.codegen-venv/`). `npm test` runs the VS Code test runner on `test-fixtures/side-by-side/exercise`, an exercise folder whose `.vscode/settings.json` names an asset pack by a relative path: it starts the game and loads a level of that pack over the REST API.

**The Python package** lives in `api/python/` (`pyproject.toml`) and has the extension's version. Install it with `pip install "git+<repo URL>#subdirectory=api/python"` or from a wheel built by `npm run build:wheel`. The command "Copy Python API to workspace" still copies it into a workspace (offline use); a copied folder sits next to the scripts and wins over an installed package.

**Run in VS Code:** press **F5** (needs the recommended extension `amodio.tsl-problem-matcher`; without it the window may report "Extension host did not start in 10 seconds"), or `code --extensionDevelopmentPath="$PWD" <folder>` after `npm run compile`. Close the game tab of an installed Dungeon Coder first, since both use port 3000. For the game canvas, use "Developer: Open Webview Developer Tools".

**Run in a browser** (faster loop, no VS Code):

```bash
DC_PORT=3100 DC_ASSET_PACKS=packs/demo npm run dev:browser
# open http://127.0.0.1:3100/index.html, then run scripts with
DUNGEONCODER_PORT=3100 python my_script.py
```

The dev server serves the same REST API and game page as the extension and relays to the browser tab over a WebSocket on port 8000 (fixed, so one dev server at a time).

### Layout

| Path | What |
|---|---|
| `src/extension.ts` | extension host: webview, REST server (Express), settings, commands |
| `game/src/` | the game (ES modules): `game.js` loop and states, `level.js` layers and rules, `character.js` hero and the API facade with statistics, `game-objects.js` objects, `fog.js`, `assets.js` pack lookup, `rendering/` drawing only |
| `game/test/` | Node unit tests for the rules (`npm run test:engine`) |
| `api/openapi.yaml` | the REST API |
| `api/python/dungeoncoder/` | the Python package: `dungeoncoder.py` (`Game`, `Hero`), `sim.py` (simulator), `asciimap.py` (text maps), `generator.py` (mazes), `testing.py` (pytest), `packs/` (text-map styles and tile rules) |
| `packs/demo/` | the CC0 demo pack |
| `tools/` | code generators, the dev server, `make_demo_pack.py`, `make_world_art.py` |
| `tools/levels/` | level tools for anyone building levels (Python; tilesets from `DC_ASSET_PACKS`, then `game/assets`): `level2ascii.py` (a level as a text map), `level2png.py` (a level as a picture, with grid, marks and paths; needs Pillow), `check_level.py` (check a level by the game's rules; with two levels: did only the look change?), `run_sim.py` (run a script in the simulator), `run_headless.py` (run a script against the dev server in headless Chrome; needs Playwright); `npm run test:tools` checks them on the demo pack |

### Adding an API command

1. Add the path to `api/openapi.yaml`, then `npm run generate`.
2. Add a handler in `game/src/script.js` (`HANDLERS`) and the logic in `CharacterInterface` or the engine. Both servers create routes from the spec; only a command that needs special handling after success gets an entry in their `afterSuccess` tables.
3. `npm run generate:python-client`, then a wrapper method with a docstring in `api/python/dungeoncoder/dungeoncoder.py`.
4. **Port the rule to the simulator** (`sim.py`, a `cmd_<operationId>` method) and check that game and simulator answer every call the same way.
5. Add a unit test in `game/test/`, and a CHANGELOG entry.

## Licence

Code: MIT (`LICENSE.txt`). Demo pack: CC0 (`packs/demo/LICENSE.md`). Based on Dungeon Coder 0.1 by Benedikt Dietrich, Munich University of Applied Sciences.
