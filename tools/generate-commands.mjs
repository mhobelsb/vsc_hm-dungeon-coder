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
const routes = [];      // the HTTP surface, shared by src/extension.ts and tools/dev-server.mjs

for (const [route, pathItem] of Object.entries(spec.paths ?? {})) {
    for (const method of httpMethods) {
        const operation = pathItem[method];
        if (!operation) {
            continue;
        }
        if (!operation.operationId) {
            throw new Error(`Missing operationId for ${method.toUpperCase()} ${route} in api/openapi.yaml`);
        }
        operationIds.push(operation.operationId);
        routes.push({ method, path: route, command: operation.operationId, body: Boolean(operation.requestBody) });
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

// Every HTTP route: method, path, RPC command, and whether the request has a JSON body.
// Both servers register exactly these; special behaviour (e.g. waiting for a step) is added per command.
export const ROUTES = Object.freeze(${JSON.stringify(routes, null, 4).replace(/\n/g, '\n')});
`;

fs.writeFileSync(outPath, output);

// Ambient TypeScript declaration for the same registry, so extension.ts can
// import game/src/commands.js without allowJs. Generated from the same list,
// so it can't drift out of sync with the spec.
const dtsPath = path.join(__dirname, '..', 'src', 'commands.d.ts');
const dtsEntries = allCommands
    .map(id => `        readonly ${toKey(id)}: ${JSON.stringify(id).replace(/"/g, "'")};`)
    .join('\n');
fs.writeFileSync(dtsPath, `// GENERATED FILE - do not edit by hand.
// Source: api/openapi.yaml, via tools/generate-commands.mjs (npm run generate).
//
// Ambient typing for the plain-JS, generated config modules under game/src/
// (commands.js, api-config.js), so extension.ts can import them without
// pulling the untyped game/ tree into TypeScript's compilation graph (no
// \`allowJs\`).
declare module '*commands.js' {
    export const COMMANDS: {
${dtsEntries}
    };
    export const COMMAND_LIST: readonly string[];
    export const ROUTES: readonly { method: 'get' | 'post'; path: string; command: string; body: boolean }[];
}

declare module '*api-config.js' {
    export const API_HOST: string;
    export const API_PORT: number;
    export const API_BASE_URL: string;
}
`);
console.log(`Generated ${path.relative(process.cwd(), outPath)} from ${allCommands.length} command(s) in api/openapi.yaml.`);
