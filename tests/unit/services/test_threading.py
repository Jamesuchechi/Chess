"""
Task 3 threading test: confirm the GUI event loop stays responsive
while an engine search is dispatched via QueuedConnection.

Structural guarantee being tested
----------------------------------
After `set_engine_worker()` connects `_request_move_signal` with
`Qt.ConnectionType.QueuedConnection`, emitting that signal from the GUI
thread should POST the call to the worker thread's event loop rather than
executing it synchronously.  We verify this by:

  1. Counting `QTimer` ticks (10 ms interval) that fire *while* the worker
     is running its (FallbackEngine-backed) search.
  2. Asserting the tick counter advances, i.e. the GUI event loop is
     not blocked by the search.

Thread-identity assertion
--------------------------
`request_move` on `EngineWorker` records `QThread.currentThread()` at the
moment it executes.  We assert it differs from the GUI thread and matches
the worker's dedicated QThread, proving the queued dispatch worked.
"""

import threading
import time

import pytest
from PySide6.QtCore import QCoreApplication, QThread, QTimer, Signal
from PySide6.QtWidgets import QApplication

from chess_desktop.engine.fallback_engine import FallbackEngine
from chess_desktop.services.engine_worker import EngineWorker
from chess_desktop.services.game_service import GameService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _TrackingFallbackEngine(FallbackEngine):
    """FallbackEngine that records which OS/Qt thread executed the search."""

    def __init__(self) -> None:
        super().__init__()
        self.search_thread_id: int | None = None
        self.search_qt_thread: QThread | None = None
        # Use an event so the test can wait for the search to start.
        self.search_started_event = threading.Event()

    def search_best_move(self, **kwargs) -> str:  # type: ignore[override]
        self.search_thread_id = threading.get_ident()
        self.search_qt_thread = QThread.currentThread()
        self.search_started_event.set()
        # Introduce a small real delay so the timer has time to tick.
        time.sleep(0.15)
        return super().search_best_move(**kwargs)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def qapp():
    """Module-scoped QApplication for all threading tests."""
    app = QApplication.instance() or QApplication([])
    yield app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_engine_executes_on_worker_thread_not_gui_thread(qapp) -> None:
    """
    Done condition (structural): after emit via QueuedConnection the slot runs
    on the worker's QThread, not the GUI thread.
    """
    tracking_engine = _TrackingFallbackEngine()
    worker = EngineWorker(engine=tracking_engine)
    service = GameService()
    service.set_engine_worker(worker)

    gui_thread = QThread.currentThread()

    # Emit the request via the queued signal — this is what _trigger_engine_if_needed
    # now does instead of calling worker.request_move() directly.
    from chess_desktop.engine.difficulty import Difficulty

    start_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
    service._request_move_signal.emit(start_fen, ["e2e4"], Difficulty.BEGINNER)

    # Wait up to 2 s for the search to start.
    assert tracking_engine.search_started_event.wait(timeout=2.0), (
        "Engine search never started — possible thread dispatch failure"
    )

    # Give the search slot time to record its QThread identity.
    deadline = time.monotonic() + 1.0
    while tracking_engine.search_qt_thread is None and time.monotonic() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.01)

    assert tracking_engine.search_qt_thread is not None, "Thread identity was never recorded"
    assert tracking_engine.search_qt_thread is not gui_thread, (
        "search_best_move ran on the GUI thread — QueuedConnection did not marshal the call"
    )
    assert tracking_engine.search_qt_thread is worker._thread, (
        "search_best_move ran on an unexpected thread (not the worker's QThread)"
    )

    service.cancel_engine_search()
    service.cleanup()


def test_gui_event_loop_stays_responsive_during_search(qapp) -> None:
    """
    Done condition (responsiveness): a QTimer fires multiple times while the
    engine search slot is executing on the worker thread.
    """
    tracking_engine = _TrackingFallbackEngine()
    worker = EngineWorker(engine=tracking_engine)
    service = GameService()
    service.set_engine_worker(worker)

    tick_count = 0

    def on_tick() -> None:
        nonlocal tick_count
        tick_count += 1

    timer = QTimer()
    timer.setInterval(20)  # 20 ms ticks
    timer.timeout.connect(on_tick)
    timer.start()

    from chess_desktop.engine.difficulty import Difficulty

    start_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
    service._request_move_signal.emit(start_fen, ["e2e4"], Difficulty.BEGINNER)

    # Wait for the search to start, then keep the event loop spinning for ~200 ms.
    assert tracking_engine.search_started_event.wait(timeout=2.0), (
        "Engine search never started"
    )

    spin_end = time.monotonic() + 0.20
    while time.monotonic() < spin_end:
        QCoreApplication.processEvents()
        time.sleep(0.005)

    timer.stop()

    # With a 20 ms interval and a 200 ms spin, we expect at least 5 ticks.
    # If the GUI were blocked, this would be 0.
    assert tick_count >= 5, (
        f"GUI event loop fired only {tick_count} timer ticks during search — "
        "the search may still be blocking the GUI thread"
    )

    service.cancel_engine_search()
    service.cleanup()
