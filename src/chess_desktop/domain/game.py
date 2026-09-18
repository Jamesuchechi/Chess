"""Game domain aggregate model."""

import uuid
from dataclasses import dataclass

from chess_desktop.domain.game_state import GameState
from chess_desktop.domain.player import Player


@dataclass
class Game:
    """Aggregate representing an entire chess match."""

    white_player: Player
    black_player: Player
    state: GameState
    game_id: str = ""

    def __post_init__(self) -> None:
        if not self.game_id:
            self.game_id = str(uuid.uuid4())
