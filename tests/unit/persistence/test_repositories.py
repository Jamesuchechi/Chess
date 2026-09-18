"""Tests for GameRepository CRUD operations and round-trip data fidelity."""

from chess_desktop.chess.board import ChessBoard
from chess_desktop.chess.move_service import MoveService
from chess_desktop.domain.enums import Color
from chess_desktop.domain.game import Game
from chess_desktop.domain.player import Player
from chess_desktop.persistence.database import DatabaseManager
from chess_desktop.persistence.repositories import GameRepository


def _create_sample_game() -> Game:
    board = ChessBoard()
    moves = [
        MoveService.execute_move(board, "e2", "e4"),
        MoveService.execute_move(board, "e7", "e5"),
        MoveService.execute_move(board, "g1", "f3"),
    ]
    state = MoveService.build_game_state(board, ("g1", "f3"), moves)
    return Game(
        white_player=Player("Alice", Color.WHITE),
        black_player=Player("Bob", Color.BLACK),
        state=state,
    )


def test_repository_save_and_get_by_id() -> None:
    """Verify saving a game and reloading it preserves players, moves, and board state."""
    db = DatabaseManager(":memory:")
    repo = GameRepository(db)

    original_game = _create_sample_game()
    game_id = repo.save(original_game, title="Alice vs Bob Round 1")

    result = repo.get_by_id(game_id)
    assert result is not None
    loaded_game, record = result

    assert loaded_game.game_id == original_game.game_id
    assert loaded_game.white_player.name == "Alice"
    assert loaded_game.black_player.name == "Bob"
    assert len(loaded_game.state.moves) == 3
    assert [m.san for m in loaded_game.state.moves] == ["e4", "e5", "Nf3"]
    assert loaded_game.state.fen == original_game.state.fen
    assert record.title == "Alice vs Bob Round 1"
    assert record.result == "*"
    assert record.move_count == 3
    db.close()


def test_repository_update_preserves_created_at() -> None:
    """Verify updating a saved game preserves original created_at timestamp."""
    db = DatabaseManager(":memory:")
    repo = GameRepository(db)

    game = _create_sample_game()
    repo.save(game, title="Version 1")

    first_result = repo.get_by_id(game.game_id)
    assert first_result is not None
    created_at = first_result[1].created_at

    # Add a move and save again
    board = ChessBoard.create_at_ply([m.uci for m in game.state.moves], len(game.state.moves))
    m4 = MoveService.execute_move(board, "b8", "c6")
    updated_moves = list(game.state.moves) + [m4]
    game.state = MoveService.build_game_state(board, ("b8", "c6"), updated_moves)

    repo.save(game, title="Version 2")
    second_result = repo.get_by_id(game.game_id)
    assert second_result is not None
    assert second_result[1].title == "Version 2"
    assert second_result[1].created_at == created_at
    assert second_result[1].move_count == 4
    db.close()


def test_repository_list_and_delete() -> None:
    """Verify list_games returns summaries and delete removes game from SQLite."""
    db = DatabaseManager(":memory:")
    repo = GameRepository(db)

    game1 = _create_sample_game()
    game2 = _create_sample_game()

    repo.save(game1, title="Match 1")
    repo.save(game2, title="Match 2")

    summaries = repo.list_games()
    assert len(summaries) == 2
    titles = [s.title for s in summaries]
    assert "Match 1" in titles
    assert "Match 2" in titles

    assert repo.delete(game1.game_id) is True
    assert repo.get_by_id(game1.game_id) is None
    assert len(repo.list_games()) == 1

    # Deleting non-existent returns False
    assert repo.delete("non_existent_id") is False
    db.close()
