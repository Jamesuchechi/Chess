"""Tests for GameService chess clock integration and timeout handling."""

from pytestqt.qtbot import QtBot

from chess_desktop.domain.enums import Color, GameStatus
from chess_desktop.domain.time_control import TimeControl
from chess_desktop.services.game_service import GameService


def test_game_service_clock_starts_and_switches(qtbot: QtBot) -> None:
    """Verify timed game starts clock and moves switch turns."""
    service = GameService()
    tc = TimeControl.blitz_3_2()

    service.new_game(time_control=tc)
    assert service.clock.is_running
    assert service.clock.active_color == Color.WHITE

    # Play e4
    with qtbot.waitSignal(service.move_made, timeout=3000):
        assert service.try_move("e2", "e4")

    # Turn should now be Black on the clock
    assert service.clock.active_color == Color.BLACK
    state = service.get_state()
    assert state.turn == Color.BLACK
    assert state.time_control == tc
    # MoveRecord contains recorded clock times
    assert state.moves[-1].white_time_ms is not None

    service.cleanup()


def test_game_service_player_timeout_triggers_loss(qtbot: QtBot) -> None:
    """Verify when a player runs out of time, GameStatus.TIMEOUT is declared and opponent wins."""
    service = GameService()
    tc = TimeControl.blitz_5_0()
    service.new_game(time_control=tc)

    # Fast forward clock near expiration
    service.clock.set_times(white_ms=40, black_ms=300000)

    with qtbot.waitSignal(service.game_over, timeout=2000) as blocker:
        pass  # Clock will expire in ~40ms

    status, msg = blocker.args
    assert status == GameStatus.TIMEOUT
    assert "White ran out of time" in msg
    assert "Black wins" in msg
    assert service.get_state().status == GameStatus.TIMEOUT
    assert not service.clock.is_running

    service.cleanup()


def test_game_service_clock_pauses_on_review(qtbot: QtBot) -> None:
    """Verify clock pauses during historical review and resumes on live."""
    service = GameService()
    service.new_game(time_control=TimeControl.blitz_5_0())

    service.try_move("e2", "e4")
    service.try_move("e7", "e5")

    assert service.clock.is_running
    # Review ply 0
    service.navigate_to_ply(0)
    assert not service.clock.is_running

    # Go back to live
    service.go_to_live()
    assert service.clock.is_running

    service.cleanup()


def test_game_service_undo_restores_clock(qtbot: QtBot) -> None:
    """Verify undo restores recorded clock times from earlier plies."""
    service = GameService()
    service.new_game(time_control=TimeControl.blitz_5_0())

    service.try_move("e2", "e4")
    w_time_after_move1 = service.get_state().moves[-1].white_time_ms

    service.try_move("e7", "e5")

    # Undo Black move
    assert service.undo_move() is True
    assert service.clock.white_time_ms == w_time_after_move1

    service.cleanup()
