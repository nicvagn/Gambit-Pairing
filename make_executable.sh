#!/usr/bin/env sh
SCRIPT_DIR=$(dirname "$0")
pip install pyinstaller || exit 1
pyinstaller "$SCRIPT_DIR/Gambit-Pairing.spec"
