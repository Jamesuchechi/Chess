from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from chess_desktop.domain.analysis import GameAnalysis, MoveClassification
from chess_desktop.domain.enums import PlayerType
from chess_desktop.domain.game_state import GameState, MoveRecord
from chess_desktop.services.game_service import GameService


class HistoryPanel(QWidget):
    """Panel containing match info, engine thinking animation, move history table, and game actions."""

    new_game_requested = Signal()
    analysis_requested = Signal()  # emitted when user clicks Analyse/Review button

    def __init__(self, game_service: GameService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = game_service
        self.setMinimumWidth(240)
        self.setMaximumWidth(320)

        self._anim_frame = 0
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(350)
        self._anim_timer.timeout.connect(self._on_thinking_tick)

        self._analysis: GameAnalysis | None = None

        self._init_ui()

        self._service.state_changed.connect(self.update_history)
        self._service.move_made.connect(self._on_move_made)
        self._service.review_changed.connect(
            lambda _: self.update_history(self._service.get_state())
        )
        self._service.engine_thinking_changed.connect(self._on_engine_thinking_changed)
        self.update_history(self._service.get_state())

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Match Info Card (Chess.com style)
        self._match_card = QFrame(self)
        self._match_card.setStyleSheet(
            """
            QFrame {
                background-color: #262626;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 4px;
            }
            """
        )
        card_layout = QVBoxLayout(self._match_card)
        card_layout.setContentsMargins(8, 6, 8, 6)
        card_layout.setSpacing(4)

        self._match_mode_lbl = QLabel("🤖 Play vs Computer", self._match_card)
        self._match_mode_lbl.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #769656; border: none; background: transparent;"
        )
        card_layout.addWidget(self._match_mode_lbl)

        self._match_opponent_lbl = QLabel("Stockfish (Intermediate)", self._match_card)
        self._match_opponent_lbl.setStyleSheet(
            "font-size: 11px; color: #b0b0b0; border: none; background: transparent;"
        )
        card_layout.addWidget(self._match_opponent_lbl)
        layout.addWidget(self._match_card)

        # Engine Thinking Visual Indicator Card
        self._thinking_card = QFrame(self)
        self._thinking_card.setStyleSheet(
            """
            QFrame {
                background-color: #2b2814;
                border: 1px solid #856f14;
                border-radius: 6px;
                padding: 4px 8px;
            }
            """
        )
        think_layout = QHBoxLayout(self._thinking_card)
        think_layout.setContentsMargins(8, 6, 8, 6)
        think_layout.setSpacing(8)

        self._thinking_icon = QLabel("⚡", self._thinking_card)
        self._thinking_icon.setStyleSheet("font-size: 13px; border: none; background: transparent;")
        think_layout.addWidget(self._thinking_icon)

        self._thinking_lbl = QLabel("Engine thinking...", self._thinking_card)
        self._thinking_lbl.setStyleSheet(
            "font-size: 12px; font-weight: bold; color: #facc15; border: none; background: transparent;"
        )
        think_layout.addWidget(self._thinking_lbl)
        think_layout.addStretch()

        self._thinking_card.hide()
        layout.addWidget(self._thinking_card)

        # Move Table Header
        title = QLabel("Move History", self)
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
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
                color: #888888;
                padding: 4px;
                border: none;
                border-bottom: 1px solid #3d3d3d;
                font-weight: bold;
                font-size: 11px;
            }
            """
        )
        self._table.cellClicked.connect(self._on_cell_clicked)
        layout.addWidget(self._table, stretch=1)

        # Selected move alternative card (shows engine alternative when move is clicked)
        self._alt_card = QFrame(self)
        self._alt_card.setStyleSheet(
            """
            QFrame {
                background-color: #1a2332;
                border: 1px solid #2a5fa0;
                border-radius: 6px;
                padding: 4px 8px;
            }
            """
        )
        alt_layout = QVBoxLayout(self._alt_card)
        alt_layout.setContentsMargins(6, 4, 6, 4)
        alt_layout.setSpacing(2)
        self._alt_move_lbl = QLabel("", self._alt_card)
        self._alt_move_lbl.setStyleSheet(
            "font-size: 11px; font-weight: bold; color: #ffffff; border: none; background: transparent;"
        )
        self._alt_best_lbl = QLabel("", self._alt_card)
        self._alt_best_lbl.setStyleSheet(
            "font-size: 11px; color: #76c076; border: none; background: transparent;"
        )
        alt_layout.addWidget(self._alt_move_lbl)
        alt_layout.addWidget(self._alt_best_lbl)
        self._alt_card.hide()
        layout.addWidget(self._alt_card)

        # Action Buttons (Hint, Flip, New)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        hint_btn = QPushButton("💡 Hint", self)
        hint_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                padding: 6px 10px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0369a1;
                color: #ffffff;
            }
            """
        )
        hint_btn.clicked.connect(self._service.request_hint)
        btn_layout.addWidget(hint_btn)

        flip_btn = QPushButton("Flip", self)
        flip_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #383838;
                color: #ffffff;
                padding: 6px 10px;
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

        new_btn = QPushButton("New", self)
        new_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #769656;
                color: #ffffff;
                padding: 6px 10px;
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

        # Accuracy bar and Summary Card (hidden until analysis is available)
        self._accuracy_bar = QFrame(self)
        self._accuracy_bar.setStyleSheet(
            """
            QFrame {
                background-color: #1e1e28;
                border: 1px solid #3d3d4d;
                border-radius: 6px;
                padding: 6px;
            }
            """
        )
        acc_layout = QVBoxLayout(self._accuracy_bar)
        acc_layout.setContentsMargins(8, 6, 8, 6)
        acc_layout.setSpacing(4)

        summary_title = QLabel("📊 Game Review", self._accuracy_bar)
        summary_title.setStyleSheet(
            "font-size: 12px; font-weight: bold; color: #60c0ff; border: none; background: transparent;"
        )
        acc_layout.addWidget(summary_title)

        # Dual-color visual eval/accuracy bar
        eval_bar_container = QFrame(self._accuracy_bar)
        eval_bar_container.setFixedHeight(6)
        eval_bar_container.setStyleSheet(
            "background-color: #333333; border-radius: 3px; border: none;"
        )
        bar_layout = QHBoxLayout(eval_bar_container)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        bar_layout.setSpacing(0)

        self._eval_bar_white = QFrame(eval_bar_container)
        self._eval_bar_white.setStyleSheet(
            "background-color: #ffffff; border-top-left-radius: 3px; border-bottom-left-radius: 3px;"
        )
        self._eval_bar_black = QFrame(eval_bar_container)
        self._eval_bar_black.setStyleSheet(
            "background-color: #404040; border-top-right-radius: 3px; border-bottom-right-radius: 3px;"
        )
        bar_layout.addWidget(self._eval_bar_white, stretch=50)
        bar_layout.addWidget(self._eval_bar_black, stretch=50)
        acc_layout.addWidget(eval_bar_container)

        self._acc_white_lbl = QLabel("White: --%", self._accuracy_bar)
        self._acc_white_lbl.setStyleSheet(
            "font-size: 11px; color: #f0f0f0; border: none; background: transparent;"
        )
        acc_layout.addWidget(self._acc_white_lbl)

        self._acc_black_lbl = QLabel("Black: --%", self._accuracy_bar)
        self._acc_black_lbl.setStyleSheet(
            "font-size: 11px; color: #b0b0b0; border: none; background: transparent;"
        )
        acc_layout.addWidget(self._acc_black_lbl)

        self._accuracy_bar.hide()
        layout.addWidget(self._accuracy_bar)

        # Analyse / Review Game button (visible only when game is over)
        self._analyse_btn = QPushButton("🔍 Review Game", self)
        self._analyse_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #1e3a5f;
                color: #60c0ff;
                border: 1px solid #2a5fa0;
                padding: 6px 10px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover:enabled {
                background-color: #2a5fa0;
                color: #ffffff;
            }
            QPushButton:disabled {
                background-color: #1a2a3a;
                color: #4a6a8a;
                border-color: #1a3050;
            }
            """
        )
        self._analyse_btn.clicked.connect(self.analysis_requested)
        self._analyse_btn.hide()
        layout.addWidget(self._analyse_btn)

    def _on_engine_thinking_changed(self, is_thinking: bool) -> None:
        """Show or hide animated engine thinking card."""
        if is_thinking:
            self._anim_frame = 0
            self._thinking_lbl.setText("Engine thinking •")
            self._thinking_card.show()
            self._anim_timer.start()
        else:
            self._anim_timer.stop()
            self._thinking_card.hide()

    def _on_thinking_tick(self) -> None:
        """Advance thinking animation spinner."""
        self._anim_frame = (self._anim_frame + 1) % 4
        dots = "•" * (self._anim_frame + 1)
        icons = ["⚡", "⏳", "✨", "🧠"]
        self._thinking_icon.setText(icons[self._anim_frame])
        self._thinking_lbl.setText(f"Engine thinking {dots}")

    def _on_cell_clicked(self, row: int, col: int) -> None:
        moves = self._service.get_state().moves
        ply = None
        if col == 1:
            ply = row * 2 + 1
        elif col == 2:
            ply = row * 2 + 2

        if ply is not None and ply <= len(moves):
            self._service.navigate_to_ply(ply)
            self._update_alternative_display(ply)

    def _on_new_game_clicked(self) -> None:
        self.new_game_requested.emit()

    def _on_move_made(self, record: MoveRecord) -> None:
        self.update_history(self._service.get_state())

    def apply_analysis(self, analysis: GameAnalysis) -> None:
        """Annotate move cells with classification badges and show accuracy bar."""
        self._analysis = analysis
        self.set_analysis_idle()

        # Count best moves and blunders for white and black
        white_best = sum(
            1
            for m in analysis.moves
            if m.ply % 2 == 1
            and m.classification in (MoveClassification.BEST, MoveClassification.BRILLIANT)
        )
        white_blunders = sum(
            1
            for m in analysis.moves
            if m.ply % 2 == 1 and m.classification == MoveClassification.BLUNDER
        )
        black_best = sum(
            1
            for m in analysis.moves
            if m.ply % 2 == 0
            and m.classification in (MoveClassification.BEST, MoveClassification.BRILLIANT)
        )
        black_blunders = sum(
            1
            for m in analysis.moves
            if m.ply % 2 == 0 and m.classification == MoveClassification.BLUNDER
        )

        self._acc_white_lbl.setText(
            f"White: {analysis.white_accuracy:.1f}%  |  ★ {white_best}  ?? {white_blunders}"
        )
        self._acc_black_lbl.setText(
            f"Black: {analysis.black_accuracy:.1f}%  |  ★ {black_best}  ?? {black_blunders}"
        )

        self._accuracy_bar.show()
        self.update_history(self._service.get_state())

    def set_analysis_progress(self, done: int, total: int) -> None:
        """Update button state during background evaluation."""
        self._analyse_btn.setEnabled(False)
        self._analyse_btn.setText(f"Analyzing ({done}/{total})...")
        self._analyse_btn.show()

    def set_analysis_idle(self) -> None:
        """Reset analyse button to idle clickable state."""
        self._analyse_btn.setEnabled(True)
        if self._analysis is not None:
            self._analyse_btn.setText("🔍 Re-review Game")
        else:
            self._analyse_btn.setText("🔍 Review Game")

    def set_game_over(self, is_over: bool) -> None:
        """Show or hide the Analyse button based on game state."""
        if is_over:
            self._analyse_btn.show()
            self.set_analysis_idle()
        else:
            self._analyse_btn.hide()
            self._accuracy_bar.hide()
            self._alt_card.hide()
            self._analysis = None

    def _update_alternative_display(self, ply: int | None) -> None:
        """Show engine alternative in alt card for the specified ply."""
        if self._analysis is None or not ply:
            self._alt_card.hide()
            return

        ma = next((m for m in self._analysis.moves if m.ply == ply), None)
        if ma is None:
            self._alt_card.hide()
            return

        moves = self._service.get_state().moves
        played_san = moves[ply - 1].san if 1 <= ply <= len(moves) else ma.played_uci
        badge_str = f" {ma.classification.badge}" if ma.classification.badge else ""
        turn_str = "White" if ply % 2 == 1 else "Black"
        move_num = (ply + 1) // 2

        self._alt_move_lbl.setText(
            f"{move_num}.{'..' if ply % 2 == 0 else ''} {played_san}{badge_str} ({ma.classification.value})"
        )
        self._alt_move_lbl.setStyleSheet(
            f"font-size: 11px; font-weight: bold; color: {ma.classification.color_hex}; border: none; background: transparent;"
        )

        if ma.best_san and ma.best_san != played_san:
            self._alt_best_lbl.setText(f"Engine alternative: {ma.best_san}")
            self._alt_best_lbl.setStyleSheet(
                "font-size: 11px; color: #76c076; border: none; background: transparent;"
            )
            self._alt_best_lbl.show()
        else:
            self._alt_best_lbl.setText("Engine top choice ✓")
            self._alt_best_lbl.setStyleSheet(
                "font-size: 11px; color: #60c0ff; border: none; background: transparent;"
            )
            self._alt_best_lbl.show()

        self._alt_card.show()

    def update_history(self, state: GameState) -> None:
        """Repopulate move history table and match info from GameState."""
        game = self._service.get_game()
        if self._service.is_lan_game:
            self._match_mode_lbl.setText("🌐 LAN Multiplayer")
            self._match_opponent_lbl.setText(
                f"{game.white_player.name} vs {game.black_player.name}"
            )
        elif self._service.is_vs_computer:
            self._match_mode_lbl.setText("🤖 Play vs Computer")
            comp_player = (
                game.black_player
                if game.black_player.player_type == PlayerType.COMPUTER
                else game.white_player
            )
            self._match_opponent_lbl.setText(f"Opponent: {comp_player.name}")
        else:
            self._match_mode_lbl.setText("👥 Pass & Play")
            self._match_opponent_lbl.setText(
                f"{game.white_player.name} vs {game.black_player.name}"
            )

        moves = state.moves
        full_turns = (len(moves) + 1) // 2
        self._table.setRowCount(full_turns)

        active_ply = state.review_ply if state.review_ply is not None else len(moves)

        # Build a ply→MoveAnalysis lookup if analysis is available
        analysis_map: dict[int, object] = {}
        if self._analysis is not None:
            for ma in self._analysis.moves:
                analysis_map[ma.ply] = ma

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
                w_text = moves[white_idx].san
                w_tooltip = ""
                if white_ply in analysis_map:
                    ma = analysis_map[white_ply]  # type: ignore[assignment]
                    badge = ma.classification.badge  # type: ignore[attr-defined]
                    if badge:
                        w_text = f"{moves[white_idx].san} {badge}"
                    if ma.best_san and ma.best_san != moves[white_idx].san:  # type: ignore[attr-defined]
                        w_tooltip = f"Best: {ma.best_san}"  # type: ignore[attr-defined]
                w_item = QTableWidgetItem(w_text)
                w_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if white_ply in analysis_map:
                    ma = analysis_map[white_ply]  # type: ignore[assignment]
                    badge_color = ma.classification.color_hex  # type: ignore[attr-defined]
                    w_item.setForeground(QColor(badge_color))
                if white_ply == active_ply:
                    w_item.setBackground(QColor("#769656"))
                    w_item.setForeground(QColor("#ffffff"))
                if w_tooltip:
                    w_item.setToolTip(w_tooltip)
                self._table.setItem(i, 1, w_item)
            else:
                self._table.setItem(i, 1, QTableWidgetItem(""))

            # Black move
            black_ply = i * 2 + 2
            black_idx = i * 2 + 1
            if black_idx < len(moves):
                b_text = moves[black_idx].san
                b_tooltip = ""
                if black_ply in analysis_map:
                    ma = analysis_map[black_ply]  # type: ignore[assignment]
                    badge = ma.classification.badge  # type: ignore[attr-defined]
                    if badge:
                        b_text = f"{moves[black_idx].san} {badge}"
                    if ma.best_san and ma.best_san != moves[black_idx].san:  # type: ignore[attr-defined]
                        b_tooltip = f"Best: {ma.best_san}"  # type: ignore[attr-defined]
                b_item = QTableWidgetItem(b_text)
                b_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if black_ply in analysis_map:
                    ma = analysis_map[black_ply]  # type: ignore[assignment]
                    badge_color = ma.classification.color_hex  # type: ignore[attr-defined]
                    b_item.setForeground(QColor(badge_color))
                if black_ply == active_ply:
                    b_item.setBackground(QColor("#769656"))
                    b_item.setForeground(QColor("#ffffff"))
                if b_tooltip:
                    b_item.setToolTip(b_tooltip)
                self._table.setItem(i, 2, b_item)
            else:
                self._table.setItem(i, 2, QTableWidgetItem(""))

        # Update alternative display for active ply
        if self._analysis is not None:
            self._update_alternative_display(active_ply)

        # Auto scroll to active ply row
        if active_ply > 0 and full_turns > 0:
            target_row = min((active_ply - 1) // 2, full_turns - 1)
            scroll_item = self._table.item(target_row, 0)
            if scroll_item is not None:
                self._table.scrollToItem(scroll_item)
