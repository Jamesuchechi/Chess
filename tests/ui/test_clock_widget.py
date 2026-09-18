"""UI tests for ClockWidget digital chess clock."""

from pytestqt.qtbot import QtBot

from chess_desktop.domain.enums import Color
from chess_desktop.ui.board.clock_widget import ClockWidget


def test_clock_widget_formatting() -> None:
    """Verify time formatting for minutes/seconds and sub-second precision."""
    assert ClockWidget.format_time(300000) == "05:00"
    assert ClockWidget.format_time(65000) == "01:05"
    # Under 20s shows tenths
    assert ClockWidget.format_time(19400) == "19.4"
    assert ClockWidget.format_time(8200) == "08.2"
    assert ClockWidget.format_time(0) == "00:00.0"


def test_clock_widget_state_transitions(qtbot: QtBot) -> None:
    """Verify clock widget updates time and displays correctly."""
    widget = ClockWidget(Color.WHITE)
    qtbot.addWidget(widget)
    widget.show()

    widget.set_time_ms(180000)
    assert widget._label.text() == "03:00"

    widget.set_active(True)
    assert widget._is_active

    # Unlimited hide
    widget.set_unlimited(True)
    assert not widget.isVisible()

    widget.set_unlimited(False)
    assert widget.isVisible()
