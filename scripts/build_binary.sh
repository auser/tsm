#!/bin/bash
set -euo pipefail

# Build the binary
uv run pyinstaller --onefile --name tsm src/tsm/cli.py

echo "Binary created at dist/tsm"