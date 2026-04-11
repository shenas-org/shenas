#!/usr/bin/env python3
"""Patch .copybara/copy.bara.sky to use an LLM-generated commit message.

Replaces metadata.squash_notes(...) with metadata.replace_message("...")
using the summary from the given file.

Usage: oss-patch-copybara.py /tmp/release_summary.txt
"""

from __future__ import annotations

import re
import sys

SUMMARY_FILE = sys.argv[1] if len(sys.argv) > 1 else "/tmp/release_summary.txt"
CONFIG = ".copybara/copy.bara.sky"

with open(SUMMARY_FILE) as f:
    summary = f.read().strip()

escaped = summary.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

with open(CONFIG) as f:
    content = f.read()

content = re.sub(
    r"metadata\.squash_notes\([^)]*\)",
    f'metadata.replace_message("{escaped}")',
    content,
)

with open(CONFIG, "w") as f:
    f.write(content)

print(f"Patched {CONFIG} with release summary")
