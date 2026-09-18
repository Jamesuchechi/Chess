"""Game state and move record domain models."""

import time
from dataclasses import dataclass, field

from chess_desktop.domain.enums import Color, GameStatus, PieceType


@dataclass(frozen=True)
class MoveRecord:
    """Historical record of a single ply."""

    san: str
    uci: str
    from_square: str
    to_square: str
    is_capture: bool
    captured_piece: PieceType | None = None
    is_check: bool = False
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class GameState:
    """Authoritative snapshot of the game state."""

    turn: Color
    status: GameStatus
    fen: str
    move_number: int = 1
    in_check: bool = False
    check_square: str | None = None
    last_move: tuple[str, str] | None = None
    captured_white: list[PieceType] = field(default_factory=list)  # Black pieces captured by White
    captured_black: list[PieceType] = field(default_factory=list)  # White pieces captured by Black
    material_difference: int = 0  # > 0 White leads, < 0 Black leads
    moves: list[MoveRecord] = field(default_factory=list)
    status_message: str | None = None
    review_ply: int | None = None  # None indicates viewing the active live position

    @property
    def is_reviewing(self) -> bool:
        """True if currently viewing an earlier historical move rather than live game."""
        return self.review_ply is not None and self.review_ply < len(self.moves)
