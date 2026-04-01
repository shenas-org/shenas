#!/usr/bin/env bash
# Build the Lit UI and vendor deps, then assemble into a single static
# directory that the Rust server embeds at compile time.
#
# Output: app/mobile/ui-dist/
#   ├── index.html           (the UI shell HTML)
#   ├── vendor/              (Lit, uPlot, Arrow, Cytoscape)
#   ├── ui/default/          (built UI JS)
#   └── static/              (images, manifest, etc.)

set -e

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DIST="$ROOT/app/mobile/ui-dist"

echo "Building UI for mobile..."

# Clean
rm -rf "$DIST"
mkdir -p "$DIST/vendor" "$DIST/ui/default" "$DIST/static"

# Build vendor libs
echo "  Building vendor..."
cd "$ROOT/app/vendor"
npm install --silent 2>/dev/null
npm run build --silent 2>/dev/null
cp dist/*.js "$DIST/vendor/"

# Build UI
echo "  Building UI..."
cd "$ROOT/plugins/ui/default"
npm install --silent 2>/dev/null
npm run build --silent 2>/dev/null
cp shenas_ui/default/static/default.js "$DIST/ui/default/"
cp default.html "$DIST/index.html"

# Copy static assets
echo "  Copying static assets..."
cp -r "$ROOT/app/static/images" "$DIST/static/" 2>/dev/null || true
cp "$ROOT/app/static/"*.json "$DIST/static/" 2>/dev/null || true

echo "UI built: $DIST"
ls -lh "$DIST"
