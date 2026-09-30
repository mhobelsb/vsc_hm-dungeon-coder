import { Game, GAME_WIDTH, GAME_HEIGHT } from './game.js';
import { COMMANDS } from './commands.js';

let vscode = null;

function acquireVsCodeIfAvailable() {
    if (isRunningInVSCodeWebview() && vscode == null) {
        vscode = acquireVsCodeApi();
    }

    return vscode;
}

function isRunningInVSCodeWebview() {
    return typeof acquireVsCodeApi === 'function';
}

export function getAssetPath(relativePath) {
    return window.VscodeGameMediaUri + '/' + relativePath;
}

// VS Code stuff if extension
if (typeof window.VscodeGameMediaUri === 'undefined') {
    console.error('VscodeGameMediaUri is not defined. Make sure the script injecting it runs first.');
}

// Both transports carry the same JSON-RPC 2.0 style envelope:
// request:  { jsonrpc: '2.0', id, method, params }
// response: { jsonrpc: '2.0', id, result } | { jsonrpc: '2.0', id, error: { message } }
function send_response_vscode(id, payload) {
    let vscode = acquireVsCodeIfAvailable();
    vscode.postMessage({ jsonrpc: '2.0', id, ...payload });
}

// Websocket if normal javascript in browser
let socket = null;
function send_response_websocket(id, payload) {
    socket.send(JSON.stringify({ jsonrpc: '2.0', id, ...payload }));
}


function loadFileAsync(file) {
    return new Promise((resolve, reject) => {
        if (!file) {
            return reject(new Error("No file provided."));
        }

        const reader = new FileReader();

        reader.onload = (e) => {
            try {
                const parsedData = JSON.parse(e.target.result);
                resolve(parsedData);
            } catch (error) {
                reject(new Error(`JSON Parsing Error: ${error.message}`));
            }
        };

        reader.onerror = () => {
            reject(new Error("File reading failed."));
        };

        reader.readAsText(file);
    });
}

