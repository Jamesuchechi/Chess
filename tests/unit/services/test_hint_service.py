
from chess_desktop.domain.enums import PlayerType
from chess_desktop.engine.fallback_engine import FallbackEngine
from chess_desktop.services.engine_worker import EngineWorker
from chess_desktop.services.game_service import GameService


def test_request_hint_starting_position(qtbot):
    worker = EngineWorker(engine=FallbackEngine(), thinking_delay_enabled=False)
    service = GameService(engine_worker=worker)

    service.new_game("Player1", "Player2", PlayerType.HUMAN, PlayerType.HUMAN)

    hint_results = []
    service.hint_received.connect(lambda f, t, s: hint_results.append((f, t, s)))

    with qtbot.waitSignal(service.hint_received, timeout=4000):
        assert service.request_hint() is True

    assert len(hint_results) == 1
    from_sq, to_sq, san = hint_results[0]
    assert len(from_sq) == 2
    assert len(to_sq) == 2
    assert san != ""
    assert service.active_hint == (from_sq, to_sq, san)

    # Test clear_hint
    service.clear_hint()
    assert service.active_hint is None

    service.cleanup()


def test_hint_cleared_on_move(qtbot):
    worker = EngineWorker(engine=FallbackEngine(), thinking_delay_enabled=False)
    service = GameService(engine_worker=worker)

    service.new_game("Player1", "Player2", PlayerType.HUMAN, PlayerType.HUMAN)

    with qtbot.waitSignal(service.hint_received, timeout=4000):
        service.request_hint()

    assert service.active_hint is not None

    # Play move
    service.try_move("e2", "e4")
    assert service.active_hint is None

    service.cleanup()
