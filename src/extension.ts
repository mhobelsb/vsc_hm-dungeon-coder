import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import express from 'express';
import { Server } from 'http'; 

let webviewPanel: vscode.WebviewPanel | undefined;
let serverInstance: Server | undefined;

const pendingWebviewRequests = new Map<string, (result: WebviewResponse) => void>();

interface WebviewResponse {
  success: boolean;
  message: string;
  exception: string;
  result: boolean;
}

const delay = (ms: number): Promise<void> => new Promise(resolve => setTimeout(resolve, ms));

async function sendMessageToWebview(message: any): Promise<WebviewResponse> {
    if (!webviewPanel) {
        vscode.window.showErrorMessage('Webview not open.');
        return {success: false, message: "Webview not open.", exception: "WebViewNotOpen", result: false};
    }

    const requestId = Date.now().toString() + Math.random().toString(36).substring(2, 9);
    const messageWithId = { ...message, requestId };

    return new Promise(resolve => {
        pendingWebviewRequests.set(requestId, resolve);
        webviewPanel!.webview.postMessage(messageWithId);
    });
}
 
function startServer(sendToWebview: (cmd: string) => void) {
    const app = express();
    app.use(express.json());

    // Helper function to wait for a specific duration
    const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

    // Helper function to poll the webview until the condition is met
    async function pollUntilStopped(pollInterval = 10): Promise<void> {
        while (true) {
            const isMovingResponse = await sendMessageToWebview({
                command: "is_moving",
                data: null
            });

            // Check if the hero has stopped moving.
            // We check for success AND result being false (not moving)
            if (isMovingResponse.success && !isMovingResponse.result) {
                return; // Exit the loop and resolve the promise
            }

            // Wait for the specified interval before polling again
            await delay(pollInterval);
        }
    }

    app.post('/hero/move', async (req, res) => {
        try {
            // 1. Send the initial move command
            const webview_response = await sendMessageToWebview({
                command: "move",
                data: null
            });

            if (!webview_response.success) {
                // The initial move command was not successful
                return res.status(500).json({ status: 'error', message: webview_response.message });
            }

            // 2. Poll the is_moving API until the hero stops
            // Set the poll interval to 10ms as in your original code
            await pollUntilStopped(10); 

            // 3. Send the final success response once polling is complete
            res.status(200).json({ status: 'success', message: 'Hero has stopped moving' });

        } catch (error: any) {
            console.error('API Error:', error);
            // Ensure the response is sent even on unexpected errors during move or polling
            if (!res.headersSent) {
                res.status(500).json({ status: 'error', message: `Internal server error: ${error.message}` });
            }
        }
    });

    app.post('/hero/configure', async (req, res) => {
        try {
            const config = req.body;
            const response = await sendMessageToWebview({
                command: "configure",
                data: config
            });

            if (response.success) {
                res.status(200).json({ status: 'success', message: response.message });
            } else {
                res.status(500).json({ status: 'error', message: response.message });
            }
        } catch (error: any) {
            console.error('API Error:', error);
            res.status(500).json({ status: 'error', message: `Internal server error: ${error.message}` });
        }
    });

    app.post('/hero/turn_left', async (req, res) => {
        try {
            const response = await sendMessageToWebview({
                command: "turn_left",
                data: null
            });

            await delay(200);

            if (response.success) {
                res.status(200).json({ status: 'success', message: response.message });
            } else {
                res.status(500).json({ status: 'error', message: response.message });
            }
        } catch (error: any) {
            console.error('API Error:', error);
            res.status(500).json({ status: 'error', message: `Internal server error: ${error.message}` });
        }
    });

    app.post('/hero/interact', async (req, res) => {
        try {
            const response = await sendMessageToWebview({
                command: "interact",
                data: null
            });
            if (response.success) {
                res.status(200).json({ status: 'success', message: response.message });
            } else {
                res.status(500).json({ status: 'error', message: response.message });
            }
        } catch (error: any) {
            console.error('API Error:', error);
            res.status(500).json({ status: 'error', message: `Internal server error: ${error.message}` });
        }
    });

    const get_endpoints = [
        'is_collision_in_front',
        'is_facing_north',
        'is_at_goal',
    ];

    get_endpoints.forEach((get_endpoint) => {
        app.get(`/hero/${get_endpoint}`, async (req, res) => {
            try {
                const response = await sendMessageToWebview({
                    command: get_endpoint,
                    data: null
                });
                if (response.success) {
                    res.status(200).json({ status: 'success', message: response.message, result: response.result });
                } else {
                    res.status(500).json({ status: 'error', message: response.message, exception: response.exception });
                }
            } catch (error: any) {
                console.error('API Error:', error);
                res.status(500).json({ status: 'error', message: `Internal server error: ${error.message}` });
            }
        });
    });

    app.post('/level/load', async (req, res) => {
        const level = req.body; 
        
        try {
            if (webviewPanel) {
                const response = await sendMessageToWebview({ command: 'load_level', data: level });
                if (response.success) {
                    res.status(200).json({ status: 'success', message: response.message });
                } else {
                    res.status(500).json({ status: 'error', message: response.message });
                }
            }
        } catch (error: any) {
            console.error('API Error:', error);
            res.status(500).json({ status: 'error', message: `Internal server error: ${error.message}` });
        }
    });

    serverInstance = app.listen(3000, () => console.log('API running on http://localhost:3000'));
}

