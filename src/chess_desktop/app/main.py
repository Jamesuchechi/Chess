"""Entry point for Chess Desktop."""

import logging
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from chess_desktop.ui.windows.main_window import MainWindow

logger = logging.getLogger(__name__)


def main() -> int:
    """Initialize and run the Chess Desktop application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("Starting Chess Desktop")

    # High-DPI scaling policy for sharp vector rendering
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Chess Desktop")
    app.setOrganizationName("ChessDesktop")

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
