"""Non-blocking TCP socket transport layer for LAN multiplayer games."""

import logging

from PySide6.QtCore import QByteArray, QObject, QTimer, Signal
from PySide6.QtNetwork import QAbstractSocket, QHostAddress, QTcpServer, QTcpSocket

from chess_desktop.network.protocol import MessageType, NetworkMessage

logger = logging.getLogger(__name__)


class LanTransport(QObject):
    """Manages TCP socket connections and framed JSON messaging for LAN multiplayer."""

    peer_connected = Signal(str)  # peer_address
    peer_disconnected = Signal(str)  # reason
    message_received = Signal(object)  # NetworkMessage
    connection_error = Signal(str)  # error_message

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._server: QTcpServer | None = None
        self._socket: QTcpSocket | None = None
        self._is_host = False
        self._port = 5000
        self._read_buffer = bytearray()

        # Heartbeat ping timer
        self._ping_timer = QTimer(self)
        self._ping_timer.setInterval(5000)
        self._ping_timer.timeout.connect(self._send_ping)

    @property
    def is_host(self) -> bool:
        """True if acting as TCP server host."""
        return self._is_host

    @property
    def is_connected(self) -> bool:
        """True if an active TCP connection to peer is open."""
        return self._socket is not None and self._socket.state() == QAbstractSocket.SocketState.ConnectedState

    @property
    def port(self) -> int:
        return self._port

    @property
    def peer_address(self) -> str:
        """IP address of connected peer."""
        if self._socket is not None:
            addr = self._socket.peerAddress().toString()
            return addr.replace("::ffff:", "")
        return ""

    def start_server(self, port: int = 5000) -> bool:
        """Start listening for client connection on specified TCP port."""
        self.disconnect_all()
        self._is_host = True
        self._port = port

        self._server = QTcpServer(self)
        self._server.newConnection.connect(self._on_new_incoming_connection)

        if not self._server.listen(QHostAddress.SpecialAddress.AnyIPv4, port):
            err = self._server.errorString()
            logger.error("Failed to start LAN host on port %d: %s", port, err)
            self.connection_error.emit(f"Failed to start server on port {port}: {err}")
            return False

        self._port = self._server.serverPort()
        logger.info("LAN multiplayer host listening on port %d", self._port)
        return True

    def connect_to_host(self, host_ip: str, port: int = 5000) -> bool:
        """Connect as client to a host IP and port."""
        self.disconnect_all()
        self._is_host = False
        self._port = port

        self._socket = QTcpSocket(self)
        self._setup_socket_signals(self._socket)

        logger.info("Connecting to LAN host at %s:%d...", host_ip, port)
        self._socket.connectToHost(host_ip, port)
        return True

    def _on_new_incoming_connection(self) -> None:
        """Handle incoming client socket connection on server."""
        if self._server is None:
            return

        client_socket = self._server.nextPendingConnection()

        # If already have an active client, reject new connection
        if self._socket is not None and self._socket.state() == QAbstractSocket.SocketState.ConnectedState:
            logger.warning("Rejected secondary connection attempt from %s", client_socket.peerAddress().toString())
            client_socket.disconnectFromHost()
            client_socket.deleteLater()
            return

        self._socket = client_socket
        self._setup_socket_signals(self._socket)
        peer = self.peer_address
        logger.info("Peer connected to host from %s", peer)
        self._ping_timer.start()
        self.peer_connected.emit(peer)

    def _setup_socket_signals(self, sock: QTcpSocket) -> None:
        sock.connected.connect(self._on_socket_connected)
        sock.readyRead.connect(self._on_socket_ready_read)
        sock.disconnected.connect(self._on_socket_disconnected)
        sock.errorOccurred.connect(self._on_socket_error)

    def _on_socket_connected(self) -> None:
        peer = self.peer_address
        logger.info("Successfully connected to peer at %s", peer)
        self._ping_timer.start()
        self.peer_connected.emit(peer)

    def _on_socket_ready_read(self) -> None:
        """Read data from socket, buffer bytes, and split by newline framing."""
        if self._socket is None:
            return

        data: QByteArray = self._socket.readAll()
        self._read_buffer.extend(data.data())

        while b"\n" in self._read_buffer:
            newline_idx = self._read_buffer.index(b"\n")
            line_bytes = self._read_buffer[:newline_idx]
            del self._read_buffer[: newline_idx + 1]

            line_str = line_bytes.decode("utf-8", errors="replace").strip()
            if not line_str:
                continue

            try:
                msg = NetworkMessage.from_json(line_str)
                if msg.type == MessageType.PING:
                    self.send_message(NetworkMessage.pong())
                elif msg.type == MessageType.PONG:
                    pass
                else:
                    self.message_received.emit(msg)
            except Exception as e:
                logger.warning("Malformed network payload received: %s (%s)", line_str, e)

    def _on_socket_disconnected(self) -> None:
        logger.info("Peer socket disconnected.")
        self._ping_timer.stop()
        self._read_buffer.clear()
        self.peer_disconnected.emit("Peer disconnected.")

    def _on_socket_error(self, socket_error: QAbstractSocket.SocketError) -> None:
        if self._socket is not None:
            err_msg = self._socket.errorString()
            logger.error("LAN socket error: %s (%s)", socket_error, err_msg)
            self.connection_error.emit(err_msg)

    def send_message(self, msg: NetworkMessage) -> bool:
        """Transmit a formatted JSON network message to the peer."""
        if not self.is_connected or self._socket is None:
            logger.warning("Attempted to send message %s when not connected.", msg.type.value)
            return False

        payload_bytes = msg.to_json().encode("utf-8")
        bytes_written = self._socket.write(payload_bytes)
        self._socket.flush()
        return bytes_written == len(payload_bytes)

    def _send_ping(self) -> None:
        if self.is_connected:
            self.send_message(NetworkMessage.ping())

    def disconnect_all(self) -> None:
        """Close socket and stop server cleanly."""
        self._ping_timer.stop()
        self._read_buffer.clear()

        if self._socket is not None:
            try:
                self._socket.blockSignals(True)
                self._socket.disconnectFromHost()
                self._socket.close()
            except Exception:
                pass
            self._socket = None

        if self._server is not None:
            try:
                self._server.close()
            except Exception:
                pass
            self._server = None

        self._is_host = False
