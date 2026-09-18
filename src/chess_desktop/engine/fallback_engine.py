"""In-process pure-Python fallback engine for environments without Stockfish."""

import random
import time

import chess

from chess_desktop.engine.engine import ChessEngine


class FallbackEngine(ChessEngine):
    """Pure Python fallback engine that plays legal moves with basic piece-value heuristics."""

    def __init__(self) -> None:
        self._board = chess.Board()
        self._is_running = False
        self._stop_requested = False

    def start(self) -> None:
        """Start the fallback engine."""
        self._is_running = True
        self._stop_requested = False

    def stop(self) -> None:
        """Signal immediate search interruption."""
        self._stop_requested = True

    def set_position(
        self,
        fen: str | None = None,
        moves_uci: list[str] | None = None,
    ) -> None:
        """Set active board position."""
        if moves_uci is not None and len(moves_uci) > 0:
            self._board = chess.Board()
            for uci in moves_uci:
                self._board.push_uci(uci)
        elif fen:
            self._board = chess.Board(fen)
        else:
            self._board = chess.Board()

    def search_best_move(
        self,
        depth: int | None = None,
        time_ms: int | None = None,
        skill_level: int | None = None,
    ) -> str:
        """Pick a move using a lightweight heuristic, respecting time delays and cancel signals."""
        if not self._is_running:
            raise RuntimeError("FallbackEngine is not started.")

        self._stop_requested = False
        legal_moves = list(self._board.legal_moves)
        if not legal_moves:
            raise RuntimeError("No legal moves available.")

        # Simulate slight thinking time (e.g. 50ms)
        delay_sec = min(0.05, (time_ms or 50) / 1000.0)
        time.sleep(delay_sec)

        if self._stop_requested:
            raise RuntimeError("Search was cancelled.")

        # Prioritize captures or checks, fallback to random
        captures = [m for m in legal_moves if self._board.is_capture(m)]
        checks = [m for m in legal_moves if self._board.gives_check(m)]

        if captures and (skill_level or 10) > 3:
            chosen = random.choice(captures)
        elif checks and (skill_level or 10) > 6:
            chosen = random.choice(checks)
        else:
            chosen = random.choice(legal_moves)

        return chosen.uci()

    def is_ready(self) -> bool:
        """Check readiness."""
        return self._is_running

    def quit(self) -> None:
        """Shut down engine."""
        self._is_running = False
        self._stop_requested = True
