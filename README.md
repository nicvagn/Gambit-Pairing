# Swiss Paring Application

This is a desktop application for managing Swiss-system chess tournaments. It provides a graphical user interface (GUI) built with PyQt6, allowing users to:

- Add and remove players.
- Start a tournament.
- Automatically generate pairings for each round, avoiding rematches where possible.
- Input results for each round.
- View current standings.
- Review the history of pairings and results from previous rounds.
- Export tournament data to a text file.

## Features

- **Player Management:** Add players to the tournament roster via a simple input field. Players can be removed via a context menu.
- **Tournament Setup:** Starts the tournament and disables further player additions to ensure fair play.
- **Automated Pairings:** Generates pairings for each round using a greedy matching algorithm that prioritizes avoiding previous matches and assigns colors (White/Black) randomly.
- **Score Input:** A table allows for easy input of match results for each round. The application handles incomplete scores gracefully.
- **Standings Display:** Dynamically updates and displays the tournament standings based on player scores.
- **Round History:** Provides a detailed history of pairings and results from each round.
- **Export Functionality:** Exports the tournament history to a text file for record-keeping and analysis.
- **High-Contrast UI:** The application features a high-contrast color scheme and custom fonts for improved readability.

## Requirements

- Python 3.6+
- PyQt6
- `TournamentReporter` (optional, for exporting)

## Installation

1.  Make sure you have Python 3.6 or higher installed.
2.  Install the required packages using pip:

    ```bash
    pip install PyQt6
    ```

3.  (Optional) To enable export functionality, ensure the `TournamentReporter` module is available. If it's a custom module, place it in the same directory as `main.py` or ensure it's in your Python path.

## Usage

1.  Run the `main.py` script.
2.  Add players to the tournament using the input field and "Add Player" button.
3.  Click "Start Tournament" to begin the tournament.
4.  After each round, input the scores in the results table and click "Next Round" to generate the next round's pairings.
5.  View the current standings in the standings table.
6.  Click "Round History" to review previous rounds.
7.  Use the "Export Tournament" option in the "Tournament" menu to export the tournament data to a text file.
8.  Use the "Reset Tournament" option in the "Tournament" menu to reset the tournament.

## Notes

-   The pairing algorithm attempts to avoid rematches but may resort to them if necessary to complete a round.
-   Bye rounds are automatically assigned to the lowest-scoring player.
-   Empty score fields are treated as 0 when advancing to the next round, with a confirmation prompt.
-   The `TournamentReporter` module is optional and required only for the export functionality.

## License

This project is open source and available under the [MIT License](LICENSE).
