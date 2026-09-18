"""Authoritative chess board wrapper around python-chess."""

from collections.abc import Iterator

import chess

from chess_desktop.domain.enums import Color, PieceType

_PIECE_MAP_FROM_CHESS: dict[chess.PieceType, PieceType] = {
    chess.PAWN: PieceType.PAWN,
    chess.KNIGHT: PieceType.KNIGHT,
    chess.BISHOP: PieceType.BISHOP,
    chess.ROOK: PieceType.ROOK,
    chess.QUEEN: PieceType.QUEEN,
    chess.KING: PieceType.KING,
}

_PIECE_MAP_TO_CHESS: dict[PieceType, chess.PieceType] = {
    v: k for k, v in _PIECE_MAP_FROM_CHESS.items()
}


class ChessBoard:
    """Encapsulates python-chess Board to provide domain-typed chess operations."""

    def __init__(self, fen: str | None = None) -> None:
        self._board = chess.Board(fen) if fen else chess.Board()

    @property
    def internal_board(self) -> chess.Board:
        """Direct reference to underlying python-chess board (used only within chess package)."""
        return self._board

    @property
    def turn(self) -> Color:
        """Active player's turn."""
        return Color.WHITE if self._board.turn == chess.WHITE else Color.BLACK

    @property
    def fullmove_number(self) -> int:
        """Current full move number."""
        return self._board.fullmove_number

    @property
    def fen(self) -> str:
        """Current FEN representation."""
        return self._board.fen()

    def piece_at(self, square_name: str) -> tuple[PieceType, Color] | None:
        """Return (PieceType, Color) at algebraic square (e.g. 'e4'), or None if empty."""
        square = chess.parse_square(square_name)
        piece = self._board.piece_at(square)
        if not piece:
            return None
        piece_type = _PIECE_MAP_FROM_CHESS[piece.piece_type]
        color = Color.WHITE if piece.color == chess.WHITE else Color.BLACK
        return piece_type, color

    def king_square(self, color: Color) -> str:
        """Return square name for the king of specified color."""
        chess_color = chess.WHITE if color == Color.WHITE else chess.BLACK
        sq = self._board.king(chess_color)
        return chess.square_name(sq) if sq is not None else ""

    def is_check(self) -> bool:
        """Check whether current side is in check."""
        return self._board.is_check()

    def is_game_over(self) -> bool:
        """Check whether game is in a terminal state."""
        return self._board.is_game_over()

    def legal_moves(self) -> Iterator[chess.Move]:
        """Yield all legal moves."""
        return iter(self._board.legal_moves)

    def push_move(self, move: chess.Move) -> None:
        """Push a legal move onto the board stack."""
        self._board.push(move)

    def pop_move(self) -> chess.Move:
        """Pop and return the last move from the board stack."""
        return self._board.pop()

    def reset(self) -> None:
        """Reset the board to standard starting position."""
        self._board.reset()

    @staticmethod
    def piece_type_to_chess(piece_type: PieceType) -> chess.PieceType:
        """Convert domain PieceType to chess.PieceType."""
        return _PIECE_MAP_TO_CHESS[piece_type]

    @staticmethod
    def piece_type_from_chess(chess_piece: chess.PieceType) -> PieceType:
        """Convert chess.PieceType to domain PieceType."""
        return _PIECE_MAP_FROM_CHESS[chess_piece]

    @classmethod
    def create_at_ply(cls, uci_moves: list[str], target_ply: int) -> "ChessBoard":
        """Construct a new ChessBoard by applying moves up to target_ply."""
        new_board = cls()
        limit = max(0, min(target_ply, len(uci_moves)))
        for i in range(limit):
            move = chess.Move.from_uci(uci_moves[i])
            new_board.push_move(move)
        return new_board
