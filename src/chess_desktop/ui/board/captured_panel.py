"""Captured pieces and player status panel."""

from collections import Counter

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QWidget,
)

import chess_desktop.ui.resources_rc  # noqa: F401
from chess_desktop.domain.enums import Color, PieceType, PlayerType
from chess_desktop.domain.game_state import GameState
from chess_desktop.services.game_service import GameService
from chess_desktop.ui.board.clock_widget import ClockWidget


class CapturedPanel(QWidget):
    """Displays player identity, turn status, captured pieces, and material differential."""

    def __init__(
        self,
        color: Color,
        game_service: GameService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._color = color
        self._service = game_service

        self.setFixedHeight(42)
        self._init_ui()

        self._service.state_changed.connect(self.update_state)
        self._service.clock_ticked.connect(self._on_clock_ticked)
        self._service.clock.active_color_changed.connect(self._on_clock_active_changed)
        self._service.engine_thinking_changed.connect(
            lambda _: self.update_state(self._service.get_state())
        )
        self.update_state(self._service.get_state())

    def _init_ui(self) -> None:
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(8, 4, 8, 4)
        self._layout.setSpacing(10)

        # Turn indicator indicator circle
        self._turn_dot = QLabel(self)
        self._turn_dot.setFixedSize(10, 10)
        self._layout.addWidget(self._turn_dot)

        # Player name label
        name = "White" if self._color == Color.WHITE else "Black"
        self._name_label = QLabel(name, self)
        self._name_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        self._layout.addWidget(self._name_label)

        # Player type badge (BOT / HUMAN)
        self._type_badge = QLabel(self)
        self._type_badge.setStyleSheet(
            """
            QLabel {
                background-color: #2e382b;
                color: #87ab62;
                font-size: 10px;
                font-weight: bold;
                border: 1px solid #4d6638;
                border-radius: 3px;
                padding: 1px 5px;
            }
            """
        )
        self._type_badge.hide()
        self._layout.addWidget(self._type_badge)

        # Captured pieces container
        self._captured_container = QWidget(self)
        self._captured_layout = QHBoxLayout(self._captured_container)
        self._captured_layout.setContentsMargins(0, 0, 0, 0)
        self._captured_layout.setSpacing(2)
        self._layout.addWidget(self._captured_container)

        # Material differential badge (+3, etc.)
        self._diff_badge = QLabel(self)
        self._diff_badge.setStyleSheet(
            """
            QLabel {
                background-color: #383838;
                color: #e0e0e0;
                font-size: 12px;
                font-weight: bold;
                border-radius: 4px;
                padding: 2px 6px;
            }
            """
        )
        self._diff_badge.hide()
        self._layout.addWidget(self._diff_badge)

        self._layout.addStretch()

        # Digital Chess Clock
        self._clock_widget = ClockWidget(self._color, self)
        self._layout.addWidget(self._clock_widget)

    def _on_clock_ticked(self, white_ms: int, black_ms: int) -> None:
        """Handle high-frequency clock tick."""
        time_ms = white_ms if self._color == Color.WHITE else black_ms
        self._clock_widget.set_time_ms(time_ms)

    def _on_clock_active_changed(self, active_color: Color | None) -> None:
        """Handle clock active turn changes."""
        self._clock_widget.set_active(active_color == self._color)

    def update_state(self, state: GameState) -> None:
        """Update display based on active GameState."""
        # Update player name and badge
        game = self._service.get_game()
        player = game.white_player if self._color == Color.WHITE else game.black_player
        self._name_label.setText(player.name)

        if player.player_type == PlayerType.COMPUTER:
            if (
                self._service.is_computer_thinking
                and state.turn == self._color
                and not state.status.is_game_over
            ):
                self._type_badge.setText("🤖 Thinking...")
                self._type_badge.setStyleSheet(
                    """
                    QLabel {
                        background-color: #3b3a24;
                        color: #facc15;
                        font-size: 10px;
                        font-weight: bold;
                        border: 1px solid #716210;
                        border-radius: 3px;
                        padding: 1px 5px;
                    }
                    """
                )
            else:
                self._type_badge.setText("🤖 BOT")
                self._type_badge.setStyleSheet(
                    """
                    QLabel {
                        background-color: #2e382b;
                        color: #87ab62;
                        font-size: 10px;
                        font-weight: bold;
                        border: 1px solid #4d6638;
                        border-radius: 3px;
                        padding: 1px 5px;
                    }
                    """
                )
            self._type_badge.show()
        else:
            self._type_badge.hide()

        # Turn indicator
        is_my_turn = state.turn == self._color and not state.status.is_game_over
        dot_color = "#769656" if is_my_turn else "transparent"
        self._turn_dot.setStyleSheet(f"background-color: {dot_color}; border-radius: 5px;")

        # Clock updates
        tc = state.time_control
        is_unlimited = tc is None or tc.is_unlimited
        self._clock_widget.set_unlimited(is_unlimited)
        if not is_unlimited:
            time_ms = state.white_time_ms if self._color == Color.WHITE else state.black_time_ms
            if time_ms is not None:
                self._clock_widget.set_time_ms(time_ms)
            self._clock_widget.set_active(self._service.clock.active_color == self._color)

        # Clear existing captured piece icons
        while self._captured_layout.count():
            item = self._captured_layout.takeAt(0)
            if item:
                widget = item.widget()
                if widget:
                    widget.deleteLater()

        # Captured pieces: captured_white contains Black pieces taken by White
        captured = state.captured_white if self._color == Color.WHITE else state.captured_black
        counts = Counter(captured)

        # Draw icons for opponent piece types captured
        opp_prefix = "b" if self._color == Color.WHITE else "w"
        piece_order = [
            (PieceType.QUEEN, "Q"),
            (PieceType.ROOK, "R"),
            (PieceType.BISHOP, "B"),
            (PieceType.KNIGHT, "N"),
            (PieceType.PAWN, "P"),
        ]

        for pt, code in piece_order:
            count = counts[pt]
            if count > 0:
                renderer = QSvgRenderer(f":/pieces/{opp_prefix}{code}.svg")
                pixmap = QPixmap(QSize(22, 22))
                pixmap.fill(Qt.GlobalColor.transparent)
                from PySide6.QtGui import QPainter

                painter = QPainter(pixmap)
                renderer.render(painter)
                painter.end()

                for _ in range(count):
                    lbl = QLabel(self)
                    lbl.setPixmap(pixmap)
                    lbl.setFixedSize(22, 22)
                    self._captured_layout.addWidget(lbl)

        # Material diff badge
        diff = state.material_difference
        my_diff = diff if self._color == Color.WHITE else -diff
        if my_diff > 0:
            self._diff_badge.setText(f"+{my_diff}")
            self._diff_badge.show()
        else:
            self._diff_badge.hide()
