"""UI tests for MainWindow keyboard shortcuts, theme updates, and audio wiring."""

from unittest.mock import MagicMock

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from pytestqt.qtbot import QtBot

from chess_desktop.domain.theme import BoardTheme
from chess_desktop.ui.windows.main_window import MainWindow


def test_main_window_keyboard_shortcuts(qtbot: QtBot) -> None:
    """MainWindow registers window-wide actions for navigation and actions."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    # Flip board
    initial_flipped = window.game_service.is_flipped
    window._flip_action.trigger()
    assert window.game_service.is_flipped != initial_flipped
    window._flip_action.trigger()
    assert window.game_service.is_flipped == initial_flipped

    # Play a move and test undo shortcut
    assert window.game_service.try_move("e2", "e4") is True
    assert len(window.game_service.get_state().moves) == 1

    window._undo_action.trigger()
    assert len(window.game_service.get_state().moves) == 0

    # Test move navigation shortcuts
    window.game_service.try_move("e2", "e4")
    window.game_service.try_move("e7", "e5")

    # Step backward
    window._prev_action.trigger()
    assert window.game_service.is_reviewing is True
    assert window.game_service.get_state().review_ply == 1

    # Step forward
    window._next_action.trigger()
    assert window.game_service.is_reviewing is False

    # First move (Home)
    window._home_action.trigger()
    assert window.game_service.is_reviewing is True
    assert window.game_service.get_state().review_ply == 0

    # Live position (End)
    window._end_action.trigger()
    assert window.game_service.is_reviewing is False


def test_escape_clears_board_selection(qtbot: QtBot) -> None:
    """Pressing Escape clears square selection on the board."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    board = window.board_widget
    board._selected_square = "e2"
    board._legal_targets = {"e3": False, "e4": False}

    # Trigger escape shortcut
    window._esc_action.trigger()
    assert board._selected_square is None
    assert len(board._legal_targets) == 0

    # Also test keyPressEvent directly on board
    board._selected_square = "d2"
    event = QKeyEvent(
        QKeyEvent.Type.KeyPress,
        Qt.Key.Key_Escape,
        Qt.KeyboardModifier.NoModifier,
    )
    board.keyPressEvent(event)
    assert board._selected_square is None


def test_main_window_theme_switching(qtbot: QtBot) -> None:
    """Changing theme in SettingsService updates BoardWidget theme immediately."""
    window = MainWindow()
    qtbot.addWidget(window)

    window.settings_service.set_board_theme("wood")
    assert window.board_widget.theme.name == "wood"

    window.settings_service.set_board_theme("high_contrast")
    assert window.board_widget.theme.name == "high_contrast"
    assert window.board_widget.theme.light_square == BoardTheme.high_contrast().light_square


def test_main_window_sound_service_wiring(qtbot: QtBot) -> None:
    """Making a move triggers play_move_record on sound service."""
    window = MainWindow()
    qtbot.addWidget(window)

    mock_play_move = MagicMock()
    window.sound_service.play_move_record = mock_play_move  # type: ignore[method-assign]

    window.game_service.try_move("e2", "e4")
    assert mock_play_move.call_count == 1
