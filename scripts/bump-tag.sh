#!/usr/bin/env bash
# Compute the next semver tag for a package based on conventional commits.
#
# Usage: scripts/bump-tag.sh <prefix> <dirs...>
# Output: TAG, BUMP, PREV as key=value lines (one per line), or nothing if
#         there are no changes since the last tag.
#
# Does NOT create or push tags -- the caller decides what to do with the output.
#
# Examples:
#   bash scripts/bump-tag.sh pipe-garmin plugins/pipes/garmin/
#   bash scripts/bump-tag.sh desktop app/ app/desktop/ build/ scheduler/

set -e

PREFIX="$1"; shift
DIRS="$@"

# Find latest tag for this prefix
LATEST=$(git describe --tags --match "$PREFIX/v*" --abbrev=0 2>/dev/null || true)

if [ -n "$LATEST" ]; then
  VERSION="${LATEST##*/v}"
  COMMITS=$(git log "$LATEST"..HEAD --pretty=format:"%s" -- $DIRS 2>/dev/null)
else
  VERSION="0.0.0"
  COMMITS=$(git log --pretty=format:"%s" -- $DIRS 2>/dev/null)
fi
[ -z "$COMMITS" ] && exit 0

# Determine bump type (highest wins: major > minor > patch)
BUMP="patch"
if echo "$COMMITS" | grep -qiE "^feat(\(.*\))?:"; then BUMP="minor"; fi
if echo "$COMMITS" | grep -qiE "^feat(\(.*\))?!:|BREAKING CHANGE"; then BUMP="major"; fi

# Compute new version
IFS='.' read -r MAJOR MINOR PATCH <<< "$VERSION"
case "$BUMP" in
  major) NEW="$((MAJOR+1)).0.0" ;;
  minor) NEW="$MAJOR.$((MINOR+1)).0" ;;
  patch) NEW="$MAJOR.$MINOR.$((PATCH+1))" ;;
esac

TAG="$PREFIX/v$NEW"
COMMIT_COUNT=$(echo "$COMMITS" | wc -l)

# Output as simple key=value (safe to eval -- no user content)
echo "TAG=$TAG"
echo "BUMP=$BUMP"
echo "PREV=$LATEST"
echo "COMMIT_COUNT=$COMMIT_COUNT"
