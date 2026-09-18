"""UI tests for PromotionDialog."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton
from pytestqt.qtbot import QtBot

from chess_desktop.domain.enums import Color, PieceType
from chess_desktop.ui.dialogs.promotion_dialog import PromotionDialog


def test_promotion_dialog_selection(qtbot: QtBot) -> None:
    """Verify PromotionDialog piece selection buttons."""
    dialog = PromotionDialog(Color.WHITE)
    qtbot.addWidget(dialog)
    dialog.show()

    assert dialog.selected_piece == PieceType.QUEEN

    # Find buttons
    buttons = dialog.findChildren(QPushButton)
    assert len(buttons) == 4

    # Click the Knight button (last button)
    knight_btn = buttons[3]
    qtbot.mouseClick(knight_btn, Qt.MouseButton.LeftButton)

    assert dialog.selected_piece == PieceType.KNIGHT
    assert dialog.result() == PromotionDialog.DialogCode.Accepted
