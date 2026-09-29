import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs/promises';
import { readFileSync, constants as fsConstants } from 'fs';
import express, { Application, Request, Response, NextFunction } from 'express';
import * as OpenApiValidator from 'express-openapi-validator';
import { Server } from 'http';
import { COMMANDS, COMMAND_LIST } from '../game/src/commands.js';
import { API_HOST, API_PORT } from '../game/src/api-config.js';
import type { components } from './generated/api-types.js';

// Upper bound for one move() step: the animation takes MOVE_DURATION_MS / pace
// (Character.moveDuration in game/src/character.js), plus generous slack.
const MOVE_DURATION_MS = 500;
const MOVE_TIMEOUT_BASE_MS = 5000;

/** Business-outcome payload, unchanged externally so the Python client needs no changes. */
interface WebviewResponse {
    success: boolean;
    message: string;
    exception?: string;
    result?: any;
}

/**
 * Wire format between the extension host and the webview: a JSON-RPC 2.0
 * style envelope, shared (as far as the message shape goes) with the
 * WebSocket transport used when the game runs outside VS Code. `method` is
 * always one of COMMANDS (game/src/commands.js) - the single source of truth
 * also consumed by game/src/script.js's dispatch table.
 */
interface WebviewRequest {
    jsonrpc: '2.0';
    id: string;
    method: string;
    params?: any;
}

interface WebviewRpcSuccess {
    jsonrpc: '2.0';
    id: string;
    result: WebviewResponse;
}

interface WebviewRpcError {
    jsonrpc: '2.0';
    id: string;
    error: { message: string };
}

type WebviewRpcResponse = WebviewRpcSuccess | WebviewRpcError;

/**
 * DungeonCoderServer – Singleton handling Express API + VS Code Webview.
 */
export class DungeonCoderServer {
    private static instance: DungeonCoderServer;
    private webviewPanel?: vscode.WebviewPanel;
    private serverInstance?: Server;
    private currentPaceFactor = 1.0;
    private turnDelay = 200;
    private readonly url = API_HOST;
    private readonly port = API_PORT;
    private readonly pendingWebviewRequests = new Map<string, (response: WebviewRpcResponse) => void>();
    private readonly registeredCommands = new Set<string>();

    private constructor() { }

    /** Singleton accessor */
    public static getInstance(): DungeonCoderServer {
        if (!DungeonCoderServer.instance) {
            DungeonCoderServer.instance = new DungeonCoderServer();
        }
        return DungeonCoderServer.instance;
    }

    /** Delay helper */
    private async delay(ms: number) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /** Send a JSON-RPC request to the webview and await its reply. */
    private async sendMessageToWebview(method: string, params: any = null): Promise<WebviewResponse> {
        if (!this.webviewPanel) {
            vscode.window.showErrorMessage('Webview not open.');
            return { success: false, message: 'Webview not open.', exception: 'WebViewNotOpen' };
        }

        const id = Date.now().toString() + Math.random().toString(36).substring(2, 9);
        const request: WebviewRequest = { jsonrpc: '2.0', id, method, params };

        const rpcResponse = await new Promise<WebviewRpcResponse>(resolve => {
            this.pendingWebviewRequests.set(id, resolve);
            this.webviewPanel!.webview.postMessage(request);
        });

        if ('error' in rpcResponse) {
            return { success: false, message: rpcResponse.error.message, exception: 'RpcError' };
        }
        return rpcResponse.result;
    }

    /** Unified Express route registration helper */
    private registerRoute(
        app: Application,
        method: 'get' | 'post',
        route: string,
        command: string,
        options?: {
            includeBody?: boolean;
            // May return a replacement response, e.g. when a follow-up step fails.
            onSuccess?: (response: WebviewResponse, req: Request) => void | WebviewResponse | Promise<void | WebviewResponse>;
        }
    ) {
        this.registeredCommands.add(command);
        (app as any)[method](route, async (req: Request, res: Response) => {
            try {
                const data = options?.includeBody ? req.body : null;
                const response = await this.sendMessageToWebview(command, data);

                if (!response.success) {
                    this.sendApiResponse(res, response);
                    return;
                }

                if (options?.onSuccess) {
                    const replacement = await options.onSuccess(response, req);
                    if (replacement) {
                        this.sendApiResponse(res, replacement);
                        return;
                    }
                }

                this.sendApiResponse(res, response);
            } catch (error: any) {
                this.handleApiError(res, error);
            }
        });
    }

