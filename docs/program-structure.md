# Program structure of Gambit-Pairing

## main.py -- entry point

- Creates the main window. Handles various OS'.

## gui module -- contains the various components and QT widgets

### mainwindow.py -- in charge of the main window

`class SwissTournamentApp(QtWidgets.QMainWindow):`

### crosstable_tab.py

`class CrosstableTab(QtWidgets.QWidget):`

### ... This module contains the Qt Widgets


## core module -- contains the business logic

### utils.py  -- logging and utility functions

### updater.py --  Handles checking for and applying application updates from GitHub Releases.

### player.py --  Represents a player in the tournament.

`class Player:`

### tournament.py -- Manages the tournament state, pairings, results, and tiebreakers.
`class Tournament:`

### constants.py -- what you think
