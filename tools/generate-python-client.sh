#!/usr/bin/env bash
# Regenerates api/python/dungeoncoder/_generated from api/openapi.yaml.
#
# This is deliberately NOT wired into `npm run compile`/`package`: it needs a
# Python 3 + a venv, which isn't guaranteed on whatever machine builds the
# extension. Its output is committed to the repo instead (see _generated/
# GENERATED.txt) so students get working code with zero codegen toolchain of
# their own - re-run this manually whenever api/openapi.yaml changes.
set -euo pipefail

GENERATOR_VERSION="0.29.0"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$REPO_ROOT/.codegen-venv"
OUTPUT_DIR="$REPO_ROOT/api/python/dungeoncoder/_generated"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating $VENV_DIR ..."
    python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/pip" install --quiet "openapi-python-client==$GENERATOR_VERSION"

rm -rf "$OUTPUT_DIR"
"$VENV_DIR/bin/openapi-python-client" generate \
    --path "$REPO_ROOT/api/openapi.yaml" \
    --meta none \
    --output-path "$OUTPUT_DIR" \
    --overwrite

cat > "$OUTPUT_DIR/GENERATED.txt" <<EOF
This directory is generated. Do not edit its contents by hand - changes will
be silently overwritten the next time it is regenerated.

Source:      api/openapi.yaml
Generator:   openapi-python-client==$GENERATOR_VERSION
Regenerate:  npm run generate:python-client   (see tools/generate-python-client.sh)

api/python/dungeoncoder/dungeoncoder.py wraps this client with the small,
hand-written, student-facing Hero/Game/Level API. Edit that file, not this one.
EOF

echo "Generated $OUTPUT_DIR from api/openapi.yaml."
