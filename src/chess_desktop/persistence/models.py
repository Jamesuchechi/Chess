"""Persistence data models and mappings for SQLite storage."""

from dataclasses import dataclass
from datetime import UTC, datetime

from chess_desktop.domain.enums import Color, GameStatus
from chess_desktop.domain.game import Game


def determine_result(status: GameStatus, turn: Color) -> str:
    """Derive standard PGN result notation from game status and current turn."""
    if status == GameStatus.CHECKMATE:
        # Checkmate means the side to move is mated, so the other side won
        return "1-0" if turn == Color.BLACK else "0-1"
    if status == GameStatus.RESIGNED:
        # Side to move resigned, so the other side won
        return "1-0" if turn == Color.BLACK else "0-1"
    if status == GameStatus.TIMEOUT:
        return "1-0" if turn == Color.BLACK else "0-1"
    if status in (
        GameStatus.STALEMATE,
        GameStatus.DRAW_AGREED,
        GameStatus.DRAW_INSUFFICIENT_MATERIAL,
        GameStatus.DRAW_REPETITION,
        GameStatus.DRAW_FIFTY_MOVES,
    ):
        return "1/2-1/2"
    return "*"


@dataclass(frozen=True)
class SavedGameRecord:
    """Full database representation of a chess game."""

    game_id: str
    title: str
    white_name: str
    black_name: str
    status: str
    result: str
    fen: str
    pgn: str
    moves_uci: str
    move_count: int
    created_at: str
    updated_at: str

    @classmethod
    def from_game(
        cls,
        game: Game,
        title: str,
        pgn_text: str = "",
        created_at: str | None = None,
    ) -> "SavedGameRecord":
        """Convert a domain Game aggregate into a persistent database record."""
        now_iso = datetime.now(UTC).isoformat()
        uci_moves = " ".join(record.uci for record in game.state.moves)
        result_str = determine_result(game.state.status, game.state.turn)

        return cls(
            game_id=game.game_id,
            title=title or f"{game.white_player.name} vs. {game.black_player.name}",
            white_name=game.white_player.name,
            black_name=game.black_player.name,
            status=game.state.status.name,
            result=result_str,
            fen=game.state.fen,
            pgn=pgn_text,
            moves_uci=uci_moves,
            move_count=len(game.state.moves),
            created_at=created_at or now_iso,
            updated_at=now_iso,
        )


@dataclass(frozen=True)
class SavedGameSummary:
    """Lightweight metadata for listing games in open/manage dialogs."""

    game_id: str
    title: str
    white_name: str
    black_name: str
    result: str
    move_count: int
    created_at: str
    updated_at: str
