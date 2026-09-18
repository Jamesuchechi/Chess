"""Unit tests for TimeControl model and presets."""

from chess_desktop.domain.time_control import TimeControl


def test_time_control_presets() -> None:
    """Verify standard time control presets configuration."""
    unlimited = TimeControl.unlimited()
    assert unlimited.is_unlimited
    assert unlimited.base_seconds == 0
    assert unlimited.increment_seconds == 0
    assert unlimited.to_pgn_tag() == "-"

    bullet = TimeControl.bullet_1_0()
    assert not bullet.is_unlimited
    assert bullet.base_seconds == 60
    assert bullet.increment_seconds == 0
    assert bullet.total_base_ms == 60000
    assert bullet.increment_ms == 0
    assert bullet.to_pgn_tag() == "60"

    blitz = TimeControl.blitz_3_2()
    assert blitz.base_seconds == 180
    assert blitz.increment_seconds == 2
    assert blitz.increment_ms == 2000
    assert blitz.to_pgn_tag() == "180+2"

    rapid = TimeControl.rapid_10_5()
    assert rapid.base_seconds == 600
    assert rapid.increment_seconds == 5
    assert rapid.to_pgn_tag() == "600+5"

    classical = TimeControl.classical_30_0()
    assert classical.base_seconds == 1800
    assert classical.increment_seconds == 0
    assert classical.to_pgn_tag() == "1800"


def test_time_control_pgn_parsing() -> None:
    """Verify parsing PGN TimeControl header strings."""
    tc1 = TimeControl.from_pgn_tag("300+2")
    assert tc1.base_seconds == 300
    assert tc1.increment_seconds == 2

    tc2 = TimeControl.from_pgn_tag("600")
    assert tc2.base_seconds == 600
    assert tc2.increment_seconds == 0

    tc3 = TimeControl.from_pgn_tag("-")
    assert tc3.is_unlimited

    tc4 = TimeControl.from_pgn_tag("invalid")
    assert tc4.is_unlimited


def test_time_control_custom() -> None:
    """Verify custom time control creation."""
    custom = TimeControl.custom(base_minutes=7, increment_seconds=4)
    assert custom.base_seconds == 420
    assert custom.increment_seconds == 4
    assert custom.to_pgn_tag() == "420+4"
