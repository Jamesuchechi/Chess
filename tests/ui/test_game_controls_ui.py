"""UI tests for game controls, navigation toolbar, and confirmation dialogs."""

from pytestqt.qtbot import QtBot

from chess_desktop.domain.enums import GameStatus, PlayerType
from chess_desktop.services.game_service import GameService
from chess_desktop.ui.board.navigation_bar import NavigationBar
from chess_desktop.ui.dialogs.confirm_dialog import ConfirmDialog
from chess_desktop.ui.windows.main_window import MainWindow


def test_confirm_dialog_acceptance(qtbot: QtBot) -> None:
    """Verify ConfirmDialog triggers accept on confirm button click."""
    dialog = ConfirmDialog(
        title="Confirm Test",
        message="Are you sure?",
        confirm_text="Yes",
        cancel_text="No",
    )
    qtbot.addWidget(dialog)

    # Click confirm button
    with qtbot.waitSignal(dialog.accepted, timeout=1000):
        dialog._confirm_btn.click()


def test_confirm_dialog_rejection(qtbot: QtBot) -> None:
    """Verify ConfirmDialog triggers reject on cancel button click."""
    dialog = ConfirmDialog(
        title="Confirm Test",
        message="Are you sure?",
        confirm_text="Yes",
        cancel_text="No",
        is_destructive=True,
    )
    qtbot.addWidget(dialog)

    # Click cancel button
    with qtbot.waitSignal(dialog.rejected, timeout=1000):
        dialog._cancel_btn.click()


def test_navigation_bar_state_progression(qtbot: QtBot) -> None:
    """Verify NavigationBar enables/disables buttons as moves are made and reviewed."""
    service = GameService()
    service.new_game("White", "Black", PlayerType.HUMAN, PlayerType.HUMAN)

    nav_bar = NavigationBar(service)
    qtbot.addWidget(nav_bar)
    nav_bar.show()

    # Initially: no moves played, undo and nav backward should be disabled
    assert not nav_bar._undo_btn.isEnabled()
    assert not nav_bar._first_btn.isEnabled()
    assert not nav_bar._prev_btn.isEnabled()
    assert not nav_bar._next_btn.isEnabled()
    assert not nav_bar._last_btn.isEnabled()
    assert not nav_bar._review_container.isVisible()

    # Make moves: e4 (ply 1), e5 (ply 2)
    assert service.try_move("e2", "e4")
    assert service.try_move("e7", "e5")

    # Now at live end: undo enabled, first/prev enabled, next/last disabled
    assert nav_bar._undo_btn.isEnabled()
    assert nav_bar._first_btn.isEnabled()
    assert nav_bar._prev_btn.isEnabled()
    assert not nav_bar._next_btn.isEnabled()
    assert not nav_bar._last_btn.isEnabled()
    assert not nav_bar._review_container.isVisible()

    # Step backward via nav button
    nav_bar._prev_btn.click()
    assert service.get_state().review_ply == 1
    assert nav_bar._review_container.isVisible()
    assert nav_bar._next_btn.isEnabled()
    assert nav_bar._last_btn.isEnabled()

    # Step to start via first button
    nav_bar._first_btn.click()
    assert service.get_state().review_ply == 0
    assert not nav_bar._prev_btn.isEnabled()
    assert nav_bar._next_btn.isEnabled()

    # Resume live position via review resume button
    nav_bar._resume_btn.click()
    assert service.get_state().review_ply is None
    assert not nav_bar._review_container.isVisible()
    assert not nav_bar._next_btn.isEnabled()
    service.cleanup()


def test_main_window_game_controls_integration(qtbot: QtBot) -> None:
    """Verify MainWindow integrates NavigationBar and handles basic game control actions."""
    window = MainWindow()
    window._skip_close_confirm = True
    qtbot.addWidget(window)
    window.show()

    service = window.game_service
    service.new_game("White", "Black", PlayerType.HUMAN, PlayerType.HUMAN)
    assert service.get_state().status == GameStatus.IN_PROGRESS

    # Make moves
    assert service.try_move("e2", "e4")
    assert len(service.get_state().moves) == 1

    # Test undo via action
    window._undo_action.trigger()
    assert len(service.get_state().moves) == 0
