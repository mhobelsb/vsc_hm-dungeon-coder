# Change Log

All notable changes to the "dungeon-coder" extension will be documented in this file.

Check [Keep a Changelog](http://keepachangelog.com/) for recommendations on how to structure this file.

## [Unreleased]

### Added

- **Statistics in Python**: `game.get_statistics()` (REST `GET /game/statistics`) returns the level's counters (moves, turns, bumps, keyboard moves, interactions, pickups, drops, sensor calls) plus `at_goal`, `level_complete` and `missing`.
- **Win conditions**: the map property `win` (comma-separated `all_sweets`, `all_switches`) must be met besides reaching the goal. While the hero stands on the goal with conditions unmet, the level keeps running and a banner names what is missing. `is_at_goal()` now means "stands on the goal field".
- **Pattern door**: an object of type `PatternDoor` with the properties `pattern` (e.g. `"101"`) and `torches` (torch object ids in bit order) is open exactly while those torches show the pattern (burning = 1). It can't be opened by hand.
- `src/commands.d.ts` is now generated from `api/openapi.yaml` together with `game/src/commands.js`.
- **Fog of war**: the map property `fog` (`"explored"`, `"dark"` or `"none"`; `true` means `"explored"`) hides what the hero hasn't seen. `explored` keeps fields the hero stood on or sensed visible (dimmed); `dark` shows only the hero's field and fields sensed in the last 1.5 s. Every sensor call (`is_*_in_front()`) and every step light the field in front; burning torches light the fields within 2 cells. In fog levels the keyboard is off unless the level sets `keyboard` explicitly.
- Keyboard moves (WASD) are counted separately and shown on the "Level Complete" screen as "Keyboard moves".
- A level can switch keyboard control off with the bool map property `keyboard: false` (set in Tiled under Map Properties).
- The dev server's HTTP port can be changed with `DC_PORT`, so it can run next to an installed Dungeon Coder extension.

### Fixed

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
