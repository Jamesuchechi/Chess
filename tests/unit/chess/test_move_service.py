"""Unit tests for MoveService verifying FIDE chess rules and state calculations."""

from chess_desktop.chess.board import ChessBoard
from chess_desktop.chess.move_service import MoveService
from chess_desktop.domain.enums import Color, GameStatus, PieceType


def test_legal_moves_initial_position() -> None:
    """Verify legal move lookup from starting squares."""
    board = ChessBoard()
    # e2 pawn can move to e3 (quiet) and e4 (quiet)
    e2_moves = MoveService.get_legal_moves_from(board, "e2")
    assert sorted(e2_moves) == [("e3", False), ("e4", False)]

    # b1 knight can move to a3 and c3
    b1_moves = MoveService.get_legal_moves_from(board, "b1")
    assert sorted(b1_moves) == [("a3", False), ("c3", False)]

    # e1 king has no legal moves initially
    assert MoveService.get_legal_moves_from(board, "e1") == []


def test_legal_moves_captures() -> None:
    """Verify capture flag is True on opponent pieces."""
    board = ChessBoard()
    MoveService.execute_move(board, "e2", "e4")
    MoveService.execute_move(board, "d7", "d5")

    # e4 pawn can now move to e5 (quiet) or capture d5 (capture)
    e4_moves = dict(MoveService.get_legal_moves_from(board, "e4"))
    assert e4_moves.get("e5") is False
    assert e4_moves.get("d5") is True


def test_fools_mate_checkmate() -> None:
    """Verify Fool's mate produces Checkmate state."""
    board = ChessBoard()
    # 1. f3 e5 2. g4 Qh4#
    MoveService.execute_move(board, "f2", "f3")
    MoveService.execute_move(board, "e7", "e5")
    MoveService.execute_move(board, "g2", "g4")
    rec = MoveService.execute_move(board, "d8", "h4")

    assert rec.is_check
    status, msg = MoveService.evaluate_game_status(board)
    assert status == GameStatus.CHECKMATE
    assert msg is not None and "Black wins" in msg


def test_stalemate() -> None:
    """Verify stalemate position detection."""
    # Classic stalemate FEN: Black king at a8, White queen at c7, White king at c6
    board = ChessBoard("k7/2Q5/2K5/8/8/8/8/8 b - - 0 1")
    status, msg = MoveService.evaluate_game_status(board)
    assert status == GameStatus.STALEMATE
    assert "stalemate" in (msg or "").lower()


def test_castling_kingside_and_queenside() -> None:
    """Verify castling rights and execution for both sides."""
    # Board ready for White castling both sides
    board = ChessBoard("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")

    # White castles kingside: e1 -> g1
    white_king_moves = [target for target, _ in MoveService.get_legal_moves_from(board, "e1")]
    assert "g1" in white_king_moves
    assert "c1" in white_king_moves

    MoveService.execute_move(board, "e1", "g1")
    assert board.piece_at("g1") == (PieceType.KING, Color.WHITE)
    assert board.piece_at("f1") == (PieceType.ROOK, Color.WHITE)

    # Black castles queenside: e8 -> c8
    MoveService.execute_move(board, "e8", "c8")
    assert board.piece_at("c8") == (PieceType.KING, Color.BLACK)
    assert board.piece_at("d8") == (PieceType.ROOK, Color.BLACK)


def test_castling_blocked_by_check() -> None:
    """Verify king cannot castle out of or through check."""
    # White king in check from Black rook on e8
    board = ChessBoard("4r3/8/8/8/8/8/8/R3K2R w KQ - 0 1")
    assert board.is_check()
    white_moves = [target for target, _ in MoveService.get_legal_moves_from(board, "e1")]
    assert "g1" not in white_moves
    assert "c1" not in white_moves


