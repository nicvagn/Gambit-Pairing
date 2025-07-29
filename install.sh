#!/usr/bin/env bash

SCRIPT_DIR=$(dirname "$0")

cd $SCRIPT_DIR

python -m pip install .

echo "gambit-pairing is now installed as a gui script"
echo "try running gambit-pairing from a shell in the python environment you installed in"
