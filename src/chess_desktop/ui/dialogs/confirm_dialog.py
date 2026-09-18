"""Reusable styled confirmation dialog."""

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ConfirmDialog(QDialog):
    """General confirmation dialog for critical user actions."""

    def __init__(
        self,
        title: str,
        message: str,
        confirm_text: str = "Confirm",
        cancel_text: str = "Cancel",
        is_destructive: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(320)

        self._title = title
        self._message = message
        self._confirm_text = confirm_text
        self._cancel_text = cancel_text
        self._is_destructive = is_destructive

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        title_lbl = QLabel(self._title, self)
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        layout.addWidget(title_lbl)

        msg_lbl = QLabel(self._message, self)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet("font-size: 13px; color: #cccccc; padding-bottom: 6px;")
        layout.addWidget(msg_lbl)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self._cancel_btn = QPushButton(self._cancel_text, self)
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

        self._confirm_btn = QPushButton(self._confirm_text, self)
        if self._is_destructive:
            confirm_style = """
                QPushButton {
                    background-color: #b91c1c;
                    color: #ffffff;
                    padding: 6px 14px;
                    border-radius: 4px;
                    font-size: 13px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #dc2626;
                }
            """
        else:
            confirm_style = """
                QPushButton {
                    background-color: #769656;
                    color: #ffffff;
                    padding: 6px 14px;
                    border-radius: 4px;
                    font-size: 13px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #87ab62;
                }
            """
        self._confirm_btn.setStyleSheet(confirm_style)
        self._confirm_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self._confirm_btn)

        layout.addLayout(btn_layout)
