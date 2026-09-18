"""Settings and Preferences dialog with tabs for Appearance, Audio, and Engine."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from chess_desktop.domain.theme import BoardTheme
from chess_desktop.engine.difficulty import Difficulty
from chess_desktop.engine.discovery import find_stockfish_binary
from chess_desktop.services.settings_service import SettingsService
from chess_desktop.services.sound_service import SoundService


class SettingsDialog(QDialog):
    """Configuration dialog for appearance, sound, and engine preferences."""

    def __init__(
        self,
        settings_service: SettingsService,
        sound_service: SoundService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings_service
        self._sound = sound_service

        self.setWindowTitle("Preferences")
        self.setFixedWidth(480)
        self.setModal(True)

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(18, 18, 18, 18)

        tabs = QTabWidget(self)

        # Tab 1: Appearance
        appearance_tab = QWidget()
        app_layout = QVBoxLayout(appearance_tab)
        app_layout.setSpacing(12)

        theme_group = QGroupBox("Board Theme", appearance_tab)
        theme_form = QFormLayout(theme_group)

        self._theme_combo = QComboBox(theme_group)
        for theme in BoardTheme.all_themes():
            self._theme_combo.addItem(theme.display_name, theme.name)

        # Pre-select current
        curr_theme = self._settings.board_theme
        for i in range(self._theme_combo.count()):
            if self._theme_combo.itemData(i) == curr_theme:
                self._theme_combo.setCurrentIndex(i)
                break

        theme_form.addRow("Theme:", self._theme_combo)

        # Swatch preview
        self._swatch_label = QLabel(theme_group)
        self._swatch_label.setFixedHeight(24)
        theme_form.addRow("Preview:", self._swatch_label)
        self._theme_combo.currentIndexChanged.connect(self._update_swatch)
        self._update_swatch()

        app_layout.addWidget(theme_group)

        # Piece Set Group
        piece_group = QGroupBox("Piece Style", appearance_tab)
        piece_form = QFormLayout(piece_group)
        self._piece_combo = QComboBox(piece_group)
        self._piece_combo.addItem("Standard (Cburnett SVG)", "standard")
        piece_form.addRow("Piece Set:", self._piece_combo)
        app_layout.addWidget(piece_group)
        app_layout.addStretch()

        tabs.addTab(appearance_tab, "Appearance")

        # Tab 2: Audio
        audio_tab = QWidget()
        audio_layout = QVBoxLayout(audio_tab)
        audio_layout.setSpacing(12)

        sound_group = QGroupBox("Sound Effects", audio_tab)
        sound_v_layout = QVBoxLayout(sound_group)
        sound_v_layout.setSpacing(10)

        self._sound_check = QCheckBox("Enable Sound Effects", sound_group)
        self._sound_check.setChecked(self._settings.sound_enabled)
        sound_v_layout.addWidget(self._sound_check)

        vol_layout = QHBoxLayout()
        vol_layout.addWidget(QLabel("Volume:", sound_group))
        self._vol_slider = QSlider(Qt.Orientation.Horizontal, sound_group)
        self._vol_slider.setRange(0, 100)
        self._vol_slider.setValue(self._settings.sound_volume)
        self._vol_label = QLabel(f"{self._settings.sound_volume}%", sound_group)
        self._vol_slider.valueChanged.connect(lambda v: self._vol_label.setText(f"{v}%"))
        vol_layout.addWidget(self._vol_slider)
        vol_layout.addWidget(self._vol_label)
        sound_v_layout.addLayout(vol_layout)

        test_btn = QPushButton("Test Move Sound", sound_group)
        test_btn.clicked.connect(self._on_test_sound)
        sound_v_layout.addWidget(test_btn)

        audio_layout.addWidget(sound_group)
        audio_layout.addStretch()
        tabs.addTab(audio_tab, "Audio")

        # Tab 3: Engine
        engine_tab = QWidget()
        eng_layout = QVBoxLayout(engine_tab)
        eng_layout.setSpacing(12)

        eng_group = QGroupBox("Stockfish Configuration", engine_tab)
        eng_form = QFormLayout(eng_group)

        path_box = QHBoxLayout()
        self._path_edit = QLineEdit(self._settings.stockfish_path, eng_group)
        browse_btn = QPushButton("Browse...", eng_group)
        browse_btn.clicked.connect(self._on_browse_engine)
        path_box.addWidget(self._path_edit)
        path_box.addWidget(browse_btn)
        eng_form.addRow("Engine Path:", path_box)

        self._diff_combo = QComboBox(eng_group)
        for diff in Difficulty:
            self._diff_combo.addItem(diff.display_name, diff.display_name)
        curr_diff = self._settings.default_difficulty
        idx = self._diff_combo.findText(curr_diff)
        if idx >= 0:
            self._diff_combo.setCurrentIndex(idx)
        eng_form.addRow("Default Level:", self._diff_combo)

        self._probe_label = QLabel(eng_group)
        self._update_engine_probe()
        eng_form.addRow("Status:", self._probe_label)

        self._delay_check = QCheckBox("Simulate realistic thinking delay (2–3 seconds)", eng_group)
        self._delay_check.setChecked(self._settings.thinking_delay_enabled)
        eng_form.addRow("", self._delay_check)

        eng_layout.addWidget(eng_group)
        eng_layout.addStretch()
        tabs.addTab(engine_tab, "Engine")

        layout.addWidget(tabs)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("Cancel", self)
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save Preferences", self)
        save_btn.setStyleSheet(
            "background-color: #4a752c; color: white; font-weight: bold; padding: 6px 14px;"
        )
        save_btn.clicked.connect(self._on_save)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _update_swatch(self) -> None:
        idx = self._theme_combo.currentIndex()
        theme_name = self._theme_combo.itemData(idx)
        theme = BoardTheme.from_name(str(theme_name))
        self._swatch_label.setStyleSheet(
            f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0.0 {theme.light_square}, stop:0.5 {theme.light_square}, stop:0.501 {theme.dark_square}, stop:1.0 {theme.dark_square});
                border: 1px solid #444444;
                border-radius: 4px;
            }}
            """
        )

    def _update_engine_probe(self) -> None:
        custom_path = self._path_edit.text().strip() or None
        found = find_stockfish_binary(custom_path)
        if found:
            self._probe_label.setText(f"✓ Found: {found}")
            self._probe_label.setStyleSheet("color: #769656; font-size: 11px;")
        else:
            self._probe_label.setText("⚠ Not found. Fallback engine will be used.")
            self._probe_label.setStyleSheet("color: #f59e0b; font-size: 11px;")

    def _on_browse_engine(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Stockfish Binary",
            "",
            "Executable Files (*);;All Files (*)",
        )
        if path:
            self._path_edit.setText(path)
            self._update_engine_probe()

    def _on_test_sound(self) -> None:
        if self._sound:
            self._sound.set_volume(self._vol_slider.value())
            self._sound.play("move")

    def accept(self) -> None:
        self._on_save()

    def _on_save(self) -> None:
        idx = self._theme_combo.currentIndex()
        theme_name = str(self._theme_combo.itemData(idx))
        self._settings.set_board_theme(theme_name)
        self._settings.set_sound_enabled(self._sound_check.isChecked())
        self._settings.set_sound_volume(self._vol_slider.value())
        self._settings.set_stockfish_path(self._path_edit.text().strip())
        self._settings.set_default_difficulty(self._diff_combo.currentText())
        self._settings.set_thinking_delay_enabled(self._delay_check.isChecked())

        if self._sound:
            self._sound.set_enabled(self._sound_check.isChecked())
            self._sound.set_volume(self._vol_slider.value())

        super().accept()
