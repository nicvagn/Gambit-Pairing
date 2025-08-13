"""Dialog modules for the GUI."""

from .about_dialog import AboutDialog
from .manual_pairing_dialog import ManualPairingDialog
from .new_tournament_dialog import NewTournamentDialog
from .player_management_dialog import PlayerManagementDialog
from .settings_dialog import SettingsDialog
from .update_dialog import UpdateDownloadDialog
from .update_prompt_dialog import UpdatePromptDialog

__all__ = [
    "NewTournamentDialog",
    "PlayerManagementDialog",
    "SettingsDialog",
    "ManualPairingDialog",
    "UpdateDownloadDialog",
    "UpdatePromptDialog",
    "AboutDialog",
]
