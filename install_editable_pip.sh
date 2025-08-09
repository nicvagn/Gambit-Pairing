#!/usr/bin/env bash
trap 'echo "FAIL: Make sure you have installed pip requirements, and activated any relevant venvs"' ERR
SCRIPT_DIR=$(dirname "$0")
python3 -m ensurepip --upgrade

python3 -m pip install --editable $SCRIPT_DIR

echo "Python pip pkg installed in --editable mode"
echo "now gambit-pairing should be on your \$PATH, try gambit-paining in your shell"
