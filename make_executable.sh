#!/usr/bin/env sh

SCRIPT_DIR=$(dirname "$0")

pip install pyinstaller

pyinstaller $SCRIPT_DIR/Gambit-Pairing.spec
