import * as assert from 'assert';
import * as vscode from 'vscode';

// The legacy extension (Benedikt Dietrich's Dungeon Coder 0.1.0, hm-benidiet.vscode-dungeon-coder) may stay
// installed next to this one: own extension ID, own command IDs. The test runs only when the legacy
// extension is in the test profile (RELEASING.md says how to put it there); otherwise it is skipped.
suite('Next to the legacy extension', () => {
    test('both activate and both sets of commands are registered', async function () {
        const legacy = vscode.extensions.getExtension('hm-benidiet.vscode-dungeon-coder');
        if (!legacy) {
            this.skip();
        }
        const current = vscode.extensions.getExtension('hm-dungeon-coder.dungeon-coder');
        assert.ok(current, 'this extension is installed');
        await current.activate();
        await legacy!.activate();
        const commands = await vscode.commands.getCommands(true);
        for (const id of ['hm-dungeon-coder.startGame', 'hm-dungeon-coder.copyPythonAPI',
            'vscode-dungeon-coder.startGame', 'vscode-dungeon-coder.copyPythonAPI']) {
            assert.ok(commands.includes(id), `${id} is registered`);
        }
    });
});
