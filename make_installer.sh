#!/usr/bin/env sh

pip install pyinstaller

pyinstaller --add-data "src/gambitpairing/resources/styles.qss:resources/styles.qss" src/gambitpairing/__main__.py
