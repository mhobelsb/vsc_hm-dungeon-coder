import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs/promises';
import { readFileSync, constants as fsConstants } from 'fs';
import express, { Application, Request, Response } from 'express';
import { Server } from 'http';

interface WebviewResponse {
  success: boolean;
  message: string;
  exception?: string;
  result?: any;
}

/**
 * DungeonCoderServer – Singleton handling Express API + VS Code Webview.
 */
export class DungeonCoderServer {
  private static instance: DungeonCoderServer;
  private webviewPanel?: vscode.WebviewPanel;
  private serverInstance?: Server;
  private currentPaceFactor = 1.0;
  private turnDelay = 200;
  private readonly url = '127.0.0.1';
  private readonly port = 3000;
  private readonly pendingWebviewRequests = new Map<string, (result: WebviewResponse) => void>();

  private constructor() {}

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

  /** Send message to webview and await reply */
  private async sendMessageToWebview(message: any): Promise<WebviewResponse> {
    if (!this.webviewPanel) {
      vscode.window.showErrorMessage('Webview not open.');
      return { success: false, message: 'Webview not open.', exception: 'WebViewNotOpen' };
    }

    const requestId = Date.now().toString() + Math.random().toString(36).substring(2, 9);
    const messageWithId = { ...message, requestId };

    return new Promise(resolve => {
      this.pendingWebviewRequests.set(requestId, resolve);
      this.webviewPanel!.webview.postMessage(messageWithId);
    });
  }

  /** Unified Express route registration helper */
  private registerRoute(
    app: Application,
    method: 'get' | 'post',
    route: string,
    command: string,
    options?: {
      includeBody?: boolean;
      onSuccess?: (response: WebviewResponse, req: Request) => void | Promise<void>;
    }
  ) {
    (app as any)[method](route, async (req: Request, res: Response) => {
      try {
        const data = options?.includeBody ? req.body : null;
        const response = await this.sendMessageToWebview({ command, data });

        if (!response.success) {
          this.sendApiResponse(res, response);
          return;
        }

        if (options?.onSuccess) {
          await options.onSuccess(response, req);
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

  /** Poll helper for move() until hero stops */
  private async pollUntilStopped(pollInterval = 10): Promise<void> {
    while (true) {
      const isMovingResponse = await this.sendMessageToWebview({
        command: 'is_moving',
        data: null,
      });

      if (isMovingResponse.success && !isMovingResponse.result) return;
      await this.delay(pollInterval);
    }
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
  public startServer() {
    if (this.serverInstance) {
      vscode.window.showErrorMessage("It seems like Dungeon Coder is already running in a different tab. Please check!");
      return false;
    }

    const app = express();
    app.use(express.json());

    // --- Hero Movement ---
    this.registerRoute(app, 'post', '/hero/move', 'move', {
      onSuccess: async () => {
        await this.pollUntilStopped(10);
      },
    });

    this.registerDelayedCommandRoute(app, '/hero/turn_left', 'turn_left', this.turnDelay);

    // --- Configuration ---
    this.registerRoute(app, 'post', '/hero/configure', 'configure', { includeBody: true });
    this.registerRoute(app, 'post', '/hero/pace', 'set_pace', {
      includeBody: true,
      onSuccess: async (_, req) => {
        const factor = req.body?.factor;
        if (typeof factor === 'number') {
          this.currentPaceFactor = factor;
          console.log(`Updated current pace factor: ${factor}`);
        }
      },
    });

    // --- Interaction ---
    this.registerRoute(app, 'post', '/hero/interact', 'interact');
    this.registerRoute(app, 'post', '/hero/pickup', 'pickup', { includeBody: true });
    this.registerRoute(app, 'post', '/hero/drop', 'drop', { includeBody: true });

    // --- Queries ---
    this.registerRoute(app, 'get', '/hero/get_items_at_position', 'get_items_at_position');
    this.registerRoute(app, 'get', '/hero/inventory', 'get_inventory');
    this.registerRoute(app, 'post', '/level/load', 'load_level', { includeBody: true });

    [
      'is_collision_in_front',
      'is_facing_north',
      'is_at_goal',
      'is_torch_in_front',
      'is_switch_in_front',
      'is_abyss_in_front',
    ].forEach(endpoint =>
      this.registerRoute(app, 'get', `/hero/${endpoint}`, endpoint)
    );

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
      message => {
        if (message.command === 'webviewResponse') {
          const requestId = message.requestId;
          const response = message.response;
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
    ret = ret && server.startServer();
    if (ret) {
        vscode.window.showInformationMessage('Enter the dungeon!');
    } else {
        vscode.window.showErrorMessage("Error: Dungeon Coder could not be started.")
    }
  });

  context.subscriptions.push(startGame);
}

