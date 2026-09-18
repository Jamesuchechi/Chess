"""Main application window for Chess Desktop."""

from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from chess_desktop.domain.enums import Color, GameStatus, PieceType
from chess_desktop.domain.game_state import GameState
from chess_desktop.services.game_service import GameService
from chess_desktop.services.save_service import SaveService
from chess_desktop.ui.board.board_widget import BoardWidget
from chess_desktop.ui.board.captured_panel import CapturedPanel
from chess_desktop.ui.board.history_panel import HistoryPanel
from chess_desktop.ui.board.navigation_bar import NavigationBar
from chess_desktop.ui.dialogs.confirm_dialog import ConfirmDialog
from chess_desktop.ui.dialogs.game_over_dialog import GameOverDialog
from chess_desktop.ui.dialogs.open_game_dialog import OpenGameDialog
from chess_desktop.ui.dialogs.promotion_dialog import PromotionDialog
from chess_desktop.ui.dialogs.save_as_dialog import SaveAsDialog


class MainWindow(QMainWindow):
    """Main application window containing board, controls, and status."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Chess Desktop")
        self.setMinimumSize(960, 720)
        self.resize(1024, 768)

        # Apply dark mode stylesheet to window
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #1e1e1e;
            }
            QStatusBar {
                background-color: #181818;
                color: #888888;
                border-top: 1px solid #2b2b2b;
            }
            """
        )

        self._service = GameService(self)
        self._save_service = SaveService(self._service, parent=self)
        self._init_menu_bar()
        self._init_ui()
        self._init_shortcuts()
        self._connect_signals()
        self._update_window_title()

    @property
    def game_service(self) -> GameService:
        """Access underlying GameService."""
        return self._service

    @property
    def save_service(self) -> SaveService:
        """Access underlying SaveService."""
        return self._save_service

    def _init_menu_bar(self) -> None:
        """Create application menu bar and File menu."""
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")

        action_new = QAction("&New Game", self)
        action_new.setShortcut(QKeySequence.StandardKey.New)
        action_new.triggered.connect(self._handle_new_game)
        file_menu.addAction(action_new)

        self._action_open = QAction("&Open Game...", self)
        self._action_open.setShortcut(QKeySequence.StandardKey.Open)
        self._action_open.triggered.connect(self._handle_open_game)
        file_menu.addAction(self._action_open)

        self._action_save = QAction("&Save Game", self)
        self._action_save.setShortcut(QKeySequence.StandardKey.Save)
        self._action_save.triggered.connect(self._handle_save_game)
        file_menu.addAction(self._action_save)

        self._action_save_as = QAction("Save Game &As...", self)
        self._action_save_as.setShortcut(QKeySequence.StandardKey.SaveAs)
        self._action_save_as.triggered.connect(self._handle_save_game_as)
        file_menu.addAction(self._action_save_as)

        file_menu.addSeparator()

        self._action_import = QAction("&Import PGN...", self)
        self._action_import.triggered.connect(self._handle_import_pgn)
        file_menu.addAction(self._action_import)

        self._action_export = QAction("&Export PGN...", self)
        self._action_export.triggered.connect(self._handle_export_pgn)
        file_menu.addAction(self._action_export)

        file_menu.addSeparator()

        action_exit = QAction("E&xit", self)
        action_exit.setShortcut(QKeySequence.StandardKey.Quit)
        action_exit.triggered.connect(self.close)
        file_menu.addAction(action_exit)

    def _init_ui(self) -> None:
        """Initialize the main window layout and components."""
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(16)

        # Left area: Board column with top & bottom captured panels and navigation bar
        board_column = QWidget(central_widget)
        board_layout = QVBoxLayout(board_column)
        board_layout.setContentsMargins(0, 0, 0, 0)
        board_layout.setSpacing(8)

        # Black status/captured panel (top)
        self._black_panel = CapturedPanel(Color.BLACK, self._service, board_column)
        board_layout.addWidget(self._black_panel)

        # Chessboard widget
        self._board_widget = BoardWidget(self._service, board_column)
        board_layout.addWidget(self._board_widget, stretch=1)

        # White status/captured panel (bottom)
        self._white_panel = CapturedPanel(Color.WHITE, self._service, board_column)
        board_layout.addWidget(self._white_panel)

        # Navigation and controls bar
        self._nav_bar = NavigationBar(self._service, board_column)
        board_layout.addWidget(self._nav_bar)

        root_layout.addWidget(board_column, stretch=1)

        # Right area: Move history & quick actions
        self._history_panel = HistoryPanel(self._service, central_widget)
        root_layout.addWidget(self._history_panel)

        # Status bar
        self._status_bar = QStatusBar(self)
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Ready. White to move.")

    def _init_shortcuts(self) -> None:
        """Set up application keyboard shortcuts."""
        # 'F' to flip board
        flip_action = QAction("Flip Board", self)
        flip_action.setShortcut(QKeySequence("F"))
        flip_action.triggered.connect(self._service.flip_board)
        self.addAction(flip_action)

        # 'Ctrl+N' for new game
        new_game_action = QAction("New Game", self)
        new_game_action.setShortcut(QKeySequence("Ctrl+N"))
        new_game_action.triggered.connect(self._handle_new_game)
        self.addAction(new_game_action)

        # 'Ctrl+Z' for undo
        self._undo_action = QAction("Undo", self)
        self._undo_action.setShortcut(QKeySequence("Ctrl+Z"))
        self._undo_action.triggered.connect(self._service.undo_move)
        self.addAction(self._undo_action)

        # Left arrow: previous move
        prev_action = QAction("Previous Move", self)
        prev_action.setShortcut(QKeySequence("Left"))
        prev_action.triggered.connect(self._service.step_backward)
        self.addAction(prev_action)

        # Right arrow: next move
        next_action = QAction("Next Move", self)
        next_action.setShortcut(QKeySequence("Right"))
        next_action.triggered.connect(self._service.step_forward)
        self.addAction(next_action)

        # Home: first move
        home_action = QAction("First Move", self)
        home_action.setShortcut(QKeySequence("Home"))
        home_action.triggered.connect(self._service.go_to_start)
        self.addAction(home_action)

        # End: live move
        end_action = QAction("Live Position", self)
        end_action.setShortcut(QKeySequence("End"))
        end_action.triggered.connect(self._service.go_to_live)
        self.addAction(end_action)

    def _connect_signals(self) -> None:
        """Connect service signals to window dialogs and status bar."""
        self._service.promotion_requested.connect(self._handle_promotion)
        self._service.game_over.connect(self._handle_game_over)
        self._service.state_changed.connect(self._handle_state_changed)
        self._save_service.dirty_changed.connect(lambda _: self._update_window_title())
        self._save_service.game_saved.connect(lambda _: self._update_window_title())
        self._save_service.game_loaded.connect(lambda _: self._update_window_title())

    def _update_window_title(self, *args: object) -> None:
        """Update window title with current game title and unsaved changes asterisk."""
        title = "Chess Desktop"
        current_title = self._save_service.current_game_title
        if current_title:
            title += f" — {current_title}"
        if self._save_service.has_unsaved_changes:
            title += " *"
        self.setWindowTitle(title)

    def _handle_new_game(self) -> None:
        """Start new game with confirmation if unsaved changes or moves in progress."""
        if self._save_service.has_unsaved_changes:
            dlg = ConfirmDialog(
                title="Start New Game?",
                message="You have unsaved changes in this game.\n\nDiscard changes and start new game?",
                confirm_text="Discard & Start",
                cancel_text="Cancel",
                is_destructive=True,
                parent=self,
            )
            if not dlg.exec():
                return
        self._service.new_game()
        self._save_service.reset_tracking()
        self._update_window_title()

    def _handle_save_game(self) -> None:
        """Save game to SQLite; prompt for title if never saved before."""
        if self._save_service.current_game_title:
            self._save_service.save()
            self._status_bar.showMessage(f"Game saved: {self._save_service.current_game_title}")
        else:
            self._handle_save_game_as()

    def _handle_save_game_as(self) -> None:
        """Prompt user for title and save game to SQLite."""
        default_title = self._save_service.current_game_title
        if not default_title:
            game = self._service.get_game()
            default_title = f"{game.white_player.name} vs. {game.black_player.name}"

        dlg = SaveAsDialog(default_title=default_title, parent=self)
        if dlg.exec():
            title = dlg.get_title()
            if title:
                self._save_service.save_as(title)
                self._status_bar.showMessage(f"Game saved as: {title}")

    def _handle_open_game(self) -> None:
        """Show open dialog and load chosen game from SQLite."""
        if self._save_service.has_unsaved_changes:
            dlg = ConfirmDialog(
                title="Unsaved Changes",
                message="Opening another game will discard current unsaved changes.\n\nContinue?",
                confirm_text="Continue",
                cancel_text="Cancel",
                is_destructive=True,
                parent=self,
            )
            if not dlg.exec():
                return

        open_dlg = OpenGameDialog(self._save_service.repository, self)
        if open_dlg.exec():
            game_id = open_dlg.selected_game_id
            if game_id:
                if self._save_service.load_game(game_id):
                    self._status_bar.showMessage(
                        f"Loaded game: {self._save_service.current_game_title}"
                    )

    def _handle_export_pgn(self) -> None:
        """Export active game to standard PGN file."""
        default_name = f"{self._save_service.current_game_title or 'game'}.pgn"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export PGN",
            default_name,
            "PGN Files (*.pgn);;All Files (*)",
        )
        if path:
            try:
                self._save_service.export_pgn_file(path)
                self._status_bar.showMessage(f"Exported PGN: {path}")
            except Exception as e:
                self._status_bar.showMessage(f"Export failed: {e}")

    def _handle_import_pgn(self) -> None:
        """Import standard PGN file into active game view."""
        if self._save_service.has_unsaved_changes:
            dlg = ConfirmDialog(
                title="Unsaved Changes",
                message="Importing a PGN will discard current unsaved changes.\n\nContinue?",
                confirm_text="Continue",
                cancel_text="Cancel",
                is_destructive=True,
                parent=self,
            )
            if not dlg.exec():
                return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import PGN",
            "",
            "PGN Files (*.pgn);;All Files (*)",
        )
        if path:
            try:
                if self._save_service.import_pgn_file(path):
                    self._status_bar.showMessage(
                        f"Imported PGN: {self._save_service.current_game_title}"
                    )
            except Exception as e:
                self._status_bar.showMessage(f"Import failed: {e}")

    def closeEvent(self, event: QCloseEvent) -> None:
        """Confirm exit if unsaved changes exist."""
        if self._save_service.has_unsaved_changes:
            dlg = ConfirmDialog(
                title="Unsaved Changes",
                message="You have unsaved changes in this game.\n\nDiscard changes and exit?",
                confirm_text="Discard & Exit",
                cancel_text="Keep Playing",
                is_destructive=True,
                parent=self,
            )
            if not dlg.exec():
                event.ignore()
                return
        event.accept()

    def _handle_promotion(self, from_sq: str, to_sq: str) -> None:
        """Prompt user for promotion piece choice and complete move."""
        current_color = self._service.get_state().turn
        dialog = PromotionDialog(current_color, self)
        if dialog.exec():
            chosen_piece: PieceType = dialog.selected_piece
            self._service.try_move(from_sq, to_sq, promotion=chosen_piece)

    def _handle_game_over(self, status: GameStatus, message: str) -> None:
        """Show Game Over dialog and offer new game."""
        dialog = GameOverDialog(status, message, self)
        if dialog.exec() and dialog.start_new_game_requested:
            self._service.new_game()

    def _handle_state_changed(self, state: GameState) -> None:
        """Update status bar on state change."""
        turn_str = "White" if state.turn == state.turn.WHITE else "Black"
        if state.is_reviewing:
            ply = state.review_ply or 0
            self._status_bar.showMessage(f"Reviewing move {ply} (Read-only). Press End to resume.")
        elif state.status.is_game_over:
            self._status_bar.showMessage(state.status_message or "Game over")
        elif state.in_check:
            self._status_bar.showMessage(f"Check! {turn_str} to move.")
        else:
            self._status_bar.showMessage(f"{turn_str} to move. Move {state.move_number}")
