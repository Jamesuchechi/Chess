"""UI tests for LanGameDialog."""

from pytestqt.qtbot import QtBot

from chess_desktop.ui.dialogs.lan_game_dialog import LanGameDialog


def test_lan_game_dialog_host_tab(qtbot: QtBot) -> None:
    dialog = LanGameDialog()
    qtbot.addWidget(dialog)
    dialog.show()

    # Host tab is active by default
    assert dialog.is_host is True

    dialog._host_name_input.setText("Alice")
    dialog._host_port_spin.setValue(5678)
    dialog._radio_host_black.setChecked(True)

    assert dialog.get_host_name() == "Alice"
    assert dialog.get_host_port() == 5678
    assert dialog.get_host_color() == "black"
    assert dialog.get_host_time_control() is not None


def test_lan_game_dialog_join_tab(qtbot: QtBot) -> None:
    dialog = LanGameDialog()
    qtbot.addWidget(dialog)
    dialog.show()

    dialog._tabs.setCurrentIndex(1)
    assert dialog.is_host is False

    dialog._client_name_input.setText("Bob")
    dialog._join_ip_input.setText("192.168.1.50")
    dialog._join_port_spin.setValue(5678)

    assert dialog.get_join_name() == "Bob"
    assert dialog.get_join_ip() == "192.168.1.50"
    assert dialog.get_join_port() == 5678
