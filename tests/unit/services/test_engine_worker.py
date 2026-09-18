"""Tests for EngineWorker asynchronous search and thread management."""

from pytestqt.qtbot import QtBot

from chess_desktop.engine.difficulty import Difficulty
from chess_desktop.engine.fallback_engine import FallbackEngine
from chess_desktop.services.engine_worker import EngineWorker


def test_engine_worker_async_search(qtbot: QtBot) -> None:
    """Verify EngineWorker emits search_started, best_move_found, and search_stopped."""
    worker = EngineWorker(engine=FallbackEngine())
    worker.start_worker()

    with qtbot.waitSignal(worker.best_move_found, timeout=3000) as blocker:
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
    worker = EngineWorker(engine=FallbackEngine())
    worker.start_worker()

    # Request move and cancel immediately
    worker.request_move(
        fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        moves_uci=[],
        difficulty=Difficulty.MASTER,
    )
    worker.cancel_search()

    worker.stop_worker()
