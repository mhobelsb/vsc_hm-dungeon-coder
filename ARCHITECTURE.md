# Architecture

How Dungeon Coder works inside, for anyone changing the engine. Based on Benedikt Dietrich's architecture
notes for version 0.1.0 (2026-09-22), brought up to date for the current code (2026-10-06). If something
here no longer matches the code, fix this file in the same change.

## 1. Three parts, two channels

```
Student's Python script (their own workspace)
        │  HTTP, JSON                       the dungeoncoder package (api/python)
        ▼
Express REST API  (src/extension.ts, inside the VS Code extension host, 127.0.0.1:3000,
        │          every request validated against api/openapi.yaml)
        │  postMessage, JSON-RPC 2.0 envelope
        ▼
Webview: game/index.html + game/src/*.js
  - holds the whole game state (Game, Level, Character, objects)
  - draws on a <canvas> in a fixed-step loop
```

**The webview is the only place with game state.** The extension host relays: an HTTP request comes in, a
JSON-RPC message goes to the webview, the webview's answer goes back as the HTTP response. Every route
therefore looks the same; the routes are generated from the API description (section 2).

`move` answers only when the step has finished: the host polls the internal command `is_moving` every
10 ms (with a time limit). `turn_left` waits a fixed 200 ms / pace.

## 2. One source of truth: `api/openapi.yaml`

Read it before changing anything API-shaped. `npm run generate` (part of `compile`, `watch` and `package`)
derives from it:

| Generated | By | Used by |
|---|---|---|
| `game/src/commands.js` (`COMMANDS`, `COMMAND_LIST`, `ROUTES`) | `tools/generate-commands.mjs` | the webview's `HANDLERS`, the extension host and the dev server (both register a route for every `ROUTES` entry) |
| `src/generated/api-types.d.ts` | `openapi-typescript` | typed request bodies in `src/extension.ts` |
| `game/src/api-config.js` | `tools/generate-api-config.mjs` | host, port: extension, webview, dev server |
| `api/python/dungeoncoder/_api_config.py` | `tools/generate-api-config.mjs` | the Python package's default port |

The low-level Python client `api/python/dungeoncoder/_generated/` is **committed** (students need no code
generator); regenerate it with `npm run generate:python-client` when the shapes change. The student-facing
layer is the hand-written `api/python/dungeoncoder/dungeoncoder.py`.

Commands without an HTTP route (`is_moving`) are listed under `x-internal-commands` in the spec.

## 3. Directory map

```
src/extension.ts            the extension: commands, the Express server, the webview, settings
                            (port, asset packs), version checks; src/test/ the VS Code tests
api/openapi.yaml            the REST API (section 2)
api/python/dungeoncoder/
    dungeoncoder.py         Game, Hero, Level for students (hand-written)
    _generated/             the generated HTTP client (committed)
    sim.py                  the simulator: the game's rules in Python (section 6)
    asciimap.py             text maps -> Tiled levels (Game("karte.txt"))
    generator.py            seeded mazes, rooms, pillar halls (Game.generate)
    testing.py              pytest helpers (spiel, wachen)
    __main__.py             python -m dungeoncoder: the setup check
    packs/                  the CC0 worlds' text-map styles, tile rules of the free tilesets,
                            items.json; learn/: the styles' recipes (not shipped)
game/index.html             the page of the webview and the dev server
game/src/
    script.js               entry: transport (postMessage or WebSocket), the RPC HANDLERS
    game.js                 the loop, the game states, loading a level, the view size
    game-state.js           WAITING_FOR_LEVEL, PLAYING, LEVEL_COMPLETE, GAME_OVER
    level.js                a Tiled level: layers, objects, collision, abyss, brightness,
                            goal and win conditions, start inventory, guards, oracle
    layers.js               TileLayer, ObjectLayer
    tiles.js                Tile, Tileset, TileFactory, AnimatedTile; flip flags; missing tilesets
    assets.js               the asset-pack lookup and the packs' item tiles (section 5)
    game-objects.js         the object classes (section 4.3)
    game-object-factory.js  object class -> JS class
    character.js            Character (the hero) and CharacterInterface (what the HANDLERS call)
    fog.js, statistics.js, input.js   fog of war, the counters, keyboard play
    sensing.js, call-log.js visible sensing marks, the list of the last calls (HTML, key L)
    rendering/              drawing only (section 4.5)
game/assets/                the bundled assets, all free: the demo pack's tilesets and screens (copied by
                            make_demo_pack.py), the four CC0 worlds, the title image; levels/ (the
                            worlds' show levels), pack.json
game/test/                  unit tests of the rules in Node (npm run test:engine)
packs/demo/                 the CC0 demo pack (tools/make_demo_pack.py)
tools/                      code generators, dev-server.mjs, make_demo_pack.py, make_world_art.py,
                            levels/ (level tools, the style learner; npm run test:tools)
test-fixtures/              a workspace for the VS Code tests
```

