"""Tests for clock state persistence in SQLite and PGN."""

from chess_desktop.chess.pgn_service import PgnService
from chess_desktop.domain.time_control import TimeControl
from chess_desktop.persistence.database import DatabaseManager
from chess_desktop.persistence.repositories import GameRepository
from chess_desktop.services.game_service import GameService


def test_repository_save_and_load_clock_state() -> None:
    """Verify saved game preserves remaining clock milliseconds and time control."""
    db = DatabaseManager(":memory:")
    repo = GameRepository(db)

    service = GameService()
    tc = TimeControl.blitz_3_2()
    service.new_game(time_control=tc)

    service.try_move("e2", "e4")
    # Manually set times
    service.clock.set_times(white_ms=175400, black_ms=180000)

    game = service.get_game()
    game_id = repo.save(game, title="Timed Blitz Battle")

    loaded = repo.get_by_id(game_id)
    assert loaded is not None
    loaded_game, record = loaded

    assert record.white_time_ms == 175400
    assert record.black_time_ms == 180000
    assert record.time_control == "180+2"

    assert loaded_game.state.white_time_ms == 175400
    assert loaded_game.state.black_time_ms == 180000
    assert loaded_game.state.time_control is not None
    assert loaded_game.state.time_control.base_seconds == 180
    assert loaded_game.state.time_control.increment_seconds == 2

    db.close()
    service.cleanup()


def test_pgn_time_control_export_and_import() -> None:
    """Verify exporting and importing PGN with TimeControl header tag."""
    service = GameService()
    tc = TimeControl.rapid_10_5()
    service.new_game(white_name="Magnus", black_name="Hikaru", time_control=tc)

    service.try_move("e2", "e4")
    service.try_move("c7", "c5")

    pgn = PgnService.export_to_pgn(service.get_game())
    assert '[TimeControl "600+5"]' in pgn

    imported = PgnService.import_from_pgn(pgn)
    assert imported.white_player.name == "Magnus"
    assert imported.black_player.name == "Hikaru"
    assert imported.state.time_control is not None
    assert imported.state.time_control.base_seconds == 600
    assert imported.state.time_control.increment_seconds == 5

    service.cleanup()
