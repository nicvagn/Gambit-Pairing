from typing import List, Tuple
from collections.abc import Iterable
from gambitpairing.core import Pairings, Players  # These are types
from gambitpairing.core.utils import root_logger
from gambitpairing.core.player import Player
from gambitpairing.core.exceptions import PairingException


"""fide handbook
Berger Tables for Round-Robin Tournaments

Where there is an odd number of players, the highest number counts as a bye.

3 or 4 players:
Rd 1: 1-4, 2-3.
Rd 2: 4-3, 1-2.
Rd 3: 2-4, 3-1.

5 or 6 players:
Rd 1: 1-6, 2-5, 3-4.
Rd 2: 6-4, 5-3, 1-2.
Rd 3: 2-6, 3-1, 4-5.
Rd 4: 6-5, 1-4, 2-3.
Rd 5: 3-6, 4-2, 5-1.

7 or 8 players:
Rd 1: 1-8, 2-7, 3-6, 4-5.
Rd 2: 8-5, 6-4, 7-3, 1-2.
Rd 3: 2-8, 3-1, 4-7, 5-6.
Rd 4: 8-6, 7-5, 1-4, 2-3.
Rd 5: 3-8, 4-2, 5-1, 6-7.
Rd 6: 8-7, 1-6, 2-5, 3-4.
Rd 7: 4-8, 5-3, 6-2, 7-1.

9 or 10 players:
Rd 1: 1-10, 2-9, 3-8, 4-7, 5-6.
Rd 2: 10-6, 7-5, 8-4, 9-3, 1-2.
Rd 3: 2-10, 3-1, 4-9, 5-8, 6-7.
Rd 4: 10-7, 8-6, 9-5, 1-4, 2-3.
Rd 5: 3-10, 4-2, 5-1, 6-9, 7-8.
Rd 6: 10-8, 9-7, 1-6, 2-5, 3-4.
Rd 7: 4-10, 5-3, 6-2, 7-1, 8-9.
Rd 8: 10-9, 1-8, 2-7, 3-6, 4-5.
Rd 9: 5-10, 6-4, 7-3, 8-2, 9-1.

11 or 12 players:
Rd 1: 1-12, 2-11, 3-10, 4-9, 5-8, 6-7.
Rd 2: 12-7, 8-6, 9-5, 10-4, 11-3, 1-2.
Rd 3: 2-12, 3-1, 4-11, 5-10, 6-9, 7-8.
Rd 4: 12-8, 9-7, 10-6, 11-5, 1-4, 2-3.
Rd 5: 3-12, 4-2, 5-1, 6-11, 7-10, 8-9.
Rd 6: 12-9, 10-8, 11-7, 1-6, 2-5, 3-4.
Rd 7: 4-12, 5-3, 6-2, 7-1, 8-11, 9-10.
Rd 8: 12-10, 11-9, 1-8, 2-7, 3-6, 4-5.
Rd 9: 5-12, 6-4, 7-3, 8-2, 9-1, 10-11.
Rd 10: 12-11, 1-10, 2-9, 3-8, 4-7, 5-6.
Rd 11: 6-12, 7-5, 8-4, 9-3, 10-2, 11-1.

13 or 14 players:
Rd 1: 1-14, 2-13, 3-12, 4-11, 5-10, 6-9, 7-8
Rd 2: 14-8, 9-7, 10-6, 11-5, 12-4, 13-3, 1-2
Rd 3: 2-14, 3-1, 4-13, 5-12, 6-11, 7-10, 8-9
Rd 4: 14-9, 10-8, 11-7, 12-6, 13-5, 1-4, 2-3
Rd 5: 3-14, 4-2, 5-1, 6-13, 7-12, 8-11, 9-10
Rd 6: 14-10, 11-9, 12-8, 13-7, 1-6, 2-5, 3-4
Rd 7: 4-14, 5-3, 6-2, 7-1, 8-13, 9-12, 10-11
Rd 8: 14-11, 12-10, 13-9, 1-8, 2-7, 3-6, 4-5
Rd 9: 5-14, 6-4, 7-3, 8-2, 9-1, 10-13, 11-12
Rd 10: 14-12, 13-11, 1-10, 2-9. 3-8, 4-7, 5-6
Rd 11: 6-14, 7-5, 8-4, 9-3, 10-2, 11-1, 12-13
Rd 12: 14-13, 1-12, 2-11, 3-10, 4-9, 5-8, 6-7
Rd 13: 7-14, 8-6, 9-5, 10-4, 11-3, 12-2, 13-1

15 or 16 players:
Rd 1: 1-16, 2-15, 3-14, 4-13, 5-12, 6-11, 7-10, 8-9.
Rd 2: 16-9, 10-8, 11-7, 12-6, 13-5, 14-4, 15-3, 1-2.
Rd 3: 2-16, 3-1, 4-15, 5-14, 6-13, 7-12, 8-11, 9-10.
Rd 4: 16-10, 11-9, 12-8, 13-7, 14-6, 15-5, 1-4, 2-3.
Rd 5: 3-16, 4-2, 5-1, 6-15, 7-14, 8-13, 9-12, 10-11.
Rd 6: 16-11, 12-10, 13-9, 14-8, 15-7, 1-6, 2-5, 3-4.
Rd 7: 4-16, 5-3, 6-2, 7-1, 8-15, 9-14, 10-13, 11-12.
Rd 8: 16-12, 13-11, 14-10, 15-9, 1-8, 2-7, 3-6, 4-5.
Rd 9: 5-16, 6-4, 7-3, 8-2, 9-1, 10-15, 11-14, 12-13.
Rd 10: 16-13, 14-12, 15-11, 1-10, 2-9, 3-8, 4-7, 5-6.
Rd 11: 6-16, 7-5, 8-4, 9-3, 10-2, 11-1, 12-15, 13-14.
Rd 12: 16-14, 15-13, 1-12, 2-11, 3-10, 4-9, 5-8, 6-7.
Rd 13: 7-16, 8-6, 9-5, 10-4, 11-3, 12-2, 13-1, 14-15.
Rd 14: 16-15, 1-14, 2-13, 3-12, 4-11, 5-10, 6-9, 7-8.
Rd 15: 8-16, 9-7, 10-6, 11-5, 12-4, 13-3, 14-2, 15-1.

For a double-round tournament it is recommended to reverse the order of the last two rounds of the first cycle. This is to avoid three consecutive games with the same colour.
"""
# adjusted for use with counting from 0
BERGER_TABLES = {
    "3-4": (
        ((0, 3), (1, 2)),
        ((3, 2), (0, 1)),
        ((1, 3), (2, 1)),
    ),
    "5-6": (
        ((0, 5), (1, 4), (2, 3)),
        ((5, 3), (4, 2), (0, 1)),
        ((1, 5), (2, 0), (3, 4)),
        ((5, 4), (0, 3), (1, 2)),
        ((2, 5), (3, 1), (4, 0)),
    ),
    "7-8": (
        ((0, 7), (1, 6), (2, 5), (3, 4)),
        ((7, 4), (5, 3), (6, 2), (0, 1)),
        ((1, 7), (2, 0), (3, 6), (4, 5)),
        ((7, 5), (6, 4), (0, 3), (1, 2)),
        ((2, 7), (3, 1), (4, 0), (5, 6)),
        ((7, 6), (0, 5), (1, 4), (2, 3)),
        ((3, 7), (4, 2), (5, 1), (6, 0)),
    ),
    "9-10": (
        ((0, 7), (1, 6), (2, 5), (3, 4)),
        ((7, 4), (5, 3), (6, 2), (0, 1)),
        ((1, 7), (2, 0), (3, 6), (4, 5)),
        ((7, 5), (6, 4), (0, 3), (1, 2)),
        ((2, 7), (3, 1), (4, 0), (5, 6)),
        ((7, 6), (0, 5), (1, 4), (2, 3)),
        ((3, 7), (4, 2), (5, 1), (6, 0)),
    ),
    "11-12": (
        ((0, 11), (1, 10), (2, 9), (3, 8), (4, 7), (5, 6)),
        ((11, 6), (7, 5), (8, 4), (9, 3), (10, 2), (0, 1)),
        ((1, 11), (2, 0), (3, 10), (4, 9), (5, 8), (6, 7)),
        ((11, 7), (8, 6), (9, 5), (10, 4), (0, 3), (1, 2)),
        ((2, 11), (3, 1), (4, 0), (5, 10), (6, 9), (7, 8)),
        ((11, 8), (9, 7), (10, 6), (0, 5), (1, 4), (2, 3)),
        ((3, 11), (4, 2), (5, 1), (6, 0), (7, 10), (8, 9)),
        ((11, 9), (10, 8), (0, 7), (1, 6), (2, 5), (3, 4)),
        ((4, 11), (5, 3), (6, 2), (7, 1), (8, 0), (9, 10)),
        ((11, 10), (0, 9), (1, 8), (2, 7), (3, 6), (4, 5)),
        ((5, 11), (6, 4), (7, 3), (8, 2), (9, 1), (10, 0)),
    ),
    "13-14": (
        ((0, 13), (1, 12), (2, 11), (3, 10), (4, 9), (5, 8), (6, 7)),
        ((13, 7), (8, 6), (9, 5), (10, 4), (11, 3), (12, 2), (0, 1)),
        ((1, 13), (2, 0), (3, 12), (4, 11), (5, 10), (6, 9), (7, 8)),
        ((13, 8), (9, 7), (10, 6), (11, 5), (12, 4), (0, 3), (1, 2)),
        ((2, 13), (3, 1), (4, 0), (5, 12), (6, 11), (7, 10), (8, 9)),
        ((13, 9), (10, 8), (11, 7), (12, 6), (0, 5), (1, 4), (2, 3)),
        ((3, 13), (4, 2), (5, 1), (6, 0), (7, 12), (8, 11), (9, 10)),
        ((13, 10), (11, 9), (12, 8), (0, 7), (1, 6), (2, 5), (3, 4)),
        ((4, 13), (5, 3), (6, 2), (7, 1), (8, 0), (9, 12), (10, 11)),
        ((13, 11), (12, 10), (0, 9), (1, 8), (2, 7), (3, 6), (4, 5)),
        ((5, 13), (6, 4), (7, 3), (8, 2), (9, 1), (10, 0), (11, 12)),
        ((13, 12), (0, 11), (1, 10), (2, 9), (3, 8), (4, 7), (5, 6)),
        ((6, 13), (7, 5), (8, 4), (9, 3), (10, 2), (11, 1), (12, 0)),
    ),
    "15-16": (
        ((0, 15), (1, 14), (2, 13), (3, 12), (4, 11), (5, 10), (6, 9), (7, 8)),
        ((15, 8), (9, 7), (10, 6), (11, 5), (12, 4), (13, 3), (14, 2), (0, 1)),
        ((1, 15), (2, 0), (3, 14), (4, 13), (5, 12), (6, 11), (7, 10), (8, 9)),
        ((15, 9), (10, 8), (11, 7), (12, 6), (13, 5), (14, 4), (0, 3), (1, 2)),
        ((2, 15), (3, 1), (4, 0), (5, 14), (6, 13), (7, 12), (8, 11), (9, 10)),
        ((15, 10), (11, 9), (12, 8), (13, 7), (14, 6), (0, 5), (1, 4), (2, 3)),
        ((3, 15), (4, 2), (5, 1), (6, 0), (7, 14), (8, 13), (9, 12), (10, 11)),
        ((15, 11), (12, 10), (13, 9), (14, 8), (0, 7), (1, 6), (2, 5), (3, 4)),
        ((4, 15), (5, 3), (6, 2), (7, 1), (8, 0), (9, 14), (10, 13), (11, 12)),
        ((15, 12), (13, 11), (14, 10), (0, 9), (1, 8), (2, 7), (3, 6), (4, 5)),
        ((5, 15), (6, 4), (7, 3), (8, 2), (9, 1), (10, 0), (11, 14), (12, 13)),
        ((15, 13), (14, 12), (0, 11), (1, 10), (2, 9), (3, 8), (4, 7), (5, 6)),
        ((6, 15), (7, 5), (8, 4), (9, 3), (10, 2), (11, 1), (12, 0), (13, 14)),
        ((15, 14), (0, 13), (1, 12), (2, 11), (3, 10), (4, 9), (5, 8), (6, 7)),
        ((7, 15), (8, 6), (9, 5), (10, 4), (11, 3), (12, 2), (13, 1), (14, 0)),
    ),
}


