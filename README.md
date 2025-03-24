# Gambit Paring (Pre-Alpha)

**Important:** Gambit Paring is in pre-alpha development. Features and stability are not guaranteed.

[Join our Discord](https://discord.gg/eEnnetMDfr)

This is a desktop application for making Swiss-system chess tournament parings. It provides a graphical user interface (GUI) built with PyQt6, allowing users to:

- Add and remove players from a list.
- Start a tournament.
- Automatically generate pairings for each round, avoiding rematches where possible and assigning colors randomly.
- Input results for each round using a table.
- View current standings in a table.
- Review the history of pairings and results from previous rounds in a dialog.
- Export tournament data to a text file.
- Reset the tournament.

## Features

- **Player Management:** Add players to the tournament roster via an input field and a list. Players can be removed via a context menu in the list.
- **Tournament Setup:** Starts the tournament and disables further player additions to ensure fair play.
- **Automated Pairings:** Generates pairings for each round using a greedy matching algorithm that prioritizes avoiding previous matches and assigns colors (White/Black) randomly. Bye rounds are assigned to the lowest-scoring player.
- **Score Input:** A table allows for easy input of match results for each round. The application handles incomplete scores gracefully, treating them as 0.
- **Standings Display:** Dynamically updates and displays the tournament standings in a table based on player scores.
- **Round History:** Provides a detailed history of pairings and results from each round in a separate dialog.
- **Export Functionality:** Exports the tournament history to a text file for record-keeping and analysis. Requires the `TournamentReporter` module.
- **Reset Functionality:** Resets the tournament, clearing all data and enabling player additions again.
- **High-Contrast UI:** The application features a high-contrast color scheme and custom fonts for improved readability.
- **Widgets:** The application incorporates various widgets to improve user experience, such as buttons, tables, input fields, list widgets, and menu bars for easy navigation and interaction.

## Requirements

- Python 3.6+
- PyQt6

## Installation

1.  Make sure you have Python 3.6 or higher installed.
2.  Install the required packages using pip:

    ```bash
    pip install PyQt6
    ```

3.  (Optional) To enable export functionality, ensure the `TournamentReporter` module is available. Place `TournamentReporter.py` in the same directory as `main.py`.

## Usage

1.  Run the `main.py` script.
2.  Add players to the tournament using the input field and "Add Player" button.
3.  Remove players by right-clicking on their name in the list and selecting "Remove Player".
4.  Click "Start Tournament" to begin the tournament.
5.  After each round, input the scores in the results table and click "Next Round" to generate the next round's pairings. Empty score fields are treated as 0.
6.  View the current standings in the standings table.
7.  Click "Round History" to review previous rounds in a dialog.
8.  Use the "Export Tournament" option in the "Tournament" menu to export the tournament data to a text file.
9.  Use the "Reset Tournament" option in the "Tournament" menu to reset the tournament.

## Notes

-   The pairing algorithm attempts to avoid rematches but may resort to them if necessary to complete a round.
-   Bye rounds are automatically assigned to the lowest-scoring player and award 1 point.
-   The `TournamentReporter` module is optional and required only for the export functionality.
-   As this is a pre-alpha version of **Gambit Paring**, you may encounter bugs or unexpected behavior. We encourage you to report any issues on our Discord server.

## License

This project is open source and available under the [MIT License](LICENSE).
