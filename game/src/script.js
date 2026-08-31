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
 
    function resizeCanvas() {
        const scaleX = Math.floor(window.innerWidth / GAME_WIDTH); 
        const scaleY = Math.floor(window.innerHeight / GAME_HEIGHT); 
        const scale = Math.max(1, Math.min(scaleX, scaleY)); // keep at least 1x 
        const displayWidth = GAME_WIDTH * scale; 
        const displayHeight = GAME_HEIGHT * scale; 
        canvas.style.width = displayWidth + "px"; 
        canvas.style.height = displayHeight + "px"; 
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

        [COMMANDS.PICKUP]: (game, character, params) => {
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

    async function process_message(game, message, send_response = send_response_websocket) {
        const character = game.getCharacterInterface();
        console.log(`Received command "${message.method}"`);

        const handler = HANDLERS[message.method];
        if (!handler) {
            send_response(message.id, { error: { message: `Unknown method: "${message.method}"` } });
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
    canvas.width = GAME_WIDTH; 
    canvas.height = GAME_HEIGHT; 
    const ctx = canvas.getContext('2d');;
    ctx.imageSmoothingEnabled = false;

    if(isRunningInVSCodeWebview()) {
        fileInput.style.display = 'none';
    }

    const game = new Game(canvas, getAssetPath(""));
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
