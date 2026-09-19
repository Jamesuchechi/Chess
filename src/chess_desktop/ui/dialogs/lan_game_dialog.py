"""Modal dialog for setting up Host and Client LAN multiplayer connections."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from chess_desktop.domain.enums import Color
from chess_desktop.domain.time_control import TimeControl
from chess_desktop.network.discovery import get_hotspot_instructions, get_primary_lan_ip
from chess_desktop.services.game_service import GameService


class LanGameDialog(QDialog):
    """LAN Multiplayer connection setup dialog supporting Host and Join flows."""

    def __init__(self, game_service: GameService | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("LAN / Hotspot Multiplayer")
        self.setFixedWidth(500)
        self.setModal(True)

        self._service = game_service or GameService(self)
        self._is_hosting = False

        self._init_ui()
        self._connect_signals()

    @property
    def is_host(self) -> bool:
        """True if Host tab is selected."""
        return self._tabs.currentIndex() == 0

    def get_host_name(self) -> str:
        return self._host_name_input.text().strip() or "Host"

    def get_host_port(self) -> int:
        return self._host_port_spin.value()

    def get_host_color(self) -> str:
        return "white" if self._radio_host_white.isChecked() else "black"

    def get_host_time_control(self) -> TimeControl:
        return self._tc_combo.currentData() or TimeControl.unlimited()

    def get_join_name(self) -> str:
        return self._client_name_input.text().strip() or "Guest"

    def get_join_ip(self) -> str:
        return self._join_ip_input.text().strip()

    def get_join_port(self) -> int:
        return self._join_port_spin.value()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # Tab Widget for Host vs Join
        self._tabs = QTabWidget(self)
        self._tabs.setStyleSheet(
            """
            QTabWidget::pane {
                border: 1px solid #3d3d3d;
                background-color: #242424;
                border-radius: 6px;
            }
            QTabBar::tab {
                background-color: #1e1e1e;
                color: #a0a0a0;
                padding: 8px 24px;
                font-size: 13px;
                font-weight: bold;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #242424;
                color: #ffffff;
                border-bottom: 2px solid #769656;
            }
            """
        )

        # 1. Host Tab
        host_tab = QWidget(self._tabs)
        host_layout = QVBoxLayout(host_tab)
        host_layout.setSpacing(12)
        host_layout.setContentsMargins(16, 16, 16, 16)

        # Detected IP info banner
        ip_box = QGroupBox("Your LAN IP Address", host_tab)
        ip_layout = QVBoxLayout(ip_box)
        self._ip_label = QLabel(f"🌐 {get_primary_lan_ip()}", ip_box)
        self._ip_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #769656;")
        ip_layout.addWidget(self._ip_label)

        hint = QLabel("Give this IP address to the other player on your Wi-Fi/Hotspot.", ip_box)
        hint.setStyleSheet("font-size: 11px; color: #888888;")
        hint.setWordWrap(True)
        ip_layout.addWidget(hint)
        host_layout.addWidget(ip_box)

        # Host Player Name & Port
        host_fields = QHBoxLayout()
        host_name_lbl = QLabel("Your Name:", host_tab)
        host_name_lbl.setStyleSheet("color: #e0e0e0; font-weight: bold;")
        self._host_name_input = QLineEdit("Host Player", host_tab)
        self._host_name_input.setStyleSheet("background-color: #1e1e1e; color: #ffffff; padding: 5px;")
        host_fields.addWidget(host_name_lbl)
        host_fields.addWidget(self._host_name_input, stretch=1)

        port_lbl = QLabel("Port:", host_tab)
        port_lbl.setStyleSheet("color: #e0e0e0; font-weight: bold;")
        self._host_port_spin = QSpinBox(host_tab)
        self._host_port_spin.setRange(1024, 65535)
        self._host_port_spin.setValue(5000)
        self._host_port_spin.setStyleSheet("background-color: #1e1e1e; color: #ffffff; padding: 5px;")
        host_fields.addWidget(port_lbl)
        host_fields.addWidget(self._host_port_spin)
        host_layout.addLayout(host_fields)

        # Host Color Choice
        color_layout = QHBoxLayout()
        color_lbl = QLabel("Your Color:", host_tab)
        color_lbl.setStyleSheet("color: #e0e0e0; font-weight: bold;")
        color_layout.addWidget(color_lbl)

        self._radio_host_white = QRadioButton("White (Move 1st)", host_tab)
        self._radio_host_black = QRadioButton("Black (Move 2nd)", host_tab)
        self._radio_host_white.setChecked(True)
        self._host_color_group = QButtonGroup(host_tab)
        self._host_color_group.addButton(self._radio_host_white)
        self._host_color_group.addButton(self._radio_host_black)
        color_layout.addWidget(self._radio_host_white)
        color_layout.addWidget(self._radio_host_black)
        color_layout.addStretch()
        host_layout.addLayout(color_layout)

        # Time Control
        tc_layout = QHBoxLayout()
        tc_lbl = QLabel("Time Control:", host_tab)
        tc_lbl.setStyleSheet("color: #e0e0e0; font-weight: bold;")
        tc_layout.addWidget(tc_lbl)

        self._tc_combo = QComboBox(host_tab)
        for preset in TimeControl.all_presets():
            self._tc_combo.addItem(preset.name, preset)
        tc_layout.addWidget(self._tc_combo, stretch=1)
        host_layout.addLayout(tc_layout)

        # Host Status & Action Button
        self._host_status_lbl = QLabel("", host_tab)
        self._host_status_lbl.setStyleSheet("color: #facc15; font-weight: bold; font-size: 12px;")
        host_layout.addWidget(self._host_status_lbl)

        self._btn_start_host = QPushButton("Start Hosting Match", host_tab)
        self._btn_start_host.setStyleSheet(
            """
            QPushButton {
                background-color: #769656;
                color: #ffffff;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #87ab62;
            }
            """
        )
        self._btn_start_host.clicked.connect(self._on_start_hosting)
        host_layout.addWidget(self._btn_start_host)

        self._tabs.addTab(host_tab, "Host LAN Game")

        # 2. Join Tab
        join_tab = QWidget(self._tabs)
        join_layout = QVBoxLayout(join_tab)
        join_layout.setSpacing(12)
        join_layout.setContentsMargins(16, 16, 16, 16)

        # Host IP & Port inputs
        join_ip_box = QGroupBox("Host Connection Details", join_tab)
        join_ip_layout = QVBoxLayout(join_ip_box)
        join_ip_layout.setSpacing(8)

        ip_input_layout = QHBoxLayout()
        join_ip_lbl = QLabel("Host IP Address:", join_ip_box)
        join_ip_lbl.setStyleSheet("color: #e0e0e0; font-weight: bold;")
        self._join_ip_input = QLineEdit("127.0.0.1", join_ip_box)
        self._join_ip_input.setPlaceholderText("e.g. 192.168.1.50")
        self._join_ip_input.setStyleSheet("background-color: #1e1e1e; color: #ffffff; padding: 5px;")
        ip_input_layout.addWidget(join_ip_lbl)
        ip_input_layout.addWidget(self._join_ip_input, stretch=1)
        join_ip_layout.addLayout(ip_input_layout)

        join_port_layout = QHBoxLayout()
        join_port_lbl = QLabel("Host Port:", join_ip_box)
        join_port_lbl.setStyleSheet("color: #e0e0e0; font-weight: bold;")
        self._join_port_spin = QSpinBox(join_ip_box)
        self._join_port_spin.setRange(1024, 65535)
        self._join_port_spin.setValue(5000)
        self._join_port_spin.setStyleSheet("background-color: #1e1e1e; color: #ffffff; padding: 5px;")
        join_port_layout.addWidget(join_port_lbl)
        join_port_layout.addWidget(self._join_port_spin)
        join_port_layout.addStretch()
        join_ip_layout.addLayout(join_port_layout)
        join_layout.addWidget(join_ip_box)

        # Client Player Name
        client_name_layout = QHBoxLayout()
        client_name_lbl = QLabel("Your Name:", join_tab)
        client_name_lbl.setStyleSheet("color: #e0e0e0; font-weight: bold;")
        self._client_name_input = QLineEdit("Guest Player", join_tab)
        self._client_name_input.setStyleSheet("background-color: #1e1e1e; color: #ffffff; padding: 5px;")
        client_name_layout.addWidget(client_name_lbl)
        client_name_layout.addWidget(self._client_name_input, stretch=1)
        join_layout.addLayout(client_name_layout)

        # Join Status & Button
        self._join_status_lbl = QLabel("", join_tab)
        self._join_status_lbl.setStyleSheet("color: #facc15; font-weight: bold; font-size: 12px;")
        join_layout.addWidget(self._join_status_lbl)

        self._btn_connect_join = QPushButton("Connect to Host", join_tab)
        self._btn_connect_join.setStyleSheet(
            """
            QPushButton {
                background-color: #769656;
                color: #ffffff;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #87ab62;
            }
            """
        )
        self._btn_connect_join.clicked.connect(self._on_connect_to_host)
        join_layout.addWidget(self._btn_connect_join)

        # Hotspot help banner
        help_box = QLabel(get_hotspot_instructions(), join_tab)
        help_box.setStyleSheet(
            "font-size: 10px; color: #888888; background-color: #1c1c1c; padding: 6px; border-radius: 4px;"
        )
        help_box.setWordWrap(True)
        join_layout.addWidget(help_box)

        self._tabs.addTab(join_tab, "Join LAN Game")
        layout.addWidget(self._tabs)

        # Close / Cancel button
        btn_close = QPushButton("Cancel", self)
        btn_close.setStyleSheet(
            """
            QPushButton {
                background-color: #383838;
                color: #ffffff;
                padding: 6px 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #484848;
            }
            """
        )
        btn_close.clicked.connect(self.reject)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

    def _connect_signals(self) -> None:
        self._service.lan_connected.connect(self._on_lan_connected)
        self._service.lan_peer_joined.connect(self._on_lan_peer_joined)
        self._service.lan_error.connect(self._on_lan_error)

    def _on_start_hosting(self) -> None:
        """Launch LAN server and await peer."""
        port = self._host_port_spin.value()
        name = self._host_name_input.text().strip() or "Host"
        color = Color.WHITE if self._radio_host_white.isChecked() else Color.BLACK
        tc = self._tc_combo.currentData()

        self._is_hosting = True
        self._btn_start_host.setEnabled(False)
        self._host_status_lbl.setText("⏳ Listening for opponent... Keep this window open.")

        success = self._service.host_lan_game(
            port=port,
            player_name=name,
            host_color=color,
            time_control=tc,
        )
        if not success:
            self._btn_start_host.setEnabled(True)
            self._host_status_lbl.setText("❌ Failed to start host on chosen port.")

    def _on_connect_to_host(self) -> None:
        """Connect to LAN host."""
        ip = self._join_ip_input.text().strip()
        port = self._join_port_spin.value()
        name = self._client_name_input.text().strip() or "Guest"

        if not ip:
            self._join_status_lbl.setText("❌ Please enter a host IP address.")
            return

        self._is_hosting = False
        self._btn_connect_join.setEnabled(False)
        self._join_status_lbl.setText(f"⏳ Connecting to {ip}:{port}...")

        self._service.join_lan_game(
            host_ip=ip,
            port=port,
            player_name=name,
        )

    def _on_lan_connected(self, peer_address: str) -> None:
        if self._is_hosting:
            self._host_status_lbl.setText(f"✅ Opponent connected from {peer_address}!")
        else:
            self._join_status_lbl.setText(f"✅ Connected to host at {peer_address}!")

    def _on_lan_peer_joined(self, peer_name: str) -> None:
        # Match negotiation complete -> dismiss dialog and start playing!
        self.accept()

    def _on_lan_error(self, error_msg: str) -> None:
        if self._is_hosting:
            self._btn_start_host.setEnabled(True)
            self._host_status_lbl.setText(f"❌ Error: {error_msg}")
        else:
            self._btn_connect_join.setEnabled(True)
            self._join_status_lbl.setText(f"❌ Connection failed: {error_msg}")
