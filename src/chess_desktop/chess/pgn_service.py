"""Standard PGN import and export service using python-chess."""

import io
from datetime import UTC, datetime

import chess
import chess.pgn

from chess_desktop.chess.board import ChessBoard
from chess_desktop.chess.move_service import MoveService
from chess_desktop.domain.enums import Color, GameStatus
from chess_desktop.domain.game import Game
from chess_desktop.domain.game_state import MoveRecord
from chess_desktop.domain.player import Player
from chess_desktop.persistence.models import determine_result


class PgnService:
    """Handles standard PGN encoding and decoding."""

    @staticmethod
    def export_to_pgn(
        game: Game,
        event: str = "Casual Game",
        site: str = "Chess Desktop",
        round_num: str = "1",
        date_str: str | None = None,
    ) -> str:
        """Export a domain Game aggregate to a standard PGN string."""
        pgn_game = chess.pgn.Game()
        result_str = determine_result(game.state.status, game.state.turn)

        if not date_str:
            date_str = datetime.now(UTC).strftime("%Y.%m.%d")

        pgn_game.headers["Event"] = event
        pgn_game.headers["Site"] = site
        pgn_game.headers["Date"] = date_str
        pgn_game.headers["Round"] = round_num
        pgn_game.headers["White"] = game.white_player.name
        pgn_game.headers["Black"] = game.black_player.name
        pgn_game.headers["Result"] = result_str

        node: chess.pgn.GameNode = pgn_game
        for record in game.state.moves:
            move = chess.Move.from_uci(record.uci)
            node = node.add_variation(move)

        exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
        return str(pgn_game.accept(exporter))

    @staticmethod
    def import_from_pgn(pgn_text: str) -> Game:
        """Parse and validate a PGN string into a complete domain Game."""
        if not pgn_text.strip():
            raise ValueError("PGN content is empty.")

        stream = io.StringIO(pgn_text.strip())
        pgn_game = chess.pgn.read_game(stream)
        if pgn_game is None:
            raise ValueError("Could not parse a valid chess game from PGN text.")

        if pgn_game.errors:
            raise ValueError(f"Invalid PGN syntax or move: {pgn_game.errors[0]}")

        mainline = list(pgn_game.mainline_moves())
        if not mainline and "[" not in pgn_text:
            raise ValueError("Could not parse any valid moves or headers from PGN text.")

        white_name = pgn_game.headers.get("White", "White")
        black_name = pgn_game.headers.get("Black", "Black")
        result = pgn_game.headers.get("Result", "*")

        board = ChessBoard()
        moves: list[MoveRecord] = []
        last_move: tuple[str, str] | None = None

        for move in pgn_game.mainline_moves():
            rec = MoveService.execute_uci(board, move.uci())
            moves.append(rec)
            last_move = (rec.from_square, rec.to_square)

        status_override: GameStatus | None = None
        eval_status, _ = MoveService.evaluate_game_status(board)
        if not eval_status.is_game_over:
            if result == "1/2-1/2":
                status_override = GameStatus.DRAW_AGREED
            elif result in ("1-0", "0-1"):
                status_override = GameStatus.RESIGNED

        state = MoveService.build_game_state(
            board=board,
            last_move=last_move,
            moves=moves,
            status_override=status_override,
        )

        return Game(
            white_player=Player(white_name, Color.WHITE),
            black_player=Player(black_name, Color.BLACK),
            state=state,
        )
