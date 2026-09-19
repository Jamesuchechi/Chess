"""LAN multiplayer networking package."""

from chess_desktop.network.discovery import get_local_ip_addresses, get_primary_lan_ip
from chess_desktop.network.lan_transport import LanTransport
from chess_desktop.network.protocol import MessageType, NetworkMessage

__all__ = [
    "LanTransport",
    "MessageType",
    "NetworkMessage",
    "get_local_ip_addresses",
    "get_primary_lan_ip",
]
