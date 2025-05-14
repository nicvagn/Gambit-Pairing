# Gambit Pairing (Alpha 0.2.0)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-Used-green.svg)](https://riverbankcomputing.com/software/pyqt/intro)
[![Discord](https://img.shields.io/badge/Discord-Join%20Chat-blue.svg)](https://discord.gg/eEnnetMDfr)

**Important:** Gambit Pairing is in alpha development (version 0.2.0). Features and stability are not guaranteed.

[Join our Discord](https://discord.gg/eEnnetMDfr)

Gambit Pairing is a desktop application for managing Swiss-system chess tournaments. It provides a modern graphical user interface (GUI) built with PyQt6, supporting USCF-style pairings, tiebreaks, and tournament management.

## Features

- **Player Management**
  - Add, edit, withdraw/reactivate, and remove players.
  - Manage player details with GUI.
  - Import/export player lists/details from/to CSV or text files.
- **Tournament Setup**
  - Configure number of rounds and tiebreak order (Median, Solkoff, Cumulative, etc.).
  - Save/load tournaments to/from disk.
- **Swiss Pairings**
  - Automated pairings for each round, avoiding rematches and balancing colors.
  - Manual adjustment of pairings before results are entered.
  - Bye assignment according to USCF rules.
- **Results Entry**
  - Enter round results via an interactive table with quick result buttons.
  - Undo last round's results.
- **Standings & Tiebreaks**
  - Standings table with configurable tiebreak columns.
  - Cross-table view showing all results.
- **History & Export**
  - Detailed history log of actions, pairings, and results.
  - Export standings and player lists to CSV or text.
- **User Interface**
  - Tabbed interface: Tournament Control, Standings, Cross-Table, History Log.
  - High-contrast, accessible UI with tooltips and context menus.

## Requirements

- Python 3.8+
- PyQt6

## Installation

1. Install Python 3.8 or higher.
2. Install all required dependencies using `requirements.txt`:
    ```bash
    pip install -r requirements.txt
    ```
3. Download or clone this repository.

## Usage

1. Run the application:
    ```bash
    python main.py
    ```
2. **Create or Load a Tournament:**
    - Use "File > New Tournament..." or "File > Load Tournament..." to start.
    - Configure rounds and tiebreaks in "Settings".
3. **Add Players:**
    - Enter player names (optionally with rating) and click "Add Player".
    - Import players from CSV via "File > Import Players from CSV...".
    - Edit, withdraw/reactivate, or remove players via right-click context menu.
4. **Start Tournament:**
    - Click "Start Tournament" when ready.
    - No further player additions/removals after starting.
5. **Pairings and Results:**
    - Prepare next round and enter results in the pairings table.
    - Use quick result buttons or select from the dropdown.
    - Manually adjust pairings if needed.
    - Undo last round's results if necessary.
6. **Standings & Cross-Table:**
    - View current standings and tiebreaks in the Standings tab.
    - View all results in the Cross-Table tab.
7. **Export & Save:**
    - Export standings or player lists via the File menu.
    - Save or load tournaments at any time.
8. **History:**
    - Review all actions and results in the History Log tab.

## Notes

- The pairing algorithm follows USCF-style Swiss rules, including color balancing and bye assignment.
- Tiebreak order is fully configurable and reflected in the standings.
- Manual pairing adjustments are logged and cannot be undone automatically.
- Tournament data is saved in `.gpf` files (JSON format).
- This is an alpha version (0.2.0); please report bugs or suggestions via [Discord](https://discord.gg/eEnnetMDfr) or make an issue on Github.

## License

This project is open source and available under the [MIT License](LICENSE).
