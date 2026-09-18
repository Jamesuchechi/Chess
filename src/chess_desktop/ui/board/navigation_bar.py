"""Navigation and game action toolbar."""

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from chess_desktop.domain.game_state import GameState
from chess_desktop.services.game_service import GameService
from chess_desktop.ui.dialogs.confirm_dialog import ConfirmDialog


class NavigationBar(QWidget):
    """Bar containing move navigation, undo, draw, resign, and review indicators."""

    def __init__(self, game_service: GameService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = game_service
        self.setFixedHeight(46)

        self._init_ui()

        self._service.state_changed.connect(self._on_state_changed)
        self._service.review_changed.connect(self._on_review_changed)
        self._on_state_changed(self._service.get_state())

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        # Style for standard nav buttons
        btn_style = """
            QPushButton {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px 10px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border-color: #555555;
            }
            QPushButton:disabled {
                background-color: #1f1f1f;
                color: #555555;
                border-color: #2b2b2b;
            }
        """

        # Navigation step buttons
        self._first_btn = QPushButton("|<<", self)
        self._first_btn.setToolTip("First Move (Home)")
        self._first_btn.setStyleSheet(btn_style)
        self._first_btn.clicked.connect(self._service.go_to_start)
        layout.addWidget(self._first_btn)

        self._prev_btn = QPushButton("<", self)
        self._prev_btn.setToolTip("Previous Move (Left Arrow)")
        self._prev_btn.setStyleSheet(btn_style)
        self._prev_btn.clicked.connect(self._service.step_backward)
        layout.addWidget(self._prev_btn)

        self._next_btn = QPushButton(">", self)
        self._next_btn.setToolTip("Next Move (Right Arrow)")
        self._next_btn.setStyleSheet(btn_style)
        self._next_btn.clicked.connect(self._service.step_forward)
        layout.addWidget(self._next_btn)

        self._last_btn = QPushButton(">>|", self)
        self._last_btn.setToolTip("Current Live Position (End)")
        self._last_btn.setStyleSheet(btn_style)
        self._last_btn.clicked.connect(self._service.go_to_live)
        layout.addWidget(self._last_btn)

        layout.addSpacing(8)

        # Undo button
        self._undo_btn = QPushButton("Undo", self)
        self._undo_btn.setToolTip("Undo Last Move (Ctrl+Z)")
        self._undo_btn.setStyleSheet(btn_style)
        self._undo_btn.clicked.connect(self._service.undo_move)
        layout.addWidget(self._undo_btn)

        # Draw button
        self._draw_btn = QPushButton("Draw", self)
        self._draw_btn.setToolTip("Offer Draw")
        self._draw_btn.setStyleSheet(btn_style)
        self._draw_btn.clicked.connect(self._on_offer_draw)
        layout.addWidget(self._draw_btn)

        # Resign button
        self._resign_btn = QPushButton("Resign", self)
        self._resign_btn.setToolTip("Resign Game")
        self._resign_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #2b2b2b;
                color: #e57373;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px 10px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #1f1f1f;
                color: #555555;
                border-color: #2b2b2b;
            }
            """
        )
        self._resign_btn.clicked.connect(self._on_resign)
        layout.addWidget(self._resign_btn)

        layout.addStretch()

        # Review mode banner indicator with Jump to Live button
        self._review_container = QWidget(self)
        rev_layout = QHBoxLayout(self._review_container)
        rev_layout.setContentsMargins(0, 0, 0, 0)
        rev_layout.setSpacing(8)

        self._review_lbl = QLabel(self._review_container)
        self._review_lbl.setStyleSheet("color: #f59e0b; font-size: 12px; font-weight: bold;")
        rev_layout.addWidget(self._review_lbl)

        self._resume_btn = QPushButton("Resume Game", self._review_container)
        self._resume_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #769656;
                color: #ffffff;
                font-size: 11px;
                font-weight: bold;
                padding: 3px 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #87ab62;
            }
            """
        )
        self._resume_btn.clicked.connect(self._service.go_to_live)
        rev_layout.addWidget(self._resume_btn)

        self._review_container.hide()
        layout.addWidget(self._review_container)

    def _on_state_changed(self, state: GameState) -> None:
        is_over = state.status.is_game_over
        total_moves = len(state.moves)
        curr_ply = state.review_ply if state.review_ply is not None else total_moves

        self._first_btn.setEnabled(curr_ply > 0)
        self._prev_btn.setEnabled(curr_ply > 0)
        self._next_btn.setEnabled(curr_ply < total_moves)
        self._last_btn.setEnabled(curr_ply < total_moves)

        self._undo_btn.setEnabled(self._service.can_undo)
        self._draw_btn.setEnabled(not is_over)
        self._resign_btn.setEnabled(not is_over)

        self._update_review_indicator(state)

    def _on_review_changed(self, ply: int | None) -> None:
        state = self._service.get_state()
        self._on_state_changed(state)

    def _update_review_indicator(self, state: GameState) -> None:
        if state.is_reviewing:
            ply = state.review_ply or 0
            move_num = (ply + 1) // 2 + 1 if ply % 2 == 0 else (ply + 1) // 2
            side = "White" if ply % 2 == 0 else "Black"
            self._review_lbl.setText(f"Viewing move {move_num} ({side}) — Board Read-Only")
            self._review_container.show()
        else:
            self._review_container.hide()

    def _on_offer_draw(self) -> None:
        state = self._service.get_state()
        turn_str = state.turn.value.capitalize()
        opp_str = state.turn.opposite.value.capitalize()

        dlg = ConfirmDialog(
            title="Offer Draw",
            message=f"{turn_str} has offered a draw.\n\nDoes {opp_str} accept?",
            confirm_text="Accept Draw",
            cancel_text="Decline",
            is_destructive=False,
            parent=self,
        )
        if dlg.exec():
            self._service.accept_draw()

    def _on_resign(self) -> None:
        state = self._service.get_state()
        turn_str = state.turn.value.capitalize()

        dlg = ConfirmDialog(
            title="Resign Game",
            message=f"Are you sure you want to resign as {turn_str}?",
            confirm_text="Resign",
            cancel_text="Cancel",
            is_destructive=True,
            parent=self,
        )
        if dlg.exec():
            self._service.resign(state.turn)
