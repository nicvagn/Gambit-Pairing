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
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog

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
APP_VERSION = "0.3" # Incremented version
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
    def __init__(self, name: str, rating: Optional[int] = None, player_id: Optional[str] = None,
                 phone: Optional[str] = None, email: Optional[str] = None, club: Optional[str] = None,
                 federation: Optional[str] = None, gender: Optional[str] = None, dob: Optional[str] = None) -> None:
        self.id: str = player_id or generate_id("player_")
        self.name: str = name
        self.rating: int = rating if rating is not None else 1000
        self.phone: Optional[str] = phone
        self.email: Optional[str] = email
        self.club: Optional[str] = club
        self.federation: Optional[str] = federation
        self.gender: Optional[str] = gender
        self.dob: Optional[str] = dob
        self.score: float = 0.0
        self.is_active: bool = True # Used for withdrawals

        # History
        self.color_history: List[Optional[str]] = [] # Stores "White", "Black", or None (for bye)
        self.opponent_ids: List[Optional[str]] = []
        self.results: List[Optional[float]] = []
        self.running_scores: List[float] = []
        self.has_received_bye: bool = False
        self.num_black_games: int = 0 # Counts actual games played as Black
        self.float_history: List[int] = []  # Track rounds where player floated down

        # Tiebreakers (calculated)
        self.tiebreakers: Dict[str, float] = {}

        # Runtime cache
        self._opponents_played_cache: List[Optional['Player']] = []

    def __repr__(self) -> str:
        status = "" if self.is_active else " (Inactive)"
        return f"{self.name} ({self.rating}){status}"

    def get_opponent_objects(self, players_dict: Dict[str, 'Player']) -> List[Optional['Player']]:
        """Resolves opponent IDs to Player objects using the provided dictionary."""
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
        """Determines color preference based on FIDE/USCF rules.
        1. Absolute: If last two played games had same color, must get the other.
        2. Preference: If colors are unbalanced, prefer the color that moves towards balance.
        Returns: "White", "Black", or None if no preference or perfectly balanced.
        """
        valid_played_colors = [c for c in self.color_history if c is not None]

        if len(valid_played_colors) >= 2:
            last_color = valid_played_colors[-1]
            second_last_color = valid_played_colors[-2]
            if last_color == second_last_color:
                return "Black" if last_color == "White" else "White"

        white_games_played = valid_played_colors.count("White")
        black_games_played = valid_played_colors.count("Black")

        if white_games_played > black_games_played:
            return "Black"
        elif black_games_played > white_games_played:
            return "White"
        
        return None

    def add_round_result(self, opponent: Optional['Player'], result: float, color: Optional[str]):
        """Records the outcome of a round for the player."""
        opponent_id = opponent.id if opponent else None
        self.opponent_ids.append(opponent_id)
        self.results.append(result)
        self.score += result
        self.running_scores.append(self.score)
        self.color_history.append(color) # color can be None for a bye
        if color == "Black": 
            self.num_black_games += 1
        if opponent is None: # This means it was a bye
            self.has_received_bye = True
            logging.debug(f"Player {self.name} marked as having received a bye.")
        self._opponents_played_cache = [] # Invalidate cache

    def to_dict(self) -> Dict[str, Any]:
        """Serializes player data."""
        data = {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Player':
        """Deserializes player data."""
        player = cls(
            name=data['name'],
            rating=data.get('rating', 1000),
            player_id=data['id'],
            phone=data.get('phone'),
            email=data.get('email'),
            club=data.get('club'),
            federation=data.get('federation'),
            gender=data.get('gender'),
            dob=data.get('dob')
        )
        for key, value in data.items():
             if hasattr(player, key) and not key.startswith('_'):
                  setattr(player, key, value)
        # Ensure essential lists exist if loading older format without them
        for list_attr in ['color_history', 'opponent_ids', 'results', 'running_scores', 'float_history']:
             if not hasattr(player, list_attr) or getattr(player, list_attr) is None:
                  setattr(player, list_attr, [])
        if not hasattr(player, 'has_received_bye'): # For older save files
            player.has_received_bye = (None in player.opponent_ids) if player.opponent_ids else False
        if not hasattr(player, 'num_black_games'): # For older save files
            player.num_black_games = player.color_history.count("Black") if player.color_history else 0

        return player

class Tournament:
    """Manages the tournament state, pairings, results, and tiebreakers."""
    def __init__(self, players: List[Player], num_rounds: int, tiebreak_order: Optional[List[str]] = None) -> None:
        self.players: Dict[str, Player] = {p.id: p for p in players}
        self.num_rounds: int = num_rounds
        self.tiebreak_order: List[str] = tiebreak_order or list(DEFAULT_TIEBREAK_SORT_ORDER) 
        self.rounds_pairings_ids: List[List[Tuple[str, str]]] = [] 
        self.rounds_byes_ids: List[Optional[str]] = []
        self.previous_matches: Set[frozenset[str]] = set() 
        self.manual_pairings: Dict[int, Dict[str, str]] = {} 

    def get_player_list(self, active_only=False) -> List[Player]:
        players = list(self.players.values())
        if active_only:
             return [p for p in players if p.is_active]
        return players

    def _get_active_players(self) -> List[Player]:
        return [p for p in self.players.values() if p.is_active]

    def _get_eligible_bye_player(self, potential_bye_players: List[Player]) -> Optional[Player]:
        """Determines the bye player according to Swiss rules.
        Priority: Active player who has not yet received a bye, lowest score, then lowest rating.
        Fallback: If all have received a bye, the active player with the lowest score, then rating, gets a second bye.
        """
        if not potential_bye_players:
            return None

        active_players = [p for p in potential_bye_players if p.is_active]
        if not active_players:
            logging.debug("_get_eligible_bye_player: No active players in potential list.")
            return None

        eligible_for_first_bye = [p for p in active_players if not p.has_received_bye]

        if eligible_for_first_bye:
            eligible_for_first_bye.sort(key=lambda p: (p.score, p.rating, p.name))
            logging.info(f"Assigning first bye to: {eligible_for_first_bye[0].name} (Score: {eligible_for_first_bye[0].score}, Rating: {eligible_for_first_bye[0].rating})")
            return eligible_for_first_bye[0]
        else:
            # All active players in the list have already received a bye.
            # A second bye must be assigned if a bye is necessary (e.g. USCF 29E2).
            logging.warning(f"All potential bye candidates ({[p.name for p in active_players]}) "
                            f"have already received a bye. Assigning a second bye as a last resort.")
            active_players.sort(key=lambda p: (p.score, p.rating, p.name))
            logging.info(f"Assigning second bye to: {active_players[0].name} (Score: {active_players[0].score}, Rating: {active_players[0].rating})")
            return active_players[0]


    def create_pairings(self, current_round: int, allow_repeat_pairing_callback=None) -> Tuple[List[Tuple[Player, Player]], Optional[Player]]:
        """Generates pairings for the next round with improved bye, floating, and color assignment."""
        active_players = self._get_active_players()
        if not active_players:
            logging.error("No active players available for pairing.")
            return [], None # Return empty list and no bye player

        # --- Round 1 Pairing (Seed-based) ---
        if current_round == 1:
            players_sorted = sorted(active_players, key=lambda p: (-p.rating, p.name))
            bye_player = None
            
            if len(players_sorted) % 2 == 1:
                # In R1, lowest rated player gets the bye. _get_eligible_bye_player handles this.
                # Candidate for bye is the lowest rated among all active players.
                bye_player = self._get_eligible_bye_player(players_sorted)
                if bye_player:
                    players_sorted.remove(bye_player) # Remove bye player from pairing list
                else: # Should not happen in R1 if active_players is not empty
                    logging.error("R1: Could not assign a bye even with odd players.")
                    # Potentially raise error or return empty if critical
            
            mid = len(players_sorted) // 2
            top_half, bottom_half = players_sorted[:mid], players_sorted[mid:]
            pairings, round_pairings_ids = [], []

            for p1, p2 in zip(top_half, bottom_half):
                white, black = p1, p2 # Higher seed White
                pairings.append((white, black))
                round_pairings_ids.append((white.id, black.id))
                self.previous_matches.add(frozenset({p1.id, p2.id}))
            
            if bye_player:
                logging.info(f"Round 1 Bye assigned to: {bye_player.name}")

            self.rounds_pairings_ids.append(round_pairings_ids)
            self.rounds_byes_ids.append(bye_player.id if bye_player else None)
            return pairings, bye_player

        # --- Subsequent Rounds Pairing (Score Group based) ---
        score_groups: Dict[float, List[Player]] = {}
        for p in active_players:
            score_groups.setdefault(p.score, []).append(p)
        sorted_scores = sorted(score_groups.keys(), reverse=True)
        pairings, round_pairings_ids = [], []
        
        # Players carried down from a higher score group because they couldn't be paired or were floated.
        # Initially, this list is empty. It can accumulate players who need to be paired down.
        unpaired_from_higher_groups: List[Player] = [] 

        floated_this_round: Set[str] = set() # Track players floated *in this round's processing*

        for score in sorted_scores:
            current_score_group = sorted(score_groups[score], key=lambda p: (-p.rating, p.name))
            
            # Add players carried down from higher score groups (if any)
            # These players must be paired first if possible, or float further.
            # They are effectively part of this score group for pairing purposes now.
            group_to_pair = unpaired_from_higher_groups + current_score_group
            group_to_pair.sort(key=lambda p: (-p.rating, p.name)) # Re-sort combined group
            unpaired_from_higher_groups = [] # Clear for next iteration
            
            logging.debug(f"Processing Score Group: {score}, Players: {[p.name for p in group_to_pair]}")

            # Handle floating if current group (group_to_pair) is odd
            if len(group_to_pair) % 2 == 1:
                # Select floater: lowest rating, hasn't floated this round, hasn't floated recently if possible
                # Candidates are from group_to_pair
                float_candidates = [p for p in group_to_pair if p.id not in floated_this_round]
                if not float_candidates: # All have floated this round (should not happen if logic is correct)
                    logging.warning(f"All players in group for score {score} already floated this round. Taking from original group_to_pair.")
                    float_candidates = group_to_pair 
                
                if float_candidates: # Ensure there's someone to float
                    # Sort by: never floated > floated longest ago, then rating, then name
                    float_candidates.sort(key=lambda p: (p.float_history[-1] if p.float_history else -999, p.rating, p.name))
                    floater = float_candidates[0]
                    
                    unpaired_from_higher_groups.append(floater) # This floater moves to the next (lower) score group
                    floated_this_round.add(floater.id)
                    floater.float_history.append(current_round)
                    group_to_pair.remove(floater)
                    logging.info(f"Player {floater.name} floated down from score group {score}.")
                else:
                    logging.warning(f"Odd group for score {score} but no float candidates found. This is unusual.")


            # Pair players within the (now even-sized) group_to_pair
            # Standard Dutch pairing: top half vs bottom half if possible, or iterative.
            # Current iterative method:
            temp_unpaired_in_group = list(group_to_pair) # Work with a copy
            
            while len(temp_unpaired_in_group) >= 2:
                p1 = temp_unpaired_in_group.pop(0) # Highest rated available
                
                best_opponent_for_p1: Optional[Player] = None
                min_color_conflict_score = float('inf')
                best_opponent_idx = -1

                for idx, p2_candidate in enumerate(temp_unpaired_in_group):
                    if frozenset({p1.id, p2_candidate.id}) in self.previous_matches:
                        continue

                    p1_pref = p1.get_color_preference()
                    p2_cand_pref = p2_candidate.get_color_preference()
                    
                    current_conflict_score = 0
                    if p1_pref is not None and p2_cand_pref is not None and p1_pref == p2_cand_pref:
                        current_conflict_score += 2 # Both want/need same color

                    if current_conflict_score < min_color_conflict_score:
                        min_color_conflict_score = current_conflict_score
                        best_opponent_for_p1 = p2_candidate
                        best_opponent_idx = idx
                        if min_color_conflict_score == 0: # Perfect color match (or no preference from one/both)
                            break 
                    # If multiple opponents give same low conflict_score, prefer closer rating? (More complex)
                    # Current logic takes the first one encountered with the best score.

                # If no valid opponent (all are previous matches), fallback: allow repeat pairing if user agrees
                if best_opponent_for_p1 is None:
                    # Try to find a previous opponent if user allows
                    for idx, p2_candidate in enumerate(temp_unpaired_in_group):
                        if allow_repeat_pairing_callback is not None:
                            # Prompt user for repeat pairing
                            proceed = allow_repeat_pairing_callback(p1, p2_candidate)
                            if proceed:
                                best_opponent_for_p1 = p2_candidate
                                best_opponent_idx = idx
                                break

                if best_opponent_for_p1 and best_opponent_idx != -1:
                    p2 = temp_unpaired_in_group.pop(best_opponent_idx)
                    
                    # Assign colors
                    pref1 = p1.get_color_preference()
                    pref2 = p2.get_color_preference()
                    white, black = None, None

                    if pref1 == "White" and (pref2 == "Black" or pref2 is None): white, black = p1, p2
                    elif pref1 == "Black" and (pref2 == "White" or pref2 is None): white, black = p2, p1
                    elif pref2 == "White" and (pref1 == "Black" or pref1 is None): white, black = p2, p1 # Redundant if covered by above
                    elif pref2 == "Black" and (pref1 == "White" or pref1 is None): white, black = p1, p2 # Redundant
                    
                    # Handle cases where one has preference and other doesn't (covered above if None is included)
                    # Or if both have same preference, or both no preference
                    if white is None: # If not assigned yet
                        if pref1 == "White": white, black = p1, p2 # p1 gets preference if p2 has same or no conflicting
                        elif pref1 == "Black": white, black = p2, p1
                        elif pref2 == "White": white, black = p2, p1
                        elif pref2 == "Black": white, black = p1, p2
                        else: # Both None, or both want same and it wasn't resolved to a clear assignment
                            p1_vc = [c for c in p1.color_history if c is not None]
                            p2_vc = [c for c in p2.color_history if c is not None]
                            p1_bal = p1_vc.count("White") - p1_vc.count("Black")
                            p2_bal = p2_vc.count("White") - p2_vc.count("Black")

                            if p1_bal > p2_bal: white, black = p2, p1 # p1 more W, gets B
                            elif p2_bal > p1_bal: white, black = p1, p2 # p2 more W, gets B
                            else: white, black = (p1, p2) if p1.rating >= p2.rating else (p2, p1)
                    
                    pairings.append((white, black))
                    round_pairings_ids.append((white.id, black.id))
                    self.previous_matches.add(frozenset({p1.id, p2.id}))
                else:
                    # p1 could not be paired in this group (e.g., all remaining are previous opponents)
                    # Add p1 to be carried down.
                    unpaired_from_higher_groups.append(p1)
                    logging.warning(f"Player {p1.name} could not be paired in score group {score} and will be carried down.")
            
            # Any players remaining in temp_unpaired_in_group also couldn't be paired
            unpaired_from_higher_groups.extend(temp_unpaired_in_group)


        # --- Handle any remaining unpaired players (usually from the lowest score group or floaters) ---
        bye_player = None
        # These are players who couldn't be paired in their score groups or were floated down to the very end.
        final_unpaired_list = unpaired_from_higher_groups
        final_unpaired_list.sort(key=lambda p: (-p.rating, p.name)) # Sort them for consistent processing


        if len(final_unpaired_list) % 2 == 1:
            # An odd player remains, needs a bye.
            # Pass the single player in a list to _get_eligible_bye_player
            bye_candidate_player = final_unpaired_list[-1] # Typically lowest rated of this small group
            bye_player = self._get_eligible_bye_player([bye_candidate_player]) # Pass as list
            if bye_player:
                if bye_player in final_unpaired_list : final_unpaired_list.remove(bye_player)
                logging.info(f"Round {current_round} Bye assigned to: {bye_player.name}")
            else:
                # This is a critical error: odd player remains but _get_eligible_bye_player returned None.
                # This implies the only remaining player is inactive or some other rule prevents bye.
                # For robustness, if _get_eligible_bye_player fails here with an odd player,
                # it's a situation that needs manual TD intervention or indicates a flaw.
                logging.error(f"Critical: Odd player {bye_candidate_player.name} remains but cannot be assigned a bye. Pairing may be incomplete.")
                # Potentially raise an error or return incomplete pairings.
                # For now, we proceed, but this player won't be paired.

        # Pair the rest of final_unpaired_list (should be even now)
        # This logic is simpler as these are "leftovers"
        # Use the same pairing and color logic as within score groups
        temp_final_unpaired = list(final_unpaired_list)
        while len(temp_final_unpaired) >= 2:
            p1 = temp_final_unpaired.pop(0)
            paired_p1 = False
            for idx, p2_candidate in enumerate(temp_final_unpaired):
                if frozenset({p1.id, p2_candidate.id}) not in self.previous_matches:
                    p2 = temp_final_unpaired.pop(idx)
                    # Assign colors (using same logic as above)
                    pref1 = p1.get_color_preference()
                    pref2 = p2_candidate.get_color_preference()
                    white, black = None, None
                    if pref1 == "White" and (pref2 == "Black" or pref2 is None): white, black = p1, p2_candidate
                    elif pref1 == "Black" and (pref2 == "White" or pref2 is None): white, black = p2_candidate, p1
                    elif pref2 == "White" and (pref1 == "Black" or pref1 is None): white, black = p2_candidate, p1
                    elif pref2 == "Black" and (pref1 == "White" or pref1 is None): white, black = p1, p2_candidate
                    if white is None:
                        p1_vc = [c for c in p1.color_history if c is not None]
                        p2_vc = [c for c in p2_candidate.color_history if c is not None]
                        p1_bal = p1_vc.count("White") - p1_vc.count("Black")
                        p2_bal = p2_vc.count("White") - p2_vc.count("Black")
                        if p1_bal > p2_bal: white, black = p2_candidate, p1
                        elif p2_bal > p1_bal: white, black = p1, p2_candidate
                        else: white, black = (p1, p2_candidate) if p1.rating >= p2_candidate.rating else (p2_candidate, p1)
                    
                    pairings.append((white, black))
                    round_pairings_ids.append((white.id, black.id))
                    self.previous_matches.add(frozenset({p1.id, p2.id}))
                    paired_p1 = True
                    break 
            # Fallback: allow repeat pairing if user agrees
            if not paired_p1:
                for idx, p2_candidate in enumerate(temp_final_unpaired):
                    if allow_repeat_pairing_callback is not None:
                        proceed = allow_repeat_pairing_callback(p1, p2_candidate)
                        if proceed:
                            # Assign colors as above
                            pref1 = p1.get_color_preference()
                            pref2 = p2_candidate.get_color_preference()
                            white, black = None, None
                            if pref1 == "White" and (pref2 == "Black" or pref2 is None): white, black = p1, p2_candidate
                            elif pref1 == "Black" and (pref2 == "White" or pref2 is None): white, black = p2_candidate, p1
                            elif pref2 == "White" and (pref1 == "Black" or pref1 is None): white, black = p2_candidate, p1
                            elif pref2 == "Black" and (pref1 == "White" or pref1 is None): white, black = p1, p2_candidate
                            if white is None:
                                p1_vc = [c for c in p1.color_history if c is not None]
                                p2_vc = [c for c in p2_candidate.color_history if c is not None]
                                p1_bal = p1_vc.count("White") - p1_vc.count("Black")
                                p2_bal = p2_vc.count("White") - p2_vc.count("Black")
                                if p1_bal > p2_bal: white, black = p2_candidate, p1
                                elif p2_bal > p1_bal: white, black = p1, p2_candidate
                                else: white, black = (p1, p2_candidate) if p1.rating >= p2_candidate.rating else (p2_candidate, p1)
                            pairings.append((white, black))
                            round_pairings_ids.append((white.id, black.id))
                            self.previous_matches.add(frozenset({p1.id, p2.id}))
                            temp_final_unpaired.pop(idx)
                            paired_p1 = True
                            break
            if not paired_p1:
                logging.error(f"Player {p1.name} could not be paired in the final pairing stage.")


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

        current_pairings_ids_for_round = self.rounds_pairings_ids[round_index]
        
        p1 = self.players.get(player1_id)
        new_opp = self.players.get(new_opponent_id)

        if not p1 or not new_opp:
            logging.error("Manual Adjust: Player or new opponent not found in master player list.")
            return False
        if p1 == new_opp:
            logging.warning("Manual Adjust: Player cannot be paired against themselves.")
            return False

        # Store original pairings for logging/reversion if needed (complex)
        if round_index not in self.manual_pairings: self.manual_pairings[round_index] = {}
        
        # Find p1's current pairing and original opponent (p1_orig_opp)
        p1_orig_opp_id = None
        p1_pair_idx = -1
        p1_was_white = False

        for idx, (w_id, b_id) in enumerate(current_pairings_ids_for_round):
            if w_id == player1_id:
                p1_orig_opp_id = b_id
                p1_pair_idx = idx
                p1_was_white = True
                break
            elif b_id == player1_id:
                p1_orig_opp_id = w_id
                p1_pair_idx = idx
                p1_was_white = False
                break
        
        if p1_pair_idx == -1 : # p1 might be the bye player
            current_bye_id = self.rounds_byes_ids[round_index]
            if current_bye_id == player1_id: # p1 was bye, now paired with new_opp
                # new_opp must have been paired or bye. Find new_opp's original pairing.
                # (This logic becomes complex quickly: swapping a bye player with a paired player)
                logging.warning(f"Manual Adjust: Player {p1.name} was bye. Trying to pair with {new_opp.name}.")
                # For simplicity, this case might need more dedicated logic or be disallowed.
                # Assuming p1 was paired for now.
            else:
                logging.error(f"Manual Adjust: Player {p1.name} not found in pairings or bye list for round {round_index+1}.")
                return False
        
        if p1_orig_opp_id == new_opponent_id:
             logging.warning(f"Manual Adjust: Player {p1.name} is already paired with {new_opp.name}.")
             return True # No change needed, but not an error

        # Find new_opp's current pairing and their original opponent (new_opp_orig_opp)
        new_opp_orig_opp_id = None
        new_opp_pair_idx = -1
        new_opp_was_white = False

        for idx, (w_id, b_id) in enumerate(current_pairings_ids_for_round):
            if w_id == new_opponent_id:
                new_opp_orig_opp_id = b_id
                new_opp_pair_idx = idx
                new_opp_was_white = True
                break
            elif b_id == new_opponent_id:
                new_opp_orig_opp_id = w_id
                new_opp_pair_idx = idx
                new_opp_was_white = False
                break
        
        # Case 1: new_opp was also paired (most common)
        if new_opp_pair_idx != -1 and new_opp_orig_opp_id is not None:
            # Record changes before making them
            self.manual_pairings[round_index][player1_id] = p1_orig_opp_id
            self.manual_pairings[round_index][new_opponent_id] = new_opp_orig_opp_id
            if p1_orig_opp_id: self.manual_pairings[round_index][p1_orig_opp_id] = player1_id
            if new_opp_orig_opp_id: self.manual_pairings[round_index][new_opp_orig_opp_id] = new_opponent_id


            # Pair p1 with new_opp. Retain p1's color if possible, or re-evaluate.
            # For simplicity, let's assume p1 keeps original color slot against new_opp.
            if p1_was_white:
                current_pairings_ids_for_round[p1_pair_idx] = (player1_id, new_opponent_id)
            else:
                current_pairings_ids_for_round[p1_pair_idx] = (new_opponent_id, player1_id)
            
            # Pair p1_orig_opp with new_opp_orig_opp.
            # Retain p1_orig_opp's color slot if possible.
            if p1_orig_opp_id and new_opp_orig_opp_id : # Both original opponents exist
                if new_opp_pair_idx != p1_pair_idx : # Ensure they were from different original pairs
                    if not p1_was_white: # p1 was black, so p1_orig_opp was white
                        current_pairings_ids_for_round[new_opp_pair_idx] = (p1_orig_opp_id, new_opp_orig_opp_id)
                    else: # p1 was white, so p1_orig_opp was black
                        current_pairings_ids_for_round[new_opp_pair_idx] = (new_opp_orig_opp_id, p1_orig_opp_id)
                # If new_opp_pair_idx == p1_pair_idx, it means we are swapping partners within the same game.
                # e.g. (A,B) and (C,D). Change A vs B to A vs C. Then B should play D.
                # p1_pair_idx held (A,B). new_opp_pair_idx held (C,D).
                # current_pairings_ids_for_round[p1_pair_idx] becomes (A,C) (if A was white)
                # current_pairings_ids_for_round[new_opp_pair_idx] should become (B,D) (if B was white against A, now B plays D)
                # This needs careful handling of who was white for p1_orig_opp and new_opp_orig_opp.
                # The current logic assumes new_opp_pair_idx refers to new_opp's original game.
                # This re-pairing of p1_orig_opp and new_opp_orig_opp is the "swap partners" part.
            elif p1_orig_opp_id : # new_opp_orig_opp_id was None (new_opp was bye)
                # p1_orig_opp now gets a bye.
                current_bye_id = self.rounds_byes_ids[round_index]
                if current_bye_id is not None and current_bye_id != new_opponent_id: 
                     logging.error("Manual Adjust: Complex bye scenario, cannot auto-assign new bye.")
                     return False
                self.rounds_byes_ids[round_index] = p1_orig_opp_id
                # Remove new_opp's original pairing (which was effectively with a bye)
                if new_opp_pair_idx != p1_pair_idx and new_opp_pair_idx < len(current_pairings_ids_for_round): # if new_opp was not bye but paired
                     #This case is tricky. if new_opp_orig_opp_id is None, new_opp was the bye.
                     # Then self.rounds_byes_ids[round_index] should have been new_opponent_id.
                     # And now new_opp is paired with p1. p1_orig_opp becomes the new bye.
                     logging.info(f"Manual Adjust: {new_opp.name} was bye, now paired. {self.players.get(p1_orig_opp_id).name if p1_orig_opp_id else 'Original opponent of p1'} becomes bye.")
            elif new_opp_orig_opp_id: # p1_orig_opp_id was None (p1 was bye)
                # new_opp_orig_opp now gets a bye.
                # Similar logic as above.
                logging.info(f"Manual Adjust: {p1.name} was bye, now paired. {self.players.get(new_opp_orig_opp_id).name if new_opp_orig_opp_id else 'Original opponent of new_opp'} becomes bye.")


        # Case 2: new_opp was the bye player
        elif self.rounds_byes_ids[round_index] == new_opponent_id:
            logging.info(f"Manual Adjust: Pairing {p1.name} with {new_opp.name} (who was bye). {self.players.get(p1_orig_opp_id).name if p1_orig_opp_id else 'P1s original opponent'} will now be bye.")
            self.manual_pairings[round_index][player1_id] = p1_orig_opp_id
            self.manual_pairings[round_index][new_opponent_id] = None # Was bye
            if p1_orig_opp_id: self.manual_pairings[round_index][p1_orig_opp_id] = player1_id

            # Pair p1 with new_opp
            if p1_was_white: current_pairings_ids_for_round[p1_pair_idx] = (player1_id, new_opponent_id)
            else: current_pairings_ids_for_round[p1_pair_idx] = (new_opponent_id, player1_id)
            
            # p1's original opponent (p1_orig_opp_id) now gets the bye
            self.rounds_byes_ids[round_index] = p1_orig_opp_id
        else:
            logging.error(f"Manual Adjust: New opponent {new_opp.name} not found in pairings or bye list for round {round_index+1}.")
            return False
            
        # Update previous_matches cautiously. Adding new ones is fine. Removing old ones might be too aggressive.
        self.previous_matches.add(frozenset({player1_id, new_opponent_id}))
        # If p1_orig_opp_id and new_opp_orig_opp_id were re-paired:
        if p1_orig_opp_id and new_opp_orig_opp_id and new_opp_pair_idx != -1 : # Check if they form a new pair
             # Only add if they are actually paired now, and were not the same player
             if p1_orig_opp_id != new_opp_orig_opp_id :
                 self.previous_matches.add(frozenset({p1_orig_opp_id, new_opp_orig_opp_id}))

        logging.warning(f"Manual Pairing Adjustment in Round {round_index+1}: {p1.name} now paired with {new_opp.name}. Other pairings potentially affected.")
        # Ensure self.rounds_pairings_ids[round_index] is updated with the modified list
        self.rounds_pairings_ids[round_index] = current_pairings_ids_for_round
        return True


    def record_results(self, round_index: int, results_data: List[Tuple[str, str, float]]):
        """Records results, checking for active status and round index."""
        if round_index < 0 or round_index >= len(self.rounds_pairings_ids):
            logging.error(f"Record Results: Invalid round index {round_index}")
            return False 

        round_pairings_ids = self.rounds_pairings_ids[round_index]
        round_bye_id = self.rounds_byes_ids[round_index]
        player_ids_in_pairings = {p_id for pair in round_pairings_ids for p_id in pair}
        processed_player_ids = set()
        success = True

        for white_id, black_id, white_score in results_data:
            p_white = self.players.get(white_id)
            p_black = self.players.get(black_id)

            if not (p_white and p_black):
                 logging.error(f"Record Results: Could not find players {white_id} or {black_id}.")
                 success = False; continue
            
            # Allow recording for inactive players but log warning.
            if not p_white.is_active : logging.warning(f"Record Results: White player {p_white.name} is inactive.")
            if not p_black.is_active : logging.warning(f"Record Results: Black player {p_black.name} is inactive.")
                 
            # Check if result already recorded for this round for these players
            # This check needs to be robust. A player's result list grows by one each round.
            # If len(p_white.results) is already round_index + 1, it means result for this round_index is in.
            if len(p_white.results) > round_index or len(p_black.results) > round_index:
                 logging.warning(f"Record Results: Attempt to double-record for round {round_index+1}, players {white_id}/{black_id}. Current results len: W={len(p_white.results)}, B={len(p_black.results)}")
                 # This might allow re-recording if undo happened. The GUI should prevent double "Record & Advance" for same round.
                 # Let's assume this is called once per round progression.
                 # If a result for this round_index is already present, it implies an issue.
                 # However, if undo occurred, results would be popped.
                 # The current_round_index in main app tracks state.
                 # This check might be too strict if we allow re-entering results for a non-advanced round.
                 # For now, if results exist for this round_index, it's likely an issue.
                 # Let's assume the GUI/workflow prevents re-recording if round already completed and advanced.
                 # A better check: if this player's opponent_ids[round_index] is already set.
                 if round_index < len(p_white.opponent_ids) and p_white.opponent_ids[round_index] is not None and p_white.opponent_ids[round_index] != black_id :
                      logging.error(f"Record Results: {p_white.name} already has opponent {p_white.opponent_ids[round_index]} for round {round_index+1}, not {black_id}")
                      success = False; continue


            black_score = WIN_SCORE - white_score
            p_white.add_round_result(opponent=p_black, result=white_score, color="White")
            p_black.add_round_result(opponent=p_white, result=black_score, color="Black")
            processed_player_ids.add(white_id)
            processed_player_ids.add(black_id)
            logging.debug(f"Recorded result: {p_white.name} ({white_score}) vs {p_black.name} ({black_score})")

        # Record bye result
        if round_bye_id:
            p_bye = self.players.get(round_bye_id)
            if p_bye:
                 # Award bye score only if player is active *at the time of recording this round's results*
                 # If player withdrew before this round started, they might not get the bye point.
                 # Current logic: if p_bye.is_active. This is status *now*.
                 # A player given a bye should generally get the point unless withdrawn *before* pairings.
                 # This depends on tournament policy. USCF: usually bye stands if player withdraws after pairings.
                 # For simplicity, if p_bye exists and is in rounds_byes_ids, they get point if active.
                 
                 if len(p_bye.results) == round_index: # Ensure not already recorded for this round
                      if p_bye.is_active:
                           p_bye.add_round_result(opponent=None, result=BYE_SCORE, color=None)
                           logging.debug(f"Recorded bye (score {BYE_SCORE}) for active player {p_bye.name}")
                      else:
                           # If player is inactive, record a "bye received" but with 0 points.
                           # This marks them as having used their bye slot.
                           p_bye.add_round_result(opponent=None, result=0.0, color=None)
                           logging.debug(f"Recorded bye (score 0.0) for inactive player {p_bye.name}. has_received_bye is now True.")
                      processed_player_ids.add(round_bye_id)
                 else:
                      logging.warning(f"Record Results: Attempt to double-record bye for round {round_index+1} for {p_bye.name}. Results len: {len(p_bye.results)}")
                      # success = False # Don't mark as failure, but this is odd.
            else:
                 logging.error(f"Record Results: Could not find bye player ID {round_bye_id}.")
                 success = False

        expected_ids = set(player_ids_in_pairings)
        if round_bye_id: expected_ids.add(round_bye_id)
        unprocessed = expected_ids - processed_player_ids
        if unprocessed:
            logging.warning(f"Record Results: Players/IDs in round {round_index + 1} not processed: {unprocessed}.")
        return success


    def compute_tiebreakers(self) -> None:
        # (No changes needed to this method based on the issues, assuming it's logically sound for its purpose)
        num_rounds_played = len(self.rounds_pairings_ids)
        if num_rounds_played == 0: return

        final_scores = {p.id: p.score for p in self.players.values()}
        player_dict = self.players

        for player in self.players.values():
            if not player.is_active and not player.results: # Skip fully inactive players with no history
                player.tiebreakers = {}
                continue

            player.tiebreakers = {}
            opponents = player.get_opponent_objects(player_dict)
            actual_opponents = []
            opponent_final_scores = [] # Scores of opponents FOR TIEBREAK CALC (can differ from current live score)
            sb_score = 0.0
            cumulative_opp_score = 0.0

            for i, opp_obj in enumerate(opponents):
                 if opp_obj is not None: # Not a bye
                      actual_opponents.append(opp_obj)
                      
                      # For tiebreaks like Solkoff/Median, use opponent's score.
                      # If opponent withdrew, their score is fixed at point of withdrawal for some systems,
                      # or their "final" score if tournament ended. Simpler: use current score.
                      # The original code's check for inactive opponent score seems reasonable:
                      # opp_final_score = (opp_obj.running_scores[-1] if opp_obj.running_scores and not opp_obj.is_active 
                      #                    else self.players.get(opp_obj.id, opp_obj).score) # Fallback if opp_obj is a shallow copy
                      # Simpler and often used: just use the opponent's current total score.
                      opp_current_score = self.players[opp_obj.id].score
                      opponent_final_scores.append(opp_current_score)


                      result_against_opp = player.results[i] if i < len(player.results) else None
                      if result_against_opp is not None:
                          if result_against_opp == WIN_SCORE: sb_score += opp_current_score
                          elif result_against_opp == DRAW_SCORE: sb_score += 0.5 * opp_current_score

                      cumulative_opp_score += opp_current_score


            # --- True Modified Median ---
            # USCF: "Adjusted scores of opponents. For players with more than 50% score, drop lowest. For less than 50%, drop highest. For 50%, drop highest and lowest."
            # This applies to games played, not total rounds.
            num_games_played_by_player = len([r for r in player.results if r is not None]) # Count actual games, not byes
            
            # Median / Solkoff usually doesn't count unplayed games (e.g. forfeits by opponent after pairing) as 0 for opponent score.
            # Here, opponent_final_scores are scores of opponents they actually played.

            if opponent_final_scores:
                # Sort scores for median calculation
                sorted_opp_scores = sorted(list(opponent_final_scores)) # Make a copy for manipulation
                
                # For Median Buchholz variants, handling of unplayed games (e.g., if an opponent later forfeits unrelated games) can vary.
                # Here we use the actual scores of opponents faced.

                # USCF Median (Mod. Median or Harkness System for ties)
                # Rule 34E3. The Median System (Modified Median or Harkness System).
                # This is sum of opponents' scores, highest and lowest dropped if player's score is 50% of max possible for games played.
                # If player's score > 50% of max possible for games played, drop only lowest.
                # If player's score < 50% of max possible for games played, drop only highest.
                
                # Max possible score for games player *actually played* (excluding byes this player received)
                max_score_for_played_games = float(len(actual_opponents)) * WIN_SCORE
                
                # Player's score from *played games only* (excluding points from byes player received)
                score_from_played_games = sum(player.results[i] for i, opp_id in enumerate(player.opponent_ids) if opp_id is not None and i < len(player.results))


                if not actual_opponents: # No games played against opponents
                    median_val = 0.0
                elif len(actual_opponents) == 1: # Only one opponent
                     median_val = sum(sorted_opp_scores) # effectively Solkoff for 1 game
                else: # Multiple opponents
                    if max_score_for_played_games == 0: # Avoid division by zero if no games played somehow
                        median_val = sum(sorted_opp_scores)
                    elif score_from_played_games > max_score_for_played_games / 2.0:
                        median_val = sum(sorted_opp_scores[1:]) # Drop lowest
                    elif score_from_played_games < max_score_for_played_games / 2.0:
                        median_val = sum(sorted_opp_scores[:-1]) # Drop highest
                    else: # Exactly 50%
                        if len(sorted_opp_scores) >= 2 : # Need at least 2 scores to drop both
                             median_val = sum(sorted_opp_scores[1:-1]) # Drop highest and lowest
                        else: # Only one score, cannot drop two. Or if only 2 scores, sum is 0.
                             median_val = sum(sorted_opp_scores) # Or 0 if only 1-2 opps and 50% score. Sum is fine.
            else:
                median_val = 0.0
            
            player.tiebreakers[TB_MEDIAN] = median_val
            player.tiebreakers[TB_SOLKOFF] = sum(opponent_final_scores) # Sum of all opponents' scores
            player.tiebreakers[TB_CUMULATIVE] = sum(player.running_scores) if player.running_scores else 0.0
            player.tiebreakers[TB_CUMULATIVE_OPP] = cumulative_opp_score # This is also Solkoff if calculated simply
            player.tiebreakers[TB_SONNENBORN_BERGER] = sb_score
            player.tiebreakers[TB_MOST_BLACKS] = float(player.num_black_games)
            player.tiebreakers[TB_HEAD_TO_HEAD] = 0.0 # Needs specific calculation logic if used directly

    def _compare_players(self, p1: Player, p2: Player) -> int:
        # (No changes needed here based on issues)
        if p1.score != p2.score: return 1 if p1.score > p2.score else -1
        h2h_score_p1_vs_p2 = 0.0
        p1_won_h2h = False
        p2_won_h2h = False

        for i, opp_id in enumerate(p1.opponent_ids):
            if opp_id == p2.id and i < len(p1.results):
                result = p1.results[i]
                if result == WIN_SCORE: p1_won_h2h = True
                elif result == LOSS_SCORE: p2_won_h2h = True
        
        if p1_won_h2h and not p2_won_h2h: return 1 # p1 beat p2
        if p2_won_h2h and not p1_won_h2h: return -1 # p2 beat p1

        for tb_key in self.tiebreak_order: 
            tb1 = p1.tiebreakers.get(tb_key, 0.0)
            tb2 = p2.tiebreakers.get(tb_key, 0.0)
            if tb1 != tb2: return 1 if tb1 > tb2 else -1
        if p1.rating != p2.rating: return 1 if p1.rating > p2.rating else -1
        if p1.name != p2.name: return -1 if p1.name < p2.name else 1
        return 0

    def get_standings(self) -> List[Player]:
        # Active players are typically shown first, then inactive ones, or inactive are hidden.
        # Current _get_active_players() filters out inactive ones. This is fine for standings.
        players_for_standings = self._get_active_players() 
        # If you want to show inactive players at the bottom:
        # players_for_standings = list(self.players.values())
        # players_for_standings.sort(key=lambda p: not p.is_active) # Active players first

        if not players_for_standings: return []
        self.compute_tiebreakers() 
        
        # Sort primarily by active status (active first), then score, then tiebreaks
        # However, get_standings is usually for ranked list of those still competing.
        # If inactive players are included, they usually appear after active ones with same score.
        # The _compare_players doesn't consider p.is_active.
        # For now, assuming get_standings is for active players.

        sorted_players = sorted(
            players_for_standings, # Only active ones
            key=functools.cmp_to_key(self._compare_players),
            reverse=True
        )
        return sorted_players

    def get_completed_rounds(self) -> int:
        # (No changes needed here)
        active_players = self._get_active_players()
        if not active_players: return 0
        players_with_results = [p for p in active_players if p.results]
        if not players_with_results: return 0
        # This should be min length of results for players who are *still active* and *have results*.
        # A player who withdrew in R1 (is_active=False) might have 1 result.
        # A player still active might have played 3 rounds. Min should be 3.
        # If all players withdrew after R1, completed_rounds is 1.
        # If some are active with 3 results, some active with 2 (late entry?), this is tricky.
        # "Completed rounds" usually means rounds for which *all* results of *scheduled* games are in.
        # The current_round_index in SwissTournamentApp is a better indicator of *processed* rounds.
        # This method is okay as an approximation.
        return min(len(p.results) for p in players_with_results)


    def to_dict(self) -> Dict[str, Any]:
        return {
            'app_version': APP_VERSION, 
            'num_rounds': self.num_rounds,
            'tiebreak_order': self.tiebreak_order,
            'players': [p.to_dict() for p in self.players.values()],
            'rounds_pairings_ids': self.rounds_pairings_ids,
            'rounds_byes_ids': self.rounds_byes_ids,
            'previous_matches': [list(pair) for pair in self.previous_matches],
            'manual_pairings': self.manual_pairings, 
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Tournament':
        players_data = data.get('players', [])
        if not players_data:
            # Compatibility: try to load from a simpler list of player dicts if 'players' key is missing
            # This depends on older save format, assuming it was just a list of player dicts at top level.
            # For now, assume current format or raise error.
             raise ValueError("Cannot load tournament: No player data found in 'players' key.")

        players = [Player.from_dict(p_data) for p_data in players_data]
        num_rounds = data.get('num_rounds', 0)
        tiebreak_order = data.get('tiebreak_order', list(DEFAULT_TIEBREAK_SORT_ORDER)) 

        if num_rounds <= 0: # Infer if missing
             num_rounds = len(data.get('rounds_pairings_ids', [])) or 3 # Default to 3 if nothing else
             logging.warning(f"Number of rounds not found or invalid, inferred/defaulted to {num_rounds}")

        tournament = cls(players, num_rounds, tiebreak_order) 
        tournament.rounds_pairings_ids = data.get('rounds_pairings_ids', [])
        tournament.rounds_byes_ids = data.get('rounds_byes_ids', [])
        tournament.previous_matches = set(frozenset(map(str, pair)) for pair in data.get('previous_matches', [])) # Ensure IDs are str
        
        # Convert round keys in manual_pairings back to int
        raw_manual_pairings = data.get('manual_pairings', {})
        tournament.manual_pairings = {int(k): v for k, v in raw_manual_pairings.items()}

        for p in tournament.players.values(): p._opponents_played_cache = [] 
        return tournament


# --- GUI Dialogs ---
# (No changes to PlayerEditDialog, PlayerDetailDialog, SettingsDialog, ManualPairDialog unless behaviorally impacted by core changes)
# PlayerDetailDialog: Default rating could be None, Player class handles default.
# SettingsDialog: Tiebreak order changes are reflected.

class PlayerEditDialog(QtWidgets.QDialog):
     def __init__(self, player_name: str, player_rating: int, player_active: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Player")
        self.layout = QtWidgets.QVBoxLayout(self)
        self.name_edit = QtWidgets.QLineEdit(player_name)
        self.rating_spin = QtWidgets.QSpinBox()
        self.rating_spin.setRange(0, 4000)
        self.rating_spin.setValue(player_rating if player_rating is not None else 1000) # Handle None rating
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
        name = self.name_edit.text().strip()
        rating = self.rating_spin.value()
        is_active = self.active_check.isChecked()
        return name, rating, is_active

class PlayerDetailDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, player_data: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.setWindowTitle("Add/Edit Player")
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        self.name_edit = QtWidgets.QLineEdit()
        self.rating_spin = QtWidgets.QSpinBox()
        self.rating_spin.setRange(0, 4000) # Rating can be 0 (e.g. unrated)
        self.rating_spin.setValue(1000) # Default if new
        gender_dob_layout = QtWidgets.QHBoxLayout()
        self.gender_combo = QtWidgets.QComboBox()
        self.gender_combo.addItems(["", "Male", "Female"])
        self.gender_combo.setToolTip("Select gender (optional)")
        gender_dob_layout.addWidget(QtWidgets.QLabel("Gender:"))
        gender_dob_layout.addWidget(self.gender_combo)
        self.dob_edit = QtWidgets.QDateEdit()
        self.dob_edit.setCalendarPopup(True)
        self.dob_edit.setDisplayFormat("yyyy-MM-dd")
        # Allow null/empty date by default
        self.dob_edit.setSpecialValueText(" ") # Show blank when date is not set
        self.dob_edit.setDate(QtCore.QDate()) # Start with an invalid/null date
        self.dob_edit.setToolTip("Select date of birth (optional)")
        # self.calendar_popup = QtWidgets.QCalendarWidget() # QDateEdit has its own popup
        # self.calendar_popup.setGridVisible(True)
        # self.calendar_popup.setMaximumDate(QtCore.QDate.currentDate())
        # self.dob_edit.setCalendarWidget(self.calendar_popup)
        gender_dob_layout.addSpacing(10)
        gender_dob_layout.addWidget(QtWidgets.QLabel("Date of Birth:"))
        gender_dob_layout.addWidget(self.dob_edit)
        phone_layout = QtWidgets.QHBoxLayout()
        self.phone_edit = QtWidgets.QLineEdit()
        self.btn_copy_phone = QtWidgets.QPushButton("📋")
        self.btn_copy_phone.setFixedWidth(28)
        self.btn_copy_phone.setToolTip("Copy phone number")
        self.btn_copy_phone.clicked.connect(lambda: QtWidgets.QApplication.clipboard().setText(self.phone_edit.text()))
        phone_layout.addWidget(self.phone_edit)
        phone_layout.addWidget(self.btn_copy_phone)
        email_layout = QtWidgets.QHBoxLayout()
        self.email_edit = QtWidgets.QLineEdit()
        self.btn_copy_email = QtWidgets.QPushButton("📋")
        self.btn_copy_email.setFixedWidth(28)
        self.btn_copy_email.setToolTip("Copy email address")
        self.btn_copy_email.clicked.connect(lambda: QtWidgets.QApplication.clipboard().setText(self.email_edit.text()))
        email_layout.addWidget(self.email_edit)
        email_layout.addWidget(self.btn_copy_email)
        self.club_edit = QtWidgets.QLineEdit()
        self.federation_edit = QtWidgets.QLineEdit()
        form.addRow("Name:", self.name_edit)
        form.addRow("Rating:", self.rating_spin)
        form.addRow(gender_dob_layout)
        form.addRow("Phone:", phone_layout)
        form.addRow("Email:", email_layout)
        form.addRow("Club:", self.club_edit)
        form.addRow("Federation:", self.federation_edit)
        layout.addLayout(form)
        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        if player_data:
            self.name_edit.setText(player_data.get('name', ''))
            self.rating_spin.setValue(player_data.get('rating', 1000) if player_data.get('rating') is not None else 1000)
            gender = player_data.get('gender', '')
            idx = self.gender_combo.findText(gender) if gender else 0
            self.gender_combo.setCurrentIndex(idx if idx >= 0 else 0)
            dob_str = player_data.get('dob')
            if dob_str:
                q_date = QtCore.QDate.fromString(dob_str, "yyyy-MM-dd")
                if q_date.isValid(): self.dob_edit.setDate(q_date)
                else: self.dob_edit.setDate(QtCore.QDate()) # Set to null if invalid
            else:
                self.dob_edit.setDate(QtCore.QDate()) # Set to null if not present

            self.phone_edit.setText(player_data.get('phone', '') or '')
            self.email_edit.setText(player_data.get('email', '') or '')
            self.club_edit.setText(player_data.get('club', '') or '')
            self.federation_edit.setText(player_data.get('federation', '') or '')
    def accept(self):
        if self.dob_edit.date().isValid() and self.dob_edit.date() > QtCore.QDate.currentDate():
            QtWidgets.QMessageBox.warning(self, "Validation Error", "Date of birth cannot be in the future.")
            return
        super().accept()
    def get_player_data(self) -> Dict[str, Any]:
        dob_qdate = self.dob_edit.date()
        return {
            'name': self.name_edit.text().strip(),
            'rating': self.rating_spin.value(),
            'gender': self.gender_combo.currentText() if self.gender_combo.currentText() else None,
            'dob': dob_qdate.toString("yyyy-MM-dd") if dob_qdate.isValid() else None,
            'phone': self.phone_edit.text().strip() or None,
            'email': self.email_edit.text().strip() or None,
            'club': self.club_edit.text().strip() or None,
            'federation': self.federation_edit.text().strip() or None
        }

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, num_rounds: int, tiebreak_order: List[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tournament Settings")
        self.setMinimumWidth(350)
        self.current_tiebreak_order = list(tiebreak_order) 
        layout = QtWidgets.QVBoxLayout(self)
        rounds_group = QtWidgets.QGroupBox("General")
        rounds_layout = QtWidgets.QFormLayout(rounds_group)
        self.spin_num_rounds = QtWidgets.QSpinBox()
        self.spin_num_rounds.setRange(1, 50)
        self.spin_num_rounds.setValue(num_rounds)
        self.spin_num_rounds.setToolTip("Set the total number of rounds.")
        rounds_layout.addRow("Number of Rounds:", self.spin_num_rounds)
        layout.addWidget(rounds_group)
        tiebreak_group = QtWidgets.QGroupBox("Tiebreak Order")
        tiebreak_layout = QtWidgets.QHBoxLayout(tiebreak_group)
        self.tiebreak_list = QtWidgets.QListWidget()
        self.tiebreak_list.setToolTip("Order in which tiebreaks are applied (higher is better). Drag to reorder.")
        self.tiebreak_list.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)
        self.populate_tiebreak_list()
        tiebreak_layout.addWidget(self.tiebreak_list)
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
        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
    def populate_tiebreak_list(self):
        self.tiebreak_list.clear()
        for tb_key in self.current_tiebreak_order:
            display_name = TIEBREAK_NAMES.get(tb_key, tb_key) 
            item = QtWidgets.QListWidgetItem(display_name)
            item.setData(Qt.ItemDataRole.UserRole, tb_key) 
            self.tiebreak_list.addItem(item)
    def move_tiebreak_up(self):
        current_row = self.tiebreak_list.currentRow()
        if current_row > 0:
            item = self.tiebreak_list.takeItem(current_row)
            self.tiebreak_list.insertItem(current_row - 1, item)
            self.tiebreak_list.setCurrentRow(current_row - 1)
            self.update_order_from_list()
    def move_tiebreak_down(self):
        current_row = self.tiebreak_list.currentRow()
        if current_row < self.tiebreak_list.count() - 1:
            item = self.tiebreak_list.takeItem(current_row)
            self.tiebreak_list.insertItem(current_row + 1, item)
            self.tiebreak_list.setCurrentRow(current_row + 1)
            self.update_order_from_list()
    def update_order_from_list(self):
         self.current_tiebreak_order = [self.tiebreak_list.item(i).data(Qt.ItemDataRole.UserRole)
                                        for i in range(self.tiebreak_list.count())]
    def accept(self):
         self.update_order_from_list()
         super().accept()
    def get_settings(self) -> Tuple[int, List[str]]:
        return self.spin_num_rounds.value(), self.current_tiebreak_order

class ManualPairDialog(QtWidgets.QDialog):
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
          self.opponent_combo.addItem("", None) 
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
          self.selected_opponent_id = self.opponent_combo.currentData()
          if not self.selected_opponent_id:
               QtWidgets.QMessageBox.warning(self, "Selection Error", "Please select a new opponent.")
               return 
          super().accept()
     def get_selected_opponent_id(self) -> Optional[str]:
          return self.selected_opponent_id

# --- Main Application Window ---

class SwissTournamentApp(QtWidgets.QMainWindow):
    """Main application window for the Swiss Tournament."""
    def __init__(self) -> None:
        super().__init__()
        self.tournament: Optional[Tournament] = None
        # current_round_index is the index of the round for which pairings have been *generated*
        # and results might be pending. If it's 0, R1 pairings might be shown.
        # After R1 results are recorded, it becomes 1, R2 pairings shown.
        self.current_round_index: int = 0 
        self.last_recorded_results_data: List[Tuple[str, str, float]] = [] 
        self._current_filepath: Optional[str] = None 
        self._dirty: bool = False 

        self._setup_ui()
        self._update_ui_state()

    def _setup_ui(self):
        self.setWindowTitle(APP_NAME)
        self.setGeometry(100, 100, 1000, 800) 
        self.setWindowIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_ComputerIcon)) 
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QtWidgets.QVBoxLayout(self.central_widget)
        self._setup_menu()
        self._setup_toolbar()
        self._setup_main_panel() 
        self.statusBar().showMessage("Ready - Create New or Load Tournament.")
        logging.info(f"{APP_NAME} v{APP_VERSION} started.")

    def _setup_menu(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        self.new_action = self._create_action("&New Tournament...", self.prompt_new_tournament, "Ctrl+N", "Create a new tournament file")
        self.load_action = self._create_action("&Load Tournament...", self.load_tournament, "Ctrl+O", "Load a tournament from a file")
        self.save_action = self._create_action("&Save Tournament", self.save_tournament, "Ctrl+S", "Save the current tournament")
        self.save_as_action = self._create_action("Save Tournament &As...", lambda: self.save_tournament(save_as=True), "Ctrl+Shift+S", "Save the current tournament to a new file")
        self.new_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileIcon))
        self.load_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogOpenButton))
        self.save_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogSaveButton))
        self.save_as_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogSaveButton))
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.load_action)
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addSeparator()
        self.import_players_action = self._create_action("&Import Players from CSV...", self.import_players_csv, tooltip="Import players from a CSV file (Name,Rating)")
        self.export_players_action = self._create_action("&Export Players to CSV...", self.export_players_csv, tooltip="Export registered players to CSV")
        self.export_standings_action = self._create_action("&Export Standings...", self.export_standings, tooltip="Export current standings to CSV or Text")
        self.import_players_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_ArrowDown))
        self.export_players_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_ArrowUp))
        self.export_standings_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DriveFDIcon))
        file_menu.addAction(self.import_players_action)
        file_menu.addAction(self.export_players_action)
        file_menu.addAction(self.export_standings_action)
        file_menu.addSeparator()
        self.settings_action = self._create_action("S&ettings...", self.show_settings_dialog, tooltip="Configure tournament settings (rounds, tiebreaks)")
        self.settings_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileDialogDetailedView))
        file_menu.addAction(self.settings_action)
        file_menu.addSeparator()
        self.exit_action = self._create_action("E&xit", self.close, "Ctrl+Q", "Exit the application")
        self.exit_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogCloseButton))
        file_menu.addAction(self.exit_action)
        tournament_menu = menu_bar.addMenu("&Tournament")
        self.start_action = self._create_action("&Start Tournament", self.start_tournament, tooltip="Start the tournament with current players/settings")
        self.prepare_round_action = self._create_action("&Prepare Next Round", self.prepare_next_round, tooltip="Generate pairings for the next round")
        self.record_results_action = self._create_action("&Record Results && Advance", self.record_and_advance, tooltip="Save results for the current round")
        self.undo_results_action = self._create_action("&Undo Last Results", self.undo_last_results, tooltip="Revert the last recorded round")
        self.start_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MediaPlay))
        self.prepare_round_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MediaSkipForward))
        self.record_results_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogApplyButton))
        self.undo_results_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_ArrowBack))
        tournament_menu.addAction(self.start_action)
        tournament_menu.addAction(self.prepare_round_action)
        tournament_menu.addAction(self.record_results_action)
        tournament_menu.addAction(self.undo_results_action)
        player_menu = menu_bar.addMenu("&Players")
        self.add_player_action = self._create_action("&Add Player...", self.focus_add_player_input, tooltip="Focus the input field to add a player")
        self.add_player_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileIcon)) # Changed icon
        player_menu.addAction(self.add_player_action)
        view_menu = menu_bar.addMenu("&View")
        self.view_control_action = view_menu.addAction("Tournament &Control")
        self.view_control_action.triggered.connect(lambda: self.tabs.setCurrentWidget(self.tournament_tab))
        self.view_standings_action = view_menu.addAction("&Standings")
        self.view_standings_action.triggered.connect(lambda: self.tabs.setCurrentWidget(self.standings_tab))
        self.view_crosstable_action = view_menu.addAction("&Cross-Table")
        self.view_crosstable_action.triggered.connect(lambda: self.tabs.setCurrentWidget(self.crosstable_tab))
        self.view_log_action = view_menu.addAction("History &Log")
        self.view_log_action.triggered.connect(lambda: self.tabs.setCurrentWidget(self.history_tab))
        help_menu = menu_bar.addMenu("&Help")
        self.about_action = self._create_action("&About...", self.show_about_dialog, tooltip="Show application information")
        self.about_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MessageBoxInformation))
        help_menu.addAction(self.about_action)

    def _create_action(self, text: str, slot: callable, shortcut: str = "", tooltip: str = "") -> QAction:
        action = QAction(text, self)
        action.triggered.connect(slot)
        if shortcut: action.setShortcut(QtGui.QKeySequence(shortcut))
        if tooltip: action.setToolTip(tooltip); action.setStatusTip(tooltip)
        return action

    def _setup_toolbar(self):
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.setIconSize(QtCore.QSize(24, 24)) 
        # Standard icons are set in _setup_menu, they propagate here.
        toolbar.addAction(self.new_action)
        toolbar.addAction(self.load_action)
        toolbar.addAction(self.save_action)
        toolbar.addSeparator()
        toolbar.addAction(self.start_action)
        toolbar.addAction(self.prepare_round_action)
        toolbar.addAction(self.record_results_action)
        toolbar.addAction(self.undo_results_action)

    def _setup_main_panel(self):
        self.tabs = QtWidgets.QTabWidget()
        self.main_layout.addWidget(self.tabs)
        self.tournament_tab = QtWidgets.QWidget()
        tab_layout = QtWidgets.QVBoxLayout(self.tournament_tab)
        top_splitter = QtWidgets.QSplitter(Qt.Orientation.Horizontal)
        player_group = QtWidgets.QGroupBox("Players")
        player_group.setToolTip("Manage players. Right-click list items for actions.")
        player_group_layout = QtWidgets.QVBoxLayout(player_group)
        self.list_players = QtWidgets.QListWidget()
        self.list_players.setToolTip("Registered players. Right-click to Edit/Withdraw/Reactivate/Remove.")
        self.list_players.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_players.customContextMenuRequested.connect(self.on_player_context_menu)
        self.list_players.setAlternatingRowColors(True)
        player_group_layout.addWidget(self.list_players)
        # Add Player button (now that detailed dialog is primary)
        self.btn_add_player_detail = QtWidgets.QPushButton(icon=self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileDialogNewFolder), text=" Add New Player...")
        self.btn_add_player_detail.setToolTip("Open dialog to add a new player with full details.")
        self.btn_add_player_detail.clicked.connect(self.add_player_detailed)
        player_group_layout.addWidget(self.btn_add_player_detail)
        top_splitter.addWidget(player_group)
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
        top_splitter.setSizes([350, 150]) # Adjust initial sizes
        tab_layout.addWidget(top_splitter)
        self.round_group = QtWidgets.QGroupBox("Current Round Pairings & Results")
        round_layout = QtWidgets.QVBoxLayout(self.round_group)
        self.table_pairings = QtWidgets.QTableWidget(0, 5)
        self.table_pairings.setHorizontalHeaderLabels(["White", "Black", "Result", "Quick Result", "Action"]) 
        self.table_pairings.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table_pairings.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table_pairings.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.table_pairings.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.table_pairings.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.ResizeToContents) 
        self.table_pairings.verticalHeader().setVisible(False)
        self.table_pairings.setAlternatingRowColors(True)
        self.table_pairings.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        round_layout.addWidget(self.table_pairings)
        self.lbl_bye = QtWidgets.QLabel("Bye: None")
        round_layout.addWidget(self.lbl_bye)
        # --- Add Print Pairings Button ---
        self.btn_print_pairings = QtWidgets.QPushButton("Print Pairings")
        self.btn_print_pairings.setToolTip("Print the current round's pairings")
        self.btn_print_pairings.clicked.connect(self.print_pairings)
        round_layout.addWidget(self.btn_print_pairings)
        tab_layout.addWidget(self.round_group)
        self.tabs.addTab(self.tournament_tab, "Tournament Control")
        self.standings_tab = QtWidgets.QWidget()
        standings_tab_layout = QtWidgets.QVBoxLayout(self.standings_tab)
        self.standings_group = QtWidgets.QGroupBox("Standings")
        standings_layout = QtWidgets.QVBoxLayout(self.standings_group)
        self.table_standings = QtWidgets.QTableWidget(0, 3) 
        self.table_standings.setHorizontalHeaderLabels(["Rank", "Player", "Score"])
        self.table_standings.setToolTip("Player standings sorted by Score and configured Tiebreakers.")
        self.table_standings.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table_standings.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_standings.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_standings.setAlternatingRowColors(True)
        standings_layout.addWidget(self.table_standings)
        # --- Add Print Standings Button ---
        self.btn_print_standings = QtWidgets.QPushButton("Print Standings")
        self.btn_print_standings.setToolTip("Print the current standings table")
        self.btn_print_standings.clicked.connect(self.print_standings)
        standings_layout.addWidget(self.btn_print_standings)
        standings_tab_layout.addWidget(self.standings_group)
        self.tabs.addTab(self.standings_tab, "Standings")
        self.crosstable_tab = QtWidgets.QWidget()
        crosstable_tab_layout = QtWidgets.QVBoxLayout(self.crosstable_tab)
        self.crosstable_group = QtWidgets.QGroupBox("Cross-Table")
        crosstable_layout = QtWidgets.QVBoxLayout(self.crosstable_group)
        self.table_crosstable = QtWidgets.QTableWidget(0, 0) 
        self.table_crosstable.setToolTip("Grid showing results between players.")
        self.table_crosstable.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_crosstable.setAlternatingRowColors(True)
        font = self.table_crosstable.font()
        font.setPointSize(font.pointSize() - 1)
        self.table_crosstable.setFont(font)
        crosstable_layout.addWidget(self.table_crosstable)
        crosstable_tab_layout.addWidget(self.crosstable_group)
        self.tabs.addTab(self.crosstable_tab, "Cross-Table")
        self.history_tab = QtWidgets.QWidget()
        history_layout = QtWidgets.QVBoxLayout(self.history_tab)
        self.history_view = QtWidgets.QPlainTextEdit()
        self.history_view.setReadOnly(True)
        self.history_view.setToolTip("Log of pairings, results, and actions.")
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont) # Monospaced font
        self.history_view.setFont(font)
        history_layout.addWidget(self.history_view)
        self.tabs.addTab(self.history_tab, "History Log")

    def _update_ui_state(self):
        tournament_exists = self.tournament is not None
        
        # Number of rounds for which pairings have been generated
        pairings_generated_for_rounds = len(self.tournament.rounds_pairings_ids) if tournament_exists else 0
        
        # Number of rounds for which results are fully recorded and processed by core logic.
        # This is essentially self.current_round_index if it means "next round to play/pair".
        # Or, more accurately, completed_rounds is the number of rounds whose results are IN.
        # If current_round_index points to the round WHOSE PAIRINGS ARE SHOWN, then current_round_index = completed_rounds.
        # For example, after R1 results recorded, current_round_index becomes 1. Completed rounds = 1.
        # Pairings for R2 (index 1) are then generated. So pairings_generated_for_rounds = 2.
        
        completed_rounds = self.current_round_index # This now means rounds with results fully recorded & processed by GUI advance logic.

        total_rounds_in_tournament = self.tournament.num_rounds if tournament_exists else 0

        tournament_started = tournament_exists and pairings_generated_for_rounds > 0
        # Can start if tournament exists, not yet started, and has enough players.
        can_start = tournament_exists and not tournament_started and len(self.tournament.players) >= 2
        
        # Can prepare next round if:
        # 1. Tournament started.
        # 2. All generated pairings have results recorded (pairings_generated_for_rounds == completed_rounds).
        # 3. Not all tournament rounds have been generated yet.
        can_prepare_next = tournament_exists and tournament_started and \
                           pairings_generated_for_rounds == completed_rounds and \
                           pairings_generated_for_rounds < total_rounds_in_tournament
        
        # Can record results if:
        # 1. Tournament started.
        # 2. Pairings have been generated for the current_round_index (i.e., pairings_generated_for_rounds > completed_rounds).
        can_record = tournament_exists and tournament_started and \
                     pairings_generated_for_rounds > completed_rounds
        
        # Can undo if results for at least one round have been recorded (completed_rounds > 0).
        # And last_recorded_results_data is not empty (safety).
        can_undo = tournament_exists and completed_rounds > 0 and bool(self.last_recorded_results_data)

        self.save_action.setEnabled(tournament_exists)
        self.save_as_action.setEnabled(tournament_exists)
        self.export_standings_action.setEnabled(tournament_exists and completed_rounds > 0)
        self.settings_action.setEnabled(True) 
        self.import_players_action.setEnabled(not tournament_started)
        self.export_players_action.setEnabled(tournament_exists and len(self.tournament.players) > 0)
        self.btn_add_player_detail.setEnabled(not tournament_started) # Can add players before start

        self.start_action.setEnabled(can_start)
        self.btn_start.setEnabled(can_start)
        self.prepare_round_action.setEnabled(can_prepare_next)
        self.btn_next.setEnabled(can_prepare_next)
        self.record_results_action.setEnabled(can_record)
        self.btn_record.setEnabled(can_record)
        self.undo_results_action.setEnabled(can_undo)
        self.btn_undo.setEnabled(can_undo)

        can_manage_players_in_list = True # Always allow withdraw/reactivate via context menu
        self.list_players.setEnabled(can_manage_players_in_list) # List itself always enabled for context menu
        self.add_player_action.setEnabled(not tournament_started) # Menu action linked to detail dialog trigger now

        status = "Ready - Create New or Load Tournament."
        if tournament_exists:
            if not tournament_started:
                status = f"Add players (min 2), check Settings, then Start Tournament. {len(self.tournament.players)} players."
            elif can_record:
                status = f"Round {completed_rounds + 1} pairings ready. Enter results."
            elif can_prepare_next:
                status = f"Round {completed_rounds} results recorded. Prepare Round {completed_rounds + 1}."
            elif completed_rounds == total_rounds_in_tournament and total_rounds_in_tournament > 0:
                status = f"Tournament finished after {total_rounds_in_tournament} rounds."
            else: # Catch-all for other states
                status = f"Tournament in progress. Completed rounds: {completed_rounds}/{total_rounds_in_tournament}."
        
        self.statusBar().showMessage(status)

        title = APP_NAME
        if self._current_filepath:
             title += f" - {QFileInfo(self._current_filepath).fileName()}"
        if self._dirty:
             title += "*"
        self.setWindowTitle(title)


    def mark_dirty(self):
        if not self._dirty:
             self._dirty = True
             self._update_ui_state() 

    def mark_clean(self):
        if self._dirty:
             self._dirty = False
             self._update_ui_state()


    def prompt_new_tournament(self):
        if not self.check_save_before_proceeding(): return
        self.reset_tournament_state()
        # Create a temporary tournament object for settings dialog
        temp_tournament_for_settings = Tournament([], num_rounds=3, tiebreak_order=list(DEFAULT_TIEBREAK_SORT_ORDER))
        self.tournament = temp_tournament_for_settings # So settings dialog can access it

        if self.show_settings_dialog(): # This will apply settings to self.tournament
             self.update_history_log(f"--- New Tournament Created (Rounds: {self.tournament.num_rounds}) ---")
             self.mark_dirty() 
             self.update_standings_table_headers() 
        else:
             self.reset_tournament_state() # User cancelled settings, so no tournament
        self._update_ui_state()


    def show_settings_dialog(self) -> bool:
         if not self.tournament: # Should not happen if prompt_new_tournament sets a temp one
              # Fallback: if called directly without a tournament context
              current_rounds = 3 
              current_tiebreaks = list(DEFAULT_TIEBREAK_SORT_ORDER)
         else:
              current_rounds = self.tournament.num_rounds
              current_tiebreaks = self.tournament.tiebreak_order

         dialog = SettingsDialog(current_rounds, current_tiebreaks, self)
         # Tournament started if pairings for R1 (index 0) exist.
         tournament_started = self.tournament and len(self.tournament.rounds_pairings_ids) > 0
         dialog.spin_num_rounds.setEnabled(not tournament_started) 

         if dialog.exec():
              new_rounds, new_tiebreaks = dialog.get_settings()
              if not self.tournament: # Should create one if totally new
                  self.tournament = Tournament([], num_rounds=new_rounds, tiebreak_order=new_tiebreaks)
                  self.mark_dirty()

              rounds_changed = self.tournament.num_rounds != new_rounds
              tiebreaks_changed = self.tournament.tiebreak_order != new_tiebreaks

              if rounds_changed and not tournament_started:
                   self.tournament.num_rounds = new_rounds
                   self.update_history_log(f"Number of rounds set to {new_rounds}.")
                   self.mark_dirty()
              elif rounds_changed and tournament_started:
                   QtWidgets.QMessageBox.information(self, "Settings Info", "Number of rounds cannot be changed after the tournament has started.")
              
              if tiebreaks_changed:
                   self.tournament.tiebreak_order = new_tiebreaks
                   self.update_history_log(f"Tiebreak order updated: {', '.join(TIEBREAK_NAMES.get(k, k) for k in new_tiebreaks)}")
                   self.mark_dirty()
                   self.update_standings_table_headers() 
                   if self.tournament.get_completed_rounds() > 0 or len(self.tournament.players)>0 : # Only update if there's data
                        self.update_standings_table() 

              self._update_ui_state()
              return True 
         return False 

    def focus_add_player_input(self):
        """Menu action to trigger adding a player, now directly calls detailed add."""
        self.add_player_detailed()


    def on_player_context_menu(self, point: QtCore.QPoint) -> None:
        item = self.list_players.itemAt(point)
        if not item or not self.tournament: return
        player_id = item.data(Qt.ItemDataRole.UserRole)
        player = self.tournament.players.get(player_id)
        if not player: return

        # Tournament started if pairings for R1 (index 0) exist.
        tournament_started = len(self.tournament.rounds_pairings_ids) > 0

        menu = QtWidgets.QMenu(self)
        edit_action = menu.addAction("Edit Player Details...")
        # Withdraw/Reactivate action text depends on player's current state
        withdraw_action_text = "Withdraw Player" if player.is_active else "Reactivate Player"
        withdraw_action = menu.addAction(withdraw_action_text)
        remove_action = menu.addAction("Remove Player")

        edit_action.setEnabled(not tournament_started) 
        remove_action.setEnabled(not tournament_started) 
        # Withdraw/Reactivate should be possible anytime, affecting future pairings/bye eligibility.
        withdraw_action.setEnabled(True) 

        action = menu.exec(self.list_players.mapToGlobal(point))

        if action == edit_action:
            dialog = PlayerDetailDialog(self, player_data=player.to_dict())
            if dialog.exec():
                data = dialog.get_player_data()
                if not data['name']:
                    QtWidgets.QMessageBox.warning(self, "Edit Error", "Player name cannot be empty.")
                    return
                # Check for duplicate name (only if name changed and it's not the current player's ID)
                if data['name'] != player.name and any(p.name == data['name'] for p in self.tournament.players.values()):
                     QtWidgets.QMessageBox.warning(self, "Edit Error", f"Another player named '{data['name']}' already exists.")
                     return
                
                player.name = data['name']
                player.rating = data['rating']
                player.gender = data.get('gender')
                player.dob = data.get('dob')
                player.phone = data.get('phone')
                player.email = data.get('email')
                player.club = data.get('club')
                player.federation = data.get('federation')
                
                self.update_player_list_item(player) # Helper to update QListWidgetItem
                self.update_history_log(f"Player '{player.name}' details updated.")
                self.mark_dirty()
        elif action == withdraw_action:
             player.is_active = not player.is_active
             status_log_msg = "Withdrawn" if not player.is_active else "Reactivated"
             self.update_player_list_item(player)
             self.update_history_log(f"Player '{player.name}' {status_log_msg}.")
             self.mark_dirty()
             self.update_standings_table() # Reflects active status if standings show inactive
             self._update_ui_state() # UI might depend on active player count

        elif action == remove_action:
             reply = QtWidgets.QMessageBox.question(self, "Remove Player", f"Remove player '{player.name}' permanently?",
                                                 QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                                                 QtWidgets.QMessageBox.StandardButton.No)
             if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                  row = self.list_players.row(item) # Get row before taking item
                  self.list_players.takeItem(row)
                  del self.tournament.players[player_id]
                  self.update_history_log(f"Player '{player.name}' removed.")
                  self.mark_dirty()
                  self._update_ui_state()


    def update_player_list_item(self, player: Player):
        """Finds and updates the QListWidgetItem for a given player."""
        for i in range(self.list_players.count()):
            item = self.list_players.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == player.id:
                display_text = f"{player.name} ({player.rating})"
                tooltip_parts = [f"ID: {player.id}"]
                if not player.is_active:
                    display_text += " (Inactive)"
                    tooltip_parts.append("Status: Inactive")
                else:
                    tooltip_parts.append("Status: Active")

                if player.gender: tooltip_parts.append(f"Gender: {player.gender}")
                if player.dob: tooltip_parts.append(f"Date of Birth: {player.dob}")
                if player.phone: tooltip_parts.append(f"Phone: {player.phone}")
                if player.email: tooltip_parts.append(f"Email: {player.email}")
                if player.club: tooltip_parts.append(f"Club: {player.club}")
                if player.federation: tooltip_parts.append(f"Federation: {player.federation}")
                
                item.setText(display_text)
                item.setToolTip("\n".join(tooltip_parts))
                item.setForeground(QtGui.QColor("gray") if not player.is_active else self.list_players.palette().color(QtGui.QPalette.ColorRole.Text))
                break


    def add_player_detailed(self):
        tournament_started = self.tournament and len(self.tournament.rounds_pairings_ids) > 0
        if tournament_started:
            QtWidgets.QMessageBox.warning(self, "Tournament Active", "Cannot add players after the tournament has started.")
            return
        if not self.tournament:
            # If adding player before "New Tournament" is fully confirmed via settings
            reply = QtWidgets.QMessageBox.information(self, "New Tournament", 
                                                  "A new tournament will be created with default settings. You can change settings later via File > Settings.",
                                                  QtWidgets.QMessageBox.StandardButton.Ok | QtWidgets.QMessageBox.StandardButton.Cancel)
            if reply == QtWidgets.QMessageBox.StandardButton.Cancel:
                return
            self.reset_tournament_state() # Clear any previous partial state
            self.tournament = Tournament([], num_rounds=3, tiebreak_order=list(DEFAULT_TIEBREAK_SORT_ORDER))
            self.update_history_log("--- New Tournament Implicitly Created (Default Settings) ---")
            self.mark_dirty()


        dialog = PlayerDetailDialog(self)
        if dialog.exec():
            data = dialog.get_player_data()
            if not data['name']:
                QtWidgets.QMessageBox.warning(self, "Validation Error", "Player name cannot be empty.")
                return
            if any(p.name == data['name'] for p in self.tournament.players.values()):
                QtWidgets.QMessageBox.warning(self, "Duplicate Player", f"Player '{data['name']}' already exists.")
                return
            new_player = Player(
                name=data['name'],
                rating=data['rating'],
                phone=data['phone'],
                email=data['email'],
                club=data['club'],
                federation=data['federation'],
                gender=data.get('gender'),
                dob=data.get('dob')
            )
            self.tournament.players[new_player.id] = new_player
            self.add_player_to_list_widget(new_player)
            self.statusBar().showMessage(f"Added player: {new_player.name}")
            self.update_history_log(f"Player '{new_player.name}' ({new_player.rating}) added.")
            self.mark_dirty()
            self._update_ui_state()


    def add_player_to_list_widget(self, player: Player):
         display_text = f"{player.name} ({player.rating})"
         tooltip_parts = [f"ID: {player.id}"]
         if not player.is_active:
             display_text += " (Inactive)"
             tooltip_parts.append("Status: Inactive")
         else:
            tooltip_parts.append("Status: Active")

         if player.gender: tooltip_parts.append(f"Gender: {player.gender}")
         if player.dob: tooltip_parts.append(f"Date of Birth: {player.dob}")
         if player.phone: tooltip_parts.append(f"Phone: {player.phone}")
         if player.email: tooltip_parts.append(f"Email: {player.email}")
         if player.club: tooltip_parts.append(f"Club: {player.club}")
         if player.federation: tooltip_parts.append(f"Federation: {player.federation}")

         list_item = QtWidgets.QListWidgetItem(display_text)
         list_item.setData(Qt.ItemDataRole.UserRole, player.id)
         list_item.setToolTip("\n".join(tooltip_parts))
         if not player.is_active:
              list_item.setForeground(QtGui.QColor("gray"))
         self.list_players.addItem(list_item)


    def import_players_csv(self):
         if self.tournament and len(self.tournament.rounds_pairings_ids) > 0:
              QtWidgets.QMessageBox.warning(self, "Import Error", "Cannot import players after tournament has started.")
              return
         if not self.tournament:
             # Implicitly create a new tournament if one doesn't exist
            self.reset_tournament_state()
            self.tournament = Tournament([], num_rounds=3, tiebreak_order=list(DEFAULT_TIEBREAK_SORT_ORDER))
            self.update_history_log("--- New Tournament Implicitly Created for Import (Default Settings) ---")
            self.mark_dirty()


         filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Import Players", "", CSV_FILTER)
         if not filename: return

         imported_count = 0
         skipped_count = 0
         try:
              with open(filename, 'r', encoding='utf-8-sig') as f: 
                   reader = csv.reader(f)
                   header = next(reader, None) 
                   # Basic header check for Name, Rating - can be extended for more columns
                   expected_headers_min = ['name', 'rating']
                   header_indices = {}
                   if header:
                       for i, col_name in enumerate(header):
                           col_name_lower = col_name.lower().strip()
                           if col_name_lower in ["name", "player name", "player"]: header_indices['name'] = i
                           elif col_name_lower in ["rating", "elo"]: header_indices['rating'] = i
                           elif col_name_lower == "gender": header_indices['gender'] = i
                           elif col_name_lower in ["dob", "date of birth", "birthdate"]: header_indices['dob'] = i
                           elif col_name_lower == "phone": header_indices['phone'] = i
                           elif col_name_lower == "email": header_indices['email'] = i
                           elif col_name_lower == "club": header_indices['club'] = i
                           elif col_name_lower == "federation": header_indices['federation'] = i
                       
                       if 'name' not in header_indices : # If crucial 'name' header is missing, assume no header
                           logging.info("CSV header not recognized or 'name' column missing, processing as no header.")
                           f.seek(0) # Rewind to process first line as data
                           header_indices = {'name': 0, 'rating': 1} # Default column order
                   else: # No lines in file or only one line which is data
                       f.seek(0)
                       header_indices = {'name': 0, 'rating': 1}


                   for row_idx, row in enumerate(reader):
                        if not row or not row[header_indices.get('name', 0)].strip(): # Skip empty rows or rows with no name
                            skipped_count +=1
                            logging.warning(f"Skipping empty or unnamed row {row_idx+1} during import: {row}")
                            continue
                        
                        name = row[header_indices.get('name', 0)].strip()
                        rating_str = row[header_indices.get('rating', 1)] if len(row) > header_indices.get('rating', 1) else None
                        rating = None
                        if rating_str and rating_str.strip():
                            try: rating = int(rating_str.strip())
                            except ValueError: 
                                logging.warning(f"Invalid rating '{rating_str}' for player {name}, using default.")
                                rating = None # Player class will use default

                        # Optional fields
                        def get_val(key_name, default_idx):
                            idx = header_indices.get(key_name)
                            if idx is not None and idx < len(row): return row[idx].strip() or None
                            # Fallback to default index if key_name not in header_indices but default_idx exists
                            if idx is None and default_idx is not None and default_idx < len(row) : return row[default_idx].strip() or None
                            return None

                        phone = get_val('phone', 2)
                        email = get_val('email', 3)
                        club = get_val('club', 4)
                        federation = get_val('federation', 5)
                        gender = get_val('gender', 6)
                        dob = get_val('dob', 7)


                        if name:
                             if any(p.name == name for p in self.tournament.players.values()):
                                  logging.warning(f"Skipping duplicate player name during import: {name}")
                                  skipped_count += 1
                             else:
                                  new_player = Player(name, rating, phone=phone, email=email, club=club, federation=federation, gender=gender, dob=dob)
                                  self.tournament.players[new_player.id] = new_player
                                  self.add_player_to_list_widget(new_player)
                                  imported_count += 1
                        else: # Should be caught by earlier check
                             skipped_count += 1

              msg = f"Imported {imported_count} players."
              if skipped_count > 0: msg += f" Skipped {skipped_count} duplicates/invalid/empty rows."
              QtWidgets.QMessageBox.information(self, "Import Complete", msg)
              self.update_history_log(f"Imported {imported_count} players from {QFileInfo(filename).fileName()}. Skipped {skipped_count}.")
              self.mark_dirty()
              self._update_ui_state()

         except Exception as e:
              logging.exception(f"Error importing players from {filename}:")
              QtWidgets.QMessageBox.critical(self, "Import Error", f"Could not import players:\n{e}")
              self.statusBar().showMessage("Error importing players.")


    def export_players_csv(self):
        if not self.tournament or not self.tournament.players:
            QtWidgets.QMessageBox.information(self, "Export Error", "No players available to export.")
            return
        filename, selected_filter = QtWidgets.QFileDialog.getSaveFileName(self, "Export Players", "", "CSV Files (*.csv);;Text Files (*.txt)")
        if not filename: return
        try:
            is_csv = selected_filter.startswith("CSV")
            delimiter = "," if is_csv else "\t"
            with open(filename, "w", encoding="utf-8", newline='') as f:
                writer = csv.writer(f, delimiter=delimiter)
                writer.writerow(["Name", "Rating", "Gender", "Date of Birth", "Phone", "Email", "Club", "Federation", "Active", "ID"]) # Added ID
                for player in sorted(list(self.tournament.players.values()), key=lambda p: p.name): # Sort by name
                    writer.writerow([
                        player.name,
                        player.rating if player.rating is not None else "",
                        player.gender or "",
                        player.dob or "",
                        player.phone or "",
                        player.email or "",
                        player.club or "",
                        player.federation or "",
                        "Yes" if player.is_active else "No",
                        player.id
                    ])
            QtWidgets.QMessageBox.information(self, "Export Successful", f"Players exported to {filename}")
            self.statusBar().showMessage(f"Players exported to {filename}")
        except Exception as e:
            logging.exception("Error exporting players:")
            QtWidgets.QMessageBox.critical(self, "Export Error", f"Could not export players:\n{e}")
            self.statusBar().showMessage("Error exporting players.")


    def reset_tournament_state(self):
         self.tournament = None
         self.current_round_index = 0 
         self.last_recorded_results_data = []
         self._current_filepath = None
         self._dirty = False 
         self.list_players.clear()
         self.table_pairings.setRowCount(0)
         self.table_standings.setRowCount(0)
         self.table_crosstable.setRowCount(0)
         self.table_crosstable.setColumnCount(0)
         self.history_view.clear()
         self.lbl_bye.setText("Bye: None")
         self.round_group.setTitle("Current Round Pairings & Results")
         # Do not log here, as this is often called before setting up a new tournament that logs its own creation.
         self._update_ui_state()
         
    def prepare_next_round(self) -> None:
        if not self.tournament: return

        # round_to_prepare_idx is the index for rounds_pairings_ids (0 for R1, 1 for R2, etc.)
        # This should align with self.current_round_index if it means "round for which results are completed"
        # Or, more accurately, completed_rounds is the number of rounds whose results are IN.
        # If current_round_index points to the round WHOSE PAIRINGS ARE SHOWN, then current_round_index = completed_rounds.
        # For example, after R1 results recorded, current_round_index becomes 1. Completed rounds = 1.
        # Pairings for R2 (index 1) are then generated. So pairings_generated_for_rounds = 2.
        
        round_to_prepare_idx = self.current_round_index 
        
        if round_to_prepare_idx >= self.tournament.num_rounds:
             QtWidgets.QMessageBox.information(self,"Tournament End", "All tournament rounds have been generated and processed.")
             self._update_ui_state(); return
        
        # Check if pairings for this round_to_prepare_idx already exist
        # This happens if "Prepare Next Round" is clicked again without "Record Results"
        if round_to_prepare_idx < len(self.tournament.rounds_pairings_ids):
            reply = QtWidgets.QMessageBox.question(self, "Re-Prepare Round?",
                                                   f"Pairings for Round {round_to_prepare_idx + 1} already exist. Re-generate them?\n"
                                                   "This is usually not needed unless player active status changed significantly.",
                                                   QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                                                   QtWidgets.QMessageBox.StandardButton.No)
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                # Clear existing pairings for this round to regenerate
                self.tournament.rounds_pairings_ids = self.tournament.rounds_pairings_ids[:round_to_prepare_idx]
                self.tournament.rounds_byes_ids = self.tournament.rounds_byes_ids[:round_to_prepare_idx]
                # We might need to clear previous_matches entries that were added for this specific round too.
                # This is complex. For now, re-pairing might result in same opponent if not careful.
                # A safer "re-prepare" might involve more state rollback.
                # Simpler: just let create_pairings run again. It checks previous_matches.
                self.update_history_log(f"--- Re-preparing pairings for Round {round_to_prepare_idx + 1} ---")
            else: # User chose not to re-prepare
                # Just display existing pairings
                display_round_num = round_to_prepare_idx + 1
                pairings_ids = self.tournament.rounds_pairings_ids[round_to_prepare_idx]
                bye_id = self.tournament.rounds_byes_ids[round_to_prepare_idx]
                pairings = []
                for w_id, b_id in pairings_ids:
                    w = self.tournament.players.get(w_id); b = self.tournament.players.get(b_id)
                    if w and b: pairings.append((w,b))
                bye_player = self.tournament.players.get(bye_id) if bye_id else None
                self.round_group.setTitle(f"Round {display_round_num} Pairings & Results Input")
                self.display_pairings_for_input(pairings, bye_player)
                self._update_ui_state()
                return


        display_round_number = self.current_round_index + 1
        self.statusBar().showMessage(f"Generating pairings for Round {display_round_number}...")
        QtWidgets.QApplication.processEvents()

        try:
            # create_pairings expects 1-based round number for its internal logic (e.g. R1 specific)
            pairings, bye_player = self.tournament.create_pairings(
                display_round_number,
                allow_repeat_pairing_callback=self.prompt_repeat_pairing
            )
            
            if not pairings and len(self.tournament._get_active_players()) > 1 and not bye_player : # Handle cases where pairing might fail
                if len(self.tournament._get_active_players()) % 2 == 0 : # Even players, no bye expected, but no pairings
                     QtWidgets.QMessageBox.critical(self, "Pairing Error", f"Pairing generation failed for Round {display_round_number}. No pairings returned. Check logs and player statuses.")
                     self.statusBar().showMessage(f"Error generating pairings for Round {display_round_number}.")
                     self._update_ui_state()
                     return
                # If odd players and no bye_player, also an issue if pairings are also empty.

            self.round_group.setTitle(f"Round {display_round_number} Pairings & Results Input")
            self.display_pairings_for_input(pairings, bye_player)
            self.update_history_log(f"--- Round {display_round_number} Pairings Generated ---")
            for white, black in pairings: self.update_history_log(f"  {white.name} (W) vs {black.name} (B)")
            if bye_player: self.update_history_log(f"  Bye: {bye_player.name}")
            self.update_history_log("-" * 20)
            self.statusBar().showMessage(f"Round {display_round_number} pairings ready. Enter results.")
            self.mark_dirty() 
        except Exception as e:
            logging.exception(f"Error generating pairings for Round {display_round_number}:")
            QtWidgets.QMessageBox.critical(self, "Pairing Error", f"Pairing generation failed for Round {display_round_number}:\n{e}")
            self.statusBar().showMessage(f"Error generating pairings for Round {display_round_number}.")
        finally:
             self._update_ui_state()

    def start_tournament(self) -> None:
        if not self.tournament:
            QtWidgets.QMessageBox.warning(self, "Start Error", "No tournament loaded.")
            return
        if len(self.tournament.players) < 2:
            QtWidgets.QMessageBox.warning(self, "Start Error", "Add at least two players.")
            return
        # New minimum players check based on the number of rounds
        min_players = 2 ** self.tournament.num_rounds
        if len(self.tournament.players) < min_players:
            reply = QtWidgets.QMessageBox.warning(
                self,
                "Insufficient Players",
                f"For a {self.tournament.num_rounds}-round tournament, a minimum of {min_players} players is recommended. The tournament may not work properly. Do you want to continue anyway?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.No
            )
            if reply == QtWidgets.QMessageBox.StandardButton.No:
                return
        reply = QtWidgets.QMessageBox.question(
            self,
            "Start Tournament",
            f"Start a {self.tournament.num_rounds}-round tournament with {len(self.tournament.players)} players?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.Yes
        )
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        # Use current_round_index (starting at 0 for Round 1)
        if self.current_round_index >= self.tournament.num_rounds:
             QtWidgets.QMessageBox.information(self,"Tournament End", "All tournament rounds have been generated and processed.")
             self._update_ui_state(); return
        
        # Check if pairings for the current round already exist
        if self.current_round_index < len(self.tournament.rounds_pairings_ids):
            reply = QtWidgets.QMessageBox.question(self, "Re-Prepare Round?",
                                                   f"Pairings for Round {self.current_round_index + 1} already exist. Re-generate them?\n"
                                                   "This is usually not needed unless player active status changed significantly.",
                                                   QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                                                   QtWidgets.QMessageBox.StandardButton.No)
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                # Clear existing pairings for this round to regenerate
                self.tournament.rounds_pairings_ids = self.tournament.rounds_pairings_ids[:self.current_round_index]
                self.tournament.rounds_byes_ids = self.tournament.rounds_byes_ids[:self.current_round_index]
                self.update_history_log(f"--- Re-preparing pairings for Round {self.current_round_index + 1} ---")
            else: 
                # Just display existing pairings
                display_round_num = self.current_round_index + 1
                pairings_ids = self.tournament.rounds_pairings_ids[self.current_round_index]
                bye_id = self.tournament.rounds_byes_ids[self.current_round_index]
                pairings = []
                for w_id, b_id in pairings_ids:
                    w = self.tournament.players.get(w_id); b = self.tournament.players.get(b_id)
                    if w and b: pairings.append((w,b))
                bye_player = self.tournament.players.get(bye_id) if bye_id else None
                self.round_group.setTitle(f"Round {display_round_num} Pairings & Results Input")
                self.display_pairings_for_input(pairings, bye_player)
                self._update_ui_state()
                return


        display_round_number = self.current_round_index + 1
        self.statusBar().showMessage(f"Generating pairings for Round {display_round_number}...")
        QtWidgets.QApplication.processEvents()

        try:
            pairings, bye_player = self.tournament.create_pairings(
                display_round_number,
                allow_repeat_pairing_callback=self.prompt_repeat_pairing
            )
            
            if not pairings and len(self.tournament._get_active_players()) > 1 and not bye_player : # Handle cases where pairing might fail
                if len(self.tournament._get_active_players()) % 2 == 0 : # Even players, no bye expected, but no pairings
                     QtWidgets.QMessageBox.critical(self, "Pairing Error", f"Pairing generation failed for Round {display_round_number}. No pairings returned. Check logs and player statuses.")
                     self.statusBar().showMessage(f"Error generating pairings for Round {display_round_number}.")
                     self._update_ui_state()
                     return
                # If odd players and no bye_player, also an issue if pairings are also empty.

            self.round_group.setTitle(f"Round {display_round_number} Pairings & Results Input")
            self.display_pairings_for_input(pairings, bye_player)
            self.update_history_log(f"--- Round {display_round_number} Pairings Generated ---")
            for white, black in pairings: self.update_history_log(f"  {white.name} (W) vs {black.name} (B)")
            if bye_player: self.update_history_log(f"  Bye: {bye_player.name}")
            self.update_history_log("-" * 20)
            self.statusBar().showMessage(f"Round {display_round_number} pairings ready. Enter results.")
            self.mark_dirty() 
        except Exception as e:
            logging.exception(f"Error generating pairings for Round {display_round_number}:")
            QtWidgets.QMessageBox.critical(self, "Pairing Error", f"Pairing generation failed for Round {display_round_number}:\n{e}")
            self.statusBar().showMessage(f"Error generating pairings for Round {display_round_number}.")
        finally:
             self._update_ui_state()

    def prompt_repeat_pairing(self, player1, player2):
        msg = (f"No valid new opponent found for {player1.name}.\n"
               f"Would you like to allow a repeat pairing with {player2.name} to ensure all players are paired?")
        reply = QtWidgets.QMessageBox.question(
            self,
            "Repeat Pairing Needed",
            msg,
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.Yes
        )
        return reply == QtWidgets.QMessageBox.StandardButton.Yes

    def display_pairings_for_input(self, pairings: List[Tuple[Player, Player]], bye_player: Optional[Player]):
        self.table_pairings.clearContents()
        self.table_pairings.setRowCount(len(pairings))

        current_round_display_idx = self.current_round_index # Round whose pairings are being shown
        # Disable adjust button if results for this round are already submitted (i.e., current_round_index has advanced past this one)
        # This check is slightly complex because display_pairings can be called for current or past (undone) round.
        # Generally, if we are *inputting* results, current_round_index matches the displayed round's index.
        # So, can_adjust is true if round_index_of_pairings == self.current_round_index.
        # We need to know the actual index of the round these pairings belong to.
        # This function is called by prepare_next_round (for self.current_round_index)
        # and by undo_last_results (for self.current_round_index, which is the undone round)
        # So, adjustment is for the round currently indexed by self.current_round_index.
        can_adjust_pairings = True # Assume yes unless logic to disable is added for "already recorded" state.
                                  # Manual adjust should only be before results are recorded.

        for row, (white, black) in enumerate(pairings):
            item_white = QtWidgets.QTableWidgetItem(f"{white.name} ({white.rating})" + (" (I)" if not white.is_active else ""))
            item_white.setFlags(item_white.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item_white.setToolTip(f"ID: {white.id}\nColor History: {' '.join(c or '_' for c in white.color_history)}")
            if not white.is_active: item_white.setForeground(QtGui.QColor("gray"))
            self.table_pairings.setItem(row, 0, item_white)

            item_black = QtWidgets.QTableWidgetItem(f"{black.name} ({black.rating})" + (" (I)" if not black.is_active else ""))
            item_black.setFlags(item_black.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item_black.setToolTip(f"ID: {black.id}\nColor History: {' '.join(c or '_' for c in black.color_history)}")
            if not black.is_active: item_black.setForeground(QtGui.QColor("gray"))
            self.table_pairings.setItem(row, 1, item_black)

            combo_result = QtWidgets.QComboBox()
            combo_result.addItems(["", RESULT_WHITE_WIN, RESULT_DRAW, RESULT_BLACK_WIN])
            combo_result.setToolTip("Select result (White's perspective)")
            combo_result.setProperty("row", row)
            combo_result.setProperty("white_id", white.id)
            combo_result.setProperty("black_id", black.id)
            
            # Auto-set result if one or both players are inactive *at the time of display*
            # This is a UI hint; final result processing in Tournament.record_results handles actual scoring.
            if not white.is_active and not black.is_active: combo_result.setCurrentText(RESULT_DRAW) # 0-0 or F-F
            elif not white.is_active: combo_result.setCurrentText(RESULT_BLACK_WIN) # Black wins by forfeit
            elif not black.is_active: combo_result.setCurrentText(RESULT_WHITE_WIN) # White wins by forfeit
            self.table_pairings.setCellWidget(row, 2, combo_result)

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

            adjust_btn = QtWidgets.QPushButton("...")
            adjust_btn.setFixedSize(25, 20)
            adjust_btn.setToolTip("Manually adjust this pairing (before results are recorded)")
            adjust_btn.setProperty("row", row)
            adjust_btn.setProperty("white_id", white.id)
            adjust_btn.setProperty("black_id", black.id)
            adjust_btn.clicked.connect(self.prompt_manual_adjust)
            # Disable if cannot adjust (e.g., results for this round already processed)
            # This depends on if display_pairings_for_input is for current input round or historical view.
            # For now, always enabled if pairings are shown for input.
            adjust_btn.setEnabled(can_adjust_pairings) 
            self.table_pairings.setCellWidget(row, 4, adjust_btn)

        if bye_player:
            status = " (Inactive)" if not bye_player.is_active else ""
            bye_score_info = BYE_SCORE if bye_player.is_active else 0.0 # Reflects score based on active status
            self.lbl_bye.setText(f"Bye: {bye_player.name} ({bye_player.rating}){status} - Receives {bye_score_info} point")
            self.lbl_bye.setVisible(True)
        else:
            self.lbl_bye.setText("Bye: None"); self.lbl_bye.setVisible(False)

        self.table_pairings.resizeColumnsToContents()
        self.table_pairings.resizeRowsToContents()

    def set_quick_result(self, row: int, result_text: str):
         combo_box = self.table_pairings.cellWidget(row, 2)
         if isinstance(combo_box, QtWidgets.QComboBox):
              index = combo_box.findText(result_text)
              if index >= 0: combo_box.setCurrentIndex(index)

    def prompt_manual_adjust(self):
         sender_button = self.sender()
         if not sender_button or not self.tournament: return

         row = sender_button.property("row")
         white_id = sender_button.property("white_id")
         black_id = sender_button.property("black_id")
         
         # Manual adjustment applies to the round currently displayed for input,
         # which is self.current_round_index.

         if self.current_round_index >= len(self.tournament.rounds_pairings_ids):
              QtWidgets.QMessageBox.warning(self, "Adjust Error", "Cannot adjust pairings for a round not yet fully generated in backend.")
              return
         # Also check if results for this round_idx_to_adjust have already been "committed" by advancing current_round_index
         # This check is tricky. 'current_round_index' is the round results are FOR.
         # If record_and_advance was called, current_round_index would have incremented.
         # For now, assume if adjust button is clickable, it's for the current "inputtable" round.

         player_to_adjust = self.tournament.players.get(white_id) 
         current_opponent = self.tournament.players.get(black_id)
         if not player_to_adjust or not current_opponent:
              QtWidgets.QMessageBox.critical(self, "Adjust Error", "Could not find players for this pairing.")
              return

         available_opponents = [p for p_id, p in self.tournament.players.items()
                                if p.is_active and p_id != white_id and p_id != black_id]
         
         # Also consider current bye player as a potential opponent IF a bye exists for this round.
         current_bye_id_for_round = self.tournament.rounds_byes_ids[self.current_round_index]
         if current_bye_id_for_round and current_bye_id_for_round not in [white_id, black_id]:
             bye_player_obj = self.tournament.players.get(current_bye_id_for_round)
             if bye_player_obj and bye_player_obj.is_active: # Can only pair with active bye player
                 # Check if already in list (should not be due to p_id != white_id etc.)
                 if not any(avail_p.id == bye_player_obj.id for avail_p in available_opponents):
                     available_opponents.append(bye_player_obj)


         dialog = ManualPairDialog(player_to_adjust.name, current_opponent.name, available_opponents, self)
         if dialog.exec():
              new_opponent_id = dialog.get_selected_opponent_id()
              if new_opponent_id:
                   new_opp_player = self.tournament.players.get(new_opponent_id)
                   if not new_opp_player: 
                       QtWidgets.QMessageBox.critical(self, "Adjust Error", "Selected new opponent not found.")
                       return

                   reply = QtWidgets.QMessageBox.warning(self, "Confirm Manual Pairing",
                                                       f"Manually pair {player_to_adjust.name} against {new_opp_player.name} for Round {self.current_round_index+1}?\n"
                                                       f"This will attempt to adjust other affected pairings.\n"
                                                       f"This action is logged. Undoing might require manual fixes if complex.",
                                                       QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                                                       QtWidgets.QMessageBox.StandardButton.No)
                   if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                        if self.tournament.manually_adjust_pairing(self.current_round_index, white_id, new_opponent_id):
                             self.update_history_log(f"MANUAL PAIRING: Round {self.current_round_index+1}, {player_to_adjust.name} vs {new_opp_player.name}. Other pairs adjusted.")
                             # Refresh the pairings display for the current round
                             current_pairings_ids = self.tournament.rounds_pairings_ids[self.current_round_index]
                             current_bye_id = self.tournament.rounds_byes_ids[self.current_round_index]
                             refreshed_pairings = []
                             for w_id, b_id in current_pairings_ids:
                                  w = self.tournament.players.get(w_id)
                                  b = self.tournament.players.get(b_id)
                                  if w and b: refreshed_pairings.append((w,b))
                             refreshed_bye_player = self.tournament.players.get(current_bye_id) if current_bye_id else None
                             self.display_pairings_for_input(refreshed_pairings, refreshed_bye_player)
                             self.mark_dirty()
                        else:
                             QtWidgets.QMessageBox.critical(self, "Adjust Error", "Manual pairing adjustment failed. Check logs. Pairings might be inconsistent.")


    def record_and_advance(self) -> None:
        if not self.tournament: return
        
        # Results are for the round currently displayed, which is self.current_round_index
        round_index_to_record = self.current_round_index
        
        if round_index_to_record >= len(self.tournament.rounds_pairings_ids):
             QtWidgets.QMessageBox.warning(self, "Record Error", "No pairings available to record results for this round index.")
             return

        results_data, all_entered = self.get_results_from_table()
        if not all_entered:
            QtWidgets.QMessageBox.warning(self, "Incomplete Results", "Please enter a result for all pairings.")
            return
        if results_data is None: 
             QtWidgets.QMessageBox.critical(self, "Input Error", "Error retrieving results from table. Cannot proceed.")
             return

        try:
            if self.tournament.record_results(round_index_to_record, results_data):
                self.last_recorded_results_data = list(results_data) # Store deep copy for undo
                
                display_round_number = round_index_to_record + 1
                self.update_history_log(f"--- Round {display_round_number} Results Recorded ---")
                self.log_results_details(results_data, round_index_to_record)

                # Advance current_round_index *after* successful recording and logging
                self.current_round_index += 1

                self.update_standings_table()
                self.update_crosstable()
                self.tabs.setCurrentWidget(self.standings_tab) # Show standings after results
                
                if self.current_round_index >= self.tournament.num_rounds:
                    self.statusBar().showMessage(f"Tournament finished after {self.tournament.num_rounds} rounds.")
                    self.update_history_log(f"--- Tournament Finished ({self.tournament.num_rounds} Rounds) ---")
                    # Clear pairings table as no more rounds to input
                    self.table_pairings.setRowCount(0)
                    self.lbl_bye.setText("Bye: None")
                    self.round_group.setTitle("Tournament Finished")
                else:
                    self.statusBar().showMessage(f"Round {display_round_number} results recorded. Prepare Round {self.current_round_index + 1}.")
                    # Clear pairings table for next round prep
                    self.table_pairings.setRowCount(0)
                    self.lbl_bye.setText("Bye: None")
                    self.round_group.setTitle(f"Round {self.current_round_index + 1} (Pending Preparation)")


                self.mark_dirty() 
            else: # record_results returned False
                 QtWidgets.QMessageBox.warning(self, "Recording Warning", "Some results may not have been recorded properly by the backend. Check logs and player status.")

        except Exception as e:
            logging.exception(f"Error during record_and_advance for round {round_index_to_record+1}:")
            QtWidgets.QMessageBox.critical(self, "Recording Error", f"Recording results failed:\n{e}")
            self.statusBar().showMessage("Error recording results.")
        finally:
             self._update_ui_state()

    def get_results_from_table(self) -> Tuple[Optional[List[Tuple[str, str, float]]], bool]:
         results_data = []
         all_entered = True
         if self.table_pairings.rowCount() == 0 and self.lbl_bye.text() == "Bye: None": # No pairings, no bye
             return [], True # Valid state of no results to record (e.g. if round had only a bye that was withdrawn)

         for row in range(self.table_pairings.rowCount()):
              combo_box = self.table_pairings.cellWidget(row, 2)
              if isinstance(combo_box, QtWidgets.QComboBox):
                   result_text = combo_box.currentText()
                   white_id = combo_box.property("white_id")
                   black_id = combo_box.property("black_id")
                   if not result_text: all_entered = False; break # Found an unentered result
                   white_score = -1.0
                   if result_text == RESULT_WHITE_WIN: white_score = WIN_SCORE
                   elif result_text == RESULT_DRAW: white_score = DRAW_SCORE
                   elif result_text == RESULT_BLACK_WIN: white_score = LOSS_SCORE
                   
                   if white_score >= 0 and white_id and black_id: 
                       results_data.append((white_id, black_id, white_score))
                   else: 
                       logging.error(f"Invalid result data in table row {row}: Text='{result_text}', W_ID='{white_id}', B_ID='{black_id}'")
                       # If IDs are missing, it's a table setup problem, critical.
                       if not white_id or not black_id: return None, False 
                       all_entered = False; break # If score invalid but IDs ok, treat as not entered.
              else: 
                  logging.error(f"Missing combo box in pairings table, row {row}. Table improperly configured."); 
                  return None, False # Critical error
         return results_data, all_entered

    def log_results_details(self, results_data, round_index_recorded): # round_index is 0-based
         # Log paired game results
         for w_id, b_id, score_w in results_data:
              w = self.tournament.players.get(w_id) # Assume player exists
              b = self.tournament.players.get(b_id)
              score_b_display = f"{WIN_SCORE - score_w:.1f}" # Calculate display for black's score
              self.update_history_log(f"  {w.name if w else w_id} ({score_w:.1f}) - {b.name if b else b_id} ({score_b_display})")
         
         # Log bye if one was assigned for the undone round
         if round_index_recorded < len(self.tournament.rounds_byes_ids):
            bye_id = self.tournament.rounds_byes_ids[round_index_recorded]
            if bye_id:
                bye_player = self.tournament.players.get(bye_id)
                if bye_player:
                    status = " (Inactive - No Score)" if not bye_player.is_active else ""
                    # Actual score for bye is handled by record_results based on active status
                    bye_score_awarded = BYE_SCORE if bye_player.is_active else 0.0
                    self.update_history_log(f"  Bye point ({bye_score_awarded:.1f}) awarded to: {bye_player.name}{status}")
                else:
                    self.update_history_log(f"  Bye player ID {bye_id} not found in player list (error).")
         self.update_history_log("-" * 20)


    def undo_last_results(self) -> None:
        if not self.tournament or not self.last_recorded_results_data or self.current_round_index == 0:
            # current_round_index is index of NEXT round to play. If 0, no rounds completed.
            QtWidgets.QMessageBox.warning(self, "Undo Error", "No results from a completed round are available to undo."); return

        round_to_undo_display_num = self.current_round_index # e.g. if current_round_index is 1, we undo R1 results.
        
        reply = QtWidgets.QMessageBox.question(self,"Undo Results", 
                                             f"Undo results from Round {round_to_undo_display_num} and revert to its pairing stage?",
                                             QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                                             QtWidgets.QMessageBox.StandardButton.No)
        if reply != QtWidgets.QMessageBox.StandardButton.Yes: return

        try:
            # The round whose results are being undone (0-indexed)
            round_index_being_undone = self.current_round_index - 1
            
            # Revert player stats for each game in last_recorded_results_data
            for white_id, black_id, _ in self.last_recorded_results_data:
                p_white = self.tournament.players.get(white_id)
                p_black = self.tournament.players.get(black_id)
                if p_white: self._revert_player_round_data(p_white)
                if p_black: self._revert_player_round_data(p_black)
            
            # Revert bye player stats if a bye was given in the undone round
            if round_index_being_undone < len(self.tournament.rounds_byes_ids):
                bye_player_id_undone_round = self.tournament.rounds_byes_ids[round_index_being_undone]
                if bye_player_id_undone_round:
                    p_bye = self.tournament.players.get(bye_player_id_undone_round)
                    if p_bye: self._revert_player_round_data(p_bye)

            # Crucial: Do NOT pop from tournament's rounds_pairings_ids or rounds_byes_ids here.
            # These store the historical pairings. Undoing results means we are going back to the
            # state *before* these results were entered for that specific round's pairings.
            # The pairings themselves remain.
            
            # If manual pairings were made for the round being undone, they are part of its history.
            # They are not automatically "undone" unless the user manually re-pairs.
            if round_index_being_undone in self.tournament.manual_pairings:
                 logging.warning(f"Manual pairings for round {round_to_undo_display_num} were part of its setup and are not automatically reverted by undoing results.")

            self.last_recorded_results_data = [] # Clear the stored results for "can_undo" check
            self.current_round_index -= 1 # Decrement GUI's round counter

            # --- Update UI ---
            # Re-display pairings for the round being "re-opened" for input
            self.round_group.setTitle(f"Round {self.current_round_index + 1} Pairings & Results Input (Re-entry)")
            
            pairings_ids_to_redisplay = self.tournament.rounds_pairings_ids[self.current_round_index]
            bye_id_to_redisplay = self.tournament.rounds_byes_ids[self.current_round_index]
            
            pairings_to_redisplay = []
            for w_id, b_id in pairings_ids_to_redisplay:
                 w = self.tournament.players.get(w_id)
                 b = self.tournament.players.get(b_id)
                 if w and b: pairings_to_redisplay.append((w,b))
                 else: logging.warning(f"Load: Missing player for pairing ({w_id} vs {b_id}) in loaded round {display_round_to_redisplay}")
            
            bye_player_to_redisplay = self.tournament.players.get(bye_id_to_redisplay) if bye_id_to_redisplay else None
            
            self.display_pairings_for_input(pairings_to_redisplay, bye_player_to_redisplay)
            self.tabs.setCurrentWidget(self.tournament_tab)

            self.update_standings_table() # Reflect reverted scores
            self.update_crosstable()
            self.update_history_log(f"--- Round {round_to_undo_display_num} Results Undone ---")
            self.statusBar().showMessage(f"Round {round_to_undo_display_num} results undone. Re-enter results or re-prepare round.")
            self.mark_dirty() 

        except Exception as e:
            logging.exception("Error undoing results:")
            QtWidgets.QMessageBox.critical(self, "Undo Error", f"Undoing results failed:\n{e}")
            self.statusBar().showMessage("Error undoing results.")
        finally:
             self._update_ui_state()


    def _revert_player_round_data(self, player: Player):
         """Helper to remove the last round's data from a player object's history lists."""
         if not player.results: return # No results to revert
         
         last_result = player.results.pop()
         # Score is recalculated from scratch or by subtracting. Subtracting is simpler here.
         if last_result is not None: player.score = round(player.score - last_result, 1) # round to handle float issues

         if player.running_scores: player.running_scores.pop()
         
         last_opponent_id = player.opponent_ids.pop() if player.opponent_ids else None
         last_color = player.color_history.pop() if player.color_history else None
         
         if last_color == "Black": player.num_black_games = max(0, player.num_black_games - 1)
         
         if last_opponent_id is None: # Means the undone round was a bye for this player
             # Check if they *still* have other byes in their history.
             # If not, has_received_bye becomes False.
             player.has_received_bye = (None in player.opponent_ids) if player.opponent_ids else False
             logging.debug(f"Player {player.name} bye undone. Has received bye: {player.has_received_bye}")

         # Invalidate opponent cache, it will be rebuilt on next access
         player._opponents_played_cache = []


    def update_standings_table_headers(self):
         if not self.tournament: return
         base_headers = ["Rank", "Player", "Score"]
         tb_headers = [TIEBREAK_NAMES.get(key, key.upper()) for key in self.tournament.tiebreak_order] # Use upper for unknown keys
         full_headers = base_headers + tb_headers
         self.table_standings.setColumnCount(len(full_headers))
         self.table_standings.setHorizontalHeaderLabels(full_headers)
         self.table_standings.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch) # Player name
         for i in range(len(full_headers)):
              if i != 1: self.table_standings.horizontalHeader().setSectionResizeMode(i, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
         header_tooltips = ["Rank", "Player Name (Rating)", "Total Score"] + \
                           [TIEBREAK_NAMES.get(key, f"Tiebreak: {key}") for key in self.tournament.tiebreak_order]
         for i, tip in enumerate(header_tooltips):
            if i < self.table_standings.columnCount(): # Check index is valid
                  header_item = self.table_standings.horizontalHeaderItem(i)
                  if header_item: # Ensure the QTableWidgetItem for header exists
                      header_item.setToolTip(tip)


    def update_standings_table(self) -> None:
        if not self.tournament: 
            self.table_standings.setRowCount(0)
            return

        try:
             # Ensure headers match current config first
             expected_col_count = 3 + len(self.tournament.tiebreak_order)
             if self.table_standings.columnCount() != expected_col_count:
                  self.update_standings_table_headers()

             standings = self.tournament.get_standings() # Gets sorted *active* players by default
             # If you want to show all players (active then inactive):
             # all_players_sorted = sorted(
             #    list(self.tournament.players.values()),
             #    key=functools.cmp_to_key(lambda p1, p2: (0 if p1.is_active else 1) - (0 if p2.is_active else 1) or self.tournament._compare_players(p1, p2)),
             #    reverse=False # custom sort, reverse for score happens in _compare_players
             # )
             # standings = all_players_sorted # Use this if showing all players.

             self.table_standings.setRowCount(len(standings))

             tb_formats = { 
                 TB_MEDIAN: '.2f', TB_SOLKOFF: '.2f', TB_CUMULATIVE: '.1f', # Using .2f for Median/Solkoff for finer detail
                 TB_CUMULATIVE_OPP: '.1f', TB_SONNENBORN_BERGER: '.2f', TB_MOST_BLACKS: '.0f' 
             }

             for rank, player in enumerate(standings):
                  row = rank
                  rank_str = str(rank + 1)
                  status_str = "" # Standings usually only show active players from get_standings()
                  # If inactive players were included in `standings`:
                  # status_str = "" if player.is_active else " (I)" 
                  
                  item_rank = QtWidgets.QTableWidgetItem(rank_str)
                  item_player = QtWidgets.QTableWidgetItem(f"{player.name} ({player.rating or 'NR'})" + status_str) # NR for No Rating
                  item_score = QtWidgets.QTableWidgetItem(f"{player.score:.1f}")
                  
                  item_rank.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                  item_score.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                  row_color = self.table_standings.palette().color(QtGui.QPalette.ColorRole.Text)
                  # if not player.is_active: row_color = QtGui.QColor("gray") # If showing inactive
                  
                  item_rank.setForeground(row_color)
                  item_player.setForeground(row_color)
                  item_score.setForeground(row_color)

                  self.table_standings.setItem(row, 0, item_rank)
                  self.table_standings.setItem(row, 1, item_player)
                  self.table_standings.setItem(row, 2, item_score)

                  col_offset = 3
                  for i, tb_key in enumerate(self.tournament.tiebreak_order):
                       value = player.tiebreakers.get(tb_key, 0.0)
                       format_spec = tb_formats.get(tb_key, '.2f') # Default format .2f
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
         if not self.tournament or not self.tournament.players:
              self.table_crosstable.setRowCount(0)
              self.table_crosstable.setColumnCount(0)
              return

         # Get players sorted by final rank (or current standings if tournament ongoing)
         # For crosstable, often all registered players are shown, sorted by current rank.
         # Here, using get_standings() which by default gives active players sorted.
         # To show all players:
         # all_players_list = list(self.tournament.players.values())
         # self.tournament.compute_tiebreakers() # Ensure tiebreakers are computed for everyone
         # sorted_players = sorted(all_players_list, key=functools.cmp_to_key(self.tournament._compare_players), reverse=True)
         
         sorted_players = self.tournament.get_standings() # Using active sorted players
         if not sorted_players: # No active players with results
             self.table_crosstable.setRowCount(0)
             self.table_crosstable.setColumnCount(0)
             return

         player_id_to_rank_map = {p.id: i for i, p in enumerate(sorted_players)}
         n = len(sorted_players)

         self.table_crosstable.setRowCount(n)
         self.table_crosstable.setColumnCount(n + 3) # Num, Name, Score + Opponent Ranks

         headers = ["#", "Player", "Score"] + [str(i + 1) for i in range(n)] 
         self.table_crosstable.setHorizontalHeaderLabels(headers)
         # Vertical headers: Rank. Name (Rating)
         v_headers = [f"{i+1}. {p.name} ({p.rating or 'NR'})" for i, p in enumerate(sorted_players)]
         self.table_crosstable.setVerticalHeaderLabels(v_headers)

         for r_idx, p1 in enumerate(sorted_players): # p1 is the player for the current row
              # Column 0: Rank
              rank_item = QtWidgets.QTableWidgetItem(str(r_idx + 1))
              rank_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
              self.table_crosstable.setItem(r_idx, 0, rank_item)
              # Column 1: Name (Rating)
              name_item = QtWidgets.QTableWidgetItem(f"{p1.name} ({p1.rating or 'NR'})")
              self.table_crosstable.setItem(r_idx, 1, name_item)
              # Column 2: Score
              score_item = QtWidgets.QTableWidgetItem(f"{p1.score:.1f}")
              score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
              self.table_crosstable.setItem(r_idx, 2, score_item)

              # Columns 3 to n+2: Results against opponents by their rank in sorted_players
              for round_num, opp_id_for_p1 in enumerate(p1.opponent_ids):
                   if round_num >= len(p1.results): continue # Result not yet recorded for this opponent

                   result_char = ""
                   bg_color = None
                   
                   if opp_id_for_p1 is None: # Bye for p1 in this round
                        result_char = "Bye"
                        bg_color = QtGui.QColor(255, 255, 224) # Light yellow
                        # Find an appropriate column to put "Bye" if player has multiple byes (not standard)
                        # Or just list sequentially. For now, find first empty opponent slot.
                        # This needs a better way to display non-opponent results.
                        # Simplification: crosstable mainly shows player-vs-player. Bye might be in notes.
                        # Let's assume we try to put it in p1's own column if empty
                        # For now, this complex display logic for byes in crosstable is deferred.
                        # We will fill player-vs-player cells.

                   elif opp_id_for_p1 in player_id_to_rank_map: # Opponent is in the sorted list
                        opp_rank_in_list = player_id_to_rank_map[opp_id_for_p1]
                        col_idx_for_opp = opp_rank_in_list + 3 # +3 for offset cols (Rank, Name, Score)
                        
                        result_val = p1.results[round_num]
                        color_played = p1.color_history[round_num] # "White" or "Black"
                        
                        opp_display_rank = opp_rank_in_list + 1 # 1-based rank of opponent

                        if result_val == WIN_SCORE: result_char = f"+{opp_display_rank}"
                        elif result_val == DRAW_SCORE: result_char = f"={opp_display_rank}"
                        elif result_val == LOSS_SCORE: result_char = f"-{opp_display_rank}"
                        else: result_char = "?" 
                        
                        if color_played == "White": result_char += "w"
                        elif color_played == "Black": result_char += "b"

                        item = QtWidgets.QTableWidgetItem(result_char)
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        # Optional: color based on win/loss/draw
                        if result_val == WIN_SCORE: item.setForeground(QtGui.QColor("green"))
                        elif result_val == LOSS_SCORE: item.setForeground(QtGui.QColor("red"))

                        self.table_crosstable.setItem(r_idx, col_idx_for_opp, item)
                   
                   # Else: opponent not in current sorted_players list (e.g. withdrawn and not shown)
                   # Such results won't appear against a ranked column.

              # Fill diagonal (player vs self) with gray background
              diag_item = QtWidgets.QTableWidgetItem("X") # Or player's score again, or empty
              diag_item.setBackground(QtGui.QColor(157, 157, 157)) # Light gray
              diag_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
              self.table_crosstable.setItem(r_idx, r_idx + 3, diag_item)


         self.table_crosstable.resizeColumnsToContents()
         self.table_crosstable.resizeRowsToContents()


    def update_history_log(self, message: str):
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        self.history_view.appendPlainText(f"[{timestamp}] {message}")
        logging.info(f"UI_LOG: {message}") # Distinguish from backend logging if needed


    def export_standings(self) -> None:
        if not self.tournament: QtWidgets.QMessageBox.information(self, "Export Error", "No tournament data."); return
        standings = self.tournament.get_standings() # Gets active sorted players
        if not standings: QtWidgets.QMessageBox.information(self, "Export Error", "No standings available to export."); return

        filename, selected_filter = QtWidgets.QFileDialog.getSaveFileName(self, "Export Standings", "", CSV_FILTER)
        if not filename: return

        try:
            with open(filename, "w", encoding="utf-8", newline='') as f:
                is_csv = selected_filter.startswith("CSV")
                delimiter = "," if is_csv else "\t"
                writer = csv.writer(f, delimiter=delimiter) if is_csv else None

                header = [self.table_standings.horizontalHeaderItem(i).text() 
                          for i in range(self.table_standings.columnCount())]
                if writer: writer.writerow(header)
                else: f.write(delimiter.join(header) + "\n")

                tb_formats = { 
                    TB_MEDIAN: '.2f', TB_SOLKOFF: '.2f', TB_CUMULATIVE: '.1f',
                    TB_CUMULATIVE_OPP: '.1f', TB_SONNENBORN_BERGER: '.2f', TB_MOST_BLACKS: '.0f' 
                }

                for rank, player in enumerate(standings):
                    rank_str = str(rank + 1)
                    player_str = f"{player.name} ({player.rating or 'NR'})" 
                    # If exporting all players, including inactive:
                    # player_str += (" (I)" if not player.is_active else "")
                    score_str = f"{player.score:.1f}"
                    data_row = [rank_str, player_str, score_str]
                    
                    for tb_key in self.tournament.tiebreak_order:
                         value = player.tiebreakers.get(tb_key, 0.0)
                         format_spec = tb_formats.get(tb_key, '.2f')
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
         if not self.tournament: 
             QtWidgets.QMessageBox.warning(self, "Save Error", "No tournament data to save."); return

         filename = self._current_filepath
         if save_as or not filename:
              filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Tournament", "", SAVE_FILE_FILTER)
              if not filename: return # User cancelled
              if not filename.lower().endswith(SAVE_FILE_EXTENSION): filename += SAVE_FILE_EXTENSION
              self._current_filepath = filename

         try:
              save_data = {
                   'app_gui_version': APP_VERSION, # Store GUI app version
                   'tournament_data': self.tournament.to_dict(), # Core tournament data
                   'gui_current_round_index': self.current_round_index, # GUI's tracking of current round
                   # last_recorded_results_data is transient for undo, not saved.
              }
              with open(filename, "w", encoding="utf-8") as f: json.dump(save_data, f, indent=4)
              self.statusBar().showMessage(f"Tournament saved to {filename}")
              self.update_history_log(f"--- Tournament Saved to {QFileInfo(filename).fileName()} ---")
              self.mark_clean() 
              self.setWindowTitle(f"{APP_NAME} - {QFileInfo(filename).fileName()}")
         except Exception as e:
              logging.exception(f"Error saving tournament to {filename}:")
              QtWidgets.QMessageBox.critical(self, "Save Error", f"Could not save tournament:\n{e}")
              self.statusBar().showMessage("Error saving tournament.")


    def load_tournament(self):
         if not self.check_save_before_proceeding(): return

         filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load Tournament", "", SAVE_FILE_FILTER)
         if not filename: return

         try:
              with open(filename, "r", encoding="utf-8") as f: load_data = json.load(f)
              
              # Compatibility with older save format
              if 'tournament' in load_data and 'tournament_data' not in load_data : # Older format likely
                  tournament_dict = load_data['tournament']
                  gui_round_idx = load_data.get('current_round_index',0)
                  logging.info("Loading from older save format.")
              elif 'tournament_data' in load_data: # Newer format
                  tournament_dict = load_data['tournament_data']
                  gui_round_idx = load_data.get('gui_current_round_index', 0)
              else:
                  raise ValueError("Invalid save file: Missing 'tournament' or 'tournament_data' key.")


              self.reset_tournament_state() 
              self.tournament = Tournament.from_dict(tournament_dict)
              self.current_round_index = gui_round_idx # Restore GUI's round progress
              self._current_filepath = filename

              self.list_players.clear()
              # Sort players by name for consistent display in list widget
              player_list_sorted = sorted(self.tournament.get_player_list(), key=lambda p: p.name.lower())
              for player in player_list_sorted: self.add_player_to_list_widget(player)

              # Display pairings for the current_round_index if results are pending for it.
              # current_round_index is the round whose results are to be entered next, or round to be prepared.
              # If current_round_index < len(tournament.rounds_pairings_ids), it means pairings for this round exist.
              if self.tournament and self.current_round_index < len(self.tournament.rounds_pairings_ids):
                   round_to_display_idx = self.current_round_index
                   display_round_num = round_to_display_idx + 1
                   self.round_group.setTitle(f"Round {display_round_num} Pairings & Results Input")
                   
                   pairings_ids = self.tournament.rounds_pairings_ids[round_to_display_idx]
                   bye_id = self.tournament.rounds_byes_ids[round_to_display_idx]
                   
                   pairings_to_show = []
                   for w_id, b_id in pairings_ids:
                        w = self.tournament.players.get(w_id)
                        b = self.tournament.players.get(b_id)
                        if w and b: pairings_to_show.append((w,b))
                        else: logging.warning(f"Load: Missing player for pairing ({w_id} vs {b_id}) in loaded round {display_round_num}")
                   
                   bye_player_to_show = self.tournament.players.get(bye_id) if bye_id else None
                   self.display_pairings_for_input(pairings_to_show, bye_player_to_show)
              else: 
                   self.table_pairings.setRowCount(0)
                   self.lbl_bye.setText("Bye: None")
                   if self.tournament and self.current_round_index >= self.tournament.num_rounds:
                       self.round_group.setTitle("Tournament Finished")
                   else:
                       self.round_group.setTitle(f"Round {self.current_round_index + 1} (Pending Preparation)")


              self.update_standings_table_headers() # Use loaded tiebreak order
              self.update_standings_table()
              self.update_crosstable()
              self.mark_clean() 
              self.statusBar().showMessage(f"Tournament loaded from {filename}")
              self.update_history_log(f"--- Tournament Loaded from {QFileInfo(filename).fileName()} ---")
              self.setWindowTitle(f"{APP_NAME} - {QFileInfo(filename).fileName()}")

         except FileNotFoundError:
              logging.error(f"Load error: File not found {filename}")
              QtWidgets.QMessageBox.critical(self, "Load Error", f"File not found:\n{filename}")
              self.statusBar().showMessage("Error loading tournament: File not found.")
         except Exception as e:
              logging.exception(f"Error loading tournament from {filename}:")
              QtWidgets.QMessageBox.critical(self, "Load Error", f"Could not load tournament:\n{e}")
              self.statusBar().showMessage("Error loading tournament.")
              self.reset_tournament_state() # Ensure clean state after failed load
         finally:
              self._update_ui_state()

    def print_pairings(self):
        """Print the current round's pairings table in a clean, ink-friendly, professional format (no input widgets)."""
        if self.table_pairings.rowCount() == 0:
            QtWidgets.QMessageBox.information(self, "Print Pairings", "No pairings to print.")
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        preview = QPrintPreviewDialog(printer, self)  # <-- FIXED LINE
        preview.setWindowTitle("Print Preview - Pairings")
        def render_preview(printer_obj):
            doc = QtGui.QTextDocument()
            round_title = self.round_group.title() if hasattr(self, "round_group") else ""
            html = f"""
            <html>
            <head>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        color: #000;
                        background: #fff;
                        margin: 0;
                        padding: 0;
                    }}
                    h2 {{
                        text-align: center;
                        margin: 0 0 0.5em 0;
                        font-size: 1.35em;
                        font-weight: normal;
                        letter-spacing: 0.03em;
                    }}
                    .subtitle {{
                        text-align: center;
                        font-size: 1.05em;
                        margin-bottom: 1.2em;
                    }}
                    table.pairings {{
                        border-collapse: collapse;
                        width: 100%;
                        margin: 0 auto 1.5em auto;
                    }}
                    table.pairings th, table.pairings td {{
                        border: 1px solid #222;
                        padding: 6px 10px;
                        text-align: left;
                        font-size: 11pt;
                        white-space: nowrap;
                    }}
                    table.pairings th {{
                        font-weight: bold;
                        background: none;
                    }}
                    .bye-row td {{
                        font-style: italic;
                        font-weight: bold;
                        text-align: center;
                        border-top: 2px solid #222;
                    }}
                    .footer {{
                        text-align: center;
                        font-size: 9pt;
                        margin-top: 2em;
                        color: #888;
                        letter-spacing: 0.04em;
                    }}
                </style>
            </head>
            <body>
                <h2>Pairings</h2>
                <div class="subtitle">{round_title}</div>
                <table class="pairings">
                    <tr>
                        <th style="width:7%;">Bd</th>
                        <th style="width:46%;">White</th>
                        <th style="width:46%;">Black</th>
                    </tr>
            """
            for row in range(self.table_pairings.rowCount()):
                white_item = self.table_pairings.item(row, 0)
                black_item = self.table_pairings.item(row, 1)
                white = white_item.text() if white_item else ""
                black = black_item.text() if black_item else ""
                html += f"""
                    <tr>
                        <td style="text-align:center;">{row + 1}</td>
                        <td>{white}</td>
                        <td>{black}</td>
                    </tr>
                """
            if self.lbl_bye.isVisible() and self.lbl_bye.text() and self.lbl_bye.text() != "Bye: None":
                html += f"""
                <tr class="bye-row">
                    <td colspan="3">{self.lbl_bye.text()}</td>
                </tr>
                """
            html += f"""
                </table>
                <div class="footer">
                    Printed by Gambit Pairing &mdash; {QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm")}
                </div>
            </body>
            </html>
            """
            doc.setHtml(html)
            doc.print(printer_obj)
        preview.paintRequested.connect(render_preview)
        preview.exec()

    def print_standings(self):
        """Print the current standings table in a clean, ink-friendly, professional format with a polished legend."""
        if self.table_standings.rowCount() == 0:
            QtWidgets.QMessageBox.information(self, "Print Standings", "No standings to print.")
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        preview = QPrintPreviewDialog(printer, self)  # <-- FIXED LINE
        preview.setWindowTitle("Print Preview - Standings")
        def render_preview(printer_obj):
            doc = QtGui.QTextDocument()
            tb_keys = []
            tb_legend = []
            for i, tb_key in enumerate(self.tournament.tiebreak_order):
                short = f"TB{i+1}"
                tb_keys.append(short)
                tb_legend.append((short, TIEBREAK_NAMES.get(tb_key, tb_key.title())))
            html = f"""
            <html>
            <head>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        color: #000;
                        background: #fff;
                        margin: 0;
                        padding: 0;
                    }}
                    h2 {{
                        text-align: center;
                        margin: 0 0 0.5em 0;
                        font-size: 1.35em;
                        font-weight: normal;
                        letter-spacing: 0.03em;
                    }}
                    .subtitle {{
                        text-align: center;
                        font-size: 1.05em;
                        margin-bottom: 1.2em;
                    }}
                    table.standings {{
                        border-collapse: collapse;
                        width: 100%;
                        margin: 0 auto 1.5em auto;
                    }}
                    table.standings th, table.standings td {{
                        border: 1px solid #222;
                        padding: 6px 10px;
                        text-align: center;
                        font-size: 11pt;
                        white-space: nowrap;
                    }}
                    table.standings th {{
                        font-weight: bold;
                        background: none;
                    }}
                    .legend {{
                        width: 100%;
                        margin: 0 auto 1.5em auto;
                        font-size: 10.5pt;
                        color: #222;
                        border: 1px solid #bbb;
                        background: none;
                        padding: 8px 12px;
                        text-align: left;
                    }}
                    .legend-title {{
                        font-weight: bold;
                        font-size: 11pt;
                        margin-bottom: 0.3em;
                        display: block;
                        letter-spacing: 0.02em;
                    }}
                    .legend-table {{
                        border-collapse: collapse;
                        margin-top: 0.2em;
                    }}
                    .legend-table td {{
                        border: none;
                        padding: 2px 10px 2px 0;
                        font-size: 10pt;
                        vertical-align: top;
                    }}
                    .footer {{
                        text-align: center;
                        font-size: 9pt;
                        margin-top: 2em;
                        color: #888;
                        letter-spacing: 0.04em;
                    }}
                </style>
            </head>
            <body>
                <h2>Standings</h2>
                <div class="subtitle">{self.round_group.title() if hasattr(self, "round_group") else ""}</div>
                <div class="legend">
                    <span class="legend-title">Tiebreaker Legend</span>
                    <table class="legend-table">
            """
            for short, name in tb_legend:
                html += f"<tr><td><b>{short}</b></td><td>{name}</td></tr>"
            html += """
                    </table>
                </div>
                <table class="standings">
                    <tr>
                        <th style="width:6%;">#</th>
                        <th style="width:32%;">Player</th>
                        <th style="width:10%;">Score</th>
            """
            for short in tb_keys:
                html += f'<th style="width:7%;">{short}</th>'
            html += "</tr>"
            # --- Table Rows ---
            for row in range(self.table_standings.rowCount()):
                html += "<tr>"
                for col in range(self.table_standings.columnCount()):
                    item = self.table_standings.item(row, col)
                    cell = item.text() if item else ""
                    # Rank and Score columns bold
                    if col == 0 or col == 2:
                        html += f'<td style="font-weight:bold;">{cell}</td>'
                    else:
                        html += f"<td>{cell}</td>"
                html += "</tr>"
            html += f"""
                </table>
                <div class="footer">
                    Printed by Gambit Pairing &mdash; {QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm")}
                </div>
            </body>
            </html>
            """
            doc.setHtml(html)
            doc.print(printer_obj)
        preview.paintRequested.connect(render_preview)
        preview.exec()
    def check_save_before_proceeding(self) -> bool:
         if not self._dirty or not self.tournament:
              return True 

         reply = QtWidgets.QMessageBox.question(self, 'Unsaved Changes',
              "The current tournament has unsaved changes. Save before proceeding?",
              QtWidgets.QMessageBox.StandardButton.Save |
              QtWidgets.QMessageBox.StandardButton.Discard |
              QtWidgets.QMessageBox.StandardButton.Cancel,
              QtWidgets.QMessageBox.StandardButton.Cancel) 

         if reply == QtWidgets.QMessageBox.StandardButton.Save:
              self.save_tournament()
              return not self._dirty # Proceed only if save was successful and marked clean
         elif reply == QtWidgets.QMessageBox.StandardButton.Discard:
              return True 
         else: # Cancel
              return False 


    def show_about_dialog(self):
         QtWidgets.QMessageBox.about(self, f"About {APP_NAME}",
              f"<h2>{APP_NAME}</h2>"
              f"<p>Version: {APP_VERSION}</p>"
              "<p>A simple Swiss pairing application using PyQt6.</p>"
              "<p>Implements Dutch System pairings with FIDE/USCF style considerations for color and byes.</p>"
              "<p><a href='https://discord.gg/eEnnetMDfr'>Join our Discord</a></p>")


    def closeEvent(self, event: QCloseEvent):
        if self.check_save_before_proceeding():
            logging.info(f"{APP_NAME} closing.")
            event.accept()
        else:
            event.ignore()


# --- Main Execution ---
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    try: 
        # Try to apply a modern style if available
        available_styles = QtWidgets.QStyleFactory.keys()
        if "Fusion" in available_styles:
            app.setStyle("Fusion")
        elif "WindowsVista" in available_styles and sys.platform == "win32": # Windows specific
            app.setStyle("WindowsVista")
        # Add other preferred styles if needed
    except Exception as e: 
        logging.warning(f"Could not set preferred application style: {e}")

    window = SwissTournamentApp()
    window.show()
    sys.exit(app.exec())