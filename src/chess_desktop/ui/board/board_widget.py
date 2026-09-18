"""64-square vector chessboard widget with SVG piece rendering and dual interaction."""

import chess
from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QRadialGradient,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QWidget

import chess_desktop.ui.resources_rc  # noqa: F401 - registers Qt resources
from chess_desktop.domain.enums import Color, PieceType
from chess_desktop.domain.game_state import GameState
from chess_desktop.services.game_service import GameService
from chess_desktop.ui.dialogs.confirm_dialog import ConfirmDialog


class BoardWidget(QWidget):
    """Interactive chessboard widget."""

    LIGHT_SQUARE = QColor("#eeeed2")
    DARK_SQUARE = QColor("#769656")
    SELECTED_COLOR = QColor(247, 247, 105, 180)
    LAST_MOVE_COLOR = QColor(186, 202, 68, 160)
    LEGAL_DOT_COLOR = QColor(20, 20, 20, 70)
    CHECK_COLOR = QColor(230, 57, 70, 190)

    def __init__(self, game_service: GameService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = game_service
        self.setMinimumSize(360, 360)
        self.setMouseTracking(True)

        # Selection and interaction state
        self._selected_square: str | None = None
        self._legal_targets: dict[str, bool] = {}  # target_square -> is_capture

        # Drag and drop state
        self._is_dragging: bool = False
        self._drag_start_pos: QPoint | None = None
        self._drag_current_pos: QPoint | None = None
        self._drag_square: str | None = None

        # Load SVG renderers for all 12 pieces
        self._renderers: dict[tuple[PieceType, Color], QSvgRenderer] = {}
        self._load_piece_renderers()

        # Connect service signals
        self._service.state_changed.connect(self._on_state_changed)
        self._service.board_flipped.connect(self._on_board_flipped)
        self._service.review_changed.connect(lambda _: self.update())

    def _load_piece_renderers(self) -> None:
        pieces = [
            (PieceType.PAWN, "P"),
            (PieceType.KNIGHT, "N"),
            (PieceType.BISHOP, "B"),
            (PieceType.ROOK, "R"),
            (PieceType.QUEEN, "Q"),
            (PieceType.KING, "K"),
        ]
        for pt, code in pieces:
            self._renderers[(pt, Color.WHITE)] = QSvgRenderer(f":/pieces/w{code}.svg")
            self._renderers[(pt, Color.BLACK)] = QSvgRenderer(f":/pieces/b{code}.svg")

    def _on_state_changed(self, state: GameState) -> None:
        self._selected_square = None
        self._legal_targets.clear()
        self._is_dragging = False
        self.update()

    def _on_board_flipped(self, is_flipped: bool) -> None:
        self.update()

    # Geometry & Coordinate helpers
    def _board_rect(self) -> tuple[float, float, float]:
        """Return (offset_x, offset_y, square_size) for current widget dimensions."""
        size = min(self.width(), self.height())
        sq_size = size / 8.0
        offset_x = (self.width() - size) / 2.0
        offset_y = (self.height() - size) / 2.0
        return offset_x, offset_y, sq_size

    def _square_at_pos(self, pos: QPoint) -> str | None:
        """Convert pixel position to algebraic square (e.g. 'e4') or None if off-board."""
        offset_x, offset_y, sq_size = self._board_rect()
        x = pos.x() - offset_x
        y = pos.y() - offset_y

        if x < 0 or y < 0 or x >= sq_size * 8 or y >= sq_size * 8:
            return None

        col = int(x // sq_size)
        row = int(y // sq_size)

        if self._service.is_flipped:
            file_idx = 7 - col
            rank_idx = row
        else:
            file_idx = col
            rank_idx = 7 - row

        return chess.square_name(chess.square(file_idx, rank_idx))

    def _square_rect(self, square_name: str) -> QRectF:
        """Return bounding QRectF for given square name."""
        offset_x, offset_y, sq_size = self._board_rect()
        sq = chess.parse_square(square_name)
        file_idx = chess.square_file(sq)
        rank_idx = chess.square_rank(sq)

        if self._service.is_flipped:
            col = 7 - file_idx
            row = rank_idx
        else:
            col = file_idx
            row = 7 - rank_idx

        return QRectF(offset_x + col * sq_size, offset_y + row * sq_size, sq_size, sq_size)

    # Mouse Event Handlers
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        click_pos = event.position().toPoint()
        clicked_sq = self._square_at_pos(click_pos)
        if not clicked_sq:
            self._selected_square = None
            self._legal_targets.clear()
            self.update()
            return

        piece_info = self._service.display_board.piece_at(clicked_sq)
        current_turn = self._service.get_state().turn

        # If clicking an already selected square's legal target -> execute move
        if self._selected_square and clicked_sq in self._legal_targets:
            from_sq = self._selected_square
            self._selected_square = None
            self._legal_targets.clear()
            self._handle_move_attempt(from_sq, clicked_sq)
            self.update()
            return

        # If clicking friendly piece -> select and prepare potential drag
        if piece_info and piece_info[1] == current_turn:
            self._selected_square = clicked_sq
            legal = self._service.get_legal_moves_from(clicked_sq)
            self._legal_targets = dict(legal)
            self._drag_start_pos = click_pos
            self._drag_square = clicked_sq
            self._is_dragging = False
            self.update()
            return

        # Clicked empty square or opponent piece (not a legal target) -> clear selection
        self._selected_square = None
        self._legal_targets.clear()
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not (event.buttons() & Qt.MouseButton.LeftButton) or not self._drag_start_pos:
            super().mouseMoveEvent(event)
            return

        current_pos = event.position().toPoint()
        distance = (current_pos - self._drag_start_pos).manhattanLength()
        if distance > QApplication.startDragDistance() and self._drag_square:
            self._is_dragging = True
            self._drag_current_pos = current_pos
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mouseReleaseEvent(event)
            return

        release_pos = event.position().toPoint()
        if self._is_dragging and self._drag_square:
            target_sq = self._square_at_pos(release_pos)
            if target_sq and target_sq in self._legal_targets:
                from_sq = self._drag_square
                self._selected_square = None
                self._legal_targets.clear()
                self._handle_move_attempt(from_sq, target_sq)

            self._is_dragging = False
            self._drag_start_pos = None
            self._drag_current_pos = None
            self._drag_square = None
            self.update()
            return

        self._is_dragging = False
        self._drag_start_pos = None
        self._drag_current_pos = None
        self._drag_square = None

    def _handle_move_attempt(self, from_sq: str, to_sq: str) -> None:
        """Handle move attempt, prompting for branching confirmation if in review mode."""
        if self._service.is_reviewing:
            dlg = ConfirmDialog(
                title="Create Move Branch?",
                message=(
                    "Playing a move from this historical position will truncate all "
                    "subsequent moves and start a new game line.\n\nContinue?"
                ),
                confirm_text="Branch & Play",
                cancel_text="Cancel",
                is_destructive=True,
                parent=self,
            )
            if dlg.exec():
                self._service.branch_at_current_ply(from_sq, to_sq)
        else:
            self._service.try_move(from_sq, to_sq)

    # Paint Event
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        offset_x, offset_y, sq_size = self._board_rect()
        state = self._service.get_state()

        # 1. Draw 64 squares
        for row in range(8):
            for col in range(8):
                is_light = (row + col) % 2 == 0
                color = self.LIGHT_SQUARE if is_light else self.DARK_SQUARE
                rect = QRectF(offset_x + col * sq_size, offset_y + row * sq_size, sq_size, sq_size)
                painter.fillRect(rect, color)

        # 2. Draw Rank and File labels
        font = QFont("sans-serif", int(sq_size * 0.16), QFont.Weight.Bold)
        painter.setFont(font)
        for i in range(8):
            # Files (bottom edge)
            file_char = chr(ord("h") - i) if self._service.is_flipped else chr(ord("a") + i)
            file_rect = QRectF(
                offset_x + i * sq_size + sq_size * 0.72,
                offset_y + 7 * sq_size + sq_size * 0.72,
                sq_size * 0.25,
                sq_size * 0.25,
            )
            is_light_bottom = (7 + i) % 2 == 0
            painter.setPen(self.DARK_SQUARE if is_light_bottom else self.LIGHT_SQUARE)
            painter.drawText(file_rect, Qt.AlignmentFlag.AlignCenter, file_char)

            # Ranks (left edge)
            rank_char = str(i + 1) if self._service.is_flipped else str(8 - i)
            rank_rect = QRectF(
                offset_x + sq_size * 0.04,
                offset_y + i * sq_size + sq_size * 0.04,
                sq_size * 0.25,
                sq_size * 0.25,
            )
            is_light_left = (i + 0) % 2 == 0
            painter.setPen(self.DARK_SQUARE if is_light_left else self.LIGHT_SQUARE)
            painter.drawText(
                rank_rect, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, rank_char
            )

        # 3. Draw Highlights
        # Last move highlight
        if state.last_move:
            from_sq, to_sq = state.last_move
            painter.fillRect(self._square_rect(from_sq), self.LAST_MOVE_COLOR)
            painter.fillRect(self._square_rect(to_sq), self.LAST_MOVE_COLOR)

        # Check highlight
        if state.in_check and state.check_square:
            k_rect = self._square_rect(state.check_square)
            grad = QRadialGradient(k_rect.center(), sq_size * 0.5)
            grad.setColorAt(0.0, self.CHECK_COLOR)
            grad.setColorAt(1.0, QColor(230, 57, 70, 0))
            painter.fillRect(k_rect, grad)

        # Selected square highlight
        if self._selected_square:
            painter.fillRect(self._square_rect(self._selected_square), self.SELECTED_COLOR)

        # Legal destination indicators
        for target_sq, is_capture in self._legal_targets.items():
            t_rect = self._square_rect(target_sq)
            if is_capture:
                # Capture indicator: hollow ring
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(self.LEGAL_DOT_COLOR)
                ring_thickness = sq_size * 0.09
                radius = sq_size * 0.44
                painter.drawEllipse(t_rect.center(), radius, radius)
                # Clear inner area to form ring
                inner_color = (
                    self.LIGHT_SQUARE
                    if (int(t_rect.x() // sq_size) + int(t_rect.y() // sq_size)) % 2 == 0
                    else self.DARK_SQUARE
                )
                painter.setBrush(inner_color)
                painter.drawEllipse(
                    t_rect.center(), radius - ring_thickness, radius - ring_thickness
                )
            else:
                # Quiet move indicator: small center dot
                dot_radius = sq_size * 0.15
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(self.LEGAL_DOT_COLOR)
                painter.drawEllipse(t_rect.center(), dot_radius, dot_radius)

        # 4. Draw Stationary Pieces
        for sq in chess.SQUARES:
            sq_name = chess.square_name(sq)
            piece_info = self._service.display_board.piece_at(sq_name)
            if not piece_info:
                continue

            rect = self._square_rect(sq_name)
            renderer = self._renderers.get(piece_info)
            if not renderer:
                continue

            # If dragging this piece, draw as semi-transparent ghost at origin
            if self._is_dragging and sq_name == self._drag_square:
                painter.setOpacity(0.35)
                renderer.render(painter, rect)
                painter.setOpacity(1.0)
            else:
                renderer.render(painter, rect)

        # 5. Draw Dragged Piece under Cursor
        if self._is_dragging and self._drag_square and self._drag_current_pos:
            drag_piece = self._service.display_board.piece_at(self._drag_square)
            if drag_piece:
                renderer = self._renderers.get(drag_piece)
                if renderer:
                    drag_size = sq_size * 1.08
                    drag_rect = QRectF(
                        self._drag_current_pos.x() - drag_size / 2.0,
                        self._drag_current_pos.y() - drag_size / 2.0,
                        drag_size,
                        drag_size,
                    )
                    # Draw subtle drop shadow
                    shadow_rect = drag_rect.translated(2.0, 4.0)
                    painter.setBrush(QColor(0, 0, 0, 60))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(shadow_rect.center(), drag_size * 0.38, drag_size * 0.38)

                    # Draw floating piece
                    renderer.render(painter, drag_rect)

        painter.end()
