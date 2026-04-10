#!/usr/bin/env bash
# Generate an LLM-summarized release changelog for the OSS repo.
#
# Reads git commits since the last Copybara sync, sends them to Claude
# for a user-focused summary that filters out private/internal refs.
#
# Requires: ANTHROPIC_API_KEY env var, curl, python3, git
# Output: writes summary to the file path given as $1 (default: /tmp/release_summary.txt)

set -euo pipefail

OUTPUT="${1:-/tmp/release_summary.txt}"

# Paths to exclude from the changelog (private/premium)
EXCLUDE_PATHS=(
  ':!server/'
  ':!app/fl/'
  ':!app/mesh/'
  ':!app/literature*'
  ':!plugins/analyses/'
  ':!plugins/models/'
  ':!.copybara/'
  ':!.github/'
  ':!scripts/oss-release-summary.sh'
)

# Find the last synced revision
LAST_REV=$(git log --all --grep="GitOrigin-RevId" --format="%b" -1 2>/dev/null \
  | grep "GitOrigin-RevId:" | awk '{print $2}' || echo "")

if [ -n "$LAST_REV" ] && git rev-parse "$LAST_REV" >/dev/null 2>&1; then
  LOG=$(git log "$LAST_REV"..HEAD --pretty=format:"- %s" -- . "${EXCLUDE_PATHS[@]}" | head -50)
else
  LOG=$(git log --pretty=format:"- %s" -30 -- . "${EXCLUDE_PATHS[@]}")
fi

if [ -z "$LOG" ]; then
  echo "Release sync" > "$OUTPUT"
  exit 0
fi

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  echo "ANTHROPIC_API_KEY not set, using raw commit log"
  echo -e "Release sync\n\n$LOG" > "$OUTPUT"
  exit 0
fi

PROMPT="Summarize these git commits for a public open-source release changelog. Write 2-5 bullet points covering the user-visible changes. Omit any references to: internal infrastructure, CI/CD fixes, Copybara, private repos, server-side code, premium features, LLM integration, literature fetching, federated learning, mesh sync. Keep it concise and user-focused. No preamble, just the bullets.\n\nCommits:\n$LOG"

PAYLOAD=$(python3 -c "
import json, sys
print(json.dumps({
    'model': 'claude-sonnet-4-20250514',
    'max_tokens': 300,
    'messages': [{'role': 'user', 'content': sys.argv[1]}]
}))
" "$PROMPT")

RESPONSE=$(curl -s https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d "$PAYLOAD")

SUMMARY=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['content'][0]['text'])" 2>/dev/null || echo "")

if [ -n "$SUMMARY" ]; then
  echo "$SUMMARY" > "$OUTPUT"
else
  echo -e "Release sync\n\n$LOG" > "$OUTPUT"
fi

echo "Release summary written to $OUTPUT"
