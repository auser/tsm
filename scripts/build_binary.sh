#!/bin/bash
set -euo pipefail

# Build the binary
uv run pyinstaller --onefile --name tsm main.py

echo "Binary created at dist/tsm"