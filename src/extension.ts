import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs/promises';
import { readFileSync, constants as fsConstants } from 'fs';
import express from 'express';
import { Server } from 'http';

interface WebviewResponse {
  success: boolean;
  message: string;
  exception: string;
  result: boolean;
}

export class DungeonCoderServer {
  private static instance: DungeonCoderServer;

  private webviewPanel: vscode.WebviewPanel | undefined;
  private serverInstance: Server | undefined;
  private readonly url = '127.0.0.1';
  private readonly port = 3000;
  private turnDelay = 200;
  private currentPaceFactor = 1.0;
  private pendingWebviewRequests = new Map<string, (result: WebviewResponse) => void>();

  // 🔒 Singleton accessor
  public static getInstance(): DungeonCoderServer {
    if (!DungeonCoderServer.instance) {
      DungeonCoderServer.instance = new DungeonCoderServer();
    }
    return DungeonCoderServer.instance;
  }

  private constructor() {
    // private constructor to enforce singleton
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  private async sendMessageToWebview(message: any): Promise<WebviewResponse> {
    if (!this.webviewPanel) {
      vscode.window.showErrorMessage('Webview not open.');
      return { success: false, message: 'Webview not open.', exception: 'WebViewNotOpen', result: false };
    }

    const requestId = Date.now().toString() + Math.random().toString(36).substring(2, 9);
    const messageWithId = { ...message, requestId };

    return new Promise(resolve => {
      this.pendingWebviewRequests.set(requestId, resolve);
      this.webviewPanel!.webview.postMessage(messageWithId);
    });
  }

  public async createWebview(context: vscode.ExtensionContext): Promise<void> {
    if (this.webviewPanel || this.serverInstance) {
      vscode.window.showInformationMessage(`Dungeon Coder is already opened in a tab. Please check.`);
      return;
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
      message => {
        if (message.command === 'webviewResponse') {
          const { requestId, response } = message;
          const resolver = this.pendingWebviewRequests.get(requestId);
          if (resolver) {
            resolver(response);
            this.pendingWebviewRequests.delete(requestId);
          }
        }
      },
      undefined,
      context.subscriptions
    );

    this.webviewPanel.onDidDispose(
      () => {
        console.log('Webview closed, stopping server...');
        this.stopServer();
      },
      null,
      context.subscriptions
    );

    this.webviewPanel.webview.html = await this.getWebviewContent(this.webviewPanel.webview, context.extensionPath);
  }

  public startServer(): void {
    if (this.serverInstance) {
      vscode.window.showInformationMessage(`Server already running on ${this.url}:${this.port}`);
      return;
    }

    const app = express();
    app.use(express.json());

    const pollUntilStopped = async (pollInterval = 10): Promise<void> => {
      while (true) {
        const isMovingResponse = await this.sendMessageToWebview({
          command: 'is_moving',
          data: null,
        });

        if (isMovingResponse.success && !isMovingResponse.result) {
          return;
        }

        await this.delay(pollInterval);
      }
    };

    app.post('/hero/move', async (req, res) => {
      try {
        const moveResponse = await this.sendMessageToWebview({ command: 'move', data: null });
        if (!moveResponse.success) {
          return res.status(500).json({ status: 'error', message: moveResponse.message });
        }

        await pollUntilStopped(10);
        res.status(200).json({ status: 'success', message: 'Hero has stopped moving' });
      } catch (error: any) {
        console.error('API Error:', error);
        res.status(500).json({ status: 'error', message: `Internal error: ${error.message}` });
      }
    });

    

    app.post('/hero/configure', async (req, res) => {
        try {
            const config = req.body;
            const response = await this.sendMessageToWebview({
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

    app.post('/hero/pace', async (req, res) => {
        try {
            const config = req.body;
            const response = await this.sendMessageToWebview({
                command: "set_pace",
                data: config
            });

            if (response.success) {
                this.currentPaceFactor = config.factor;
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
            const response = await this.sendMessageToWebview({
                command: "turn_left",
                data: null
            });

            await this.delay(this.turnDelay / this.currentPaceFactor);

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
            const response = await this.sendMessageToWebview({
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

    app.get('/hero/get_items_at_position', async (req, res) => {
        try {
            const response = await this.sendMessageToWebview({
                command: "get_items_at_position",
                data: null
            });
            if (response.success) {
                res.status(200).json({ status: 'success', message: response.message, result: response.result });
            } else {
                res.status(500).json({ status: 'error', message: response.message, result: [] });
            }
        } catch (error: any) {
            console.error('API Error:', error);
            res.status(500).json({ status: 'error', message: `Internal server error: ${error.message}`, result: [] });
        }
    });

    app.get('/hero/inventory', async (req, res) => {
        try {
            const response = await this.sendMessageToWebview({
                command: "get_inventory",
                data: null
            });
            if (response.success) {
                res.status(200).json({ status: 'success', message: response.message, result: response.result });
            } else {
                res.status(500).json({ status: 'error', message: response.message, result: []});
            }
        } catch (error: any) {
            console.error('API Error:', error);
            res.status(500).json({ status: 'error', message: `Internal server error: ${error.message}`, result: [] });
        }
    });

    app.post('/hero/pickup', async (req, res) => {
        try {
            const data = req.body;
            const response = await this.sendMessageToWebview({
                command: "pickup",
                data: data
            });
            if (response.success) {
                res.status(200).json({ status: 'success', message: response.message, result: response.result });
            } else {
                res.status(500).json({ status: 'error', message: response.message, result: []});
            }
        } catch (error: any) {
            console.error('API Error:', error);
            res.status(500).json({ status: 'error', message: `Internal server error: ${error.message}`, result: [] });
        }
    });

    app.post('/hero/drop', async (req, res) => {
        try {
            const data = req.body;
            const response = await this.sendMessageToWebview({
                command: "drop",
                data: data
            });
            if (response.success) {
                res.status(200).json({ status: 'success', message: response.message, result: response.result });
            } else {
                res.status(500).json({ status: 'error', message: response.message, result: []});
            }
        } catch (error: any) {
            console.error('API Error:', error);
            res.status(500).json({ status: 'error', message: `Internal server error: ${error.message}`, result: [] });
        }
    });


    const get_endpoints = [
        'is_collision_in_front',
        'is_facing_north',
        'is_at_goal',
        'is_torch_in_front',
        'is_switch_in_front',
        'is_abyss_in_front'
    ];

    get_endpoints.forEach((get_endpoint) => {
        app.get(`/hero/${get_endpoint}`, async (req, res) => {
            try {
                const response = await this.sendMessageToWebview({
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
            if (this.webviewPanel) {
                const response = await this.sendMessageToWebview({ command: 'load_level', data: level });
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

    this.serverInstance = app.listen(this.port, this.url, () => {
      console.log(`API running on ${this.url}:${this.port}`);
    });

    this.serverInstance.on('error', err => {
      if ((err as any).code === 'EADDRINUSE') {
        vscode.window.showErrorMessage(
          `Port ${this.port} already in use. Another Dungeon Coder instance might be running.`
        );
        this.stopServer();
        this.webviewPanel?.dispose();
      } else {
        vscode.window.showErrorMessage(`Unexpected server error: ${(err as Error).message}`);
        this.webviewPanel?.dispose();
      }
    });
  }

  public stopServer(): void {
    if (this.serverInstance) {
      console.log('Stopping server...');
      this.serverInstance.close(err => {
        if (err) {
          console.error('Error stopping server:', err);
        } else {
          console.log('Server stopped.');
          this.serverInstance = undefined;
        }
      });
    }
  }

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

    htmlContent = htmlContent
      .replace('<!-- CSP -->', csp)
      .replace(/\$\{webview.cspSource\}/g, webview.cspSource)
      .replace(/\$\{nonce\}/g, nonce)
      .replace(/\$\{gameFolderUri\}/g, mediaFolderUri.toString());

    return htmlContent;
  }

  private getNonce(): string {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    return Array.from({ length: 32 }, () => chars[Math.floor(Math.random() * chars.length)]).join('');
  }
}

// ------------------------------------------------------------
// VSCode activate function using the Singleton
// ------------------------------------------------------------
export function activate(context: vscode.ExtensionContext) {
  const server = DungeonCoderServer.getInstance();

  const startGame = vscode.commands.registerCommand('vscode-dungeon-coder.startGame', async () => {
    vscode.window.showInformationMessage('Enter the dungeon!');
    await server.createWebview(context);
    server.startServer();
  });

  context.subscriptions.push(startGame);
}
