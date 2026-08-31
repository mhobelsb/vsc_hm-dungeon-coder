// Generates the API host/port/base-URL constants shared by extension.ts,
// tools/dev-server.mjs, and dungeoncoder.py, from api/openapi.yaml's
// servers[0].url - the single source of truth for where the REST API lives.
// Run via `npm run generate`.

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { load as loadYaml } from 'js-yaml';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const specPath = path.join(__dirname, '..', 'api', 'openapi.yaml');

const spec = loadYaml(fs.readFileSync(specPath, 'utf8'));
const serverUrl = spec.servers?.[0]?.url;
if (!serverUrl) {
    throw new Error('api/openapi.yaml has no servers[0].url to generate API connection config from.');
}

const parsedUrl = new URL(serverUrl);
const host = parsedUrl.hostname;
const port = Number(parsedUrl.port || (parsedUrl.protocol === 'https:' ? 443 : 80));
const baseUrl = parsedUrl.origin;

const jsOutPath = path.join(__dirname, '..', 'game', 'src', 'api-config.js');
fs.writeFileSync(jsOutPath, `// GENERATED FILE - do not edit by hand.
// Source: api/openapi.yaml (servers[0].url).
// Regenerate with: npm run generate
//
// Consumed by src/extension.ts and tools/dev-server.mjs - the two places
// that actually bind an Express server to a host/port.
export const API_HOST = ${JSON.stringify(host)};
export const API_PORT = ${port};
export const API_BASE_URL = ${JSON.stringify(baseUrl)};
`);

const pyOutPath = path.join(__dirname, '..', 'api', 'python', 'dungeoncoder', '_api_config.py');
fs.writeFileSync(pyOutPath, `# GENERATED FILE - do not edit by hand.
# Source: api/openapi.yaml (servers[0].url).
# Regenerate with: npm run generate
HOST = ${JSON.stringify(host)}
PORT = ${port}
BASE_URL = ${JSON.stringify(baseUrl)}
`);

console.log(`Generated ${path.relative(process.cwd(), jsOutPath)} and ${path.relative(process.cwd(), pyOutPath)} from api/openapi.yaml.`);