## 4. Core concepts

### 4.1 Levels are Tiled maps

A level is a [Tiled](https://www.mapeditor.org/) map saved as JSON. Students load it with `Game(file)`: the
Python package reads the file locally and sends its content (`POST /level/load`); `POST /level/reset` reloads
the last content (the webview keeps it). Text maps (`.txt`) are turned into a Tiled level in Python first.

- **Tile layers** draw the floor, walls and decoration. A layer with the bool property `collision` makes every
  tile on it a wall (except local id 0 of a tileset). A field whose **topmost** tile has the class `Abyss`
  is an abyss: walking onto it means falling, then Game Over.
- **One object layer** holds the hero (the object named `MainCharacter`), the `Goal` and the objects. An
  object's class is its own `type`/`class`, else the class of its tile. A co-op level has further heroes,
  `Character` objects named `Hero2`, `Hero3`, … (`Level.heroes`; every hero route takes the query parameter
  `hero`, the index). With one hero only the first `Goal` counts; with several, every `Goal`.
  `Region` rectangles describe level variants; the Python client moves the objects whose property `region`
  names one and removes the rectangles (`dungeoncoder/variants.py`), the engine ignores any left over.
- **Map properties** switch on the mechanics: `fog`, `keyboard`, `win`, `inventory_size`, `hero_inventory`,
  `fernrohr`, `orakel`, `amulett`, `max_moves`, `show_sensing`, `torch_light`, `world` (end screens of a world),
  `pack` (the asset pack the art comes from, named in the "missing tileset" message), `seed` (a generated
  level or a variant: shown on the end screens), `variants: random` (a new variant per load).

### 4.2 Coordinates

Positions are in **pixels**. The tile size is the level's own (`tilewidth`, `tileheight`; 16 px in the dungeon,
32 px in the worlds), handed to the hero with `setTileSize`. A grid check converts with
`Math.floor(x / tileWidth)`. The hero moves one field at a time, interpolated over `moveDuration` ms.
Tile objects are anchored bottom-left: cell = (x / tilewidth, (y - 1) / tileheight). An object counts as
standing on every field its picture covers.

### 4.3 Object classes (`game-objects.js`)

```
GameObject                   tile per state, collision, interact()
├── TwoStateGameObject       toggles between its two states; may pass interact() on to the object
│   │                        its `controls` property names (by object id)
│   ├── Torch                burning/off, passes on
│   ├── TwoWaySwitch         left/right, passes on
│   ├── OpenableGameObject   open/closed, does not pass on
│   │   ├── Door
│   │   │   ├── VerticalDoor, Grille, VerticalGrille
│   │   │   └── PatternDoor  open exactly while its torches show a bit pattern
│   │   └── Chest
│   └── Jug                  unbroken/broken (can't be mended)
├── Item                     lies on the floor, can be picked up, may carry a `value`
├── Guard                    moves one step per hero step (patrol or chase)
└── Goal                     interact() does nothing: completion is a position check
Character                    the hero (character.js), also a GameObject
```

`CharacterInterface` is the façade the RPC `HANDLERS` call: it keeps the statistics and refuses actions once
the level is over or the hero is falling.

