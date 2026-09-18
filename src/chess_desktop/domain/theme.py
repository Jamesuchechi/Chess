"""Board themes and visual styles configuration."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BoardTheme:
    """Represents a chessboard color theme."""

    name: str
    display_name: str
    light_square: str
    dark_square: str
    selected_overlay: str = "rgba(247, 247, 105, 0.7)"
    last_move_overlay: str = "rgba(186, 202, 68, 0.6)"

    @classmethod
    def classic(cls) -> "BoardTheme":
        return cls(
            name="classic",
            display_name="Classic (Green & Buff)",
            light_square="#eeeed2",
            dark_square="#769656",
        )

    @classmethod
    def wood(cls) -> "BoardTheme":
        return cls(
            name="wood",
            display_name="Wood (Walnut & Oak)",
            light_square="#e3c08b",
            dark_square="#b88b4a",
            selected_overlay="rgba(255, 235, 130, 0.7)",
            last_move_overlay="rgba(205, 155, 75, 0.6)",
        )

    @classmethod
    def modern(cls) -> "BoardTheme":
        return cls(
            name="modern",
            display_name="Modern (Slate & Blue)",
            light_square="#dee3e6",
            dark_square="#8ca2ad",
            selected_overlay="rgba(130, 200, 255, 0.7)",
            last_move_overlay="rgba(100, 160, 210, 0.6)",
        )

    @classmethod
    def minimal(cls) -> "BoardTheme":
        return cls(
            name="minimal",
            display_name="Minimal (Charcoal & Gray)",
            light_square="#e0e0e0",
            dark_square="#5a5a5a",
            selected_overlay="rgba(220, 220, 100, 0.7)",
            last_move_overlay="rgba(150, 150, 150, 0.6)",
        )

    @classmethod
    def high_contrast(cls) -> "BoardTheme":
        return cls(
            name="high_contrast",
            display_name="High Contrast (Accessible)",
            light_square="#ffffff",
            dark_square="#1a1a1a",
            selected_overlay="rgba(255, 255, 0, 0.8)",
            last_move_overlay="rgba(0, 200, 255, 0.6)",
        )

    @classmethod
    def all_themes(cls) -> list["BoardTheme"]:
        """All predefined themes."""
        return [
            cls.classic(),
            cls.wood(),
            cls.modern(),
            cls.minimal(),
            cls.high_contrast(),
        ]

    @classmethod
    def from_name(cls, name: str) -> "BoardTheme":
        """Get theme by identifier, fallback to classic."""
        for t in cls.all_themes():
            if t.name.lower() == name.lower() or t.display_name.lower() == name.lower():
                return t
        return cls.classic()
