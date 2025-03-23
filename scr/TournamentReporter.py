class TournamentReporter:
    def __init__(self, rounds):
        self.rounds = rounds

    def format_history(self):
        report = []
        for idx, (pairings, bye) in enumerate(self.rounds, 1):
            report.append(f"Round {idx} Pairings:")
            for white, black in pairings:
                report.append(f"  {white} (White) vs {black} (Black)")
            if bye:
                report.append(f"  Bye: {bye} (1 point awarded)")
            report.append("")  # blank line between rounds
        return "\n".join(report)
