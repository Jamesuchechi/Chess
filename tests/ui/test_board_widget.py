"""UI tests for BoardWidget."""

from PySide6.QtCore import QPoint, Qt
from pytestqt.qtbot import QtBot

from chess_desktop.domain.enums import Color, PieceType, PlayerType
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
    service.new_game("White", "Black", PlayerType.HUMAN, PlayerType.HUMAN)
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
    service.cleanup()


def test_board_widget_blocks_input_during_engine_thinking(qtbot: QtBot) -> None:
    """Verify clicking piece does not select or move when engine is calculating."""
    service = GameService()
    service.new_game("White", "Black", PlayerType.HUMAN, PlayerType.COMPUTER)
    widget = BoardWidget(service)
    qtbot.addWidget(widget)
    widget.resize(400, 400)
    widget.show()

    # Simulate engine thinking
    service._is_engine_thinking = True
    service.engine_thinking_changed.emit(True)

    assert widget.cursor().shape() == Qt.CursorShape.WaitCursor

    e2_rect = widget._square_rect("e2")
    e2_center = e2_rect.center().toPoint()
    qtbot.mouseClick(widget, Qt.MouseButton.LeftButton, pos=e2_center)

    # Selection should remain None
    assert widget._selected_square is None
    assert widget._legal_targets == {}

    # Reset thinking
    service._is_engine_thinking = False
    service.engine_thinking_changed.emit(False)
    assert widget.cursor().shape() == Qt.CursorShape.ArrowCursor
    service.cleanup()


def test_board_widget_move_animation_trigger(qtbot: QtBot) -> None:
    """Verify playing a move launches a piece move animation on BoardWidget."""
    service = GameService()
    service.new_game("White", "Black", PlayerType.HUMAN, PlayerType.HUMAN)
    widget = BoardWidget(service)
    qtbot.addWidget(widget)
    widget.resize(400, 400)
    widget.show()

    assert len(widget._animations) == 0

    assert service.try_move("e2", "e4")
    assert len(widget._animations) == 1
    assert widget._animations[0]["to_sq"] == "e4"

    # Wait for animation to finish
    qtbot.waitUntil(lambda: len(widget._animations) == 0, timeout=1000)
    service.cleanup()


def test_board_widget_castling_dual_animation(qtbot: QtBot) -> None:
    """Verify castling move triggers dual animations for King and Rook."""
    service = GameService()
    service.new_game("White", "Black", PlayerType.HUMAN, PlayerType.HUMAN)
    widget = BoardWidget(service)
    qtbot.addWidget(widget)
    widget.resize(400, 400)
    widget.show()

    # Play moves to reach castling: 1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. O-O
    moves = [("e2", "e4"), ("e7", "e5"), ("g1", "f3"), ("b8", "c6"), ("f1", "c4"), ("f8", "c5")]
    for f, t in moves:
        service.try_move(f, t)
        widget._clear_animations()

    # Castling move: White O-O
    assert service.try_move("e1", "g1")
    # Should create 2 animations: King (e1->g1) and Rook (h1->f1)
    assert len(widget._animations) == 2
    anim_to_sqs = {a["to_sq"] for a in widget._animations}
    assert "g1" in anim_to_sqs
    assert "f1" in anim_to_sqs

    qtbot.waitUntil(lambda: len(widget._animations) == 0, timeout=1000)
    service.cleanup()


def test_board_widget_illegal_drop_snapback(qtbot: QtBot) -> None:
    """Verify dropping a dragged piece on an illegal square triggers snap-back animation."""
    service = GameService()
    service.new_game("White", "Black", PlayerType.HUMAN, PlayerType.HUMAN)
    widget = BoardWidget(service)
    qtbot.addWidget(widget)
    widget.resize(400, 400)
    widget.show()

    e2_rect = widget._square_rect("e2")
    e2_center = e2_rect.center().toPoint()

    # Press on e2
    qtbot.mousePress(widget, Qt.MouseButton.LeftButton, pos=e2_center)
    assert widget._selected_square == "e2"

    # Drag to e5 (illegal destination for White pawn on first move)
    e5_rect = widget._square_rect("e5")
    e5_center = e5_rect.center().toPoint()

    widget._is_dragging = True
    widget._drag_square = "e2"
    widget._drag_start_pos = e2_center
    widget._drag_current_pos = e5_center

    # Release on e5
    qtbot.mouseRelease(widget, Qt.MouseButton.LeftButton, pos=e5_center)

    # Snap-back animation should be active
    assert widget._snapback_anim is not None
    assert widget._snapback_piece == (PieceType.PAWN, Color.WHITE)

    # Wait for snap-back animation to finish
    qtbot.waitUntil(lambda: widget._snapback_anim is None, timeout=1000)
    assert widget._is_dragging is False
    service.cleanup()
