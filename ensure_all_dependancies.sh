#!/usr/bin/env sh
echo "ensuring pip is up to date"
python -m ensurepip --upgrade
echo "installing dependancise"
python -m pip install $(python -c 'import tomllib; print(*tomllib.load(open("pyproject.toml", "rb"))["project"]["dependencies"])')

echo "installing dev dependancise"
python -m pip install $(python -c 'import tomllib; print(*tomllib.load(open("pyproject.toml", "rb"))["project"]["optional-dependencies"]["dev"])')