### 4.4 Game loop and states (`game.js`)

A fixed-step loop (60 per second) over `requestAnimationFrame`:

```
WAITING_FOR_LEVEL --loadLevel()--> PLAYING
PLAYING --a hero dead / caught / out of moves--> GAME_OVER
PLAYING --level complete--> LEVEL_COMPLETE
GAME_OVER / LEVEL_COMPLETE --after the end screen--> WAITING_FOR_LEVEL
```

Transitions happen in `Game.gameLoop()`; which screen to draw is decided only in the renderer.

### 4.5 Rendering (`game/src/rendering/`)

Drawing only, no game logic; the model classes have no `draw()` methods. `create-renderer.js` builds the
renderer graph; `game-renderer.js` picks the screen by the game state; `hud-renderer.js` draws the title, end
screens, texts, the move budget and the darkness overlay; `fog-renderer.js` the fog; `sensing-renderer.js` a
frame around each cell a sensor just looked at. The list of the last calls is HTML next to the canvas
(`call-log.js`, fed by `process_message` in `script.js`). New visuals go into a renderer, not into a model
class.

### 4.6 The message envelope

Both transports (VS Code's `postMessage`, the dev server's WebSocket) carry the same JSON-RPC 2.0 shaped
envelope:

```jsonc
// request                                  // answer
{ "jsonrpc": "2.0", "id": "...",            { "jsonrpc": "2.0", "id": "...",
  "method": "move", "params": {} }            "result": { "success": true, "message": "...", "result": true } }
                                            // transport error only
                                            { "jsonrpc": "2.0", "id": "...", "error": { "message": "..." } }
```

Keep the two levels apart: the outer `error` is a transport failure (no webview, unknown method); the inner
`success: false` is an ordinary negative outcome (a wall ahead, no such item). The host maps the inner answer
to the HTTP response: for historical reasons an ordinary "no" is **HTTP 500**, which the Python layer turns
into the method's default value (`False`, `[]`). Changing that would change every student-facing method, so
it waits for an API version 2.

## 5. Asset packs

The engine loads every tileset, its image and the screens from an ordered list of packs: the folders of the
setting `dungeonCoder.assetPacks` (dev server: `DC_ASSET_PACKS`), then the bundled `game/assets/`, which
holds only free pictures (the demo pack and the CC0 worlds); a course brings its own art as a pack. A pack is a
folder with `tilesets/`, `images/`, optionally `styles/` (text-map styles) and a `pack.json`:

```json
{
 "name": "my-pack", "version": "1.0",
 "engine": "0.1.0",
 "styles": ["dungeon"], "worlds": [],
 "items": {"Pebble": {"tileset": "x.json", "tile": 20}, "Crystal": {"tileset": "x.json", "tile": 18}}
}
```

- `engine`: the oldest Dungeon Coder that draws the pack correctly. At game start the extension warns if a
  configured pack needs a newer one (`packsNeedingNewerEngine`); so does `python -m dungeoncoder`.
- `styles`, `worlds`: the text-map styles the pack brings, and which of them are worlds (informational).
- `items`: the tiles of the items the engine creates itself (start inventory) and the text-map builder places
  (`K` crystal, `o` pebble); the first pack that names an item wins.

A level whose tileset no pack has is refused with a message naming the tileset; if the level names its pack
(map property `pack`), the message names the pack too. Game and simulator use the same wording.

## 6. The simulator

`api/python/dungeoncoder/sim.py` is the game's rules in Python, for running scripts without VS Code or a
browser: grading, pytest, experiments on many levels. It replaces only the transport: `_call` in
`dungeoncoder.py` asks the simulator for the answer the host would send, so every message and return value
takes the same code path. Switch it on with `dungeoncoder.use_simulator()` or `DUNGEONCODER_SIM=1`.
**Every rule change in the engine goes into the simulator too**, and the conformance suite (in the course
workspace) runs the same scripts in both and compares every call.

