"""Engine difficulty presets and parameter mapping."""

from enum import Enum


class Difficulty(Enum):
    """User-facing engine strength presets mapped to internal UCI constraints."""

    BEGINNER = "beginner"
    CASUAL = "casual"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    MASTER = "master"

    @property
    def display_name(self) -> str:
        """Human-readable name for UI display."""
        match self:
            case Difficulty.BEGINNER:
                return "Beginner"
            case Difficulty.CASUAL:
                return "Casual"
            case Difficulty.INTERMEDIATE:
                return "Intermediate"
            case Difficulty.ADVANCED:
                return "Advanced"
            case Difficulty.MASTER:
                return "Master"

    @property
    def description(self) -> str:
        """Short description of the playstyle."""
        match self:
            case Difficulty.BEGINNER:
                return "Generous and makes frequent mistakes"
            case Difficulty.CASUAL:
                return "Fun, friendly match for recreational players"
            case Difficulty.INTERMEDIATE:
                return "Solid play, catches simple tactical errors"
            case Difficulty.ADVANCED:
                return "Strong positional play and deep tactics"
            case Difficulty.MASTER:
                return "Maximum engine power with full depth"

    @property
    def skill_level(self) -> int:
        """Stockfish Skill Level parameter (0-20)."""
        match self:
            case Difficulty.BEGINNER:
                return 1
            case Difficulty.CASUAL:
                return 5
            case Difficulty.INTERMEDIATE:
                return 10
            case Difficulty.ADVANCED:
                return 15
            case Difficulty.MASTER:
                return 20

    @property
    def depth_limit(self) -> int:
        """Search depth ceiling."""
        match self:
            case Difficulty.BEGINNER:
                return 1
            case Difficulty.CASUAL:
                return 3
            case Difficulty.INTERMEDIATE:
                return 6
            case Difficulty.ADVANCED:
                return 10
            case Difficulty.MASTER:
                return 15

    @property
    def time_limit_ms(self) -> int:
        """Search time ceiling in milliseconds."""
        match self:
            case Difficulty.BEGINNER:
                return 100
            case Difficulty.CASUAL:
                return 250
            case Difficulty.INTERMEDIATE:
                return 500
            case Difficulty.ADVANCED:
                return 1000
            case Difficulty.MASTER:
                return 2000

    @property
    def thinking_delay_range_ms(self) -> tuple[int, int]:
        """Realistic thinking delay range in ms (min_ms, max_ms) to simulate human ponder time."""
        match self:
            case Difficulty.BEGINNER:
                return (1200, 2000)
            case Difficulty.CASUAL:
                return (1500, 2400)
            case Difficulty.INTERMEDIATE:
                return (2000, 3000)
            case Difficulty.ADVANCED:
                return (2200, 3500)
            case Difficulty.MASTER:
                return (2500, 4000)
