"""A FIDE chess player."""

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
from typing import Any, Dict, List, Optional, Tuple

from gambitpairing.core.constants import B, W
from gambitpairing.core.players.base_player import BasePlayer
from gambitpairing.core.utils import generate_id, setup_logger

logger = setup_logger(__name__)


class FidePlayer(BasePlayer):
    """Represents A FIDE a player in the tournament."""

    def __init__(
        self,
        name: str,
        rating: Optional[int] = None,
        player_id: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        club: Optional[str] = None,
        federation: Optional[str] = None,
        gender: Optional[str] = None,
        dob: Optional[str] = None,
        fide_id: Optional[int] = None,
        fide_title: Optional[str] = None,
        fide_standard: Optional[int] = None,
        fide_rapid: Optional[int] = None,
        fide_blitz: Optional[int] = None,
        birth_year: Optional[int] = None,
    ) -> None:
        super().__init__(
            name=name,
            player_id=player_id,
            phone=phone,
            email=email,
            club=club,
            federation=federation,
            gender=gender,
            dob=dob,
        )
        # FIDE Related data
        self.fide_id: Optional[int] = fide_id
        self.fide_title: Optional[str] = fide_title
        self.fide_standard: Optional[int] = fide_standard
        self.fide_rapid: Optional[int] = fide_rapid
        self.fide_blitz: Optional[int] = fide_blitz
        self.birth_year: Optional[int] = birth_year
        self.score: float = 0.0
        self.is_active: bool = True  # Used for withdrawals

    @classmethod
    def from_dict(cls, player_data: Dict[str, Any]) -> cls:
        """Create a python Player instance from serialized data.

        Parameters
        ----------
        player_data : Dict[str, Any]

        Returns
        -------
        FidePlayer
            A Fide chess player from the given data
        """
        # Handle backward compatibility for sex/gender field consolidation
        gender = player_data.get("gender") or player_data.get("sex")

        player = cls(
            name=player_data["name"],
            rating=player_data.get("rating", 1000),
            player_id=player_data["id"],
            phone=player_data.get("phone"),
            email=player_data.get("email"),
            club=player_data.get("club"),
            federation=player_data.get("federation"),
            gender=gender,
            dob=player_data.get("dob"),
            fide_id=player_data.get("fide_id"),
            fide_title=player_data.get("fide_title"),
            fide_standard=player_data.get("fide_standard"),
            fide_rapid=player_data.get("fide_rapid"),
            fide_blitz=player_data.get("fide_blitz"),
            birth_year=player_data.get("birth_year"),
        )
        for key, value in player_data.items():
            if hasattr(player, key) and not key.startswith("_"):
                setattr(player, key, value)
        # Ensure essential lists exist if loading older format without them
        for list_attr in [
            "color_history",
            "opponent_ids",
            "results",
            "running_scores",
            "float_history",
        ]:
            if not hasattr(player, list_attr) or getattr(player, list_attr) is None:
                setattr(player, list_attr, [])
        if not hasattr(player, "has_received_bye"):  # For older save files
            player.has_received_bye = (
                (None in player.opponent_ids) if player.opponent_ids else False
            )
        if not hasattr(player, "num_black_games"):  # For older save files
            player.num_black_games = (
                player.color_history.count(B) if player.color_history else 0
            )

        return player


#  LocalWords:  FidePlayer
