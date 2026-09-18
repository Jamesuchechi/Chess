"""Move history panel displaying standard algebraic notation (SAN) moves."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from chess_desktop.domain.game_state import GameState, MoveRecord
from chess_desktop.services.game_service import GameService
from chess_desktop.ui.dialogs.confirm_dialog import ConfirmDialog


class HistoryPanel(QWidget):
    """Panel containing scrollable move history table and game action shortcuts."""

    def __init__(self, game_service: GameService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = game_service
        self.setMinimumWidth(220)
        self.setMaximumWidth(280)

        self._init_ui()

        self._service.state_changed.connect(self.update_history)
        self._service.move_made.connect(self._on_move_made)
        self._service.review_changed.connect(
            lambda _: self.update_history(self._service.get_state())
        )

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # Header
        title = QLabel("Move History", self)
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff;")
        layout.addWidget(title)

        # Move Table
        self._table = QTableWidget(0, 3, self)
        self._table.setHorizontalHeaderLabels(["#", "White", "Black"])
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._table.setStyleSheet(
            """
            QTableWidget {
                background-color: #262626;
                color: #e0e0e0;
                gridline-color: #333333;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #1e1e1e;
                color: #a0a0a0;
                padding: 4px;
                font-weight: bold;
                border: none;
                border-bottom: 1px solid #3d3d3d;
            }
            """
        )
        self._table.cellClicked.connect(self._on_cell_clicked)
        layout.addWidget(self._table)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        flip_btn = QPushButton("Flip Board", self)
        flip_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #383838;
                color: #ffffff;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #484848;
            }
            """
        )
        flip_btn.clicked.connect(self._service.flip_board)
        btn_layout.addWidget(flip_btn)

        new_btn = QPushButton("New Game", self)
        new_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #769656;
                color: #ffffff;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #87ab62;
            }
            """
        )
        new_btn.clicked.connect(self._on_new_game_clicked)
        btn_layout.addWidget(new_btn)

        layout.addLayout(btn_layout)

    def _on_cell_clicked(self, row: int, col: int) -> None:
        moves = self._service.get_state().moves
        if col == 1:
            ply = row * 2 + 1
            if ply <= len(moves):
                self._service.navigate_to_ply(ply)
        elif col == 2:
            ply = row * 2 + 2
            if ply <= len(moves):
                self._service.navigate_to_ply(ply)

    def _on_new_game_clicked(self) -> None:
        state = self._service.get_state()
        if len(state.moves) > 0 and not state.status.is_game_over:
            dlg = ConfirmDialog(
                title="Start New Game?",
                message="Your current game has moves in progress.\n\nDiscard and start new game?",
                confirm_text="Discard & Start",
                cancel_text="Cancel",
                is_destructive=True,
                parent=self,
            )
            if not dlg.exec():
                return
        self._service.new_game()

    def _on_move_made(self, record: MoveRecord) -> None:
        self.update_history(self._service.get_state())

    def update_history(self, state: GameState) -> None:
        """Repopulate move history table from GameState."""
        moves = state.moves
        full_turns = (len(moves) + 1) // 2
        self._table.setRowCount(full_turns)

        active_ply = state.review_ply if state.review_ply is not None else len(moves)

        for i in range(full_turns):
            # Move number column
            num_item = QTableWidgetItem(f"{i + 1}.")
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            num_item.setForeground(QColor("#888888"))
            self._table.setItem(i, 0, num_item)

            # White move
            white_ply = i * 2 + 1
            white_idx = i * 2
            if white_idx < len(moves):
                w_item = QTableWidgetItem(moves[white_idx].san)
                w_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if white_ply == active_ply:
                    w_item.setBackground(QColor("#769656"))
                    w_item.setForeground(QColor("#ffffff"))
                self._table.setItem(i, 1, w_item)
            else:
                self._table.setItem(i, 1, QTableWidgetItem(""))

            # Black move
            black_ply = i * 2 + 2
            black_idx = i * 2 + 1
            if black_idx < len(moves):
                b_item = QTableWidgetItem(moves[black_idx].san)
                b_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if black_ply == active_ply:
                    b_item.setBackground(QColor("#769656"))
                    b_item.setForeground(QColor("#ffffff"))
                self._table.setItem(i, 2, b_item)
            else:
                self._table.setItem(i, 2, QTableWidgetItem(""))

        # Auto scroll to active ply row
        if active_ply > 0 and full_turns > 0:
            target_row = min((active_ply - 1) // 2, full_turns - 1)
            scroll_item = self._table.item(target_row, 0)
            if scroll_item is not None:
                self._table.scrollToItem(scroll_item)
