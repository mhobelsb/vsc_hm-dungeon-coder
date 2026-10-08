import * as assert from 'assert';
import { mkdtempSync, readFileSync, writeFileSync } from 'fs';
import * as os from 'os';
import * as path from 'path';
import * as vscode from 'vscode';

// The workspace is test-fixtures/side-by-side/exercise (.vscode-test.mjs). Its
// .vscode/settings.json names the demo pack by a relative path and sets the port.
const PORT = 3197;
const DEMO_PACK = path.resolve(__dirname, '..', '..', 'packs', 'demo');

async function loadLevel(level: object): Promise<{ status: number; body: string }> {
    const response = await fetch(`http://127.0.0.1:${PORT}/level/load`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(level),
    });
    return { status: response.status, body: await response.text() };
}

/** Retries while the game in the webview is still starting. */
async function loadLevelWhenReady(level: object): Promise<{ status: number; body: string }> {
    let last = { status: 0, body: 'no answer' };
    for (let attempt = 0; attempt < 40; attempt++) {
        try {
            last = await loadLevel(level);
            if (last.status === 200 || last.body.includes('Missing tileset')) {
                return last;
            }
        } catch (err) {
            last = { status: 0, body: String(err) };
        }
        await new Promise(resolve => setTimeout(resolve, 500));
    }
    return last;
}

suite('Asset pack next to the exercise folder (P3)', () => {
    suiteSetup(async () => {
        await vscode.commands.executeCommand('vscode-dungeon-coder.startGame');
    });

    test('the relative path starts at the workspace folder', () => {
        const extension = vscode.extensions.all.find(e => e.id === 'hm-benidiet.vscode-dungeon-coder');
        assert.ok(extension, 'extension not found');
        const settings = vscode.workspace.getConfiguration('dungeonCoder').get<string[]>('assetPacks');
        assert.deepStrictEqual(settings, ['../../../packs/demo']);
        const workspace = vscode.workspace.workspaceFolders![0].uri.fsPath;
        assert.strictEqual(path.resolve(workspace, settings![0]), DEMO_PACK);
    });

    test('a level of the pack loads', async () => {
        const level = JSON.parse(readFileSync(path.join(DEMO_PACK, 'levels', 'demo_gang.json'), 'utf8'));
        const result = await loadLevelWhenReady(level);
        assert.strictEqual(result.status, 200, result.body);
    });

    test('a tileset no pack has is refused (control)', async () => {
        const level = JSON.parse(readFileSync(path.join(DEMO_PACK, 'levels', 'demo_gang.json'), 'utf8'));
        level.tilesets[0].source = '../tilesets/kein_pack_hat_das.json';
        const result = await loadLevelWhenReady(level);
        assert.notStrictEqual(result.status, 200);
        assert.ok(result.body.includes('kein_pack_hat_das.json'), result.body);
    });
});

suite('Asset packs found without a setting', () => {
    test('a dungeon-coder-assets with a pack.json in, above or directly inside the opened folder, nearest first', () => {
        const { findAssetPacks } = require('../extension') as typeof import('../extension');
        const { mkdirSync } = require('fs') as typeof import('fs');
        const root = mkdtempSync(path.join(os.tmpdir(), 'dc-find-'));
        const pack = (folder: string, withManifest = true) => {
            mkdirSync(folder, { recursive: true });
            if (withManifest) {
                writeFileSync(path.join(folder, 'pack.json'), '{"name": "x"}');
            }
            return folder;
        };
        const far = pack(path.join(root, 'dungeon-coder-assets'));
        const near = pack(path.join(root, 'semester', 'dungeon-coder-assets'));
        pack(path.join(root, 'semester', 'loesungen', 'dungeon-coder-assets'), false);   // no pack.json: not a pack
        const opened = path.join(root, 'semester', 'loesungen', 'dc-03');
        mkdirSync(opened, { recursive: true });
        assert.deepStrictEqual(findAssetPacks(opened, ['dungeon-coder-assets']), [near, far]);
        // the folder holding the repo is opened: the pack lies one level down
        const holder = path.join(root, 'holder');
        const inside = pack(path.join(holder, 'repo', 'dungeon-coder-assets'));
        assert.deepStrictEqual(findAssetPacks(holder, ['dungeon-coder-assets']), [far, inside]);
        assert.deepStrictEqual(findAssetPacks(opened, ['other-name']), []);
    });
});

suite('A pack named in the settings but not cloned', () => {
    test('is reported as missing', () => {
        const { missingFolders } = require('../extension') as typeof import('../extension');
        const workspace = vscode.workspace.workspaceFolders![0].uri.fsPath;
        const notCloned = path.join(workspace, '..', 'dungeon-coder-assets');
        assert.deepStrictEqual(missingFolders([DEMO_PACK, notCloned]), [notCloned]);
    });
});

suite('Pack manifest (G6)', () => {
    test('a pack that needs a newer engine is named, one without "engine" fits every version', () => {
        const { versionAtLeast, packsNeedingNewerEngine } = require('../extension') as typeof import('../extension');
        assert.ok(versionAtLeast('0.10.0', '0.9.3') && versionAtLeast('1.0', '1.0.0') && !versionAtLeast('0.1.0', '0.2.0'));
        const folder = mkdtempSync(path.join(os.tmpdir(), 'dc-pack-'));
        writeFileSync(path.join(folder, 'pack.json'), JSON.stringify({ name: 'future', engine: '99.0.0' }));
        assert.deepStrictEqual(packsNeedingNewerEngine([DEMO_PACK, folder], '0.1.0'), ['future (needs 99.0.0)']);
    });
});

suite('Versions (G4)', () => {
    test('GET /version reports the extension version and the API version', async () => {
        const response = await fetch(`http://127.0.0.1:${PORT}/version`);
        const body = await response.json() as { result: { extension: string; api: string } };
        const pkg = JSON.parse(readFileSync(path.resolve(__dirname, '..', '..', 'package.json'), 'utf8'));
        assert.strictEqual(response.status, 200);
        assert.strictEqual(body.result.extension, pkg.version);
        assert.strictEqual(body.result.api, pkg.version);
    });

    test('a copied Python API is recognised: none, an old copy, a versioned copy', () => {
        const { copiedApiVersion } = require('../extension') as typeof import('../extension');
        const { mkdtempSync, mkdirSync, writeFileSync } = require('fs') as typeof import('fs');
        const os = require('os') as typeof import('os');
        const none = mkdtempSync(path.join(os.tmpdir(), 'dc-'));
        const old = mkdtempSync(path.join(os.tmpdir(), 'dc-'));
        mkdirSync(path.join(old, 'dungeoncoder'));
        writeFileSync(path.join(old, 'dungeoncoder', '__init__.py'), 'from .dungeoncoder import Game, Hero\n');
        const current = mkdtempSync(path.join(os.tmpdir(), 'dc-'));
        mkdirSync(path.join(current, 'dungeoncoder'));
        writeFileSync(path.join(current, 'dungeoncoder', '__init__.py'), '__version__ = "0.1.0"\n');
        assert.strictEqual(copiedApiVersion(none), undefined);
        assert.strictEqual(copiedApiVersion(old), 'old');
        assert.strictEqual(copiedApiVersion(current), '0.1.0');
    });
});
