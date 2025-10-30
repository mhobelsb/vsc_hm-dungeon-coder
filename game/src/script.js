import { Game, GAME_WIDTH, GAME_HEIGHT } from './game.js';

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

function send_response_vscode(requestId, response) {
    let vscode = acquireVsCodeIfAvailable();
    vscode.postMessage({
        command: 'webviewResponse',
        requestId: requestId,
        response: response
    });
}

// Websocket if normal javascript in browser
let socket = null;
function send_response_websocket(response) {
    socket.send(JSON.stringify(response));
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

    async function process_message(game, message, send_response=send_response_websocket) {
        let response = {success: true, message: "", exception: "", result: true};
        const character = game.getCharacterInterface();

        console.log(`Received command "${message.command}"`);

        try {
            switch (message.command) {
                case 'load_level': 
                    response.result = await game.loadLevel(message.data);
                    canvas.focus();
                    response.message = response.result ? "Parsing level successful." : "Parsing level failed.";
                    break;

                case 'move':
                    response.result = character.move();
                    response.message = response.result ? "Hero moved successfully." : "Moving failed. Way is blocked.";
                    break;

                case 'interact':
                    response.result = character.interact();
                    response.message = response.result ? "Hero interacted successfully." : "Hero could not interact.";
                    break;

                case 'turn_left':
                    response.result = character.turnLeft();
                    response.message = "Hero turned left successfully.";
                    break;

                case 'is_moving':
                    response.result = character.isMoving();
                    response.message = response.result ? `Hero is moving.`: `Hero is standing.`
                    break;
                
                case 'configure':
                    response.result = character.configure(message.data.name, message.data.typeNumber);
                    response.message = response.result ? "Hero configured successfully." : "Unable to configure hero.";

                case 'is_facing_north':
                    response.result = character.isFacingNorth();
                    response.message = response.result ? `Hero is facing north.`: `Hero is not facing north.`
                    break;
                
                case 'is_at_goal':
                    response.result = character.isAtGoal();
                    response.message = response.result ? `Hero has reached the goal.`: `Hero is not at the goal.`
                    break;

                case 'is_collision_in_front':
                    response.result = character.isCollisionInFront();
                    response.message = response.result ? `There is a collision in front.`: `There is no collision in front.`
                    break;

                case 'is_abyss_in_front':
                    response.result = character.isAbyssInFront();
                    response.message = response.result ? `Hero is standing in front of an abyss.`: `Hero is standing on solid ground. No abyss in front.`
                    break;

                case 'is_torch_in_front':
                    response.result = character.isTorchInFront();
                    response.message = response.result ? `There is a torch in front.`: `There is no torch in front.`
                    break;

                case 'is_switch_in_front':
                    response.result = character.isSwitchInFront();
                    response.message = response.result ? `There is a switch in front.`: `There is no switch in front.`
                    break;

                case 'get_items_at_position':
                    response.result = character.getItemsAtHeroPosition();
                    response.message = response.result.length > 0 ? 'There are items at the current position.' : 'There are no items at the current position.';
                    break;

                case 'get_inventory':
                    response.result = character.getInventory();
                    response.message = response.result.length > 0 ? 'There are items in the inventory.' : 'There are no items in the inventory.';
                    break;

                case 'pickup':
                    response.result = character.pickup(message.data.name);
                    response.message = response.result ? `Picked up item. "${message.data}"` : `Item "${message.data}" not found at current location.`;
                    break;

                case 'drop':
                    response.result = character.drop(message.data.name);
                    response.message = response.result ? `Successfully dropped item "${message.data}."` : `Item "${message.data}" not in inventory.`;
                    break;

                case 'set_pace':
                    response.result = character.set_pace(message.data.factor);
                    response.message = response.result ? `Successfully changed pace to factor "${message.data.factor}."` : `Could not change pace to "${message.data.factor}".`;
                    break;

                default:
                    response.success = false;
                    response.message = "Error: Command not found."
                    break;
            }
        } catch(error) {
            console.error(`Request "${message.command}" failed.`)
            response.success = false;
        }

        send_response(message.requestId, response);
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
