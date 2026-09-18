"""New Game configuration dialog supporting Local Multiplayer and Play vs Computer."""

import random

from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from chess_desktop.domain.enums import Color, PlayerType
from chess_desktop.domain.time_control import TimeControl
from chess_desktop.engine.difficulty import Difficulty
from chess_desktop.engine.discovery import find_stockfish_binary


class NewGameDialog(QDialog):
    """Modal dialog allowing the player to configure a new chess match."""

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Start New Game")
        self.setFixedWidth(460)
        self.setModal(True)

        self._stockfish_path = find_stockfish_binary()
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # 1. Game Mode Selection
        mode_group = QGroupBox("Game Mode", self)
        mode_layout = QVBoxLayout(mode_group)
        mode_layout.setSpacing(8)

        self._btn_pass_play = QRadioButton("Pass & Play (Local 2-Player)", mode_group)
        self._btn_vs_computer = QRadioButton("Play vs Computer (Stockfish)", mode_group)
        self._btn_vs_computer.setChecked(True)

        self._mode_btn_group = QButtonGroup(self)
        self._mode_btn_group.addButton(self._btn_pass_play)
        self._mode_btn_group.addButton(self._btn_vs_computer)
        self._mode_btn_group.buttonToggled.connect(self._on_mode_toggled)

        mode_layout.addWidget(self._btn_vs_computer)
        mode_layout.addWidget(self._btn_pass_play)
        layout.addWidget(mode_group)

        # 2. Computer Options Group
        self._comp_group = QGroupBox("Computer Settings", self)
        comp_layout = QVBoxLayout(self._comp_group)
        comp_layout.setSpacing(12)

        # Color Choice
        color_lbl = QLabel("Choose Your Color:", self._comp_group)
        color_lbl.setStyleSheet("color: #e0e0e0; font-weight: bold; font-size: 12px;")
        comp_layout.addWidget(color_lbl)

        color_h_layout = QHBoxLayout()
        self._radio_white = QRadioButton("White", self._comp_group)
        self._radio_black = QRadioButton("Black", self._comp_group)
        self._radio_random = QRadioButton("Random", self._comp_group)
        self._radio_white.setChecked(True)

        self._color_group = QButtonGroup(self)
        self._color_group.addButton(self._radio_white)
        self._color_group.addButton(self._radio_black)
        self._color_group.addButton(self._radio_random)

        color_h_layout.addWidget(self._radio_white)
        color_h_layout.addWidget(self._radio_black)
        color_h_layout.addWidget(self._radio_random)
        comp_layout.addLayout(color_h_layout)

        # Difficulty Selection
        diff_lbl = QLabel("Difficulty:", self._comp_group)
        diff_lbl.setStyleSheet("color: #e0e0e0; font-weight: bold; font-size: 12px;")
        comp_layout.addWidget(diff_lbl)

        self._diff_combo = QComboBox(self._comp_group)
        for diff in Difficulty:
            self._diff_combo.addItem(diff.display_name, diff)
        self._diff_combo.setCurrentIndex(2)  # Intermediate by default
        self._diff_combo.currentIndexChanged.connect(self._on_difficulty_changed)
        comp_layout.addWidget(self._diff_combo)

        self._diff_desc = QLabel(self._comp_group)
        self._diff_desc.setStyleSheet("color: #aaaaaa; font-size: 11px; font-style: italic;")
        self._on_difficulty_changed(self._diff_combo.currentIndex())
        comp_layout.addWidget(self._diff_desc)

        # Engine Detection Status Banner
        engine_box = QHBoxLayout()
        self._engine_status_lbl = QLabel(self._comp_group)
        self._update_engine_status_ui()
        engine_box.addWidget(self._engine_status_lbl, stretch=1)

        browse_btn = QPushButton("Browse...", self._comp_group)
        browse_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #333333;
                color: #e0e0e0;
                padding: 4px 10px;
                border: 1px solid #444444;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #444444;
            }
            """
        )
        browse_btn.clicked.connect(self._on_browse_engine)
        engine_box.addWidget(browse_btn)

        comp_layout.addLayout(engine_box)
        layout.addWidget(self._comp_group)

        # 3. Local Players Group
        self._local_group = QGroupBox("Player Names", self)
        local_layout = QVBoxLayout(self._local_group)
        local_layout.setSpacing(8)

        self._white_name_edit = QLineEdit("White", self._local_group)
        self._black_name_edit = QLineEdit("Black", self._local_group)

        local_layout.addWidget(QLabel("White Player:", self._local_group))
        local_layout.addWidget(self._white_name_edit)
        local_layout.addWidget(QLabel("Black Player:", self._local_group))
        local_layout.addWidget(self._black_name_edit)

        layout.addWidget(self._local_group)
        self._local_group.hide()

        # 4. Time Control Group
        self._tc_group = QGroupBox("Time Control", self)
        tc_layout = QVBoxLayout(self._tc_group)
        tc_layout.setSpacing(8)

        self._tc_combo = QComboBox(self._tc_group)
        for preset in TimeControl.all_presets():
            self._tc_combo.addItem(preset.name, preset)
        self._tc_combo.addItem("Custom...", None)
        self._tc_combo.currentIndexChanged.connect(self._on_time_control_changed)
        tc_layout.addWidget(self._tc_combo)

        # Custom controls
        self._custom_widget = QWidget(self._tc_group)
        custom_layout = QHBoxLayout(self._custom_widget)
        custom_layout.setContentsMargins(0, 0, 0, 0)
        custom_layout.setSpacing(8)

        custom_layout.addWidget(QLabel("Minutes:", self._custom_widget))
        self._custom_minutes = QSpinBox(self._custom_widget)
        self._custom_minutes.setRange(1, 180)
        self._custom_minutes.setValue(5)
        custom_layout.addWidget(self._custom_minutes)

        custom_layout.addWidget(QLabel("Increment (s):", self._custom_widget))
        self._custom_increment = QSpinBox(self._custom_widget)
        self._custom_increment.setRange(0, 60)
        self._custom_increment.setValue(3)
        custom_layout.addWidget(self._custom_increment)

        tc_layout.addWidget(self._custom_widget)
        self._custom_widget.hide()
        layout.addWidget(self._tc_group)

        # 5. Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self._cancel_btn = QPushButton("Cancel", self)
        self._cancel_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #383838;
                color: #e0e0e0;
                padding: 6px 14px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #484848;
            }
            """
        )
        self._cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._cancel_btn)

        self._start_btn = QPushButton("Start Game", self)
        self._start_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #769656;
                color: #ffffff;
                padding: 6px 18px;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #87ab62;
            }
            """
        )
        self._start_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self._start_btn)

        layout.addLayout(btn_layout)

        # Apply dark theme styling to dialog
        self.setStyleSheet(
            """
            QDialog {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QGroupBox {
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #333333;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QRadioButton {
                color: #e0e0e0;
                font-size: 12px;
            }
            QRadioButton::indicator {
                width: 14px;
                height: 14px;
            }
            QComboBox, QLineEdit {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #ffffff;
                selection-background-color: #769656;
            }
            """
        )

    def _update_engine_status_ui(self) -> None:
        """Update detection indicator text and style."""
        if self._stockfish_path:
            self._engine_status_lbl.setText(f"✓ Stockfish Engine: {self._stockfish_path}")
            self._engine_status_lbl.setStyleSheet(
                "color: #769656; font-size: 11px; font-weight: bold;"
            )
        else:
            self._engine_status_lbl.setText(
                "⚠ Stockfish not found. Using built-in fallback engine."
            )
            self._engine_status_lbl.setStyleSheet("color: #f59e0b; font-size: 11px;")

    def _on_browse_engine(self) -> None:
        """Let user browse for custom engine binary."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Locate Stockfish Binary",
            "",
            "Executable Files (*);;All Files (*)",
        )
        if path:
            found = find_stockfish_binary(path)
            if found:
                self._stockfish_path = found
                self._update_engine_status_ui()
            else:
                self._engine_status_lbl.setText(
                    "Selected file is not an executable Stockfish binary."
                )
                self._engine_status_lbl.setStyleSheet("color: #ef4444; font-size: 11px;")

    def _on_mode_toggled(self) -> None:
        is_vs_comp = self._btn_vs_computer.isChecked()
        self._comp_group.setVisible(is_vs_comp)
        self._local_group.setVisible(not is_vs_comp)

    def _on_difficulty_changed(self, index: int) -> None:
        diff = self._diff_combo.itemData(index)
        if isinstance(diff, Difficulty):
            self._diff_desc.setText(diff.description)

    def _on_time_control_changed(self, index: int) -> None:
        is_custom = self._tc_combo.itemData(index) is None
        self._custom_widget.setVisible(is_custom)

    # Output configuration getters
    @property
    def is_vs_computer(self) -> bool:
        """True if player vs computer was selected."""
        return self._btn_vs_computer.isChecked()

    @property
    def selected_difficulty(self) -> Difficulty:
        """Selected engine difficulty."""
        data = self._diff_combo.currentData()
        return data if isinstance(data, Difficulty) else Difficulty.INTERMEDIATE

    @property
    def selected_time_control(self) -> TimeControl:
        """Selected TimeControl preset or custom configuration."""
        data = self._tc_combo.currentData()
        if isinstance(data, TimeControl):
            return data
        return TimeControl.custom(
            base_minutes=self._custom_minutes.value(),
            increment_seconds=self._custom_increment.value(),
        )

    @property
    def stockfish_path(self) -> str | None:
        """Configured stockfish path, if any."""
        return self._stockfish_path

    def get_game_parameters(
        self,
    ) -> tuple[str, str, PlayerType, PlayerType, Difficulty, TimeControl]:
        """Return (white_name, black_name, white_type, black_type, difficulty, time_control)."""
        diff = self.selected_difficulty
        tc = self.selected_time_control

        if not self.is_vs_computer:
            w_name = self._white_name_edit.text().strip() or "White"
            b_name = self._black_name_edit.text().strip() or "Black"
            return (w_name, b_name, PlayerType.HUMAN, PlayerType.HUMAN, diff, tc)

        # Play vs Computer
        if self._radio_white.isChecked():
            human_color = Color.WHITE
        elif self._radio_black.isChecked():
            human_color = Color.BLACK
        else:
            human_color = random.choice([Color.WHITE, Color.BLACK])

        engine_name = f"Stockfish ({diff.display_name})"
        if human_color == Color.WHITE:
            return ("Player", engine_name, PlayerType.HUMAN, PlayerType.COMPUTER, diff, tc)
        return (engine_name, "Player", PlayerType.COMPUTER, PlayerType.HUMAN, diff, tc)
