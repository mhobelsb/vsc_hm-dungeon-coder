// Before `vsce publish --pre-release`: the package must be marked as a pre-release, and it must
// name this extension and the version in package.json. A package without the mark would become
// the release version that everyone with auto-update gets (RELEASING.md, section 5).
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';

const vsix = process.argv[2];
const manifest = execFileSync('unzip', ['-p', vsix, 'extension.vsixmanifest'], { encoding: 'utf8' });
const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));
const problems = [];
if (!/<Property Id="Microsoft\.VisualStudio\.Code\.PreRelease" Value="true"/.test(manifest)) {
    problems.push('the package is not marked as a pre-release (npm run package:prerelease)');
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
if (problems.length) {
    for (const p of problems) {
        console.error(`ERROR  ${p}`);
    }
    process.exit(1);
}
console.log(`ok  ${pkg.publisher}.${pkg.name} ${pkg.version}, marked as a pre-release`);