    /** Specialized delayed command (like turn_left) */
    private registerDelayedCommandRoute(app: Application, route: string, command: string, baseDelay: number) {
        this.registerRoute(app, 'post', route, command, {
            onSuccess: async () => {
                await this.delay(baseDelay / this.currentPaceFactor);
            },
        });
    }

    /**
     * Polls until the hero has finished its step. Gives up when the webview
     * reports an error or the step takes far longer than the animation
     * should, instead of polling forever.
     * @returns undefined once the hero stands, otherwise an error response.
     */
    private async pollUntilStopped(pollInterval = 10): Promise<WebviewResponse | undefined> {
        const deadline = Date.now() + MOVE_TIMEOUT_BASE_MS + MOVE_DURATION_MS / this.currentPaceFactor;
        while (Date.now() < deadline) {
            const isMovingResponse = await this.sendMessageToWebview(COMMANDS.IS_MOVING);

            if (!isMovingResponse.success) {
                return isMovingResponse;
            }
            if (!isMovingResponse.result) {
                return undefined;
            }
            await this.delay(pollInterval);
        }
        return { success: false, message: 'The hero did not finish its step in time.', exception: 'MoveTimeout' };
    }

    /** Unified success/error response handling */
    private sendApiResponse(res: Response, response: WebviewResponse) {
        if (response.success) {
            res.status(200).json({
                status: 'success',
                message: response.message,
                result: response.result ?? null,
            });
        } else {
            res.status(500).json({
                status: 'error',
                message: response.message,
                exception: response.exception,
            });
        }
    }

    private handleApiError(res: Response, error: any) {
        console.error('API Error:', error);
        if (!res.headersSent) {
            res.status(500).json({
                status: 'error',
                message: `Internal server error: ${error.message}`,
            });
        }
    }

