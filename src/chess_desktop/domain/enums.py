"""Domain enumerations for Chess Desktop."""

from enum import Enum, auto


class Color(Enum):
    """Piece or player color."""

    WHITE = "white"
    BLACK = "black"

    @property
    def opposite(self) -> "Color":
        """Return the opposite color."""
        return Color.BLACK if self == Color.WHITE else Color.WHITE


class PieceType(Enum):
    """Chess piece types."""

    PAWN = "pawn"
    KNIGHT = "knight"
    BISHOP = "bishop"
    ROOK = "rook"
    QUEEN = "queen"
    KING = "king"

    @property
    def material_value(self) -> int:
        """Standard piece point value."""
        match self:
            case PieceType.PAWN:
                return 1
            case PieceType.KNIGHT | PieceType.BISHOP:
                return 3
            case PieceType.ROOK:
                return 5
            case PieceType.QUEEN:
                return 9
            case PieceType.KING:
                return 0


class GameStatus(Enum):
    """Current state and outcome of the game."""

    IN_PROGRESS = auto()
    CHECK = auto()
    CHECKMATE = auto()
    STALEMATE = auto()
    DRAW_INSUFFICIENT_MATERIAL = auto()
    DRAW_REPETITION = auto()
    DRAW_FIFTY_MOVES = auto()
    DRAW_AGREED = auto()
    RESIGNED = auto()
    TIMEOUT = auto()

    @property
    def is_game_over(self) -> bool:
        """True if game has ended."""
        return self not in (GameStatus.IN_PROGRESS, GameStatus.CHECK)

    @property
    def is_draw(self) -> bool:
        """True if game ended in a draw."""
        return self in (
            GameStatus.STALEMATE,
            GameStatus.DRAW_INSUFFICIENT_MATERIAL,
            GameStatus.DRAW_REPETITION,
            GameStatus.DRAW_FIFTY_MOVES,
            GameStatus.DRAW_AGREED,
        )


class PlayerType(Enum):
    """Type of player controller."""

    HUMAN = auto()
    COMPUTER = auto()
