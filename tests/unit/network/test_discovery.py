from chess_desktop.network.discovery import (
    get_hotspot_instructions,
    get_local_ip_addresses,
    get_primary_lan_ip,
)


def test_get_primary_lan_ip():
    ip = get_primary_lan_ip()
    assert isinstance(ip, str)
    assert len(ip.split(".")) == 4


def test_get_local_ip_addresses():
    ips = get_local_ip_addresses()
    assert isinstance(ips, list)
    assert len(ips) >= 1


def test_get_hotspot_instructions():
    instructions = get_hotspot_instructions()
    assert "Hotspot Setup" in instructions
