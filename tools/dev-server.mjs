import { appendFileSync, readFileSync } from 'fs';
// Standalone counterpart to DungeonCoderServer (src/extension.ts) for running
// and testing the game in a plain browser, without VS Code. Serves the same
// REST API on the same port so an unmodified `dungeoncoder` Python client
// works against it, and serves game/ as static files so the page can be
// opened directly. Commands are relayed to the browser over a WebSocket
// (game/src/script.js's non-VS-Code branch) instead of postMessage, using
// the same JSON-RPC 2.0 style envelope described in game/src/commands.js.
//
// Run with: npm run dev:browser
// Then open: http://127.0.0.1:3000/index.html

import path from 'path';
import { fileURLToPath } from 'url';
import express from 'express';
import { WebSocketServer } from 'ws';
import * as OpenApiValidator from 'express-openapi-validator';
import { COMMANDS, COMMAND_LIST, ROUTES } from '../game/src/commands.js';
import { API_HOST, API_PORT } from '../game/src/api-config.js';
import { RoomAccess } from '../game/src/room-access.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
// DC_HOST opens the server to other computers (a live game in the room: DC_HOST=0.0.0.0, the
// page on this machine's beamer, the teams' scripts on their laptops). Then only this machine
// loads levels and runs the game (loopback), and every hero belongs to the computer that joined it.
const HOST = process.env.DC_HOST || API_HOST;
const EXPOSED = !['127.0.0.1', 'localhost', '::1'].includes(HOST);
// DC_PORT lets the dev server run next to an installed Dungeon Coder
// extension, which already occupies API_PORT while its game tab is open.
// Python clients then need Game.BASE_URL pointed at the same port.
const HTTP_PORT = Number(process.env.DC_PORT ?? API_PORT);
// DC_WS_PORT: the page's socket to this server (index.html gets it as ${wsPort})
const WS_PORT = Number(process.env.DC_WS_PORT ?? 8000);
const TURN_DELAY_MS = 200;
// Same move() step bound as src/extension.ts: animation 500 ms / pace plus slack.
const MOVE_DURATION_MS = 500;
const MOVE_TIMEOUT_BASE_MS = 5000;

let currentPaceFactor = 1.0;
let activeSocket = null;
const pendingRequests = new Map();

function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/** Send a JSON-RPC request to the connected browser client and await its reply. */
function sendToClient(method, params = null) {
    if (!activeSocket) {
        return Promise.resolve({ success: false, message: 'No browser client connected. Open the game page first.', exception: 'NoClient' });
    }

    const id = Date.now().toString() + Math.random().toString(36).slice(2, 9);
    return new Promise(resolve => {
        pendingRequests.set(id, resolve);
        activeSocket.send(JSON.stringify({ jsonrpc: '2.0', id, method, params }));
    });
}

const wss = new WebSocketServer({ port: WS_PORT, path: '/ws/game' });
wss.on('connection', socket => {
    console.log('Browser client connected.');
    activeSocket = socket;
    if (ROUNDS.length > 0) {
        // a game box: the (re)connected page gets the current round, or round 1
        setTimeout(() => loadRound(Math.max(0, currentRound)), 300);
    }

    socket.on('message', raw => {
        const message = JSON.parse(raw.toString());
        const resolver = pendingRequests.get(message.id);
        if (!resolver) {
            return;
        }
        pendingRequests.delete(message.id);

        if (message.error) {
            resolver({ success: false, message: message.error.message, exception: 'RpcError' });
        } else {
            resolver(message.result);
        }
    });

    socket.on('close', () => {
        console.log('Browser client disconnected.');
        if (activeSocket === socket) {
            activeSocket = null;
            // Fail everything still waiting for this page, so no request (and
            // no move poll) outlives the session it belongs to.
            for (const resolver of pendingRequests.values()) {
                resolver({ success: false, message: 'Browser client disconnected.', exception: 'NoClient' });
            }
            pendingRequests.clear();
        }
    });
});

/** Polls until the hero has finished its step; returns an error response on failure or timeout. */
async function pollUntilStopped(pollInterval = 10, hero = undefined) {
    const deadline = Date.now() + MOVE_TIMEOUT_BASE_MS + MOVE_DURATION_MS / currentPaceFactor;
    // co-op levels: ask about the hero that moved (query parameter hero), not about any hero
    const params = hero !== undefined && hero !== '' ? { hero: Number(hero) } : null;
    while (Date.now() < deadline) {
        const isMovingResponse = await sendToClient(COMMANDS.IS_MOVING, params);
        if (!isMovingResponse.success) {
            return isMovingResponse;
        }
        if (!isMovingResponse.result) {
            return undefined;
        }
        await delay(pollInterval);
    }
    return { success: false, message: 'The hero did not finish its step in time.', exception: 'MoveTimeout' };
}