    /** Start server */
    public startServer(extensionPath: string) {
        if (this.serverInstance) {
            vscode.window.showErrorMessage("It seems like Dungeon Coder is already running in a different tab. Please check!");
            return false;
        }

        const app = express();
        app.use(express.json());

        // Validates every request against api/openapi.yaml before it reaches
        // a route handler - the spec is the single source of truth for what
        // a request is allowed to look like, so this is enforced rather than
        // re-checked by hand per route.
        app.use(OpenApiValidator.middleware({
            apiSpec: path.join(extensionPath, 'api', 'openapi.yaml'),
            validateRequests: true,
            validateResponses: false,
        }));

        // --- Hero Movement ---
        this.registerRoute(app, 'post', '/hero/move', COMMANDS.MOVE, {
            onSuccess: async () => this.pollUntilStopped(10),
        });

        this.registerDelayedCommandRoute(app, '/hero/turn_left', COMMANDS.TURN_LEFT, this.turnDelay);

        // --- Configuration ---
        this.registerRoute(app, 'post', '/hero/configure', COMMANDS.CONFIGURE, { includeBody: true });
        this.registerRoute(app, 'post', '/hero/pace', COMMANDS.SET_PACE, {
            includeBody: true,
            onSuccess: async (_, req) => {
                // req.body is shaped per api/openapi.yaml's PaceParams schema and
                // has already passed the OpenAPI validator by the time we get here.
                const body: components['schemas']['PaceParams'] = req.body;
                this.currentPaceFactor = body.factor;
                console.log(`Updated current pace factor: ${body.factor}`);
            },
        });

        // --- Interaction ---
        this.registerRoute(app, 'post', '/hero/interact', COMMANDS.INTERACT);
        this.registerRoute(app, 'post', '/hero/pickup', COMMANDS.PICKUP, { includeBody: true });
        this.registerRoute(app, 'post', '/hero/drop', COMMANDS.DROP, { includeBody: true });

        // --- Queries ---
        this.registerRoute(app, 'get', '/hero/get_items_at_position', COMMANDS.GET_ITEMS_AT_POSITION);
        this.registerRoute(app, 'get', '/hero/inventory', COMMANDS.GET_INVENTORY);
        this.registerRoute(app, 'get', '/game/statistics', COMMANDS.GET_STATISTICS);

        // --- Level ---
        // A (re)loaded level has a fresh hero at pace 1, so the host's copy of
        // the pace must be reset too, or turns keep the old script's delay.
        const resetPace = () => { this.currentPaceFactor = 1.0; };
        this.registerRoute(app, 'post', '/level/load', COMMANDS.LOAD_LEVEL, { includeBody: true, onSuccess: resetPace });
        this.registerRoute(app, 'post', '/level/reset', COMMANDS.RESET_LEVEL, { onSuccess: resetPace });

        [
            COMMANDS.IS_COLLISION_IN_FRONT,
            COMMANDS.IS_FACING_NORTH,
            COMMANDS.IS_AT_GOAL,
            COMMANDS.IS_TORCH_IN_FRONT,
            COMMANDS.IS_SWITCH_IN_FRONT,
            COMMANDS.IS_ABYSS_IN_FRONT,
        ].forEach(command =>
            this.registerRoute(app, 'get', `/hero/${command}`, command)
        );

        // IS_MOVING is used only internally by pollUntilStopped(), not exposed as an HTTP route.
        this.registeredCommands.add(COMMANDS.IS_MOVING);
        const missingRoutes = COMMAND_LIST.filter(command => !this.registeredCommands.has(command));
        if (missingRoutes.length > 0) {
            console.error(`Dungeon Coder: no HTTP route registered for command(s): ${missingRoutes.join(', ')}`);
        }

        // Translates express-openapi-validator's error shape (and any other
        // thrown error) into the same { status, message, exception } envelope
        // every route already returns, so the Python client's response
        // parsing doesn't need to special-case validation failures.
        app.use((err: any, req: Request, res: Response, next: NextFunction) => {
            console.error('API validation/error:', err.message);
            res.status(err.status ?? 500).json({
                status: 'error',
                message: err.message,
                exception: err.name ?? 'ServerError',
            });
        });

        this.serverInstance = app.listen(this.port, this.url, () =>
            console.log(`API running on ${this.url}:${this.port}`)
        );

        this.serverInstance.on('error', err => {
            if ((err as any).code === 'EADDRINUSE') {
                const message = `Error: Port ${this.port} is already in use. Is another instance running?`;
                vscode.window.showErrorMessage(message);
                this.stopServer();
                this.webviewPanel?.dispose();
            } else {
                console.error('Unexpected server error:', err);
                vscode.window.showErrorMessage(`Unexpected error: ${err.message}`);
                this.webviewPanel?.dispose();
            }
        });

        return true;
    }

    /** Stop server */
    public stopServer() {
        if (this.serverInstance) {
            console.log('Stopping server...');
            this.serverInstance.close(err => {
                if (err) console.error('Error stopping server:', err);
                else console.log('Server stopped successfully.');
                this.serverInstance = undefined;
            });
        } else {
            console.log('Server not running.');
        }
    }

    /** Create VS Code webview */
    public async createWebview(context: vscode.ExtensionContext) {
        if (this.webviewPanel) {
            vscode.window.showErrorMessage('It seems like Dungeon Coder is already running in another tab. Please check!');
            return false;
        }

        this.webviewPanel = vscode.window.createWebviewPanel(
            'gamePanel',
            'Dungeon Coder - Live View',
            vscode.ViewColumn.Beside,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
                localResourceRoots: [vscode.Uri.joinPath(context.extensionUri, 'game')],
            }
        );

        this.webviewPanel.webview.onDidReceiveMessage(
            (message: WebviewRpcResponse) => {
                if (message?.jsonrpc === '2.0' && message.id) {
                    const resolver = this.pendingWebviewRequests.get(message.id);
                    if (resolver) {
                        resolver(message);
                        this.pendingWebviewRequests.delete(message.id);
                    }
                }
            },
            undefined,
            context.subscriptions
        );

