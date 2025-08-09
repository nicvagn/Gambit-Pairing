#!/usr/bin/env sh
SCRIPT_DIR=$(dirname "$0")

python3 $SCRIPT_DIR/src/gambitpairing/resources/scripts/formatting.py --target $SCRIPT_DIR/src/gambitpairing
