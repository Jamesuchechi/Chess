
from chess_desktop.domain.enums import Color, GameStatus
from chess_desktop.domain.time_control import TimeControl
from chess_desktop.services.game_service import GameService


def test_lan_game_host_and_join_flow(qtbot):
    host_service = GameService()
    client_service = GameService()

    tc = TimeControl.rapid_10_0()

    # Host starts server on dynamic port 0
    assert host_service.host_lan_game(
        port=0,
        player_name="HostAlice",
        host_color=Color.WHITE,
        time_control=tc,
    ) is True
    port = host_service._lan_transport.port
    assert port > 0

    # Client joins
    with qtbot.waitSignal(host_service.lan_connected, timeout=3000):
        with qtbot.waitSignal(client_service.lan_connected, timeout=3000):
            client_service.join_lan_game(host_ip="127.0.0.1", port=port, player_name="ClientBob")

    # Give event loop a moment to finish handshake exchange
    qtbot.wait(100)

    assert host_service.is_lan_game is True
    assert client_service.is_lan_game is True
    assert host_service.local_player_color == Color.WHITE
    assert client_service.local_player_color == Color.BLACK
    assert host_service.is_flipped is False
    assert client_service.is_flipped is True

    # Host plays e2-e4
    with qtbot.waitSignal(client_service.move_made, timeout=3000):
        moved = host_service.try_move("e2", "e4")
        assert moved is True

    assert len(host_service.get_state().moves) == 1
    assert len(client_service.get_state().moves) == 1
    assert client_service.get_state().moves[-1].uci == "e2e4"

    # Verify Host cannot move during Black's turn:
    assert host_service.try_move("g8", "f6") is False

    # Client plays e7-e5
    with qtbot.waitSignal(host_service.move_made, timeout=3000):
        client_moved = client_service.try_move("e7", "e5")
        assert client_moved is True

    assert len(host_service.get_state().moves) == 2
    assert len(client_service.get_state().moves) == 2
    assert host_service.get_state().moves[-1].uci == "e7e5"

    # Test Draw offer and acceptance
    with qtbot.waitSignal(client_service.lan_draw_offered, timeout=3000):
        host_service.send_lan_draw_offer()

    # Client responds accepting draw
    with qtbot.waitSignal(host_service.game_over, timeout=3000):
        client_service.send_lan_draw_response(accept=True)

    assert host_service.get_state().status == GameStatus.DRAW_AGREED
    assert client_service.get_state().status == GameStatus.DRAW_AGREED

    # Cleanup
    host_service.cleanup()
    client_service.cleanup()


def test_lan_game_resignation(qtbot):
    host_service = GameService()
    client_service = GameService()

    host_service.host_lan_game(
        port=0,
        player_name="HostAlice",
        host_color=Color.BLACK,
        time_control=TimeControl.blitz_5_0(),
    )
    port = host_service._lan_transport.port

    with qtbot.waitSignal(host_service.lan_connected, timeout=3000):
        client_service.join_lan_game(host_ip="127.0.0.1", port=port, player_name="ClientBob")

    qtbot.wait(100)

    # Host is black, client is white
    assert host_service.local_player_color == Color.BLACK
    assert client_service.local_player_color == Color.WHITE

    # Client resigns
    with qtbot.waitSignal(host_service.game_over, timeout=3000):
        client_service.resign(Color.WHITE)

    assert host_service.get_state().status == GameStatus.RESIGNED
    assert client_service.get_state().status == GameStatus.RESIGNED

    host_service.cleanup()
    client_service.cleanup()
