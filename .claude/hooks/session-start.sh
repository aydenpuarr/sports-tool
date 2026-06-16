#!/bin/bash
set -euo pipefail

# Only run in remote (Claude Code on the web) environments
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# Create venv if it doesn't already exist
if [ ! -f ".venv/bin/python3" ]; then
  python3 -m venv .venv
fi

# Install/sync all dependencies
.venv/bin/pip install --quiet -r requirements.txt

# Make src importable without needing to set PYTHONPATH manually each time
echo 'export PYTHONPATH="$CLAUDE_PROJECT_DIR"' >> "$CLAUDE_ENV_FILE"
