"""Dialog for specifying a title when saving a game."""

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class SaveAsDialog(QDialog):
    """Dialog prompting the user for a game title."""

    def __init__(
        self,
        default_title: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Save Game")
        self.setFixedWidth(400)
        self.setModal(True)

        self._title_edit = QLineEdit(default_title, self)
        self._title_edit.selectAll()

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        label = QLabel("Enter a title for this game:", self)
        label.setStyleSheet("color: #e0e0e0; font-size: 13px; font-weight: bold;")
        layout.addWidget(label)

        self._title_edit.setStyleSheet(
            """
            QLineEdit {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #769656;
            }
            """
        )
        self._title_edit.returnPressed.connect(self._on_save)
        layout.addWidget(self._title_edit)

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

        self._save_btn = QPushButton("Save", self)
        self._save_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #769656;
                color: #ffffff;
                padding: 6px 16px;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #87ab62;
            }
            """
        )
        self._save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self._save_btn)

        layout.addLayout(btn_layout)

        self.setStyleSheet(
            """
            QDialog {
                background-color: #1e1e1e;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
            }
            """
        )

    def _on_save(self) -> None:
        title = self.get_title()
        if title:
            self.accept()

    def get_title(self) -> str:
        """Return the trimmed title entered by user."""
        return self._title_edit.text().strip()
