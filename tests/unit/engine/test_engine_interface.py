"""Tests for engine difficulty presets and FallbackEngine."""

import pytest

from chess_desktop.engine.difficulty import Difficulty
from chess_desktop.engine.fallback_engine import FallbackEngine


def test_difficulty_parameters() -> None:
    """Verify Difficulty presets provide valid UCI constraint values."""
    for diff in Difficulty:
        assert 0 <= diff.skill_level <= 20
        assert diff.depth_limit >= 1
        assert diff.time_limit_ms >= 50
        assert diff.display_name
        assert diff.description


def test_fallback_engine_play_move() -> None:
    """Verify FallbackEngine returns a legal move and respects stop."""
    engine = FallbackEngine()
    engine.start()
    assert engine.is_ready()

    engine.set_position(moves_uci=["e2e4"])
    move = engine.search_best_move(depth=1, time_ms=10, skill_level=1)
    assert len(move) in (4, 5)

    engine.stop()
    engine.quit()
    assert not engine.is_ready()


def test_fallback_engine_not_started_error() -> None:
    """Verify searching on an unstarted fallback engine raises RuntimeError."""
    engine = FallbackEngine()
    with pytest.raises(RuntimeError):
        engine.search_best_move()
