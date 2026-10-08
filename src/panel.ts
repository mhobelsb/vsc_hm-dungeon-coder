import * as vscode from 'vscode';
import * as path from 'path';
import { readFileSync } from 'fs';

/**
 * The Dungeon Coder side panel (DC-T2h): the levels of the open exercise in the Explorer, one
 * click loads a level into the game; "run on all levels" for the open program (in the simulator,
 * `python -m dungeoncoder variants`); replaying a trace; a status bar item with the counters.
 */

/** Folders whose JSON and text files are levels: level/ and levels/ (and secret/ for tutors). */
const LEVEL_GLOB = '**/{level,levels,secret}/*.{json,txt}';
const EXCLUDE_GLOB = '**/{node_modules,.venv,venv,dungeoncoder,.git}/**';

/** A path is a level file if it lies in a level folder and is a .json or .txt file. */
export function isLevelPath(file: string): boolean {
    const parts = file.split(/[\\/]/);
    const folder = parts[parts.length - 2] ?? '';
    return ['level', 'levels', 'secret'].includes(folder) && /\.(json|txt)$/i.test(file)
        && !file.endsWith('.trace.json');
}

/** A short line for the status bar from the game's statistics (api/openapi.yaml, Statistics). */
export function statusText(stats: any): string {
    if (!stats) {
        return '$(game) Dungeon Coder';
    }
    let text = `$(game) ${stats.moves} moves · ${stats.turns} turns`;
    if (stats.bumps) {
        text += ` · ${stats.bumps} bumps`;
    }
    if (stats.moves_left !== null && stats.moves_left !== undefined) {
        text += ` · ${stats.moves_left} left`;
    }
    if (stats.level_complete) {
        text += ' · $(pass) done';
    } else if (stats.game_over) {
        text += ' · $(error) lost';
    }
    return text;
}

type Folder = { kind: 'folder'; uri: vscode.Uri; files: vscode.Uri[] };
type File = { kind: 'file'; uri: vscode.Uri };
type Node = Folder | File;

class LevelTree implements vscode.TreeDataProvider<Node> {
    private readonly changed = new vscode.EventEmitter<void>();
    readonly onDidChangeTreeData = this.changed.event;

    refresh() {
        this.changed.fire();
    }

    async getChildren(node?: Node): Promise<Node[]> {
        if (node?.kind === 'folder') {
            return node.files.map(uri => ({ kind: 'file', uri }));
        }
        if (node) {
            return [];
        }
        const files = (await vscode.workspace.findFiles(LEVEL_GLOB, EXCLUDE_GLOB, 2000))
            .filter(uri => isLevelPath(uri.fsPath))
            .sort((a, b) => a.fsPath.localeCompare(b.fsPath));
        const folders = new Map<string, Folder>();
        for (const uri of files) {
            const dir = path.dirname(uri.fsPath);
            if (!folders.has(dir)) {
                folders.set(dir, { kind: 'folder', uri: vscode.Uri.file(dir), files: [] });
            }
            folders.get(dir)!.files.push(uri);
        }
        return [...folders.values()];
    }

    getTreeItem(node: Node): vscode.TreeItem {
        if (node.kind === 'folder') {
            const item = new vscode.TreeItem(vscode.workspace.asRelativePath(node.uri), vscode.TreeItemCollapsibleState.Expanded);
            item.iconPath = vscode.ThemeIcon.Folder;
            return item;
        }
        const item = new vscode.TreeItem(path.basename(node.uri.fsPath), vscode.TreeItemCollapsibleState.None);
        item.resourceUri = node.uri;
        item.contextValue = 'dungeonCoderLevel';
        item.tooltip = `Load into the game: ${vscode.workspace.asRelativePath(node.uri)}`;
        item.command = { command: 'hm-dungeon-coder.loadLevel', title: 'Load level', arguments: [node.uri] };
        return item;
    }
}

/** The Python that runs the student's programs: the Python extension's choice, else python3/python. */
async function pythonCommand(): Promise<string> {
    try {
        const chosen = await vscode.commands.executeCommand<string>('python.interpreterPath',
            { workspaceFolder: vscode.workspace.workspaceFolders?.[0]?.uri.fsPath });
        if (chosen) {
            return `"${chosen}"`;
        }
    } catch {
        // no Python extension: the PATH's Python
    }
    return process.platform === 'win32' ? 'python' : 'python3';
}

function quote(file: string): string {
    return `"${vscode.workspace.asRelativePath(file, false)}"`;
}

let terminal: vscode.Terminal | undefined;

