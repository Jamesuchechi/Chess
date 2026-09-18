"""Tests for StockfishEngine UCI process communication."""

import pytest

from chess_desktop.engine.discovery import find_stockfish_binary
from chess_desktop.engine.stockfish import SearchCancelledError, StockfishEngine


@pytest.fixture
def stockfish_path() -> str:
    path = find_stockfish_binary()
    if not path:
        pytest.skip("Stockfish binary not installed on this test runner.")
    return path


def test_stockfish_engine_lifecycle_and_search(stockfish_path: str) -> None:
    """Verify Stockfish starts, responds to isready, calculates best move, and quits."""
    engine = StockfishEngine(stockfish_path)
    engine.start()
    assert engine.is_ready()

    engine.set_position(moves_uci=["e2e4"])
    best_move = engine.search_best_move(depth=3, time_ms=100, skill_level=5)
    assert len(best_move) in (4, 5)

    engine.quit()
    assert not engine.is_ready()


def test_stockfish_engine_cancellation(stockfish_path: str) -> None:
    """Verify calling stop() cancels an active search cleanly."""
    import threading

    engine = StockfishEngine(stockfish_path)
    engine.start()

    engine.set_position(moves_uci=["e2e4", "e7e5"])
    # Trigger stop shortly after search starts
    threading.Timer(0.05, engine.stop).start()

    with pytest.raises(SearchCancelledError):
        engine.search_best_move(depth=25, time_ms=3000)

    engine.quit()
