// Before `vsce publish`: is this package the one we mean to publish? (RELEASING.md, section 5)
//
//   node tools/check-vsix.mjs --release     out/vscode-dungeon-coder-X.Y.Z.vsix
//   node tools/check-vsix.mjs --pre-release out/vscode-dungeon-coder-X.Y.Z-pre.vsix
//
// Both: the package names this extension and the version in package.json, and that version is higher
// than every version on the Marketplace (else VS Code keeps pre-release users on an older pre-release,
// and the Marketplace refuses a version it has). From 1.0.0 on, VS Code's convention: an even minor
// is a release (1.0.x, 1.2.x), an odd minor a pre-release (1.1.x), so the two never collide.
// --release: no pre-release mark (everyone with auto-update gets it) and a CHANGELOG section for it.
// --pre-release: the mark is there (without it the package would become the release version).
// --offline skips the Marketplace check (only to try the script; never before publishing).
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';

const args = process.argv.slice(2);
const kind = args.includes('--release') ? 'release' : args.includes('--pre-release') ? 'pre-release' : null;
const vsix = args.find((a) => !a.startsWith('--'));
if (!kind || !vsix) {
    console.error('usage: node tools/check-vsix.mjs --release|--pre-release [--offline] PACKAGE.vsix');
    process.exit(2);
}
const read = (file) => readFileSync(new URL(`../${file}`, import.meta.url), 'utf8');
const pkg = JSON.parse(read('package.json'));
const problems = [];

let manifest = '';
try {
    manifest = execFileSync('unzip', ['-p', vsix, 'extension.vsixmanifest'], { encoding: 'utf8' });
} catch {
    console.error(`ERROR  cannot read ${vsix} (npm run package:${kind === 'release' ? 'release' : 'prerelease'})`);
    process.exit(1);
}
const marked = /<Property Id="Microsoft\.VisualStudio\.Code\.PreRelease" Value="true"/.test(manifest);
if (kind === 'pre-release' && !marked) {
    problems.push('the package is not marked as a pre-release (npm run package:prerelease)');
}
if (kind === 'release' && marked) {
    problems.push('the package is marked as a pre-release (npm run package:release)');
}
const identity = manifest.match(/<Identity [^>]*Id="([^"]+)"[^>]*Version="([^"]+)"[^>]*Publisher="([^"]+)"/);
if (!identity) {
    problems.push('no identity in the package manifest');
} else {
    const [, id, version, publisher] = identity;
    if (`${publisher}.${id}` !== `${pkg.publisher}.${pkg.name}`) {
        problems.push(`the package is ${publisher}.${id}, not ${pkg.publisher}.${pkg.name}`);
    }
    if (version !== pkg.version) {
        problems.push(`the package has version ${version}, package.json ${pkg.version}`);
    }
}

const parse = (v) => v.split('.').map(Number);
const compare = (a, b) => {
    const [x, y] = [parse(a), parse(b)];
    return x[0] - y[0] || x[1] - y[1] || x[2] - y[2];
};
const [major, minor] = parse(pkg.version);
if (major >= 1 && kind === 'release' && minor % 2 !== 0) {
    problems.push(`${pkg.version}: from 1.0.0 on a release has an even minor version (1.0.x, 1.2.x)`);
}
if (major >= 1 && kind === 'pre-release' && minor % 2 === 0) {
    problems.push(`${pkg.version}: from 1.0.0 on a pre-release has an odd minor version (1.1.x, 1.3.x)`);
}
if (kind === 'release' && !read('CHANGELOG.md').includes(`## [${pkg.version}]`)) {
    problems.push(`CHANGELOG.md has no section "## [${pkg.version}]"`);
}

if (!args.includes('--offline')) {
    let published = [];
    try {
        const out = execFileSync('npx', ['--yes', '@vscode/vsce', 'show', `${pkg.publisher}.${pkg.name}`, '--json'],
            { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
        published = JSON.parse(out).versions.map((v) => v.version);
    } catch {
        problems.push('cannot ask the Marketplace for the published versions (offline?)');
    }
    const newest = published.reduce((a, b) => (compare(a, b) >= 0 ? a : b), '0.0.0');
    if (published.length && compare(pkg.version, newest) <= 0) {
        problems.push(`version ${pkg.version} is not higher than ${newest}, the newest on the Marketplace`);
    }
}

if (problems.length) {
    for (const p of problems) {
        console.error(`ERROR  ${p}`);
    }
    process.exit(1);
}
console.log(`ok  ${pkg.publisher}.${pkg.name} ${pkg.version} as a ${kind}`);