def create_round_robin_pairings(players: Players) -> Tuple[Pairings]:
    """
    Create pairings for FIDE round robin tournament

    Parameters
    ----------
    players : Players

    Returns
    -------
    Tuple(Pairings)
        the Pairings generated, index 0 is first round, etc.
    """

    rr = RoundRobin(players)

    root_logger.info("Round Robin created %s", rr)


class RoundRobin:
    """A round robin chess tournament"""

    def __init__(self, players: Iterable) -> None:
        n_players = len(players)

        if n_players > 16 or n_players < 3:
            root_logger.error(
                "Tried to pair round robin with invalid n_players: %s", n_players
            )
            raise PairingException(
                "Can not pair a round robin with n=%s players, n must be less than 17 and more than 3.",
                n_players,
            )

        # n_players is < 16 and > 3, so this will set the Berger table
        # to the correct val by starting from the top and decending
        if n_players > 14:
            self.berger_table = BERGER_TABLES["15-16"]
            root_logger.info("round robin created for 15-16 players")
        elif n_players > 12:
            self.berger_table = BERGER_TABLES["13-14"]
            root_logger.info("round robin created for 13-14 players")
        elif n_players > 10:
            self.berger_table = BERGER_TABLES["11-12"]
            root_logger.info("round robin created for 11-12 players")
        elif n_players > 8:
            self.berger_table = BERGER_TABLES["9-10"]
            root_logger.info("round robin created for 9-10 players")
        elif n_players > 6:
            self.berger_table = BERGER_TABLES["7-8"]
            root_logger.info("round robin created for 7-8 players")
        elif n_players > 6:
            self.berger_table = BERGER_TABLES["5-6"]
            root_logger.info("round robin created for 5-6 players")
        else:
            self.berger_table = BERGER_TABLES["3-4"]
            root_logger.info("round robin created for 3-4 players")

        self.round_num = 1
        self.number_of_rounds = len(self.berger_table)
        # we transform the list of players into an immutable tuple.
        # The order must be kept constant as the Berger tables require it.
        self.players = tuple(players)

        # pair the round robin. The entire round robin can be paired
        self._pair_round_robin()

    def _pair_round_robin(self):
        """Pair entire round robin tournament

        Parameters
        ----------
        self : RoundRobin
            A fully initalized RoundRobin
        """
        root_logger.info(f"players: {self.players}\nBerger Table: {self.berger_table}")

        self.round_pairings: List[Pairings] = []
        for rnd in range(self.number_of_rounds):
            self.round_pairings.append(self._pair_round_robin_round(rnd))

    def _pair_round_robin_round(self, round_number: int) -> Pairings:
        """Pair one round in a round robin tournament

        Raises
        ------
        PairingException
           if rnd is not paired for a tournament of this size

        Parameters
        ----------
        self : RoundRobin
            A fully initalized RoundRobin
        round_number : int
            round number to pair
        """
        if round_number > len(self.berger_table) or round_number < 0:
            raise (
                PairingException(
                    "round number %s not in %s berger table", round_number, self.berger_table
                )
            )
        berger_table = self.berger_table[round_number]

        root_logger.info(
            "Berger table for round (%s): \n%s\n |---| \n", round_number, berger_table
        )
        n = 1
        round_pairings = []
        for match_pairing in berger_table:
            pairing = (self.players[match_pairing[0]], self.players[match_pairing[1]])
            root_logger.info("game (%s): %s", n, pairing)
            round_pairings.append(pairing)
            root_logger.debug("round_pairings after pairing appended: (%s)", round_pairings)
            n = n + 1

        return tuple(round_pairings)

    def get_round_pairings(self, rnd: int) -> Pairings:
        """get pairings for a given round

        Raises
        ------
        PairingException
           if rnd is not in availible pairings

        Parametersfrom collections.abc import Iterable
        ----------
        rnd : int
            desired round of pairings

        Returns
        -------
        Pairings
            the pairings of desired round
        """
        if rnd > len(self.round_pairings):
            raise PairingException("Round %s is not in the RoundRobin", rnd)
        return self.round_pairings[int(rnd - 1)]

    def _pair_match(white: Player, black: Player,):
        """"""
    def __str__(self):
        n_rounds = len(self.berger_table)
        s = f"Round Robin with {n_rounds} rounds\n"
        for n in range(0, n_rounds):
            s += f"round {n} pairings: \n{self.round_pairings[n]} \n [-----]"
        return s


if __name__ == "__main__":
    p = [Player("nic"), Player("mom"), Player("ruth"), Player("sarah")]
    rr = RoundRobin(p)
