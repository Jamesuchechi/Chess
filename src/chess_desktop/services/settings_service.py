"""Application settings and user preferences management using QSettings."""

import logging
from typing import Any

from PySide6.QtCore import QObject, QSettings, Signal

logger = logging.getLogger(__name__)


class SettingsService(QObject):
    """Manages application settings persisted via QSettings."""

    settings_changed = Signal()
    board_theme_changed = Signal(str)
    piece_set_changed = Signal(str)
    sound_enabled_changed = Signal(bool)
    sound_volume_changed = Signal(int)
    stockfish_path_changed = Signal(str)
    default_difficulty_changed = Signal(str)

    def __init__(self, parent: Any = None, settings: QSettings | None = None) -> None:
        super().__init__(parent)
        self._settings = settings if settings is not None else QSettings("ChessDesktop", "Chess")

    @property
    def board_theme(self) -> str:
        val = self._settings.value("appearance/board_theme", "classic")
        return str(val)

    def set_board_theme(self, theme_name: str) -> None:
        self._settings.setValue("appearance/board_theme", theme_name)
        self.board_theme_changed.emit(theme_name)
        self.settings_changed.emit()

    @property
    def piece_set(self) -> str:
        val = self._settings.value("appearance/piece_set", "standard")
        return str(val)

    def set_piece_set(self, set_name: str) -> None:
        self._settings.setValue("appearance/piece_set", set_name)
        self.piece_set_changed.emit(set_name)
        self.settings_changed.emit()

    @property
    def sound_enabled(self) -> bool:
        val = self._settings.value("audio/sound_enabled", True)
        if isinstance(val, bool):
            return val
        return str(val).lower() in ("true", "1")

    def set_sound_enabled(self, enabled: bool) -> None:
        self._settings.setValue("audio/sound_enabled", enabled)
        self.sound_enabled_changed.emit(enabled)
        self.settings_changed.emit()

    @property
    def sound_volume(self) -> int:
        val = self._settings.value("audio/sound_volume", 80)
        try:
            return int(str(val))
        except (ValueError, TypeError):
            return 80

    def set_sound_volume(self, volume: int) -> None:
        clamped = max(0, min(100, volume))
        self._settings.setValue("audio/sound_volume", clamped)
        self.sound_volume_changed.emit(clamped)
        self.settings_changed.emit()

    @property
    def stockfish_path(self) -> str:
        val = self._settings.value("engine/stockfish_path", "")
        return str(val)

    def set_stockfish_path(self, path: str) -> None:
        self._settings.setValue("engine/stockfish_path", path)
        self.stockfish_path_changed.emit(path)
        self.settings_changed.emit()

    @property
    def default_difficulty(self) -> str:
        val = self._settings.value("engine/default_difficulty", "Intermediate")
        return str(val)

    def set_default_difficulty(self, diff: str) -> None:
        self._settings.setValue("engine/default_difficulty", diff)
        self.default_difficulty_changed.emit(diff)
        self.settings_changed.emit()
