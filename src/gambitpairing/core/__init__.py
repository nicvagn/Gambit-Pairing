"""Types used in Gambit Pairing."""

from typing import List, Literal, Optional, Tuple

from gambitpairing.core.club import Club

# chess colours XD
W = Literal["White"]
B = Literal["Black"]
Colour = Literal[W, B]
MatchPairing = Tuple[int, int]  # Tuple of player indices
RoundSchedule = Tuple[MatchPairing, ...]  # All pairings for one round
Pairings = Tuple[List[Tuple["Player", "Player"]], Optional["Player"]]
MaybePlayer = Optional["Player"]
Players = List["Player"]
#  LocalWords:  MatchPairing RoundSchedule
