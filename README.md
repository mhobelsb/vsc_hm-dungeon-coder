# VS Code Dungeon Coder

This VS Code extension provides a gamified environment where students write simple algorithms to control a hero and navigate a challenging dungeon.

*Note: This is still under development.*

![](game/assets/images/dungeon_coder.png)

## Prerequisites

- [Node.js](https://nodejs.org/) 18+ and npm
- [Visual Studio Code](https://code.visualstudio.com/) 1.102+
- Python 3

## Install

```bash
npm install
```

The bundled `dungeoncoder` Python package (the one copied into a student's workspace by the "Copy Python API to workspace" command) already ships pre-generated, so no Python setup is needed just to work on the extension.

## Build

```bash
npm run compile   # development build -> dist/extension.js
npm run watch     # development build, rebuilds on every change
npm run package   # production build (minified), used when packaging the extension
```

All three first run `npm run generate`, which derives several files from `api/openapi.yaml` - the single source of truth for the REST API:

- `game/src/commands.js` - the RPC command registry shared by the extension host, the webview, and the standalone dev server
- `src/generated/api-types.d.ts` - TypeScript types for the Express API
- `game/src/api-config.js` - the API host/port

These are regenerated automatically on every build; you never need to run `npm run generate` by hand.

Type-check and lint separately with:

```bash
npm run compile-tests   # tsc, no emit beyond out/
npm run lint             # eslint src
```

## Run & Debug

Press **F5** in VS Code (or Run → Start Debugging). This runs the default build task (`npm: watch`) and opens a new **Extension Development Host** window with the extension loaded.

In that new window:

1. Open the Command Palette (`Cmd/Ctrl+Shift+P`).
2. Run **"Dungeon Coder: Enter the dungeon"** - opens the game webview and starts the REST API on `http://127.0.0.1:3000`.
3. Run **"Dungeon Coder: Copy Python API to workspace"** to drop the `dungeoncoder` package into your open folder, then write a Python script that imports it to drive the hero.

Breakpoints in `src/extension.ts` are hit in the Extension Development Host, and the Debug Console shows its `console.log` output. To inspect the webview itself (the game canvas), use the Command Palette's "Developer: Open Webview Developer Tools" while the game panel is open.

### Faster iteration loop

Relaunching the Extension Development Host on every change is slow. To iterate on the game engine or the API without VS Code in the loop:

```bash
npm run dev:browser
```

Then open `http://127.0.0.1:3000/index.html` in a regular browser tab. If an installed Dungeon Coder extension already holds port 3000, start it with `DC_PORT=3100 npm run dev:browser` instead and set `Game.BASE_URL = "http://127.0.0.1:3100"` in the Python script. This serves the same REST API and game page as the real extension, and can be driven by any Python script pointed at `http://127.0.0.1:3000`.

## Tests

```bash
npm test
```

Runs the VS Code extension test suite via `@vscode/test-cli`.

## Regenerating the Python API client (advanced)

`api/python/dungeoncoder/_generated/` is a committed, pre-generated client (from `api/openapi.yaml`) that ships with the extension so students never need a codegen toolchain themselves. If you change `api/openapi.yaml`, regenerate it with:

```bash
npm run generate:python-client
```

This needs Python 3 - it creates its own virtual environment at `.codegen-venv/` and installs `openapi-python-client` into it, nothing is installed system-wide.
