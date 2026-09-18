import dataclasses
import logging
from typing import Any

from PySide6.QtCore import QObject, Signal

from chess_desktop.chess.board import ChessBoard
from chess_desktop.chess.clock import ChessClock
from chess_desktop.chess.move_service import MoveService
from chess_desktop.domain.enums import Color, GameStatus, PieceType, PlayerType
from chess_desktop.domain.game import Game
from chess_desktop.domain.game_state import GameState, MoveRecord
from chess_desktop.domain.player import Player
from chess_desktop.domain.time_control import TimeControl
from chess_desktop.engine.difficulty import Difficulty
from chess_desktop.services.engine_worker import EngineWorker

logger = logging.getLogger(__name__)


class GameService(QObject):
    """Central orchestrator for active chess matches."""

    # Qt Signals
    state_changed = Signal(object)  # GameState
    move_made = Signal(object)  # MoveRecord
    game_over = Signal(object, str)  # (GameStatus, message)
    board_flipped = Signal(bool)  # is_flipped
    promotion_requested = Signal(str, str)  # (from_sq, to_sq)
    review_changed = Signal(object)  # int | None
    engine_thinking_changed = Signal(bool)  # is_thinking
    clock_ticked = Signal(int, int)  # (white_ms, black_ms)
    clock_timeout = Signal(object)  # (Color)

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
        self._engine_worker: EngineWorker | None = None
        if engine_worker is not None:
            self.set_engine_worker(engine_worker)

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
        return (
            self._white_player.player_type == PlayerType.COMPUTER
            or self._black_player.player_type == PlayerType.COMPUTER
        )

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
        self._engine_worker.best_move_found.connect(self._on_engine_move)
        self._engine_worker.search_started.connect(self._on_search_started)
        self._engine_worker.search_stopped.connect(self._on_search_stopped)
        self._engine_worker.start_worker()

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
        """True if a move can be undone."""
        return len(self._moves) > 0 and not self.get_state().status.is_game_over

    def new_game(
        self,
        white_name: str = "Player",
        black_name: str | None = None,
        white_type: PlayerType = PlayerType.HUMAN,
        black_type: PlayerType = PlayerType.COMPUTER,
        difficulty: Difficulty = Difficulty.INTERMEDIATE,
        time_control: TimeControl | None = None,
    ) -> None:
        """Reset and start a new game."""
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

    def get_game(self) -> Game:
        """Return the current Game aggregate with latest state."""
        self._game.state = self.get_state()
        return self._game

    def load_game(self, game: Game) -> None:
        """Load an existing game aggregate into the service."""
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

        # If current turn is computer, reject human manual move attempt
        state = self.get_state()
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
        if self.is_reviewing:
            return

        state = self.get_state()
        if state.status.is_game_over:
            return

        current_player = self._white_player if state.turn == Color.WHITE else self._black_player
        if current_player.player_type == PlayerType.COMPUTER:
            worker = self.ensure_engine_worker()
            moves_uci = [m.uci for m in self._moves]
            worker.request_move(state.fen, moves_uci, self._difficulty)

    def _on_engine_move(self, uci_move: str) -> None:
        """Execute move returned by engine worker."""
        if self.is_reviewing:
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
        """Undo the last half-move (or two plies when playing vs computer)."""
        if not self.can_undo:
            return False

        # Cancel any active search immediately
        self.cancel_engine_search()

        if self.is_reviewing:
            self.go_to_live()

        # When vs. computer:
        # If it is currently HUMAN turn, the computer just moved, so undo computer + human (2 moves).
        # If it is currently COMPUTER turn (cancelled search), undo 1 move (human's move).
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
            prev = self._moves[-1]
            if prev.white_time_ms is not None and prev.black_time_ms is not None:
                self._clock.set_times(prev.white_time_ms, prev.black_time_ms)
        else:
            self._clock.reset(self._clock.time_control)

        new_state = MoveService.build_game_state(
            self._board,
            self._last_move,
            self._moves,
            white_time_ms=self._clock.white_time_ms,
            black_time_ms=self._clock.black_time_ms,
            time_control=self._clock.time_control,
        )
        self._game.state = new_state

        logger.info("Move undone (%d plies reverted)", moves_to_undo)
        self.state_changed.emit(new_state)
        return True

    def resign(self, color: Color | None = None) -> bool:
        """Resign game on behalf of the specified color (or current turn)."""
        self.cancel_engine_search()
        self._clock.stop()
        if self.get_state().status.is_game_over:
            return False

        resigning = color or self.get_state().turn
        winner = resigning.opposite
        msg = f"{resigning.value.capitalize()} resigned. {winner.value.capitalize()} wins."

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
        """Accept draw offer and terminate game by mutual agreement."""
        self.cancel_engine_search()
        self._clock.stop()
        if self.get_state().status.is_game_over:
            return False

        msg = "Draw agreed by mutual consent."
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
        """Step one ply backward in history."""
        curr = self.current_ply
        if curr > 0:
            self.navigate_to_ply(curr - 1)

    def step_forward(self) -> None:
        """Step one ply forward towards live position."""
        if self._review_ply is not None:
            self.navigate_to_ply(self._review_ply + 1)

    def go_to_start(self) -> None:
        """Jump to position before move 1."""
        self.navigate_to_ply(0)

    def go_to_live(self) -> None:
        """Jump to the active live position."""
        self.navigate_to_ply(None)

    def branch_at_current_ply(
        self,
        from_square: str,
        to_square: str,
        promotion: PieceType | None = None,
    ) -> bool:
        """Truncate moves after current review ply and execute new move."""
        if self._review_ply is None:
            return self.try_move(from_square, to_square, promotion)

        target_ply = self._review_ply
        # Truncate moves
        self._moves = self._moves[:target_ply]
        # Rebuild live board up to truncated ply
        self._board = ChessBoard.create_at_ply([m.uci for m in self._moves], target_ply)
        self._review_ply = None
        self._review_board = None

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
        """Shut down engine worker and clean up background resources."""
        self._clock.stop()
        if self._engine_worker is not None:
            self._engine_worker.stop_worker()
            self._engine_worker = None
