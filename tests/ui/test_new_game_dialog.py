"""UI tests for NewGameDialog."""

from pytestqt.qtbot import QtBot

from chess_desktop.domain.enums import PlayerType
from chess_desktop.engine.difficulty import Difficulty
from chess_desktop.ui.dialogs.new_game_dialog import NewGameDialog


def test_new_game_dialog_vs_computer_configuration(qtbot: QtBot) -> None:
    """Verify NewGameDialog returns proper parameters for vs Computer mode."""
    dialog = NewGameDialog()
    qtbot.addWidget(dialog)
    dialog.show()

    # Defaults to vs computer
    assert dialog.is_vs_computer
    assert dialog._comp_group.isVisible()

    # Change difficulty to Advanced
    dialog._diff_combo.setCurrentText(Difficulty.ADVANCED.display_name)
    assert dialog.selected_difficulty == Difficulty.ADVANCED

    # Choose Black for human
    dialog._radio_black.setChecked(True)

    # Select Blitz 3+2
    dialog._tc_combo.setCurrentText("3+2 | Blitz")

    w_name, b_name, w_type, b_type, diff, tc = dialog.get_game_parameters()
    assert w_type == PlayerType.COMPUTER
    assert b_type == PlayerType.HUMAN
    assert diff == Difficulty.ADVANCED
    assert "Stockfish" in w_name
    assert b_name == "Player"
    assert tc.base_seconds == 180
    assert tc.increment_seconds == 2


def test_new_game_dialog_pass_and_play_configuration(qtbot: QtBot) -> None:
    """Verify NewGameDialog toggles to Pass & Play and returns human names."""
    dialog = NewGameDialog()
    qtbot.addWidget(dialog)
    dialog.show()

    dialog._btn_pass_play.setChecked(True)
    assert not dialog.is_vs_computer
    assert not dialog._comp_group.isVisible()
    assert dialog._local_group.isVisible()

    dialog._white_name_edit.setText("Kasparov")
    dialog._black_name_edit.setText("Karpov")

    w_name, b_name, w_type, b_type, _, tc = dialog.get_game_parameters()
    assert w_name == "Kasparov"
    assert b_name == "Karpov"
    assert w_type == PlayerType.HUMAN
    assert b_type == PlayerType.HUMAN
    assert tc.is_unlimited
