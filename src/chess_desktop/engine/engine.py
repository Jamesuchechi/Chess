"""Abstract base interface for chess engines."""

from abc import ABC, abstractmethod


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
    def is_ready(self) -> bool:
        """Check if the engine is running and ready for commands."""

    @abstractmethod
    def quit(self) -> None:
        """Terminate the engine process cleanly."""
