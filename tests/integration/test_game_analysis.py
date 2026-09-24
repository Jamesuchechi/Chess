"""Integration test for game review analysis and SQLite cache persistence.

Verifies:
1. Analysis runs on a short scripted game (Fool's Mate).
2. Each move gets a classification.
3. Cache round-trips through SQLite via AnalysisRepository.
4. Cached analysis is served on subsequent requests without re-evaluating.
"""

import time
import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from chess_desktop.domain.analysis import GameAnalysis, MoveClassification
from chess_desktop.engine.fallback_engine import FallbackEngine
from chess_desktop.persistence.database import DatabaseManager
from chess_desktop.persistence.repositories import AnalysisRepository
from chess_desktop.services.analysis_service import AnalysisService, AnalysisWorker


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_analysis_runs_on_scripted_game_and_caches_in_sqlite(qapp, tmp_path):
    """Run analysis on Fool's Mate, check classification, and verify SQLite round-trip."""
    db_file = tmp_path / "test_chess.db"
    db = DatabaseManager(str(db_file))
    repo = AnalysisRepository(db)

    # Scripted 4-ply game (Fool's Mate: 1. f3 e5 2. g4 Qh4#)
    game_id = "test-fools-mate-game"
    moves_uci = ["f2f3", "e7e5", "g2g4", "d8h4"]

    engine = FallbackEngine()
    service = AnalysisService(engine=engine, db=db)

    received_analysis: list[GameAnalysis] = []
    service.analysis_complete.connect(lambda ga: received_analysis.append(ga))

    # Request analysis
    service.request_analysis(game_id, moves_uci, depth=6)

    # Process Qt event loop until complete
    timeout = 10.0
    start = time.time()
    while not received_analysis and (time.time() - start) < timeout:
        QCoreApplication.processEvents()
        time.sleep(0.02)

    assert len(received_analysis) == 1, "Analysis did not complete in time"
    analysis = received_analysis[0]

    # Verify each move got a classification
    assert analysis.game_id == game_id
    assert len(analysis.moves) == 4
    for ply_idx, m in enumerate(analysis.moves, start=1):
        assert m.ply == ply_idx
        assert m.played_uci == moves_uci[ply_idx - 1]
        assert isinstance(m.classification, MoveClassification)

    # Verify accuracy percentages are computed
    assert 0.0 <= analysis.white_accuracy <= 100.0
    assert 0.0 <= analysis.black_accuracy <= 100.0

    # Verify SQLite cache round-trip directly from repository
    assert repo.exists(game_id)
    cached = repo.get(game_id)
    assert cached is not None
    assert cached.game_id == game_id
    assert len(cached.moves) == 4
    assert cached.white_accuracy == analysis.white_accuracy
    assert cached.black_accuracy == analysis.black_accuracy

    # Clean up service worker thread
    service.cleanup()


def test_analysis_service_serves_from_cache(qapp, tmp_path):
    """If analysis is already cached, request_analysis returns it immediately without worker."""
    db_file = tmp_path / "test_cache.db"
    db = DatabaseManager(str(db_file))
    repo = AnalysisRepository(db)

    game_id = "cached-game-123"
    precomputed = GameAnalysis(
        game_id=game_id,
        moves=[],
        white_accuracy=88.5,
        black_accuracy=91.0,
    )
    repo.save(precomputed)

    engine = FallbackEngine()
    service = AnalysisService(engine=engine, db=db)

    received: list[GameAnalysis] = []
    service.analysis_complete.connect(lambda ga: received.append(ga))

    service.request_analysis(game_id, ["e2e4"])

    # Should be delivered immediately (emitted directly in request_analysis)
    QCoreApplication.processEvents()
    assert len(received) == 1
    assert received[0].white_accuracy == 88.5

    service.cleanup()
