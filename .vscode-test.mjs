import { defineConfig } from '@vscode/test-cli';
import { existsSync } from 'node:fs';
import { homedir, tmpdir } from 'node:os';
import { join } from 'node:path';

// The test VS Code (~300 MB) and its profile stay out of the repository folder, which
// may sit in a synced folder: `npm run test:download` puts VS Code into ~/.cache/vscode-test.
const VERSION = '1.140.0';
// (the macOS binary is called Code in newer versions, Electron in older ones)
const cached = ['Code', 'Electron'].map(name => join(homedir(), '.cache', 'vscode-test',
	`vscode-darwin-arm64-${VERSION}`, 'Visual Studio Code.app', 'Contents', 'MacOS', name)).find(existsSync);
const executable = process.env.DC_VSCODE_TEST_EXECUTABLE || cached;
const profile = join(tmpdir(), 'dungeon-coder-vscode-test');

export default defineConfig({
	files: 'out/test/**/*.test.js',
	version: VERSION,
	...(executable ? { useInstallation: { fromPath: executable } } : {}),
	// an exercise folder with an asset pack in its .vscode/settings.json (asset-packs.test.ts)
	workspaceFolder: './test-fixtures/side-by-side/exercise',
	launchArgs: [`--user-data-dir=${join(profile, 'user-data')}`, `--extensions-dir=${join(profile, 'extensions')}`],
	mocha: { timeout: 60000 },
});
