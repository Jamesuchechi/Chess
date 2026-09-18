"""Unit tests for SettingsService user preferences persistence and signals."""

from PySide6.QtCore import QCoreApplication, QSettings

from chess_desktop.services.settings_service import SettingsService


def test_settings_service_defaults() -> None:
    """SettingsService provides reasonable defaults on a clean settings store."""
    _app = QCoreApplication.instance() or QCoreApplication([])
    settings = QSettings("ChessTestCorp", "TestDefaults")
    settings.clear()

    service = SettingsService(settings=settings)
    assert service.board_theme == "classic"
    assert service.piece_set == "standard"
    assert service.sound_enabled is True
    assert service.sound_volume == 80
    assert service.stockfish_path == ""
    assert service.default_difficulty == "Intermediate"
    settings.clear()


def test_settings_service_updates_and_signals() -> None:
    """Setting preferences persists them and triggers appropriate signals."""
    _app = QCoreApplication.instance() or QCoreApplication([])
    settings = QSettings("ChessTestCorp", "TestUpdates")
    settings.clear()

    service = SettingsService(settings=settings)

    theme_calls: list[str] = []
    volume_calls: list[int] = []
    sound_calls: list[bool] = []
    generic_calls: list[int] = []

    service.board_theme_changed.connect(theme_calls.append)
    service.sound_volume_changed.connect(volume_calls.append)
    service.sound_enabled_changed.connect(sound_calls.append)
    service.settings_changed.connect(lambda: generic_calls.append(1))

    # Theme
    service.set_board_theme("wood")
    assert service.board_theme == "wood"
    assert theme_calls == ["wood"]

    # Sound enabled
    service.set_sound_enabled(False)
    assert service.sound_enabled is False
    assert sound_calls == [False]

    # Volume clamping
    service.set_sound_volume(65)
    assert service.sound_volume == 65
    assert volume_calls[-1] == 65

    service.set_sound_volume(120)
    assert service.sound_volume == 100
    assert volume_calls[-1] == 100

    service.set_sound_volume(-5)
    assert service.sound_volume == 0
    assert volume_calls[-1] == 0

    # Stockfish path & difficulty
    service.set_stockfish_path("/usr/bin/stockfish")
    assert service.stockfish_path == "/usr/bin/stockfish"

    service.set_default_difficulty("Expert")
    assert service.default_difficulty == "Expert"

    assert len(generic_calls) >= 5
    settings.clear()
