#!/usr/bin/env python3
"""Generate an LLM-summarized release changelog for the OSS repo.

Reads git commits since the last Copybara sync, sends them to Claude
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

EXCLUDE_PATHS = [
    ":!server/",
    ":!app/fl/",
    ":!app/mesh/",
    ":!app/literature*",
    ":!plugins/analyses/",
    ":!plugins/models/",
    ":!.copybara/",
    ":!.github/",
    ":!scripts/oss-release-summary.py",
]

PROMPT = (
    "Summarize these git commits for a public open-source release changelog. "
    "Write 2-5 bullet points covering the user-visible changes. "
    "Omit any references to: internal infrastructure, CI/CD fixes, Copybara, "
    "private repos, server-side code, premium features, LLM integration, "
    "literature fetching, federated learning, mesh sync. "
    "Keep it concise and user-focused. No preamble, just the bullets."
)


def run_git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    return result.stdout.strip()


def get_commits() -> str:
    # Find last synced revision from GitOrigin-RevId marker
    body = run_git("log", "--all", "--grep=GitOrigin-RevId", "--format=%b", "-1")
    last_rev = ""
    for line in body.splitlines():
        if line.startswith("GitOrigin-RevId:"):
            last_rev = line.split(":", 1)[1].strip()
            break

    log_args = ["log", "--pretty=format:- %s"]

    if last_rev:
        # Verify the rev exists
        check = subprocess.run(["git", "rev-parse", last_rev], capture_output=True)
        if check.returncode == 0:
            log_args.append(f"{last_rev}..HEAD")
        else:
            log_args.append("-30")
    else:
        log_args.append("-30")

    log_args.extend(["--", ".", *EXCLUDE_PATHS])
    output = run_git(*log_args)
    # Limit to 50 lines
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
        summary = "Release sync"
    else:
        summary = ask_claude(commits)
        if not summary:
            print(
                "ANTHROPIC_API_KEY not set or API failed, using raw commit log",
                file=sys.stderr,
            )
            summary = f"Release sync\n\n{commits}"

    with open(OUTPUT, "w") as f:
        f.write(summary)

    print(f"Release summary written to {OUTPUT}")


if __name__ == "__main__":
    main()
