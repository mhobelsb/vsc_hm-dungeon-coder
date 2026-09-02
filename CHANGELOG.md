# Change Log

All notable changes to the "dungeon-coder" extension will be documented in this file.

Check [Keep a Changelog](http://keepachangelog.com/) for recommendations on how to structure this file.

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
