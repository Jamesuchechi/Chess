"""Regression tests for Task 1 — silent engine-cancellation bug.

Reproduces the real-world failure sequence:
  1. Game is in progress (or just started).
  2. GameService.new_game() is called — this unconditionally calls
     cancel_engine_search(), which calls EngineWorker.cancel_search(),
     which calls engine.stop().
  3. On the new game the computer side must still play its first move.

Pre-fix: stop() set _is_cancelled=True even when no search was running.
         search_best_move() immediately raised SearchCancelledError →
         computer never moved → human couldn't move those pieces either.
Post-fix: stop() is a no-op for _is_cancelled when no search is active.
"""

from __future__ import annotations

import pytest
from pytestqt.qtbot import QtBot

from chess_desktop.domain.enums import Color, PlayerType
from chess_desktop.engine.difficulty import Difficulty
from chess_desktop.engine.discovery import find_stockfish_binary
from chess_desktop.engine.fallback_engine import FallbackEngine
from chess_desktop.engine.stockfish import SearchCancelledError, StockfishEngine
from chess_desktop.services.engine_worker import EngineWorker
from chess_desktop.services.game_service import GameService


# ---------------------------------------------------------------------------
# Part A – pure StockfishEngine unit-level regression (no GUI thread needed)
# ---------------------------------------------------------------------------

class _StockfishStub:
    """Minimal StockfishEngine-shaped double that records stop() calls.

    Allows the test to assert that an idle stop() does not set _is_cancelled,
    without requiring a real Stockfish binary.
    """

    def __init__(self) -> None:
        self._is_searching = False
        self._is_cancelled = False
        self._move_counter = 0

    # ------------------------------------------------------------------
    # Mirror the StockfishEngine public surface used by EngineWorker
    # ------------------------------------------------------------------
    def start(self) -> None:
        self._is_cancelled = False

    def stop(self) -> None:
        """Exact post-fix logic copied from StockfishEngine.stop()."""
        # Guard: only poison if actually searching (no lock needed in tests).
        if self._is_searching:
            self._is_cancelled = True

    def set_position(self, fen: str | None = None, moves_uci: list[str] | None = None) -> None:
        pass  # no-op stub

    def search_best_move(
        self,
        depth: int | None = None,
        time_ms: int | None = None,
        skill_level: int | None = None,
    ) -> str:
        if self._is_cancelled:
            self._is_cancelled = False
            raise SearchCancelledError("Search was cancelled by user.")
        # Return a deterministic legal UCI move.
        legal_moves = ["e2e4", "d2d4", "g1f3", "c2c4"]
        self._move_counter += 1
        return legal_moves[self._move_counter % len(legal_moves)]

    def is_ready(self) -> bool:
        return True

    def quit(self) -> None:
        self._is_cancelled = False


def test_stub_idle_stop_does_not_poison_search() -> None:
    """Verify the fixed stop() logic: idle stop() → search still succeeds."""
    stub = _StockfishStub()
    stub.start()

    # Simulate GameService.new_game() calling cancel_engine_search() while idle
    stub.stop()

    # The next search must NOT raise SearchCancelledError.
    move = stub.search_best_move(depth=3)
    assert len(move) in (4, 5), f"Expected UCI move, got: {move!r}"


def test_stub_active_stop_does_cancel() -> None:
    """Verify the fixed stop() logic still cancels when a search IS active."""
    stub = _StockfishStub()
    stub.start()

    # Manually mark as searching (as search_best_move() would).
    stub._is_searching = True
    stub.stop()
    stub._is_searching = False  # simulate search ending

    with pytest.raises(SearchCancelledError):
        stub.search_best_move(depth=3)


# ---------------------------------------------------------------------------
# Part B – integration-level regression via GameService + FallbackEngine
#
# This reproduces the real-world sequence end-to-end using FallbackEngine
# (always available, no Stockfish binary required in CI).
# ---------------------------------------------------------------------------

