"""Game orchestration service managing game session and move lifecycle."""

import logging
from typing import Any

from PySide6.QtCore import QObject, Signal

from chess_desktop.chess.board import ChessBoard
from chess_desktop.chess.move_service import MoveService
from chess_desktop.domain.enums import Color, GameStatus, PieceType
from chess_desktop.domain.game import Game
from chess_desktop.domain.game_state import GameState, MoveRecord
from chess_desktop.domain.player import Player

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

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._board = ChessBoard()
        self._moves: list[MoveRecord] = []
        self._last_move: tuple[str, str] | None = None
        self._is_flipped = False
        self._review_ply: int | None = None
        self._review_board: ChessBoard | None = None

        self._white_player = Player("White", Color.WHITE)
        self._black_player = Player("Black", Color.BLACK)
        self._game = Game(
            white_player=self._white_player,
            black_player=self._black_player,
            state=MoveService.build_game_state(self._board, None, []),
        )

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
        white_name: str = "White",
        black_name: str = "Black",
    ) -> None:
        """Reset and start a new game."""
        self._board.reset()
        self._moves.clear()
        self._last_move = None
        self._review_ply = None
        self._review_board = None
        self._white_player = Player(white_name, Color.WHITE)
        self._black_player = Player(black_name, Color.BLACK)

        state = MoveService.build_game_state(self._board, None, [])
        self._game = Game(
            white_player=self._white_player,
            black_player=self._black_player,
            state=state,
        )

        logger.info("New game started: %s vs %s", white_name, black_name)
        self.review_changed.emit(None)
        self.state_changed.emit(state)

    def get_game(self) -> Game:
        """Return the current Game aggregate with latest state."""
        self._game.state = self.get_state()
        return self._game

    def load_game(self, game: Game) -> None:
        """Load an existing game aggregate into the service."""
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

        logger.info(
            "Game loaded: %s vs %s (%d moves)",
            game.white_player.name,
            game.black_player.name,
            len(self._moves),
        )
        self.review_changed.emit(None)
        self.state_changed.emit(game.state)

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
        # If in review mode, do not execute move directly on live board without branching
        if self.is_reviewing:
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

        self._moves.append(record)
        self._last_move = (from_square, to_square)
        self._review_ply = None
        self._review_board = None

        state = MoveService.build_game_state(self._board, self._last_move, self._moves)
        self._game.state = state

        logger.info("Move played: %s (FEN: %s)", record.san, state.fen)
        self.move_made.emit(record)
        self.state_changed.emit(state)

        if state.status.is_game_over:
            logger.info("Game over: %s (%s)", state.status, state.status_message)
            self.game_over.emit(state.status, state.status_message or "Game over")

        return True

    def undo_move(self) -> bool:
        """Undo the last half-move (ply). In local mode, reverts 1 ply."""
        if not self.can_undo:
            return False

        # If currently reviewing, jump back to live before undoing
        if self.is_reviewing:
            self.go_to_live()

        self._board.pop_move()
        self._moves.pop()

        if self._moves:
            last = self._moves[-1]
            self._last_move = (last.from_square, last.to_square)
        else:
            self._last_move = None

        self._review_ply = None
        self._review_board = None

        state = MoveService.build_game_state(self._board, self._last_move, self._moves)
        self._game.state = state

        logger.info("Move undone. Current turn: %s", state.turn)
        self.state_changed.emit(state)
        return True

    def resign(self, color: Color | None = None) -> bool:
        """Resign game on behalf of the specified color (or current turn)."""
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
        )
        self._game.state = state
        logger.info("Resignation: %s", msg)
        self.state_changed.emit(state)
        self.game_over.emit(GameStatus.RESIGNED, msg)
        return True

    def accept_draw(self) -> bool:
        """Accept draw offer and terminate game by mutual agreement."""
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
            state = MoveService.build_game_state(self._board, last_move, self._moves)
        else:
            uci_list = [m.uci for m in self._moves]
            self._review_board = ChessBoard.create_at_ply(uci_list, ply)
            if ply > 0:
                m = self._moves[ply - 1]
                last_move = (m.from_square, m.to_square)
            else:
                last_move = None
            state = MoveService.build_game_state(
                self._review_board, last_move, self._moves, review_ply=ply
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
        return self._game.state
