
import sys
import random
import logging
import json
import functools
import csv
from typing import List, Optional, Tuple, Set, Dict, Any
from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtCore import Qt, QDateTime, QFileInfo
from PyQt6.QtGui import QAction, QFontDatabase, QCloseEvent

# --- Logging Setup ---
# Setup logging to file and console
log_formatter = logging.Formatter("%(asctime)s [%(levelname)-5.5s] %(message)s")
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO) # Set minimum level

# File Handler
try:
    # Attempt to create a log file in the user's home directory or a temp directory
    log_dir = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.StandardLocation.AppDataLocation)
    if not log_dir:
        log_dir = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.StandardLocation.TempLocation)
    if log_dir:
        log_path = QtCore.QDir(log_dir).filePath("gambit_pairing.log")
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(log_formatter)
        root_logger.addHandler(file_handler)
        print(f"Logging to: {log_path}") # Inform user where logs are
    else:
        print("Warning: Could not determine writable location for log file.")
except Exception as e:
    print(f"Warning: Could not create log file handler: {e}")


# Console Handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
root_logger.addHandler(console_handler)


# --- Constants ---
APP_NAME = "Gambit Pairing"
APP_VERSION = "0.1.0"
SAVE_FILE_EXTENSION = ".gpf"
SAVE_FILE_FILTER = f"Gambit Pairing Files (*{SAVE_FILE_EXTENSION});;All Files (*)"
CSV_FILTER = "CSV Files (*.csv);;Text Files (*.txt)"

WIN_SCORE = 1.0
DRAW_SCORE = 0.5
LOSS_SCORE = 0.0
BYE_SCORE = 1.0

# Result types
RESULT_WHITE_WIN = "1-0"
RESULT_DRAW = "0.5-0.5"
RESULT_BLACK_WIN = "0-1"
# TODO: Add Forfeit result types and handling
# RESULT_FORFEIT_WIN_W = "1F-0"
# RESULT_FORFEIT_WIN_B = "0-1F"
# RESULT_FORFEIT_LOSS_W = "0F-1"
# RESULT_FORFEIT_LOSS_B = "1-0F"
# RESULT_DOUBLE_FORFEIT = "0F-0F"

# Tiebreaker Keys & Default Order
TB_MEDIAN = 'median'
TB_SOLKOFF = 'solkoff'
TB_CUMULATIVE = 'cumulative'
TB_CUMULATIVE_OPP = 'cumulative_opp'
TB_SONNENBORN_BERGER = 'sb'
TB_MOST_BLACKS = 'most_blacks'
TB_HEAD_TO_HEAD = 'h2h' # Internal comparison key

# Default display names for tiebreaks
TIEBREAK_NAMES = {
    TB_MEDIAN: "Median",
    TB_SOLKOFF: "Solkoff",
    TB_CUMULATIVE: "Cumulative",
    TB_CUMULATIVE_OPP: "Cumulative Opp",
    TB_SONNENBORN_BERGER: "Sonnenborn-Berger",
    TB_MOST_BLACKS: "Most Blacks",
}

# Default order used for sorting if not configured otherwise
DEFAULT_TIEBREAK_SORT_ORDER = [
    TB_MEDIAN,
    TB_SOLKOFF,
    TB_CUMULATIVE,
    TB_CUMULATIVE_OPP,
    TB_SONNENBORN_BERGER,
    TB_MOST_BLACKS,
]

# --- Utility Functions ---
def generate_id(prefix: str = "item_") -> str:
    """Generates a simple unique ID."""
    return f"{prefix}{random.randint(100000, 999999)}_{int(QDateTime.currentMSecsSinceEpoch())}"

# --- Core Classes ---

class Player:
    """Represents a player in the tournament."""
    def __init__(self, name: str, rating: Optional[int] = None, player_id: Optional[str] = None) -> None:
        self.id: str = player_id or generate_id("player_")
        self.name: str = name
        self.rating: int = rating if rating is not None else 1000
        self.score: float = 0.0
        self.is_active: bool = True # Used for withdrawals

        # History
        self.color_history: List[Optional[str]] = []
        self.opponent_ids: List[Optional[str]] = []
        self.results: List[Optional[float]] = []
        self.running_scores: List[float] = []
        self.has_received_bye: bool = False
        self.num_black_games: int = 0

        # Tiebreakers (calculated)
        self.tiebreakers: Dict[str, float] = {}

        # Runtime cache
        self._opponents_played_cache: List[Optional['Player']] = []

    def __repr__(self) -> str:
        status = "" if self.is_active else " (Inactive)"
        return f"{self.name} ({self.rating}){status}"

    def get_opponent_objects(self, players_dict: Dict[str, 'Player']) -> List[Optional['Player']]:
        """Resolves opponent IDs to Player objects using the provided dictionary."""
        # Simple caching - rebuild if length mismatch (safer than complex invalidation)
        if len(self._opponents_played_cache) != len(self.opponent_ids):
             self._opponents_played_cache = [players_dict.get(opp_id) if opp_id else None for opp_id in self.opponent_ids]
        return self._opponents_played_cache

    def get_last_two_colors(self) -> Tuple[Optional[str], Optional[str]]:
        """Returns the colors of the last two non-bye games played."""
        valid_colors = [c for c in self.color_history if c is not None]
        if len(valid_colors) >= 2: return valid_colors[-1], valid_colors[-2]
        elif len(valid_colors) == 1: return valid_colors[-1], None
        else: return None, None

    def get_color_preference(self) -> Optional[str]:
        """Determines color preference based on USCF rules (simplified)."""
        last_color, second_last_color = self.get_last_two_colors()
        if last_color and last_color == second_last_color: return "Black" if last_color == "White" else "White"
        white_count = self.color_history.count("White")
        black_count = self.num_black_games
        if white_count > black_count + 1: return "Black"
        elif black_count > white_count + 1: return "White"
        elif white_count > black_count: return "Black"
        elif black_count > white_count: return "White"
        else:
            last_played_color = self.color_history[-1] if self.color_history else None
            if last_played_color: return "Black" if last_played_color == "White" else "White"
            else: return None # No preference

    def add_round_result(self, opponent: Optional['Player'], result: float, color: Optional[str]):
        """Records the outcome of a round for the player."""
        opponent_id = opponent.id if opponent else None
        self.opponent_ids.append(opponent_id)
        self.results.append(result)
        self.score += result
        self.running_scores.append(self.score)
        self.color_history.append(color)
        if color == "Black": self.num_black_games += 1
        if opponent is None: self.has_received_bye = True
        self._opponents_played_cache = [] # Invalidate cache

    def to_dict(self) -> Dict[str, Any]:
        """Serializes player data."""
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')} # Exclude cache

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Player':
        """Deserializes player data."""
        player = cls(name=data['name'], rating=data['rating'], player_id=data['id'])
        for key, value in data.items():
             if hasattr(player, key) and not key.startswith('_'):
                  setattr(player, key, value)
        # Ensure essential lists exist if loading older format without them
        for list_attr in ['color_history', 'opponent_ids', 'results', 'running_scores']:
             if not hasattr(player, list_attr) or getattr(player, list_attr) is None:
                  setattr(player, list_attr, [])
        return player

