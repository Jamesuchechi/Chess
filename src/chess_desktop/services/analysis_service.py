"""Off-GUI-thread analysis pipeline for post-game move classification.

Architecture:
  AnalysisService emits _request_analysis_signal (QueuedConnection)
      → AnalysisWorker.run_analysis() executes on worker QThread
      → AnalysisWorker.analysis_complete emits back (auto-marshalled to GUI thread)
      → AnalysisService saves to AnalysisRepository and emits to UI
"""

from __future__ import annotations

import logging

import chess
from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot

from chess_desktop.domain.analysis import (
    GameAnalysis,
    MoveAnalysis,
    classify_move,
    compute_accuracy,
    game_analysis_from_json,
    game_analysis_to_json,
)
from chess_desktop.engine.discovery import find_stockfish_binary
from chess_desktop.engine.engine import ChessEngine, PositionEval
from chess_desktop.engine.fallback_engine import FallbackEngine
from chess_desktop.engine.stockfish import SearchCancelledError, StockfishEngine
from chess_desktop.persistence.database import DatabaseManager
from chess_desktop.persistence.repositories import AnalysisRepository

logger = logging.getLogger(__name__)

# Re-export JSON helpers so callers can import from analysis_service if desired
__all__ = [
    "AnalysisService",
    "AnalysisWorker",
    "game_analysis_from_json",
    "game_analysis_to_json",
]


# ---------------------------------------------------------------------------
# Worker (runs on dedicated QThread)
# ---------------------------------------------------------------------------


