"""Asynchronous engine worker thread manager for non-blocking search."""

import logging
import random
import time
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal, Slot

from chess_desktop.engine.difficulty import Difficulty
from chess_desktop.engine.discovery import find_stockfish_binary
from chess_desktop.engine.engine import ChessEngine
from chess_desktop.engine.fallback_engine import FallbackEngine
from chess_desktop.engine.stockfish import SearchCancelledError, StockfishEngine

logger = logging.getLogger(__name__)


class EngineWorker(QObject):
    """Executes chess engine calculations on a dedicated worker thread."""

    best_move_found = Signal(str)  # UCI move (e.g. 'e7e5')
    search_started = Signal()
    search_stopped = Signal()
    engine_error = Signal(str)

    def __init__(
        self,
        engine: ChessEngine | None = None,
        thinking_delay_enabled: bool = True,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._thinking_delay_enabled = thinking_delay_enabled
        self._is_cancelled = False

        if engine is not None:
            self._engine = engine
        else:
            # Auto-detect Stockfish, fallback if not installed
            binary = find_stockfish_binary()
            if binary:
                try:
                    self._engine = StockfishEngine(binary)
                except Exception as e:
                    logger.warning("Stockfish launch failed: %s. Using FallbackEngine.", e)
                    self._engine = FallbackEngine()
            else:
                logger.info("No Stockfish binary found. Using FallbackEngine.")
                self._engine = FallbackEngine()

        self._thread: QThread | None = None
        self._is_started = False

    @property
    def engine(self) -> ChessEngine:
        """Underlying ChessEngine instance."""
        return self._engine

    @property
    def is_cancelled(self) -> bool:
        """True if cancellation was requested."""
        return self._is_cancelled

    @property
    def is_using_stockfish(self) -> bool:
        """True if the active engine is StockfishEngine."""
        return isinstance(self._engine, StockfishEngine)

    @property
    def thinking_delay_enabled(self) -> bool:
        """True if human-like thinking delay is simulated."""
        return self._thinking_delay_enabled

    @thinking_delay_enabled.setter
    def thinking_delay_enabled(self, value: bool) -> None:
        self._thinking_delay_enabled = value

    def start_worker(self) -> None:
        """Start engine backend and move worker onto dedicated QThread."""
        if self._is_started:
            return

        try:
            self._engine.start()
        except Exception as e:
            logger.error("Engine startup failure: %s", e)
            self.engine_error.emit(str(e))
            return

        self._thread = QThread()
        self.moveToThread(self._thread)
        self._thread.start()
        self._is_started = True
        logger.info("EngineWorker started on dedicated QThread.")

    def stop_worker(self) -> None:
        """Cancel search, terminate engine, and stop the thread."""
        if not self._is_started:
            return

        self.cancel_search()
        try:
            self._engine.quit()
        except Exception as e:
            logger.debug("Engine quit exception: %s", e)

        if self._thread is not None:
            thread = self._thread
            self._thread = None
            thread.quit()
            thread.wait(2000)

        self._is_started = False
        logger.info("EngineWorker stopped cleanly.")

    @Slot(str, list, object)
    def request_move(
        self,
        fen: str,
        moves_uci: list[str],
        difficulty: Any,
    ) -> None:
        """Perform search on worker thread and emit best_move_found signal."""
        diff: Difficulty = (
            difficulty if isinstance(difficulty, Difficulty) else Difficulty.INTERMEDIATE
        )
        self._is_cancelled = False
        start_time = time.monotonic()

        try:
            self.search_started.emit()
            self._engine.set_position(fen=fen, moves_uci=moves_uci)

            move = self._engine.search_best_move(
                depth=diff.depth_limit,
                time_ms=diff.time_limit_ms,
                skill_level=diff.skill_level,
            )

            if self.is_cancelled:
                logger.debug("Search cancelled after engine search.")
                return

            # Simulate realistic 2-3s human-like thinking delay
            if self._thinking_delay_enabled:
                min_delay_ms, max_delay_ms = diff.thinking_delay_range_ms
                target_delay_sec = random.uniform(min_delay_ms / 1000.0, max_delay_ms / 1000.0)
                elapsed = time.monotonic() - start_time
                remaining = target_delay_sec - elapsed

                # Sleep in short slices checking cancellation so Undo/Resign/New Game respond instantly
                while remaining > 0 and not self.is_cancelled:
                    chunk = min(remaining, 0.05)
                    time.sleep(chunk)
                    remaining -= chunk

            if getattr(self, "_is_cancelled", False):
                logger.debug("Search cancelled during simulated thinking delay.")
                return

            self.best_move_found.emit(move)
        except SearchCancelledError:
            logger.debug("Search cancelled as requested.")
        except Exception as e:
            logger.error("Engine search error: %s", e)
            self.engine_error.emit(str(e))
        finally:
            self.search_stopped.emit()

    @Slot()
    def cancel_search(self) -> None:
        """Interrupt any ongoing engine calculation."""
        self._is_cancelled = True
        try:
            self._engine.stop()
        except Exception as e:
            logger.debug("Error stopping engine: %s", e)
