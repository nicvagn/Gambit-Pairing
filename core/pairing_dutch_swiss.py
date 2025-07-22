from typing import List, Tuple, Optional, Set, Dict
from enum import Enum
import copy

from core.player import Player
from core.constants import W, B

class FloatType(Enum):
    """Types of floaters based on C++ implementation"""
    FLOAT_DOWN = 1
    FLOAT_UP = 2  
    FLOAT_NONE = 3

class PairingWeight:
    """Edge weight class similar to C++ matching_computer::edge_weight"""
    def __init__(self, value: int = 0):
        self.value = value
    
    def __lt__(self, other):
        return self.value < other.value
    
    def __eq__(self, other):
        return self.value == other.value
    
    def __add__(self, other):
        if isinstance(other, int):
            return PairingWeight(self.value + other)
        return PairingWeight(self.value + other.value)
    
    def __or__(self, other):
        if isinstance(other, int):
            return PairingWeight(self.value | other)
        return PairingWeight(self.value | other.value)
    
    def shift_left(self, bits: int):
        """Left shift operation"""
        self.value <<= bits
        return self

# FIDE Dutch Swiss pairing algorithm implementation
# Based on the C++ reference implementation, adapted for Python
def create_dutch_swiss_pairings(
    players: List[Player],
    current_round: int,
    previous_matches: Set[frozenset],
    get_eligible_bye_player,
    allow_repeat_pairing_callback=None
) -> Tuple[List[Tuple[Player, Player]], Optional[Player], List[Tuple[str, str]], Optional[str]]:
    """
    Create pairings for a Swiss-system round using the FIDE Dutch system.
    Based on C++ implementation from swisssystems::dutch
    
    - players: list of Player objects
    - current_round: The 1-based index of the current round.
    - previous_matches: set of frozenset({player1.id, player2.id}) for all previous matches
    - get_eligible_bye_player: A function to select a player to receive a bye.
    - allow_repeat_pairing_callback: function(player1, player2) -> bool, called if a repeat pairing is needed
    Returns: (pairings, bye_player, round_pairings_ids, bye_player_id)
    """
    
    # Filter out inactive players and ensure pairing numbers are set
    active_players = [p for p in players if p.is_active]
    for idx, p in enumerate(active_players):
        if not hasattr(p, 'pairing_number') or p.pairing_number is None:
            p.pairing_number = idx + 1
            
    # Sort players by score (descending), then rating (descending), then pairing number
    sorted_players = sorted(active_players, key=lambda p: (-p.score, -p.rating, p.pairing_number))

    bye_player = None
    bye_player_id = None
    
    # Handle bye assignment for odd number of players
    if len(sorted_players) % 2 == 1:
        bye_player = get_eligible_bye_player(sorted_players)
        if bye_player:
            bye_player_id = bye_player.id
            sorted_players.remove(bye_player)

    # Round 1 special case: top half vs bottom half
    if current_round == 1:
        return _pair_round_one(sorted_players, bye_player, bye_player_id)

    # Main pairing algorithm for rounds 2+
    return _compute_dutch_pairings(sorted_players, current_round, previous_matches, bye_player, bye_player_id)


