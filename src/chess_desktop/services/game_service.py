import dataclasses
import logging
from typing import Any

import chess
from PySide6.QtCore import QObject, Qt, Signal

from chess_desktop.chess.board import ChessBoard
from chess_desktop.chess.clock import ChessClock
from chess_desktop.chess.move_service import MoveService
from chess_desktop.domain.enums import Color, GameStatus, PieceType, PlayerType
from chess_desktop.domain.game import Game
from chess_desktop.domain.game_state import GameState, MoveRecord
from chess_desktop.domain.player import Player
from chess_desktop.domain.time_control import TimeControl
from chess_desktop.engine.difficulty import Difficulty
from chess_desktop.network.lan_transport import LanTransport
from chess_desktop.network.protocol import MessageType, NetworkMessage
from chess_desktop.services.engine_worker import EngineWorker

logger = logging.getLogger(__name__)


class GameService(QObject):
    """Central orchestrator for active chess matches, engine calculations, and LAN multiplayer."""

    # Qt Signals
    state_changed = Signal(object)  # GameState
    move_made = Signal(object)  # MoveRecord
    game_over = Signal(object, str)  # (GameStatus, message)
    board_flipped = Signal(bool)  # is_flipped
    promotion_requested = Signal(str, str)  # (from_sq, to_sq)
    review_changed = Signal(object)  # int | None
    engine_thinking_changed = Signal(bool)  # is_thinking
    engine_error = Signal(str)  # error_message
    hint_received = Signal(str, str, str)  # (from_sq, to_sq, san)
    hint_cleared = Signal()
    clock_ticked = Signal(int, int)  # (white_ms, black_ms)
    clock_timeout = Signal(object)  # (Color)

    # LAN Multiplayer Signals
    lan_connected = Signal(str)  # peer_address
    lan_disconnected = Signal(str)  # reason
    lan_peer_joined = Signal(str)  # peer_name
    lan_draw_offered = Signal()
    lan_error = Signal(str)

    # Private queued-dispatch signals — emit these instead of calling the
    # EngineWorker slots directly so that the call is marshalled onto the
    # worker's QThread event loop rather than executing on the GUI thread.
    _request_move_signal = Signal(str, list, object)  # (fen, moves_uci, difficulty)
    _request_hint_signal = Signal(str, list)  # (fen, moves_uci)
    _restart_engine_signal = Signal()

    def __init__(
        self,
        parent: Any = None,
        engine_worker: EngineWorker | None = None,
    ) -> None:
        super().__init__(parent)
        self._board = ChessBoard()
        self._moves: list[MoveRecord] = []
        self._last_move: tuple[str, str] | None = None
        self._is_flipped = False
        self._review_ply: int | None = None
        self._review_board: ChessBoard | None = None

        self._clock = ChessClock(parent=self)
        self._clock.tick.connect(self._on_clock_tick)
        self._clock.timeout.connect(self._on_clock_timeout)

        self._difficulty: Difficulty = Difficulty.INTERMEDIATE
        self._is_engine_thinking = False
        self._active_hint: tuple[str, str, str] | None = None
        self._engine_worker: EngineWorker | None = None
        if engine_worker is not None:
            self.set_engine_worker(engine_worker)

        # LAN Multiplayer State
        self._is_lan_game = False
        self._lan_transport: LanTransport | None = None
        self._local_player_color = Color.WHITE
        self._local_player_name = "Player"

        self._white_player = Player("Player", Color.WHITE, player_type=PlayerType.HUMAN)
        self._black_player = Player(
            f"Stockfish ({self._difficulty.display_name})",
            Color.BLACK,
            player_type=PlayerType.COMPUTER,
        )
        self._game = Game(
            white_player=self._white_player,
            black_player=self._black_player,
            state=MoveService.build_game_state(
                self._board,
                None,
                [],
                white_time_ms=self._clock.white_time_ms,
                black_time_ms=self._clock.black_time_ms,
                time_control=self._clock.time_control,
            ),
        )

    @property
    def clock(self) -> ChessClock:
        """Active chess clock manager."""
        return self._clock

    def _on_clock_tick(self, white_ms: int, black_ms: int) -> None:
        self.clock_ticked.emit(white_ms, black_ms)

    def _on_clock_timeout(self, timed_out_color: Color) -> None:
        if self.get_state().status.is_game_over:
            return

        self.cancel_engine_search()
        winner = timed_out_color.opposite
        msg = f"{timed_out_color.value.capitalize()} ran out of time. {winner.value.capitalize()} wins."
        state = MoveService.build_game_state(
            self._board,
            self._last_move,
            self._moves,
            review_ply=self._review_ply,
            status_override=GameStatus.TIMEOUT,
            status_message_override=msg,
            white_time_ms=self._clock.white_time_ms,
            black_time_ms=self._clock.black_time_ms,
            time_control=self._clock.time_control,
        )
        self._game.state = state
        logger.info("Timeout: %s", msg)
        self.clock_timeout.emit(timed_out_color)
        self.state_changed.emit(state)
        self.game_over.emit(GameStatus.TIMEOUT, msg)

    @property
    def is_vs_computer(self) -> bool:
        """True if either side is controlled by a computer engine."""
        return not self._is_lan_game and (
            self._white_player.player_type == PlayerType.COMPUTER
            or self._black_player.player_type == PlayerType.COMPUTER
        )

    @property
    def is_lan_game(self) -> bool:
        """True if active match is played over LAN networking."""
        return self._is_lan_game

    @property
    def is_lan_host(self) -> bool:
        """True if hosting the LAN match."""
        return self._is_lan_game and self._lan_transport is not None and self._lan_transport.is_host

    @property
    def local_player_color(self) -> Color:
        """The local human player's assigned color in LAN multiplayer."""
        return self._local_player_color

    @property
    def is_computer_thinking(self) -> bool:
        """True if the engine worker is currently calculating a move."""
        return self._is_engine_thinking

    @property
    def engine_difficulty(self) -> Difficulty:
        """Active engine difficulty preset."""
        return self._difficulty

    def set_engine_worker(self, worker: EngineWorker) -> None:
        """Attach an EngineWorker instance and wire signals."""
        if self._engine_worker is not None:
            self._engine_worker.stop_worker()

        self._engine_worker = worker
        # Worker → GameService (results delivered back to GUI thread via AutoConnection)
        self._engine_worker.best_move_found.connect(self._on_engine_move)
        self._engine_worker.hint_found.connect(self._on_engine_hint)
        self._engine_worker.search_started.connect(self._on_search_started)
        self._engine_worker.search_stopped.connect(self._on_search_stopped)
        self._engine_worker.engine_error.connect(self._on_engine_error)
        # GameService → Worker: use QueuedConnection so the call is posted to the
        # worker thread's event loop rather than executing synchronously on the GUI thread.
        self._request_move_signal.connect(
            worker.request_move, Qt.ConnectionType.QueuedConnection
        )
        self._request_hint_signal.connect(
            worker.request_hint, Qt.ConnectionType.QueuedConnection
        )
        self._restart_engine_signal.connect(
            worker.restart_engine, Qt.ConnectionType.QueuedConnection
        )
        self._engine_worker.start_worker()

    @property
    def active_hint(self) -> tuple[str, str, str] | None:
        """Current active best move suggestion (from_sq, to_sq, san)."""
        return self._active_hint

    def request_hint(self) -> bool:
        """Request the engine to compute the top recommended move."""
        if self._is_engine_thinking or self.is_reviewing:
            return False

        state = self.get_state()
        if state.status.is_game_over:
            return False

        self.ensure_engine_worker()
        moves_uci = [m.uci for m in self._moves]
        self._request_hint_signal.emit(state.fen, moves_uci)
        return True

    def clear_hint(self) -> None:
        """Dismiss the active hint overlay."""
        if self._active_hint is not None:
            self._active_hint = None
            self.hint_cleared.emit()

    def _on_engine_hint(self, uci_move: str) -> None:
        """Process hint returned by engine worker."""
        if not uci_move or len(uci_move) < 4:
            return
        from_sq = uci_move[:2]
        to_sq = uci_move[2:4]
        try:
            move_obj = chess.Move.from_uci(uci_move)
            san = self._board._board.san(move_obj)
        except Exception:
            san = uci_move

        self._active_hint = (from_sq, to_sq, san)
        self.hint_received.emit(from_sq, to_sq, san)

    def ensure_engine_worker(self) -> EngineWorker:
        """Ensure an EngineWorker is initialized and started."""
        if self._engine_worker is None:
            worker = EngineWorker()
            self.set_engine_worker(worker)
        assert self._engine_worker is not None
        return self._engine_worker

    def cancel_engine_search(self) -> None:
        """Interrupt and cancel any active engine search."""
        if self._engine_worker is not None:
            self._engine_worker.cancel_search()
        self._is_engine_thinking = False
        self.engine_thinking_changed.emit(False)

    def restart_engine(self) -> None:
        """Restart engine backend and re-trigger calculation if needed."""
        self._is_engine_thinking = False
        self.engine_thinking_changed.emit(False)
        self.ensure_engine_worker()
        self._restart_engine_signal.emit()
        # Re-trigger is posted *after* the restart signal so it arrives on the
        # worker thread after the restart slot has already completed its work.
        self._trigger_engine_if_needed()

    def _on_engine_error(self, error_message: str) -> None:
        """Handle engine execution failure or process crash."""
        logger.error("Engine failure reported: %s", error_message)
        self._is_engine_thinking = False
        self.engine_thinking_changed.emit(False)
        self.engine_error.emit(error_message)

    def _on_search_started(self) -> None:
        self._is_engine_thinking = True
        self.engine_thinking_changed.emit(True)

    def _on_search_stopped(self) -> None:
        self._is_engine_thinking = False
        self.engine_thinking_changed.emit(False)

    @property
    def board(self) -> ChessBoard:
        """Active live chess board wrapper."""
        return self._board

    @property
    def display_board(self) -> ChessBoard:
        """Board to be rendered on screen (review snapshot or live board)."""
        if self._review_ply is not None and self._review_board is not None:
            return self._review_board
        return self._board

    @property
    def is_flipped(self) -> bool:
        """True if board is flipped (Black at bottom)."""
        return self._is_flipped

    @property
    def is_reviewing(self) -> bool:
        """True if viewing past moves rather than live head."""
        return self._review_ply is not None and self._review_ply < len(self._moves)

    @property
    def current_ply(self) -> int:
        """Currently viewed ply index (0 to N)."""
        return self._review_ply if self._review_ply is not None else len(self._moves)

    @property
    def can_undo(self) -> bool:
        """True if a move can be undone (disabled in LAN multiplayer)."""
        return not self._is_lan_game and len(self._moves) > 0 and not self.get_state().status.is_game_over

    def new_game(
        self,
        white_name: str = "Player",
        black_name: str | None = None,
        white_type: PlayerType = PlayerType.HUMAN,
        black_type: PlayerType = PlayerType.COMPUTER,
        difficulty: Difficulty = Difficulty.INTERMEDIATE,
        time_control: TimeControl | None = None,
    ) -> None:
        """Reset and start a new local / computer game."""
        self.clear_hint()
        self.disconnect_lan()
        self.cancel_engine_search()
        self._difficulty = difficulty
        tc = time_control or TimeControl.unlimited()
        self._clock.reset(tc)

        if black_name is None:
            black_name = (
                f"Stockfish ({difficulty.display_name})"
                if black_type == PlayerType.COMPUTER
                else "Black"
            )

        self._board.reset()
        self._moves.clear()
        self._last_move = None
        self._review_ply = None
        self._review_board = None
        self._white_player = Player(white_name, Color.WHITE, player_type=white_type)
        self._black_player = Player(black_name, Color.BLACK, player_type=black_type)

        state = MoveService.build_game_state(
            self._board,
            None,
            [],
            white_time_ms=self._clock.white_time_ms,
            black_time_ms=self._clock.black_time_ms,
            time_control=tc,
        )
        self._game = Game(
            white_player=self._white_player,
            black_player=self._black_player,
            state=state,
        )

        logger.info(
            "New game started: %s (%s) vs %s (%s) [%s]",
            white_name,
            white_type.name,
            black_name,
            black_type.name,
            tc.name,
        )
        self.review_changed.emit(None)
        self.state_changed.emit(state)

        if not tc.is_unlimited:
            self._clock.start(Color.WHITE)

        if self.is_vs_computer:
            self._trigger_engine_if_needed()

    # LAN Multiplayer Orchestration
    def host_lan_game(
        self,
        port: int = 5000,
        player_name: str = "Host",
        host_color: Color = Color.WHITE,
        time_control: TimeControl | None = None,
    ) -> bool:
        """Initialize and host a LAN multiplayer match."""
        self.disconnect_lan()
        self.cancel_engine_search()

        self._is_lan_game = True
        self._local_player_color = host_color
        self._local_player_name = player_name
        tc = time_control or TimeControl.unlimited()

        self._board.reset()
        self._moves.clear()
        self._last_move = None
        self._review_ply = None
        self._review_board = None
        self._clock.reset(tc)

        if host_color == Color.WHITE:
            self._white_player = Player(player_name, Color.WHITE, PlayerType.HUMAN)
            self._black_player = Player("Waiting for opponent...", Color.BLACK, PlayerType.HUMAN)
            self._is_flipped = False
        else:
            self._white_player = Player("Waiting for opponent...", Color.WHITE, PlayerType.HUMAN)
            self._black_player = Player(player_name, Color.BLACK, PlayerType.HUMAN)
            self._is_flipped = True

        state = MoveService.build_game_state(
            self._board,
            None,
            [],
            white_time_ms=self._clock.white_time_ms,
            black_time_ms=self._clock.black_time_ms,
            time_control=tc,
        )
        self._game = Game(self._white_player, self._black_player, state=state)

        self._lan_transport = LanTransport(parent=self)
        self._lan_transport.peer_connected.connect(self._on_lan_peer_connected)
        self._lan_transport.peer_disconnected.connect(self._on_lan_peer_disconnected)
        self._lan_transport.message_received.connect(self._on_lan_message_received)
        self._lan_transport.connection_error.connect(self._on_lan_connection_error)

        success = self._lan_transport.start_server(port)
        if success:
            self.board_flipped.emit(self._is_flipped)
            self.review_changed.emit(None)
            self.state_changed.emit(state)
        return success

    def join_lan_game(
        self,
        host_ip: str,
        port: int = 5000,
        player_name: str = "Client",
    ) -> bool:
        """Connect as client to a host LAN multiplayer match."""
        self.disconnect_lan()
        self.cancel_engine_search()

        self._is_lan_game = True
        self._local_player_name = player_name
        self._board.reset()
        self._moves.clear()
        self._last_move = None
        self._review_ply = None
        self._review_board = None

        self._lan_transport = LanTransport(parent=self)
        self._lan_transport.peer_connected.connect(self._on_lan_peer_connected)
        self._lan_transport.peer_disconnected.connect(self._on_lan_peer_disconnected)
        self._lan_transport.message_received.connect(self._on_lan_message_received)
        self._lan_transport.connection_error.connect(self._on_lan_connection_error)

        return self._lan_transport.connect_to_host(host_ip, port)

    def disconnect_lan(self) -> None:
        """Disconnect and tear down LAN transport cleanly."""
        if self._lan_transport is not None:
            self._lan_transport.disconnect_all()
            self._lan_transport.deleteLater()
            self._lan_transport = None
        self._is_lan_game = False

    def _on_lan_peer_connected(self, peer_address: str) -> None:
        logger.info("LAN peer connected: %s", peer_address)
        self.lan_connected.emit(peer_address)

        # If Host: Send Handshake with match configuration
        if self.is_lan_host and self._lan_transport is not None:
            tc = self._clock.time_control or TimeControl.unlimited()
            msg = NetworkMessage.handshake(
                player_name=self._local_player_name,
                host_color=self._local_player_color.value,
                time_control_name=tc.name,
                initial_time_ms=tc.total_base_ms,
                increment_ms=tc.increment_ms,
            )
            self._lan_transport.send_message(msg)

    def _on_lan_peer_disconnected(self, reason: str) -> None:
        logger.info("LAN peer disconnected: %s", reason)
        self.lan_disconnected.emit(reason)

    def _on_lan_connection_error(self, error_msg: str) -> None:
        logger.error("LAN transport error: %s", error_msg)
        self.lan_error.emit(error_msg)

    def _on_lan_message_received(self, msg: NetworkMessage) -> None:
        """Process incoming LAN network message."""
        match msg.type:
            case MessageType.HANDSHAKE:
                self._handle_lan_handshake(msg.payload)
            case MessageType.HANDSHAKE_ACK:
                self._handle_lan_handshake_ack(msg.payload)
            case MessageType.MOVE:
                self._handle_lan_move(msg.payload)
            case MessageType.DRAW_OFFER:
                self.lan_draw_offered.emit()
            case MessageType.DRAW_RESPONSE:
                if msg.payload.get("accept", False):
                    self.accept_draw()
            case MessageType.RESIGN:
                # Opponent resigned -> trigger win for local player
                opp_color = self._local_player_color.opposite
                self.resign(opp_color)
            case MessageType.SYNC_REQUEST:
                self._handle_lan_sync_request()
            case MessageType.SYNC_STATE:
                self._handle_lan_sync_state(msg.payload)

    def _handle_lan_handshake(self, payload: dict[str, Any]) -> None:
        """Client side: establish game configuration based on host handshake."""
        host_name = payload.get("player_name", "Host")
        host_color_str = payload.get("host_color", "white")
        host_color = Color.WHITE if host_color_str == "white" else Color.BLACK

        tc_name = payload.get("time_control_name", "Untimed")
        init_ms = payload.get("initial_time_ms", 0)
        inc_ms = payload.get("increment_ms", 0)
        tc = TimeControl(tc_name, init_ms, inc_ms)

        self._local_player_color = host_color.opposite
        self._clock.reset(tc)

        if self._local_player_color == Color.WHITE:
            self._white_player = Player(self._local_player_name, Color.WHITE, PlayerType.HUMAN)
            self._black_player = Player(host_name, Color.BLACK, PlayerType.HUMAN)
            self._is_flipped = False
        else:
            self._white_player = Player(host_name, Color.WHITE, PlayerType.HUMAN)
            self._black_player = Player(self._local_player_name, Color.BLACK, PlayerType.HUMAN)
            self._is_flipped = True

        state = MoveService.build_game_state(
            self._board,
            None,
            [],
            white_time_ms=self._clock.white_time_ms,
            black_time_ms=self._clock.black_time_ms,
            time_control=tc,
        )
        self._game = Game(self._white_player, self._black_player, state=state)

        # Send ACK back to host
        if self._lan_transport is not None:
            self._lan_transport.send_message(NetworkMessage.handshake_ack(self._local_player_name))

        self.board_flipped.emit(self._is_flipped)
        self.review_changed.emit(None)
        self.state_changed.emit(state)
        self.lan_peer_joined.emit(host_name)

        if not tc.is_unlimited:
            self._clock.start(Color.WHITE)

    def _handle_lan_handshake_ack(self, payload: dict[str, Any]) -> None:
        """Host side: client confirmed handshake."""
        client_name = payload.get("player_name", "Opponent")
        if self._local_player_color == Color.WHITE:
            self._black_player = Player(client_name, Color.BLACK, PlayerType.HUMAN)
        else:
            self._white_player = Player(client_name, Color.WHITE, PlayerType.HUMAN)

        self._game.white_player = self._white_player
        self._game.black_player = self._black_player
        state = self.get_state()
        self.state_changed.emit(state)
        self.lan_peer_joined.emit(client_name)

        tc = self._clock.time_control
        if tc and not tc.is_unlimited and not self._clock.is_running:
            self._clock.start(Color.WHITE)

    def _handle_lan_move(self, payload: dict[str, Any]) -> None:
        """Apply move received from remote opponent."""
        uci_move = payload.get("uci")
        if not uci_move:
            return

        w_time = payload.get("white_time_ms")
        b_time = payload.get("black_time_ms")
        if w_time is not None and b_time is not None:
            self._clock.set_times(w_time, b_time)

        try:
            record = MoveService.execute_uci(self._board, uci_move)
        except Exception as e:
            logger.error("Failed to execute remote LAN move '%s': %s", uci_move, e)
            return

        record = dataclasses.replace(
            record,
            white_time_ms=self._clock.white_time_ms,
            black_time_ms=self._clock.black_time_ms,
        )
        self._moves.append(record)
        self._last_move = (record.from_square, record.to_square)
        self._review_ply = None
        self._review_board = None

        new_state = MoveService.build_game_state(
            self._board,
            self._last_move,
            self._moves,
            white_time_ms=self._clock.white_time_ms,
            black_time_ms=self._clock.black_time_ms,
            time_control=self._clock.time_control,
        )
        self._game.state = new_state

        logger.info("Remote LAN move executed: %s (%s)", record.san, uci_move)
        self.move_made.emit(record)
        self.state_changed.emit(new_state)

        if new_state.status.is_game_over:
            self._clock.stop()
            self.game_over.emit(new_state.status, new_state.status_message or "Game over")
        else:
            self._clock.switch_turn(new_state.turn)

    def _handle_lan_sync_request(self) -> None:
        """Send current move history and clocks for client reconnection realignment."""
        if self._lan_transport is not None:
            msg = NetworkMessage.sync_state(
                moves_uci=[m.uci for m in self._moves],
                white_time_ms=self._clock.white_time_ms,
                black_time_ms=self._clock.black_time_ms,
            )
            self._lan_transport.send_message(msg)

    def _handle_lan_sync_state(self, payload: dict[str, Any]) -> None:
        """Replay move history from host on reconnection."""
        moves_uci: list[str] = payload.get("moves_uci", [])
        w_time = payload.get("white_time_ms")
        b_time = payload.get("black_time_ms")
        if w_time is not None and b_time is not None:
            self._clock.set_times(w_time, b_time)

        self._board.reset()
        self._moves.clear()
        for uci in moves_uci:
            rec = MoveService.execute_uci(self._board, uci)
            self._moves.append(rec)

        self._last_move = (
            (self._moves[-1].from_square, self._moves[-1].to_square) if self._moves else None
        )
        self._review_ply = None
        self._review_board = None

        new_state = MoveService.build_game_state(
            self._board,
            self._last_move,
            self._moves,
            white_time_ms=self._clock.white_time_ms,
            black_time_ms=self._clock.black_time_ms,
            time_control=self._clock.time_control,
        )
        self._game.state = new_state
        self.review_changed.emit(None)
        self.state_changed.emit(new_state)

    def send_lan_draw_offer(self) -> None:
        """Transmit draw offer to peer over LAN."""
        if self._is_lan_game and self._lan_transport is not None:
            self._lan_transport.send_message(NetworkMessage.draw_offer())

    def send_lan_draw_response(self, accept: bool) -> None:
        """Transmit draw response to peer over LAN."""
        if self._is_lan_game and self._lan_transport is not None:
            self._lan_transport.send_message(NetworkMessage.draw_response(accept))
            if accept:
                self.accept_draw()

    def get_game(self) -> Game:
        """Return the current Game aggregate with latest state."""
        self._game.state = self.get_state()
        return self._game

    def load_game(self, game: Game) -> None:
        """Load an existing game aggregate into the service."""
        self.clear_hint()
        self.disconnect_lan()
        self.cancel_engine_search()
        self._game = game
        self._white_player = game.white_player
        self._black_player = game.black_player
        self._moves = list(game.state.moves)
        self._board = ChessBoard.create_at_ply([m.uci for m in self._moves], len(self._moves))
        self._last_move = (
            (self._moves[-1].from_square, self._moves[-1].to_square) if self._moves else None
        )
        self._review_ply = None
        self._review_board = None
        self._is_flipped = False

        tc = game.state.time_control or TimeControl.unlimited()
        self._clock.reset(tc, white_ms=game.state.white_time_ms, black_ms=game.state.black_time_ms)
        if not tc.is_unlimited and not game.state.status.is_game_over:
            self._clock.start(game.state.turn)

        logger.info(
            "Game loaded: %s vs %s (%d moves) [%s]",
            game.white_player.name,
            game.black_player.name,
            len(self._moves),
            tc.name,
        )
        self.review_changed.emit(None)
        self.state_changed.emit(game.state)

        if self.is_vs_computer:
            self._trigger_engine_if_needed()

    def get_legal_moves_from(self, square: str) -> list[tuple[str, bool]]:
        """Return legal destination squares for piece on square."""
        return MoveService.get_legal_moves_from(self.display_board, square)

    def is_promotion(self, from_square: str, to_square: str) -> bool:
        """Check if move requires pawn promotion."""
        return MoveService.is_promotion(self.display_board, from_square, to_square)

    def try_move(
        self,
        from_square: str,
        to_square: str,
        promotion: PieceType | None = None,
    ) -> bool:
        """Attempt to execute a move on the live board. Returns True if successful."""
        if self.is_reviewing:
            return False

        if self._is_engine_thinking:
            return False

        state = self.get_state()

        # In LAN games, ensure player only moves on their assigned turn
        if self._is_lan_game and state.turn != self._local_player_color:
            return False

        # In vs Computer games, reject manual moves during computer turn
        if not self._is_lan_game:
            current_player = self._white_player if state.turn == Color.WHITE else self._black_player
            if current_player.player_type == PlayerType.COMPUTER:
                return False

        if MoveService.is_promotion(self._board, from_square, to_square) and promotion is None:
            self.promotion_requested.emit(from_square, to_square)
            return False

        try:
            record = MoveService.execute_move(
                self._board, from_square, to_square, promotion=promotion
            )
        except ValueError as e:
            logger.warning("Attempted illegal move %s->%s: %s", from_square, to_square, e)
            return False

        record = dataclasses.replace(
            record,
            white_time_ms=self._clock.white_time_ms,
            black_time_ms=self._clock.black_time_ms,
        )
        self._moves.append(record)
        self._last_move = (from_square, to_square)
        self._review_ply = None
        self._review_board = None
        self.clear_hint()

        new_state = MoveService.build_game_state(
            self._board,
            self._last_move,
            self._moves,
            white_time_ms=self._clock.white_time_ms,
            black_time_ms=self._clock.black_time_ms,
            time_control=self._clock.time_control,
        )
        self._game.state = new_state

        logger.info("Move played: %s (FEN: %s)", record.san, new_state.fen)
        self.move_made.emit(record)
        self.state_changed.emit(new_state)

        # Transmit move over LAN if multiplayer
        if self._is_lan_game and self._lan_transport is not None:
            self._lan_transport.send_message(
                NetworkMessage.move(
                    record.uci,
                    self._clock.white_time_ms,
                    self._clock.black_time_ms,
                )
            )

        if new_state.status.is_game_over:
            self._clock.stop()
            logger.info("Game over: %s (%s)", new_state.status, new_state.status_message)
            self.game_over.emit(new_state.status, new_state.status_message or "Game over")
        else:
            self._clock.switch_turn(new_state.turn)
            self._trigger_engine_if_needed()

        return True

    def _trigger_engine_if_needed(self) -> None:
        """Request move from engine if it is computer player's turn."""
        if self.is_reviewing or self._is_lan_game:
            return

        state = self.get_state()
        if state.status.is_game_over:
            return

        current_player = self._white_player if state.turn == Color.WHITE else self._black_player
        if current_player.player_type == PlayerType.COMPUTER:
            self.ensure_engine_worker()
            moves_uci = [m.uci for m in self._moves]
            self._request_move_signal.emit(state.fen, moves_uci, self._difficulty)

    def _on_engine_move(self, uci_move: str) -> None:
        """Execute move returned by engine worker."""
        if self.is_reviewing or self._is_lan_game:
            return

        state = self.get_state()
        if state.status.is_game_over:
            return

        current_player = self._white_player if state.turn == Color.WHITE else self._black_player
        if current_player.player_type != PlayerType.COMPUTER:
            return

        try:
            record = MoveService.execute_uci(self._board, uci_move)
        except Exception as e:
            logger.error("Failed to execute engine move '%s': %s", uci_move, e)
            return

        record = dataclasses.replace(
            record,
            white_time_ms=self._clock.white_time_ms,
            black_time_ms=self._clock.black_time_ms,
        )
        self._moves.append(record)
        self._last_move = (record.from_square, record.to_square)
        self._review_ply = None
        self._review_board = None

        new_state = MoveService.build_game_state(
            self._board,
            self._last_move,
            self._moves,
            white_time_ms=self._clock.white_time_ms,
            black_time_ms=self._clock.black_time_ms,
            time_control=self._clock.time_control,
        )
        self._game.state = new_state

        logger.info("Engine move played: %s (%s)", record.san, uci_move)
        self.move_made.emit(record)
        self.state_changed.emit(new_state)

        if new_state.status.is_game_over:
            self._clock.stop()
            logger.info("Game over: %s (%s)", new_state.status, new_state.status_message)
            self.game_over.emit(new_state.status, new_state.status_message or "Game over")
        else:
            self._clock.switch_turn(new_state.turn)

    def undo_move(self) -> bool:
        """Undo the last move, or last two moves if playing against Computer."""
        if not self.can_undo:
            return False

        self.clear_hint()
        self.cancel_engine_search()

        if self.is_reviewing:
            self.go_to_live()

        moves_to_undo = 1
        if self.is_vs_computer and len(self._moves) >= 2:
            state = self.get_state()
            current_player = self._white_player if state.turn == Color.WHITE else self._black_player
            if current_player.player_type == PlayerType.HUMAN:
                moves_to_undo = 2

        for _ in range(moves_to_undo):
            if not self._moves:
                break
            self._board.pop_move()
            self._moves.pop()

        self._last_move = (
            (self._moves[-1].from_square, self._moves[-1].to_square) if self._moves else None
        )
        self._review_ply = None
        self._review_board = None

        if self._moves:
            last_rec = self._moves[-1]
            next_turn = Color.WHITE if len(self._moves) % 2 == 0 else Color.BLACK
            self._clock.set_times_and_turn(last_rec.white_time_ms, last_rec.black_time_ms, next_turn)
        else:
            tc = self._clock.time_control
            if tc:
                self._clock.reset(tc)
                if not tc.is_unlimited:
                    self._clock.start(Color.WHITE)

        new_state = MoveService.build_game_state(
            self._board,
            self._last_move,
            self._moves,
            white_time_ms=self._clock.white_time_ms,
            black_time_ms=self._clock.black_time_ms,
            time_control=self._clock.time_control,
        )
        self._game.state = new_state

        logger.info("Undo executed. Moves remaining: %d", len(self._moves))
        self.review_changed.emit(None)
        self.state_changed.emit(new_state)

        return True

    def resign(self, player_color: Color) -> bool:
        """Handle resignation by player_color."""
        if self.get_state().status.is_game_over:
            return False

        # In LAN games, transmit resignation to peer if local player resigned
        if self._is_lan_game and player_color == self._local_player_color and self._lan_transport:
            self._lan_transport.send_message(NetworkMessage.resign())

        self.cancel_engine_search()
        self._clock.stop()
        winner_color = player_color.opposite
        winner_player = self._white_player if winner_color == Color.WHITE else self._black_player
        loser_player = self._white_player if player_color == Color.WHITE else self._black_player

        msg = f"{loser_player.name} ({player_color.value.capitalize()}) resigned. {winner_player.name} wins."
        state = MoveService.build_game_state(
            self._board,
            self._last_move,
            self._moves,
            review_ply=self._review_ply,
            status_override=GameStatus.RESIGNED,
            status_message_override=msg,
            white_time_ms=self._clock.white_time_ms,
            black_time_ms=self._clock.black_time_ms,
            time_control=self._clock.time_control,
        )
        self._game.state = state
        logger.info("Resignation: %s", msg)
        self.state_changed.emit(state)
        self.game_over.emit(GameStatus.RESIGNED, msg)
        return True

    def accept_draw(self) -> bool:
        """Handle mutual agreement to draw."""
        if self.get_state().status.is_game_over:
            return False

        self.cancel_engine_search()
        self._clock.stop()
        msg = "Game drawn by mutual agreement."
        state = MoveService.build_game_state(
            self._board,
            self._last_move,
            self._moves,
            review_ply=self._review_ply,
            status_override=GameStatus.DRAW_AGREED,
            status_message_override=msg,
            white_time_ms=self._clock.white_time_ms,
            black_time_ms=self._clock.black_time_ms,
            time_control=self._clock.time_control,
        )
        self._game.state = state
        logger.info("Draw agreed: %s", msg)
        self.state_changed.emit(state)
        self.game_over.emit(GameStatus.DRAW_AGREED, msg)
        return True

    # Navigation & Review Controls
    def navigate_to_ply(self, ply: int | None) -> None:
        """Navigate to a specific historical ply (0 to len(moves)), or None for live."""
        self.clear_hint()
        if ply is not None:
            ply = max(0, min(ply, len(self._moves)))
            if ply == len(self._moves):
                ply = None

        self._review_ply = ply

        if ply is None:
            self._review_board = None
            last_move = self._last_move
            state = MoveService.build_game_state(
                self._board,
                last_move,
                self._moves,
                white_time_ms=self._clock.white_time_ms,
                black_time_ms=self._clock.black_time_ms,
                time_control=self._clock.time_control,
            )
            if not state.status.is_game_over:
                self._clock.resume()
        else:
            self._clock.pause()
            uci_list = [m.uci for m in self._moves]
            self._review_board = ChessBoard.create_at_ply(uci_list, ply)
            if ply > 0:
                m = self._moves[ply - 1]
                last_move = (m.from_square, m.to_square)
            else:
                last_move = None
            state = MoveService.build_game_state(
                self._review_board,
                last_move,
                self._moves,
                review_ply=ply,
                white_time_ms=self._clock.white_time_ms,
                black_time_ms=self._clock.black_time_ms,
                time_control=self._clock.time_control,
            )

        self._game.state = state
        self.review_changed.emit(self._review_ply)
        self.state_changed.emit(state)

    def step_backward(self) -> None:
        target = (self.current_ply - 1) if self._review_ply is not None else (len(self._moves) - 1)
        if target >= 0:
            self.navigate_to_ply(target)

    def step_forward(self) -> None:
        if self._review_ply is not None:
            target = self._review_ply + 1
            if target <= len(self._moves):
                self.navigate_to_ply(target if target < len(self._moves) else None)

    def go_to_start(self) -> None:
        if len(self._moves) > 0:
            self.navigate_to_ply(0)

    def go_to_live(self) -> None:
        if self._review_ply is not None:
            self.navigate_to_ply(None)

    def branch_at_current_ply(
        self,
        from_square: str,
        to_square: str,
        promotion: PieceType | None = None,
    ) -> bool:
        """Truncate move history after reviewed ply and branch into a new variation."""
        if not self.is_reviewing:
            return self.try_move(from_square, to_square, promotion)

        if self._is_lan_game:
            return False

        target_ply = self._review_ply if self._review_ply is not None else len(self._moves)
        trunc_count = len(self._moves) - target_ply

        for _ in range(trunc_count):
            self._board.pop_move()
            self._moves.pop()

        self._last_move = (
            (self._moves[-1].from_square, self._moves[-1].to_square) if self._moves else None
        )
        self._review_ply = None
        self._review_board = None

        if self._moves:
            last_rec = self._moves[-1]
            self._clock.set_times(last_rec.white_time_ms, last_rec.black_time_ms)
        else:
            tc = self._clock.time_control
            if tc:
                self._clock.reset(tc)

        logger.info("Branched game at ply %d", target_ply)
        self.review_changed.emit(None)
        return self.try_move(from_square, to_square, promotion)

    def flip_board(self) -> None:
        """Toggle board orientation."""
        self._is_flipped = not self._is_flipped
        self.board_flipped.emit(self._is_flipped)

    def get_state(self) -> GameState:
        """Return current authoritative GameState."""
        current = self._game.state
        if (
            current.white_time_ms != self._clock.white_time_ms
            or current.black_time_ms != self._clock.black_time_ms
        ):
            self._game.state = dataclasses.replace(
                current,
                white_time_ms=self._clock.white_time_ms,
                black_time_ms=self._clock.black_time_ms,
                time_control=self._clock.time_control,
            )
        return self._game.state

    def cleanup(self) -> None:
        """Shut down engine worker, disconnect network, and clean up background resources."""
        self.disconnect_lan()
        self._clock.stop()
        if self._engine_worker is not None:
            self._engine_worker.stop_worker()
            self._engine_worker = None
