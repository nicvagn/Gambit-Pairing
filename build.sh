#!/usr/bin/env bash

SCRIPT_DIR=$(dirname "$0")

cd $SCRIPT_DIR

python -m pip install build

python -m build .

echo "installed build with pip and build gambit pairing"
echo "dist should contain built wheel"
