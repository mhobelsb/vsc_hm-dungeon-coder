# Change Log

All notable changes to the "dungeon-coder" extension will be documented in this file.

Check [Keep a Changelog](http://keepachangelog.com/) for recommendations on how to structure this file.

## [Unreleased]

### Added

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
