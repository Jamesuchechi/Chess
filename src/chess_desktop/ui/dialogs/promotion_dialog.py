"""Pawn promotion selection dialog."""

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import chess_desktop.ui.resources_rc  # noqa: F401 - registers Qt resources
from chess_desktop.domain.enums import Color, PieceType


class PromotionDialog(QDialog):
    """Modal dialog prompting the user to select a promotion piece."""

    def __init__(self, color: Color, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Pawn Promotion")
        self.setModal(True)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint
        )

        self._selected_piece: PieceType = PieceType.QUEEN
        self._color = color

        self._init_ui()

    @property
    def selected_piece(self) -> PieceType:
        """The chosen piece type."""
        return self._selected_piece

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Choose promotion piece:", self)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff;")
        layout.addWidget(title)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        prefix = "w" if self._color == Color.WHITE else "b"
        choices = [
            (PieceType.QUEEN, f":/pieces/{prefix}Q.svg", "Queen"),
            (PieceType.ROOK, f":/pieces/{prefix}R.svg", "Rook"),
            (PieceType.BISHOP, f":/pieces/{prefix}B.svg", "Bishop"),
            (PieceType.KNIGHT, f":/pieces/{prefix}N.svg", "Knight"),
        ]

        for piece_type, res_path, label_text in choices:
            btn = QPushButton(self)
            btn.setToolTip(label_text)
            btn.setFixedSize(72, 72)
            btn.setStyleSheet(
                """
                QPushButton {
                    background-color: #2b2b2b;
                    border: 2px solid #3d3d3d;
                    border-radius: 8px;
                }
                QPushButton:hover {
                    background-color: #404040;
                    border-color: #769656;
                }
                QPushButton:pressed {
                    background-color: #505050;
                }
                """
            )

            # Render SVG into icon
            renderer = QSvgRenderer(res_path)
            pixmap = QPixmap(QSize(56, 56))
            pixmap.fill(Qt.GlobalColor.transparent)
            from PySide6.QtGui import QPainter

            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()

            btn.setIcon(QIcon(pixmap))
            btn.setIconSize(QSize(56, 56))

            # Connect clicked handler
            btn.clicked.connect(lambda _, pt=piece_type: self._select_and_accept(pt))
            button_layout.addWidget(btn)

        layout.addLayout(button_layout)

    def _select_and_accept(self, piece_type: PieceType) -> None:
        self._selected_piece = piece_type
        self.accept()
