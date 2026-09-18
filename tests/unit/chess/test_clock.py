"""Unit tests for monotonic ChessClock."""

from pytestqt.qtbot import QtBot

from chess_desktop.chess.clock import ChessClock
from chess_desktop.domain.enums import Color
from chess_desktop.domain.time_control import TimeControl


def test_clock_initial_state() -> None:
    """Verify clock initializes correctly with time control."""
    tc = TimeControl.blitz_3_2()
    clock = ChessClock(tc)
    assert clock.white_time_ms == 180000
    assert clock.black_time_ms == 180000
    assert not clock.is_running
    assert clock.active_color is None


def test_clock_monotonic_ticking(qtbot: QtBot) -> None:
    """Verify clock ticks down for the active player using monotonic timing."""
    tc = TimeControl.blitz_5_0()
    clock = ChessClock(tc)

    clock.start(Color.WHITE)
    assert clock.is_running
    assert clock.active_color == Color.WHITE

    # Wait 150ms
    qtbot.wait(150)
    assert clock.white_time_ms < 300000
    # Black time remains untouched
    assert clock.black_time_ms == 300000

    clock.stop()
    assert not clock.is_running


def test_clock_switch_turn_and_increment(qtbot: QtBot) -> None:
    """Verify switching turn credits increment to the player who moved and switches active player."""
    tc = TimeControl(name="10s+2s", base_seconds=10, increment_seconds=2)
    clock = ChessClock(tc)

    clock.start(Color.WHITE)
    qtbot.wait(100)

    # Switch to Black: White should receive 2000ms increment
    white_before = clock.white_time_ms
    clock.switch_turn(Color.BLACK)

    assert clock.active_color == Color.BLACK
    assert clock.white_time_ms > white_before  # Added 2s increment minus ~100ms
    assert clock.black_time_ms == 10000

    clock.stop()


def test_clock_timeout_signal(qtbot: QtBot) -> None:
    """Verify timeout signal is emitted when player's time expires."""
    tc = TimeControl(name="Test", base_seconds=10, increment_seconds=0)
    clock = ChessClock(tc)
    # Manually configure 50ms remaining
    clock.reset(tc, white_ms=50, black_ms=5000)

    with qtbot.waitSignal(clock.timeout, timeout=2000) as blocker:
        clock.start(Color.WHITE)

    assert blocker.args == [Color.WHITE]
    assert clock.white_time_ms == 0
    assert not clock.is_running


def test_clock_pause_and_resume(qtbot: QtBot) -> None:
    """Verify pause stops decrementing and resume continues."""
    tc = TimeControl.blitz_5_0()
    clock = ChessClock(tc)

    clock.start(Color.WHITE)
    qtbot.wait(100)
    clock.pause()
    assert not clock.is_running

    paused_time = clock.white_time_ms
    qtbot.wait(100)
    assert clock.white_time_ms == paused_time  # Did not decrease while paused

    clock.resume()
    assert clock.is_running
    qtbot.wait(100)
    assert clock.white_time_ms < paused_time
    clock.stop()
