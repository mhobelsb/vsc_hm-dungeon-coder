import * as assert from 'assert';
import { readFileSync } from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';

// The workspace is test-fixtures/side-by-side/exercise (.vscode-test.mjs), port 3197.
const PORT = 3197;

suite('Side panel (DC-T2h)', () => {
    test('level files: level/, levels/ and secret/ folders, no traces', () => {
        const { isLevelPath } = require('../panel') as typeof import('../panel');
        assert.ok(isLevelPath('/x/ex/levels/a.json') && isLevelPath('C:\\x\\level\\b.txt') && isLevelPath('/x/secret/s1.json'));
        assert.ok(!isLevelPath('/x/ex/tilesets/a.json') && !isLevelPath('/x/levels/a.trace.json') && !isLevelPath('/x/levels/a.py'));
    });

    test('the status bar line', () => {
        const { statusText } = require('../panel') as typeof import('../panel');
        assert.strictEqual(statusText(null), '$(game) Dungeon Coder');
        assert.strictEqual(statusText({ moves: 3, turns: 1, bumps: 0, moves_left: null, level_complete: false }),
            '$(game) 3 moves · 1 turns');
        assert.strictEqual(statusText({ moves: 3, turns: 1, bumps: 2, moves_left: 5, level_complete: true }),
            '$(game) 3 moves · 1 turns · 2 bumps · 5 left · $(pass) done');
    });

    test('the hero index of a co-op level reaches the game with the body', () => {
        const { withHero } = require('../extension') as typeof import('../extension');
        assert.strictEqual(withHero(null, undefined), null);
        assert.deepStrictEqual(withHero(null, '2'), { hero: 2 });
        assert.deepStrictEqual(withHero({ name: 'Sweets' }, '1'), { name: 'Sweets', hero: 1 });
    });

    test('"Load level" loads a JSON level into the game', async () => {
        const demo = path.resolve(__dirname, '..', '..', 'packs', 'demo', 'levels', 'demo_gang.json');
        await vscode.commands.executeCommand('hm-dungeon-coder.loadLevel', vscode.Uri.file(demo));
        const response = await fetch(`http://127.0.0.1:${PORT}/game/statistics`);
        const body = await response.json() as { result: { moves: number; heroes: number } };
        assert.strictEqual(response.status, 200);
        assert.strictEqual(body.result.moves, 0);
        const level = JSON.parse(readFileSync(demo, 'utf8'));
        assert.ok(level.layers.length > 0);
    });
});
