"""Tests for Stockfish binary discovery."""

from pathlib import Path

from chess_desktop.engine.discovery import find_stockfish_binary, is_executable_binary


def test_discovery_finds_installed_stockfish() -> None:
    """Verify Stockfish is discovered on this machine at /usr/games/stockfish."""
    path = find_stockfish_binary()
    assert path is not None
    assert Path(path).exists()
    assert is_executable_binary(path)


def test_discovery_custom_path() -> None:
    """Verify custom path lookup validates executable permission."""
    # Invalid custom path returns None
    assert find_stockfish_binary("/non/existent/path/to/stockfish") is None

    # Valid custom path returns resolved path
    actual_path = find_stockfish_binary()
    assert actual_path is not None
    assert find_stockfish_binary(actual_path) == str(Path(actual_path).resolve())
