"""Tests for SaveService state management, saving, loading, and dirty tracking."""

import tempfile
from pathlib import Path

from chess_desktop.domain.enums import PlayerType
from chess_desktop.persistence.database import DatabaseManager
from chess_desktop.persistence.repositories import GameRepository
from chess_desktop.services.game_service import GameService
from chess_desktop.services.save_service import SaveService


def test_save_service_dirty_tracking() -> None:
    """Verify moves make service dirty and saving marks it clean."""
    db = DatabaseManager(":memory:")
    repo = GameRepository(db)
    game_service = GameService()
    game_service.new_game("White", "Black", PlayerType.HUMAN, PlayerType.HUMAN)
    save_service = SaveService(game_service, repository=repo)

    assert not save_service.has_unsaved_changes

    # Play move
    assert game_service.try_move("e2", "e4")
    assert save_service.has_unsaved_changes

    # Save as
    game_id = save_service.save_as("Test Game")
    assert not save_service.has_unsaved_changes
    assert save_service.current_game_id == game_id
    assert save_service.current_game_title == "Test Game"

    # Play another move
    assert game_service.try_move("e7", "e5")
    assert save_service.has_unsaved_changes

    # Quick save
    saved_id = save_service.save()
    assert saved_id == game_id
    assert not save_service.has_unsaved_changes
    db.close()
    game_service.cleanup()


def test_save_service_load_game() -> None:
    """Verify SaveService loads saved game into GameService correctly."""
    db = DatabaseManager(":memory:")
    repo = GameRepository(db)
    game_service = GameService()
    game_service.new_game("White", "Black", PlayerType.HUMAN, PlayerType.HUMAN)
    save_service = SaveService(game_service, repository=repo)

    # Play moves and save
    game_service.try_move("d2", "d4")
    game_service.try_move("d7", "d5")
    game_id = save_service.save_as("Queen's Pawn")

    # Start brand new game
    game_service.new_game("Player1", "Player2", PlayerType.HUMAN, PlayerType.HUMAN)
    save_service.reset_tracking()
    assert len(game_service.get_state().moves) == 0

    # Load previously saved game
    success = save_service.load_game(game_id)
    assert success is True
    assert len(game_service.get_state().moves) == 2
    assert [m.san for m in game_service.get_state().moves] == ["d4", "d5"]
    assert save_service.current_game_id == game_id
    assert save_service.current_game_title == "Queen's Pawn"
    assert not save_service.has_unsaved_changes
    db.close()
    game_service.cleanup()


def test_save_service_export_and_import_pgn_file() -> None:
    """Verify exporting and re-importing PGN file via SaveService."""
    db = DatabaseManager(":memory:")
    repo = GameRepository(db)
    game_service = GameService()
    game_service.new_game("White", "Black", PlayerType.HUMAN, PlayerType.HUMAN)
    save_service = SaveService(game_service, repository=repo)

    game_service.try_move("e2", "e4")
    game_service.try_move("c7", "c5")

    with tempfile.TemporaryDirectory() as tmp_dir:
        pgn_path = str(Path(tmp_dir) / "sicilian.pgn")
        save_service.export_pgn_file(pgn_path)

        assert Path(pgn_path).exists()

        # Reset to new game
        game_service.new_game("White", "Black", PlayerType.HUMAN, PlayerType.HUMAN)
        assert len(game_service.get_state().moves) == 0

        # Import PGN
        assert save_service.import_pgn_file(pgn_path) is True
        assert len(game_service.get_state().moves) == 2
        assert [m.san for m in game_service.get_state().moves] == ["e4", "c5"]
        assert save_service.current_game_title == "sicilian"
        db.close()
        game_service.cleanup()
