"""Unit tests for ChessBoard wrapper."""

import chess

from chess_desktop.chess.board import ChessBoard
from chess_desktop.domain.enums import Color, PieceType


def test_initial_board_setup() -> None:
    """Verify standard initial board position."""
    board = ChessBoard()
    assert board.turn == Color.WHITE
    assert board.fullmove_number == 1
    assert not board.is_check()
    assert not board.is_game_over()
    assert board.piece_at("e1") == (PieceType.KING, Color.WHITE)
    assert board.piece_at("e8") == (PieceType.KING, Color.BLACK)
    assert board.piece_at("e4") is None


def test_king_square_lookup() -> None:
    """Verify king square position is retrieved correctly."""
    board = ChessBoard()
    assert board.king_square(Color.WHITE) == "e1"
    assert board.king_square(Color.BLACK) == "e8"


def test_push_and_pop_move() -> None:
    """Verify pushing and popping moves on the board stack."""
    board = ChessBoard()
    e2_e4 = chess.Move.from_uci("e2e4")
    board.push_move(e2_e4)

    assert board.turn == Color.BLACK
    assert board.piece_at("e4") == (PieceType.PAWN, Color.WHITE)
    assert board.piece_at("e2") is None

    popped = board.pop_move()
    assert popped == e2_e4
    assert board.turn == Color.WHITE
    assert board.piece_at("e2") == (PieceType.PAWN, Color.WHITE)
    assert board.piece_at("e4") is None
