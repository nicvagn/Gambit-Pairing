# Gambit Pairing
# Copyright (C) 2025  Gambit Pairing developers
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