class AnalysisWorker(QObject):
    """Iterates game positions on a background thread and emits classification results."""

    analysis_started = Signal(str)  # game_id
    analysis_progress = Signal(str, int, int)  # (game_id, done_ply, total_ply)
    analysis_complete = Signal(object)  # GameAnalysis
    analysis_error = Signal(str)

    def __init__(
        self,
        engine: ChessEngine | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        if engine is not None:
            self._engine = engine
        else:
            binary = find_stockfish_binary()
            if binary:
                try:
                    self._engine = StockfishEngine(binary)
                except Exception as e:
                    logger.warning("Stockfish launch failed: %s. Using FallbackEngine.", e)
                    self._engine = FallbackEngine()
            else:
                self._engine = FallbackEngine()

        self._cancelled = False
        self._thread: QThread | None = None
        self._is_started = False

    def start_worker(self) -> None:
        """Start engine and move worker onto a dedicated QThread."""
        if self._is_started:
            return
        try:
            self._engine.start()
        except Exception as e:
            logger.error("AnalysisWorker engine start failed: %s", e)
            return

        self._thread = QThread()
        self.moveToThread(self._thread)
        self._thread.start()
        self._is_started = True
        logger.info("AnalysisWorker started on dedicated QThread.")

    def stop_worker(self) -> None:
        """Cancel any running analysis and stop the thread."""
        self.cancel()
        try:
            self._engine.quit()
        except Exception:
            pass
        if self._thread is not None:
            thread = self._thread
            self._thread = None
            thread.quit()
            thread.wait(2000)
        self._is_started = False

    def cancel(self) -> None:
        """Cancel current analysis run."""
        self._cancelled = True
        try:
            self._engine.stop()
        except Exception:
            pass

    @Slot(str, list, int)
    def run_analysis(self, game_id: str, moves_uci: list[str], depth: int) -> None:
        """Evaluate each position in the move list and emit analysis_complete.

        Args:
            game_id: Unique game identifier (used for caching lookup).
            moves_uci: Full move list in UCI notation.
            depth: Engine search depth per position.
        """
        self._cancelled = False
        self.analysis_started.emit(game_id)
        total = len(moves_uci)

        board = chess.Board()
        move_analyses: list[MoveAnalysis] = []

        # Evaluate starting position (from White's perspective)
        try:
            self._engine.set_position(fen=board.fen())
            eval_before: PositionEval = self._engine.evaluate_position(depth=depth, time_ms=500)
        except SearchCancelledError:
            logger.debug("Analysis cancelled at start.")
            return
        except Exception as e:
            logger.error("AnalysisWorker: failed to evaluate starting position: %s", e)
            self.analysis_error.emit(str(e))
            return

        for ply_idx, uci in enumerate(moves_uci, start=1):
            if self._cancelled:
                logger.debug("Analysis cancelled at ply %d.", ply_idx)
                return

            try:
                move = chess.Move.from_uci(uci)
            except Exception as e:
                logger.error("AnalysisWorker: invalid UCI '%s' at ply %d: %s", uci, ply_idx, e)
                continue

            # Convert best move to SAN while board is in pre-move state
            best_san: str | None = None
            if eval_before.best_move_uci:
                try:
                    best_move_obj = chess.Move.from_uci(eval_before.best_move_uci)
                    if best_move_obj in board.legal_moves:
                        best_san = board.san(best_move_obj)
                    else:
                        best_san = eval_before.best_move_uci
                except Exception:
                    best_san = eval_before.best_move_uci

            try:
                board.push(move)
            except Exception as e:
                logger.error("AnalysisWorker: illegal move '%s' at ply %d: %s", uci, ply_idx, e)
                continue

            # Check if game ended in checkmate on this move
            if board.is_checkmate():
                # Side that just moved delivered checkmate
                eval_after = PositionEval(
                    best_move_uci=None, score_cp=None, mate_in=0, depth=depth
                )
            else:
                try:
                    uci_so_far = moves_uci[:ply_idx]
                    self._engine.set_position(moves_uci=uci_so_far)
                    eval_after = self._engine.evaluate_position(depth=depth, time_ms=500)
                except SearchCancelledError:
                    logger.debug("Analysis cancelled during search at ply %d.", ply_idx)
                    return
                except Exception as e:
                    logger.error("AnalysisWorker: eval failed at ply %d: %s", ply_idx, e)
                    eval_after = PositionEval(
                        best_move_uci=None, score_cp=0, mate_in=None, depth=depth
                    )

            if self._cancelled:
                return

            # Negate eval_after so it is from the mover's perspective
            after_cp_from_mover = (
                -eval_after.score_cp if eval_after.score_cp is not None else None
            )
            # If eval_after is mate 0, mover delivered mate (mate_after=0)
            if eval_after.mate_in == 0:
                after_mate_from_mover = 0
            elif eval_after.mate_in is not None:
                after_mate_from_mover = -eval_after.mate_in
            else:
                after_mate_from_mover = None

            classification, cp_loss = classify_move(
                played_uci=uci,
                best_uci=eval_before.best_move_uci,
                eval_before_cp=eval_before.score_cp,
                eval_after_cp=after_cp_from_mover,
                mate_before=eval_before.mate_in,
                mate_after=after_mate_from_mover,
            )

            # If played move is best move, don't show an alternative SAN
            display_best_san = best_san if eval_before.best_move_uci != uci else None

            move_analyses.append(
                MoveAnalysis(
                    ply=ply_idx,
                    played_uci=uci,
                    best_uci=eval_before.best_move_uci,
                    best_san=display_best_san,
                    cp_loss=cp_loss,
                    classification=classification,
                    eval_before_cp=eval_before.score_cp,
                    eval_after_cp=after_cp_from_mover,
                )
            )

            self.analysis_progress.emit(game_id, ply_idx, total)

            # For next ply, the position before the move is the position after this move!
            # Since eval_after was evaluated with next ply's mover to move, it already
            # has the score and best move from the next mover's perspective.
            eval_before = eval_after

        white_accuracy = compute_accuracy(move_analyses, is_white=True)
        black_accuracy = compute_accuracy(move_analyses, is_white=False)

        result = GameAnalysis(
            game_id=game_id,
            moves=move_analyses,
            white_accuracy=white_accuracy,
            black_accuracy=black_accuracy,
        )
        self.analysis_complete.emit(result)
        logger.info(
            "Analysis complete for game %s: %d moves, W=%.1f%% B=%.1f%%",
            game_id,
            len(move_analyses),
            white_accuracy,
            black_accuracy,
        )


# ---------------------------------------------------------------------------
# Service (lives on GUI thread; owns worker + persistence cache)
# ---------------------------------------------------------------------------


class AnalysisService(QObject):
    """Coordinates on-demand game analysis, caching, and UI notifications."""

    # Public signals (received on GUI thread)
    analysis_started = Signal(str)  # game_id
    analysis_progress = Signal(str, int, int)  # (game_id, done_ply, total_ply)
    analysis_complete = Signal(object)  # GameAnalysis
    analysis_error = Signal(str)

    # Private queued-dispatch signal (Task-3 QueuedConnection pattern)
    _request_analysis_signal = Signal(str, list, int)  # (game_id, moves_uci, depth)

    DEFAULT_DEPTH = 14

    def __init__(
        self,
        engine: ChessEngine | None = None,
        db: DatabaseManager | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._repo = AnalysisRepository(db or DatabaseManager())
        self._worker = AnalysisWorker(engine=engine)
        self._worker.analysis_started.connect(self.analysis_started)
        self._worker.analysis_progress.connect(self.analysis_progress)
        self._worker.analysis_complete.connect(self._on_worker_analysis_complete)
        self._worker.analysis_error.connect(self.analysis_error)

        # Queued connection: emitting from GUI thread posts to worker thread
        self._request_analysis_signal.connect(
            self._worker.run_analysis, Qt.ConnectionType.QueuedConnection
        )
        self._worker.start_worker()

    @property
    def repository(self) -> AnalysisRepository:
        """Access underlying AnalysisRepository."""
        return self._repo

    def get_cached_analysis(self, game_id: str) -> GameAnalysis | None:
        """Retrieve cached analysis from SQLite if available."""
        return self._repo.get(game_id)

    def request_analysis(
        self,
        game_id: str,
        moves_uci: list[str],
        depth: int = DEFAULT_DEPTH,
    ) -> None:
        """Kick off analysis for the given game (dispatched to worker thread).

        If analysis is already cached in SQLite, emits analysis_complete immediately.
        """
        cached = self.get_cached_analysis(game_id)
        if cached is not None:
            self.analysis_complete.emit(cached)
            return

        self._request_analysis_signal.emit(game_id, moves_uci, depth)

    def cancel_analysis(self) -> None:
        """Cancel ongoing analysis."""
        self._worker.cancel()

    def _on_worker_analysis_complete(self, analysis: GameAnalysis) -> None:
        """Persist result to database and propagate to GUI thread listeners."""
        try:
            self._repo.save(analysis)
        except Exception as e:
            logger.warning("Failed to cache game analysis in SQLite: %s", e)
        self.analysis_complete.emit(analysis)

    def cleanup(self) -> None:
        """Stop worker thread and engine process."""
        self._worker.stop_worker()
