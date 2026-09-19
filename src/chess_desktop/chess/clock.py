"""Monotonic chess clock implementation for timed games."""

import logging
import time
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal

from chess_desktop.domain.enums import Color
from chess_desktop.domain.time_control import TimeControl

logger = logging.getLogger(__name__)


class ChessClock(QObject):
    """Authoritative digital chess clock tracking player remaining times with monotonic precision."""

    tick = Signal(int, int)  # (white_time_ms, black_time_ms)
    timeout = Signal(object)  # (Color) - color of player whose time expired
    active_color_changed = Signal(object)  # (Color | None)

    def __init__(
        self,
        time_control: TimeControl | None = None,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._time_control = time_control or TimeControl.unlimited()
        self._white_ms = self._time_control.total_base_ms
        self._black_ms = self._time_control.total_base_ms
        self._active_color: Color | None = None
        self._last_monotonic: float | None = None
        self._is_running = False

        self._timer = QTimer(self)
        self._timer.setInterval(50)  # 50ms tick frequency for smooth sub-second updates
        self._timer.timeout.connect(self._on_timer_tick)

    @property
    def time_control(self) -> TimeControl:
        """Current TimeControl configuration."""
        return self._time_control

    @property
    def white_time_ms(self) -> int:
        """Remaining time for White in milliseconds."""
        return self._white_ms

    @property
    def black_time_ms(self) -> int:
        """Remaining time for Black in milliseconds."""
        return self._black_ms

    @property
    def is_running(self) -> bool:
        """True if clock timer is actively ticking."""
        return self._is_running

    @property
    def active_color(self) -> Color | None:
        """Color currently on the clock."""
        return self._active_color

    def reset(
        self,
        time_control: TimeControl | None = None,
        white_ms: int | None = None,
        black_ms: int | None = None,
    ) -> None:
        """Reset clocks with new or existing time control and optional explicit times."""
        self.stop()
        if time_control is not None:
            self._time_control = time_control

        self._white_ms = white_ms if white_ms is not None else self._time_control.total_base_ms
        self._black_ms = black_ms if black_ms is not None else self._time_control.total_base_ms
        self._active_color = None
        self._last_monotonic = None
        self.tick.emit(self._white_ms, self._black_ms)

    def start(self, initial_color: Color = Color.WHITE) -> None:
        """Start ticking down for the initial color."""
        if self._time_control.is_unlimited:
            return

        self._active_color = initial_color
        self._last_monotonic = time.monotonic()
        self._is_running = True
        self._timer.start()
        self.active_color_changed.emit(self._active_color)
        self.tick.emit(self._white_ms, self._black_ms)

    def switch_turn(self, new_turn: Color) -> None:
        """Switch clock to the next player and credit increment to the player who just moved."""
        if self._time_control.is_unlimited:
            return

        now = time.monotonic()
        # Deduct time for the player who just moved
        if self._is_running and self._active_color is not None and self._last_monotonic is not None:
            elapsed_ms = int((now - self._last_monotonic) * 1000)
            if self._active_color == Color.WHITE:
                self._white_ms = max(0, self._white_ms - elapsed_ms)
                # Credit increment
                self._white_ms += self._time_control.increment_ms
                if self._white_ms == 0:
                    self._handle_timeout(Color.WHITE)
                    return
            else:
                self._black_ms = max(0, self._black_ms - elapsed_ms)
                # Credit increment
                self._black_ms += self._time_control.increment_ms
                if self._black_ms == 0:
                    self._handle_timeout(Color.BLACK)
                    return

        self._active_color = new_turn
        self._last_monotonic = now

        if not self._is_running:
            self._is_running = True
            self._timer.start()

        self.active_color_changed.emit(self._active_color)
        self.tick.emit(self._white_ms, self._black_ms)

    def pause(self) -> None:
        """Pause clock without clearing the active player or resetting times."""
        if not self._is_running:
            return

        now = time.monotonic()
        if self._active_color is not None and self._last_monotonic is not None:
            elapsed_ms = int((now - self._last_monotonic) * 1000)
            if self._active_color == Color.WHITE:
                self._white_ms = max(0, self._white_ms - elapsed_ms)
            else:
                self._black_ms = max(0, self._black_ms - elapsed_ms)

        self._timer.stop()
        self._is_running = False
        self._last_monotonic = None
        self.tick.emit(self._white_ms, self._black_ms)

    def resume(self) -> None:
        """Resume ticking if not unlimited and an active color exists."""
        if self._time_control.is_unlimited or self._is_running or self._active_color is None:
            return

        self._last_monotonic = time.monotonic()
        self._is_running = True
        self._timer.start()
        self.tick.emit(self._white_ms, self._black_ms)

    def stop(self) -> None:
        """Fully stop the clock."""
        self._timer.stop()
        self._is_running = False
        self._active_color = None
        self._last_monotonic = None
        self.active_color_changed.emit(None)

    def set_times(self, white_ms: int | None, black_ms: int | None) -> None:
        """Directly adjust current player times (e.g. restoring state on undo)."""
        self._white_ms = max(0, white_ms if white_ms is not None else 0)
        self._black_ms = max(0, black_ms if black_ms is not None else 0)
        if self._is_running:
            self._last_monotonic = time.monotonic()
        self.tick.emit(self._white_ms, self._black_ms)

    def set_times_and_turn(
        self, white_ms: int | None, black_ms: int | None, active_turn: Color
    ) -> None:
        """Explicitly restore clocks and set active turn without deducting time or crediting increment."""
        self._white_ms = max(0, white_ms if white_ms is not None else 0)
        self._black_ms = max(0, black_ms if black_ms is not None else 0)
        self._active_color = active_turn
        if not self._time_control.is_unlimited:
            self._last_monotonic = time.monotonic()
            if not self._is_running:
                self._is_running = True
                self._timer.start()
        self.active_color_changed.emit(self._active_color)
        self.tick.emit(self._white_ms, self._black_ms)

    def _on_timer_tick(self) -> None:
        """Periodically update active player remaining time using monotonic clock."""
        if not self._is_running or self._active_color is None or self._time_control.is_unlimited:
            return

        now = time.monotonic()
        if self._last_monotonic is None:
            self._last_monotonic = now
            return

        elapsed_ms = int((now - self._last_monotonic) * 1000)
        self._last_monotonic = now

        if self._active_color == Color.WHITE:
            self._white_ms = max(0, self._white_ms - elapsed_ms)
            if self._white_ms == 0:
                self._handle_timeout(Color.WHITE)
                return
        else:
            self._black_ms = max(0, self._black_ms - elapsed_ms)
            if self._black_ms == 0:
                self._handle_timeout(Color.BLACK)
                return

        self.tick.emit(self._white_ms, self._black_ms)

    def _handle_timeout(self, timed_out_color: Color) -> None:
        """Process time expiration for a player."""
        self.stop()
        self.tick.emit(self._white_ms, self._black_ms)
        logger.info("%s timed out!", timed_out_color.name)
        self.timeout.emit(timed_out_color)