class Tournament:
    """Manages the tournament state, pairings, results, and tiebreakers."""
    def __init__(self, players: List[Player], num_rounds: int, tiebreak_order: Optional[List[str]] = None) -> None:
        self.players: Dict[str, Player] = {p.id: p for p in players}
        self.num_rounds: int = num_rounds
        self.tiebreak_order: List[str] = tiebreak_order or list(DEFAULT_TIEBREAK_SORT_ORDER) # Use default if none provided
        self.rounds_pairings_ids: List[List[Tuple[str, str]]] = [] # (white_id, black_id)
        self.rounds_byes_ids: List[Optional[str]] = []
        self.previous_matches: Set[frozenset[str]] = set() # frozenset({p1_id, p2_id})
        self.manual_pairings: Dict[int, Dict[str, str]] = {} # {round_idx: {player_id: original_opponent_id}}

    def get_player_list(self, active_only=False) -> List[Player]:
        """Returns a list of player objects."""
        players = list(self.players.values())
        if active_only:
             return [p for p in players if p.is_active]
        return players

    def _get_active_players(self) -> List[Player]:
        """Returns a list of active players."""
        return [p for p in self.players.values() if p.is_active]

    def _get_eligible_bye_player(self, potential_bye_players: List[Player]) -> Optional[Player]:
        """Determines the bye player according to USCF rules (active, lowest rated, hasn't had bye)."""
        active_potentials = [p for p in potential_bye_players if p.is_active]
        if not active_potentials: return None
        active_potentials.sort(key=lambda p: (p.rating, p.name))
        for player in active_potentials:
            if not player.has_received_bye: return player
        return active_potentials[0] # Fallback: lowest rated active if all had byes

    def create_pairings(self, current_round: int) -> Tuple[List[Tuple[Player, Player]], Optional[Player]]:
        """Generates pairings for the next round."""
        # Implementation largely similar to v3, ensuring it uses _get_active_players()
        # and handles potential errors more gracefully.
        active_players = self._get_active_players()
        if not active_players: raise ValueError("No active players available for pairing.")

        if current_round == 1:
            # --- Round 1 Pairing (Seed-based) ---
            players_sorted = sorted(active_players, key=lambda p: (-p.rating, p.name))
            mid = len(players_sorted) // 2
            top_half, bottom_half = players_sorted[:mid], players_sorted[mid:]
            pairings, round_pairings_ids = [], []
            bye_player = None

            for p1, p2 in zip(top_half, bottom_half):
                white, black = p1, p2 # Higher seed White
                pairings.append((white, black))
                round_pairings_ids.append((white.id, black.id))
                self.previous_matches.add(frozenset({p1.id, p2.id}))

            if len(players_sorted) % 2 == 1:
                bye_player = players_sorted[-1] # Lowest rated active player
                logging.info(f"Round 1 Bye assigned to: {bye_player.name}")

            self.rounds_pairings_ids.append(round_pairings_ids)
            self.rounds_byes_ids.append(bye_player.id if bye_player else None)
            return pairings, bye_player

        else:
            # --- Subsequent Rounds Pairing (Score Group based) ---
            # NOTE: USCF requires limiting floats to one per group, backtracking to avoid rematches and better color balance.
            # TODO: Enhance pairing algorithm to restrict the float per group and implement full color-violation and backtracking logic.
            score_groups: Dict[float, List[Player]] = {}
            for p in active_players: score_groups.setdefault(p.score, []).append(p)
            sorted_scores = sorted(score_groups.keys(), reverse=True)
            pairings, round_pairings_ids = [], []
            unpaired_players = []

            for score in sorted_scores:
                group = sorted(score_groups[score], key=lambda p: (-p.rating, p.name))
                current_group_unpaired = list(unpaired_players)
                unpaired_players = []
                group.extend(current_group_unpaired)
                group.sort(key=lambda p: (-p.rating, p.name))

                logging.debug(f"Processing Score Group: {score}, Players: {[p.name for p in group]}")
                paired_in_group = set()
                temp_group = list(group)
                group_paired_indices = set()

                for i in range(len(temp_group)):
                    if i in group_paired_indices: continue
                    p1 = temp_group[i]
                    best_opponent_index = -1
                    min_violation_score = float('inf')

                    for j in range(i + 1, len(temp_group)):
                        if j in group_paired_indices: continue
                        p2 = temp_group[j]
                        if frozenset({p1.id, p2.id}) in self.previous_matches: continue

                        # Basic color violation check (as in v3)
                        pref1, pref2 = p1.get_color_preference(), p2.get_color_preference()
                        tentative_white, tentative_black = (p1, p2) if p1.rating >= p2.rating else (p2, p1)
                        color_violation = 0
                        if pref1 and tentative_white == p1 and pref1 == "Black": color_violation += 2
                        if pref1 and tentative_black == p1 and pref1 == "White": color_violation += 2
                        # ... (rest of violation checks) ...

                        if color_violation < min_violation_score:
                            min_violation_score = color_violation
                            best_opponent_index = j

                    if best_opponent_index != -1:
                        p2 = temp_group[best_opponent_index]
                        # Final color assignment (as in v3)
                        pref1, pref2 = p1.get_color_preference(), p2.get_color_preference()
                        if pref1 == "White" and pref2 == "Black": white, black = p1, p2
                        elif pref1 == "Black" and pref2 == "White": white, black = p2, p1
                        # ... (rest of color assignment) ...
                        else: white, black = (p1, p2) if p1.rating >= p2.rating else (p2, p1)

                        if white and black:
                            pairings.append((white, black))
                            round_pairings_ids.append((white.id, black.id))
                            self.previous_matches.add(frozenset({p1.id, p2.id}))
                            paired_in_group.add(p1.id)
                            paired_in_group.add(p2.id)
                            group_paired_indices.add(i)
                            group_paired_indices.add(best_opponent_index)
                            logging.debug(f"  Paired: {white.name} (W) vs {black.name} (B)")

                for i in range(len(temp_group)):
                    if i not in group_paired_indices:
                        p = temp_group[i]
                        if p.id not in paired_in_group:
                            unpaired_players.append(p)
                            logging.debug(f"  Floating down: {p.name}")

            # --- Bye Assignment ---
            bye_player = None
            if unpaired_players:
                active_unpaired = [p for p in unpaired_players if p.is_active]
                if active_unpaired:
                     lowest_score = min(p.score for p in active_unpaired)
                     eligible_for_bye = [p for p in active_unpaired if p.score == lowest_score]
                     bye_player = self._get_eligible_bye_player(eligible_for_bye)
                     if bye_player: logging.info(f"Round {current_round} Bye assigned to: {bye_player.name}")
                     else: logging.warning("Could not assign bye according to rules.") # Should ideally not happen
                else:
                     logging.warning("No active players left unpaired to receive a bye.")


            self.rounds_pairings_ids.append(round_pairings_ids)
            self.rounds_byes_ids.append(bye_player.id if bye_player else None)
            return pairings, bye_player


    def manually_adjust_pairing(self, round_index: int, player1_id: str, new_opponent_id: str) -> bool:
        """Allows manual adjustment of one player's opponent in a specific round's pairings."""
        if round_index < 0 or round_index >= len(self.rounds_pairings_ids):
            logging.error(f"Manual Adjust: Invalid round index {round_index}.")
            return False
        if round_index < self.get_completed_rounds():
             logging.error(f"Manual Adjust: Cannot adjust pairings for completed round {round_index+1}.")
             return False

        current_pairings = self.rounds_pairings_ids[round_index]
        player_found = False
        original_opponent_id = None
        pair_index = -1
        is_white = False

        # Find the player and their current opponent
        for idx, (w_id, b_id) in enumerate(current_pairings):
            if w_id == player1_id:
                player_found = True
                original_opponent_id = b_id
                pair_index = idx
                is_white = True
                break
            elif b_id == player1_id:
                player_found = True
                original_opponent_id = w_id
                pair_index = idx
                is_white = False
                break

        if not player_found:
            logging.error(f"Manual Adjust: Player {player1_id} not found in pairings for round {round_index+1}.")
            return False
        if original_opponent_id == new_opponent_id:
             logging.warning(f"Manual Adjust: Player {player1_id} is already paired with {new_opponent_id}.")
             return False # No change needed

        # --- Find the new opponent's current pairing ---
        new_opp_original_opponent_id = None
        new_opp_pair_index = -1
        new_opp_is_white = False
        for idx, (w_id, b_id) in enumerate(current_pairings):
             if w_id == new_opponent_id:
                  new_opp_original_opponent_id = b_id
                  new_opp_pair_index = idx
                  new_opp_is_white = True
                  break
             elif b_id == new_opponent_id:
                  new_opp_original_opponent_id = w_id
                  new_opp_pair_index = idx
                  new_opp_is_white = False
                  break

        if new_opp_pair_index == -1:
             logging.error(f"Manual Adjust: New opponent {new_opponent_id} not found in pairings.")
             # Could potentially allow pairing with a bye player here if needed
             return False
        if new_opp_original_opponent_id is None:
             logging.error(f"Manual Adjust: Could not determine new opponent's original partner.")
             return False

        # --- Perform the swap ---
        # Record the manual change before modifying
        if round_index not in self.manual_pairings: self.manual_pairings[round_index] = {}
        self.manual_pairings[round_index][player1_id] = original_opponent_id
        self.manual_pairings[round_index][new_opponent_id] = new_opp_original_opponent_id
        # Also record the original opponents' changes
        if original_opponent_id: self.manual_pairings[round_index][original_opponent_id] = player1_id
        if new_opp_original_opponent_id: self.manual_pairings[round_index][new_opp_original_opponent_id] = new_opponent_id


        # Update player1's pairing
        if is_white: current_pairings[pair_index] = (player1_id, new_opponent_id)
        else: current_pairings[pair_index] = (new_opponent_id, player1_id) # Assume new opponent takes original color slot

        # Update the original opponent's pairing (pair them with the new opponent's original partner)
        if new_opp_pair_index != pair_index: # Avoid modifying the same pair twice if swapping within pair
            if new_opp_is_white: # The new opponent was white
                 # Pair original_opponent_id with new_opp_original_opponent_id
                 # Need to decide colors - keep original_opponent_id's color?
                 if original_opponent_id: # Ensure original opponent exists (not a bye swap)
                     current_pairings[new_opp_pair_index] = (original_opponent_id, new_opp_original_opponent_id) if not is_white else (new_opp_original_opponent_id, original_opponent_id)
            else: # The new opponent was black
                 if original_opponent_id:
                     current_pairings[new_opp_pair_index] = (new_opp_original_opponent_id, original_opponent_id) if is_white else (original_opponent_id, new_opp_original_opponent_id)


        # Update previous matches (remove old, add new) - Be careful! This might allow rematches later.
        # It might be better *not* to update previous_matches for manual adjustments, forcing the TD to be aware.
        # Let's skip updating previous_matches for now to avoid unintended consequences.
        # if original_opponent_id: self.previous_matches.discard(frozenset({player1_id, original_opponent_id}))
        # if new_opp_original_opponent_id: self.previous_matches.discard(frozenset({new_opponent_id, new_opp_original_opponent_id}))
        # self.previous_matches.add(frozenset({player1_id, new_opponent_id}))
        # if original_opponent_id and new_opp_original_opponent_id:
        #     self.previous_matches.add(frozenset({original_opponent_id, new_opp_original_opponent_id}))

        logging.warning(f"Manual Pairing Adjustment in Round {round_index+1}: {player1_id} now paired with {new_opponent_id}. Previous pairings also adjusted.")
        return True


    def record_results(self, round_index: int, results_data: List[Tuple[str, str, float]]):
        """Records results, checking for active status and round index."""
        # Implementation similar to v3, but ensure checks use self.players dictionary
        if round_index < 0 or round_index >= len(self.rounds_pairings_ids):
            logging.error(f"Record Results: Invalid round index {round_index}")
            return False # Indicate failure

        round_pairings_ids = self.rounds_pairings_ids[round_index]
        round_bye_id = self.rounds_byes_ids[round_index]
        player_ids_in_pairings = {p_id for pair in round_pairings_ids for p_id in pair}
        processed_player_ids = set()
        success = True

        for white_id, black_id, white_score in results_data:
            # Find players
            p_white = self.players.get(white_id)
            p_black = self.players.get(black_id)

            if not (p_white and p_black):
                 logging.error(f"Record Results: Could not find players {white_id} or {black_id}.")
                 success = False; continue
            if not (p_white.is_active and p_black.is_active):
                 logging.warning(f"Record Results: Recording result for inactive player(s): {p_white}/{p_black}")
                 # Allow recording but log warning. Could add stricter checks.

            # Check if result already recorded for this round for these players
            if len(p_white.results) > round_index or len(p_black.results) > round_index:
                 logging.warning(f"Record Results: Attempt to double-record for round {round_index+1}, players {white_id}/{black_id}")
                 success = False; continue # Skip this result

            black_score = WIN_SCORE - white_score
            # TODO: Extend forfeit handling (e.g., 1F-0 or 0-1F) if needed in future.
            p_white.add_round_result(opponent=p_black, result=white_score, color="White")
            p_black.add_round_result(opponent=p_white, result=black_score, color="Black")
            processed_player_ids.add(white_id)
            processed_player_ids.add(black_id)
            logging.debug(f"Recorded result: {p_white.name} ({white_score}) vs {p_black.name} ({black_score})")

        # Record bye result
        if round_bye_id:
            p_bye = self.players.get(round_bye_id)
            if p_bye:
                 if p_bye.is_active:
                      if len(p_bye.results) == round_index: # Ensure not already recorded
                           p_bye.add_round_result(opponent=None, result=BYE_SCORE, color=None)
                           processed_player_ids.add(round_bye_id)
                           logging.debug(f"Recorded bye for {p_bye.name}")
                      else:
                           logging.warning(f"Record Results: Attempt to double-record bye for round {round_index+1} for {p_bye.name}")
                           success = False
                 else:
                      logging.warning(f"Record Results: Bye player {p_bye.name} is inactive, bye not awarded score.")
                      # Add placeholder result? Or just skip? Skipping for now.
                      # p_bye.add_round_result(opponent=None, result=0.0, color=None) # Record 0 if inactive?
                      processed_player_ids.add(round_bye_id) # Mark as processed even if inactive
            else:
                 logging.error(f"Record Results: Could not find bye player ID {round_bye_id}.")
                 success = False

        # Sanity check
        expected_ids = set(player_ids_in_pairings)
        if round_bye_id: expected_ids.add(round_bye_id)
        unprocessed = expected_ids - processed_player_ids
        if unprocessed:
            logging.warning(f"Record Results: Players/IDs in round {round_index + 1} not processed: {unprocessed}.")
            # Consider adding logic here to handle missing results (e.g., assign 0-0 automatically?)

        return success


    def compute_tiebreakers(self) -> None:
        """Calculates tiebreakers for active players based on configured order."""
        # Implementation similar to v3, but needs refinement for inactive/unplayed games
        num_rounds_played = len(self.rounds_pairings_ids)
        if num_rounds_played == 0: return

        final_scores = {p.id: p.score for p in self.players.values()}
        player_dict = self.players

        for player in self.players.values():
            if not player.is_active:
                player.tiebreakers = {}
                continue

            player.tiebreakers = {}
            opponents = player.get_opponent_objects(player_dict)
            actual_opponents = []
            opponent_final_scores = []
            sb_score = 0.0
            cumulative_opp_score = 0.0

            for i, opp in enumerate(opponents):
                 if opp is not None: # Not a bye
                      actual_opponents.append(opp)
                      # Use fixed final score at time of withdrawal if opponent inactive
                      opp_final_score = (opp.running_scores[-1] if opp.running_scores and not opp.is_active 
                                         else self.players.get(opp.id, opp).score)
                      opponent_final_scores.append(opp_final_score)

                      # Sonnenborn-Berger
                      result_against_opp = player.results[i]
                      if result_against_opp == WIN_SCORE: sb_score += opp_final_score
                      elif result_against_opp == DRAW_SCORE: sb_score += 0.5 * opp_final_score

                      # Cumulative Opponent Score (Approximation)
                      cumulative_opp_score += opp.score


            # --- True Modified Median ---
            all_opp_scores = sorted(opponent_final_scores) if opponent_final_scores else []
            max_possible_score = float(len(player.results))
            if all_opp_scores:
                if player.score > max_possible_score / 2.0:
                    # Drop lowest opponent score
                    median_score = sum(all_opp_scores[1:]) if len(all_opp_scores) > 1 else all_opp_scores[0]
                elif player.score < max_possible_score / 2.0:
                    # Drop highest opponent score
                    median_score = sum(all_opp_scores[:-1]) if len(all_opp_scores) > 1 else all_opp_scores[0]
                else:
                    # Exactly 50%: drop both lowest and highest if at least 3 rounds played; else drop one
                    median_score = sum(all_opp_scores[1:-1]) if len(all_opp_scores) >= 3 else all_opp_scores[0]
            else:
                median_score = 0.0

            player.tiebreakers[TB_MEDIAN] = median_score
            player.tiebreakers[TB_SOLKOFF] = sum(opponent_final_scores)
            player.tiebreakers[TB_CUMULATIVE] = sum(player.running_scores)
            player.tiebreakers[TB_CUMULATIVE_OPP] = cumulative_opp_score
            player.tiebreakers[TB_SONNENBORN_BERGER] = sb_score
            player.tiebreakers[TB_MOST_BLACKS] = float(player.num_black_games)
            # TODO: Implement full head-to-head calculation and store in TB_HEAD_TO_HEAD
            player.tiebreakers[TB_HEAD_TO_HEAD] = 0.0


    def _compare_players(self, p1: Player, p2: Player) -> int:
        """Comparison function using the configured tiebreak order."""
        # 1. Score
        if p1.score != p2.score: return 1 if p1.score > p2.score else -1

        # 2. Head-to-Head (full logic not yet implemented)
        h2h_score = 0.0
        found_match = False
        for i, opp_id in enumerate(p1.opponent_ids):
            if opp_id == p2.id:
                h2h_score += p1.results[i]
                found_match = True
        if found_match:
            # TODO: Refine head-to-head tiebreak to immediately decide when applicable.
            if h2h_score > 0.5: 
                return 1
            if h2h_score < 0.5: 
                return -1

        # 3. Configured Tiebreakers
        for tb_key in self.tiebreak_order: # Use configured order
            tb1 = p1.tiebreakers.get(tb_key, 0.0)
            tb2 = p2.tiebreakers.get(tb_key, 0.0)
            if tb1 != tb2: return 1 if tb1 > tb2 else -1

        # 4. Rating
        if p1.rating != p2.rating: return 1 if p1.rating > p2.rating else -1

        # 5. Name
        if p1.name != p2.name: return -1 if p1.name < p2.name else 1

        return 0

    def get_standings(self) -> List[Player]:
        """Returns active players sorted by score and configured tiebreakers."""
        active_players = self._get_active_players()
        if not active_players: return []
        self.compute_tiebreakers() # Ensure calculation
        sorted_players = sorted(
            active_players,
            key=functools.cmp_to_key(self._compare_players),
            reverse=True
        )
        return sorted_players

    def get_completed_rounds(self) -> int:
        """Returns the number of rounds for which results have been fully entered."""
        # This is approximated by the minimum number of results recorded by any active player
        # who has played at least one round. A more robust check might be needed.
        active_players = self._get_active_players()
        if not active_players: return 0
        # Find players who have played at least one game (result list not empty)
        players_with_results = [p for p in active_players if p.results]
        if not players_with_results: return 0
        return min(len(p.results) for p in players_with_results)


    def to_dict(self) -> Dict[str, Any]:
        """Serializes tournament state."""
        return {
            'app_version': APP_VERSION, # Store app version
            'num_rounds': self.num_rounds,
            'tiebreak_order': self.tiebreak_order,
            'players': [p.to_dict() for p in self.players.values()],
            'rounds_pairings_ids': self.rounds_pairings_ids,
            'rounds_byes_ids': self.rounds_byes_ids,
            'previous_matches': [list(pair) for pair in self.previous_matches],
            'manual_pairings': self.manual_pairings, # Save manual adjustments
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Tournament':
        """Deserializes tournament state."""
        # Check version compatibility if needed later
        # loaded_version = data.get('app_version')

        players = [Player.from_dict(p_data) for p_data in data.get('players', [])]
        num_rounds = data.get('num_rounds', 0)
        tiebreak_order = data.get('tiebreak_order', list(DEFAULT_TIEBREAK_SORT_ORDER)) # Load saved order

        if not players: raise ValueError("Cannot load tournament: No player data found.")
        if num_rounds <= 0:
             num_rounds = len(data.get('rounds_pairings_ids', [])) or 3
             logging.warning(f"Number of rounds not found, inferred/defaulted to {num_rounds}")

        tournament = cls(players, num_rounds, tiebreak_order) # Pass loaded tiebreak order
        tournament.rounds_pairings_ids = data.get('rounds_pairings_ids', [])
        tournament.rounds_byes_ids = data.get('rounds_byes_ids', [])
        tournament.previous_matches = set(frozenset(pair) for pair in data.get('previous_matches', []))
        tournament.manual_pairings = data.get('manual_pairings', {})
        # Convert round keys in manual_pairings back to int if needed (JSON saves keys as strings)
        tournament.manual_pairings = {int(k): v for k, v in tournament.manual_pairings.items()}


        for p in tournament.players.values(): p._opponents_played_cache = [] # Clear cache
        return tournament


# --- GUI Dialogs ---

class PlayerEditDialog(QtWidgets.QDialog):
     """Dialog to edit player name and rating."""
     # (Identical to v3)
     def __init__(self, player_name: str, player_rating: int, player_active: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Player")
        self.layout = QtWidgets.QVBoxLayout(self)

        self.name_edit = QtWidgets.QLineEdit(player_name)
        self.rating_spin = QtWidgets.QSpinBox()
        self.rating_spin.setRange(0, 4000)
        self.rating_spin.setValue(player_rating)
        self.active_check = QtWidgets.QCheckBox("Active")
        self.active_check.setChecked(player_active)
        self.active_check.setToolTip("Uncheck to mark player as withdrawn.")


        form_layout = QtWidgets.QFormLayout()
        form_layout.addRow("Name:", self.name_edit)
        form_layout.addRow("Rating:", self.rating_spin)
        form_layout.addRow(self.active_check)
        self.layout.addLayout(form_layout)

        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

     def get_data(self) -> Tuple[str, int, bool]:
        """Returns the edited name, rating, and active status."""
        name = self.name_edit.text().strip()
        rating = self.rating_spin.value()
        is_active = self.active_check.isChecked()
        return name, rating, is_active

class SettingsDialog(QtWidgets.QDialog):
    """Dialog for tournament settings (rounds, tiebreaks)."""
    def __init__(self, num_rounds: int, tiebreak_order: List[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tournament Settings")
        self.setMinimumWidth(350)

        self.current_tiebreak_order = list(tiebreak_order) # Work on a copy

        layout = QtWidgets.QVBoxLayout(self)

        # Number of Rounds
        rounds_group = QtWidgets.QGroupBox("General")
        rounds_layout = QtWidgets.QFormLayout(rounds_group)
        self.spin_num_rounds = QtWidgets.QSpinBox()
        self.spin_num_rounds.setRange(1, 50)
        self.spin_num_rounds.setValue(num_rounds)
        self.spin_num_rounds.setToolTip("Set the total number of rounds.")
        rounds_layout.addRow("Number of Rounds:", self.spin_num_rounds)
        layout.addWidget(rounds_group)

        # Tiebreak Order
        tiebreak_group = QtWidgets.QGroupBox("Tiebreak Order")
        tiebreak_layout = QtWidgets.QHBoxLayout(tiebreak_group)
        self.tiebreak_list = QtWidgets.QListWidget()
        self.tiebreak_list.setToolTip("Order in which tiebreaks are applied (higher is better). Drag to reorder.")
        self.tiebreak_list.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)
        self.populate_tiebreak_list()
        tiebreak_layout.addWidget(self.tiebreak_list)

        # Buttons for moving items
        move_button_layout = QtWidgets.QVBoxLayout()
        btn_up = QtWidgets.QPushButton("Up")
        btn_down = QtWidgets.QPushButton("Down")
        btn_up.clicked.connect(self.move_tiebreak_up)
        btn_down.clicked.connect(self.move_tiebreak_down)
        move_button_layout.addStretch()
        move_button_layout.addWidget(btn_up)
        move_button_layout.addWidget(btn_down)
        move_button_layout.addStretch()
        tiebreak_layout.addLayout(move_button_layout)
        layout.addWidget(tiebreak_group)


        # Standard buttons
        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def populate_tiebreak_list(self):
        """Fills the list widget with current tiebreak order."""
        self.tiebreak_list.clear()
        for tb_key in self.current_tiebreak_order:
            display_name = TIEBREAK_NAMES.get(tb_key, tb_key) # Use display name
            item = QtWidgets.QListWidgetItem(display_name)
            item.setData(Qt.ItemDataRole.UserRole, tb_key) # Store key in item data
            self.tiebreak_list.addItem(item)

    def move_tiebreak_up(self):
        """Moves the selected tiebreak item up one position."""
        current_row = self.tiebreak_list.currentRow()
        if current_row > 0:
            item = self.tiebreak_list.takeItem(current_row)
            self.tiebreak_list.insertItem(current_row - 1, item)
            self.tiebreak_list.setCurrentRow(current_row - 1)
            self.update_order_from_list()

    def move_tiebreak_down(self):
        """Moves the selected tiebreak item down one position."""
        current_row = self.tiebreak_list.currentRow()
        if current_row < self.tiebreak_list.count() - 1:
            item = self.tiebreak_list.takeItem(current_row)
            self.tiebreak_list.insertItem(current_row + 1, item)
            self.tiebreak_list.setCurrentRow(current_row + 1)
            self.update_order_from_list()

    def update_order_from_list(self):
         """Updates the internal order based on the list widget items."""
         self.current_tiebreak_order = [self.tiebreak_list.item(i).data(Qt.ItemDataRole.UserRole)
                                        for i in range(self.tiebreak_list.count())]

    def accept(self):
         """Update the order when OK is clicked."""
         self.update_order_from_list()
         super().accept()


    def get_settings(self) -> Tuple[int, List[str]]:
        """Returns the selected number of rounds and tiebreak order."""
        return self.spin_num_rounds.value(), self.current_tiebreak_order


class ManualPairDialog(QtWidgets.QDialog):
     """Dialog to manually select a new opponent for a player."""
     def __init__(self, player_name: str, current_opponent_name: str, available_opponents: List[Player], parent=None):
          super().__init__(parent)
          self.setWindowTitle(f"Adjust Pairing for {player_name}")
          self.setMinimumWidth(300)

          self.available_opponents = available_opponents
          self.selected_opponent_id = None

          layout = QtWidgets.QVBoxLayout(self)
          layout.addWidget(QtWidgets.QLabel(f"Current Opponent: {current_opponent_name}"))
          layout.addWidget(QtWidgets.QLabel("Select New Opponent:"))

          self.opponent_combo = QtWidgets.QComboBox()
          self.opponent_combo.addItem("", None) # Add empty option
          for opp in sorted(available_opponents, key=lambda p: p.name):
               self.opponent_combo.addItem(f"{opp.name} ({opp.rating})", opp.id)
          layout.addWidget(self.opponent_combo)

          self.buttons = QtWidgets.QDialogButtonBox(
               QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
          )
          self.buttons.accepted.connect(self.accept)
          self.buttons.rejected.connect(self.reject)
          layout.addWidget(self.buttons)

     def accept(self):
          """Store the selected opponent ID before accepting."""
          self.selected_opponent_id = self.opponent_combo.currentData()
          if not self.selected_opponent_id:
               QtWidgets.QMessageBox.warning(self, "Selection Error", "Please select a new opponent.")
               return # Don't close dialog
          super().accept()

     def get_selected_opponent_id(self) -> Optional[str]:
          return self.selected_opponent_id

# --- Main Application Window ---

class SwissTournamentApp(QtWidgets.QMainWindow):
    """Main application window for the Swiss Tournament."""
    def __init__(self) -> None:
        super().__init__()
        self.tournament: Optional[Tournament] = None
        self.current_round_index: int = 0 # Index of the round being prepared/displayed
        self.last_recorded_results_data: List[Tuple[str, str, float]] = [] # For undo
        self._current_filepath: Optional[str] = None # For Save/Save As
        self._dirty: bool = False # Flag for unsaved changes

        self._setup_ui()
        self._update_ui_state()

    def _setup_ui(self):
        """Sets up the main UI elements."""
        self.setWindowTitle(APP_NAME)
        self.setGeometry(100, 100, 1000, 800) # Increased size
        self.setWindowIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_ComputerIcon)) # Generic icon

        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QtWidgets.QVBoxLayout(self.central_widget)

        self._setup_menu()
        self._setup_toolbar()
        self._setup_main_panel() # Creates the tab widget

        self.statusBar().showMessage("Ready - Create New or Load Tournament.")
        logging.info(f"{APP_NAME} v{APP_VERSION} started.")

    def _setup_menu(self):
        """Sets up the menu bar."""
        menu_bar = self.menuBar()
        # --- File Menu ---
        file_menu = menu_bar.addMenu("&File")
        self.new_action = self._create_action("&New Tournament...", self.prompt_new_tournament, "Ctrl+N", "Create a new tournament file")
        self.load_action = self._create_action("&Load Tournament...", self.load_tournament, "Ctrl+O", "Load a tournament from a file")
        self.save_action = self._create_action("&Save Tournament", self.save_tournament, "Ctrl+S", "Save the current tournament")
        self.save_as_action = self._create_action("Save Tournament &As...", lambda: self.save_tournament(save_as=True), "Ctrl+Shift+S", "Save the current tournament to a new file")
        file_menu.addSeparator()
        self.import_players_action = self._create_action("&Import Players from CSV...", self.import_players_csv, tooltip="Import players from a CSV file (Name,Rating)")
        self.export_players_action = self._create_action("&Export Players to CSV...", self.export_players_csv, tooltip="Export registered players to CSV")
        self.export_standings_action = self._create_action("&Export Standings...", self.export_standings, tooltip="Export current standings to CSV or Text")
        file_menu.addAction(self.import_players_action)
        file_menu.addAction(self.export_players_action)
        file_menu.addAction(self.export_standings_action)
        file_menu.addSeparator()
        self.settings_action = self._create_action("S&ettings...", self.show_settings_dialog, tooltip="Configure tournament settings (rounds, tiebreaks)")
        file_menu.addSeparator()
        self.exit_action = self._create_action("E&xit", self.close, "Ctrl+Q", "Exit the application")
        file_menu.addActions([self.new_action, self.load_action, self.save_action, self.save_as_action])
        file_menu.addSeparator()
        file_menu.addAction(self.settings_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        # --- Tournament Menu ---
        tournament_menu = menu_bar.addMenu("&Tournament")
        self.start_action = self._create_action("&Start Tournament", self.start_tournament, tooltip="Start the tournament with current players/settings")
        self.prepare_round_action = self._create_action("&Prepare Next Round", self.prepare_next_round, tooltip="Generate pairings for the next round")
        self.record_results_action = self._create_action("&Record Results && Advance", self.record_and_advance, tooltip="Save results for the current round")
        self.undo_results_action = self._create_action("&Undo Last Results", self.undo_last_results, tooltip="Revert the last recorded round")
        tournament_menu.addActions([self.start_action, self.prepare_round_action, self.record_results_action, self.undo_results_action])

        # --- Player Menu ---
        player_menu = menu_bar.addMenu("&Players")
        self.add_player_action = self._create_action("&Add Player...", self.focus_add_player_input, tooltip="Focus the input field to add a player")
        # Add Withdraw/Reactivate actions later if needed
        player_menu.addAction(self.add_player_action)

        # --- View Menu ---
        view_menu = menu_bar.addMenu("&View")
        self.view_control_action = view_menu.addAction("Tournament &Control")
        self.view_control_action.triggered.connect(lambda: self.tabs.setCurrentWidget(self.tournament_tab))
        self.view_standings_action = view_menu.addAction("&Standings")
        self.view_standings_action.triggered.connect(lambda: self.tabs.setCurrentWidget(self.standings_tab))
        self.view_crosstable_action = view_menu.addAction("&Cross-Table")
        self.view_crosstable_action.triggered.connect(lambda: self.tabs.setCurrentWidget(self.crosstable_tab))
        self.view_log_action = view_menu.addAction("History &Log")
        self.view_log_action.triggered.connect(lambda: self.tabs.setCurrentWidget(self.history_tab))

        # --- Help Menu ---
        help_menu = menu_bar.addMenu("&Help")
        self.about_action = self._create_action("&About...", self.show_about_dialog, tooltip="Show application information")
        help_menu.addAction(self.about_action)


    def _create_action(self, text: str, slot: callable, shortcut: str = "", tooltip: str = "") -> QAction:
        """Helper to create a QAction."""
        action = QAction(text, self)
        action.triggered.connect(slot)
        if shortcut: action.setShortcut(QtGui.QKeySequence(shortcut))
        if tooltip: action.setToolTip(tooltip); action.setStatusTip(tooltip)
        return action

    def _setup_toolbar(self):
        """Sets up the main toolbar."""
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.setIconSize(QtCore.QSize(24, 24)) # Slightly larger icons
        # Use standard icons where appropriate
        self.new_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileIcon))
        self.load_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogOpenButton))
        self.save_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogSaveButton))
        self.start_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MediaPlay))
        self.prepare_round_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MediaSkipForward))
        self.record_results_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogApplyButton)) # Use Apply icon
        self.undo_results_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_ArrowBack))

        toolbar.addAction(self.new_action)
        toolbar.addAction(self.load_action)
        toolbar.addAction(self.save_action)
        toolbar.addSeparator()
        toolbar.addAction(self.start_action)
        toolbar.addAction(self.prepare_round_action)
        toolbar.addAction(self.record_results_action)
        toolbar.addAction(self.undo_results_action)

    def _setup_main_panel(self):
        """Sets up the main tabbed content area."""
        self.tabs = QtWidgets.QTabWidget()
        self.main_layout.addWidget(self.tabs)

        # --- Tournament Control Tab ---
        self.tournament_tab = QtWidgets.QWidget()
        tab_layout = QtWidgets.QVBoxLayout(self.tournament_tab)
        # (Layout similar to v3, with minor adjustments)
        top_splitter = QtWidgets.QSplitter(Qt.Orientation.Horizontal)
        # Player Input Section
        player_group = QtWidgets.QGroupBox("Players")
        player_group.setToolTip("Manage players before starting. Right-click list items.")
        player_group_layout = QtWidgets.QVBoxLayout(player_group)
        input_layout = QtWidgets.QHBoxLayout()
        self.input_player_line = QtWidgets.QLineEdit()
        self.input_player_line.setPlaceholderText("Enter player name (optional rating)")
        self.input_player_line.returnPressed.connect(self.add_player)
        self.btn_add_player = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileIcon), text=" Add Player")
        self.btn_add_player.setToolTip("Add Player")
        self.btn_add_player.clicked.connect(self.add_player)
        input_layout.addWidget(self.input_player_line)
        input_layout.addWidget(self.btn_add_player)
        player_group_layout.addLayout(input_layout)
        self.list_players = QtWidgets.QListWidget()
        self.list_players.setToolTip("Registered players. Right-click to Edit/Withdraw/Remove before start.")
        self.list_players.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_players.customContextMenuRequested.connect(self.on_player_context_menu)
        self.list_players.setAlternatingRowColors(True)
        player_group_layout.addWidget(self.list_players)
        top_splitter.addWidget(player_group)
        # Action Section (Removed rounds spinner - moved to Settings)
        action_group = QtWidgets.QGroupBox("Tournament Control")
        action_group_layout = QtWidgets.QVBoxLayout(action_group)
        self.btn_start = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MediaPlay), text=" Start Tournament")
        self.btn_start.setToolTip("Start the tournament")
        self.btn_start.clicked.connect(self.start_tournament)
        self.btn_next = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MediaSkipForward), text=" Prepare Next Round")
        self.btn_next.setToolTip("Generate pairings")
        self.btn_next.clicked.connect(self.prepare_next_round)
        self.btn_record = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogApplyButton), text=" Record Results && Advance")
        self.btn_record.setToolTip("Save results and advance")
        self.btn_record.clicked.connect(self.record_and_advance)
        self.btn_undo = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_ArrowBack), text=" Undo Last Results")
        self.btn_undo.setToolTip("Revert last round")
        self.btn_undo.clicked.connect(self.undo_last_results)
        action_group_layout.addWidget(self.btn_start)
        action_group_layout.addWidget(self.btn_next)
        action_group_layout.addWidget(self.btn_record)
        action_group_layout.addWidget(self.btn_undo)
        action_group_layout.addStretch()
        top_splitter.addWidget(action_group)
        top_splitter.setSizes([350, 150])
        tab_layout.addWidget(top_splitter)
        # Pairings/Results Table
        self.round_group = QtWidgets.QGroupBox("Current Round Pairings & Results")
        round_layout = QtWidgets.QVBoxLayout(self.round_group)
        self.table_pairings = QtWidgets.QTableWidget(0, 5)
        self.table_pairings.setHorizontalHeaderLabels(["White", "Black", "Result", "Quick Result", "Action"]) # Added Action col
        # ... (resize modes as before) ...
        self.table_pairings.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table_pairings.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table_pairings.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.table_pairings.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.table_pairings.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.ResizeToContents) # Action button
        self.table_pairings.verticalHeader().setVisible(False)
        self.table_pairings.setAlternatingRowColors(True)
        self.table_pairings.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        round_layout.addWidget(self.table_pairings)
        self.lbl_bye = QtWidgets.QLabel("Bye: None")
        round_layout.addWidget(self.lbl_bye)
        tab_layout.addWidget(self.round_group)
        self.tabs.addTab(self.tournament_tab, "Tournament Control")

        # --- Standings Tab ---
        self.standings_tab = QtWidgets.QWidget()
        standings_tab_layout = QtWidgets.QVBoxLayout(self.standings_tab)
        self.standings_group = QtWidgets.QGroupBox("Standings")
        standings_layout = QtWidgets.QVBoxLayout(self.standings_group)
        # Tiebreaker headers will be dynamically generated based on config
        self.table_standings = QtWidgets.QTableWidget(0, 3) # Start with Rank, Player, Score
        self.table_standings.setHorizontalHeaderLabels(["Rank", "Player", "Score"])
        self.table_standings.setToolTip("Player standings sorted by Score and configured Tiebreakers.")
        # ... (resize modes, tooltips, etc. as before, applied dynamically) ...
        self.table_standings.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table_standings.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_standings.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_standings.setAlternatingRowColors(True)
        standings_layout.addWidget(self.table_standings)
        standings_tab_layout.addWidget(self.standings_group)
        self.tabs.addTab(self.standings_tab, "Standings")

        # --- Cross-Table Tab ---
        self.crosstable_tab = QtWidgets.QWidget()
        crosstable_tab_layout = QtWidgets.QVBoxLayout(self.crosstable_tab)
        self.crosstable_group = QtWidgets.QGroupBox("Cross-Table")
        crosstable_layout = QtWidgets.QVBoxLayout(self.crosstable_group)
        self.table_crosstable = QtWidgets.QTableWidget(0, 0) # Will be populated dynamically
        self.table_crosstable.setToolTip("Grid showing results between players.")
        self.table_crosstable.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_crosstable.setAlternatingRowColors(True)
        # Adjust font size for potentially dense table
        font = self.table_crosstable.font()
        font.setPointSize(font.pointSize() - 1)
        self.table_crosstable.setFont(font)
        crosstable_layout.addWidget(self.table_crosstable)
        crosstable_tab_layout.addWidget(self.crosstable_group)
        self.tabs.addTab(self.crosstable_tab, "Cross-Table")


        # --- History Log Tab ---
        self.history_tab = QtWidgets.QWidget()
        history_layout = QtWidgets.QVBoxLayout(self.history_tab)
        self.history_view = QtWidgets.QPlainTextEdit()
        self.history_view.setReadOnly(True)
        self.history_view.setToolTip("Log of pairings, results, and actions.")
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        self.history_view.setFont(font)
        history_layout.addWidget(self.history_view)
        self.tabs.addTab(self.history_tab, "History Log")

    def _update_ui_state(self):
        """Enable/disable UI elements based on tournament state."""
        tournament_exists = self.tournament is not None
        # Check based on completed rounds vs total rounds
        completed_rounds = self.tournament.get_completed_rounds() if tournament_exists else 0
        total_rounds = self.tournament.num_rounds if tournament_exists else 0
        pairings_generated_count = len(self.tournament.rounds_pairings_ids) if tournament_exists else 0

        tournament_started = tournament_exists and pairings_generated_count > 0
        can_start = tournament_exists and not tournament_started and len(self.tournament.players) >= 2
        # Can prepare if results for last generated round are in (completed == generated) AND not all rounds generated
        can_prepare_next = tournament_exists and tournament_started and \
                           completed_rounds == pairings_generated_count and \
                           pairings_generated_count < total_rounds
        # Can record if pairings generated > completed rounds
        can_record = tournament_exists and tournament_started and pairings_generated_count > completed_rounds
        # Fix: Convert last_recorded_results_data to a boolean.
        can_undo = tournament_exists and completed_rounds > 0 and bool(self.last_recorded_results_data)

        # File Menu / Toolbar
        self.save_action.setEnabled(tournament_exists)
        self.save_as_action.setEnabled(tournament_exists)
        self.export_standings_action.setEnabled(tournament_exists and completed_rounds > 0)
        self.settings_action.setEnabled(True) # Always allow settings? Or disable during round? Allow for now.
        self.import_players_action.setEnabled(not tournament_started)
        self.export_players_action.setEnabled(tournament_exists and len(self.tournament.players) > 0)

        # Tournament Menu / Toolbar / Buttons
        self.start_action.setEnabled(can_start)
        self.btn_start.setEnabled(can_start)
        self.prepare_round_action.setEnabled(can_prepare_next)
        self.btn_next.setEnabled(can_prepare_next)
        self.record_results_action.setEnabled(can_record)
        self.btn_record.setEnabled(can_record)
        self.undo_results_action.setEnabled(can_undo)
        self.btn_undo.setEnabled(can_undo)

        # Player Management
        can_manage_players = not tournament_started
        self.input_player_line.setEnabled(can_manage_players)
        self.btn_add_player.setEnabled(can_manage_players)
        # List enabled always, but context menu checks started status
        self.list_players.setEnabled(True)
        self.add_player_action.setEnabled(can_manage_players)

        # Set status bar message
        if not tournament_exists: status = "Ready - Create New or Load Tournament."
        elif not tournament_started: status = "Add players, check Settings, then Start Tournament."
        elif can_record: status = f"Round {completed_rounds + 1} pairings ready. Enter results."
        elif can_prepare_next: status = f"Round {completed_rounds} results recorded. Prepare Round {completed_rounds + 1}."
        elif completed_rounds == total_rounds: status = f"Tournament finished after {total_rounds} rounds."
        else: status = "Tournament in progress."
        self.statusBar().showMessage(status)

        # Update window title based on file path and dirty status
        title = APP_NAME
        if self._current_filepath:
             title += f" - {QFileInfo(self._current_filepath).fileName()}"
        if self._dirty:
             title += "*"
        self.setWindowTitle(title)


    def mark_dirty(self):
        """Marks the current tournament state as modified."""
        if not self._dirty:
             self._dirty = True
             self._update_ui_state() # Update window title

    def mark_clean(self):
        """Marks the current tournament state as saved."""
        if self._dirty:
             self._dirty = False
             self._update_ui_state()


    def prompt_new_tournament(self):
        """Creates a new, empty tournament."""
        if not self.check_save_before_proceeding(): return
        self.reset_tournament_state()
        # Show settings dialog immediately for new tournament
        if self.show_settings_dialog():
             num_rounds = self.tournament.num_rounds # Get rounds from dialog result
             tiebreaks = self.tournament.tiebreak_order
             self.tournament = Tournament([], num_rounds=num_rounds, tiebreak_order=tiebreaks)
             self.update_history_log("--- New Tournament Created ---")
             self.mark_dirty() # New tournament is unsaved
             self._update_ui_state()
             self.update_standings_table_headers() # Update headers based on new settings
        else:
             # User cancelled settings dialog, don't create tournament
             self.reset_tournament_state()


    def show_settings_dialog(self) -> bool:
         """Shows the settings dialog and updates tournament if OK clicked."""
         if not self.tournament:
              # If no tournament exists, create a temporary default one for the dialog
              temp_rounds = 3
              temp_tiebreaks = list(DEFAULT_TIEBREAK_SORT_ORDER)
         else:
              temp_rounds = self.tournament.num_rounds
              temp_tiebreaks = self.tournament.tiebreak_order

         dialog = SettingsDialog(temp_rounds, temp_tiebreaks, self)
         tournament_started = self.tournament and len(self.tournament.rounds_pairings_ids) > 0
         dialog.spin_num_rounds.setEnabled(not tournament_started) # Lock rounds after start

         if dialog.exec():
              new_rounds, new_tiebreaks = dialog.get_settings()
              if self.tournament:
                   # Check if settings changed
                   rounds_changed = self.tournament.num_rounds != new_rounds and not tournament_started
                   tiebreaks_changed = self.tournament.tiebreak_order != new_tiebreaks

                   if rounds_changed:
                        self.tournament.num_rounds = new_rounds
                        self.update_history_log(f"Number of rounds set to {new_rounds}.")
                        self.mark_dirty()
                   if tiebreaks_changed:
                        self.tournament.tiebreak_order = new_tiebreaks
                        self.update_history_log(f"Tiebreak order updated: {', '.join(TIEBREAK_NAMES.get(k, k) for k in new_tiebreaks)}")
                        self.mark_dirty()
                        self.update_standings_table_headers() # Update headers immediately
                        self.update_standings_table() # Recalculate/sort with new order

              else:
                   # Store settings from dialog for when tournament is created
                   self.tournament = Tournament([], num_rounds=new_rounds, tiebreak_order=new_tiebreaks)

              self._update_ui_state()
              return True # Settings were accepted
         return False # Settings were cancelled

    def focus_add_player_input(self):
        """Sets focus to the player input line."""
        tournament_started = self.tournament and len(self.tournament.rounds_pairings_ids) > 0
        if not tournament_started:
             self.input_player_line.setFocus()
        else:
             QtWidgets.QMessageBox.information(self,"Info", "Cannot add players after tournament has started.")


    def on_player_context_menu(self, point: QtCore.QPoint) -> None:
        """Handles right-click context menu on the player list."""
        item = self.list_players.itemAt(point)
        if not item or not self.tournament: return

        player_id = item.data(Qt.ItemDataRole.UserRole)
        player = self.tournament.players.get(player_id)
        if not player: return

        tournament_started = len(self.tournament.rounds_pairings_ids) > 0

        menu = QtWidgets.QMenu(self)
        edit_action = menu.addAction("Edit Player...")
        withdraw_action = menu.addAction("Withdraw Player" if player.is_active else "Reactivate Player")
        remove_action = menu.addAction("Remove Player")

        edit_action.setEnabled(not tournament_started) # Can only edit before start
        remove_action.setEnabled(not tournament_started) # Can only remove before start
        withdraw_action.setEnabled(tournament_started) # Can only withdraw after start

        action = menu.exec(self.list_players.mapToGlobal(point))

        if action == edit_action:
             dialog = PlayerEditDialog(player.name, player.rating, player.is_active, self)
             dialog.active_check.setEnabled(False) # Don't allow changing active status here
             if dialog.exec():
                  new_name, new_rating, _ = dialog.get_data()
                  if new_name:
                       is_duplicate = any(p.name == new_name for p_id, p in self.tournament.players.items() if p_id != player_id)
                       if is_duplicate: QtWidgets.QMessageBox.warning(self, "Edit Error", f"Another player named '{new_name}' already exists.")
                       else:
                            player.name = new_name
                            player.rating = new_rating
                            item.setText(f"{player.name} ({player.rating})")
                            self.update_history_log(f"Player '{player.name}' details updated.")
                            self.mark_dirty()
                  else: QtWidgets.QMessageBox.warning(self, "Edit Error", "Player name cannot be empty.")

        elif action == withdraw_action:
             player.is_active = not player.is_active
             status = "Withdrawn" if not player.is_active else "Reactivated"
             item.setText(f"{player.name} ({player.rating})" + (" (Inactive)" if not player.is_active else ""))
             item.setForeground(QtGui.QColor("gray") if not player.is_active else self.list_players.palette().color(QtGui.QPalette.ColorRole.Text))
             self.update_history_log(f"Player '{player.name}' marked as {status}.")
             self.mark_dirty()
             self.update_standings_table() # Update standings to reflect active status change

        elif action == remove_action:
             reply = QtWidgets.QMessageBox.question(self, "Remove Player", f"Remove player '{player.name}' permanently?",
                                                 QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                                                 QtWidgets.QMessageBox.StandardButton.No)
             if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                  row = self.list_players.row(item)
                  self.list_players.takeItem(row)
                  del self.tournament.players[player_id]
                  self.update_history_log(f"Player '{player.name}' removed.")
                  self.mark_dirty()
                  self._update_ui_state()


    def add_player(self) -> None:
        """Adds a player."""
        # (Logic similar to v3, ensures tournament exists)
        tournament_started = self.tournament and len(self.tournament.rounds_pairings_ids) > 0
        if tournament_started:
            QtWidgets.QMessageBox.warning(self, "Tournament Active", "Cannot add players after the tournament has started.")
            return
        if not self.tournament:
             QtWidgets.QMessageBox.warning(self, "Add Player Error", "Create or load a tournament first.")
             return

        line_text = self.input_player_line.text().strip()
        if not line_text: return
        name, rating = self.parse_player_input(line_text)

        if any(p.name == name for p in self.tournament.players.values()):
            QtWidgets.QMessageBox.warning(self, "Duplicate Player", f"Player '{name}' already exists.")
            return

        new_player = Player(name, rating)
        self.tournament.players[new_player.id] = new_player
        self.add_player_to_list_widget(new_player)
        self.input_player_line.clear()
        self.statusBar().showMessage(f"Added player: {name}")
        self.update_history_log(f"Player '{name}' ({new_player.rating}) added.")
        self.mark_dirty()
        self._update_ui_state()

    def parse_player_input(self, text: str) -> Tuple[str, Optional[int]]:
         """Parses 'Name Rating' or 'Name' input."""
         name = text.strip()
         rating = None
         parts = text.split()
         if len(parts) > 1:
              try:
                   rating_part = parts[-1]
                   if rating_part.isdigit() and 0 <= int(rating_part) <= 4000:
                        rating = int(rating_part)
                        name = " ".join(parts[:-1]).strip()
              except ValueError: pass # Last part wasn't a valid integer rating
         return name, rating

    def add_player_to_list_widget(self, player: Player):
         """Adds a player object to the QListWidget."""
         display_text = f"{player.name} ({player.rating})"
         if not player.is_active: display_text += " (Inactive)"
         list_item = QtWidgets.QListWidgetItem(display_text)
         list_item.setData(Qt.ItemDataRole.UserRole, player.id)
         list_item.setToolTip(f"ID: {player.id}")
         if not player.is_active:
              list_item.setForeground(QtGui.QColor("gray"))
         self.list_players.addItem(list_item)


    def import_players_csv(self):
         """Imports players from a CSV file (Name,Rating)."""
         if self.tournament and len(self.tournament.rounds_pairings_ids) > 0:
              QtWidgets.QMessageBox.warning(self, "Import Error", "Cannot import players after tournament has started.")
              return
         if not self.tournament:
              QtWidgets.QMessageBox.warning(self, "Import Error", "Create or load a tournament first.")
              return

         filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Import Players", "", CSV_FILTER)
         if not filename: return

         imported_count = 0
         skipped_count = 0
         try:
              with open(filename, 'r', encoding='utf-8-sig') as f: # Use utf-8-sig to handle potential BOM
                   reader = csv.reader(f)
                   header = next(reader, None) # Skip header row if present
                   if header and header[0].lower() == 'name' and header[1].lower() == 'rating':
                        logging.info("CSV header detected and skipped.")
                   else:
                        f.seek(0) # Rewind if no header or unexpected header

                   for row in reader:
                        if len(row) >= 1:
                             name = row[0].strip()
                             rating = None
                             if len(row) >= 2:
                                  try: rating = int(row[1].strip())
                                  except ValueError: rating = None # Ignore invalid ratings

                             if name:
                                  # Check for duplicates before adding
                                  if any(p.name == name for p in self.tournament.players.values()):
                                       logging.warning(f"Skipping duplicate player name during import: {name}")
                                       skipped_count += 1
                                  else:
                                       new_player = Player(name, rating)
                                       self.tournament.players[new_player.id] = new_player
                                       self.add_player_to_list_widget(new_player)
                                       imported_count += 1
                             else:
                                  logging.warning(f"Skipping row with empty name during import: {row}")
                                  skipped_count += 1

              msg = f"Imported {imported_count} players."
              if skipped_count > 0: msg += f" Skipped {skipped_count} duplicates/invalid rows."
              QtWidgets.QMessageBox.information(self, "Import Complete", msg)
              self.update_history_log(f"Imported {imported_count} players from {QFileInfo(filename).fileName()}. Skipped {skipped_count}.")
              self.mark_dirty()
              self._update_ui_state()

         except Exception as e:
              logging.exception(f"Error importing players from {filename}:")
              QtWidgets.QMessageBox.critical(self, "Import Error", f"Could not import players:\n{e}")
              self.statusBar().showMessage("Error importing players.")


    def export_players_csv(self):
        """Exports registered players to a CSV file."""
        if not self.tournament or not self.tournament.players:
            QtWidgets.QMessageBox.information(self, "Export Error", "No players available to export.")
            return
        filename, selected_filter = QtWidgets.QFileDialog.getSaveFileName(self, "Export Players", "", "CSV Files (*.csv);;Text Files (*.txt)")
        if not filename:
            return
        try:
            is_csv = selected_filter.startswith("CSV")
            delimiter = "," if is_csv else "\t"
            with open(filename, "w", encoding="utf-8", newline='') as f:
                writer = csv.writer(f, delimiter=delimiter)
                writer.writerow(["Name", "Rating", "Active"])
                for player in self.tournament.players.values():
                    writer.writerow([player.name, player.rating, "Yes" if player.is_active else "No"])
            QtWidgets.QMessageBox.information(self, "Export Successful", f"Players exported to {filename}")
            self.statusBar().showMessage(f"Players exported to {filename}")
        except Exception as e:
            logging.exception("Error exporting players:")
            QtWidgets.QMessageBox.critical(self, "Export Error", f"Could not export players:\n{e}")
            self.statusBar().showMessage("Error exporting players.")


    def reset_tournament_state(self):
         """Clears the current tournament data and resets the UI."""
         self.tournament = None
         self.current_round_index = 0
         self.last_recorded_results_data = []
         self._current_filepath = None
         self._dirty = False # Reset dirty flag

         self.list_players.clear()
         self.table_pairings.setRowCount(0)
         self.table_standings.setRowCount(0)
         self.table_crosstable.setRowCount(0)
         self.table_crosstable.setColumnCount(0)
         self.history_view.clear()
         self.lbl_bye.setText("Bye: None")
         self.round_group.setTitle("Current Round Pairings & Results")

         self.update_history_log("--- Tournament Reset ---")
         self._update_ui_state()


    def start_tournament(self) -> None:
        """Starts the tournament."""
        # (Logic similar to v3, ensures tournament exists and has players)
        if not self.tournament: QtWidgets.QMessageBox.warning(self, "Start Error", "No tournament loaded."); return
        if len(self.tournament.players) < 2: QtWidgets.QMessageBox.warning(self, "Start Error", "Add at least two players."); return
        if len(self.tournament.rounds_pairings_ids) > 0: QtWidgets.QMessageBox.warning(self, "Start Error", "Tournament already started."); return

        # Confirm start
        reply = QtWidgets.QMessageBox.question(self, "Start Tournament",
                                             f"Start a {self.tournament.num_rounds}-round tournament with {len(self.tournament.players)} players?",
                                             QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                                             QtWidgets.QMessageBox.StandardButton.Yes)
        if reply != QtWidgets.QMessageBox.StandardButton.Yes: return


        self.current_round_index = 0
        self.statusBar().showMessage(f"Tournament started ({self.tournament.num_rounds} rounds). Prepare Round 1.")
        self.update_history_log(f"--- Tournament Started ({self.tournament.num_rounds} Rounds) ---")
        self.mark_dirty()
        self.prepare_next_round()
        self._update_ui_state()


    def prepare_next_round(self) -> None:
        """Generates and displays pairings for the next round."""
        # (Logic similar to v3)
        if not self.tournament: return
        if len(self.tournament.rounds_pairings_ids) >= self.tournament.num_rounds:
             QtWidgets.QMessageBox.information(self,"Tournament End", "All rounds have been generated.")
             self._update_ui_state(); return

        round_to_prepare = len(self.tournament.rounds_pairings_ids)
        display_round_number = round_to_prepare + 1
        self.statusBar().showMessage(f"Generating pairings for Round {display_round_number}...")
        QtWidgets.QApplication.processEvents()

        try:
            pairings, bye_player = self.tournament.create_pairings(display_round_number)
            self.round_group.setTitle(f"Round {display_round_number} Pairings & Results Input")
            self.display_pairings_for_input(pairings, bye_player)
            self.update_history_log(f"--- Round {display_round_number} Pairings Generated ---")
            for white, black in pairings: self.update_history_log(f"  {white.name} (W) vs {black.name} (B)")
            if bye_player: self.update_history_log(f"  Bye: {bye_player.name}")
            self.update_history_log("-" * 20)
            self.statusBar().showMessage(f"Round {display_round_number} pairings ready. Enter results.")
            self.mark_dirty() # Generating pairings modifies state
        except Exception as e:
            logging.exception("Error generating pairings:")
            QtWidgets.QMessageBox.critical(self, "Pairing Error", f"Pairing generation failed:\n{e}")
            self.statusBar().showMessage("Error generating pairings.")
        finally:
             self._update_ui_state()


    def display_pairings_for_input(self, pairings: List[Tuple[Player, Player]], bye_player: Optional[Player]):
        """Populates the pairings table."""
        # (Similar to v3, but adds Manual Adjust button)
        self.table_pairings.clearContents()
        self.table_pairings.setRowCount(len(pairings))

        for row, (white, black) in enumerate(pairings):
            # White/Black items with tooltips (show inactive status)
            item_white = QtWidgets.QTableWidgetItem(f"{white.name} ({white.rating})" + (" (I)" if not white.is_active else ""))
            item_white.setFlags(item_white.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item_white.setToolTip(f"Color History: {' '.join(c or '_' for c in white.color_history)}")
            if not white.is_active: item_white.setForeground(QtGui.QColor("gray"))
            self.table_pairings.setItem(row, 0, item_white)

            item_black = QtWidgets.QTableWidgetItem(f"{black.name} ({black.rating})" + (" (I)" if not black.is_active else ""))
            item_black.setFlags(item_black.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item_black.setToolTip(f"Color History: {' '.join(c or '_' for c in black.color_history)}")
            if not black.is_active: item_black.setForeground(QtGui.QColor("gray"))
            self.table_pairings.setItem(row, 1, item_black)

            # Result Combo Box
            combo_result = QtWidgets.QComboBox()
            combo_result.addItems(["", RESULT_WHITE_WIN, RESULT_DRAW, RESULT_BLACK_WIN])
            combo_result.setToolTip("Select result (White's perspective)")
            combo_result.setProperty("row", row)
            combo_result.setProperty("white_id", white.id)
            combo_result.setProperty("black_id", black.id)
            # Pre-select result if players are inactive? (e.g., double forfeit 0-0)
            if not white.is_active and not black.is_active:
                 # combo_result.setCurrentText(RESULT_DRAW) # Or a forfeit result if implemented
                 pass # Let TD decide for now
            elif not white.is_active: # Black wins by forfeit?
                 # combo_result.setCurrentText(RESULT_BLACK_WIN)
                 pass
            elif not black.is_active: # White wins by forfeit?
                 # combo_result.setCurrentText(RESULT_WHITE_WIN)
                 pass
            self.table_pairings.setCellWidget(row, 2, combo_result)

            # Quick Result Buttons (as in v3)
            btn_widget = QtWidgets.QWidget()
            btn_layout = QtWidgets.QHBoxLayout(btn_widget); btn_layout.setContentsMargins(0,0,0,0); btn_layout.setSpacing(2)
            btn_1_0 = QtWidgets.QPushButton("1-0"); btn_05_05 = QtWidgets.QPushButton("½-½"); btn_0_1 = QtWidgets.QPushButton("0-1")
            btn_1_0.setFixedSize(40, 20); btn_05_05.setFixedSize(40, 20); btn_0_1.setFixedSize(40, 20)
            btn_1_0.setToolTip("White wins"); btn_05_05.setToolTip("Draw"); btn_0_1.setToolTip("Black wins")
            btn_layout.addWidget(btn_1_0); btn_layout.addWidget(btn_05_05); btn_layout.addWidget(btn_0_1); btn_layout.addStretch()
            self.table_pairings.setCellWidget(row, 3, btn_widget)
            btn_1_0.clicked.connect(lambda chk, r=row, res=RESULT_WHITE_WIN: self.set_quick_result(r, res))
            btn_05_05.clicked.connect(lambda chk, r=row, res=RESULT_DRAW: self.set_quick_result(r, res))
            btn_0_1.clicked.connect(lambda chk, r=row, res=RESULT_BLACK_WIN: self.set_quick_result(r, res))

            # Manual Adjust Button
            adjust_btn = QtWidgets.QPushButton("...")
            adjust_btn.setFixedSize(25, 20)
            adjust_btn.setToolTip("Manually adjust this pairing")
            adjust_btn.setProperty("row", row)
            adjust_btn.setProperty("white_id", white.id)
            adjust_btn.setProperty("black_id", black.id)
            adjust_btn.clicked.connect(self.prompt_manual_adjust)
            self.table_pairings.setCellWidget(row, 4, adjust_btn)


        # Display Bye Player
        if bye_player:
            status = " (Inactive)" if not bye_player.is_active else ""
            self.lbl_bye.setText(f"Bye: {bye_player.name} ({bye_player.rating}){status} - Receives {BYE_SCORE} point" + (" (if active)" if not bye_player.is_active else ""))
            self.lbl_bye.setVisible(True)
        else:
            self.lbl_bye.setText("Bye: None"); self.lbl_bye.setVisible(False)

        self.table_pairings.resizeColumnsToContents()
        self.table_pairings.resizeRowsToContents()

    def set_quick_result(self, row: int, result_text: str):
         """Sets the result in the combo box."""
         # (Identical to v3)
         combo_box = self.table_pairings.cellWidget(row, 2)
         if isinstance(combo_box, QtWidgets.QComboBox):
              index = combo_box.findText(result_text)
              if index >= 0: combo_box.setCurrentIndex(index)

    def prompt_manual_adjust(self):
         """Handles click on the manual adjust button for a pairing."""
         sender_button = self.sender()
         if not sender_button or not self.tournament: return

         row = sender_button.property("row")
         white_id = sender_button.property("white_id")
         black_id = sender_button.property("black_id")
         round_index = self.current_round_index # Adjust pairings for the round currently displayed

         if round_index >= len(self.tournament.rounds_pairings_ids):
              QtWidgets.QMessageBox.warning(self, "Adjust Error", "Cannot adjust pairings for a round not yet generated.")
              return

         player_to_adjust = self.tournament.players.get(white_id) # Adjust White's opponent by default
         current_opponent = self.tournament.players.get(black_id)
         if not player_to_adjust or not current_opponent:
              QtWidgets.QMessageBox.critical(self, "Adjust Error", "Could not find players for this pairing.")
              return

         # Get list of potential new opponents (all *other* active players in the tournament)
         available_opponents = [p for p_id, p in self.tournament.players.items()
                                if p.is_active and p_id != white_id and p_id != black_id]
         # TODO: Could also allow pairing against the current Bye player if one exists

         dialog = ManualPairDialog(player_to_adjust.name, current_opponent.name, available_opponents, self)
         if dialog.exec():
              new_opponent_id = dialog.get_selected_opponent_id()
              if new_opponent_id:
                   # Confirm the adjustment
                   new_opp_player = self.tournament.players.get(new_opponent_id)
                   reply = QtWidgets.QMessageBox.warning(self, "Confirm Manual Pairing",
                                                       f"Manually pair {player_to_adjust.name} against {new_opp_player.name} for Round {round_index+1}?\n"
                                                       f"This will also adjust the opponents for {current_opponent.name} and {new_opp_player.name}'s original partner.\n"
                                                       f"This action is logged but CANNOT BE UNDONE easily.",
                                                       QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                                                       QtWidgets.QMessageBox.StandardButton.No)
                   if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                        if self.tournament.manually_adjust_pairing(round_index, white_id, new_opponent_id):
                             self.update_history_log(f"WARNING: Manual pairing adjustment performed in Round {round_index+1} for {player_to_adjust.name}.")
                             # Refresh the pairings display
                             current_pairings_ids = self.tournament.rounds_pairings_ids[round_index]
                             current_bye_id = self.tournament.rounds_byes_ids[round_index]
                             current_pairings = []
                             for w_id, b_id in current_pairings_ids:
                                  w = self.tournament.players.get(w_id)
                                  b = self.tournament.players.get(b_id)
                                  if w and b: current_pairings.append((w,b))
                             current_bye = self.tournament.players.get(current_bye_id) if current_bye_id else None
                             self.display_pairings_for_input(current_pairings, current_bye)
                             self.mark_dirty()
                        else:
                             QtWidgets.QMessageBox.critical(self, "Adjust Error", "Manual pairing adjustment failed. Check logs.")


    def record_and_advance(self) -> None:
        """Reads results, records them, updates state."""
        # (Logic similar to v3, uses helper to get data)
        if not self.tournament: return
        round_index_to_record = self.current_round_index
        if round_index_to_record >= len(self.tournament.rounds_pairings_ids): return

        results_data, all_entered = self.get_results_from_table()
        if not all_entered:
            QtWidgets.QMessageBox.warning(self, "Incomplete Results", "Please enter a result for all pairings.")
            return
        if results_data is None: # Indicates error during retrieval
             return

        # --- Record the results ---
        try:
            if self.tournament.record_results(round_index_to_record, results_data):
                self.last_recorded_results_data = results_data # Store for undo
                self.current_round_index += 1

                display_round_number = round_index_to_record + 1
                self.update_history_log(f"--- Round {display_round_number} Results Recorded ---")
                # (Log details as in v3)
                self.log_results_details(results_data, round_index_to_record)

                self.update_standings_table()
                self.update_crosstable()
                self.tabs.setCurrentWidget(self.standings_tab)
                self.statusBar().showMessage(f"Round {display_round_number} results recorded.")
                self.mark_dirty() # Recording results modifies state
            else:
                 QtWidgets.QMessageBox.warning(self, "Recording Warning", "Some results may not have been recorded properly. Check logs and player status.")

        except Exception as e:
            logging.exception("Error recording results:")
            QtWidgets.QMessageBox.critical(self, "Recording Error", f"Recording results failed:\n{e}")
            self.statusBar().showMessage("Error recording results.")
        finally:
             self._update_ui_state()

    def get_results_from_table(self) -> Tuple[Optional[List[Tuple[str, str, float]]], bool]:
         """Extracts results data from the pairings table."""
         results_data = []
         all_entered = True
         for row in range(self.table_pairings.rowCount()):
              combo_box = self.table_pairings.cellWidget(row, 2)
              if isinstance(combo_box, QtWidgets.QComboBox):
                   result_text = combo_box.currentText()
                   white_id = combo_box.property("white_id")
                   black_id = combo_box.property("black_id")
                   if not result_text: all_entered = False; break
                   white_score = -1.0
                   if result_text == RESULT_WHITE_WIN: white_score = WIN_SCORE
                   elif result_text == RESULT_DRAW: white_score = DRAW_SCORE
                   elif result_text == RESULT_BLACK_WIN: white_score = LOSS_SCORE
                   if white_score >= 0 and white_id and black_id: results_data.append((white_id, black_id, white_score))
                   else: logging.error(f"Invalid data row {row}."); return None, False # Error
              else: logging.error(f"Missing combo box row {row}."); return None, False # Error
         return results_data, all_entered

    def log_results_details(self, results_data, round_index):
         """Logs recorded results to history."""
         for w_id, b_id, score_w in results_data:
              w = self.tournament.players.get(w_id, Player("?",None))
              b = self.tournament.players.get(b_id, Player("?",None))
              score_b = WIN_SCORE - score_w
              self.update_history_log(f"  {w.name} ({score_w:.1f}) - {b.name} ({score_b:.1f})")
         bye_id = self.tournament.rounds_byes_ids[round_index]
         if bye_id:
              bye = self.tournament.players.get(bye_id, Player("?", None))
              status = " (Inactive - No Score)" if not bye.is_active else ""
              self.update_history_log(f"  Bye point awarded to: {bye.name}{status}")
         self.update_history_log("-" * 20)


    def undo_last_results(self) -> None:
        """Reverts the last recorded round."""
        # (Logic similar to v3, uses stored results data)
        if not self.tournament or not self.last_recorded_results_data or self.current_round_index == 0:
            QtWidgets.QMessageBox.warning(self, "Undo Error", "No results available to undo."); return

        round_to_undo_display = self.current_round_index
        reply = QtWidgets.QMessageBox.question(self,"Undo Results", f"Undo results from Round {round_to_undo_display}?",
                                             QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                                             QtWidgets.QMessageBox.StandardButton.No)
        if reply != QtWidgets.QMessageBox.StandardButton.Yes: return

        try:
            round_index_to_undo = self.current_round_index - 1
            bye_player_id_undone = self.tournament.rounds_byes_ids[round_index_to_undo]

            # Revert player stats
            for white_id, black_id, _ in self.last_recorded_results_data:
                p_white = self.tournament.players.get(white_id)
                p_black = self.tournament.players.get(black_id)
                if p_white: self._revert_player_round(p_white)
                if p_black: self._revert_player_round(p_black)
            if bye_player_id_undone:
                 p_bye = self.tournament.players.get(bye_player_id_undone)
                 if p_bye: self._revert_player_round(p_bye) # Revert even if inactive

            # Revert tournament state (pop pairings/bye for the undone round)
            if self.tournament.rounds_pairings_ids: self.tournament.rounds_pairings_ids.pop()
            if self.tournament.rounds_byes_ids: self.tournament.rounds_byes_ids.pop()
            # Revert manual pairings for this round if any? Or leave them? Leaving them for now.
            if round_index_to_undo in self.tournament.manual_pairings:
                 logging.warning(f"Manual pairings for round {round_to_undo_display} were not automatically reverted by undo.")
                 # del self.tournament.manual_pairings[round_index_to_undo] # Option to revert manual changes too

            self.last_recorded_results_data = []
            self.current_round_index -= 1

            # --- Update UI ---
            self.round_group.setTitle(f"Round {round_to_undo_display} Pairings & Results Input (Re-entry)")
            # Re-display pairings for the round being undone
            pairings_ids = self.tournament.rounds_pairings_ids[round_index_to_undo] if round_index_to_undo < len(self.tournament.rounds_pairings_ids) else []
            pairings = []
            for w_id, b_id in pairings_ids:
                 w = self.tournament.players.get(w_id); b = self.tournament.players.get(b_id)
                 if w and b: pairings.append((w,b))
            bye_player = self.tournament.players.get(bye_player_id_undone) if bye_player_id_undone else None
            self.display_pairings_for_input(pairings, bye_player)
            self.tabs.setCurrentWidget(self.tournament_tab)

            self.update_standings_table()
            self.update_crosstable()
            self.update_history_log(f"--- Round {round_to_undo_display} Results Undone ---")
            self.statusBar().showMessage(f"Round {round_to_undo_display} results undone. Re-enter results.")
            self.mark_dirty() # Undoing is a modification

        except Exception as e:
            logging.exception("Error undoing results:")
            QtWidgets.QMessageBox.critical(self, "Undo Error", f"Undoing results failed:\n{e}")
            self.statusBar().showMessage("Error undoing results.")
        finally:
             self._update_ui_state()


    def _revert_player_round(self, player: Player):
         """Helper to remove the last round's data from a player object."""
         # (Identical to v3)
         if not player.results: return
         last_result = player.results.pop()
         if last_result is not None: player.score = max(0.0, player.score - last_result)
         if player.running_scores: player.running_scores.pop()
         last_opponent_id = player.opponent_ids.pop() if player.opponent_ids else None
         last_color = player.color_history.pop() if player.color_history else None
         if last_color == "Black": player.num_black_games = max(0, player.num_black_games - 1)
         if last_opponent_id is None: # Was a bye round
             player.has_received_bye = (None in player.opponent_ids) # Still has bye if another None exists
         player._opponents_played_cache = []


    def update_standings_table_headers(self):
         """Updates the standings table headers based on configured tiebreak order."""
         if not self.tournament: return
         base_headers = ["Rank", "Player", "Score"]
         tb_headers = [TIEBREAK_NAMES.get(key, key) for key in self.tournament.tiebreak_order]
         full_headers = base_headers + tb_headers
         self.table_standings.setColumnCount(len(full_headers))
         self.table_standings.setHorizontalHeaderLabels(full_headers)
         # Reset resize modes (apply stretch to player, others content)
         self.table_standings.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
         for i in range(len(full_headers)):
              if i != 1: self.table_standings.horizontalHeader().setSectionResizeMode(i, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
         # Add tooltips
         header_tooltips = ["Rank", "Player Name (Rating)", "Total Score"] + \
                           [TIEBREAK_NAMES.get(key, key) for key in self.tournament.tiebreak_order] # Basic tooltips for now
         for i, tip in enumerate(header_tooltips):
              self.table_standings.horizontalHeaderItem(i).setToolTip(tip)


    def update_standings_table(self) -> None:
        """Updates the standings table."""
        if not self.tournament: self.table_standings.setRowCount(0); return

        try:
             # Ensure headers match current config first
             if self.table_standings.columnCount() != 3 + len(self.tournament.tiebreak_order):
                  self.update_standings_table_headers()

             standings = self.tournament.get_standings() # Gets sorted active players
             self.table_standings.setRowCount(len(standings))

             # Define formatting (could be made configurable later)
             tb_formats = { TB_MEDIAN: '.1f', TB_SOLKOFF: '.1f', TB_CUMULATIVE: '.1f',
                            TB_CUMULATIVE_OPP: '.1f', TB_SONNENBORN_BERGER: '.2f', TB_MOST_BLACKS: '.0f' }

             for rank, player in enumerate(standings):
                  row = rank
                  rank_str = str(rank + 1)
                  status_str = "" if player.is_active else " (I)"
                  item_rank = QtWidgets.QTableWidgetItem(rank_str)
                  item_player = QtWidgets.QTableWidgetItem(f"{player.name} ({player.rating}){status_str}")
                  item_score = QtWidgets.QTableWidgetItem(f"{player.score:.1f}")
                  item_score.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                  # Set inactive player rows to gray
                  row_color = self.table_standings.palette().color(QtGui.QPalette.ColorRole.Text)
                  if not player.is_active: row_color = QtGui.QColor("gray")
                  item_rank.setForeground(row_color)
                  item_player.setForeground(row_color)
                  item_score.setForeground(row_color)

                  self.table_standings.setItem(row, 0, item_rank)
                  self.table_standings.setItem(row, 1, item_player)
                  self.table_standings.setItem(row, 2, item_score)

                  # Tiebreakers based on configured order
                  col_offset = 3
                  for i, tb_key in enumerate(self.tournament.tiebreak_order):
                       value = player.tiebreakers.get(tb_key, 0.0)
                       format_spec = tb_formats.get(tb_key, '.1f') # Default format
                       item_tb = QtWidgets.QTableWidgetItem(f"{value:{format_spec}}")
                       item_tb.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                       item_tb.setForeground(row_color)
                       self.table_standings.setItem(row, col_offset + i, item_tb)

             self.table_standings.resizeColumnsToContents()
             self.table_standings.resizeRowsToContents()

        except Exception as e:
             logging.exception("Error updating standings table:")
             QtWidgets.QMessageBox.warning(self, "Standings Error", f"Could not update standings: {e}")


    def update_crosstable(self):
         """Populates the cross-table tab."""
         if not self.tournament or not self.tournament.players:
              self.table_crosstable.setRowCount(0)
              self.table_crosstable.setColumnCount(0)
              return

         # Get players sorted by final rank (or current standings)
         sorted_players = self.tournament.get_standings()
         player_map = {p.id: p for p in sorted_players} # Map ID to player for quick lookup
         player_order = [p.id for p in sorted_players] # Order for rows/columns
         n = len(sorted_players)

         self.table_crosstable.setRowCount(n)
         self.table_crosstable.setColumnCount(n + 3) # Num, Name, Score + Opponents

         # Set Headers
         headers = ["#", "Player", "Score"] + [str(i + 1) for i in range(n)] # Opponent numbers
         self.table_crosstable.setHorizontalHeaderLabels(headers)
         v_headers = [f"{i+1}. {p.name}" for i, p in enumerate(sorted_players)]
         self.table_crosstable.setVerticalHeaderLabels(v_headers)

         # Populate table
         for r, p1_id in enumerate(player_order):
              p1 = player_map[p1_id]
              # Column 0: Rank
              rank_item = QtWidgets.QTableWidgetItem(str(r + 1))
              rank_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
              self.table_crosstable.setItem(r, 0, rank_item)
              # Column 1: Name (Rating)
              name_item = QtWidgets.QTableWidgetItem(f"{p1.name} ({p1.rating})")
              self.table_crosstable.setItem(r, 1, name_item)
              # Column 2: Score
              score_item = QtWidgets.QTableWidgetItem(f"{p1.score:.1f}")
              score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
              self.table_crosstable.setItem(r, 2, score_item)

              # Columns 3 to n+2: Results against opponents
              for round_num, opp_id in enumerate(p1.opponent_ids):
                   result_char = "-" # Default if no opponent/result
                   bg_color = None
                   if opp_id is None: # Bye
                        result_char = "Bye"
                        bg_color = QtGui.QColor("lightyellow")
                   elif opp_id in player_map:
                        # Find opponent's rank/column index
                        try:
                             c = player_order.index(opp_id) + 3 # +3 for offset cols
                             result = p1.results[round_num]
                             color = p1.color_history[round_num]
                             color_char = ' W ' if color == "White" else ' B ' if color == "Black" else ' '
                             if result == WIN_SCORE: result_char = f"+{player_order.index(opp_id)+1}{color_char}" # Show opponent number and color
                             elif result == DRAW_SCORE: result_char = f"={player_order.index(opp_id)+1}{color_char}"
                             elif result == LOSS_SCORE: result_char = f"-{player_order.index(opp_id)+1}{color_char}"
                             else: result_char = "?" # Should not happen

                             # Set background color for self-pairing cell
                             if r == c - 3: bg_color = QtGui.QColor("lightgray")

                             item = QtWidgets.QTableWidgetItem(result_char)
                             item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                             if bg_color: item.setBackground(bg_color)
                             self.table_crosstable.setItem(r, c, item)

                        except ValueError:
                             logging.warning(f"Opponent ID {opp_id} not found in player_order for cross-table.")
                             # Handle case where opponent might be inactive and not in standings
                             opp = self.tournament.players.get(opp_id)
                             result_char = f"? ({opp.name if opp else 'Unknown'})" # Indicate missing opponent
                             # Find an empty column? Or just log? Logging for now.

                   else: # Opponent not found (e.g., removed player?)
                        result_char = "Err"

              # Fill diagonal with gray background
              diag_item = QtWidgets.QTableWidgetItem("X")
              diag_item.setBackground(QtGui.QColor("lightgray"))
              diag_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
              self.table_crosstable.setItem(r, r + 3, diag_item)


         self.table_crosstable.resizeColumnsToContents()
         self.table_crosstable.resizeRowsToContents()


    def update_history_log(self, message: str):
        """Appends a timestamped message to the history log."""
        # (Identical to v3)
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        self.history_view.appendPlainText(f"[{timestamp}] {message}")
        logging.info(f"Log: {message}")


    def export_standings(self) -> None:
        """Exports standings."""
        # (Logic similar to v3, uses configured headers)
        if not self.tournament: QtWidgets.QMessageBox.information(self, "Export Error", "No tournament data."); return
        standings = self.tournament.get_standings()
        if not standings: QtWidgets.QMessageBox.information(self, "Export Error", "No standings available."); return

        filename, selected_filter = QtWidgets.QFileDialog.getSaveFileName(self, "Export Standings", "", CSV_FILTER)
        if not filename: return

        try:
            with open(filename, "w", encoding="utf-8", newline='') as f:
                is_csv = selected_filter.startswith("CSV")
                delimiter = "," if is_csv else "\t"
                writer = csv.writer(f, delimiter=delimiter) if is_csv else None

                # Write Header (use current table headers)
                header = [self.table_standings.horizontalHeaderItem(i).text() for i in range(self.table_standings.columnCount())]
                if writer: writer.writerow(header)
                else: f.write(delimiter.join(header) + "\n")

                # Write Player Data
                tb_formats = { TB_MEDIAN: '.1f', TB_SOLKOFF: '.1f', TB_CUMULATIVE: '.1f',
                               TB_CUMULATIVE_OPP: '.1f', TB_SONNENBORN_BERGER: '.2f', TB_MOST_BLACKS: '.0f' }

                for rank, player in enumerate(standings):
                    rank_str = str(rank + 1)
                    player_str = f"{player.name} ({player.rating})" + (" (I)" if not player.is_active else "")
                    score_str = f"{player.score:.1f}"
                    data_row = [rank_str, player_str, score_str]
                    for tb_key in self.tournament.tiebreak_order:
                         value = player.tiebreakers.get(tb_key, 0.0)
                         format_spec = tb_formats.get(tb_key, '.1f')
                         data_row.append(f"{value:{format_spec}}")

                    if writer: writer.writerow(data_row)
                    else: f.write(delimiter.join(data_row) + "\n")

            QtWidgets.QMessageBox.information(self, "Export Successful", f"Standings exported to {filename}")
            self.statusBar().showMessage(f"Standings exported to {filename}")
        except Exception as e:
            logging.exception("Error exporting standings:")
            QtWidgets.QMessageBox.critical(self, "Export Error", f"Could not save standings:\n{e}")
            self.statusBar().showMessage("Error exporting standings.")


    def save_tournament(self, save_as=False):
         """Saves the current tournament state."""
         # (Logic similar to v3, marks clean)
         if not self.tournament: QtWidgets.QMessageBox.warning(self, "Save Error", "No tournament data."); return

         filename = self._current_filepath
         if save_as or not filename:
              filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Tournament", "", SAVE_FILE_FILTER)
              if not filename: return
              if not filename.lower().endswith(SAVE_FILE_EXTENSION): filename += SAVE_FILE_EXTENSION
              self._current_filepath = filename

         try:
              save_data = {
                   'tournament': self.tournament.to_dict(),
                   'current_round_index': self.current_round_index,
                   'gui_version': APP_VERSION # Store GUI version too
              }
              with open(filename, "w", encoding="utf-8") as f: json.dump(save_data, f, indent=4)
              self.statusBar().showMessage(f"Tournament saved to {filename}")
              self.update_history_log(f"--- Tournament Saved to {filename} ---")
              self.mark_clean() # Mark as saved
              self.setWindowTitle(f"{APP_NAME} - {QFileInfo(filename).fileName()}")
         except Exception as e:
              logging.exception(f"Error saving tournament to {filename}:")
              QtWidgets.QMessageBox.critical(self, "Save Error", f"Could not save tournament:\n{e}")
              self.statusBar().showMessage("Error saving tournament.")


    def load_tournament(self):
         """Loads tournament state from a file."""
         # (Logic similar to v3, resets state, repopulates UI, marks clean)
         if not self.check_save_before_proceeding(): return

         filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load Tournament", "", SAVE_FILE_FILTER)
         if not filename: return

         try:
              with open(filename, "r", encoding="utf-8") as f: load_data = json.load(f)
              if 'tournament' not in load_data: raise ValueError("Invalid save file: 'tournament' key missing.")

              self.reset_tournament_state() # Clear current state fully
              self.tournament = Tournament.from_dict(load_data['tournament'])
              self.current_round_index = load_data.get('current_round_index', 0)
              self._current_filepath = filename

              # --- Repopulate UI ---
              self.list_players.clear()
              player_list = sorted(self.tournament.get_player_list(), key=lambda p: p.name)
              for player in player_list: self.add_player_to_list_widget(player)

              # Display pairings for the current round if results not yet entered
              if self.current_round_index < len(self.tournament.rounds_pairings_ids):
                   round_to_display_idx = self.current_round_index
                   display_round_num = round_to_display_idx + 1
                   self.round_group.setTitle(f"Round {display_round_num} Pairings & Results Input")
                   pairings_ids = self.tournament.rounds_pairings_ids[round_to_display_idx]
                   bye_id = self.tournament.rounds_byes_ids[round_to_display_idx]
                   pairings = []
                   for w_id, b_id in pairings_ids:
                        w = self.tournament.players.get(w_id); b = self.tournament.players.get(b_id)
                        if w and b: pairings.append((w,b))
                   bye_player = self.tournament.players.get(bye_id) if bye_id else None
                   self.display_pairings_for_input(pairings, bye_player)
              else: # Tournament finished or between rounds
                   self.table_pairings.setRowCount(0)
                   self.lbl_bye.setText("Bye: None")
                   completed_rounds = self.tournament.get_completed_rounds()
                   self.round_group.setTitle(f"Round {completed_rounds+1} (Not Started)" if completed_rounds < self.tournament.num_rounds else "Tournament Finished")


              self.update_standings_table_headers() # Use loaded tiebreak order
              self.update_standings_table()
              self.update_crosstable()
              self.mark_clean() # Loaded state is clean initially
              self.statusBar().showMessage(f"Tournament loaded from {filename}")
              self.update_history_log(f"--- Tournament Loaded from {filename} ---")
              self.setWindowTitle(f"{APP_NAME} - {QFileInfo(filename).fileName()}")

         except FileNotFoundError:
              logging.error(f"Load error: File not found {filename}")
              QtWidgets.QMessageBox.critical(self, "Load Error", f"File not found:\n{filename}")
              self.statusBar().showMessage("Error loading tournament: File not found.")
         except Exception as e:
              logging.exception(f"Error loading tournament from {filename}:")
              QtWidgets.QMessageBox.critical(self, "Load Error", f"Could not load tournament:\n{e}")
              self.statusBar().showMessage("Error loading tournament.")
              self.reset_tournament_state()
         finally:
              self._update_ui_state()


    def check_save_before_proceeding(self) -> bool:
         """Checks if there are unsaved changes and prompts the user. Returns True if safe to proceed."""
         if not self._dirty or not self.tournament:
              return True # No changes or no tournament, safe to proceed

         reply = QtWidgets.QMessageBox.question(self, 'Unsaved Changes',
              "The current tournament has unsaved changes. Save before proceeding?",
              QtWidgets.QMessageBox.StandardButton.Save |
              QtWidgets.QMessageBox.StandardButton.Discard |
              QtWidgets.QMessageBox.StandardButton.Cancel,
              QtWidgets.QMessageBox.StandardButton.Cancel) # Default to Cancel

         if reply == QtWidgets.QMessageBox.StandardButton.Save:
              self.save_tournament()
              return not self._dirty # Proceed only if save was successful (marked clean)
         elif reply == QtWidgets.QMessageBox.StandardButton.Discard:
              return True # User chose to discard changes
         else: # Cancel
              return False # Do not proceed


    def show_about_dialog(self):
         """Displays the About dialog."""
         QtWidgets.QMessageBox.about(self, f"About {APP_NAME}",
              f"<h2>{APP_NAME}</h2>"
              f"<p>Version: {APP_VERSION}</p>"
              "<p>A simple Swiss pairing application using PyQt6.</p>"
              "<p>Features USCF-style pairings and tiebreaks.</p>"
              "<p><a href='https://discord.gg/eEnnetMDfr'>Join our Discord community</a></p>"
              "<p>&copy; 2025</p>")


    def closeEvent(self, event: QCloseEvent):
        """Handle closing the application, prompt to save."""
        if self.check_save_before_proceeding():
            logging.info(f"{APP_NAME} closing.")
            event.accept()
        else:
            event.ignore()


# --- Main Execution ---
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    try: app.setStyle("Fusion")
    except Exception as e: logging.warning(f"Could not set Fusion style: {e}")

    window = SwissTournamentApp()
    window.show()
    sys.exit(app.exec())
