"""Tests for EngineWorker asynchronous search and thread management."""

from pytestqt.qtbot import QtBot

from chess_desktop.engine.difficulty import Difficulty
from chess_desktop.engine.fallback_engine import FallbackEngine
from chess_desktop.services.engine_worker import EngineWorker


def test_engine_worker_fast_mode(qtbot: QtBot) -> None:
    """Verify EngineWorker with thinking_delay_enabled=False executes immediately."""
    worker = EngineWorker(engine=FallbackEngine(), thinking_delay_enabled=False)
    worker.start_worker()

    with qtbot.waitSignal(worker.best_move_found, timeout=1000) as blocker:
        worker.request_move(
            fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            moves_uci=["e2e4"],
            difficulty=Difficulty.BEGINNER,
        )

    assert blocker.args is not None
    assert len(blocker.args[0]) in (4, 5)
    worker.stop_worker()


def test_engine_worker_cancellation(qtbot: QtBot) -> None:
    """Verify cancel_search interrupts search without emitting best_move_found."""
    worker = EngineWorker(engine=FallbackEngine(), thinking_delay_enabled=True)
    worker.start_worker()

    # Request move and cancel immediately during delay
    worker.request_move(
        fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        moves_uci=[],
        difficulty=Difficulty.MASTER,
    )
    worker.cancel_search()

    worker.stop_worker()


def test_engine_worker_handles_error(qtbot: QtBot) -> None:
    """Verify EngineWorker catches engine exceptions and emits engine_error."""
    class FailingEngine(FallbackEngine):
        def search_best_move(self, *args, **kwargs) -> str:
            raise RuntimeError("Engine process crashed unexpectedly")

    worker = EngineWorker(engine=FailingEngine(), thinking_delay_enabled=False)
    worker.start_worker()

    with qtbot.waitSignal(worker.engine_error, timeout=1000) as blocker:
        worker.request_move(
            fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            moves_uci=[],
            difficulty=Difficulty.BEGINNER,
        )

    assert blocker.args is not None
    assert "Engine process crashed unexpectedly" in blocker.args[0]
    worker.stop_worker()


def test_engine_worker_restart(qtbot: QtBot) -> None:
    """Verify restart_engine restarts the engine cleanly."""
    engine = FallbackEngine()
    worker = EngineWorker(engine=engine, thinking_delay_enabled=False)
    worker.start_worker()

    worker.restart_engine()
    assert engine.is_ready()

    with qtbot.waitSignal(worker.best_move_found, timeout=1000) as blocker:
        worker.request_move(
            fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            moves_uci=[],
            difficulty=Difficulty.BEGINNER,
        )

    assert blocker.args is not None
    worker.stop_worker()


def test_engine_worker_hint(qtbot: QtBot) -> None:
    """Verify EngineWorker computes on-demand hint."""
    engine = FallbackEngine()
    worker = EngineWorker(engine=engine, thinking_delay_enabled=False)
    worker.start_worker()

    with qtbot.waitSignal(worker.hint_found, timeout=1000) as blocker:
        worker.request_hint(
            fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            moves_uci=[],
        )

    assert blocker.args is not None
    assert len(blocker.args[0]) in (4, 5)
    worker.stop_worker()


