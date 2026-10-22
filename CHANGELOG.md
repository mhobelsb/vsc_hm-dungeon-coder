# Change Log

All notable changes to the "dungeon-coder" extension will be documented in this file.

Check [Keep a Changelog](http://keepachangelog.com/) for recommendations on how to structure this file.

## [Unreleased]

### Added

- **A game box**: the dev server takes a list of rounds (`DC_ROUNDS`, Tiled JSON files separated by the path delimiter). It loads round 1 as soon as the page connects (and the current round again after a reload); on the page, **N** loads the next round and **R** the same again (`POST /referee/round`, this machine only; `GET /referee/round` tells the page which round it shows, for the scoreboard: "Round 2/3"). With `DC_HOST=0.0.0.0` a small computer at the beamer (e.g. a Raspberry Pi with its own WLAN) is the whole live game.

## [1.1.1] - 2026-10-21

A **pre-release** for the course's first live game in week 8 (the Mini-Challenge): a simpler setup in the room. Everything 1.1.0 did is unchanged.

### Added

- **"Dungeon Coder: Open the game to the room (live game)"**: the extension itself opens its game to the room's network and shows the address; no dev server needed. Levels, start and end stay with this computer, a hero belongs to the computer that joined it. The rules live in `game/src/room-access.js`, shared with the dev server.
- **`Game.join` finds the game by itself**: a file `.dungeoncoder-url` in the working folder or above it holds the address (an exercise folder ships it); `DUNGEONCODER_URL` and the `url` argument still win. `Game("level.txt")` is not affected.
- **Teams may name themselves**: `Game.join(code, name="Die Runenjäger")` (at most 24 characters) shows the name on the scoreboard and the name tag.
- **The scoreboard**: who has joined ("Ready: 4 of 6", "not joined"), a bar for the room towards 80 percent, German with the map property `lang: de`.
- **Sounds in a live game**: a blip for every rune picked up, a chord at the start and the end (WebAudio, after the referee's first key; `sound: false` switches them off).
- **An arena loaded by the script itself starts at once** (`Game("arena.txt")`): a training ground at home with the room's rules and scoreboard.
- **`generate: arena`** takes `room: 0` (no hall) and `exits: niches` (an exit on the first field out of every niche).

### Changed

- **The amulet measures the nearest exit** (`sense_goal()`): a level with one exit is as before; a live game may have one exit per team.
- **Guards by the clock leave a hero on an exit alone**, and the simulator steps them once per `heroes * tick / 500 ms` moves, so a guard with `tick: 800` is slower than the heroes, as in the game.

## [1.1.0] - 2026-10-19

A **pre-release** (odd minor, see `RELEASING.md`): the live game in the room for the course's game days in December 2026. Everything 1.0.0 did is unchanged; scripts and levels keep working. VS Code offers it only to those who chose pre-releases.

### Added

- **A live game in the room (the arena).** A level with the map property `arena: true` and the teams' codes in `codes` ("ROT-4711 BLAU-2234 …") is a game for several teams at once, in one game on the referee's computer (the dev server with `DC_HOST=0.0.0.0`, its page on the beamer). Each team's script joins from its own computer with `Game.join("ROT-4711")` (`POST /game/join`; the package reads `DUNGEONCODER_URL`) and waits until the referee starts the game (Space on the page, `POST /game/start`); E ends the round (`POST /game/end`): everything stops and stays on screen. Every hero has its own counters (`GET /game/statistics?hero=N`), its own move budget and its own end: a caught, fallen or collapsed hero lies on the floor and the others play on (`out`, `started` in the statistics). The pace is fixed, the keyboard off. The page shows a name tag in the team's colour above every hero and a scoreboard beside the canvas. With the server open to the room, only the referee's machine loads levels or starts and ends the game, and a hero belongs to the computer that joined it. The simulator plays arenas too (it has no referee: `Game.join` starts the game there). `dungeoncoder.arena` is the referee's side (`load`, `start`, `end`, `statistics`). Levels without `arena` are as before.
- **`hero.is_hero_in_front()`**: whether another hero stands on the field in front (heroes block each other like walls, but a wall never moves).
- **`generate: arena`** (`Game.generate(kind="arena")`; `teams`, `items`, `loops`; default 39 x 23): a maze with a hall in the middle, one start per team on the edge with ways to the hall of the same length (within 7 percent), crystals with values (the dearest in the hall), `max_moves: 300` and `inventory_size: 6` unless the recipe says otherwise. Generated levels may now be up to 99 x 99 (the view follows the level).
- **Text maps**: heroes `2` to `9` (before: `2` to `4`); `start:` takes one direction per hero ("start: east south west").
- **The dev server**: `DC_HOST` (listen on another interface), `DC_WS_PORT` (the page's socket; `index.html` gets it as `${wsPort}`), `DC_TRACE` (every answered command as a JSON line: the record of a live game).
- **Guards by the clock** (map property `tick: 500`, milliseconds): guards step by time instead of once per hero move, a chaser towards the nearest hero; with several heroes (an arena) a guard no longer runs once per hero. Walking into a guard is still being caught. The simulator steps such guards once per round of moves.
- **`hero.is_enemy_in_front(distance=1)`**: with a map property `witterung: N` the hero may look up to N fields ahead in a straight line (a wall ends the view); more is refused. Query parameter `distance`.
- **An erring oracle**: `orakel: 70` (a percentage) makes `ask_oracle()` wrong in the other 30 percent of its answers, reproducibly from the level's `seed` and the question's number, in the game and in the simulator alike. `orakel: true` is unchanged.

### Changed

- **A move waits only for its own hero.** The host polled "is any hero moving?" after a `move`, so with several heroes walking at once (an arena) a step waited for the others (up to 1.3 s instead of 0.5 s). The poll now names the hero (`is_moving` takes `hero`); with one hero nothing changes.
- **The simulator keeps one inventory per hero** (as the game does); before, co-op heroes shared one list.

## [1.0.0] - 2026-10-15

The first regular release of the new engine: it replaces 0.1.0 as the release version that VS Code installs (until now 0.2.x came as pre-releases). Everything since 0.1.0 is in it (sections 0.2.0 to 0.2.4 and below); scripts and levels written for 0.1.0 keep working.

**What changes for users of 0.1.0:**

- **The extension no longer brings the course's pixel art.** It has a free demo pack and four free worlds; levels drawn with other art need their asset pack (a folder with `tilesets/`, `images/`, `pack.json`). It is found without a setting when a folder `dungeon-coder-assets` lies in the opened folder, above it or directly inside it (setting `dungeonCoder.findAssetPacks`), or named in the setting `dungeonCoder.assetPacks`. A level without its pack fails to load with a message that names the missing tilesets (and the pack, if the level names it: map property `pack`).
- **The Python package comes from PyPI**: `pip install dungeoncoder` (same version as the extension). "Dungeon Coder: Copy Python API to workspace" still copies it into the folder, for use without internet access. A copy made by 0.1.0 (a folder `dungeoncoder` in the workspace) is named when the game starts, with an offer to copy the current one.
- An older `dungeoncoder` from PyPI keeps working with this extension. Before 1.0.0 (0.2.0 to 0.2.4) it printed a warning once per program against an extension of another minor version; `pip install --upgrade dungeoncoder` ends it.
- **Back to 0.1.0**, if needed: "Install Specific Version…" on the extension's page (auto-update off for it), or `code --install-extension hm-benidiet.vscode-dungeon-coder@0.1.0`.

**Version numbers from now on**: releases have an even minor version (1.0.x, 1.2.x), pre-releases an odd one (1.1.x); see `RELEASING.md`.

### Added

- **A free default style for text maps**: a map without `style:` and `Game.generate()` without a style used the course's `dungeon` and `maze`, and failed without the course's asset pack ("unknown style"). They now use `dungeon` and `maze` when an asset pack brings them, and otherwise `demo`, the demo pack's plain dungeon (a new style learned from the new demo level `demo_objekte`, which has every object a text map can place; in `demo_raum` the torch now hangs on a wall field, as torches do in text maps). With the course's pack nothing changes.
- **Demo pack 1.2: grille tiles for a vertical wall line** (`VerticalGrille`, closed and open). The game builds an object only if its tileset has a tile for every state of its class; a text map's `G` between two walls above and below (a `VerticalGrille`) failed to load in the demo pack's look. The simulator didn't notice (it needs no pictures); `test_level_tools.py` now checks that the demo pack has a tile for every state of every object class.
- **`npm run package:release` and `npm run publish:release`** for a regular release; `tools/check-vsix.mjs` (replaces `check-prerelease.mjs`) checks a package before either kind of publishing: the pre-release mark (there or not), the ID, the version against `package.json` and against every version on the Marketplace, from 1.0.0 on the even/odd minor convention (releases 1.0.x, 1.2.x; pre-releases 1.1.x), and for a release a CHANGELOG section. `npm run package:vsix` is gone (it built a package without either check). `RELEASING.md` describes both ways and how to go back.

### Changed

- **The version warning only for a package newer than the extension**: `Game()` warned once per program whenever the Python package and the extension differed in major or minor version, also when the package was older, which works (the extension keeps every older command), e.g. an exercise's `.venv` with `dungeoncoder` 0.2.4 against extension 1.0. It now warns only when the package is newer than the extension (commands may be missing); `python -m dungeoncoder` reports an older package as fitting, with a note on how to get the newest commands.
- `check_level.py` with two levels ignores the map property `pack` (which asset pack has the art), like `handmade`: adding it to an older level doesn't count as a change of the rules.
- **Text maps look more like levels drawn by hand** (only the look; a level's rules stay the same):
  - a small free-standing rectangular block of wall (2 to 4 fields, at most 2 x 2, touching no other wall) is drawn as a large obstacle (rubble, a rock) where the style has one of exactly that size, instead of a lone piece of wall; without such a picture it stays a wall (a pillar hall keeps its pillars);
  - with `deko:`, small details gather around obstacles and objects (a chest, a switch, a door) and the open floor stays calm, instead of being spread evenly;
  - a style can learn its **outer rim** separately (recipe field `rim`: levels to learn from): the wall fields next to the outside of the map, e.g. water with a rocky shore around a terrain instead of the hedge of its inner walls. Style packs without a rim draw it as before.

## [0.2.4] - 2026-10-09

### Fixed

- **A briefly busy machine no longer changes a sensor's answer**: sensors, queries (`is_facing_north()`, `get_items_at_position()`, `read_item_value()`, …) and loading a level waited at most 1 s for the game's answer and then returned their default (`False`, `None`, `[]`) with only the message "Timeout error occurred". A program's view of the world could silently go wrong, e.g. a turn too many in `while not hero.is_facing_north(): hero.turn_left()`. They now wait up to 10 s for an answer; connecting still fails at once (1 s) when the game isn't running. Found as an intermittent failure of a model solution in the course's full game run; reproduced by blocking the game page 1.5 s every 3 s.

## [0.2.3] - 2026-10-08

### Added

- **`show_calls` and `show_sensing` from the program**: `Game(level, show_calls=True, show_sensing=False)` sets them for one level, the class variables `Game.SHOW_CALLS` and `Game.SHOW_SENSING` for every level loaded afterwards (also by helper modules and `Game.generate`); a parameter wins over the class variable, which wins over the level's own property; `None` (the default) leaves it to the level. The Python package writes them into the level it sends, so the game and the simulator are unchanged.

## [0.2.2] - 2026-10-08

### Changed

- **The call log is off unless a level switches it on**: the list of the program's last calls in the tab's corner shows only in levels with the map property `show_calls: true` (text maps: the header line `show_calls: true`); every level load decides anew, and key **L** still shows or hides it in any level. Before, it was on in every level.

## [0.2.1] - 2026-10-08

### Added

- **Asset packs are found without a setting**: a folder named `dungeon-coder-assets` (new setting `dungeonCoder.findAssetPacks`, the list of names) with a `pack.json`, in the opened folder, any folder above it, or a folder directly inside it, is used after the packs of `dungeonCoder.assetPacks`. So a course repo works whatever folder of it is opened (the repo, an exercise, a solution, or the folder holding the repo). The Python package searches the same way when `DC_ASSET_PACKS` isn't set (in and above the current folder and the running script's), so the simulator and text maps find the pack in any terminal; an explicitly set `DC_ASSET_PACKS`, also an empty one, still decides. The message about a missing tileset says so (same words in the game and the simulator).


## [0.2.0] - 2026-10-08

The first version of this repository, and the first one on PyPI (`pip install dungeoncoder`). Scripts and levels written for 0.1.0 keep working.

### Added

- **Amulet** (map property `amulett`): `hero.sense_goal()` returns how many fields the exit is away as the crow flies (columns plus rows; walls don't count), so "always get warmer" can get stuck. Without an amulet the call is refused (`None`).
- **Move budget** (map property `max_moves`): every `move()` call costs, also a blocked one; one call too many and the hero collapses (game over, "Out of moves" on the end screen). `get_statistics()["moves_left"]`; the game shows the moves left.
- **Co-op heroes**: further heroes are `Character` objects named `Hero2`, `Hero3`, … (text maps: `2`, `3`, `4`; `hero: 7 13 1` picks their sprites). `game.get_heroes()`; every hero route takes the query parameter `hero`. Heroes block each other like walls; win condition `all_heroes` (every hero on an exit); with several heroes every `Goal` counts. Statistics: `heroes`.
- **Level variants**: objects with the property `region` lie on any free field of the `Region` rectangle it names; `Game("x.json", seed=17)` picks a variant (the same seed, the same variant), map property `variants: random` makes a new one per load (seed printed; `DUNGEONCODER_SEED` fixes it). Text maps: `region: s 2,2 17,13`. Made in Python before loading, so game and simulator get the same level.
- **Fresh levels per load**: `Game.generate()` without a seed picks one and prints it (`game.seed`); a text map whose header says `generate: maze` (with `size`, `loops`, `seed: random`, map properties) is a recipe for a generated level. The end screens show the level's seed.
- **Visible sensing**: the cell a sensor looked at is framed for a moment (green yes, white no), in every level (`show_sensing: false` switches it off); a list of the program's last calls in the tab's corner (key L).
- **Traces**: `game.save_trace(path)` or `DUNGEONCODER_TRACE=path` write every call with its answer and the level; `python -m dungeoncoder replay` plays a trace in the game (and says where it differs), `python -m dungeoncoder trace` lists it with the hero's field after every call, `python -m dungeoncoder variants PROG LEVEL...` runs a program on several levels in the simulator and keeps the traces of failed runs (`--traces DIR`; a program in an endless loop is stopped and still leaves its trace). `python -m dungeoncoder load LEVEL` loads a level into the game.
- **Side panel**: the Explorer view "Dungeon Coder Levels" lists the levels of the workspace (`level/`, `levels/`, `secret/`), a click loads one (starting the game if needed); "Run program on all levels" over a Python file runs it in the simulator; "Replay trace" on a `*.trace.json`; the status bar shows moves, turns, bumps, moves left.

- **Item tiles from the asset packs**: a pack's `pack.json` names the tiles of the items the engine creates itself (`"items"`: `Pebble`, `Crystal`, `Crystal:orange`, each `{"tileset", "tile"}`), the first pack wins. The start inventory (`hero_inventory`) in the game and the simulator, and the crystals `K` and pebbles `o` of text maps, take their tiles from there instead of a fixed tileset. The bundled assets have their own `pack.json`; the Python package a copy (`packs/items.json`), checked equal by a unit test. An item type no pack names isn't given (the game warns).
- **A level names its asset pack** (map property `pack`; text-map styles can set it, so generated levels carry it): when a tileset is missing, game and simulator say which pack to get.
- **Pack manifest**: `pack.json` may give `engine` (the oldest Dungeon Coder that draws the pack correctly), `styles` and `worlds`. At game start the extension warns about a configured pack that needs a newer extension; `python -m dungeoncoder` does the same.
- **ARCHITECTURE.md**: how the engine works inside (from Benedikt Dietrich's notes for 0.1.0, updated).
- **Demo pack 1.1**: grille tiles (closed, open) and an `items` entry for its pebble and crystals, so the demo pack alone plays levels with a start inventory.
- **Style learner**: `tools/levels/learn_styles.py` (`npm run learn:styles`, `--check`) learns text-map style packs from hand-built levels by JSON recipes (`<folder>/learn/<style>.json`: source levels and options, figure sheet, abyss, items, decoration, large props) and writes each pack to the folder above its recipes. `api/python/dungeoncoder/packs/learn/` holds the recipes of the CC0 worlds, so the engine rebuilds its own styles (checked in `npm run test:tools`).
- `Game.generate(..., style=...)`: the text-map style of a generated level (default `maze`).

- **Versions**: `GET /version` returns the versions of the extension and of the API (answered by the server, `x-host` in `api/openapi.yaml`). `Game()` warns once per program if the Python package doesn't fit the running extension (another major/minor version, or an extension without `/version`). When the game starts, the extension warns about an outdated copied `dungeoncoder/` folder in the workspace and offers to copy the matching one. "Copy Python API to workspace" now replaces an existing folder instead of copying over it.
- **Setup check**: `python -m dungeoncoder` prints the Python, the package (copied or installed), where the game is expected and whether it answers and fits, the asset packs, and whether the simulator runs; each line `ok`, `note` or `PROBLEM` with what to do. A missing `httpx` now gives a message that names the Python in use and the fix (select the interpreter, install the packages).
- **Text maps: large props**: a style pack may list large obstacles (`big_props`: a footprint of w x h fields, one tile per footprint field, and parts beyond it: a crown, the devices on a bench). A block of touching `x` that is a rectangle of exactly a prop's size becomes that prop; other blocks are filled with the props marked `fill`, largest first; a single `x` keeps the small props. Every footprint field gets its own wall tile, so the rules are the same as before; the parts beyond the footprint go into as many `Deko` layers as overlap. Decoration only: the simulator is unchanged.
- **Level tools** in `tools/levels/`: `level2ascii.py`, `level2png.py`, `check_level.py`, `run_sim.py`, `run_headless.py` and their shared level model `dclevel.py`, for anyone building levels; tilesets come from `DC_ASSET_PACKS`, then the engine's assets. `npm run test:tools` checks them on the demo pack.
- **The Python package as a wheel**: `api/python/pyproject.toml` builds `dungeoncoder` (with its style packs) at the extension's version (`dungeoncoder.__version__`); `npm run build:wheel`, `npm run check:version`. It installs with pip from the repository too (`#subdirectory=api/python`).
- When the game starts, a folder in `dungeonCoder.assetPacks` that doesn't exist (a course pack that wasn't cloned) is named in a warning.
- **Integration tests in VS Code**: `npm test` opens a fixture exercise folder that names the demo pack in its `.vscode/settings.json` (relative path), starts the game and loads a level of the pack. The test VS Code is kept in `~/.cache/vscode-test` (`npm run test:download`).
- **Mirrored tiles**: the game draws Tiled's flip flags (horizontal, vertical, diagonal) on tile layers and objects; a mirrored tile keeps its rules (wall, abyss, goal). A door that changes state stays mirrored. The simulator ignores the flags, as before, for the rules.
- **Text maps: decoration and size**: `x` an obstacle (a wall for the rules, drawn as furniture, crates, a rock), `,` a path, `"` a small detail, and the header `deko: N` scatters details on N % of the plain floor and walls (seeded, the same map always looks the same). Maps may be larger than 30 x 20; the field grows with the map. The goal is drawn facing the way the hero comes in, where the style has exits for four directions.
- Asset packs can bring their own text-map styles (`styles/<style>.json`), which `Game("karte.txt")` prefers; the extension passes `dungeonCoder.assetPacks` to new terminals as `DC_ASSET_PACKS`.
- **Port setting**: `dungeonCoder.port` (default 3000) lets a second Dungeon Coder run next to another one. The extension writes the port to `.dungeoncoder-port` in the workspace, and the Python package finds it there (or in `DUNGEONCODER_PORT`). The "port in use" message now says what is probably running and how to switch.
- Both servers (extension and dev server) register their routes from one table generated from `api/openapi.yaml` (`ROUTES` in `game/src/commands.js`) instead of two hand-kept lists.
- **The view follows the level**: the game view is as large as the level (`width` x `tilewidth`, `height` x `tileheight`) instead of a fixed 480 x 320. Levels of 30 x 20 cells of 16 px look as before; a smaller level (e.g. 15 x 10 cells) fills the panel with larger cells, a larger one is shown completely. Texts, banners and the title/end pictures scale with the view; the pictures keep their shape and are centred. The canvas carries `data-view-width`/`data-view-height`.
- **Text maps: `view: fit`**: this header line cuts the level to the map and one field around it (instead of the 30 x 20 field), so small maps are shown with larger fields. Also for generated mazes: `Game.generate(seed, view="fit")`.
- **Worlds beside the dungeon**: the same game in other settings. `tools/make_world_art.py` draws four worlds at 32 px per field (CC0, placeholders for better art later): `station` (a hospital ward with a care robot), `studio` (a light studio with a wall of lamps), `werkstatt` (a production hall with a transport robot and people) and `gelaende` (a survey area). Text maps choose them with `style: <world>`; a style can name the figure used for the agents `W` (`guard_sprite`). A world has its own figure sheet, its own item classes and its own end screens.
- **Item classes of an asset pack**: a tile with the bool property `item` makes objects of its class items (they lie on the floor, can carry a `value`, can be picked up), under the class name of the tile, e.g. `Bett` or `Probe`. Before, only `Crystal` and `Pebble` could carry a value. Engine and simulator.
- **End screens per world**: a level with the map property `world` (set by the world's text-map style) shows `images/welt_<world>_geschafft.png` and `images/welt_<world>_halt.png` instead of the dungeon's pictures.
- **`torch_light: false`** (map property): torches that are off don't darken the level, e.g. when they are the pixels of a display.
- Figures (the hero, guards) are drawn after the items, so an item on their field doesn't hide them.
- **Unit tests for the game's rules**: `npm run test:engine` runs `game/test/engine.test.mjs` in Node, without a browser, on the demo pack (collision, abyss, `controls`, goal check, inventory, win conditions, statistics, tile size).
- `npm run lint` now also checks `game/src` and `tools`; all warnings fixed (semicolons, braces, strict comparisons). `api/openapi.yaml`: version 0.1.0, as the extension.
- **Native 32 px tiles**: the demo pack now has every picture twice, with 16 px tiles (`demo_*`) and with 32 px tiles (`demo32_*`, levels of 15 x 10 cells). The game draws them in full size, and the simulator knows their rules (`packs/tilesets.json`).
- Text maps: the builder takes the field size from the style pack (`tile_size`, default 16), so a style with 32 px tiles places its objects on a 32 px grid.
- Demo pack: the titles of the screen pictures sit above the centre, where the game doesn't write.
- **One tile size**: the hero now steps and senses on the level's own grid (`tilewidth`/`tileheight` of the level file) instead of a fixed 16 px (`TILE_SIZE` is gone), in the game and in the simulator. Levels with 16 px cells behave as before; a level with 32 px cells now plays by the same rules.
- **Bigger, sharper game view**: the game now fills the panel with any scale factor (before: whole numbers only, so a 700 px panel showed it at 1×), and it is drawn into a buffer twice as large, so text is crisp.
- **Asset packs**: tilesets, images and screens are looked up in the asset packs named by the setting `dungeonCoder.assetPacks` (or `DC_ASSET_PACKS` for the dev server) before the extension's own assets. A free **demo pack** (`packs/demo`, every picture drawn by `tools/make_demo_pack.py`, CC0) with two demo levels shows the format.
- **Guards and the oracle** (turn-based): objects of type `Guard` with the property `behaviour` = `patrol` (walks in `direction` and turns back at obstacles) or `chase` (steps towards the hero) take one step each time the hero tries `move()` (also a blocked one; turning takes no time). A guard on the hero's field, the hero walking into one, or swapping fields ends the game. `hero.is_enemy_in_front()` senses them. In levels with `orakel: true`, `hero.ask_oracle()` answers the first step of a shortest way to the exit. Statistics: `questions`, and `game_over` (fallen or caught). Text maps: `W` with a `guards:` header line. The simulator does all of it.
- **Simulator**: `dungeoncoder.use_simulator()` (or the environment variable `DUNGEONCODER_SIM=1`) runs any script without VS Code: a pure-Python port of the game's rules (`dungeoncoder/sim.py`). Same classes, same return values, no picture, no waiting. `DUNGEONCODER_LEVEL=<file>` makes every level load play that file instead (for grading). `dungeoncoder.testing.spiel(map_text)` gives `(game, hero)` for pytest. Tile rules come from `dungeoncoder/packs/tilesets.json`.
- **Items with values**: objects of type `Crystal` (and `Pebble`) can carry an integer property `value`, e.g. a crystal's weight. It is never drawn; `hero.read_item_value()` returns the value on the hero's field (or `None`). In levels with the bool map property `fernrohr`, `hero.peek_item_value(k)` reads the value k fields ahead without walking. Both count as `reads` in the statistics.
- **Inventory size**: the map property `inventory_size` limits how many items the hero can carry; `pickup()` then refuses with a message.
- **Win conditions `sorted` and `stable`**: the fields where valued items lie at the start are slots (reading order). `sorted`: one item per slot, values rising; `stable`: also equal values in their start order.
- **Start inventory**: the map property `hero_inventory` (e.g. `"Pebble*20"`) puts items into the hero's inventory at the start, e.g. breadcrumbs.
- **Generated mazes**: `Game.generate(seed, kind="maze"|"rooms"|"pillars", width=15, height=11, loops=0, **map_properties)` (rooms joined by doorways and open halls with pillars have their exit inside, away from the outer wall) loads a maze built by a seeded randomised depth-first search; the same seed always gives the same maze. `loops` adds cycles and free-standing walls. New map style `maze` (from `maze.json`). In text maps: `K` crystal (`values:`, `colors:` headers), `o` pebble.
- **Levels from ASCII maps**: `Game("karte.txt")` builds the level from a text map (`#` wall, `.` floor, `~` abyss, `H` hero, `Z` goal, `*` sweets, `s` switch, `D` door, `T`/`t` torch, ...) with an optional header (`start`, `hero`, `style`, `controls`, `pattern`, and any map property such as `fog: dark`). The tiles come from style packs (`dungeoncoder/packs/*.json`: `dungeon`, `corridor`, `arena`, `bridge`) learned from the levels that ship with the game, so no tileset is needed on the Python side. Mistakes in a map give a message with the position, e.g. `unknown symbol 'X' at (3,1)`.
- **Statistics in Python**: `game.get_statistics()` (REST `GET /game/statistics`) returns the level's counters (moves, turns, bumps, keyboard moves, interactions, pickups, drops, sensor calls) plus `at_goal`, `level_complete` and `missing`.
- **Win conditions**: the map property `win` (comma-separated `all_sweets`, `all_switches`) must be met besides reaching the goal. While the hero stands on the goal with conditions unmet, the level keeps running and a banner names what is missing. `is_at_goal()` now means "stands on the goal field".
- **Pattern door**: an object of type `PatternDoor` with the properties `pattern` (e.g. `"101"`) and `torches` (torch object ids in bit order) is open exactly while those torches show the pattern (burning = 1). It can't be opened by hand.
- `src/commands.d.ts` is now generated from `api/openapi.yaml` together with `game/src/commands.js`.
- **Fog of war**: the map property `fog` (`"explored"`, `"dark"` or `"none"`; `true` means `"explored"`) hides what the hero hasn't seen. `explored` keeps fields the hero stood on or sensed visible (dimmed); `dark` shows only the hero's field and fields sensed in the last 1.5 s. Every sensor call (`is_*_in_front()`) and every step light the field in front; burning torches light the fields within 2 cells. In fog levels the keyboard is off unless the level sets `keyboard` explicitly.
- Keyboard moves (WASD) are counted separately and shown on the "Level Complete" screen as "Keyboard moves".
- A level can switch keyboard control off with the bool map property `keyboard: false` (set in Tiled under Map Properties).
- The dev server's HTTP port can be changed with `DC_PORT`, so it can run next to an installed Dungeon Coder extension.

### Changed

- **The bundled assets are free**: `game/assets/` now holds the demo pack (copied by `tools/make_demo_pack.py`: its tilesets, the end screens), the four CC0 worlds and the title image. The bought pixel art of the HM course (the dungeon, Halloween and fire tilesets, the figure sheet, the icon sheet) left the extension and comes from the course's own asset pack (setting `dungeonCoder.assetPacks`). Pebbles and crystals of a start inventory take the demo pack's tiles unless a configured pack names others. Text-map style recipes must now name their figure sheet (`hero`) and abyss tileset (`abyss`); the style learner had course tilesets as defaults.
- **Published as a pre-release of the existing extension** `hm-benidiet.vscode-dungeon-coder` ("Dungeon Coder", same ID and commands as 0.1.0): `vsce publish --pre-release`; who wants it chooses "Switch to Pre-Release Version" in VS Code, everyone else keeps 0.1.0, and "Switch to Release Version" goes back. Repository, issues and homepage: https://github.com/mhobelsb/vsc_hm-dungeon-coder; contact martin.hobelsberger@hm.edu.

- The level tools' shared model (`tools/levels/dclevel.py`) asks the simulator for walls and abysses (`Level.wall_tile_at`, `Level.abyss_tile_at`, split out of `is_collision` and `abyss_at` without a change in behaviour), so the rules exist once; its learning views stay its own.
- The Python package ships only the CC0 worlds' styles and the tile rules of the free tilesets (demo pack, CC0 worlds); the course styles (`dungeon`, `corridor`, `arena`, `bridge`, `maze`) and their rules come with the course's asset pack. An unknown style's message names the available ones and the asset-pack setting. The setup check (`python -m dungeoncoder`) plays its small map in a bundled style.
- The 11 course levels are no longer bundled (`game/assets/levels/` keeps the four show levels of the CC0 worlds); they live in the private course assets.

### Fixed

- A level that names a tileset no asset pack has (for example a course level while `dungeonCoder.assetPacks` is not set) was reported as loaded and showed a broken level; the simulator even played it without walls. The game and the simulator now refuse it, `Game()` prints which tileset is missing and which setting to change, and the previous level stays loaded.
- A level without a hero (`MainCharacter`) stopped the game loop for good; every level loaded afterwards stayed frozen.
- With asset packs, a screen picture drawn while it was still being looked up in the packs stopped the game loop for good (black canvas).
- A floor drawn over an abyss background counted as abyss: walking through e.g. `playground.json`'s door made the hero fall, and `is_abyss_in_front()` was `True` in front of most walls. Now only an Abyss tile with nothing drawn over it is an abyss.
- While the hero was falling into an abyss (the 3 s before "Game over"), actions were still accepted; a `move()` could start a step that never finished. Actions are now refused from the moment the hero falls.
- `pickup()` and `drop()` returned `False` even when they succeeded.
- `interact()` always returned `False`. It now returns `True` if an object reacted, and `False` if there is nothing to interact with, or nothing changed (e.g. a jug that is already broken).
- `configure()` returned `1` instead of `True`, and rejected hero type `0` although 0–15 are documented.
- Loading a level was always reported as failed to the Python client (`Game.loadLevel()` returned nothing).
- The last `move()` onto the goal could time out and return `False` at some pace values: the goal check compared positions while the hero was still mid-step (floating-point rounding), so the game froze the hero in its walking state.
- A `move()` whose step never finished was polled forever by the extension host and the dev server. The poll now gives up after the step time plus 5 s, or on an error, and returns an error. The dev server also fails pending requests when the browser tab closes.
- `move()` and `turn_left()` timed out in the Python client below pace ~0.5. Their timeout now follows the pace.
- After a script changed the pace, the next loaded level kept the old turn delay on the host side while the hero itself was back at normal pace.
- `set_pace()` accepted 0 or negative values, which froze the hero.
- Actions (`move`, `turn_left`, `interact`, `pickup`, `drop`) after the level had ended (goal reached, game over, or no level loaded) started but never finished. They now fail at once with "The level is over".
- A turn was counted in the statistics even when it was refused.
- A missing level file raised `FileExistsError` and was hidden behind a generic message. `Game()` now names the file and the current folder, reports invalid JSON separately, and says when Dungeon Coder isn't running.
- Docstring errors in `is_torch_in_front()` and `is_abyss_in_front()`.

## [0.1.0] - 2026-09-02

### Added

- The REST API is now described by an OpenAPI specification (`api/openapi.yaml`), which is the single source of truth for the extension's Express routes, the webview's command dispatcher, the standalone dev server, and the generated Python client. Every incoming request is validated against it.
- `Game.Level.reset()` (and its `/level/reset` endpoint) now actually works - it was previously missing on the extension side and always failed silently.
- A standalone dev server (`npm run dev:browser`) for running and testing the game in a plain browser tab, without launching the full VS Code Extension Development Host.
- A `debugDraw` flag on `Character` that renders a bounding box, anchor point, and facing-tile marker for debugging positioning/collision issues.
- Distinct "Game Over" and "Level Complete" screens, each with its own background image.

### Changed

- The `dungeoncoder` Python package is now generated from the OpenAPI spec and wrapped by a small hand-written, student-facing API; it now depends on `httpx`/`attrs` instead of `requests`.
- The game engine was split out of a single ~2000-line file into focused modules (tiles, layers, game objects, character, level, input), and rendering was separated from game logic into a dedicated `rendering/` layer with no `draw()` methods left on any model class.
- "Game Over" and "Level Complete" now have their own game states instead of sharing one, so the renderer never needs the hero object just to tell them apart.

### Fixed

- The `configure()` API call could silently return the wrong result due to a missing `break` in the webview's command handling.
- Several instances of dead/unreachable code removed (an always-false animation branch, a disabled debug-drawing block, a stray commented-out command).

### Removed

- The duplicate `startGame_old` command; use "Dungeon Coder: Enter the dungeon" instead.

## [0.0.1] - 2025-10-17

- Initial release
