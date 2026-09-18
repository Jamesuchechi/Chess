"""Tests for default Play vs Computer game mode mirroring Chess.com."""

from pytestqt.qtbot import QtBot

from chess_desktop.domain.enums import Color, PlayerType
from chess_desktop.engine.difficulty import Difficulty
from chess_desktop.engine.fallback_engine import FallbackEngine
from chess_desktop.services.engine_worker import EngineWorker
from chess_desktop.services.game_service import GameService
from chess_desktop.ui.windows.main_window import MainWindow


def test_default_game_is_play_vs_computer() -> None:
    """Verify fresh GameService defaults to Play vs Computer (Player vs Stockfish)."""
    service = GameService()
    game = service.get_game()

    assert service.is_vs_computer is True
    assert game.white_player.name == "Player"
    assert game.white_player.player_type == PlayerType.HUMAN
    assert "Stockfish" in game.black_player.name
    assert game.black_player.player_type == PlayerType.COMPUTER
    assert service.engine_difficulty == Difficulty.INTERMEDIATE
    service.cleanup()


def test_default_game_triggers_computer_reply(qtbot: QtBot) -> None:
    """Verify that playing move 1 in the default game triggers an automatic computer response."""
    worker = EngineWorker(engine=FallbackEngine())
    service = GameService(engine_worker=worker)

    assert service.is_vs_computer is True

    # Human plays move 1: e4
    with qtbot.waitSignal(service.move_made, timeout=3000):
        assert service.try_move("e2", "e4")

    # Wait for computer move 1 reply
    qtbot.waitUntil(lambda: len(service.get_state().moves) == 2, timeout=3000)

    state = service.get_state()
    assert len(state.moves) == 2
    assert state.turn == Color.WHITE
    service.cleanup()


def test_main_window_defaults_to_play_vs_computer(qtbot: QtBot) -> None:
    """Verify MainWindow launches with Play vs Computer enabled by default."""
    window = MainWindow()
    qtbot.addWidget(window)

    service = window.game_service
    assert service.is_vs_computer is True
    assert service.get_game().black_player.player_type == PlayerType.COMPUTER
