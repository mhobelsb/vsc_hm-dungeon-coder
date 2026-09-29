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
import { COMMANDS, COMMAND_LIST } from '../game/src/commands.js';
import { API_HOST, API_PORT } from '../game/src/api-config.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const HOST = API_HOST;
// DC_PORT lets the dev server run next to an installed Dungeon Coder
// extension, which already occupies API_PORT while its game tab is open.
// Python clients then need Game.BASE_URL pointed at the same port.
const HTTP_PORT = Number(process.env.DC_PORT ?? API_PORT);
const WS_PORT = 8000;
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

    socket.on('message', raw => {
        const message = JSON.parse(raw.toString());
        const resolver = pendingRequests.get(message.id);
        if (!resolver) return;
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
async function pollUntilStopped(pollInterval = 10) {
    const deadline = Date.now() + MOVE_TIMEOUT_BASE_MS + MOVE_DURATION_MS / currentPaceFactor;
    while (Date.now() < deadline) {
        const isMovingResponse = await sendToClient(COMMANDS.IS_MOVING);
        if (!isMovingResponse.success) return isMovingResponse;
        if (!isMovingResponse.result) return undefined;
        await delay(pollInterval);
    }
    return { success: false, message: 'The hero did not finish its step in time.', exception: 'MoveTimeout' };
}

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname, '..', 'game')));
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

function registerRoute(method, route, command, options = {}) {
    app[method](route, async (req, res) => {
        try {
            const params = options.includeBody ? req.body : null;
            const response = await sendToClient(command, params);
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

// --- Hero Movement ---
registerRoute('post', '/hero/move', COMMANDS.MOVE, { onSuccess: () => pollUntilStopped(10) });
registerRoute('post', '/hero/turn_left', COMMANDS.TURN_LEFT, {
    onSuccess: () => delay(TURN_DELAY_MS / currentPaceFactor),
});

// --- Configuration ---
registerRoute('post', '/hero/configure', COMMANDS.CONFIGURE, { includeBody: true });
registerRoute('post', '/hero/pace', COMMANDS.SET_PACE, {
    includeBody: true,
    onSuccess: (_, req) => {
        const factor = req.body?.factor;
        if (typeof factor === 'number') {
            currentPaceFactor = factor;
        }
    },
});

// --- Interaction ---
registerRoute('post', '/hero/interact', COMMANDS.INTERACT);
registerRoute('post', '/hero/pickup', COMMANDS.PICKUP, { includeBody: true });
registerRoute('post', '/hero/drop', COMMANDS.DROP, { includeBody: true });

// --- Queries ---
registerRoute('get', '/hero/get_items_at_position', COMMANDS.GET_ITEMS_AT_POSITION);
registerRoute('get', '/hero/inventory', COMMANDS.GET_INVENTORY);
registerRoute('get', '/game/statistics', COMMANDS.GET_STATISTICS);

// --- Level ---
// A (re)loaded level has a fresh hero at pace 1; reset the server's copy too.
const resetPace = () => { currentPaceFactor = 1.0; };
registerRoute('post', '/level/load', COMMANDS.LOAD_LEVEL, { includeBody: true, onSuccess: resetPace });
registerRoute('post', '/level/reset', COMMANDS.RESET_LEVEL, { onSuccess: resetPace });

const registeredCommands = new Set([
    COMMANDS.MOVE, COMMANDS.TURN_LEFT, COMMANDS.CONFIGURE, COMMANDS.SET_PACE,
    COMMANDS.INTERACT, COMMANDS.PICKUP, COMMANDS.DROP, COMMANDS.GET_ITEMS_AT_POSITION,
    COMMANDS.GET_INVENTORY, COMMANDS.GET_STATISTICS, COMMANDS.LOAD_LEVEL, COMMANDS.RESET_LEVEL,
    // Used only internally by pollUntilStopped(), not exposed as an HTTP route.
    COMMANDS.IS_MOVING,
]);

[
    COMMANDS.IS_COLLISION_IN_FRONT,
    COMMANDS.IS_FACING_NORTH,
    COMMANDS.IS_AT_GOAL,
    COMMANDS.IS_TORCH_IN_FRONT,
    COMMANDS.IS_SWITCH_IN_FRONT,
    COMMANDS.IS_ABYSS_IN_FRONT,
].forEach(command => {
    registerRoute('get', `/hero/${command}`, command);
    registeredCommands.add(command);
});

const missingRoutes = COMMAND_LIST.filter(command => !registeredCommands.has(command));
if (missingRoutes.length > 0) {
    console.error(`dev-server: no HTTP route registered for command(s): ${missingRoutes.join(', ')}`);
}

// eslint-disable-next-line no-unused-vars
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
});
