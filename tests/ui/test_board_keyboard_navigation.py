from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from pytestqt.qtbot import QtBot

from chess_desktop.domain.enums import PlayerType
from chess_desktop.services.game_service import GameService
from chess_desktop.ui.board.board_widget import BoardWidget


def test_board_keyboard_arrow_navigation(qtbot: QtBot) -> None:
    service = GameService()
    service.new_game("Player1", "Player2", PlayerType.HUMAN, PlayerType.HUMAN)
    board = BoardWidget(service)
    qtbot.addWidget(board)
    board.show()

    # Initial cursor at e2
    board._cursor_square = "e2"

    # Press Key_Up -> e3
    event_up = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Up, Qt.KeyboardModifier.NoModifier)
    board.keyPressEvent(event_up)
    assert board._cursor_square == "e3"

    # Press Key_Up -> e4
    board.keyPressEvent(event_up)
    assert board._cursor_square == "e4"

    # Press Key_Left -> d4
    event_left = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Left, Qt.KeyboardModifier.NoModifier)
    board.keyPressEvent(event_left)
    assert board._cursor_square == "d4"

    # Press Key_Right -> e4
    event_right = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.KeyboardModifier.NoModifier)
    board.keyPressEvent(event_right)
    assert board._cursor_square == "e4"

    # Press Key_Down -> e3
    event_down = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier)
    board.keyPressEvent(event_down)
    assert board._cursor_square == "e3"

    service.cleanup()


def test_board_keyboard_move_execution(qtbot: QtBot) -> None:
    service = GameService()
    service.new_game("Player1", "Player2", PlayerType.HUMAN, PlayerType.HUMAN)
    board = BoardWidget(service)
    qtbot.addWidget(board)
    board.show()

    # Position cursor at e2
    board._cursor_square = "e2"

    # Press Space to select e2
    event_space = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier)
    board.keyPressEvent(event_space)
    assert board._selected_square == "e2"
    assert "e4" in board._legal_targets

    # Move cursor to e4
    event_up = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Up, Qt.KeyboardModifier.NoModifier)
    board.keyPressEvent(event_up)
    board.keyPressEvent(event_up)
    assert board._cursor_square == "e4"

    # Press Return to execute move e2 -> e4
    event_return = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
    board.keyPressEvent(event_return)

    # Move should be made and selection cleared
    assert board._selected_square is None
    assert len(service.get_state().moves) == 1
    assert service.get_state().moves[-1].uci == "e2e4"

    service.cleanup()


def test_board_keyboard_escape_deselects(qtbot: QtBot) -> None:
    service = GameService()
    service.new_game("Player1", "Player2", PlayerType.HUMAN, PlayerType.HUMAN)
    board = BoardWidget(service)
    qtbot.addWidget(board)
    board.show()

    board._cursor_square = "d2"
    event_space = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier)
    board.keyPressEvent(event_space)
    assert board._selected_square == "d2"

    event_esc = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
    board.keyPressEvent(event_esc)
    assert board._selected_square is None

    service.cleanup()
