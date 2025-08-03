# Import all dialogs from their separate modules
from .dialogs.new_tournament_dialog import NewTournamentDialog
from .dialogs.player_edit_dialog import PlayerEditDialog
from .dialogs.player_detail_dialog import PlayerDetailDialog
from .dialogs.settings_dialog import SettingsDialog
from .dialogs.manual_pair_dialog import ManualPairDialog
from .dialogs.manual_pairing_dialog import ManualPairingDialog
from .dialogs.update_dialog import UpdateDownloadDialog
from .dialogs.update_prompt_dialog import UpdatePromptDialog

# Re-export for backward compatibility
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
