"""Tests for Player vs Computer gameplay orchestration in GameService."""

from pytestqt.qtbot import QtBot

from chess_desktop.domain.enums import Color, PlayerType
from chess_desktop.engine.difficulty import Difficulty
from chess_desktop.engine.fallback_engine import FallbackEngine
from chess_desktop.services.engine_worker import EngineWorker
from chess_desktop.services.game_service import GameService


def test_vs_computer_reply_and_two_ply_undo(qtbot: QtBot) -> None:
    """Verify computer automatically replies to human move and undo rewinds 2 plies."""
    worker = EngineWorker(engine=FallbackEngine(), thinking_delay_enabled=False)
    service = GameService(engine_worker=worker)

    service.new_game(
        white_name="Human",
        black_name="Computer",
        white_type=PlayerType.HUMAN,
        black_type=PlayerType.COMPUTER,
        difficulty=Difficulty.BEGINNER,
    )
    assert service.is_vs_computer

    # Human plays move 1: e4
    with qtbot.waitSignal(service.move_made, timeout=3000):
        # Human plays e4, triggers computer reply
        assert service.try_move("e2", "e4")

    # Wait for computer move signal
    qtbot.waitUntil(lambda: len(service.get_state().moves) == 2, timeout=3000)

    state = service.get_state()
    assert len(state.moves) == 2
    assert state.turn == Color.WHITE

    # Test 2-ply undo: rewinds computer move + human move back to start
    assert service.undo_move() is True
    assert len(service.get_state().moves) == 0
    assert service.get_state().turn == Color.WHITE
    service.cleanup()


def test_vs_computer_as_white(qtbot: QtBot) -> None:
    """Verify when Computer is White, it plays move 1 automatically."""
    worker = EngineWorker(engine=FallbackEngine(), thinking_delay_enabled=False)
    service = GameService(engine_worker=worker)

    service.new_game(
        white_name="Computer",
        black_name="Human",
        white_type=PlayerType.COMPUTER,
        black_type=PlayerType.HUMAN,
        difficulty=Difficulty.BEGINNER,
    )

    # Wait for computer move 1
    qtbot.waitUntil(lambda: len(service.get_state().moves) == 1, timeout=3000)
    assert service.get_state().turn == Color.BLACK
    service.cleanup()


def test_vs_computer_blocks_move_during_thinking(qtbot: QtBot) -> None:
    """Verify human cannot play a move while computer is computing its reply."""
    worker = EngineWorker(engine=FallbackEngine(), thinking_delay_enabled=False)
    service = GameService(engine_worker=worker)

    service.new_game(
        white_name="Human",
        black_name="Computer",
        white_type=PlayerType.HUMAN,
        black_type=PlayerType.COMPUTER,
    )

    # Manually simulate engine thinking flag
    service._is_engine_thinking = True
    assert service.try_move("e2", "e4") is False

    service._is_engine_thinking = False
    service.cleanup()


def test_vs_computer_propagates_engine_error(qtbot: QtBot) -> None:
    """Verify GameService re-emits engine_error and clears thinking state."""
    class FailingEngine(FallbackEngine):
        def search_best_move(self, *args, **kwargs) -> str:
            raise RuntimeError("Engine process died")

    worker = EngineWorker(engine=FailingEngine(), thinking_delay_enabled=False)
    service = GameService(engine_worker=worker)

    with qtbot.waitSignal(service.engine_error, timeout=1000) as blocker:
        service.new_game(
            white_name="Human",
            black_name="Computer",
            white_type=PlayerType.HUMAN,
            black_type=PlayerType.COMPUTER,
        )
        assert service.try_move("e2", "e4")

    assert blocker.args is not None
    assert "Engine process died" in blocker.args[0]
    assert not service.is_computer_thinking
    service.cleanup()


def test_vs_computer_restart_engine(qtbot: QtBot) -> None:
    """Verify GameService.restart_engine restores engine and triggers move if computer turn."""
    engine = FallbackEngine()
    worker = EngineWorker(engine=engine, thinking_delay_enabled=False)
    service = GameService(engine_worker=worker)

    service.new_game(
        white_name="Computer",
        black_name="Human",
        white_type=PlayerType.COMPUTER,
        black_type=PlayerType.HUMAN,
    )

    qtbot.waitUntil(lambda: len(service.get_state().moves) >= 1, timeout=3000)
    service.restart_engine()
    assert engine.is_ready()
    service.cleanup()