// DC_TRACE: every command the game answered, one JSON line each (time, hero, method, params,
// outcome): the record of a live game, for a replay or the "move of the day"
const TRACE_FILE = process.env.DC_TRACE || '';
function traceLine(command, params, response) {
    if (!TRACE_FILE || command === COMMANDS.IS_MOVING) {
        return;
    }
    const line = { t: Date.now(), hero: params?.hero ?? 0, method: command, params: params && command !== COMMANDS.LOAD_LEVEL ? params : null,
        ok: Boolean(response?.success), result: command === COMMANDS.LOAD_LEVEL ? null : (response?.result ?? null) };
    appendFileSync(TRACE_FILE, JSON.stringify(line) + '\n');
}

// DC_ROUNDS: the rounds of a live game, Tiled JSON files separated by the path delimiter (a game box
// in the room, e.g. a Raspberry Pi at the beamer). The page gets round 1 as soon as it connects; on the
// page, N loads the next round and R the same again (POST /referee/round, this machine only).
const ROUNDS = (process.env.DC_ROUNDS || '').split(path.delimiter).filter(p => p);
let currentRound = -1;

async function loadRound(index) {
    if (index < 0 || index >= ROUNDS.length) {
        return { ok: false, round: currentRound + 1, of: ROUNDS.length, message: 'There is no such round.' };
    }
    let level;
    try {
        level = JSON.parse(readFileSync(ROUNDS[index], 'utf8'));
    } catch (error) {
        return { ok: false, round: currentRound + 1, of: ROUNDS.length, message: `Round ${index + 1}: ${error.message}` };
    }
    const response = await sendToClient(COMMANDS.LOAD_LEVEL, level);
    traceLine(COMMANDS.LOAD_LEVEL, null, response);
    room.answered(COMMANDS.LOAD_LEVEL, '127.0.0.1', response);
    if (response.success) {
        currentRound = index;
        console.log(`Round ${index + 1} of ${ROUNDS.length} loaded: ${path.basename(ROUNDS[index])}`);
    }
    return { ok: Boolean(response.success), round: currentRound + 1, of: ROUNDS.length, message: response.message };
}

const app = express();
app.use(express.json());
// Asset packs (D8a): DC_ASSET_PACKS lists pack folders (separated by the path delimiter).
// Each is served under /packs/<i>/ and named in index.html before the bundled assets.
const ASSET_PACKS = (process.env.DC_ASSET_PACKS || '').split(path.delimiter).filter(p => p);
ASSET_PACKS.forEach((folder, i) => app.use(`/packs/${i}`, express.static(path.resolve(folder))));
app.get(['/', '/index.html'], (req, res) => {
    const html = readFileSync(path.join(__dirname, '..', 'game', 'index.html'), 'utf8')
        .replace(/\$\{assetPackUris\}/g, JSON.stringify(ASSET_PACKS.map((_, i) => `/packs/${i}/`)))
        .replace(/\$\{wsPort\}/g, String(WS_PORT))
        .replace(/\$\{rounds\}/g, String(ROUNDS.length));
    res.type('html').send(html);
});
app.use(express.static(path.join(__dirname, '..', 'game')));
// the referee's round switch (keys N and R on the page): not part of the API, this machine only;
// GET tells the page which round is loaded (for the scoreboard)
app.get('/referee/round', (req, res) => {
    res.json({ ok: ROUNDS.length > 0, round: currentRound + 1, of: ROUNDS.length });
});
app.post('/referee/round', async (req, res) => {
    if (!RoomAccess.isLoopback(req.ip)) {
        res.status(403).json({ ok: false, message: 'Only the game\'s own computer may switch rounds.' });
        return;
    }
    if (ROUNDS.length === 0) {
        res.status(404).json({ ok: false, message: 'No rounds (DC_ROUNDS) were given to this server.' });
        return;
    }
    const step = req.body?.step;
    const index = step === 'next' ? currentRound + 1 : step === 'first' ? 0 : Math.max(0, currentRound);
    res.json(await loadRound(index));
});
app.use(OpenApiValidator.middleware({
    apiSpec: path.join(__dirname, '..', 'api', 'openapi.yaml'),
    validateRequests: true,
    validateResponses: false,
}));

