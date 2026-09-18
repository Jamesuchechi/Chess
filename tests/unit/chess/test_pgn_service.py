"""Tests for standard PGN import and export."""

import pytest

from chess_desktop.chess.board import ChessBoard
from chess_desktop.chess.move_service import MoveService
from chess_desktop.chess.pgn_service import PgnService
from chess_desktop.domain.enums import Color, GameStatus
from chess_desktop.domain.game import Game
from chess_desktop.domain.player import Player


def test_pgn_export_standard_game() -> None:
    """Verify exporting a game produces valid Seven Tag Roster and SAN movetext."""
    board = ChessBoard()
    moves = [
        MoveService.execute_move(board, "e2", "e4"),
        MoveService.execute_move(board, "e7", "e5"),
        MoveService.execute_move(board, "d1", "h5"),
        MoveService.execute_move(board, "b8", "c6"),
        MoveService.execute_move(board, "f1", "c4"),
        MoveService.execute_move(board, "g8", "f6"),
        MoveService.execute_move(board, "h5", "f7"),  # Scholar's mate
    ]
    state = MoveService.build_game_state(board, ("h5", "f7"), moves)
    assert state.status == GameStatus.CHECKMATE

    game = Game(
        white_player=Player("Magnus", Color.WHITE),
        black_player=Player("Hikaru", Color.BLACK),
        state=state,
    )

    pgn = PgnService.export_to_pgn(game, event="World Championship", site="Online")
    assert '[Event "World Championship"]' in pgn
    assert '[Site "Online"]' in pgn
    assert '[White "Magnus"]' in pgn
    assert '[Black "Hikaru"]' in pgn
    assert '[Result "1-0"]' in pgn
    assert "1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7#" in pgn


def test_pgn_import_valid_game() -> None:
    """Verify importing PGN string reconstructs complete domain Game."""
    sample_pgn = """
[Event "F/S Return Match"]
[Site "Belgrade, Serbia JUG"]
[Date "1992.11.04"]
[Round "29"]
[White "Fischer, Robert J."]
[Black "Spassky, Boris V."]
[Result "1/2-1/2"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 1/2-1/2
"""
    game = PgnService.import_from_pgn(sample_pgn)

    assert game.white_player.name == "Fischer, Robert J."
    assert game.black_player.name == "Spassky, Boris V."
    assert len(game.state.moves) == 10
    assert game.state.moves[0].san == "e4"
    assert game.state.moves[9].san == "Be7"
    assert game.state.status == GameStatus.DRAW_AGREED


def test_pgn_import_invalid_input() -> None:
    """Verify malformed or empty PGN raises ValueError."""
    with pytest.raises(ValueError, match="empty"):
        PgnService.import_from_pgn("")

    with pytest.raises(ValueError):
        PgnService.import_from_pgn("1. NotAValidMoveAtAll")
