#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo ""
echo "Environment ready. Activate with:"
echo "  source .venv/bin/activate"
echo "  export ANSIBLE_COLLECTIONS_PATH=\"$(pwd)/collections\""
