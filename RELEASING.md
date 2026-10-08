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

The extension is `hm-dungeon-coder.dungeon-coder` ("HM Dungeon Coder"). The legacy extension
`hm-benidiet.vscode-dungeon-coder` stays on the Marketplace; both can be installed together.

```bash
npm run compile && npm run lint && npm run compile-tests && npm test
npm run package:vsix                  # out/dungeon-coder-X.Y.Z.vsix
npx @vscode/vsce ls                   # what goes in
```

Everything in the `.vsix` is public once it is on the Marketplace: check that no course graphics are
in `game/assets/` (only the CC0 `welt_*` and demo tilesets; `docs/public-release.md` of the course
workspace, steps 2 and 3). The README image is linked to the public repository
(`--baseImagesUrl` in `package:vsix`); it shows once that repository exists.

To run the tests next to the legacy extension, install it once into the test profile (the path is
`profile` in `.vscode-test.mjs`):

```bash
CODE="$HOME/.cache/vscode-test/vscode-darwin-arm64-1.140.0/Visual Studio Code.app/Contents/Resources/app/bin/code"
P=$(node -e "console.log(require('os').tmpdir())")/dungeon-coder-vscode-test
"$CODE" --user-data-dir="$P/user-data" --extensions-dir="$P/extensions" --install-extension hm-benidiet.vscode-dungeon-coder
```

Publishing (once per machine: a Personal Access Token from Azure DevOps with the scope
"Marketplace → Manage", for the publisher `hm-dungeon-coder`):

```bash
npx @vscode/vsce login hm-dungeon-coder
npx @vscode/vsce publish --packagePath out/dungeon-coder-X.Y.Z.vsix
```

## 6. Afterwards

Tag the release commit: `git tag vX.Y.Z`. The extension (`.vsix`) gets the same version; it is
built with `npx @vscode/vsce package`.
