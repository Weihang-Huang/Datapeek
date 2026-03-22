#!/usr/bin/env bash
# Build DataPeek Electron app
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Step 1: Bundle Flask backend with PyInstaller ==="
cd "$ROOT_DIR"
pip install pyinstaller
pyinstaller web_app/app.py --onefile --name datapeek-server \
    --add-data "web_app/templates:web_app/templates" \
    --add-data "web_app/static:web_app/static" \
    --hidden-import web_app.routes.upload \
    --hidden-import web_app.routes.data \
    --hidden-import web_app.routes.export

echo "=== Step 2: Copy server binary to Electron dist ==="
mkdir -p "$ROOT_DIR/electron/dist"
cp "$ROOT_DIR/dist/datapeek-server" "$ROOT_DIR/electron/dist/"

echo "=== Step 3: Build Electron package ==="
cd "$ROOT_DIR/electron"
npm install
npx electron-builder

echo "=== Done! Check electron/dist/ for the packaged app ==="
