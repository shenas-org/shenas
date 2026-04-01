#!/usr/bin/env bash
# Compute the next semver tag for a package based on conventional commits.
#
# Usage: scripts/bump-tag.sh <prefix> <dirs...>
# Output: Shell-evaluable variables (TAG, BUMP, PREV, COMMITS) or nothing if
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
LATEST=$(git describe --tags --match "$PREFIX/v*" --abbrev=0 2>/dev/null || echo "$PREFIX/v0.0.0")
VERSION="${LATEST##*/v}"

# Collect conventional commits since last tag that touch these dirs
COMMITS=$(git log "$LATEST"..HEAD --pretty=format:"%s" -- $DIRS 2>/dev/null)
[ -z "$COMMITS" ] && exit 0

# Determine bump type (highest wins: major > minor > patch)
BUMP="patch"
echo "$COMMITS" | grep -qiE "^feat(\(.*\))?:" && BUMP="minor"
echo "$COMMITS" | grep -qiE "^feat(\(.*\))?!:|BREAKING CHANGE" && BUMP="major"

# Compute new version
IFS='.' read -r MAJOR MINOR PATCH <<< "$VERSION"
case "$BUMP" in
  major) NEW="$((MAJOR+1)).0.0" ;;
  minor) NEW="$MAJOR.$((MINOR+1)).0" ;;
  patch) NEW="$MAJOR.$MINOR.$((PATCH+1))" ;;
esac

TAG="$PREFIX/v$NEW"

# Output as shell-evaluable variables
echo "TAG=$TAG"
echo "BUMP=$BUMP"
echo "PREV=$LATEST"
echo "COMMITS<<EOF"
echo "$COMMITS"
echo "EOF"