/** Runs `python -m dungeoncoder ...` in the panel's own terminal (in the workspace folder). */
async function runInTerminal(args: string) {
    if (!terminal || terminal.exitStatus !== undefined) {
        terminal = vscode.window.createTerminal({ name: 'Dungeon Coder', cwd: vscode.workspace.workspaceFolders?.[0]?.uri });
    }
    terminal.show(true);
    terminal.sendText(`${await pythonCommand()} -m dungeoncoder ${args}`);
}

export interface GameAccess {
    /** Starts the game if needed; false if it could not start. */
    ensureRunning(): Promise<boolean>;
    /** Loads a Tiled level (JSON) into the game: the game's message. */
    loadLevel(level: object): Promise<{ success: boolean; message: string }>;
    /** Called with the game's statistics after every action of a program. */
    onStatistics(listener: (stats: any) => void): void;
}

export function registerPanel(context: vscode.ExtensionContext, game: GameAccess) {
    const tree = new LevelTree();
    context.subscriptions.push(vscode.window.registerTreeDataProvider('dungeonCoder.levels', tree));
    const watcher = vscode.workspace.createFileSystemWatcher(LEVEL_GLOB);
    watcher.onDidCreate(() => tree.refresh());
    watcher.onDidDelete(() => tree.refresh());
    context.subscriptions.push(watcher);

    const status = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 50);
    status.text = statusText(null);
    status.tooltip = 'Dungeon Coder: counters of the current level (Game.get_statistics())';
    context.subscriptions.push(status);
    game.onStatistics(stats => {
        status.text = statusText(stats);
        status.show();
    });

    context.subscriptions.push(
        vscode.commands.registerCommand('hm-dungeon-coder.refreshLevels', () => tree.refresh()),
        vscode.commands.registerCommand('hm-dungeon-coder.loadLevel', async (uri?: vscode.Uri) => {
            uri = uri ?? vscode.window.activeTextEditor?.document.uri;
            if (!uri) {
                return;
            }
            if (!(await game.ensureRunning())) {
                return;
            }
            if (uri.fsPath.endsWith('.txt')) {
                // a text map is built in Python (dungeoncoder/asciimap.py), with the student's packs
                await runInTerminal(`load ${quote(uri.fsPath)}`);
                return;
            }
            try {
                const answer = await game.loadLevel(JSON.parse(readFileSync(uri.fsPath, 'utf8')));
                if (!answer.success) {
                    vscode.window.showErrorMessage(`Dungeon Coder: ${answer.message}`);
                }
            } catch (err: any) {
                vscode.window.showErrorMessage(`Dungeon Coder: ${path.basename(uri.fsPath)} is not a level (${err.message}).`);
            }
        }),
        vscode.commands.registerCommand('hm-dungeon-coder.runOnAllLevels', async (uri?: vscode.Uri) => {
            uri = uri ?? vscode.window.activeTextEditor?.document.uri;
            if (!uri || !uri.fsPath.endsWith('.py')) {
                vscode.window.showErrorMessage('Dungeon Coder: open the Python program to run first.');
                return;
            }
            const levels = (await vscode.workspace.findFiles(LEVEL_GLOB, EXCLUDE_GLOB, 2000))
                .filter(level => isLevelPath(level.fsPath))
                .sort((a, b) => a.fsPath.localeCompare(b.fsPath));
            const near = levels.filter(level => path.dirname(path.dirname(level.fsPath)) === path.dirname(uri!.fsPath));
            const picked = await vscode.window.showQuickPick(
                levels.map(level => ({ label: vscode.workspace.asRelativePath(level), picked: near.includes(level), level })),
                { canPickMany: true, title: `Run ${path.basename(uri.fsPath)} on these levels (in the simulator)` });
            if (!picked || picked.length === 0) {
                return;
            }
            await vscode.workspace.saveAll(false);
            await runInTerminal(`variants ${quote(uri.fsPath)} ${picked.map(p => quote(p.level.fsPath)).join(' ')} --traces .dungeoncoder-traces`);
        }),
        vscode.commands.registerCommand('hm-dungeon-coder.replayTrace', async (uri?: vscode.Uri) => {
            uri = uri ?? vscode.window.activeTextEditor?.document.uri;
            if (!uri || !uri.fsPath.endsWith('.json')) {
                vscode.window.showErrorMessage('Dungeon Coder: choose a trace file (*.trace.json).');
                return;
            }
            if (await game.ensureRunning()) {
                await runInTerminal(`replay ${quote(uri.fsPath)}`);
            }
        }),
    );
}
