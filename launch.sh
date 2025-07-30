#!/usr/bin/env bash
echo "running from the src directory."
trap 'echo "FAIL: Make sure you have installed pip requirements, and activated any relevant venvs"' ERR
SCRIPT_DIR=$(dirname "$0")
python3 $SCRIPT_DIR/src/gambitpairing
