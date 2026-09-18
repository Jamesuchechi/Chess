"""Unit tests for SoundService audio playback and fallback logic."""

from unittest.mock import MagicMock

from PySide6.QtCore import QCoreApplication

from chess_desktop.domain.enums import PieceType
from chess_desktop.domain.game_state import MoveRecord
from chess_desktop.services.sound_service import SoundService


def test_sound_service_init() -> None:
    """SoundService initializes with default settings."""
    _app = QCoreApplication.instance() or QCoreApplication([])
    service = SoundService()
    assert service.sound_enabled is True
    assert service.sound_volume == 80


def test_sound_service_mute_and_volume() -> None:
    """Toggling mute and adjusting volume updates internal state."""
    _app = QCoreApplication.instance() or QCoreApplication([])
    service = SoundService()

    service.set_sound_enabled(False)
    assert service.sound_enabled is False

    service.set_volume(45)
    assert service.sound_volume == 45

    # Clamping
    service.set_volume(150)
    assert service.sound_volume == 100
    service.set_volume(-10)
    assert service.sound_volume == 0


def test_sound_service_determines_correct_sound_type() -> None:
    """Move records map to the expected sound name."""
    _app = QCoreApplication.instance() or QCoreApplication([])
    service = SoundService()

    # Normal move
    m1 = MoveRecord(
        san="e4",
        uci="e2e4",
        from_square="e2",
        to_square="e4",
        is_capture=False,
    )
    assert service.sound_name_for_move(m1) == "move"

    # Capture move
    m2 = MoveRecord(
        san="exd5",
        uci="e4d5",
        from_square="e4",
        to_square="d5",
        is_capture=True,
        captured_piece=PieceType.PAWN,
    )
    assert service.sound_name_for_move(m2) == "capture"

    # Check move takes precedence
    m3 = MoveRecord(
        san="Qh5+",
        uci="d1h5",
        from_square="d1",
        to_square="h5",
        is_capture=False,
        is_check=True,
    )
    assert service.sound_name_for_move(m3) == "check"

    # Castling move
    m4 = MoveRecord(
        san="O-O",
        uci="e1g1",
        from_square="e1",
        to_square="g1",
        is_capture=False,
    )
    assert service.sound_name_for_move(m4) == "castle"

    # Promotion move
    m5 = MoveRecord(
        san="e8=Q",
        uci="e7e8q",
        from_square="e7",
        to_square="e8",
        is_capture=False,
    )
    assert service.sound_name_for_move(m5) == "promotion"


def test_sound_service_play_when_disabled_does_not_play() -> None:
    """When sound is disabled, play_sound does nothing."""
    _app = QCoreApplication.instance() or QCoreApplication([])
    service = SoundService()
    service.set_sound_enabled(False)

    mock_effect = MagicMock()
    service._effects["move"] = mock_effect

    service.play_sound("move")
    mock_effect.play.assert_not_called()


def test_sound_service_handles_playback_exception_gracefully() -> None:
    """When audio backend raises an exception, play_sound catches it without crashing."""
    _app = QCoreApplication.instance() or QCoreApplication([])
    service = SoundService()
    service.set_sound_enabled(True)

    mock_effect = MagicMock()
    mock_effect.play.side_effect = RuntimeError("PulseAudio daemon not running")
    service._effects["check"] = mock_effect

    # Must not raise
    service.play_sound("check")
