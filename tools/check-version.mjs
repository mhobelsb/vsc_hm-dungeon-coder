// The extension and the Python package carry one version (package.json and
// dungeoncoder.__version__), and so does the API description (openapi.yaml).
// Exits with 1 if they differ.
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const read = (file) => readFileSync(join(root, file), 'utf8');

const versions = {
    'package.json': JSON.parse(read('package.json')).version,
    'api/python/dungeoncoder/__init__.py': (read('api/python/dungeoncoder/__init__.py').match(/__version__ = "([^"]+)"/) || [])[1],
    'api/openapi.yaml': (read('api/openapi.yaml').match(/^ {2}version: *"?([^"\s]+)"?/m) || [])[1],
};
const distinct = new Set(Object.values(versions));
if (distinct.size !== 1) {
    for (const [file, version] of Object.entries(versions)) {
        console.error(`${file}: ${version}`);
    }
    console.error('The versions differ; set them all to the same value.');
    process.exit(1);
}
console.log(`version ${[...distinct][0]}`);
