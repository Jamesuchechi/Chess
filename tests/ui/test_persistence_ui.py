"""UI tests for SaveAsDialog, OpenGameDialog, and MainWindow File operations."""

from pytestqt.qtbot import QtBot

from chess_desktop.chess.board import ChessBoard
from chess_desktop.chess.move_service import MoveService
from chess_desktop.domain.enums import Color
from chess_desktop.domain.game import Game
from chess_desktop.domain.player import Player
from chess_desktop.persistence.database import DatabaseManager
from chess_desktop.persistence.repositories import GameRepository
from chess_desktop.ui.dialogs.open_game_dialog import OpenGameDialog
from chess_desktop.ui.dialogs.save_as_dialog import SaveAsDialog
from chess_desktop.ui.windows.main_window import MainWindow


def test_save_as_dialog_acceptance(qtbot: QtBot) -> None:
    """Verify SaveAsDialog returns trimmed user title."""
    dlg = SaveAsDialog(default_title="My Match", parent=None)
    qtbot.addWidget(dlg)

    assert dlg.get_title() == "My Match"
    dlg._title_edit.setText("  Championship Final  ")
    assert dlg.get_title() == "Championship Final"

    with qtbot.waitSignal(dlg.accepted, timeout=1000):
        dlg._save_btn.click()


def test_save_as_dialog_rejection(qtbot: QtBot) -> None:
    """Verify SaveAsDialog cancel button rejects dialog."""
    dlg = SaveAsDialog(default_title="My Match", parent=None)
    qtbot.addWidget(dlg)

    with qtbot.waitSignal(dlg.rejected, timeout=1000):
        dlg._cancel_btn.click()


def test_open_game_dialog_flow(qtbot: QtBot) -> None:
    """Verify OpenGameDialog populates table, filters, and allows selection."""
    db = DatabaseManager(":memory:")
    repo = GameRepository(db)

    # Save a game in repo
    board = ChessBoard()
    m1 = MoveService.execute_move(board, "e2", "e4")
    state = MoveService.build_game_state(board, ("e2", "e4"), [m1])
    game = Game(Player("Carlsen", Color.WHITE), Player("Nakamura", Color.BLACK), state)
    saved_id = repo.save(game, title="Blitz Final")

    dlg = OpenGameDialog(repo)
    qtbot.addWidget(dlg)
    dlg.show()

    assert dlg._table.rowCount() == 1
    assert dlg._table.item(0, 0) is not None
    assert dlg._table.item(0, 0).text() == "Blitz Final"
    assert not dlg._open_btn.isEnabled()

    # Select row
    dlg._table.selectRow(0)
    assert dlg._open_btn.isEnabled()
    assert dlg._delete_btn.isEnabled()

    # Test filtering
    dlg._filter_edit.setText("NonExistent")
    assert dlg._table.rowCount() == 0

    dlg._filter_edit.setText("Carlsen")
    assert dlg._table.rowCount() == 1

    dlg._table.selectRow(0)
    with qtbot.waitSignal(dlg.accepted, timeout=1000):
        dlg._open_btn.click()

    assert dlg.selected_game_id == saved_id
    db.close()


def test_main_window_save_and_title_update(qtbot: QtBot) -> None:
    """Verify saving a game updates MainWindow title and marks clean."""
    window = MainWindow()
    window._skip_close_confirm = True
    qtbot.addWidget(window)
    window.show()

    assert "Chess Desktop" in window.windowTitle()
    assert "*" not in window.windowTitle()

    # Play move
    window.game_service.try_move("e2", "e4")
    assert "*" in window.windowTitle()

    # Save directly via SaveService
    window.save_service.save_as("Test Title")
    assert "Test Title" in window.windowTitle()
    assert "*" not in window.windowTitle()
