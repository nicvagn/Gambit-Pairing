#!/usr/bin/env sh
SCRIPT_DIR=$(dirname "$0")
echo "Ensuring dependancies"
$SCRIPT_DIR/ensure_all_dependancies.sh
echo "installing with pyinstaller"
pyinstaller "$SCRIPT_DIR/Gambit-Pairing.spec"
