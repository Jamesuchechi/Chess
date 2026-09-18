"""Digital chess clock widget displaying remaining player time."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QWidget

from chess_desktop.domain.enums import Color


class ClockWidget(QWidget):
    """Digital LCD-style chess clock widget with sub-second precision when low on time."""

    def __init__(
        self,
        color: Color,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._color = color
        self._time_ms: int = 0
        self._is_active: bool = False
        self._is_unlimited: bool = True

        self.setFixedSize(88, 32)
        self._label = QLabel("05:00", self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setGeometry(0, 0, 88, 32)

        self._update_display()

    @property
    def color(self) -> Color:
        return self._color

    def set_unlimited(self, unlimited: bool) -> None:
        """Hide widget if time control is unlimited."""
        self._is_unlimited = unlimited
        self.setVisible(not unlimited)

    def set_time_ms(self, time_ms: int) -> None:
        """Update remaining time in milliseconds."""
        self._time_ms = max(0, time_ms)
        self._update_display()

    def set_active(self, is_active: bool) -> None:
        """Set whether this clock is actively ticking."""
        if self._is_active != is_active:
            self._is_active = is_active
            self._update_display()

    @staticmethod
    def format_time(time_ms: int) -> str:
        """Format milliseconds into MM:SS or SS.T."""
        if time_ms <= 0:
            return "00:00.0"

        total_seconds = time_ms / 1000.0
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        tenths = int((time_ms % 1000) // 100)

        if total_seconds < 20.0:
            # Sub-second precision for time scrambles
            return f"{seconds:02d}.{tenths}"
        return f"{minutes:02d}:{seconds:02d}"

    def _update_display(self) -> None:
        text = self.format_time(self._time_ms)
        self._label.setText(text)

        # Style based on state and remaining time
        if self._time_ms <= 0 and not self._is_unlimited:
            # Timed out
            self._label.setStyleSheet(
                """
                QLabel {
                    background-color: #8b0000;
                    color: #ffffff;
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 15px;
                    font-weight: bold;
                    border: 2px solid #ff3333;
                    border-radius: 6px;
                }
                """
            )
        elif self._time_ms < 10000 and not self._is_unlimited:
            # Critical time (< 10s)
            self._label.setStyleSheet(
                """
                QLabel {
                    background-color: #4a1515;
                    color: #ff6b6b;
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 15px;
                    font-weight: bold;
                    border: 2px solid #e04444;
                    border-radius: 6px;
                }
                """
            )
        elif self._time_ms < 30000 and not self._is_unlimited:
            # Warning time (< 30s)
            self._label.setStyleSheet(
                """
                QLabel {
                    background-color: #3d2c14;
                    color: #ffb84d;
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 15px;
                    font-weight: bold;
                    border: 2px solid #e6912c;
                    border-radius: 6px;
                }
                """
            )
        elif self._is_active:
            # Active / Ticking
            self._label.setStyleSheet(
                """
                QLabel {
                    background-color: #2b2b2b;
                    color: #ffffff;
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 15px;
                    font-weight: bold;
                    border: 2px solid #81b64c;
                    border-radius: 6px;
                }
                """
            )
        else:
            # Inactive
            self._label.setStyleSheet(
                """
                QLabel {
                    background-color: #1e1e1e;
                    color: #8c8c8c;
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 15px;
                    font-weight: bold;
                    border: 1px solid #383838;
                    border-radius: 6px;
                }
                """
            )
