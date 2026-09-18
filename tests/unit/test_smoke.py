"""Smoke tests verifying package imports and dependencies."""

import chess

import chess_desktop
from chess_desktop.ui.windows.main_window import MainWindow


def test_package_version() -> None:
    """Verify package version is defined."""
    assert chess_desktop.__version__ == "0.1.0"


def test_python_chess_dependency() -> None:
    """Verify python-chess initializes correctly."""
    board = chess.Board()
    assert board.is_valid()
    assert len(list(board.legal_moves)) == 20


def test_main_window_class_exists() -> None:
    """Verify MainWindow class can be referenced."""
    assert MainWindow is not None
