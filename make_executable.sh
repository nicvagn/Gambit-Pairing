#!/usr/bin/env sh
SCRIPT_DIR=$(dirname "$0")

$SCRIPT_DIR/ensure_all_dependancies.sh

pyinstaller "$SCRIPT_DIR/Gambit-Pairing.spec"
