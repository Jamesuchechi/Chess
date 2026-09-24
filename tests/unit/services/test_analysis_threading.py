"""Threading test for AnalysisService and AnalysisWorker.

Verifies:
1. Analysis runs on a dedicated background QThread, not the GUI thread.
2. The GUI event loop stays responsive during analysis (QTimer ticks continuously).
"""

import threading
import time
import pytest
from PySide6.QtCore import QCoreApplication, QObject, QThread, QTimer
from PySide6.QtWidgets import QApplication

from chess_desktop.engine.engine import PositionEval
from chess_desktop.engine.fallback_engine import FallbackEngine
from chess_desktop.persistence.database import DatabaseManager
from chess_desktop.services.analysis_service import AnalysisService, AnalysisWorker


class _TrackingAnalysisEngine(FallbackEngine):
    """Engine that records which thread evaluates positions and adds delay."""

    def __init__(self) -> None:
        super().__init__()
        self.eval_qt_thread: QThread | None = None
        self.eval_thread_id: int | None = None
        self.eval_started_event = threading.Event()

    def evaluate_position(self, depth: int = 14, time_ms: int | None = None) -> PositionEval:
        self.eval_thread_id = threading.get_ident()
        self.eval_qt_thread = QThread.currentThread()
        self.eval_started_event.set()
        time.sleep(0.15)  # artificial delay so GUI event loop timer can tick
        return super().evaluate_position(depth=depth, time_ms=time_ms)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_analysis_executes_on_worker_thread_not_gui_thread(qapp, tmp_path):
    """Verify that AnalysisWorker runs on dedicated QThread, not GUI thread."""
    tracking_engine = _TrackingAnalysisEngine()
    db = DatabaseManager(str(tmp_path / "test_th.db"))
    service = AnalysisService(engine=tracking_engine, db=db)

    gui_thread = QThread.currentThread()

    # Request analysis
    service.request_analysis("thread-test-game", ["e2e4", "e7e5"], depth=4)

    # Wait up to 3 seconds for evaluation to start
    assert tracking_engine.eval_started_event.wait(timeout=3.0), (
        "Analysis search never started — possible queued dispatch failure"
    )

    # Allow worker thread time to record thread identity
    timeout = 3.0
    start = time.time()
    while tracking_engine.eval_qt_thread is None and (time.time() - start) < timeout:
        QCoreApplication.processEvents()
        time.sleep(0.01)

    assert tracking_engine.eval_qt_thread is not None
    assert tracking_engine.eval_qt_thread != gui_thread, (
        f"Analysis ran on GUI thread ({gui_thread}) instead of worker thread!"
    )

    service.cleanup()


def test_gui_event_loop_stays_responsive_during_analysis(qapp, tmp_path):
    """Verify that a QTimer continues ticking on GUI thread while analysis is running."""
    tracking_engine = _TrackingAnalysisEngine()
    db = DatabaseManager(str(tmp_path / "test_responsive.db"))
    service = AnalysisService(engine=tracking_engine, db=db)

    timer_ticks = 0

    def on_tick() -> None:
        nonlocal timer_ticks
        timer_ticks += 1

    timer = QTimer()
    timer.setInterval(10)  # tick every 10 ms
    timer.timeout.connect(on_tick)
    timer.start()

    analysis_finished = threading.Event()
    service.analysis_complete.connect(lambda _: analysis_finished.set())

    service.request_analysis("gui-loop-test", ["e2e4", "e7e5", "g1f3"], depth=4)

    timeout = 5.0
    start = time.time()
    while not analysis_finished.is_set() and (time.time() - start) < timeout:
        QCoreApplication.processEvents()
        time.sleep(0.01)

    timer.stop()
    service.cleanup()

    assert analysis_finished.is_set(), "Analysis did not finish within timeout"
    assert timer_ticks >= 5, (
        f"GUI event loop was starved during analysis! Timer only ticked {timer_ticks} times."
    )
