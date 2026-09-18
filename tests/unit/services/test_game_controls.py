"""Unit tests for Phase 2 game controls (Undo, Resign, Draw, Navigation, Branching)."""

from chess_desktop.domain.enums import Color, GameStatus, PieceType
from chess_desktop.services.game_service import GameService


def test_undo_single_move() -> None:
    """Verify undo reverts 1 ply and restores board state and turn."""
    service = GameService()
    service.try_move("e2", "e4")
    assert len(service.get_state().moves) == 1
    assert service.get_state().turn == Color.BLACK

    success = service.undo_move()
    assert success is True
    assert len(service.get_state().moves) == 0
    assert service.get_state().turn == Color.WHITE
    assert service.board.piece_at("e4") is None
    assert service.board.piece_at("e2") == (PieceType.PAWN, Color.WHITE)


def test_undo_restores_captured_piece() -> None:
    """Verify undoing a capture restores the captured piece and material diff."""
    service = GameService()
    service.try_move("e2", "e4")
    service.try_move("d7", "d5")
    service.try_move("e4", "d5")  # White captures pawn

    state = service.get_state()
    assert state.captured_white == [PieceType.PAWN]
    assert state.material_difference == 1

    # Undo capture
    service.undo_move()
    state_after = service.get_state()
    assert state_after.captured_white == []
    assert state_after.material_difference == 0
    assert service.board.piece_at("d5") == (PieceType.PAWN, Color.BLACK)
    assert service.board.piece_at("e4") == (PieceType.PAWN, Color.WHITE)


def test_undo_when_not_allowed() -> None:
    """Verify undo cannot be performed on empty board or finished game."""
    service = GameService()
    assert service.can_undo is False
    assert service.undo_move() is False


def test_resign_game() -> None:
    """Verify resignation announces opponent win and terminates game."""
    service = GameService()
    service.try_move("e2", "e4")

    game_over_signals = []
    service.game_over.connect(lambda s, m: game_over_signals.append((s, m)))

    # Black resigns
    success = service.resign(Color.BLACK)
    assert success is True
    assert service.get_state().status == GameStatus.RESIGNED
    assert len(game_over_signals) == 1
    assert "White wins" in game_over_signals[0][1]

    # Cannot resign again
    assert service.resign(Color.WHITE) is False


def test_accept_draw() -> None:
    """Verify mutual draw agreement terminates game."""
    service = GameService()
    service.try_move("e2", "e4")
    service.try_move("e7", "e5")

    success = service.accept_draw()
    assert success is True
    assert service.get_state().status == GameStatus.DRAW_AGREED
    assert service.get_state().status.is_draw is True


def test_move_navigation_and_review_mode() -> None:
    """Verify historical navigation sets review mode and produces accurate board snapshots."""
    service = GameService()
    service.try_move("e2", "e4")  # ply 1
    service.try_move("e7", "e5")  # ply 2
    service.try_move("g1", "f3")  # ply 3
    service.try_move("b8", "c6")  # ply 4

    assert not service.is_reviewing
    assert service.current_ply == 4

    # Navigate to ply 2 (after 1... e5)
    service.navigate_to_ply(2)
    assert service.is_reviewing is True
    assert service.current_ply == 2
    assert service.display_board.piece_at("f3") is None  # Knight not moved yet at ply 2
    assert service.display_board.piece_at("e5") == (PieceType.PAWN, Color.BLACK)

    # Step backward to ply 1
    service.step_backward()
    assert service.current_ply == 1
    assert service.display_board.piece_at("e5") is None

    # Step forward to ply 2
    service.step_forward()
    assert service.current_ply == 2

    # Jump to start
    service.go_to_start()
    assert service.current_ply == 0
    assert service.display_board.piece_at("e4") is None

    # Jump to live
    service.go_to_live()
    assert not service.is_reviewing
    assert service.current_ply == 4
    assert service.display_board.piece_at("c6") == (PieceType.KNIGHT, Color.BLACK)


def test_branching_at_historical_ply() -> None:
    """Verify playing from an earlier ply truncates future moves and starts a new line."""
    service = GameService()
    service.try_move("e2", "e4")  # ply 1
    service.try_move("e7", "e5")  # ply 2
    service.try_move("g1", "f3")  # ply 3
    service.try_move("b8", "c6")  # ply 4

    # Review back to ply 2 (after 1... e5)
    service.navigate_to_ply(2)
    assert service.is_reviewing is True

    # Branch with 2. d4 instead of 2. Nf3
    success = service.branch_at_current_ply("d2", "d4")
    assert success is True
    assert not service.is_reviewing

    state = service.get_state()
    assert len(state.moves) == 3
    assert state.moves[0].san == "e4"
    assert state.moves[1].san == "e5"
    assert state.moves[2].san == "d4"
    assert service.board.piece_at("f3") is None
    assert service.board.piece_at("d4") == (PieceType.PAWN, Color.WHITE)
