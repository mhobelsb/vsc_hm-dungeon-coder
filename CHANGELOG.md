# Change Log

All notable changes to the "dungeon-coder" extension will be documented in this file.

Check [Keep a Changelog](http://keepachangelog.com/) for recommendations on how to structure this file.

## [Unreleased]

### Added

- **Port setting**: `dungeonCoder.port` (default 3000) lets a second Dungeon Coder run next to another one. The extension writes the port to `.dungeoncoder-port` in the workspace, and the Python package finds it there (or in `DUNGEONCODER_PORT`). The "port in use" message now says what is probably running and how to switch.
- Both servers (extension and dev server) register their routes from one table generated from `api/openapi.yaml` (`ROUTES` in `game/src/commands.js`) instead of two hand-kept lists.
- **One tile size**: the hero now steps and senses on the level's own grid (`tilewidth`/`tileheight` of the level file) instead of a fixed 16 px (`TILE_SIZE` is gone), in the game and in the simulator. Levels with 16 px cells behave as before; a level with 32 px cells now plays by the same rules (the view is still sized for 30x20 cells of 16 px).
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

### Fixed

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
