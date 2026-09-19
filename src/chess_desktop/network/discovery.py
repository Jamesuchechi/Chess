"""LAN discovery and IP resolution utilities for local multiplayer."""

import logging
import socket

logger = logging.getLogger(__name__)


def get_local_ip_addresses() -> list[str]:
    """Return all detected non-loopback IPv4 addresses on this machine."""
    ips: list[str] = []
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127.") and ":" not in ip:
                ips.append(ip)
    except Exception as e:
        logger.debug("Hostname IP lookup failed: %s", e)

    # Secondary method using dummy UDP socket connection
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        # Connect to a public DNS IP (no packet is actually sent)
        s.connect(("8.8.8.8", 80))
        primary_ip = s.getsockname()[0]
        s.close()
        if primary_ip and primary_ip not in ips and not primary_ip.startswith("127."):
            ips.insert(0, primary_ip)
    except Exception:
        pass

    if not ips:
        ips.append("127.0.0.1")

    return list(dict.fromkeys(ips))


def get_primary_lan_ip() -> str:
    """Return the most likely LAN IP address to share with the opponent."""
    ips = get_local_ip_addresses()
    # Prefer standard private network ranges (192.168.x.x, 10.x.x.x, 172.16-31.x.x)
    for ip in ips:
        if ip.startswith("192.168.") or ip.startswith("10."):
            return ip
    for ip in ips:
        if not ip.startswith("127."):
            return ip
    return "127.0.0.1"


def get_hotspot_instructions() -> str:
    """Return concise setup instructions for connecting over a mobile hotspot."""
    return (
        "Hotspot Setup:\n"
        "1. Turn on Mobile Hotspot / Wi-Fi Hotspot on either laptop or phone.\n"
        "2. Connect both laptops to that same hotspot network.\n"
        "3. Enter the Host IP address shown above on the second laptop."
    )