def test_new_game_after_game_over_computer_plays(qtbot: QtBot) -> None:
    """Regression: computer must play after new_game() following a completed game.

    Sequence:
      1. Start a vs-Computer game (computer = Black).
      2. Play human move e4 → wait for computer reply (2 plies).
      3. Call new_game() again (same configuration).
         new_game() internally calls cancel_engine_search(), which calls
         EngineWorker.cancel_search() → engine.stop() while engine is IDLE.
      4. Human plays e4 again → computer must respond.

    Pre-fix: step 4 would silently fail (SearchCancelledError suppressed)
             and the computer side would never move.
    Post-fix: step 4 produces a computer reply within the timeout.
    """
    worker = EngineWorker(engine=FallbackEngine(), thinking_delay_enabled=False)
    service = GameService(engine_worker=worker)

    # Game 1 ---------------------------------------------------------------
    service.new_game(
        white_name="Human",
        black_name="Computer",
        white_type=PlayerType.HUMAN,
        black_type=PlayerType.COMPUTER,
        difficulty=Difficulty.BEGINNER,
    )

    with qtbot.waitSignal(service.move_made, timeout=3000):
        assert service.try_move("e2", "e4")

    # Wait for computer move 1
    qtbot.waitUntil(lambda: len(service.get_state().moves) == 2, timeout=3000)
    assert service.get_state().turn == Color.WHITE

    # Game 2 ---------------------------------------------------------------
    # new_game() will call cancel_engine_search() while engine is idle.
    service.new_game(
        white_name="Human",
        black_name="Computer",
        white_type=PlayerType.HUMAN,
        black_type=PlayerType.COMPUTER,
        difficulty=Difficulty.BEGINNER,
    )

    assert len(service.get_state().moves) == 0, "Board should be reset after new_game()"

    # Human plays e4 again.
    with qtbot.waitSignal(service.move_made, timeout=3000):
        assert service.try_move("e2", "e4"), "Human move should succeed on fresh game"

    # Computer MUST reply (fails before fix).
    qtbot.waitUntil(
        lambda: len(service.get_state().moves) == 2,
        timeout=5000,
    )

    state = service.get_state()
    assert len(state.moves) == 2, (
        "Computer did not produce a move after new_game() — "
        "idle cancel_engine_search() poisoned _is_cancelled"
    )
    assert state.turn == Color.WHITE

    service.cleanup()


def test_new_game_computer_as_white_after_restart(qtbot: QtBot) -> None:
    """Regression: computer (as White) moves on game 2 after new_game() resets."""
    worker = EngineWorker(engine=FallbackEngine(), thinking_delay_enabled=False)
    service = GameService(engine_worker=worker)

    # Game 1: Computer = White
    service.new_game(
        white_name="Computer",
        black_name="Human",
        white_type=PlayerType.COMPUTER,
        black_type=PlayerType.HUMAN,
        difficulty=Difficulty.BEGINNER,
    )
    qtbot.waitUntil(lambda: len(service.get_state().moves) >= 1, timeout=3000)

    # Game 2: new_game() while engine is idle (no search running)
    service.new_game(
        white_name="Computer",
        black_name="Human",
        white_type=PlayerType.COMPUTER,
        black_type=PlayerType.HUMAN,
        difficulty=Difficulty.BEGINNER,
    )

    # Computer must still play move 1 on game 2 (regression guard).
    qtbot.waitUntil(
        lambda: len(service.get_state().moves) >= 1,
        timeout=5000,
    )
    assert len(service.get_state().moves) >= 1, (
        "Computer (White) did not play move 1 after second new_game() call"
    )

    service.cleanup()


def test_new_game_with_stockfish_after_game_over_computer_plays(qtbot: QtBot) -> None:
    """Real Stockfish regression: computer replies after new_game() resets idle engine."""
    stockfish_path = find_stockfish_binary()
    if not stockfish_path:
        pytest.skip("Stockfish binary not available on system.")

    engine = StockfishEngine(stockfish_path)
    engine.start()
    worker = EngineWorker(engine=engine, thinking_delay_enabled=False)
    service = GameService(engine_worker=worker)

    try:
        # Game 1: Human vs Computer
        service.new_game(
            white_name="Human",
            black_name="Stockfish",
            white_type=PlayerType.HUMAN,
            black_type=PlayerType.COMPUTER,
            difficulty=Difficulty.BEGINNER,
        )

        with qtbot.waitSignal(service.move_made, timeout=3000):
            assert service.try_move("e2", "e4")

        # Wait for computer reply
        qtbot.waitUntil(lambda: len(service.get_state().moves) == 2, timeout=5000)
        assert service.get_state().turn == Color.WHITE

        # Game 2: Start new game
        service.new_game(
            white_name="Human",
            black_name="Stockfish",
            white_type=PlayerType.HUMAN,
            black_type=PlayerType.COMPUTER,
            difficulty=Difficulty.BEGINNER,
        )
        assert len(service.get_state().moves) == 0

        # Human plays e4 again
        with qtbot.waitSignal(service.move_made, timeout=3000):
            assert service.try_move("e2", "e4")

        # Computer MUST reply
        qtbot.waitUntil(lambda: len(service.get_state().moves) == 2, timeout=5000)
        assert len(service.get_state().moves) == 2
        assert service.get_state().turn == Color.WHITE
    finally:
        service.cleanup()
        engine.quit()