function sendApiResponse(res, response) {
    if (response.success) {
        res.status(200).json({ status: 'success', message: response.message, result: response.result ?? null });
    } else {
        res.status(500).json({ status: 'error', message: response.message, exception: response.exception });
    }
}

// A live game with the server open to the room (EXPOSED): the same rules as the extension's
const room = new RoomAccess(EXPOSED);

function registerRoute(method, route, command, options = {}) {
    app[method](route, async (req, res) => {
        try {
            // co-op levels: the query parameter `hero` picks the hero (as in src/extension.ts, withHero)
            let params = options.includeBody ? req.body : null;
            // query parameters the game needs: hero (co-op levels), distance (is_enemy_in_front)
            for (const key of ['hero', 'distance']) {
                if (req.query[key] !== undefined && req.query[key] !== '') {
                    params = { ...(params ?? {}), [key]: Number(req.query[key]) };
                }
            }
            const refused = room.refusal(command, req.ip, params);
            if (refused) {
                sendApiResponse(res, { success: false, message: refused, exception: 'Refused' });
                return;
            }
            const response = await sendToClient(command, params);
            traceLine(command, params, response);
            room.answered(command, req.ip, response);
            if (response.success && options.onSuccess) {
                // onSuccess may return a replacement response, e.g. a failed move poll.
                const replacement = await options.onSuccess(response, req);
                if (replacement) {
                    sendApiResponse(res, replacement);
                    return;
                }
            }
            sendApiResponse(res, response);
        } catch (error) {
            console.error('API Error:', error);
            res.status(500).json({ status: 'error', message: `Internal server error: ${error.message}` });
        }
    });
}

// --- Routes: all from api/openapi.yaml (ROUTES, generated), plus special behaviour per command ---
// A (re)loaded level has a fresh hero at pace 1; reset the server's copy too.
const resetPace = () => { currentPaceFactor = 1.0; };
const AFTER_SUCCESS = {
    [COMMANDS.MOVE]: (_, req) => pollUntilStopped(10, req.query.hero),
    [COMMANDS.TURN_LEFT]: () => delay(TURN_DELAY_MS / currentPaceFactor),
    [COMMANDS.SET_PACE]: (_, req) => {
        const factor = req.body?.factor;
        if (typeof factor === 'number') {
            currentPaceFactor = factor;
        }
    },
    [COMMANDS.LOAD_LEVEL]: resetPace,
    [COMMANDS.RESET_LEVEL]: resetPace,
};
const registeredCommands = new Set([
    // Used only internally by pollUntilStopped(), not exposed as an HTTP route.
    COMMANDS.IS_MOVING,
]);
for (const route of ROUTES) {
    if (route.host) {
        continue;
    }
    registerRoute(route.method, route.path, route.command, { includeBody: route.body, onSuccess: AFTER_SUCCESS[route.command] });
    registeredCommands.add(route.command);
}
// answered here, not by the game (x-host in the spec): the Python package checks that it fits
app.get('/version', (req, res) => {
    const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
    const extension = JSON.parse(readFileSync(path.join(root, 'package.json'), 'utf8')).version;
    const spec = readFileSync(path.join(root, 'api', 'openapi.yaml'), 'utf8');
    const api = (spec.match(/^ {2}version: *"?([^"\s]+)"?/m) || [])[1] ?? 'unknown';
    res.json({ status: 'success', message: 'versions', result: { extension, api } });
});

const missingRoutes = COMMAND_LIST.filter(command => !registeredCommands.has(command));
if (missingRoutes.length > 0) {
    console.error(`dev-server: no HTTP route registered for command(s): ${missingRoutes.join(', ')}`);
}

app.use((err, req, res, next) => {
    console.error('API validation/error:', err.message);
    res.status(err.status ?? 500).json({
        status: 'error',
        message: err.message,
        exception: err.name ?? 'ServerError',
    });
});

app.listen(HTTP_PORT, HOST, () => {
    console.log(`Dev API running on http://${HOST}:${HTTP_PORT} (open /index.html in a browser)`);
    console.log(`Dev WebSocket listening on ws://${HOST}:${WS_PORT}/ws/game`);
    if (EXPOSED) {
        console.log('Open to other computers (DC_HOST): levels, start and end only from this machine; heroes belong to the computer that joined them.');
    }
    if (ROUNDS.length > 0) {
        console.log(`${ROUNDS.length} round(s) (DC_ROUNDS): round 1 loads when the page connects; on the page N = next round, R = again.`);
    }
});
