"""Unit tests for GameService."""

from chess_desktop.chess.board import ChessBoard
from chess_desktop.domain.enums import Color, PieceType, PlayerType
from chess_desktop.domain.game_state import GameState, MoveRecord
from chess_desktop.services.game_service import GameService


def test_game_service_new_game() -> None:
    """Verify new game initialization."""
    service = GameService()
    state = service.get_state()

    assert state.turn == Color.WHITE
    assert state.move_number == 1
    assert not state.in_check
    assert not state.status.is_game_over
    assert state.moves == []


def test_game_service_make_move() -> None:
    """Verify making a legal move updates state and emits signals."""
    service = GameService()
    service.new_game("White", "Black", PlayerType.HUMAN, PlayerType.HUMAN)
    received_records: list[MoveRecord] = []
    received_states: list[GameState] = []

    service.move_made.connect(received_records.append)
    service.state_changed.connect(received_states.append)

    success = service.try_move("e2", "e4")
    assert success is True
    assert len(received_records) == 1
    assert received_records[0].san == "e4"
    assert len(received_states) == 1
    assert received_states[0].turn == Color.BLACK
    assert received_states[0].last_move == ("e2", "e4")
    service.cleanup()


def test_game_service_illegal_move() -> None:
    """Verify illegal move is rejected without state change."""
    service = GameService()
    success = service.try_move("e2", "e5")  # Illegal pawn move
    assert success is False
    assert service.get_state().turn == Color.WHITE
    assert service.get_state().moves == []
    service.cleanup()


def test_game_service_promotion_request() -> None:
    """Verify promotion signal is emitted when pawn reaches 8th rank."""
    service = GameService()
    # Set up board with white pawn ready to promote on a7
    service._board = ChessBoard("8/P7/8/8/8/8/8/k1K5 w - - 0 1")

    promotions_requested: list[tuple[str, str]] = []
    service.promotion_requested.connect(lambda f, t: promotions_requested.append((f, t)))

    # Attempting move without promotion piece should emit signal and return False
    success = service.try_move("a7", "a8")
    assert success is False
    assert promotions_requested == [("a7", "a8")]

    # Now attempt with promotion piece
    success = service.try_move("a7", "a8", promotion=PieceType.QUEEN)
    assert success is True
    assert service.get_state().moves[-1].san == "a8=Q#"
    service.cleanup()


def test_game_service_board_flip() -> None:
    """Verify flip board toggles orientation."""
    service = GameService()
    assert service.is_flipped is False

    flips: list[bool] = []
    service.board_flipped.connect(flips.append)

    service.flip_board()
    assert service.is_flipped is True
    assert flips == [True]

    service.flip_board()
    assert service.is_flipped is False
    assert flips == [True, False]
    service.cleanup()
