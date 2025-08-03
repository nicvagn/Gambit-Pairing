"""Dialog modules for the GUI."""

from .new_tournament_dialog import NewTournamentDialog
from .player_edit_dialog import PlayerEditDialog
from .player_detail_dialog import PlayerDetailDialog
from .settings_dialog import SettingsDialog
from .manual_pair_dialog import ManualPairDialog
from .manual_pairing_dialog import ManualPairingDialog
from .update_dialog import UpdateDownloadDialog
from .update_prompt_dialog import UpdatePromptDialog

__all__ = [
    "NewTournamentDialog",
    "PlayerEditDialog", 
    "PlayerDetailDialog",
    "SettingsDialog",
    "ManualPairDialog",
    "ManualPairingDialog",
    "UpdateDownloadDialog",
    "UpdatePromptDialog",
]
