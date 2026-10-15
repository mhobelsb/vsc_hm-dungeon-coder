# Releasing

The extension and the Python package `dungeoncoder` share one version number. It lives in three files:
`package.json` (with `package-lock.json`), `api/python/dungeoncoder/__init__.py` and `api/openapi.yaml`.
`npm run check:version` fails if they differ, or if `api/python/LICENSE.txt` is no longer a copy of `LICENSE.txt`.

A version on PyPI can never be replaced or uploaded again, not even after deleting it. Check everything
on TestPyPI first.

## 1. Set the version

```bash
npm version X.Y.Z --no-git-tag-version          # package.json and package-lock.json
# then the same number in api/python/dungeoncoder/__init__.py and in api/openapi.yaml (info.version)
npm run check:version
```

Move the entries under `## [Unreleased]` in `CHANGELOG.md` to a new `## [X.Y.Z] - date` section.

## 2. Build the Python package

Once, a separate environment with the release tools:

```bash
python3 -m venv ~/.venvs/dc-release
~/.venvs/dc-release/bin/pip install build twine
```

Then, in this folder:

```bash
PATH=~/.venvs/dc-release/bin:$PATH npm run build:dist     # out/dist/dungeoncoder-X.Y.Z.tar.gz and -py3-none-any.whl
~/.venvs/dc-release/bin/twine check out/dist/*
```

Look at what goes in: `unzip -l out/dist/*.whl`. Only the API, the simulator and the free styles
(`packs/tilesets.json` names only `demo*` and `welt_*` tilesets); no course levels, course styles or tilesets.

## 3. Try it in a fresh environment

```bash
python3 -m venv /tmp/dc-try && /tmp/dc-try/bin/pip install out/dist/*.whl
/tmp/dc-try/bin/python -m dungeoncoder            # ends with "Everything is ready."
```

## 4. TestPyPI, then PyPI

The upload asks for a token: user name `__token__`, password the token (`pypi-…`). Or put both in
`~/.pypirc` (sections `[testpypi]` and `[pypi]`). Tokens never go into this repository.

```bash
~/.venvs/dc-release/bin/twine upload --repository testpypi out/dist/*
python3 -m venv /tmp/dc-test && /tmp/dc-test/bin/pip install \
    -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ dungeoncoder==X.Y.Z
/tmp/dc-test/bin/python -m dungeoncoder

~/.venvs/dc-release/bin/twine upload out/dist/*
```

`--extra-index-url` lets pip take `httpx` and `attrs` from PyPI; TestPyPI has its own, unrelated copies.

After the first upload: replace the token for "all projects" with one scoped to `dungeoncoder`.

## 5. The extension (`.vsix`, Marketplace)

The extension is `hm-benidiet.vscode-dungeon-coder` ("Dungeon Coder"). Its release version was 0.1.0
until 1.0.0; the versions between (0.2.x) went out as **pre-releases**. VS Code offers a pre-release
only to those who choose "Switch to Pre-Release Version" (back with "Switch to Release Version");
everyone else gets the release version, and with auto-update they get each new one.

**Version numbers.** The Marketplace takes plain `major.minor.patch` numbers only (no `-beta`), and
VS Code keeps a pre-release user on the pre-release channel only while it has a higher version than
the newest release. From 1.0.0 on we follow VS Code's convention: **an even minor is a release**
(1.0.x, 1.2.x), **an odd minor a pre-release** (1.1.x, 1.3.x), each higher than everything before.
`tools/check-vsix.mjs` checks this and asks the Marketplace for the published versions.
PyPI has no such channel: the Python package of a pre-release is an ordinary version that `pip`
installs for everyone whose requirement allows it (`dungeoncoder>=1.0`). Upload it only when it is
backwards compatible, as every version so far; otherwise wait for the release.

```bash
npm run compile && npm run lint && npm run compile-tests && npm test
npx @vscode/vsce ls                   # what goes in
```

Everything in the `.vsix` is public once it is on the Marketplace: `game/assets/` must hold only free
pictures (the demo pack, the CC0 `welt_*` worlds, the title image). The course art comes from the
course's own asset pack. The README image is resolved against the public repository (`repository`
in `package.json`); it shows once the image is pushed there.

Once per machine: `npx @vscode/vsce login hm-benidiet` with a Personal Access Token (Azure DevOps,
scope "Marketplace → Manage"). Publish only with the scripts below: each checks the package first
(`tools/check-vsix.mjs`: pre-release mark, ID, version, Marketplace, CHANGELOG). Never call
`npx @vscode/vsce publish` directly.

**A release** reaches everyone with auto-update within hours, also pre-release users (their
pre-release is now lower than the release). Before it: the courses that use the extension know
it is coming (no release during an exam period; an exam machine installs a fixed `.vsix`, see the
course's notes), and the CHANGELOG section says what changes for users.

```bash
npm run package:release                     # out/vscode-dungeon-coder-X.Y.Z.vsix, without the pre-release mark
npm run publish:release                     # checks it, then publishes
```

**A pre-release** reaches only those who chose pre-releases.

```bash
npm run package:prerelease                  # out/vscode-dungeon-coder-X.Y.Z-pre.vsix
npm run publish:prerelease                  # checks the mark, the ID and the version, then publishes
```

**Afterwards: check what a fresh VS Code installs**, normally and with `--pre-release` (the test
VS Code from `npm run test:download`). After a release both give the release (until the next
pre-release); after a pre-release, only `--pre-release` gives it:

```bash
CODE="$HOME/.cache/vscode-test/vscode-darwin-arm64-1.140.0/Visual Studio Code.app/Contents/Resources/app/bin/code"
for flag in "" --pre-release; do
  P=$(mktemp -d)
  "$CODE" --user-data-dir="$P/u" --extensions-dir="$P/e" --install-extension hm-benidiet.vscode-dungeon-coder $flag
  "$CODE" --user-data-dir="$P/u" --extensions-dir="$P/e" --list-extensions --show-versions | grep dungeon
done
```

**Going back.** A published version can't be replaced; a broken release is fixed by a higher one.
Users can install an older version themselves ("Install Specific Version…" on the extension's page,
or `code --install-extension hm-benidiet.vscode-dungeon-coder@0.1.0`); auto-update then has to be off
for this extension, or it comes back.

## 6. Afterwards

Tag the release commit: `git tag vX.Y.Z` and push it with the commit. The extension and the
Python package have the same version; a release of one is a release of both.
