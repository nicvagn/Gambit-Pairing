"""A base chess player in a tournament. This is a base class."""

# Gambit Pairing
# Copyright (C) 2025  Gambit Pairing developers
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import logging
import re
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from gambitpairing.core.club import Club
from gambitpairing.core.constants import B, W
from gambitpairing.core.utils import generate_id, setup_logger

logger = setup_logger(__name__)


class Player:
    """Represents a player in the tournament."""

    Player.email_regex = re.compile(
        r"([-!#-'*+/-9=?A-Z^-~]+(\.[-!#-'*+/-9=?A-Z^-~]+)*|\"([]!#-[^-~ \t]|(\\[\t -~]))+\")@([-!#-'*+/-9=?A-Z^-~]+(\.[-!#-'*+/-9=?A-Z^-~]+)*|\[[\t -Z^-~]*])"
    )
    Player.phone_regex = re.compile(
        r"^[+]{1}(?:[0-9\\-\\(\\)\\/\\.]\\s?){6,15}[0-9]{1}$"
    )

    def __init__(
        self,
        name: str,
        player_id: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        club: Optional[Club] = None,
        federation: Optional[str] = None,
        gender: Optional[str] = None,
        dob: Optional[str] = None,
    ) -> None:
        self.id: str = player_id or generate_id("player_")
        self.name: str = name

        if Player.phone_regex.match(email):
            self.phone = phone
        else:
            raise RuntimeWarning(
                "The phone number: %s is not valid, phone not set for Player with id: %s",
                phone,
                self.id,
            )

        if Player.email_regex.match(email):
            self.email = email
        else:
            raise RuntimeWarning(
                "The email: %s is not valid. email not set for Player with id: %s",
                email,
                self.id,
            )
        self.club: Optional[Club] = club
        self.gender: Optional[str] = gender
        self.dob: Optional[str] = dob

        # History
        self.color_history: List[Optional[str]] = []  # Stores W, B, or None (for bye)
        self.opponent_ids: List[Optional[str]] = []
        self.results: List[Optional[float]] = []
        self.running_scores: List[float] = []
        self.has_received_bye: bool = False
        self.num_black_games: int = 0  # Counts actual games played as Black
        self.float_history: List[int] = []  # Track rounds where player floated down
        self.match_history: List[Optional[Dict[str, Any]]] = (
            []
        )  # Stores {'opponent_id': str, 'opponent_score': float}

        # Tiebreakers (calculated)
        self.tiebreakers: Dict[str, float] = {}

        # Runtime cache
        self._opponents_played_cache: List[Optional["Player"]] = []

    def __repr__(self) -> str:
        """Representation of Player."""
        status = "" if self.is_active else " (Inactive)"
        return f"{self.name} ({self.rating}){status}"

    @property
    def age(self) -> Optional[date]:
        """Calculate age from birth year or date of birth.

        Returns
        -------
        int : Optional[int]
            The players age, if known
        """
        # Try to calculate from birth year first
        if self.birth_year:
            current_year = date.today().year
            return current_year - self.birth_year

        # Try to calculate from date of birth
        if self.dob:
            try:
                if isinstance(self.dob, str):
                    # Parse various date formats
                    if "-" in self.dob:  # YYYY-MM-DD format
                        birth_date = date.fromisoformat(self.dob)
                    else:  # Try other formats if needed
                        return None
                else:
                    return None

                today = date.today()
                age = today.year - birth_date.year
                # Adjust if birthday hasn't occurred this year
                if today.month < birth_date.month or (
                    today.month == birth_date.month and today.day < birth_date.day
                ):
                    age -= 1
                return age
            except (ValueError, AttributeError):
                return None

        return None

    @property
    def date_of_birth(self) -> Optional[datetime.date]:
        """Return the date of birth, maintaining compatibility.

        Returns
        -------
        datetime.date
            The date of the players birth
        """
        return self.dob

    @date_of_birth.setter
    def date_of_birth(self, value: Optional[str]) -> None:
        """Set the date of birth, maintaining compatibility."""
        self.dob = value

    def get_opponent_objects(
        self, players_dict: Dict[str, "Player"]
    ) -> List[Optional["Player"]]:
        """Resolve opponent ID's to Player objects using the provided dictionary.

        Parameters
        ----------
        player_dict : Dict[str, "Player"]

        Returns
        -------
        List of your opponents
        """
        if len(self._opponents_played_cache) != len(self.opponent_ids):
            self._opponents_played_cache = [
                players_dict.get(opp_id) if opp_id else None
                for opp_id in self.opponent_ids
            ]
        return self._opponents_played_cache

    def get_last_two_colors(self) -> Tuple[Optional[str], Optional[str]]:
        """Return the colors of the last two non-bye games played."""
        valid_colors = [c for c in self.color_history if c is not None]
        if len(valid_colors) >= 2:
            return valid_colors[-1], valid_colors[-2]
        elif len(valid_colors) == 1:
            return valid_colors[-1], None
        else:
            return None, None

    def get_color_preference(self) -> Optional[str]:
        """Determine color preference based on FIDE/USCF rules.

        Notes
        -----
        1. Absolute: If last two played games had same color, must get the other.
        2. Preference: If colors are unbalanced, prefer the color that moves towards balance.

        Returns
        -------
        string
            "White", "Black", or None if no preference or perfectly balanced.
        """
        valid_played_colors = [c for c in self.color_history if c is not None]

        if len(valid_played_colors) >= 2:
            last_color = valid_played_colors[-1]
            second_last_color = valid_played_colors[-2]
            if last_color == second_last_color:
                return B if last_color == B else W

        white_games_played = valid_played_colors.count(W)
        black_games_played = valid_played_colors.count(B)

        if white_games_played > black_games_played:
            return B
        elif black_games_played > white_games_played:
            return W

        return None

    def add_round_result(
        self, opponent: Optional["Player"], result: float, color: Optional[str]
    ) -> None:
        """Record the outcome of a round for the player."""
        opponent_id = opponent.id if opponent else None
        self.opponent_ids.append(opponent_id)
        self.results.append(result)

        # Record match details for both players before updating scores
        player_score_before_round = self.score
        opponent_score_before_round = opponent.score if opponent else 0.0

        self.match_history.append(
            {
                "opponent_id": opponent_id,
                "player_score": player_score_before_round,
                "opponent_score": opponent_score_before_round,
            }
        )
        if opponent:
            opponent.match_history.append(
                {
                    "opponent_id": self.id,
                    "player_score": opponent_score_before_round,
                    "opponent_score": player_score_before_round,
                }
            )

        self.score += result
        self.running_scores.append(self.score)
        self.color_history.append(color)  # color can be None for a bye
        if color == B:
            self.num_black_games += 1
        if opponent is None:  # This means it was a bye
            self.has_received_bye = True
            logging.debug(f"Player {self.name} marked as having received a bye.")
        self._opponents_played_cache = []  # Invalidate cache

    def to_dict(self) -> Dict[str, Any]:
        """Serialize player data."""
        data = {k: v for k, v in self.__dict__.items() if not k.startswith("_")}
        return data

    @abstractmethod
    @classmethod
    def from_dict(cls, player_data: Dict[str, Any]) -> "Player":
        """Create a python Player instance from serialized data.

        Parameters
        ----------
        player-data : Dict[str, Any]
            the player data used to construct the Chess Player
        """
        pass
