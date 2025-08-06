"""Types used in Gambit Pairing"""

from typing import List, Tuple, Optional, Set, Dict, Any
from gambitpairing.core.player import Player

RoundSchedule = Tuple[MatchPairing, ...]  # All pairings for one round
MatchPairing = Tuple[int, int]  # Tuple of player indices
Pairings = Tuple[List[Tuple[Player, Player]], Optional[Player]]
MaybePlayer = Optional[Player]
Players = List[Player]

#  LocalWords:  MatchPairing RoundSchedule
