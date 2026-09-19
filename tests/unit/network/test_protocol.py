import pytest

from chess_desktop.network.protocol import MessageType, NetworkMessage


def test_handshake_serialization():
    msg = NetworkMessage.handshake(
        player_name="Alice",
        host_color="white",
        time_control_name="5 min",
        initial_time_ms=300000,
        increment_ms=3000,
    )
    raw = msg.to_json()
    assert raw.endswith("\n")

    parsed = NetworkMessage.from_json(raw)
    assert parsed.type == MessageType.HANDSHAKE
    assert parsed.payload["player_name"] == "Alice"
    assert parsed.payload["host_color"] == "white"
    assert parsed.payload["initial_time_ms"] == 300000
    assert parsed.payload["increment_ms"] == 3000


def test_move_serialization():
    msg = NetworkMessage.move("e2e4", white_time_ms=298000, black_time_ms=300000)
    raw = msg.to_json()
    parsed = NetworkMessage.from_json(raw)
    assert parsed.type == MessageType.MOVE
    assert parsed.payload["uci"] == "e2e4"
    assert parsed.payload["white_time_ms"] == 298000


def test_draw_and_resign_serialization():
    offer = NetworkMessage.draw_offer()
    assert NetworkMessage.from_json(offer.to_json()).type == MessageType.DRAW_OFFER

    resp = NetworkMessage.draw_response(accept=True)
    parsed_resp = NetworkMessage.from_json(resp.to_json())
    assert parsed_resp.type == MessageType.DRAW_RESPONSE
    assert parsed_resp.payload["accept"] is True

    resign = NetworkMessage.resign()
    assert NetworkMessage.from_json(resign.to_json()).type == MessageType.RESIGN


def test_sync_state_serialization():
    msg = NetworkMessage.sync_state(["e2e4", "e7e5", "g1f3"], white_time_ms=280000, black_time_ms=290000)
    raw = msg.to_json()
    parsed = NetworkMessage.from_json(raw)
    assert parsed.type == MessageType.SYNC_STATE
    assert parsed.payload["moves_uci"] == ["e2e4", "e7e5", "g1f3"]
    assert parsed.payload["white_time_ms"] == 280000


def test_ping_pong_serialization():
    ping = NetworkMessage.ping()
    pong = NetworkMessage.pong()
    assert NetworkMessage.from_json(ping.to_json()).type == MessageType.PING
    assert NetworkMessage.from_json(pong.to_json()).type == MessageType.PONG


def test_invalid_json_handling():
    with pytest.raises(ValueError, match="Empty message payload"):
        NetworkMessage.from_json("   \n")

    with pytest.raises(ValueError, match="Missing 'type' field"):
        NetworkMessage.from_json('{"payload": {}}')