        this.webviewPanel.onDidDispose(
            () => {
                console.log('Webview closed. Cleaning up...');
                this.stopServer();
                this.webviewPanel = undefined;
            },
            null,
            context.subscriptions
        );

        this.webviewPanel.webview.html = await this.getWebviewContent(
            this.webviewPanel.webview,
            context.extensionPath
        );

        return true;
    }

    /** Load HTML with CSP */
    private async getWebviewContent(webview: vscode.Webview, extensionPath: string): Promise<string> {
        const nonce = this.getNonce();
        const mediaFolderUri = webview.asWebviewUri(vscode.Uri.file(path.join(extensionPath, 'game')));
        const htmlFilePath = path.join(extensionPath, 'game', 'index.html');

        let htmlContent: string;
        try {
            htmlContent = readFileSync(htmlFilePath, 'utf8');
        } catch (error: any) {
            throw new Error(`Could not read index.html: ${error.message}`);
        }

        const csp = `
      <meta http-equiv="Content-Security-Policy"
      content="
        default-src 'none';
        img-src ${webview.cspSource} https:;
        script-src ${webview.cspSource} 'nonce-${nonce}';
        style-src ${webview.cspSource} 'nonce-${nonce}';
        connect-src ${webview.cspSource} ${this.url}:${this.port};
      ">
    `;

        return htmlContent
            .replace('<!-- CSP -->', csp)
            .replace(/\$\{webview.cspSource\}/g, webview.cspSource)
            .replace(/\$\{nonce\}/g, nonce)
            .replace(/\$\{gameFolderUri\}/g, mediaFolderUri.toString());
    }

    private getNonce() {
        const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
        return Array.from({ length: 32 }, () =>
            possible.charAt(Math.floor(Math.random() * possible.length))
        ).join('');
    }
}

// ------------------------------------------------------------
// VSCode activate function using the Singleton
// ------------------------------------------------------------
export function activate(context: vscode.ExtensionContext) {
    const server = DungeonCoderServer.getInstance();

    const startGame = vscode.commands.registerCommand('vscode-dungeon-coder.startGame', async () => {
        let ret = await server.createWebview(context);
        ret = ret && server.startServer(context.extensionPath);
        if (ret) {
            vscode.window.showInformationMessage('Enter the dungeon!');
        } else {
            vscode.window.showErrorMessage("Error: Dungeon Coder could not be started.")
        }
    });

    let copyPythonDisposable = vscode.commands.registerCommand('vscode-dungeon-coder.copyPythonAPI', async () => {
        const folders = vscode.workspace.workspaceFolders;
        if (!folders || folders.length === 0) {
            vscode.window.showErrorMessage('Please open a workspace or folder first.');
            return;
        }

        const workspacePath = folders[0].uri.fsPath;
        const sourcePath = path.join(context.extensionPath, 'api', 'python', 'dungeoncoder');
        const destPath = path.join(workspacePath, 'dungeoncoder');

        try {
            // Check if already exists
            try {
                await fs.access(destPath, fsConstants.F_OK);
                const overwrite = await vscode.window.showQuickPick(['Yes', 'No'], {
                    placeHolder: `Folder 'dungeoncoder' already exists. Overwrite?`
                });
                if (overwrite !== 'Yes') return;
            } catch {
                // folder doesn’t exist, continue
            }

            // Create destination folder
            await fs.mkdir(destPath, { recursive: true });

            // Copy files recursively
            await copyFolderRecursive(sourcePath, destPath);

            vscode.window.showInformationMessage(`Python files copied to ${destPath}`);
        } catch (err) {
            vscode.window.showErrorMessage(`Failed to copy Python files: ${err}`);
        }
    });

    context.subscriptions.push(startGame);
    context.subscriptions.push(copyPythonDisposable);

}




async function copyFolderRecursive(src: string, dest: string) {
    const entries = await fs.readdir(src, { withFileTypes: true });
    for (const entry of entries) {
        const srcPath = path.join(src, entry.name);
        const destPath = path.join(dest, entry.name);
        if (entry.isDirectory()) {
            await fs.mkdir(destPath, { recursive: true });
            await copyFolderRecursive(srcPath, destPath);
        } else {
            await fs.copyFile(srcPath, destPath);
        }
    }
}
