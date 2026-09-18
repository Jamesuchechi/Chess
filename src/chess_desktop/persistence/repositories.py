"""Repository for storing and querying chess games in SQLite."""

from chess_desktop.chess.board import ChessBoard
from chess_desktop.chess.move_service import MoveService
from chess_desktop.domain.enums import Color, GameStatus
from chess_desktop.domain.game import Game
from chess_desktop.domain.game_state import MoveRecord
from chess_desktop.domain.player import Player
from chess_desktop.persistence.database import DatabaseManager
from chess_desktop.persistence.models import SavedGameRecord, SavedGameSummary


class GameRepository:
    """Repository handling CRUD operations for saved games."""

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    def save(
        self,
        game: Game,
        title: str | None = None,
        pgn_text: str = "",
    ) -> str:
        """Insert or update a game in the database."""
        existing_created_at: str | None = None
        with self._db.connection() as conn:
            row = conn.execute(
                "SELECT created_at FROM games WHERE id = ?", (game.game_id,)
            ).fetchone()
            if row:
                existing_created_at = str(row["created_at"])

        record = SavedGameRecord.from_game(
            game=game,
            title=title or f"{game.white_player.name} vs. {game.black_player.name}",
            pgn_text=pgn_text,
            created_at=existing_created_at,
        )

        with self._db.connection() as conn:
            conn.execute(
                """
                INSERT INTO games (
                    id, title, white_name, black_name, status, result,
                    fen, pgn, moves_uci, move_count, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    white_name = excluded.white_name,
                    black_name = excluded.black_name,
                    status = excluded.status,
                    result = excluded.result,
                    fen = excluded.fen,
                    pgn = excluded.pgn,
                    moves_uci = excluded.moves_uci,
                    move_count = excluded.move_count,
                    updated_at = excluded.updated_at;
                """,
                (
                    record.game_id,
                    record.title,
                    record.white_name,
                    record.black_name,
                    record.status,
                    record.result,
                    record.fen,
                    record.pgn,
                    record.moves_uci,
                    record.move_count,
                    record.created_at,
                    record.updated_at,
                ),
            )
        return record.game_id

    def get_by_id(self, game_id: str) -> tuple[Game, SavedGameRecord] | None:
        """Retrieve a game by ID, reconstructing the complete domain Game and metadata record."""
        with self._db.connection() as conn:
            row = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
            if not row:
                return None

        record = SavedGameRecord(
            game_id=str(row["id"]),
            title=str(row["title"]),
            white_name=str(row["white_name"]),
            black_name=str(row["black_name"]),
            status=str(row["status"]),
            result=str(row["result"]),
            fen=str(row["fen"]),
            pgn=str(row["pgn"]),
            moves_uci=str(row["moves_uci"]),
            move_count=int(row["move_count"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

        # Replay moves to reconstruct verified domain Game
        board = ChessBoard()
        moves: list[MoveRecord] = []
        last_move: tuple[str, str] | None = None

        if record.moves_uci.strip():
            for uci in record.moves_uci.split():
                rec = MoveService.execute_uci(board, uci)
                moves.append(rec)
                last_move = (rec.from_square, rec.to_square)

        status_enum = GameStatus[record.status] if record.status in GameStatus.__members__ else None
        state = MoveService.build_game_state(
            board=board,
            last_move=last_move,
            moves=moves,
            status_override=status_enum,
        )

        white_player = Player(record.white_name, Color.WHITE)
        black_player = Player(record.black_name, Color.BLACK)
        game = Game(
            white_player=white_player,
            black_player=black_player,
            state=state,
            game_id=record.game_id,
        )

        return game, record

    def list_games(self) -> list[SavedGameSummary]:
        """List all saved games ordered by most recently updated."""
        with self._db.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, title, white_name, black_name, result, move_count, created_at, updated_at
                FROM games
                ORDER BY updated_at DESC;
                """
            ).fetchall()

        return [
            SavedGameSummary(
                game_id=str(r["id"]),
                title=str(r["title"]),
                white_name=str(r["white_name"]),
                black_name=str(r["black_name"]),
                result=str(r["result"]),
                move_count=int(r["move_count"]),
                created_at=str(r["created_at"]),
                updated_at=str(r["updated_at"]),
            )
            for r in rows
        ]

    def delete(self, game_id: str) -> bool:
        """Delete a saved game by ID."""
        with self._db.connection() as conn:
            cursor = conn.execute("DELETE FROM games WHERE id = ?", (game_id,))
            return cursor.rowcount > 0
