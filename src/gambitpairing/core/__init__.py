"""Types used in Gambit Pairing"""

from typing import List, Tuple, Optional, Set, Dict, Any
from gambitpairing.core.player import Player

type Pairings = Tuple[List[Tuple[Player, Player]], Optional[Player]]
type MaybePlayer = Optional[Player]
type Players = List[Players]
