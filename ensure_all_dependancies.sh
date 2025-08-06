#!/usr/bin/env sh
echo "ensuring pip is up to date"
python3 -m ensurepip --upgrade
echo "installing dependancise"
python3 -m pip install $(python3 -c 'import tomllib; print(*tomllib.load(open("pyproject.toml", "rb"))["project"]["dependencies"])')

echo "installing dev dependancise"
python3 -m pip install $(python3 -c 'import tomllib; print(*tomllib.load(open("pyproject.toml", "rb"))["project"]["optional-dependencies"]["dev"])')
