"""Abstract base interface for chess engines."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class PositionEval:
    """Result of a position evaluation search.

    Scores are always from the **side-to-move's perspective** (positive means
    the side to move is better off).  When the position is a forced mate,
    ``score_cp`` is ``None`` and ``mate_in`` holds the move-count (positive =
    the side to move is mating, negative = the side to move is being mated).
    """

    best_move_uci: str | None  # engine top choice in UCI notation, or None if no moves
    score_cp: int | None  # centipawn score, None when mate
    mate_in: int | None  # mate distance, None when not a forced mate
    depth: int  # depth actually searched


class ChessEngine(ABC):
    """Abstract interface defining the engine lifecycle and search operations."""

    @abstractmethod
    def start(self) -> None:
        """Start the engine process or backend."""

    @abstractmethod
    def stop(self) -> None:
        """Immediately interrupt and cancel an ongoing search."""

    @abstractmethod
    def set_position(
        self,
        fen: str | None = None,
        moves_uci: list[str] | None = None,
    ) -> None:
        """Set the active board position using FEN and/or played UCI moves."""

    @abstractmethod
    def search_best_move(
        self,
        depth: int | None = None,
        time_ms: int | None = None,
        skill_level: int | None = None,
    ) -> str:
        """Search for the best move under the specified constraints.

        Returns:
            The chosen move in UCI format (e.g., 'e2e4' or 'e7e8q').

        Raises:
            RuntimeError: If the search fails or the engine is not running.
        """

    @abstractmethod
    def evaluate_position(
        self,
        depth: int = 14,
        time_ms: int | None = None,
    ) -> PositionEval:
        """Evaluate the current position at the given depth.

        Returns a :class:`PositionEval` containing the best move and score
        from the side-to-move's perspective.  Does not alter the position set
        via :meth:`set_position`.

        Args:
            depth: Search depth limit.
            time_ms: Optional wall-clock time limit in milliseconds.

        Raises:
            RuntimeError: If the engine is not running or evaluation fails.
        """

    @abstractmethod
    def is_ready(self) -> bool:
        """Check if the engine is running and ready for commands."""

    @abstractmethod
    def quit(self) -> None:
        """Terminate the engine process cleanly."""
