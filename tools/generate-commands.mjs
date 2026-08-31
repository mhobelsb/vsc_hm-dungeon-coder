// Generates game/src/commands.js - the RPC method registry shared by the
// webview's dispatch table, the extension host's route registration, and
// the standalone dev server - from api/openapi.yaml's operationIds (plus
// any x-internal-commands with no HTTP surface). Run via `npm run generate`.

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { load as loadYaml } from 'js-yaml';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const specPath = path.join(__dirname, '..', 'api', 'openapi.yaml');
const outPath = path.join(__dirname, '..', 'game', 'src', 'commands.js');

const spec = loadYaml(fs.readFileSync(specPath, 'utf8'));

const httpMethods = ['get', 'post', 'put', 'delete', 'patch', 'options', 'head'];
const operationIds = [];

for (const [route, pathItem] of Object.entries(spec.paths ?? {})) {
    for (const method of httpMethods) {
        const operation = pathItem[method];
        if (!operation) continue;
        if (!operation.operationId) {
            throw new Error(`Missing operationId for ${method.toUpperCase()} ${route} in api/openapi.yaml`);
        }
        operationIds.push(operation.operationId);
    }
}

const internalOnly = spec['x-internal-commands'] ?? [];
const allCommands = [...operationIds, ...internalOnly];

const duplicates = allCommands.filter((id, index) => allCommands.indexOf(id) !== index);
if (duplicates.length > 0) {
    throw new Error(`Duplicate command name(s) in api/openapi.yaml: ${[...new Set(duplicates)].join(', ')}`);
}

const toKey = operationId => operationId.toUpperCase();

const entries = allCommands
    .map(id => `    ${toKey(id)}: ${JSON.stringify(id)},`)
    .join('\n');

const output = `// GENERATED FILE - do not edit by hand.
// Source: api/openapi.yaml (paths[*].operationId, plus x-internal-commands).
// Regenerate with: npm run generate
//
// Single source of truth for the RPC method names shared by the Express API
// (src/extension.ts), the webview command dispatcher (game/src/script.js),
// and the standalone dev server (tools/dev-server.mjs). Plain ES module so
// it can be loaded unmodified by the browser (webview) and by Node/webpack.
export const COMMANDS = Object.freeze({
${entries}
});

export const COMMAND_LIST = Object.freeze(Object.values(COMMANDS));
`;

fs.writeFileSync(outPath, output);
console.log(`Generated ${path.relative(process.cwd(), outPath)} from ${allCommands.length} command(s) in api/openapi.yaml.`);
