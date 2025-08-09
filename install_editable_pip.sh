#!/usr/bin/env bash
trap 'echo "FAIL: Make sure you have installed pip requirements, and activated any relevant venvs"' ERR
SCRIPT_DIR=$(dirname "$0")

bash $SCRIPT_DIR/ensure_all_dependancies.sh

echo "Python pip pkg installed in --editable mode"
python3 -m pip install --editable $SCRIPT_DIR

echo "now gambit-pairing should be on your \$PATH, try gambit-paining in your shell"