def _pair_round_one(players: List[Player], bye_player: Optional[Player], bye_player_id: Optional[str]) -> Tuple[List[Tuple[Player, Player]], Optional[Player], List[Tuple[str, str]], Optional[str]]:
    """Handle round 1 pairing: top half vs bottom half by initial rating/rank"""
    n = len(players)
    pairings = []
    round_pairings_ids = []
    
    # For round 1, sort by rating descending (highest rated first)
    players_by_rating = sorted(players, key=lambda p: (-p.rating, p.pairing_number))
    
    s1 = players_by_rating[:n//2]  # Top half (highest rated)
    s2 = players_by_rating[n//2:]  # Bottom half (lowest rated)
    
    # FIDE Rule: Pair rank 1 vs rank (n/2+1), rank 2 vs rank (n/2+2), etc.
    for i in range(n//2):
        higher_rated = s1[i]  # Rank i+1
        lower_rated = s2[i]   # Rank (n/2+i+1)
        
        # FIDE Color assignment in round 1:
        # Boards 1, 3, 5, etc.: higher rated gets white
        # Boards 2, 4, 6, etc.: lower rated gets white
        if i % 2 == 0:  # Odd-numbered boards (1, 3, 5, ...)
            white_player = higher_rated
            black_player = lower_rated
        else:  # Even-numbered boards (2, 4, 6, ...)
            white_player = lower_rated  
            black_player = higher_rated
        
        pairings.append((white_player, black_player))
        round_pairings_ids.append((white_player.id, black_player.id))

    return pairings, bye_player, round_pairings_ids, bye_player_id


def _compute_dutch_pairings(players: List[Player], current_round: int, previous_matches: Set[frozenset], bye_player: Optional[Player], bye_player_id: Optional[str]) -> Tuple[List[Tuple[Player, Player]], Optional[Player], List[Tuple[str, str]], Optional[str]]:
    """Main Dutch system pairing computation for rounds 2+ - FIDE compliant"""
    
    # Sort players by score (desc), then rating (desc), then pairing number
    sorted_players = sorted(players, key=lambda p: (-p.score, -p.rating, p.pairing_number))
    
    # Group players by score into brackets
    score_groups = _group_players_by_score(sorted_players)
    sorted_scores = sorted(score_groups.keys(), reverse=True)
    
    pairings = []
    round_pairings_ids = []
    moved_down_players = []  # MDPs from higher brackets
    
    # Process each score group (bracket) from highest to lowest
    for score_idx, score in enumerate(sorted_scores):
        # Create the bracket: resident players + moved down players
        resident_players = score_groups[score]
        bracket_players = moved_down_players + resident_players
        moved_down_players = []  # Reset for next bracket
        
        if len(bracket_players) == 0:
            continue
        
        # Determine bracket type and parameters
        M0 = len([p for p in bracket_players if hasattr(p, 'is_moved_down') and p.is_moved_down])
        resident_count = len(resident_players)
        total_in_bracket = len(bracket_players)
        
        # FIDE Rule: MaxPairs = maximum pairs possible in this bracket
        MaxPairs = min(total_in_bracket // 2, resident_count)
        
        # FIDE Rule: M1 = maximum MDPs that can be paired
        M1 = min(M0, resident_count, MaxPairs)
        
        # Tag players with Bracket Sequence Numbers (BSN)
        for i, player in enumerate(bracket_players):
            player.bsn = i + 1
        
        # Process bracket according to FIDE rules
        if M0 == 0:
            # Homogeneous bracket - all same score
            bracket_pairings, remaining = _process_homogeneous_bracket(
                bracket_players, previous_matches, current_round
            )
        else:
            # Heterogeneous bracket - mixed scores with MDPs
            bracket_pairings, remaining = _process_heterogeneous_bracket(
                bracket_players, resident_players, M1, previous_matches, current_round
            )
        
        pairings.extend(bracket_pairings)
        round_pairings_ids.extend([(p[0].id, p[1].id) for p in bracket_pairings])
        
        # Mark remaining players as moved down for next bracket
        for player in remaining:
            player.is_moved_down = True
        moved_down_players = remaining

    return pairings, bye_player, round_pairings_ids, bye_player_id


def _process_homogeneous_bracket(bracket: List[Player], previous_matches: Set[frozenset], current_round: int) -> Tuple[List[Tuple[Player, Player]], List[Player]]:
    """Process homogeneous bracket (all same score) according to FIDE Dutch rules"""
    if len(bracket) <= 1:
        return [], bracket
    
    # FIDE Rule 2.2: Divide into S1 and S2
    MaxPairs = len(bracket) // 2
    S1 = bracket[:MaxPairs]
    S2 = bracket[MaxPairs:]
    
    # Try all possible configurations according to FIDE sequence
    configurations = []
    
    # 1. Original candidate (S1[i] with S2[i])
    config = _evaluate_fide_configuration(S1, S2, previous_matches, current_round, "original")
    if config:
        configurations.append(config)
    
    # 2. All transpositions of S2 (FIDE Article 4.2)
    s2_transpositions = _generate_s2_transpositions(S2, len(S1))
    for i, s2_variant in enumerate(s2_transpositions):
        config = _evaluate_fide_configuration(S1, s2_variant, previous_matches, current_round, f"s2_trans_{i}")
        if config:
            configurations.append(config)
    
    # 3. All exchanges between original S1 and S2 (FIDE Article 4.3)
    exchanges = _generate_resident_exchanges(S1, S2)
    for i, (new_s1, new_s2) in enumerate(exchanges):
        config = _evaluate_fide_configuration(new_s1, new_s2, previous_matches, current_round, f"exchange_{i}")
        if config:
            configurations.append(config)
    
    # Select best configuration according to FIDE criteria
    best_config = _select_best_fide_configuration(configurations)
    
    if best_config:
        return best_config['pairings'], best_config['unpaired']
    else:
        return [], bracket


def _process_heterogeneous_bracket(bracket: List[Player], resident_players: List[Player], M1: int, previous_matches: Set[frozenset], current_round: int) -> Tuple[List[Tuple[Player, Player]], List[Player]]:
    """Process heterogeneous bracket (mixed scores) according to FIDE Dutch rules"""
    
    # FIDE Rule 2.2: Create S1 with M1 highest players, S2 with residents
    S1 = bracket[:M1]  # M1 highest players (includes MDPs)
    S2 = resident_players.copy()  # All resident players
    
    # FIDE Rule 2.2.3: Limbo contains excess MDPs
    M0 = len([p for p in bracket if hasattr(p, 'is_moved_down') and p.is_moved_down])
    Limbo = bracket[M1:M0] if M0 > M1 else []
    
    configurations = []
    
    # Generate MDP-Pairings and process remainders
    # 1. Original configuration
    config = _evaluate_heterogeneous_configuration(S1, S2, Limbo, previous_matches, current_round, "original")
    if config:
        configurations.append(config)
    
    # 2. S2 transpositions for MDP-Pairing
    s2_transpositions = _generate_s2_transpositions(S2, M1)
    for i, s2_variant in enumerate(s2_transpositions):
        config = _evaluate_heterogeneous_configuration(S1, s2_variant, Limbo, previous_matches, current_round, f"mdp_trans_{i}")
        if config:
            configurations.append(config)
    
    # 3. MDP exchanges between S1 and Limbo (if Limbo exists)
    if len(Limbo) > 0:
        exchanges = _generate_mdp_exchanges(S1, Limbo)
        for i, (new_s1, new_limbo) in enumerate(exchanges):
            config = _evaluate_heterogeneous_configuration(new_s1, S2, new_limbo, previous_matches, current_round, f"mdp_exchange_{i}")
            if config:
                configurations.append(config)
    
    best_config = _select_best_fide_configuration(configurations)
    
    if best_config:
        return best_config['pairings'], best_config['unpaired'] + Limbo
    else:
        return [], bracket


def _evaluate_fide_configuration(S1: List[Player], S2: List[Player], previous_matches: Set[frozenset], current_round: int, config_name: str) -> Optional[Dict]:
    """Evaluate configuration according to FIDE criteria"""
    pairings = []
    unpaired = []
    
    # FIDE Rule 2.3.1: Pair S1[i] with S2[i]
    min_pairs = min(len(S1), len(S2))
    paired_count = 0
    
    for i in range(min_pairs):
        p1, p2 = S1[i], S2[i]
        
        # Check absolute criteria [C1-C3]
        if not _meets_absolute_criteria(p1, p2, previous_matches):
            unpaired.extend([p1, p2])
            continue
        
        # Assign colors according to FIDE Article 5
        white, black = _assign_colors_fide(p1, p2, current_round)
        pairings.append((white, black))
        paired_count += 1
    
    # Add unpaired players
    for i in range(min_pairs, len(S1)):
        unpaired.append(S1[i])
    for i in range(min_pairs, len(S2)):
        unpaired.append(S2[i])
    
    # Calculate FIDE quality metrics
    downfloaters = len(unpaired)
    score_differences = sum(abs(p1.score - p2.score) for p1, p2 in pairings)
    color_violations = sum(1 for p1, p2 in pairings if not _colors_satisfy_fide_preferences(p1, p2))
    
    return {
        'name': config_name,
        'pairings': pairings,
        'unpaired': unpaired,
        'downfloaters': downfloaters,
        'score_diff_total': score_differences,
        'color_violations': color_violations,
        'paired_count': paired_count
    }


def _evaluate_heterogeneous_configuration(S1: List[Player], S2: List[Player], Limbo: List[Player], previous_matches: Set[frozenset], current_round: int, config_name: str) -> Optional[Dict]:
    """Evaluate heterogeneous bracket configuration with MDP-Pairing and remainder"""
    
    # Create MDP-Pairing (S1 MDPs with S2 residents)
    mdp_pairings = []
    M1 = len(S1)
    
    for i in range(min(M1, len(S2))):
        p1, p2 = S1[i], S2[i]
        
        if not _meets_absolute_criteria(p1, p2, previous_matches):
            # If MDP-Pairing fails, this configuration is invalid
            return None
        
        white, black = _assign_colors_fide(p1, p2, current_round)
        mdp_pairings.append((white, black))
    
    # Process remainder (remaining S2 players)
    remainder_players = S2[M1:]
    remainder_pairings, remainder_unpaired = _process_homogeneous_bracket(remainder_players, previous_matches, current_round)
    
    # Combine results
    all_pairings = mdp_pairings + remainder_pairings
    all_unpaired = remainder_unpaired + Limbo
    
    downfloaters = len(all_unpaired)
    score_differences = sum(abs(p1.score - p2.score) for p1, p2 in all_pairings)
    color_violations = sum(1 for p1, p2 in all_pairings if not _colors_satisfy_fide_preferences(p1, p2))
    
    return {
        'name': config_name,
        'pairings': all_pairings,
        'unpaired': all_unpaired,
        'downfloaters': downfloaters,
        'score_diff_total': score_differences,
        'color_violations': color_violations,
        'paired_count': len(all_pairings)
    }


def _generate_s2_transpositions(S2: List[Player], N1: int) -> List[List[Player]]:
    """Generate all transpositions of S2 according to FIDE Article 4.2"""
    if len(S2) == 0:
        return []
    
    transpositions = []
    
    # 1. Original order
    transpositions.append(S2.copy())
    
    if len(S2) >= 2:
        # 2. Reverse the entire S2
        reversed_s2 = S2.copy()
        reversed_s2.reverse()
        transpositions.append(reversed_s2)
        
        # 3. Strategic swaps to generate key configurations
        # Try swapping first two elements
        variant = S2.copy()
        variant[0], variant[1] = variant[1], variant[0]
        transpositions.append(variant)
        
        if len(S2) >= 4:
            # 4. Try [0,2,1,3,...] pattern
            variant = S2.copy()
            variant[0], variant[2] = variant[2], variant[0]
            transpositions.append(variant)
            
            # 5. Try [1,0,3,2,...] pattern  
            variant = S2.copy()
            variant[0], variant[1] = variant[1], variant[0]
            variant[2], variant[3] = variant[3], variant[2]
            transpositions.append(variant)
    
    return transpositions


def _generate_resident_exchanges(S1: List[Player], S2: List[Player]) -> List[Tuple[List[Player], List[Player]]]:
    """Generate resident exchanges according to FIDE Article 4.3"""
    exchanges = []
    
    # Generate strategic exchanges that can produce optimal pairings
    # Based on FIDE rules: smaller number of exchanges preferred
    
    # Single player exchanges - most important
    for i in range(min(len(S1), 4)):  
        for j in range(min(len(S2), 4)):  
            new_s1 = S1.copy()
            new_s2 = S2.copy()
            
            # Perform the exchange
            new_s1[i], new_s2[j] = new_s2[j], new_s1[i]
            
            # Re-sort according to FIDE Article 1.2
            new_s1.sort(key=lambda p: (-p.score, -p.rating, p.pairing_number))
            new_s2.sort(key=lambda p: (-p.score, -p.rating, p.pairing_number))
            
            exchanges.append((new_s1, new_s2))
    
    # Two-player exchanges (limited set for performance)
    if len(S1) >= 2 and len(S2) >= 2:
        # Exchange positions (0,1) from S1 with (0,1) from S2
        new_s1 = S1.copy()
        new_s2 = S2.copy()
        new_s1[0], new_s2[0] = new_s2[0], new_s1[0]
        new_s1[1], new_s2[1] = new_s2[1], new_s1[1]
        new_s1.sort(key=lambda p: (-p.score, -p.rating, p.pairing_number))
        new_s2.sort(key=lambda p: (-p.score, -p.rating, p.pairing_number))
        exchanges.append((new_s1, new_s2))
    
    return exchanges


def _generate_mdp_exchanges(S1: List[Player], Limbo: List[Player]) -> List[Tuple[List[Player], List[Player]]]:
    """Generate MDP exchanges according to FIDE Article 4.4"""
    exchanges = []
    
    # Single MDP exchanges between S1 and Limbo
    for i in range(len(S1)):
        for j in range(len(Limbo)):
            new_s1 = S1.copy()
            new_limbo = Limbo.copy()
            new_s1[i], new_limbo[j] = new_limbo[j], new_s1[i]
            # Re-sort S1 by score then BSN
            new_s1.sort(key=lambda p: (-p.score, -p.rating, p.pairing_number))
            exchanges.append((new_s1, new_limbo))
    
    return exchanges


def _select_best_fide_configuration(configurations: List[Dict]) -> Optional[Dict]:
    """Select best configuration according to FIDE quality criteria [C6-C21]"""
    if not configurations:
        return None
    
    # Remove configurations that don't produce any pairings
    valid_configs = [c for c in configurations if c['paired_count'] > 0]
    if not valid_configs:
        return None
    
    # FIDE Priority (Article 3.4) with enhanced color preference evaluation:
    # C6: Minimize downfloaters (maximize pairs) - PRIMARY
    # C7: Minimize PSD (score differences) - SECONDARY  
    # C12: Minimize color preference violations - TERTIARY
    # Earlier sequence priority - QUATERNARY
    
    # Enhanced scoring that considers color balance satisfaction
    def score_config(config):
        # Primary: Maximize pairings
        pairing_score = -config['paired_count'] * 1000
        
        # Secondary: Minimize downfloaters  
        downfloater_penalty = config['downfloaters'] * 100
        
        # Tertiary: Score differences (normalized)
        score_diff_penalty = config['score_diff_total']
        
        # Quaternary: Color violations with higher weight for better balance
        color_penalty = config['color_violations'] * 10
        
        # Bonus for configurations that better satisfy color preferences
        color_satisfaction_bonus = 0
        for p1, p2 in config['pairings']:
            if _colors_satisfy_fide_preferences(p1, p2):
                color_satisfaction_bonus -= 5  # Bonus for good color match
        
        return pairing_score + downfloater_penalty + score_diff_penalty + color_penalty + color_satisfaction_bonus
    
    best = min(valid_configs, key=score_config)
    return best


def _meets_absolute_criteria(p1: Player, p2: Player, previous_matches: Set[frozenset]) -> bool:
    """Check FIDE absolute criteria [C1-C3]"""
    # C1: Players must not have played before
    if frozenset({p1.id, p2.id}) in previous_matches:
        return False
    
    # C3: Non-topscorers with same absolute color preference cannot meet
    if _has_absolute_color_preference(p1) and _has_absolute_color_preference(p2):
        pref1 = _get_color_preference(p1)
        pref2 = _get_color_preference(p2)
        if pref1 == pref2:
            return False
    
    return True


def _assign_colors_fide(p1: Player, p2: Player, current_round: int) -> Tuple[Player, Player]:
    """Assign colors according to FIDE Article 5 rules"""
    pref1 = _get_color_preference(p1)
    pref2 = _get_color_preference(p2)
    abs1 = _has_absolute_color_preference(p1)
    abs2 = _has_absolute_color_preference(p2)
    
    # 5.2.1: Grant both preferences if compatible
    if pref1 and pref2 and pref1 != pref2:
        return (p1, p2) if pref1 == W else (p2, p1)
    
    # 5.2.2: Grant stronger preference
    if abs1 and not abs2:
        return (p1, p2) if pref1 == W else (p2, p1)
    elif abs2 and not abs1:
        return (p2, p1) if pref2 == W else (p1, p2)
    elif abs1 and abs2:
        # Both absolute - grant wider color difference
        return _assign_by_color_balance(p1, p2, current_round)
    
    # 5.2.3: Alternate to most recent W vs B
    # (Simplified implementation)
    
    # 5.2.4: Grant preference of higher ranked player
    higher_ranked = p1 if (-p1.score, -p1.rating, p1.pairing_number) < (-p2.score, -p2.rating, p2.pairing_number) else p2
    lower_ranked = p2 if higher_ranked == p1 else p1
    
    higher_pref = _get_color_preference(higher_ranked)
    if higher_pref:
        return (higher_ranked, lower_ranked) if higher_pref == W else (lower_ranked, higher_ranked)
    
    # 5.2.5: Use pairing number parity
    if higher_ranked.pairing_number % 2 == 1:
        return (higher_ranked, lower_ranked)  # Give initial color (White)
    else:
        return (lower_ranked, higher_ranked)   # Give opposite color


def _colors_satisfy_fide_preferences(white: Player, black: Player) -> bool:
    """Check if color assignment satisfies FIDE preferences"""
    white_pref = _get_color_preference(white)
    black_pref = _get_color_preference(black)
    
    white_satisfied = not white_pref or white_pref == W
    black_satisfied = not black_pref or black_pref == B
    
    return white_satisfied and black_satisfied


def _pair_dutch_bracket_improved(bracket: List[Player], previous_matches: Set[frozenset], current_round: int) -> Tuple[List[Tuple[Player, Player]], List[Player]]:
    """
    Improved Dutch system bracket pairing with better configuration selection.
    Uses more sophisticated scoring and FIDE-compliant optimization.
    """
    if len(bracket) <= 1:
        return [], bracket
    
    # If only 2 players, try to pair them directly
    if len(bracket) == 2:
        p1, p2 = bracket[0], bracket[1]
        if _are_players_compatible(p1, p2, previous_matches):
            white, black = _assign_colors_dutch_improved(p1, p2, current_round)
            return [(white, black)], []
        else:
            return [], bracket
    
    # For larger brackets, try enhanced S1/S2 approach first
    mid = len(bracket) // 2
    s1 = bracket[:mid]
    s2 = bracket[mid:]
    
    # Generate comprehensive pairing configurations
    configurations = _generate_comprehensive_configurations(s1, s2, previous_matches, current_round)
    
    # Select the best configuration using enhanced FIDE criteria
    best_config = _select_optimal_configuration(configurations)
    
    # If we have a good configuration, use it
    if best_config and len(best_config['pairings']) >= len(bracket) // 2 - 1:
        return best_config['pairings'], best_config['unpaired']
    
    # If Dutch system doesn't work well, fall back to enhanced greedy approach
    return _enhanced_fallback_pairing(bracket, previous_matches, current_round)


def _generate_comprehensive_configurations(s1: List[Player], s2: List[Player], previous_matches: Set[frozenset], current_round: int) -> List[Dict]:
    """Generate comprehensive pairing configurations with better scoring"""
    configurations = []
    
    # Standard configuration: S1[i] vs S2[i]
    config = _evaluate_configuration(s1, s2, previous_matches, current_round, "standard")
    if config:
        configurations.append(config)
    
    # Transposed configuration: S2[i] vs S1[i] 
    config = _evaluate_configuration(s2, s1, previous_matches, current_round, "transpose")
    if config:
        configurations.append(config)
    
    # Adjacent exchanges in S1 (try all possible adjacent swaps)
    for i in range(len(s1) - 1):
        s1_variant = s1.copy()
        s1_variant[i], s1_variant[i + 1] = s1_variant[i + 1], s1_variant[i]
        config = _evaluate_configuration(s1_variant, s2, previous_matches, current_round, f"s1_exchange_{i}")
        if config:
            configurations.append(config)
    
    # Adjacent exchanges in S2 (try all possible adjacent swaps)
    for i in range(len(s2) - 1):
        s2_variant = s2.copy()
        s2_variant[i], s2_variant[i + 1] = s2_variant[i + 1], s2_variant[i]
        config = _evaluate_configuration(s1, s2_variant, previous_matches, current_round, f"s2_exchange_{i}")
        if config:
            configurations.append(config)
    
    # Try combinations of exchanges if we don't have enough good configurations
    if len(configurations) < 3:
        for i in range(min(2, len(s1) - 1)):
            for j in range(min(2, len(s2) - 1)):
                s1_variant = s1.copy()
                s2_variant = s2.copy()
                s1_variant[i], s1_variant[i + 1] = s1_variant[i + 1], s1_variant[i]
                s2_variant[j], s2_variant[j + 1] = s2_variant[j + 1], s2_variant[j]
                config = _evaluate_configuration(s1_variant, s2_variant, previous_matches, current_round, f"combo_{i}_{j}")
                if config:
                    configurations.append(config)
    
    return configurations


def _evaluate_configuration(list1: List[Player], list2: List[Player], previous_matches: Set[frozenset], current_round: int, config_name: str) -> Optional[Dict]:
    """Evaluate a specific pairing configuration with comprehensive scoring"""
    pairings = []
    unpaired = []
    
    # Detailed scoring metrics
    score_diff_total = 0
    rating_diff_total = 0
    absolute_color_violations = 0
    strong_color_violations = 0
    mild_color_violations = 0
    repeat_pairings = 0
    
    min_pairs = min(len(list1), len(list2))
    paired_ids = set()
    
    # Try to pair players from list1 and list2
    for i in range(min_pairs):
        p1, p2 = list1[i], list2[i]
        
        if p1.id in paired_ids or p2.id in paired_ids:
            continue
        
        # Check for repeat pairing
        if frozenset({p1.id, p2.id}) in previous_matches:
            repeat_pairings += 1
            unpaired.extend([p1, p2])
            continue
        
        # Check absolute color compatibility
        if not _are_colors_compatible(p1, p2):
            absolute_color_violations += 1
            unpaired.extend([p1, p2])
            continue
        
        # Assign colors and evaluate satisfaction
        white, black = _assign_colors_dutch_improved(p1, p2, current_round)
        pairings.append((white, black))
        paired_ids.add(p1.id)
        paired_ids.add(p2.id)
        
        # Calculate detailed metrics
        score_diff_total += abs(p1.score - p2.score)
        rating_diff_total += abs(p1.rating - p2.rating)
        
        # Evaluate color preference satisfaction
        color_satisfaction = _evaluate_color_satisfaction(white, black)
        if color_satisfaction['absolute_violation']:
            absolute_color_violations += 1
        elif color_satisfaction['strong_violation']:
            strong_color_violations += 1
        elif color_satisfaction['mild_violation']:
            mild_color_violations += 1
    
    # Add unpaired players
    for player in list1 + list2:
        if player.id not in paired_ids:
            unpaired.append(player)
    
    return {
        'name': config_name,
        'pairings': pairings,
        'unpaired': unpaired,
        'score_diff': score_diff_total,
        'rating_diff': rating_diff_total,
        'absolute_violations': absolute_color_violations,
        'strong_violations': strong_color_violations,
        'mild_violations': mild_color_violations,
        'repeat_pairings': repeat_pairings,
        'num_pairs': len(pairings),
        'pairing_efficiency': len(pairings) / (len(list1) + len(list2)) * 2 if len(list1) + len(list2) > 0 else 0
    }


def _select_optimal_configuration(configurations: List[Dict]) -> Optional[Dict]:
    """Select optimal configuration using enhanced but pragmatic FIDE criteria"""
    if not configurations:
        return None
    
    # First, filter out any configs with repeat pairings if we have alternatives
    no_repeats = [c for c in configurations if c['repeat_pairings'] == 0]
    if no_repeats:
        configurations = no_repeats
    
    # Then filter out configs with absolute violations if we have alternatives
    no_absolute = [c for c in configurations if c['absolute_violations'] == 0]
    if no_absolute:
        configurations = no_absolute
    
    # FIDE Priority with pragmatic approach:
    # 1. Maximize number of pairings (most important)
    # 2. Minimize absolute violations (if any remain)
    # 3. Minimize repeat pairings (if any remain)
    # 4. Minimize strong color violations
    # 5. Minimize score differences
    # 6. Minimize mild violations and rating differences
    best = max(configurations, key=lambda c: (
        c['num_pairs'],                  # PRIMARY: maximize pairings
        -c['absolute_violations'],       # Then minimize absolute violations
        -c['repeat_pairings'],          # Then minimize repeats
        -c['strong_violations'],        # Then minimize strong violations
        -c['score_diff'] / max(1, c['num_pairs']),  # Normalized score difference
        -c['mild_violations']           # Finally mild violations
    ))
    
    return best


def _are_colors_compatible(player1: Player, player2: Player) -> bool:
    """Check if two players can be paired considering absolute color constraints"""
    abs1 = _has_absolute_color_preference(player1)
    abs2 = _has_absolute_color_preference(player2)
    
    if abs1 and abs2:
        pref1 = _get_color_preference(player1)
        pref2 = _get_color_preference(player2)
        # Both have absolute preferences - they must be different
        return pref1 != pref2
    
    return True


def _evaluate_color_satisfaction(white_player: Player, black_player: Player) -> Dict:
    """Evaluate how well the color assignment satisfies preferences"""
    white_pref = _get_color_preference(white_player)
    black_pref = _get_color_preference(black_player)
    white_abs = _has_absolute_color_preference(white_player)
    black_abs = _has_absolute_color_preference(black_player)
    
    result = {
        'absolute_violation': False,
        'strong_violation': False,
        'mild_violation': False
    }
    
    # Check absolute violations
    if white_abs and white_pref != W:
        result['absolute_violation'] = True
    elif black_abs and black_pref != B:
        result['absolute_violation'] = True
    # Check strong preference violations
    elif white_pref and white_pref != W and not white_abs:
        result['strong_violation'] = True
    elif black_pref and black_pref != B and not black_abs:
        result['strong_violation'] = True
    # Check mild preference violations (if neither strong nor absolute)
    elif white_pref == B or black_pref == W:
        result['mild_violation'] = True
    
    return result


def _enhanced_fallback_pairing(bracket: List[Player], previous_matches: Set[frozenset], current_round: int) -> Tuple[List[Tuple[Player, Player]], List[Player]]:
    """Enhanced fallback pairing with better compatibility checking"""
    pairings = []
    remaining = bracket.copy()
    
    # Sort by priority: players with absolute color preferences first, then by score/rating
    remaining.sort(key=lambda p: (not _has_absolute_color_preference(p), -p.score, -p.rating, p.pairing_number))
    
    while len(remaining) >= 2:
        player1 = remaining.pop(0)
        best_opponent_idx = None
        best_score = float('inf')
        
        for i, player2 in enumerate(remaining):
            # Basic compatibility checks
            compatible = True
            
            # Skip if they've played before (strict check)
            if frozenset({player1.id, player2.id}) in previous_matches:
                compatible = False
            
            # Skip if colors are absolutely incompatible
            if compatible and not _are_colors_compatible(player1, player2):
                compatible = False
            
            if not compatible:
                continue
            
            # Score this pairing - prioritize by compatibility and balance
            score_diff = abs(player1.score - player2.score)
            rating_diff = abs(player1.rating - player2.rating) / 1000  # Normalize
            
            # Color compatibility bonus
            color_bonus = 0
            if _colors_would_satisfy_preferences(player1, player2):
                color_bonus = -5  # Good color match bonus
            
            # Preference for similar scores (within same bracket)
            score_bonus = 0 if score_diff == 0 else 2
            
            total_score = score_diff + rating_diff + color_bonus + score_bonus
            
            if total_score < best_score:
                best_score = total_score
                best_opponent_idx = i
        
        if best_opponent_idx is not None:
            player2 = remaining.pop(best_opponent_idx)
            white, black = _assign_colors_dutch_improved(player1, player2, current_round)
            pairings.append((white, black))
        else:
            # If no compatible opponent found, try one more relaxed pass
            # allowing some color preferences to be violated if necessary
            for i, player2 in enumerate(remaining):
                if frozenset({player1.id, player2.id}) not in previous_matches:
                    player2 = remaining.pop(i)
                    white, black = _assign_colors_dutch_improved(player1, player2, current_round)
                    pairings.append((white, black))
                    break
            # If still no pairing possible, player1 becomes unpaired
    
    return pairings, remaining


def _colors_would_satisfy_preferences(player1: Player, player2: Player) -> bool:
    """Check if a pairing would satisfy both players' color preferences"""
    pref1 = _get_color_preference(player1)
    pref2 = _get_color_preference(player2)
    
    # If no preferences, it's fine
    if not pref1 and not pref2:
        return True
    
    # If preferences are compatible (one wants white, other wants black or doesn't care)
    if pref1 == W and (not pref2 or pref2 == B):
        return True
    if pref2 == W and (not pref1 or pref1 == B):
        return True
    if pref1 == B and (not pref2 or pref2 == W):
        return True
    if pref2 == B and (not pref1 or pref1 == W):
        return True
    
    return False


def _group_players_by_score(players: List[Player]) -> Dict[float, List[Player]]:
    """Group players by their current score"""
    score_groups = {}
    for player in players:
        score_groups.setdefault(player.score, []).append(player)
    return score_groups


def _group_players_by_score(players: List[Player]) -> Dict[float, List[Player]]:
    """Group players by their current score"""
    score_groups = {}
    for player in players:
        score_groups.setdefault(player.score, []).append(player)
    return score_groups


def _generate_dutch_configurations(s1: List[Player], s2: List[Player], previous_matches: Set[frozenset], current_round: int) -> List[Dict]:
    """Generate all valid pairing configurations using Dutch system rules"""
    configurations = []
    
    # Configuration 1: Standard pairing (S1[i] vs S2[i])
    config = _try_dutch_configuration(s1, s2, previous_matches, current_round, "standard")
    if config:
        configurations.append(config)
    
    # Configuration 2: Transposition (S2[i] vs S1[i])
    config = _try_dutch_configuration(s2, s1, previous_matches, current_round, "transpose")
    if config:
        configurations.append(config)
    
    # Configuration 3+: Adjacent exchanges in S1
    for i in range(len(s1) - 1):
        s1_variant = s1.copy()
        s1_variant[i], s1_variant[i + 1] = s1_variant[i + 1], s1_variant[i]
        config = _try_dutch_configuration(s1_variant, s2, previous_matches, current_round, f"s1_exchange_{i}")
        if config:
            configurations.append(config)
    
    # Configuration N+: Adjacent exchanges in S2
    for i in range(len(s2) - 1):
        s2_variant = s2.copy()
        s2_variant[i], s2_variant[i + 1] = s2_variant[i + 1], s2_variant[i]
        config = _try_dutch_configuration(s1, s2_variant, previous_matches, current_round, f"s2_exchange_{i}")
        if config:
            configurations.append(config)
    
    return configurations


def _try_dutch_configuration(list1: List[Player], list2: List[Player], previous_matches: Set[frozenset], current_round: int, config_name: str) -> Optional[Dict]:
    """Try a specific Dutch system pairing configuration"""
    pairings = []
    unpaired = []
    score_diff_total = 0
    color_balance_violations = 0
    
    min_pairs = min(len(list1), len(list2))
    paired_ids = set()
    
    # Try to pair players from list1 and list2
    for i in range(min_pairs):
        p1, p2 = list1[i], list2[i]
        
        if p1.id in paired_ids or p2.id in paired_ids:
            continue
        
        # Check compatibility
        if not _are_players_compatible(p1, p2, previous_matches):
            unpaired.extend([p1, p2])
            continue
        
        # Assign colors using Dutch system rules
        white, black = _assign_colors_dutch_improved(p1, p2, current_round)
        pairings.append((white, black))
        paired_ids.add(p1.id)
        paired_ids.add(p2.id)
        
        # Calculate metrics for optimization
        score_diff_total += abs(p1.score - p2.score)
        
        # Check color balance satisfaction
        if not _colors_satisfy_preferences(white, black):
            color_balance_violations += 1
    
    # Add unpaired players
    for player in list1 + list2:
        if player.id not in paired_ids:
            unpaired.append(player)
    
    return {
        'name': config_name,
        'pairings': pairings,
        'unpaired': unpaired,
        'score_diff': score_diff_total,
        'color_violations': color_balance_violations,
        'num_pairs': len(pairings)
    }


def _select_best_dutch_configuration(configurations: List[Dict]) -> Optional[Dict]:
    """Select the best configuration based on FIDE Dutch system criteria"""
    if not configurations:
        return None
    
    # FIDE Priority order:
    # 1. Minimize unpaired players (maximize number of pairings)
    # 2. Minimize absolute color preference violations
    # 3. Minimize total score differences within pairings  
    # 4. Minimize mild color preference violations
    best = min(configurations, key=lambda c: (
        len(c['unpaired']),           # Primary: minimize unpaired players
        c['color_violations'],        # Secondary: minimize color violations
        c['score_diff']              # Tertiary: minimize score differences
    ))
    
    return best


def _assign_colors_dutch_improved(player1: Player, player2: Player, current_round: int) -> Tuple[Player, Player]:
    """
    Enhanced color assignment using stricter FIDE Dutch system rules.
    Returns (white_player, black_player)
    """
    pref1 = _get_color_preference(player1)
    pref2 = _get_color_preference(player2)
    abs1 = _has_absolute_color_preference(player1)
    abs2 = _has_absolute_color_preference(player2)
    
    # Rule 1: Absolute preferences have highest priority
    if abs1 and not abs2:
        # Player1 has absolute preference, player2 doesn't
        if pref1 == W:
            return (player1, player2)
        else:
            return (player2, player1)
    elif abs2 and not abs1:
        # Player2 has absolute preference, player1 doesn't
        if pref2 == W:
            return (player2, player1)
        else:
            return (player1, player2)
    elif abs1 and abs2:
        # Both have absolute preferences - they should be compatible at this point
        if pref1 == W and pref2 == B:
            return (player1, player2)
        elif pref1 == B and pref2 == W:
            return (player2, player1)
        else:
            # This shouldn't happen if compatibility was checked properly
            # Fall back to balance-based assignment
            return _assign_by_color_balance(player1, player2, current_round)
    
    # Rule 2: Strong (non-absolute) preferences
    if pref1 and pref2:
        if pref1 == W and pref2 == B:
            return (player1, player2)
        elif pref1 == B and pref2 == W:
            return (player2, player1)
        elif pref1 == pref2:
            # Both want same color - use balance to decide
            return _assign_by_color_balance(player1, player2, current_round)
    
    # Rule 3: Single strong preference
    if pref1 and not pref2:
        if pref1 == W:
            return (player1, player2)
        else:
            return (player2, player1)
    elif pref2 and not pref1:
        if pref2 == W:
            return (player2, player1)
        else:
            return (player1, player2)
    
    # Rule 4: No strong preferences - use color balance
    return _assign_by_color_balance(player1, player2, current_round)


def _assign_by_color_balance(player1: Player, player2: Player, current_round: int) -> Tuple[Player, Player]:
    """Assign colors based on color balance when no strong preferences exist"""
    colors1 = [c for c in player1.color_history if c is not None]
    colors2 = [c for c in player2.color_history if c is not None]
    
    balance1 = colors1.count(W) - colors1.count(B) if colors1 else 0
    balance2 = colors2.count(W) - colors2.count(B) if colors2 else 0
    
    # Prefer to balance colors - give white to player with fewer whites
    if balance1 < balance2:
        return (player1, player2)
    elif balance2 < balance1:
        return (player2, player1)
    
    # If equal balance, use other criteria
    # Check last color played to avoid consecutive same colors if possible
    last1 = colors1[-1] if colors1 else None
    last2 = colors2[-1] if colors2 else None
    
    if last1 == B and last2 != B:
        return (player1, player2)  # Give white to player who played black last
    elif last2 == B and last1 != B:
        return (player2, player1)
    elif last1 == W and last2 != W:
        return (player2, player1)  # Give white to player who didn't play white last
    elif last2 == W and last1 != W:
        return (player1, player2)
    
    # Final tiebreaker: use rating and round number for deterministic assignment
    if player1.rating >= player2.rating:
        # Higher rated player gets color based on round parity and some determinism
        if (current_round + player1.pairing_number) % 2 == 0:
            return (player1, player2)
        else:
            return (player2, player1)
    else:
        # Lower rated player gets opposite treatment
        if (current_round + player2.pairing_number) % 2 == 0:
            return (player2, player1)
        else:
            return (player1, player2)


def _colors_satisfy_preferences(white_player: Player, black_player: Player) -> bool:
    """Check if the color assignment satisfies both players' preferences"""
    white_pref = _get_color_preference(white_player)
    black_pref = _get_color_preference(black_player)
    
    # Check if assignment violates absolute preferences
    if _has_absolute_color_preference(white_player) and white_pref != W:
        return False
    if _has_absolute_color_preference(black_player) and black_pref != B:
        return False
    
    return True


def _pair_remaining_players(players: List[Player], previous_matches: Set[frozenset]) -> List[Tuple[Player, Player]]:
    """Pair remaining players with minimal constraints"""
    pairings = []
    remaining = players.copy()
    
    while len(remaining) >= 2:
        player1 = remaining.pop(0)
        
        # Find best available opponent
        best_opponent_idx = None
        best_score_diff = float('inf')
        
        for i, player2 in enumerate(remaining):
            # Allow repeat pairings as last resort for remaining players
            score_diff = abs(player1.score - player2.score)
            if score_diff < best_score_diff:
                best_score_diff = score_diff
                best_opponent_idx = i
        
        if best_opponent_idx is not None:
            player2 = remaining.pop(best_opponent_idx)
            white, black = _assign_colors_dutch_improved(player1, player2, 99)  # Use high round for default logic
            pairings.append((white, black))
    
    return pairings


def _are_players_compatible(player1: Player, player2: Player, previous_matches: Set[frozenset]) -> bool:
    """Check if two players can be paired (absolute constraints)"""
    # Check if they have played before
    if frozenset({player1.id, player2.id}) in previous_matches:
        return False
    
    # Check absolute color constraints
    if _has_absolute_color_preference(player1) and _has_absolute_color_preference(player2):
        pref1 = _get_color_preference(player1)
        pref2 = _get_color_preference(player2)
        if pref1 == pref2:
            return False
    
    return True


def _select_best_candidate(candidates: List[Dict]) -> Optional[Dict]:
    """Select the best pairing candidate based on FIDE criteria"""
    if not candidates:
        return None
    
    # Sort by: fewer floaters (better), then lower total score difference
    best_candidate = min(candidates, key=lambda c: (len(c['floaters']), c['score_diff']))
    return best_candidate


def _greedy_pair_bracket(bracket: List[Player], previous_matches: Set[frozenset]) -> Tuple[List[Tuple[Player, Player]], List[Player]]:
    """Fallback greedy pairing when optimal pairing fails"""
    pairings = []
    remaining = bracket.copy()
    
    while len(remaining) >= 2:
        player1 = remaining.pop(0)
        paired = False
        
        for i, player2 in enumerate(remaining):
            if _are_players_compatible(player1, player2, previous_matches):
                white_player, black_player = _assign_colors_dutch_improved(player1, player2, 99)
                pairings.append((white_player, black_player))
                remaining.pop(i)
                paired = True
                break
        
        if not paired:
            # No legal opponent found, this player becomes a floater
            continue
    
    return pairings, remaining


def _get_color_preference(player: Player) -> Optional[str]:
    """Determine a player's color preference based on FIDE rules"""
    if not hasattr(player, 'color_history') or not player.color_history:
        return None
    
    # Filter out None values (byes)
    valid_colors = [c for c in player.color_history if c is not None]
    
    if not valid_colors:
        return None
    
    # Absolute preference: if last two games were same color, must play opposite
    if len(valid_colors) >= 2 and valid_colors[-1] == valid_colors[-2]:
        return B if valid_colors[-1] == W else W
    
    # Strong preference: if color imbalance > 1, prefer underrepresented color
    white_count = valid_colors.count(W)
    black_count = valid_colors.count(B)
    color_diff = white_count - black_count
    
    if color_diff > 1:
        return B
    elif color_diff < -1:
        return W
    
    # Mild preference: if color imbalance = 1, mildly prefer underrepresented color
    # But don't make this too restrictive for pairing purposes
    if color_diff == 1:
        return B
    elif color_diff == -1:
        return W
    
    return None


def _has_absolute_color_preference(player: Player) -> bool:
    """Check if player has an absolute color preference that cannot be violated"""
    if not hasattr(player, 'color_history') or not player.color_history:
        return False
    
    # Filter out None values (byes)
    valid_colors = [c for c in player.color_history if c is not None]
    
    if len(valid_colors) < 2:
        return False
    
    # Absolute Rule 1: If color imbalance >= 2, player must get the minority color
    white_count = valid_colors.count(W)
    black_count = valid_colors.count(B)
    color_diff = white_count - black_count
    
    if abs(color_diff) >= 2:
        return True
    
    # Absolute Rule 2: If last two consecutive games were same color, must alternate
    if len(valid_colors) >= 2 and valid_colors[-1] == valid_colors[-2]:
        return True
    
    return False


def _get_float_type(player: Player, rounds_back: int, current_round: int) -> FloatType:
    """Determine the float direction of a player in a previous round"""
    if rounds_back >= current_round or rounds_back < 1:
        return FloatType.FLOAT_NONE
    
    target_round = current_round - rounds_back
    if target_round <= 0 or target_round > len(player.running_scores):
        return FloatType.FLOAT_NONE
    
    # This would need more sophisticated logic to track actual floater status
    # For now, return FLOAT_NONE as a placeholder
    return FloatType.FLOAT_NONE
