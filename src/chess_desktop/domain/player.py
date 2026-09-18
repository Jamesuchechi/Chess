"""Player domain model."""

from dataclasses import dataclass

from chess_desktop.domain.enums import Color, PlayerType


@dataclass(frozen=True)
class Player:
    """Represents a chess player."""

    name: str
    color: Color
    player_type: PlayerType = PlayerType.HUMAN
