"""LAN multiplayer message protocol definitions and serialization."""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MessageType(Enum):
    """Supported network message types for LAN play."""

    HANDSHAKE = "handshake"
    HANDSHAKE_ACK = "handshake_ack"
    MOVE = "move"
    DRAW_OFFER = "draw_offer"
    DRAW_RESPONSE = "draw_response"
    RESIGN = "resign"
    SYNC_REQUEST = "sync_request"
    SYNC_STATE = "sync_state"
    PING = "ping"
    PONG = "pong"
    CHAT = "chat"


@dataclass(frozen=True)
class NetworkMessage:
    """Encapsulates a framed JSON network message."""

    type: MessageType
    payload: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Serialize message to a JSON string terminated by newline."""
        data = {
            "type": self.type.value,
            "payload": self.payload,
        }
        return json.dumps(data) + "\n"

    @classmethod
    def from_json(cls, line: str) -> "NetworkMessage":
        """Deserialize a trimmed JSON string into a NetworkMessage."""
        clean = line.strip()
        if not clean:
            raise ValueError("Empty message payload.")
        data = json.loads(clean)
        msg_type_str = data.get("type")
        if not msg_type_str:
            raise ValueError("Missing 'type' field in network message.")
        msg_type = MessageType(msg_type_str)
        payload = data.get("payload", {})
        return cls(type=msg_type, payload=payload)

    # Convenience Factory Methods
    @classmethod
    def handshake(
        cls,
        player_name: str,
        host_color: str,
        time_control_name: str,
        initial_time_ms: int,
        increment_ms: int,
    ) -> "NetworkMessage":
        return cls(
            type=MessageType.HANDSHAKE,
            payload={
                "player_name": player_name,
                "host_color": host_color,
                "time_control_name": time_control_name,
                "initial_time_ms": initial_time_ms,
                "increment_ms": increment_ms,
                "version": "1.0",
            },
        )

    @classmethod
    def handshake_ack(cls, player_name: str, accepted: bool = True) -> "NetworkMessage":
        return cls(
            type=MessageType.HANDSHAKE_ACK,
            payload={"player_name": player_name, "accepted": accepted},
        )

    @classmethod
    def move(
        cls,
        uci: str,
        white_time_ms: int | None = None,
        black_time_ms: int | None = None,
    ) -> "NetworkMessage":
        return cls(
            type=MessageType.MOVE,
            payload={
                "uci": uci,
                "white_time_ms": white_time_ms,
                "black_time_ms": black_time_ms,
            },
        )

    @classmethod
    def draw_offer(cls) -> "NetworkMessage":
        return cls(type=MessageType.DRAW_OFFER)

    @classmethod
    def draw_response(cls, accept: bool) -> "NetworkMessage":
        return cls(type=MessageType.DRAW_RESPONSE, payload={"accept": accept})

    @classmethod
    def resign(cls) -> "NetworkMessage":
        return cls(type=MessageType.RESIGN)

    @classmethod
    def sync_request(cls) -> "NetworkMessage":
        return cls(type=MessageType.SYNC_REQUEST)

    @classmethod
    def sync_state(
        cls,
        moves_uci: list[str],
        white_time_ms: int | None = None,
        black_time_ms: int | None = None,
    ) -> "NetworkMessage":
        return cls(
            type=MessageType.SYNC_STATE,
            payload={
                "moves_uci": moves_uci,
                "white_time_ms": white_time_ms,
                "black_time_ms": black_time_ms,
            },
        )

    @classmethod
    def ping(cls) -> "NetworkMessage":
        return cls(type=MessageType.PING)

    @classmethod
    def pong(cls) -> "NetworkMessage":
        return cls(type=MessageType.PONG)
