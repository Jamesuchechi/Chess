"""UI tests for BoardWidget."""

from PySide6.QtCore import QPoint, Qt
from pytestqt.qtbot import QtBot

from chess_desktop.services.game_service import GameService
from chess_desktop.ui.board.board_widget import BoardWidget


def test_board_widget_initial_state(qtbot: QtBot) -> None:
    """Verify BoardWidget initializes with correct size and properties."""
    service = GameService()
    widget = BoardWidget(service)
    qtbot.addWidget(widget)
    widget.resize(400, 400)
    widget.show()

    assert widget._selected_square is None
    assert widget._legal_targets == {}
    assert widget._is_dragging is False


def test_board_widget_square_at_pos(qtbot: QtBot) -> None:
    """Verify pixel coordinates map accurately to algebraic squares."""
    service = GameService()
    widget = BoardWidget(service)
    qtbot.addWidget(widget)
    widget.resize(400, 400)
    widget.show()

    # Square size is 400 / 8 = 50px
    # Top-left square (col 0, row 0) should be 'a8' when not flipped
    sq = widget._square_at_pos(QPoint(25, 25))
    assert sq == "a8"

    # Bottom-left square (col 0, row 7) should be 'a1'
    sq = widget._square_at_pos(QPoint(25, 375))
    assert sq == "a1"

    # Bottom-right square (col 7, row 7) should be 'h1'
    sq = widget._square_at_pos(QPoint(375, 375))
    assert sq == "h1"

    # Outside board boundary
    assert widget._square_at_pos(QPoint(-10, -10)) is None


def test_board_widget_click_selection_and_move(qtbot: QtBot) -> None:
    """Verify clicking friendly piece selects it and clicking target executes move."""
    service = GameService()
    widget = BoardWidget(service)
    qtbot.addWidget(widget)
    widget.resize(400, 400)
    widget.show()

    # e2 square is col 4, row 6 -> x = 4.5 * 50 = 225, y = 6.5 * 50 = 325
    e2_rect = widget._square_rect("e2")
    e2_center = e2_rect.center().toPoint()

    # Click on e2
    qtbot.mouseClick(widget, Qt.MouseButton.LeftButton, pos=e2_center)
    assert widget._selected_square == "e2"
    assert "e4" in widget._legal_targets
    assert "e3" in widget._legal_targets

    # Click on e4
    e4_rect = widget._square_rect("e4")
    e4_center = e4_rect.center().toPoint()
    qtbot.mouseClick(widget, Qt.MouseButton.LeftButton, pos=e4_center)

    assert widget._selected_square is None
    assert service.get_state().last_move == ("e2", "e4")
    assert service.get_state().turn.value == "black"
