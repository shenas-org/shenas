#!/usr/bin/env python3
"""Read VERSION file, bump patch, write back, print new version."""
import sys
from pathlib import Path

version_file = Path(sys.argv[1])
parts = version_file.read_text().strip().split(".")
parts[2] = str(int(parts[2]) + 1)
new_version = ".".join(parts)
version_file.write_text(new_version + "\n")
print(new_version)
