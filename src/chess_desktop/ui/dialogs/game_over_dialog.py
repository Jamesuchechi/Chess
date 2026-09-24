"""Game over announcement dialog."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from chess_desktop.domain.enums import GameStatus


class GameOverDialog(QDialog):
    """Modal dialog announcing game termination with options to review or start new."""

    def __init__(
        self,
        status: GameStatus,
        message: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Game Over")
        self.setModal(True)
        self.setMinimumWidth(320)

        self._status = status
        self._message = message
        self._start_new_game = False
        self._analyse_requested = False

        self._init_ui()

    @property
    def start_new_game_requested(self) -> bool:
        """True if player clicked New Game button."""
        return self._start_new_game

    @property
    def analyse_requested(self) -> bool:
        """True if player clicked Review Game button."""
        return self._analyse_requested

    @property
    def review_game_requested(self) -> bool:
        """True if player clicked Review Game button."""
        return self._analyse_requested

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        status_heading = "GAME OVER"
        if self._status == GameStatus.CHECKMATE:
            status_heading = "CHECKMATE"
        elif self._status.is_draw:
            status_heading = "DRAW"

        title = QLabel(status_heading, self)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: 800; color: #769656;")
        layout.addWidget(title)

        desc = QLabel(self._message, self)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 14px; color: #dddddd; padding-bottom: 8px;")
        layout.addWidget(desc)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        review_btn = QPushButton("Review Board", self)
        review_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            """
        )
        review_btn.clicked.connect(self.reject)
        btn_layout.addWidget(review_btn)

        analyse_btn = QPushButton("🔍 Review Game", self)
        analyse_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #1e3a5f;
                color: #60c0ff;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
                border: 1px solid #2a5fa0;
            }
            QPushButton:hover {
                background-color: #2a5fa0;
                color: #ffffff;
            }
            """
        )
        analyse_btn.clicked.connect(self._on_analyse)
        btn_layout.addWidget(analyse_btn)

        new_game_btn = QPushButton("New Game", self)
        new_game_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #769656;
                color: #ffffff;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #87ab62;
            }
            """
        )
        new_game_btn.clicked.connect(self._on_new_game)
        btn_layout.addWidget(new_game_btn)

        layout.addLayout(btn_layout)

    def _on_new_game(self) -> None:
        self._start_new_game = True
        self.accept()

    def _on_analyse(self) -> None:
        self._analyse_requested = True
        self.accept()
