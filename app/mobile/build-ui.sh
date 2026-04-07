#!/usr/bin/env bash
# Build the Lit frontend and vendor deps, then assemble into a single static
# directory that the Rust server embeds at compile time.
#
# Output: app/mobile/mobile-dist/
#   ├── index.html              (the frontend shell HTML)
#   ├── vendor/                 (Lit, uPlot, Arrow, Cytoscape)
#   ├── frontend/default/       (built frontend JS)
#   └── static/                 (images, manifest, etc.)

set -e

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DIST="$ROOT/app/mobile/mobile-dist"

echo "Building UI for mobile..."

# Clean
rm -rf "$DIST"
mkdir -p "$DIST/vendor" "$DIST/frontend/default" "$DIST/static"

# Build vendor libs
echo "  Building vendor..."
cd "$ROOT/app/vendor"
npm install --silent 2>/dev/null
npm run build --silent 2>/dev/null
cp dist/*.js "$DIST/vendor/"

# Build frontend
echo "  Building frontend..."
cd "$ROOT/plugins/frontends/default"
npm install --silent 2>/dev/null
npm run build --silent 2>/dev/null
cp shenas_frontends/default/static/default.js "$DIST/frontend/default/"
cp default.html "$DIST/index.html"

# Patch for mobile: API base and remove service worker (doesn't work in Tauri)
sed -i 's|api-base="/api"|api-base="http://127.0.0.1:7280/api"|' "$DIST/index.html"
sed -i '/serviceWorker/d' "$DIST/index.html"

# Copy static assets
echo "  Copying static assets..."
cp -r "$ROOT/app/static/images" "$DIST/static/" 2>/dev/null || true
cp "$ROOT/app/static/"*.json "$DIST/static/" 2>/dev/null || true

echo "UI built: $DIST"
ls -lh "$DIST"
