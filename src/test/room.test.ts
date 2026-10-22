import * as assert from 'assert';
import * as vscode from 'vscode';

suite('Live game in the room', () => {
    test('the command that opens the game to the room is there', async () => {
        await vscode.extensions.getExtension('hm-benidiet.vscode-dungeon-coder')?.activate();
        const commands = await vscode.commands.getCommands(true);
        assert.ok(commands.includes('vscode-dungeon-coder.openToRoom'));
    });

    test('the addresses to give the teams are IPv4 addresses, never loopback', () => {
        const { lanAddresses } = require('../extension') as typeof import('../extension');
        const addresses = lanAddresses();
        assert.ok(Array.isArray(addresses));
        assert.ok(addresses.every(a => /^\d+\.\d+\.\d+\.\d+$/.test(a) && !a.startsWith('127.')));
    });

    test('opened to the room: other computers may join, but not load levels', async function () {
        this.timeout(20000);
        const addresses = await vscode.commands.executeCommand<string[]>('vscode-dungeon-coder.openToRoom');
        assert.ok(Array.isArray(addresses));
        if (addresses.length === 0) {
            this.skip();                    // a machine without a network: nothing to reach
        }
        const base = addresses[0];
        const version = await fetch(`${base}/version`);
        assert.strictEqual(version.status, 200);
        const load = await fetch(`${base}/level/load`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
        const answer = await load.json() as { message: string };
        assert.match(answer.message, /referee/);
        const local = await fetch(`http://127.0.0.1:${new URL(base).port}/version`);
        assert.strictEqual(local.status, 200);
    });

    test('the distance of is_enemy_in_front reaches the game with the body', () => {
        const { withQuery } = require('../extension') as typeof import('../extension');
        assert.strictEqual(withQuery(null, {}), null);
        assert.deepStrictEqual(withQuery({ hero: 1 }, { distance: '2' }), { hero: 1, distance: 2 });
    });
});
