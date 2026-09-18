"""Tests for main window creation and basic properties."""

from pytestqt.qtbot import QtBot

from chess_desktop.ui.windows.main_window import MainWindow


def test_main_window_init(qtbot: QtBot) -> None:
    """Verify MainWindow initializes with correct properties."""
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.windowTitle() == "Chess Desktop"
    assert window.minimumWidth() == 960
    assert window.minimumHeight() == 720
    assert window.centralWidget() is not None
