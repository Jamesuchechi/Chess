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


def test_new_game_dialog_remembers_pass_and_play_on_reopen(qtbot: QtBot) -> None:
    """Done condition: Closing and reopening NewGameDialog after selecting 'Pass & Play'

    shows 'Pass & Play' pre-selected on the next open, in the same session and after app restart.
    """
    from PySide6.QtCore import QSettings
    from chess_desktop.services.settings_service import SettingsService

    settings = QSettings("ChessTestCorp", "TestPassAndPlayReopen")
    settings.clear()

    service = SettingsService(settings=settings)

    # 1. First open: initial default is vs Computer
    dialog1 = NewGameDialog(settings_service=service)
    qtbot.addWidget(dialog1)
    assert dialog1.is_vs_computer
    assert dialog1._btn_vs_computer.isChecked()

    # User selects Pass & Play and accepts/starts game
    dialog1._btn_pass_play.setChecked(True)
    dialog1.accept()

    # Verify service received the updated mode
    assert service.last_game_mode == "Pass & Play"

    # 2. Reopen in same session
    dialog2 = NewGameDialog(settings_service=service)
    qtbot.addWidget(dialog2)
    dialog2.show()
    assert not dialog2.is_vs_computer
    assert dialog2._btn_pass_play.isChecked()
    assert dialog2._local_group.isVisible()
    assert not dialog2._comp_group.isVisible()

    # 3. Simulate app restart: instantiate brand new SettingsService on the same store
    restart_service = SettingsService(settings=settings)
    dialog3 = NewGameDialog(settings_service=restart_service)
    qtbot.addWidget(dialog3)
    dialog3.show()
    assert not dialog3.is_vs_computer
    assert dialog3._btn_pass_play.isChecked()
    assert dialog3._local_group.isVisible()
    assert not dialog3._comp_group.isVisible()

    settings.clear()


def test_new_game_dialog_remembers_color_and_difficulty_on_reopen(qtbot: QtBot) -> None:
    """Verify player color and difficulty selections are remembered across dialog openings."""
    from PySide6.QtCore import QSettings
    from chess_desktop.services.settings_service import SettingsService

    settings = QSettings("ChessTestCorp", "TestColorDiffReopen")
    settings.clear()

    service = SettingsService(settings=settings)

    dialog1 = NewGameDialog(settings_service=service)
    qtbot.addWidget(dialog1)

    dialog1._radio_black.setChecked(True)
    dialog1._diff_combo.setCurrentText(Difficulty.MASTER.display_name)
    dialog1.accept()

    assert service.last_player_color == "black"
    assert service.last_difficulty == Difficulty.MASTER.display_name

    # Reopen dialog
    dialog2 = NewGameDialog(settings_service=service)
    qtbot.addWidget(dialog2)

    assert dialog2.is_vs_computer
    assert dialog2._radio_black.isChecked()
    assert dialog2.selected_difficulty == Difficulty.MASTER

    settings.clear()

