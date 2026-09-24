"""Dialog for browsing, opening, and managing saved games from SQLite."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from chess_desktop.persistence.models import SavedGameSummary
from chess_desktop.persistence.repositories import GameRepository
from chess_desktop.ui.dialogs.confirm_dialog import ConfirmDialog


class OpenGameDialog(QDialog):
    """Modal dialog displaying list of saved games."""

    def __init__(
        self,
        repository: GameRepository,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._repo = repository
        self._selected_game_id: str | None = None
        self._review_requested: bool = False
        self._all_games: list[SavedGameSummary] = []

        self.setWindowTitle("Open Saved Game")
        self.resize(700, 420)
        self.setModal(True)

        self._init_ui()
        self._load_games()

    @property
    def selected_game_id(self) -> str | None:
        """Return ID of chosen game, or None if cancelled."""
        return self._selected_game_id

    @property
    def review_requested(self) -> bool:
        """Return True if user requested Review Game on the selected game."""
        return self._review_requested

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header with filter
        header_layout = QHBoxLayout()
        lbl = QLabel("Saved Games", self)
        lbl.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: bold;")
        header_layout.addWidget(lbl)

        header_layout.addStretch()

        self._filter_edit = QLineEdit(self)
        self._filter_edit.setPlaceholderText("Filter games...")
        self._filter_edit.setFixedWidth(220)
        self._filter_edit.setStyleSheet(
            """
            QLineEdit {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px 8px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #769656;
            }
            """
        )
        self._filter_edit.textChanged.connect(self._apply_filter)
        header_layout.addWidget(self._filter_edit)
        layout.addLayout(header_layout)

        # Games Table
        self._table = QTableWidget(self)
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(
            ["Title", "White", "Black", "Result", "Moves", "Last Saved"]
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            5, QHeaderView.ResizeMode.ResizeToContents
        )

        self._table.setStyleSheet(
            """
            QTableWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
                border: 1px solid #333333;
                border-radius: 4px;
                gridline-color: #2b2b2b;
                selection-background-color: #384f29;
                selection-color: #ffffff;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #262626;
                color: #aaaaaa;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #333333;
                font-weight: bold;
                font-size: 11px;
            }
            """
        )
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.itemDoubleClicked.connect(lambda _: self._on_open())
        layout.addWidget(self._table)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self._delete_btn = QPushButton("Delete Game", self)
        self._delete_btn.setEnabled(False)
        self._delete_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #2b2b2b;
                color: #ef4444;
                border: 1px solid #4b1a1a;
                padding: 6px 14px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover:enabled {
                background-color: #451a1a;
            }
            QPushButton:disabled {
                color: #666666;
                border-color: #333333;
            }
            """
        )
        self._delete_btn.clicked.connect(self._on_delete)
        btn_layout.addWidget(self._delete_btn)

        btn_layout.addStretch()

        self._cancel_btn = QPushButton("Cancel", self)
        self._cancel_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #383838;
                color: #e0e0e0;
                padding: 6px 14px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #484848;
            }
            """
        )
        self._cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._cancel_btn)

        self._open_btn = QPushButton("Open Game", self)
        self._open_btn.setEnabled(False)
        self._open_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #383838;
                color: #ffffff;
                padding: 6px 14px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover:enabled {
                background-color: #484848;
            }
            QPushButton:disabled {
                background-color: #2b2b2b;
                color: #666666;
            }
            """
        )
        self._open_btn.clicked.connect(self._on_open)
        btn_layout.addWidget(self._open_btn)

        self._review_btn = QPushButton("🔍 Review Game", self)
        self._review_btn.setEnabled(False)
        self._review_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #1e3a5f;
                color: #60c0ff;
                padding: 6px 16px;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
                border: 1px solid #2a5fa0;
            }
            QPushButton:hover:enabled {
                background-color: #2a5fa0;
                color: #ffffff;
            }
            QPushButton:disabled {
                background-color: #1a2a3a;
                color: #3a6080;
                border-color: #1a3050;
            }
            """
        )
        self._review_btn.clicked.connect(self._on_review)
        btn_layout.addWidget(self._review_btn)

        layout.addLayout(btn_layout)

    def _load_games(self) -> None:
        """Fetch all games from repository."""
        self._all_games = self._repo.list_games()
        self._populate_table(self._all_games)

    def _populate_table(self, games: list[SavedGameSummary]) -> None:
        self._table.setRowCount(len(games))
        for row, g in enumerate(games):
            item_title = QTableWidgetItem(g.title)
            item_title.setData(Qt.ItemDataRole.UserRole, g.game_id)

            item_white = QTableWidgetItem(g.white_name)
            item_black = QTableWidgetItem(g.black_name)
            item_result = QTableWidgetItem(g.result)
            item_result.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_moves = QTableWidgetItem(str(g.move_count))
            item_moves.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            date_str = g.updated_at[:10] if len(g.updated_at) >= 10 else g.updated_at
            item_date = QTableWidgetItem(date_str)
            item_date.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self._table.setItem(row, 0, item_title)
            self._table.setItem(row, 1, item_white)
            self._table.setItem(row, 2, item_black)
            self._table.setItem(row, 3, item_result)
            self._table.setItem(row, 4, item_moves)
            self._table.setItem(row, 5, item_date)

        self._on_selection_changed()

    def _apply_filter(self, text: str) -> None:
        query = text.lower().strip()
        if not query:
            self._populate_table(self._all_games)
            return

        filtered = [
            g
            for g in self._all_games
            if query in g.title.lower()
            or query in g.white_name.lower()
            or query in g.black_name.lower()
        ]
        self._populate_table(filtered)

    def _on_selection_changed(self) -> None:
        selected_rows = self._table.selectionModel().selectedRows()
        has_sel = len(selected_rows) > 0
        self._open_btn.setEnabled(has_sel)
        self._review_btn.setEnabled(has_sel)
        self._delete_btn.setEnabled(has_sel)

    def _get_current_selected_id(self) -> str | None:
        selected_rows = self._table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        row = selected_rows[0].row()
        item = self._table.item(row, 0)
        if item is not None:
            game_id = item.data(Qt.ItemDataRole.UserRole)
            return str(game_id) if game_id is not None else None
        return None

    def _on_open(self) -> None:
        game_id = self._get_current_selected_id()
        if game_id:
            self._selected_game_id = game_id
            self._review_requested = False
            self.accept()

    def _on_review(self) -> None:
        game_id = self._get_current_selected_id()
        if game_id:
            self._selected_game_id = game_id
            self._review_requested = True
            self.accept()

    def _on_delete(self) -> None:
        game_id = self._get_current_selected_id()
        if not game_id:
            return

        dlg = ConfirmDialog(
            title="Delete Saved Game",
            message="Are you sure you want to permanently delete this saved game?",
            confirm_text="Delete",
            cancel_text="Cancel",
            is_destructive=True,
            parent=self,
        )
        if dlg.exec():
            self._repo.delete(game_id)
            self._load_games()
