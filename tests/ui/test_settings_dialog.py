"""UI tests for SettingsDialog preferences interaction."""

from PySide6.QtCore import QSettings
from pytestqt.qtbot import QtBot

from chess_desktop.services.settings_service import SettingsService
from chess_desktop.ui.dialogs.settings_dialog import SettingsDialog


def test_settings_dialog_loads_and_saves_preferences(qtbot: QtBot) -> None:
    """SettingsDialog loads current settings and saves modifications upon acceptance."""
    settings = QSettings("ChessTestCorp", "TestDialog")
    settings.clear()
    service = SettingsService(settings=settings)
    service.set_board_theme("classic")
    service.set_sound_enabled(True)
    service.set_sound_volume(80)

    dialog = SettingsDialog(service)
    qtbot.addWidget(dialog)

    # Initial dialog states match service
    assert dialog._theme_combo.currentData() == "classic"
    assert dialog._sound_check.isChecked() is True
    assert dialog._vol_slider.value() == 80

    # User modifies values
    wood_idx = dialog._theme_combo.findData("wood")
    assert wood_idx >= 0
    dialog._theme_combo.setCurrentIndex(wood_idx)

    dialog._sound_check.setChecked(False)
    dialog._vol_slider.setValue(40)
    dialog._path_edit.setText("/custom/path/stockfish")

    adv_idx = dialog._diff_combo.findText("Advanced")
    assert adv_idx >= 0
    dialog._diff_combo.setCurrentIndex(adv_idx)

    # Accept dialog
    dialog.accept()

    # Service should be updated
    assert service.board_theme == "wood"
    assert service.sound_enabled is False
    assert service.sound_volume == 40
    assert service.stockfish_path == "/custom/path/stockfish"
    assert service.default_difficulty == "Advanced"

    settings.clear()


def test_settings_dialog_reject_does_not_save(qtbot: QtBot) -> None:
    """Rejecting/Canceling the dialog leaves settings unchanged."""
    settings = QSettings("ChessTestCorp", "TestReject")
    settings.clear()
    service = SettingsService(settings=settings)
    service.set_board_theme("classic")

    dialog = SettingsDialog(service)
    qtbot.addWidget(dialog)

    modern_idx = dialog._theme_combo.findData("modern")
    dialog._theme_combo.setCurrentIndex(modern_idx)

    dialog.reject()

    # Board theme remains unchanged
    assert service.board_theme == "classic"
    settings.clear()
