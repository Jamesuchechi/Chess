
from chess_desktop.network.lan_transport import LanTransport
from chess_desktop.network.protocol import MessageType, NetworkMessage


def test_transport_host_and_client_loopback(qtbot):
    server_transport = LanTransport()
    client_transport = LanTransport()

    # Start server on dynamic port 0
    assert server_transport.start_server(port=0) is True
    port = server_transport.port
    assert port > 0

    # Connect client
    with qtbot.waitSignal(server_transport.peer_connected, timeout=3000):
        with qtbot.waitSignal(client_transport.peer_connected, timeout=3000):
            client_transport.connect_to_host("127.0.0.1", port=port)

    assert server_transport.is_connected
    assert client_transport.is_connected

    # Test sending message from client to server
    msg_received = []

    def on_server_msg(msg: NetworkMessage):
        msg_received.append(msg)

    server_transport.message_received.connect(on_server_msg)

    test_msg = NetworkMessage.move("e2e4", 300000, 300000)
    with qtbot.waitSignal(server_transport.message_received, timeout=3000):
        client_transport.send_message(test_msg)

    assert len(msg_received) == 1
    assert msg_received[0].type == MessageType.MOVE
    assert msg_received[0].payload["uci"] == "e2e4"

    # Test sending application message from server to client
    client_received = []
    client_transport.message_received.connect(lambda m: client_received.append(m))

    draw_msg = NetworkMessage.draw_offer()
    with qtbot.waitSignal(client_transport.message_received, timeout=3000):
        server_transport.send_message(draw_msg)

    assert len(client_received) == 1
    assert client_received[0].type == MessageType.DRAW_OFFER

    # Cleanup
    server_transport.disconnect_all()
    client_transport.disconnect_all()