def test_en_passant() -> None:
    """Verify en passant capture detection and piece removal."""
    board = ChessBoard()
    # 1. e4 a6 2. e5 d5
    MoveService.execute_move(board, "e2", "e4")
    MoveService.execute_move(board, "a7", "a6")
    MoveService.execute_move(board, "e4", "e5")
    MoveService.execute_move(board, "d7", "d5")

    # White pawn on e5 can capture en passant on d6
    e5_moves = dict(MoveService.get_legal_moves_from(board, "e5"))
    assert e5_moves.get("d6") is True

    record = MoveService.execute_move(board, "e5", "d6")
    assert record.is_capture
    assert record.captured_piece == PieceType.PAWN
    # Black pawn on d5 should now be gone
    assert board.piece_at("d5") is None
    assert board.piece_at("d6") == (PieceType.PAWN, Color.WHITE)


def test_pawn_promotion() -> None:
    """Verify pawn promotion requirement and piece conversion."""
    # White pawn at a7
    board = ChessBoard("8/P7/8/8/8/8/8/k1K5 w - - 0 1")
    assert MoveService.is_promotion(board, "a7", "a8")

    # Promote to Knight
    rec = MoveService.execute_move(board, "a7", "a8", promotion=PieceType.KNIGHT)
    assert rec.san == "a8=N"
    assert board.piece_at("a8") == (PieceType.KNIGHT, Color.WHITE)


def test_insufficient_material() -> None:
    """Verify King vs King is insufficient material."""
    board = ChessBoard("8/8/8/4k3/8/8/4K3/8 w - - 0 1")
    status, msg = MoveService.evaluate_game_status(board)
    assert status == GameStatus.DRAW_INSUFFICIENT_MATERIAL


def test_threefold_repetition() -> None:
    """Verify threefold repetition detection."""
    board = ChessBoard()
    # 1. Nf3 Nf6 2. Ng1 Ng8 3. Nf3 Nf6 4. Ng1 Ng8
    moves = [
        ("g1", "f3"),
        ("g8", "f6"),
        ("f3", "g1"),
        ("f6", "g8"),
        ("g1", "f3"),
        ("g8", "f6"),
        ("f3", "g1"),
        ("f6", "g8"),
    ]
    for from_sq, to_sq in moves:
        MoveService.execute_move(board, from_sq, to_sq)

    status, _ = MoveService.evaluate_game_status(board)
    assert status == GameStatus.DRAW_REPETITION


def test_material_calculation() -> None:
    """Verify captured piece tracking and material advantage differential."""
    board = ChessBoard()
    # Initially 0 captured pieces and 0 diff
    cap_w, cap_b, diff = MoveService.calculate_material(board)
    assert cap_w == []
    assert cap_b == []
    assert diff == 0

    # 1. e4 d5 2. exd5 (White captures black pawn)
    MoveService.execute_move(board, "e2", "e4")
    MoveService.execute_move(board, "d7", "d5")
    MoveService.execute_move(board, "e4", "d5")

    cap_w, cap_b, diff = MoveService.calculate_material(board)
    assert cap_w == [PieceType.PAWN]
    assert cap_b == []
    assert diff == 1  # White +1


def test_scholars_mate_full_game() -> None:
    """Verify full legal game ending in Scholar's mate."""
    board = ChessBoard()
    # 1. e4 e5 2. Bc4 Nc6 3. Qh5 Nf6 4. Qxf7#
    moves = [
        ("e2", "e4"),
        ("e7", "e5"),
        ("f1", "c4"),
        ("b8", "c6"),
        ("d1", "h5"),
        ("g8", "f6"),
        ("h5", "f7"),
    ]
    records = []
    for from_sq, to_sq in moves:
        rec = MoveService.execute_move(board, from_sq, to_sq)
        records.append(rec)

    assert records[-1].san == "Qxf7#"
    assert records[-1].is_capture is True
    assert records[-1].is_check is True

    state = MoveService.build_game_state(board, ("h5", "f7"), records)
    assert state.status == GameStatus.CHECKMATE
    assert state.in_check is True
    assert state.check_square == "e8"
    assert "White wins" in (state.status_message or "")
