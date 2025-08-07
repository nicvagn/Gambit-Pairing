"""Dialog modules for the GUI."""

from .new_tournament_dialog import NewTournamentDialog
from .player_edit_dialog import PlayerEditDialog
from .player_detail_dialog import PlayerDetailDialog
from .settings_dialog import SettingsDialog
from .manual_pairing_dialog import ManualPairingDialog
from .update_dialog import UpdateDownloadDialog
from .update_prompt_dialog import UpdatePromptDialog
from .about_dialog import AboutDialog

__all__ = [
    "NewTournamentDialog",
    "PlayerEditDialog", 
    "PlayerDetailDialog",
    "SettingsDialog",
    "ManualPairingDialog",
    "UpdateDownloadDialog",
    "UpdatePromptDialog",
    "AboutDialog",
]
