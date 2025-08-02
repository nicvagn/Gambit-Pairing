"""Types used in Gambit Pairing"""

from typing import List, Tuple, Optional, Set, Dict, Any
from gambitpairing.core.player import Player

type Pairings = List[Tuple[Player, Player]]
type MaybePlayers = Optional[Player]
type Players = List[Players]