export function stopServer() {
    if (serverInstance) {
        console.log('Stopping server...');
        
        serverInstance.close((err) => {
            if (err) {
                console.error('Error stopping server:', err);
                return;
            }
            console.log('Server stopped successfully.');
            serverInstance = undefined;
        });
    } else {
        console.log('Server is not running.');
    }
}

async function createWebview(context: vscode.ExtensionContext) {
    webviewPanel = vscode.window.createWebviewPanel(
        'gamePanel',
        'Dungeon Coder - Live View',
        vscode.ViewColumn.Beside,
        {
            enableScripts: true,
            retainContextWhenHidden: true,
            localResourceRoots: [vscode.Uri.joinPath(context.extensionUri, 'game')],
        }
    );

    webviewPanel.webview.onDidReceiveMessage(
        message => {
            switch (message.command) {
                case 'webviewResponse':
                    const requestId = message.requestId;
                    const response = message.response;
                    if (pendingWebviewRequests.has(requestId)) {
                        const resolve = pendingWebviewRequests.get(requestId);
                        if (resolve) {
                            resolve(response);
                            pendingWebviewRequests.delete(requestId);
                        }
                    }
                    return;
            }
        },
        undefined,
        context.subscriptions
    );

    webviewPanel.onDidDispose(
        () => {
            console.log('Webview panel closed. Cleaning up...');    
            stopServer();
        },
        null,
        context.subscriptions
    );

    webviewPanel.webview.html = await getWebviewContent(webviewPanel.webview, context.extensionPath);
}

export function activate(context: vscode.ExtensionContext) {
    const dungeonCoderExtension = vscode.extensions.getExtension('hm-benidiet.vscode-dungeon-coder');
    if (dungeonCoderExtension) {
        const extensionId = dungeonCoderExtension.id; 

        console.log('Dungeon Coder loaded successfully. Have fun coding!');

        let disposable = vscode.commands.registerCommand('vscode-dungeon-coder.startGame', () => {
            vscode.window.showInformationMessage('Enter the dungeon!');
            createWebview(context);  
            startServer((cmd: string) => {
                if (webviewPanel)
                    webviewPanel.webview.postMessage({ command: cmd });
            });
        });

        context.subscriptions.push(disposable);
    }
}

async function getWebviewContent(webview: vscode.Webview, extensionPath: string): Promise<string> {
    const nonce = getNonce();

    const mediaFolderUri = webview.asWebviewUri(
        vscode.Uri.file(path.join(extensionPath, 'game'))
    );

    const htmlFilePath = path.join(extensionPath, 'game', 'index.html');

    let htmlContent: string;
    try {
        htmlContent = fs.readFileSync(htmlFilePath, 'utf8');
    } catch (error: any) { // Type 'any' for error to access 'message'
        throw new Error(`Could not read index.html: ${error.message}`);
    }


    // Replace the placeholders in the HTML with actual values
    htmlContent = htmlContent.replace(/\$\{webview.cspSource\}/g, webview.cspSource);
    htmlContent = htmlContent.replace(/\$\{nonce\}/g, nonce);
    htmlContent = htmlContent.replace(/\$\{gameFolderUri\}/g, mediaFolderUri.toString());

    return htmlContent;
}

function getNonce() {
    let text = '';
    const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    for (let i = 0; i < 32; i++) {
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    }
    return text;
}