"""Time control domain models and preset configurations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TimeControl:
    """Represents a game time control with base time and increment."""

    name: str
    base_seconds: int
    increment_seconds: int

    @property
    def is_unlimited(self) -> bool:
        """True if the game has no time constraints."""
        return self.base_seconds <= 0

    @property
    def total_base_ms(self) -> int:
        """Base time in milliseconds."""
        return self.base_seconds * 1000

    @property
    def increment_ms(self) -> int:
        """Increment per move in milliseconds."""
        return self.increment_seconds * 1000

    def to_pgn_tag(self) -> str:
        """Convert time control to standard PGN TimeControl tag value."""
        if self.is_unlimited:
            return "-"
        if self.increment_seconds > 0:
            return f"{self.base_seconds}+{self.increment_seconds}"
        return f"{self.base_seconds}"

    @classmethod
    def from_pgn_tag(cls, tag: str) -> "TimeControl":
        """Parse standard PGN TimeControl tag into a TimeControl instance."""
        clean = tag.strip()
        if not clean or clean in ("-", "?"):
            return cls.unlimited()

        try:
            if "+" in clean:
                base_str, inc_str = clean.split("+", 1)
                base = int(base_str)
                inc = int(inc_str)
            else:
                base = int(clean)
                inc = 0

            # Match known preset or create custom
            for preset in cls.all_presets():
                if preset.base_seconds == base and preset.increment_seconds == inc:
                    return preset

            mins = base // 60
            name = f"{mins} min" if inc == 0 else f"{mins} min + {inc}s"
            return cls(name=name, base_seconds=base, increment_seconds=inc)
        except (ValueError, TypeError):
            return cls.unlimited()

    @classmethod
    def unlimited(cls) -> "TimeControl":
        return cls(name="Unlimited", base_seconds=0, increment_seconds=0)

    @classmethod
    def bullet_1_0(cls) -> "TimeControl":
        return cls(name="1+0 | Bullet", base_seconds=60, increment_seconds=0)

    @classmethod
    def blitz_3_0(cls) -> "TimeControl":
        return cls(name="3+0 | Blitz", base_seconds=180, increment_seconds=0)

    @classmethod
    def blitz_3_2(cls) -> "TimeControl":
        return cls(name="3+2 | Blitz", base_seconds=180, increment_seconds=2)

    @classmethod
    def blitz_5_0(cls) -> "TimeControl":
        return cls(name="5+0 | Blitz", base_seconds=300, increment_seconds=0)

    @classmethod
    def rapid_10_0(cls) -> "TimeControl":
        return cls(name="10+0 | Rapid", base_seconds=600, increment_seconds=0)

    @classmethod
    def rapid_10_5(cls) -> "TimeControl":
        return cls(name="10+5 | Rapid", base_seconds=600, increment_seconds=5)

    @classmethod
    def rapid_15_10(cls) -> "TimeControl":
        return cls(name="15+10 | Rapid", base_seconds=900, increment_seconds=10)

    @classmethod
    def classical_30_0(cls) -> "TimeControl":
        return cls(name="30+0 | Classical", base_seconds=1800, increment_seconds=0)

    @classmethod
    def custom(cls, base_minutes: int, increment_seconds: int) -> "TimeControl":
        base_sec = max(0, base_minutes * 60)
        inc_sec = max(0, increment_seconds)
        if base_sec == 0:
            return cls.unlimited()
        name = f"{base_minutes} min" if inc_sec == 0 else f"{base_minutes} min + {inc_sec}s"
        return cls(name=f"{name} | Custom", base_seconds=base_sec, increment_seconds=inc_sec)

    @classmethod
    def all_presets(cls) -> list["TimeControl"]:
        """Standard preset collection ordered by speed."""
        return [
            cls.unlimited(),
            cls.bullet_1_0(),
            cls.blitz_3_0(),
            cls.blitz_3_2(),
            cls.blitz_5_0(),
            cls.rapid_10_0(),
            cls.rapid_10_5(),
            cls.rapid_15_10(),
            cls.classical_30_0(),
        ]
