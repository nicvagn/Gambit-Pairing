# Program structure of Gambit-Pairing

- is an implicit namespace package. See PEP 420
> like:
"""
mynamespace-subpackage-a/
    pyproject.toml # AND/OR setup.py, setup.cfg
    src/
        mynamespace/ # namespace package
            # No __init__.py here.
            subpackage_a/
                # Regular import packages have an __init__.py.
                __init__.py
                module.py
"""

- uses a src  layout, see:
https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/#src-layout-vs-flat-layout

# in the gambitpairing module:

## __main.py__ -- entry point
- Creates the main window. Handles various OS'.
- `from gui.mainwindow import SwissTournamentApp` imports app

# gui module -- contains the various components and QT widgets

## mainwindow.py -- in charge of the main window

`class SwissTournamentApp(QtWidgets.QMainWindow):`

## crosstable_tab.py

`class CrosstableTab(QtWidgets.QWidget):`

## ... This module contains the Qt Widgets

# core module -- contains the business logic

## utils.py  -- logging and utility functions

## updater.py --  Handles checking for and applying application updates from GitHub Releases.

## player.py --  Represents a player in the tournament.

`class Player:`

## tournament.py -- Manages the tournament state, pairings, results, and tiebreakers.
`class Tournament:`

## constants.py -- what you think
