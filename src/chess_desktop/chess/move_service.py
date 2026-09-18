"""Authoritative move validation, execution, and state evaluation service."""

from collections import Counter

import chess

from chess_desktop.chess.board import ChessBoard
from chess_desktop.domain.enums import GameStatus, PieceType
from chess_desktop.domain.game_state import GameState, MoveRecord

# Standard piece count per side
_INITIAL_PIECES: Counter[PieceType] = Counter(
    {
        PieceType.PAWN: 8,
        PieceType.KNIGHT: 2,
        PieceType.BISHOP: 2,
        PieceType.ROOK: 2,
        PieceType.QUEEN: 1,
    }
)


class MoveService:
    """Provides pure chess logic and state evaluations using ChessBoard."""

    @staticmethod
    def get_legal_moves_from(board: ChessBoard, square_name: str) -> list[tuple[str, bool]]:
        """Return legal destination squares for piece on square_name and whether each is a capture."""
        try:
            from_sq = chess.parse_square(square_name)
        except ValueError:
            return []

        piece = board.internal_board.piece_at(from_sq)
        if not piece or (piece.color != board.internal_board.turn):
            return []

        results: list[tuple[str, bool]] = []
        seen_targets: set[str] = set()

        for move in board.legal_moves():
            if move.from_square == from_sq:
                to_name = chess.square_name(move.to_square)
                if to_name in seen_targets:
                    continue
                seen_targets.add(to_name)
                is_capture = board.internal_board.is_capture(move)
                results.append((to_name, is_capture))

        return results

    @staticmethod
    def is_promotion(board: ChessBoard, from_square: str, to_square: str) -> bool:
        """Check if move from from_square to to_square requires pawn promotion."""
        try:
            from_sq = chess.parse_square(from_square)
            to_sq = chess.parse_square(to_square)
        except ValueError:
            return False

        piece = board.internal_board.piece_at(from_sq)
        if not piece or piece.piece_type != chess.PAWN:
            return False

        target_rank = chess.square_rank(to_sq)
        return (piece.color == chess.WHITE and target_rank == 7) or (
            piece.color == chess.BLACK and target_rank == 0
        )

    @staticmethod
    def execute_move(
        board: ChessBoard,
        from_square: str,
        to_square: str,
        promotion: PieceType | None = None,
    ) -> MoveRecord:
        """Validate and execute move on board, returning MoveRecord."""
        from_sq = chess.parse_square(from_square)
        to_sq = chess.parse_square(to_square)

        promo_type: chess.PieceType | None = None
        if promotion:
            promo_type = ChessBoard.piece_type_to_chess(promotion)
        elif MoveService.is_promotion(board, from_square, to_square):
            # Default to Queen if not specified
            promo_type = chess.QUEEN

        move = chess.Move(from_sq, to_sq, promotion=promo_type)

        if move not in board.internal_board.legal_moves:
            raise ValueError(f"Illegal move: {from_square} -> {to_square}")

        is_capture = board.internal_board.is_capture(move)
        captured_piece: PieceType | None = None
        if is_capture:
            target_piece = board.internal_board.piece_at(to_sq)
            if target_piece:
                captured_piece = ChessBoard.piece_type_from_chess(target_piece.piece_type)
            elif board.internal_board.is_en_passant(move):
                captured_piece = PieceType.PAWN

        san = board.internal_board.san(move)
        board.push_move(move)

        is_check = board.is_check()

        return MoveRecord(
            san=san,
            uci=move.uci(),
            from_square=from_square,
            to_square=to_square,
            is_capture=is_capture,
            captured_piece=captured_piece,
            is_check=is_check,
        )

    @staticmethod
    def execute_uci(board: ChessBoard, uci: str) -> MoveRecord:
        """Validate and execute a UCI move string (e.g. 'e2e4' or 'e7e8q')."""
        from_sq = uci[:2]
        to_sq = uci[2:4]
        promo: PieceType | None = None
        if len(uci) >= 5:
            promo_map = {
                "q": PieceType.QUEEN,
                "r": PieceType.ROOK,
                "b": PieceType.BISHOP,
                "n": PieceType.KNIGHT,
            }
            promo = promo_map.get(uci[4].lower())
        return MoveService.execute_move(board, from_sq, to_sq, promotion=promo)

    @staticmethod
    def evaluate_game_status(board: ChessBoard) -> tuple[GameStatus, str | None]:
        """Evaluate current board for checkmate, stalemate, check, or draws."""
        b = board.internal_board
        if b.is_checkmate():
            winner = "Black" if b.turn == chess.WHITE else "White"
            return GameStatus.CHECKMATE, f"Checkmate! {winner} wins."
        if b.is_stalemate():
            return GameStatus.STALEMATE, "Draw by stalemate."
        if b.is_insufficient_material():
            return GameStatus.DRAW_INSUFFICIENT_MATERIAL, "Draw by insufficient material."
        if b.can_claim_threefold_repetition():
            return GameStatus.DRAW_REPETITION, "Draw by threefold repetition."
        if b.can_claim_fifty_moves():
            return GameStatus.DRAW_FIFTY_MOVES, "Draw by fifty-move rule."
        if b.is_check():
            return GameStatus.CHECK, "Check!"

        return GameStatus.IN_PROGRESS, None

    @staticmethod
    def calculate_material(board: ChessBoard) -> tuple[list[PieceType], list[PieceType], int]:
        """Calculate captured pieces for White and Black, and net material difference."""
        white_on_board: Counter[PieceType] = Counter()
        black_on_board: Counter[PieceType] = Counter()

        for sq in chess.SQUARES:
            piece = board.internal_board.piece_at(sq)
            if piece and piece.piece_type != chess.KING:
                pt = ChessBoard.piece_type_from_chess(piece.piece_type)
                if piece.color == chess.WHITE:
                    white_on_board[pt] += 1
                else:
                    black_on_board[pt] += 1

        # Captured by White = initial black pieces minus currently on board
        captured_by_white: list[PieceType] = []
        for pt, initial_count in _INITIAL_PIECES.items():
            missing = initial_count - black_on_board[pt]
            if missing > 0:
                captured_by_white.extend([pt] * missing)

        # Captured by Black = initial white pieces minus currently on board
        captured_by_black: list[PieceType] = []
        for pt, initial_count in _INITIAL_PIECES.items():
            missing = initial_count - white_on_board[pt]
            if missing > 0:
                captured_by_black.extend([pt] * missing)

        # Sort pieces by value descending for display
        captured_by_white.sort(key=lambda p: p.material_value, reverse=True)
        captured_by_black.sort(key=lambda p: p.material_value, reverse=True)

        white_material = sum(pt.material_value for pt in white_on_board.elements())
        black_material = sum(pt.material_value for pt in black_on_board.elements())
        diff = white_material - black_material

        return captured_by_white, captured_by_black, diff

    @staticmethod
    def build_game_state(
        board: ChessBoard,
        last_move: tuple[str, str] | None,
        moves: list[MoveRecord],
        review_ply: int | None = None,
        status_override: GameStatus | None = None,
        status_message_override: str | None = None,
    ) -> GameState:
        """Construct authoritative GameState snapshot from board."""
        status, msg = MoveService.evaluate_game_status(board)
        if status_override is not None:
            status = status_override
            msg = status_message_override or msg

        in_check = board.is_check()
        check_sq = board.king_square(board.turn) if in_check else None
        cap_w, cap_b, diff = MoveService.calculate_material(board)

        return GameState(
            turn=board.turn,
            status=status,
            fen=board.fen,
            move_number=board.fullmove_number,
            in_check=in_check,
            check_square=check_sq,
            last_move=last_move,
            captured_white=cap_w,
            captured_black=cap_b,
            material_difference=diff,
            moves=moves,
            status_message=msg,
            review_ply=review_ply,
        )