Things that are decided in Python, before a level reaches either, need no simulator twin: generated levels
(`generator.py`, also as a text map with the header `generate:`), variants (`variants.py`) and traces
(`trace.py`: `_call` records every call; `replay.py` plays a trace again, in the game or in the simulator).

## 7. Two ways to run

1. **The extension** (F5, "Run Extension"): an Extension Development Host window; run "Dungeon Coder: Enter
   the dungeon" there. Changes to the host need a restart; changes to `game/` a reload of the game tab.
2. **The dev server** (`npm run dev:browser`, `tools/dev-server.mjs`): the same REST API and `game/` in a
   normal browser tab at `http://127.0.0.1:3000/index.html`, the webview channel replaced by a WebSocket
   (`ws://127.0.0.1:8000/ws/game`). Unchanged Python scripts work against it. `DC_PORT` moves the HTTP port.
   The fast loop for engine and API work.

After touching `src/extension.ts`, `tools/dev-server.mjs`, `game/src/script.js` or `api/openapi.yaml`, try
both.

## 8. Tests

| Command | What |
|---|---|
| `npm run test:engine` | the rules in Node, no browser, demo pack only (`game/test/`) |
| `npm run test:tools` | the level tools and the style learner on the demo pack |
| `npm test` | VS Code tests: a fixture workspace with the demo pack, loading levels over REST, versions, the side panel |
| `npm run lint` | `src/`, `game/src/`, `tools/` |
| `npm run check:version` | `package.json`, `openapi.yaml` and the Python package agree |

## 9. Adding an API command

1. `api/openapi.yaml`: path, `operationId`, schemas; `npm run generate`.
2. `game/src/script.js`: a `HANDLERS[COMMANDS.X]` entry; the logic in `CharacterInterface` / `Level`.
3. Nothing to register by hand: both servers create a route for every `ROUTES` entry. Only a command that
   needs special handling after success (waiting for a step, remembering the pace) gets an entry in each
   server's `afterSuccess` / `AFTER_SUCCESS` table.
4. `npm run generate:python-client`, then a method with a docstring in `dungeoncoder.py` (the `_call(...,
   default=...)` pattern).
5. The same command in the simulator (`sim.py`: a `cmd_<operationId>` method, counters, refusals).
6. Tests, CHANGELOG.

## 10. Deliberate quirks

Not bugs to fix unasked:

- **HTTP 500 for an ordinary "no"** (section 4.6).
- **No `turn_right()` and no absolute position**: building `turn()` and keeping track of the own position are
  learning goals of the course.
- **Picked-up items are hidden, not removed**: `pickup()` moves the object off-screen (`x = -100`,
  `visible = false`) and keeps it in the object list.
- **`Goal.interact()` does nothing**: the level is complete when the hero stands on the goal's field and the
  `win` conditions hold.
- **Keyboard moves are always counted**; a level can switch the keyboard off (`keyboard: false`).

## 11. Where do I change …

| I want to … | Start here |
|---|---|
| add a Python method for students | `api/openapi.yaml`, then section 9 |
| change what happens when the hero moves, dies, wins | `character.js`, `level.js`, `game.js` (and `sim.py`) |
| add an object type (lever, key, …) | `game-objects.js`, register it in `game-object-factory.js` (and `sim.py`) |
| change how something is drawn | `game/src/rendering/*.js`, wired in `create-renderer.js` |
| author a level | Tiled (JSON), or a text map |
| change the webview's HTML or CSP | `game/index.html`, `getWebviewContent()` in `src/extension.ts` |
| change commands or settings of the extension | `src/extension.ts`, `package.json` (`contributes`) |
| change the Python package students get | `api/python/dungeoncoder/dungeoncoder.py` (never `_generated/` by hand) |

## 12. Working conventions

- One concern per change; small, reviewable steps.
- Add, don't break: scripts written for earlier versions must keep working.
- Every user-visible change goes into `CHANGELOG.md` (Keep a Changelog).
- Regenerate (`npm run generate`) before testing an API change: stale generated files cause confusing errors.
