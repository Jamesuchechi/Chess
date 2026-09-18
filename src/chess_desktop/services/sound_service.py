"""Audio sound effects service with graceful degradation when audio drivers are missing."""

import logging
from typing import Any

from PySide6.QtCore import QObject, QUrl

import chess_desktop.ui.resources_rc  # noqa: F401
from chess_desktop.domain.game_state import MoveRecord

logger = logging.getLogger(__name__)

# Attempt to import QSoundEffect from QtMultimedia
try:
    from PySide6.QtMultimedia import QSoundEffect

    _AUDIO_AVAILABLE = True
except ImportError:
    _AUDIO_AVAILABLE = False
    logger.warning("QtMultimedia is not available. Audio sound effects disabled.")


class SoundService(QObject):
    """Manages audio effects for chess actions with robust fallback for headless/driverless environments."""

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._enabled = True
        self._volume = 0.8
        self._effects: dict[str, Any] = {}

        if _AUDIO_AVAILABLE:
            self._init_effects()

    def _init_effects(self) -> None:
        """Preload sound effect assets from Qt resources."""
        sound_names = [
            "move",
            "capture",
            "check",
            "castle",
            "promotion",
            "game_start",
            "game_end",
        ]
        for name in sound_names:
            try:
                effect = QSoundEffect(self)
                effect.setSource(QUrl(f"qrc:/sounds/{name}.wav"))
                effect.setVolume(self._volume)
                self._effects[name] = effect
            except Exception as e:
                logger.debug("Failed to initialize sound '%s': %s", name, e)

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    @property
    def sound_enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def set_sound_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    @property
    def volume(self) -> int:
        """Volume as percentage (0 to 100)."""
        return int(self._volume * 100)

    @property
    def sound_volume(self) -> int:
        """Volume as percentage (0 to 100)."""
        return int(self._volume * 100)

    def set_volume(self, volume: int) -> None:
        """Set volume (0 to 100)."""
        clamped = max(0, min(100, volume))
        self._volume = clamped / 100.0
        for effect in self._effects.values():
            try:
                effect.setVolume(self._volume)
            except Exception:
                pass

    def play(self, sound_name: str) -> None:
        """Play a named sound effect safely."""
        if not self._enabled or sound_name not in self._effects:
            return

        try:
            effect = self._effects[sound_name]
            effect.play()
        except Exception as e:
            # Graceful degradation if audio pipeline fails at runtime
            logger.debug("Sound playback error for '%s': %s", sound_name, e)

    def play_sound(self, sound_name: str) -> None:
        """Alias for play()."""
        self.play(sound_name)

    def sound_name_for_move(self, record: MoveRecord) -> str:
        """Return the sound name appropriate for a move record."""
        if record.is_check:
            return "check"
        if record.is_capture:
            return "capture"
        if record.san in ("O-O", "O-O-O") or record.uci in ("e1g1", "e1c1", "e8g8", "e8c8"):
            return "castle"
        if "=" in record.san or (len(record.uci) == 5 and record.uci[4] in "qrbn"):
            return "promotion"
        return "move"

    def play_move_record(self, record: MoveRecord) -> None:
        """Play the contextually appropriate audio effect for a completed move."""
        sound_name = self.sound_name_for_move(record)
        self.play(sound_name)

    def play_game_start(self) -> None:
        self.play("game_start")

    def play_game_end(self) -> None:
        self.play("game_end")