(async function () {
 
    // Fit the game into the panel: any scale, not only whole numbers, so a panel of
    // e.g. 700 px shows the game at 1.4x instead of 1x (tile-size step A, docs/tile-size.md).
    // The picture stays pixel-sharp (image-rendering: pixelated, drawn at RENDER_SCALE).
    function resizeCanvas() {
        const picker = document.getElementById('json-file-input');     // only shown in the browser
        const reserved = picker && picker.style.display !== 'none' ? picker.offsetHeight + 16 : 0;
        const width = game.viewWidth, height = game.viewHeight;     // the level's size in game pixels
        const fit = 0.97 * Math.min(window.innerWidth / width, (window.innerHeight - reserved) / height);
        const scale = Math.max(0.5 * Math.min(GAME_WIDTH / width, GAME_HEIGHT / height), fit);
        canvas.style.width = Math.floor(width * scale) + "px";
        canvas.style.height = Math.floor(height * scale) + "px";
    }

    // One handler per RPC method, keyed by the shared COMMANDS registry
    // (game/src/commands.js). Each handler returns the business-outcome
    // payload { success, message, result }; a missing/failing handler is a
    // transport-level error (JSON-RPC `error`), not a business outcome.
    const HANDLERS = {
        [COMMANDS.LOAD_LEVEL]: async (game, character, params) => {
            const result = await game.loadLevel(params);
            canvas.focus();
            return { success: result, message: result ? "Parsing level successful." : "Parsing level failed.", result };
        },

        [COMMANDS.RESET_LEVEL]: async (game, character) => {
            const result = await game.resetLevel();
            canvas.focus();
            return { success: result, message: result ? "Level reset successfully." : "No level has been loaded yet.", result };
        },

        [COMMANDS.MOVE]: (game, character) => {
            const result = character.move();
            return { success: result, message: result ? "Hero moved successfully." : "Moving failed. Way is blocked.", result };
        },

        [COMMANDS.INTERACT]: (game, character) => {
            const result = character.interact();
            return { success: result, message: result ? "Hero interacted successfully." : "Hero could not interact.", result };
        },

        [COMMANDS.TURN_LEFT]: (game, character) => {
            const result = character.turnLeft();
            return { success: true, message: "Hero turned left successfully.", result };
        },

        [COMMANDS.IS_MOVING]: (game, character) => {
            const result = character.isMoving();
            return { success: true, message: result ? "Hero is moving." : "Hero is standing.", result };
        },

        [COMMANDS.CONFIGURE]: (game, character, params) => {
            const result = character.configure(params.name, params.typeNumber);
            return { success: result, message: result ? "Hero configured successfully." : "Unable to configure hero.", result };
        },

        [COMMANDS.IS_FACING_NORTH]: (game, character) => {
            const result = character.isFacingNorth();
            return { success: true, message: result ? "Hero is facing north." : "Hero is not facing north.", result };
        },

        [COMMANDS.IS_AT_GOAL]: (game, character) => {
            const result = character.isAtGoal();
            return { success: true, message: result ? "Hero has reached the goal." : "Hero is not at the goal.", result };
        },

        [COMMANDS.IS_COLLISION_IN_FRONT]: (game, character) => {
            const result = character.isCollisionInFront();
            return { success: true, message: result ? "There is a collision in front." : "There is no collision in front.", result };
        },

        [COMMANDS.IS_ABYSS_IN_FRONT]: (game, character) => {
            const result = character.isAbyssInFront();
            return { success: true, message: result ? "Hero is standing in front of an abyss." : "Hero is standing on solid ground. No abyss in front.", result };
        },

        [COMMANDS.IS_TORCH_IN_FRONT]: (game, character) => {
            const result = character.isTorchInFront();
            return { success: true, message: result ? "There is a torch in front." : "There is no torch in front.", result };
        },

        [COMMANDS.IS_SWITCH_IN_FRONT]: (game, character) => {
            const result = character.isSwitchInFront();
            return { success: true, message: result ? "There is a switch in front." : "There is no switch in front.", result };
        },

        [COMMANDS.GET_ITEMS_AT_POSITION]: (game, character) => {
            const result = character.getItemsAtHeroPosition();
            return { success: true, message: result.length > 0 ? "There are items at the current position." : "There are no items at the current position.", result };
        },

        [COMMANDS.GET_INVENTORY]: (game, character) => {
            const result = character.getInventory();
            return { success: true, message: result.length > 0 ? "There are items in the inventory." : "There are no items in the inventory.", result };
        },

        [COMMANDS.GET_STATISTICS]: (game, character) => {
            if (!character) {
                return { success: false, message: "No level loaded.", result: null };
            }
            return { success: true, message: "Statistics of the current level.", result: character.getStatistics() };
        },

        [COMMANDS.IS_ENEMY_IN_FRONT]: (game, character) => {
            const result = character.isEnemyInFront();
            return { success: true, message: result ? "There is a guard in front." : "There is no guard in front.", result };
        },

        [COMMANDS.ASK_ORACLE]: (game, character) => {
            if (!character.hasOracle()) {
                return { success: false, message: "There is no oracle in this level (map property orakel).", result: null };
            }
            const result = character.askOracle();
            return { success: true, message: result === null ? "The oracle is silent." : `The oracle says: ${result}.`, result };
        },

        [COMMANDS.READ_ITEM_VALUE]: (game, character) => {
            const result = character.readItemValue();
            return { success: true, message: result === null ? "There is no item with a value here." : `The item here has the value ${result}.`, result };
        },

        [COMMANDS.PEEK_ITEM_VALUE]: (game, character, params) => {
            if (!character.hasFernrohr()) {
                return { success: false, message: "This level has no Fernrohr (map property fernrohr), so values can only be read on the hero's own field.", result: null };
            }
            if (!Number.isInteger(params?.distance) || params.distance < 1) {
                return { success: false, message: `distance must be a whole number of at least 1, not ${JSON.stringify(params?.distance)}.`, result: null };
            }
            const result = character.peekItemValue(params.distance);
            return { success: true, message: result === null ? `There is no item with a value ${params.distance} field(s) ahead.` : `The item ${params.distance} field(s) ahead has the value ${result}.`, result };
        },

        [COMMANDS.PICKUP]: (game, character, params) => {
            if (character.isInventoryFull()) {
                return { success: false, message: `The inventory is full (the level allows ${game.level?.getProperty?.('inventory_size')} item(s)). Drop something first.`, result: false };
            }
            const result = character.pickup(params.name);
            return { success: result, message: result ? `Picked up item "${params.name}".` : `Item "${params.name}" not found at current location.`, result };
        },

        [COMMANDS.DROP]: (game, character, params) => {
            const result = character.drop(params.name);
            return { success: result, message: result ? `Successfully dropped item "${params.name}".` : `Item "${params.name}" not in inventory.`, result };
        },

        [COMMANDS.SET_PACE]: (game, character, params) => {
            const result = character.set_pace(params.factor);
            return { success: result, message: result ? `Successfully changed pace to factor "${params.factor}".` : `Could not change pace to "${params.factor}".`, result };
        },
    };

    const ACTIONS_NEEDING_RUNNING_LEVEL = new Set([
        COMMANDS.MOVE, COMMANDS.TURN_LEFT, COMMANDS.INTERACT, COMMANDS.PICKUP, COMMANDS.DROP,
    ]);

    async function process_message(game, message, send_response = send_response_websocket) {
        const character = game.getCharacterInterface();
        console.log(`Received command "${message.method}"`);

        const handler = HANDLERS[message.method];
        if (!handler) {
            send_response(message.id, { error: { message: `Unknown method: "${message.method}"` } });
            return;
        }

        // Once a level is complete or lost, the world no longer updates, so
        // an action would start and never finish. Refuse it right away.
        if (ACTIONS_NEEDING_RUNNING_LEVEL.has(message.method) && !game.isRunning()) {
            send_response(message.id, { result: { success: false, message: "The level is over (goal reached or game over). Load a level to continue.", result: false } });
            return;
        }

        try {
            const result = await handler(game, character, message.params);
            send_response(message.id, { result });
        } catch (error) {
            console.error(`Request "${message.method}" failed:`, error);
            send_response(message.id, { error: { message: error.message } });
        }
    }

    const fileInput = document.getElementById('json-file-input');
    const canvas = document.getElementById('gameCanvas');
    if(isRunningInVSCodeWebview()) {
        fileInput.style.display = 'none';
    }

    // The game sizes the canvas buffer itself (Game.setViewSize): larger than the view, so
    // text gets crisp. Everything draws in game pixels; the transform does the scaling.
    const game = new Game(canvas, getAssetPath(""));
    game.onViewChange = resizeCanvas;
    game.start();

    fileInput.addEventListener('change', async (event) => {
        const file = event.target.files[0];
        if (!file) {
            return;
        }
        
        try {
            const parsedData = await loadFileAsync(file); 
            await game.loadLevel(parsedData);
            canvas.focus();
        } catch (error) {
            console.error('Operation failed:', error);
        }
    });

    if (!isRunningInVSCodeWebview()) {
        socket = new WebSocket("ws://127.0.0.1:8000/ws/game");
        socket.onopen = () => {
            socket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                process_message(game, data, send_response_websocket);
            };
        };
    } else {
        window.addEventListener('message', event => {
            process_message(game, event.data, send_response_vscode);
        });
    }

    window.addEventListener("resize", resizeCanvas); 
    resizeCanvas(); // initial fit

})();
