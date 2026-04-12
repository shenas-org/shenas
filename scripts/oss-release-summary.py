#!/usr/bin/env python3
"""Generate an LLM-summarized release changelog for the OSS repo.

Reads git commits since the last OSS release tag, sends them to Claude
for a user-focused summary that filters out private/internal refs.

Requires: ANTHROPIC_API_KEY env var (falls back to raw log without it)
Output: writes summary to the file path given as argv[1] (default: /tmp/release_summary.txt)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/release_summary.txt"

# Tags that trigger OSS releases (same prefixes as oss-release.yml)
OSS_TAG_PATTERNS = [
    "app/v*",
    "shenasctl/v*",
    "scheduler/v*",
    "source-*/v*",
    "dataset-*/v*",
    "dashboard-*/v*",
    "plugin-core/v*",
    "transformation-*/v*",
    "frontend-*/v*",
    "theme-*/v*",
    "analysis-*/v*",
    "model-*/v*",
]

EXCLUDE_PATHS = [
    ":!server/",
    ":!app/fl/",
    ":!app/mesh/",
    ":!app/desktop/",
    ":!app/mobile/",
    ":!.copybara/",
    ":!.github/",
    ":!.moon/",
    ":!scripts/",
]

PROMPT = (
    "Summarize these git commits for a public open-source release changelog. "
    "Write first a one-line summary, then start the next line by summing up "
    "the commits with 2-5 bullet points, covering the user-visible changes. "
    "Omit any references to: shenas-net, shenas-org, internal infrastructure, CI/CD fixes, Copybara, "
    "private repos, server-side code, premium features, LLM integration, "
    "literature fetching, federated learning, mesh sync. "
    "Keep it concise and user-focused. No preamble, just the bullets."
    "Make it look like we know what we are doing."
    "Avoid 'Enhanced' as the first word of the message."
)


def run_git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    return result.stdout.strip()


def find_previous_oss_tag() -> str | None:
    """Find the most recent OSS-relevant tag on an older commit than HEAD.

    Lists all tags matching OSS patterns, sorted newest first, and
    returns the first one that points to a different commit than HEAD.
    This gives us the tag from the previous release batch.
    """
    tag_args = []
    for pattern in OSS_TAG_PATTERNS:
        tag_args.extend(["--list", pattern])

    sorted_tags = run_git("tag", *tag_args, "--sort=-creatordate")
    if not sorted_tags:
        return None

    head = run_git("rev-parse", "HEAD")

    for tag in sorted_tags.splitlines():
        tag_commit = run_git("rev-list", "-1", tag)
        if tag_commit != head:
            return tag
    return None


def get_commits() -> str:
    prev_tag = find_previous_oss_tag()

    log_args = ["log", "--pretty=format:- %s"]

    if prev_tag:
        log_args.append(f"{prev_tag}..HEAD")
        print(f"Commits since {prev_tag}:", file=sys.stderr)
    else:
        log_args.append("-30")
        print("No previous OSS tag found, using last 30 commits", file=sys.stderr)

    log_args.extend(["--", ".", *EXCLUDE_PATHS])
    output = run_git(*log_args)
    lines = output.splitlines()[:50]
    return "\n".join(lines)


def ask_claude(commits: str) -> str | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    payload = json.dumps(
        {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 300,
            "messages": [{"role": "user", "content": f"{PROMPT}\n\nCommits:\n{commits}"}],
        }
    ).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return data["content"][0]["text"]
    except urllib.error.HTTPError as exc:
        body = exc.read().decode() if exc.fp else ""
        print(f"Claude API error: {exc} -- {body}", file=sys.stderr)
    except Exception as exc:
        print(f"Claude API error: {exc}", file=sys.stderr)
        return None


def main() -> None:
    commits = get_commits()

    if not commits:
        summary = "No commits seen, just bump"
    else:
        summary = ask_claude(commits)
        if not summary:
            print(
                "ANTHROPIC_API_KEY not set or API failed, using raw commit log",
                file=sys.stderr,
            )
            summary = "Commit message missing"

    with open(OUTPUT, "w") as f:
        f.write(summary)

    print(f"Release summary written to {OUTPUT}")


if __name__ == "__main__":
    main()
