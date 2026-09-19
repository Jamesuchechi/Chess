"""64-square vector chessboard widget with SVG piece rendering, smooth animations, and dual interaction."""

import math
from typing import Any

import chess
from PySide6.QtCore import QEasingCurve, QPoint, QPointF, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import (
    QColor,
    QFont,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
    QRadialGradient,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QWidget

import chess_desktop.ui.resources_rc  # noqa: F401 - registers Qt resources
from chess_desktop.domain.enums import Color, PieceType
from chess_desktop.domain.game_state import GameState, MoveRecord
from chess_desktop.domain.theme import BoardTheme
from chess_desktop.services.game_service import GameService
from chess_desktop.ui.dialogs.confirm_dialog import ConfirmDialog


class BoardWidget(QWidget):
    """Interactive chessboard widget with smooth movement animations and drag-and-drop."""

    LIGHT_SQUARE = QColor("#eeeed2")
    DARK_SQUARE = QColor("#769656")
    SELECTED_COLOR = QColor(247, 247, 105, 180)
    LAST_MOVE_COLOR = QColor(186, 202, 68, 160)
    LEGAL_DOT_COLOR = QColor(20, 20, 20, 70)
    CHECK_COLOR = QColor(230, 57, 70, 190)

    def __init__(self, game_service: GameService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = game_service
        self._theme = BoardTheme.classic()
        self.setMinimumSize(360, 360)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Selection, keyboard cursor, and interaction state
        self._selected_square: str | None = None
        self._cursor_square: str | None = "e2"
        self._hint_move: tuple[str, str] | None = None
        self._legal_targets: dict[str, bool] = {}  # target_square -> is_capture

        # Drag and drop state
        self._is_dragging: bool = False
        self._drag_start_pos: QPoint | None = None
        self._drag_current_pos: QPoint | None = None
        self._drag_square: str | None = None
        self._skip_next_animation: bool = False

        # Active move animations (dict list: {anim, piece, to_sq, current_pos})
        self._animations: list[dict[str, Any]] = []

        # Snap-back animation state for illegal drops
        self._snapback_anim: QVariantAnimation | None = None
        self._snapback_piece: tuple[PieceType, Color] | None = None
        self._snapback_pos: QPointF | None = None

        # Load SVG renderers for all 12 pieces
        self._renderers: dict[tuple[PieceType, Color], QSvgRenderer] = {}
        self._load_piece_renderers()

        # Connect service signals
        self._service.state_changed.connect(self._on_state_changed)
        self._service.board_flipped.connect(self._on_board_flipped)
        self._service.review_changed.connect(self._on_review_changed)
        self._service.engine_thinking_changed.connect(self._on_engine_thinking_changed)
        self._service.move_made.connect(self._on_move_made)
        self._service.hint_received.connect(self._on_hint_received)
        self._service.hint_cleared.connect(self._on_hint_cleared)

    @property
    def theme(self) -> BoardTheme:
        """Active board color theme."""
        return self._theme

    def set_theme(self, theme: BoardTheme) -> None:
        """Change board theme and trigger repaint."""
        self._theme = theme
        self.update()

    def focusInEvent(self, event: Any) -> None:
        super().focusInEvent(event)
        self.update()

    def focusOutEvent(self, event: Any) -> None:
        super().focusOutEvent(event)
        self.update()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle keyboard accessibility navigation, piece selection, and actions."""
        key = event.key()

        # Arrow keys: Navigate focused square on board grid
        if key in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            if not self._cursor_square:
                self._cursor_square = "e2" if not self._service.is_flipped else "e7"

            sq_idx = chess.parse_square(self._cursor_square)
            file_idx = chess.square_file(sq_idx)
            rank_idx = chess.square_rank(sq_idx)

            flipped = self._service.is_flipped
            if key == Qt.Key.Key_Left:
                file_idx = max(0, min(7, file_idx + (1 if flipped else -1)))
            elif key == Qt.Key.Key_Right:
                file_idx = max(0, min(7, file_idx + (-1 if flipped else 1)))
            elif key == Qt.Key.Key_Up:
                rank_idx = max(0, min(7, rank_idx + (-1 if flipped else 1)))
            elif key == Qt.Key.Key_Down:
                rank_idx = max(0, min(7, rank_idx + (1 if flipped else -1)))

            self._cursor_square = chess.square_name(chess.square(file_idx, rank_idx))
            self.update()
            return

        # Space or Enter: Select piece on cursor square or execute move
        if key in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if not self._cursor_square:
                self._cursor_square = "e2" if not self._service.is_flipped else "e7"

            target_sq = self._cursor_square
            if self._selected_square is None:
                piece = self._service.display_board.piece_at(target_sq)
                if piece:
                    self._selected_square = target_sq
                    targets = self._service.get_legal_moves_from(target_sq)
                    self._legal_targets = dict(targets)
                    self.update()
            else:
                if target_sq == self._selected_square:
                    self.clear_selection()
                else:
                    moved = self._service.try_move(self._selected_square, target_sq)
                    if not moved:
                        piece = self._service.display_board.piece_at(target_sq)
                        if piece:
                            self._selected_square = target_sq
                            targets = self._service.get_legal_moves_from(target_sq)
                            self._legal_targets = dict(targets)
                        else:
                            self.clear_selection()
                    else:
                        self.clear_selection()
            return

        if key == Qt.Key.Key_Escape:
            self.clear_selection()
            self._service.clear_hint()
            return

        if key == Qt.Key.Key_H:
            self._service.request_hint()
            return

        if key == Qt.Key.Key_F:
            self._service.flip_board()
            return

        if key == Qt.Key.Key_Z and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self._service.undo_move()
            return

        super().keyPressEvent(event)

    def _on_hint_received(self, from_sq: str, to_sq: str, san: str) -> None:
        self._hint_move = (from_sq, to_sq)
        self.update()

    def _on_hint_cleared(self) -> None:
        self._hint_move = None
        self.update()

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
        self._skip_next_animation = False
        self.update()

    def _on_review_changed(self, ply: int | None) -> None:
        self._clear_animations()
        self.update()

    def _on_board_flipped(self, is_flipped: bool) -> None:
        self._clear_animations()
        self.update()

    def _on_engine_thinking_changed(self, is_thinking: bool) -> None:
        if is_thinking:
            self.clear_selection()
            self.setCursor(Qt.CursorShape.WaitCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()

    def _clear_animations(self) -> None:
        """Cancel and clean up all active animations."""
        for item in self._animations:
            anim: QVariantAnimation = item["anim"]
            try:
                anim.stop()
            except Exception:
                pass
        self._animations.clear()

        if self._snapback_anim is not None:
            try:
                self._snapback_anim.stop()
            except Exception:
                pass
            self._snapback_anim = None
            self._snapback_piece = None
            self._snapback_pos = None

    def _on_move_made(self, record: MoveRecord) -> None:
        """Animate piece movement smoothly between squares."""
        skip_primary = self._skip_next_animation
        self._skip_next_animation = False

        if not self.isVisible() or self.width() < 100 or self.height() < 100:
            self.update()
            return

        # Determine piece at destination square
        piece_info = self._service.display_board.piece_at(record.to_square)
        if not piece_info:
            self.update()
            return

        # Handle castling (both King and Rook animate, or just Rook if King was directly dragged)
        if record.san in ("O-O", "O-O-O") or record.uci in ("e1g1", "e1c1", "e8g8", "e8c8"):
            if not skip_primary:
                # Animate King
                self._start_piece_animation(record.from_square, record.to_square, piece_info)
            # Animate corresponding Rook
            rook_color = piece_info[1]
            if record.uci in ("e1g1", "e8g8") or record.san == "O-O":
                # Kingside castle: h1->f1 (White) or h8->f8 (Black)
                r_from = "h1" if rook_color == Color.WHITE else "h8"
                r_to = "f1" if rook_color == Color.WHITE else "f8"
            else:
                # Queenside castle: a1->d1 (White) or a8->d8 (Black)
                r_from = "a1" if rook_color == Color.WHITE else "a8"
                r_to = "d1" if rook_color == Color.WHITE else "d8"

            rook_piece = (PieceType.ROOK, rook_color)
            self._start_piece_animation(r_from, r_to, rook_piece)
        else:
            if not skip_primary:
                self._start_piece_animation(record.from_square, record.to_square, piece_info)
            else:
                self.update()

    def _start_piece_animation(
        self,
        from_sq: str,
        to_sq: str,
        piece: tuple[PieceType, Color],
    ) -> None:
        """Launch a smooth coordinate interpolation animation for a piece."""
        from_center = self._square_rect(from_sq).center()
        to_center = self._square_rect(to_sq).center()

        anim_entry: dict[str, Any] = {
            "anim": None,
            "piece": piece,
            "to_sq": to_sq,
            "current_pos": QPointF(from_center),
        }

        anim = QVariantAnimation(self)
        anim.setDuration(160)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        anim.setStartValue(QPointF(from_center))
        anim.setEndValue(QPointF(to_center))

        def on_value_changed(value: QPointF) -> None:
            anim_entry["current_pos"] = value
            self.update()

        def on_finished() -> None:
            if anim_entry in self._animations:
                self._animations.remove(anim_entry)
            self.update()

        anim.valueChanged.connect(on_value_changed)
        anim.finished.connect(on_finished)
        anim_entry["anim"] = anim

        self._animations.append(anim_entry)
        anim.start()

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

        # Disable interaction when engine is calculating or game has ended
        if self._service.is_computer_thinking or self._service.get_state().status.is_game_over:
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

        if self._service.is_computer_thinking or self._service.get_state().status.is_game_over:
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

        if self._service.is_computer_thinking or self._service.get_state().status.is_game_over:
            self._is_dragging = False
            self._drag_start_pos = None
            self._drag_current_pos = None
            self._drag_square = None
            return

        release_pos = event.position().toPoint()
        if self._is_dragging and self._drag_square:
            target_sq = self._square_at_pos(release_pos)
            if target_sq and target_sq in self._legal_targets:
                from_sq = self._drag_square
                self._selected_square = None
                self._legal_targets.clear()
                self._is_dragging = False
                self._drag_start_pos = None
                self._drag_current_pos = None
                self._drag_square = None
                self._skip_next_animation = True
                self._handle_move_attempt(from_sq, target_sq)
                self.update()
                return

            # Illegal drop: launch smooth snap-back animation
            drag_piece = self._service.display_board.piece_at(self._drag_square)
            if drag_piece:
                target_center = self._square_rect(self._drag_square).center()
                self._snapback_piece = drag_piece
                self._snapback_pos = QPointF(release_pos)

                snap_anim = QVariantAnimation(self)
                snap_anim.setDuration(140)
                snap_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
                snap_anim.setStartValue(QPointF(release_pos))
                snap_anim.setEndValue(QPointF(target_center))

                def on_snap_changed(pos: QPointF) -> None:
                    self._snapback_pos = pos
                    self.update()

                def on_snap_finished() -> None:
                    self._snapback_anim = None
                    self._snapback_piece = None
                    self._snapback_pos = None
                    self.update()

                snap_anim.valueChanged.connect(on_snap_changed)
                snap_anim.finished.connect(on_snap_finished)
                self._snapback_anim = snap_anim
                snap_anim.start()

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

    def clear_selection(self) -> None:
        """Clear currently selected square and legal targets."""
        self._selected_square = None
        self._legal_targets.clear()
        self._is_dragging = False
        self._drag_square = None
        self._drag_start_pos = None
        self.update()

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
        light_sq = QColor(self._theme.light_square)
        dark_sq = QColor(self._theme.dark_square)

        # 1. Draw 64 squares
        for row in range(8):
            for col in range(8):
                is_light = (row + col) % 2 == 0
                color = light_sq if is_light else dark_sq
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
            painter.setPen(dark_sq if is_light_bottom else light_sq)
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
            painter.setPen(dark_sq if is_light_left else light_sq)
            painter.drawText(
                rank_rect, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, rank_char
            )

        # 3. Draw Highlights
        # Last move highlight
        if state.last_move:
            from_sq, to_sq = state.last_move
            painter.fillRect(self._square_rect(from_sq), self.LAST_MOVE_COLOR)
            painter.fillRect(self._square_rect(to_sq), self.LAST_MOVE_COLOR)

        # Hint move highlight
        if self._hint_move:
            from_sq, to_sq = self._hint_move
            painter.fillRect(self._square_rect(from_sq), QColor(6, 182, 212, 100))
            painter.fillRect(self._square_rect(to_sq), QColor(16, 185, 129, 130))

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
                    light_sq
                    if (int(t_rect.x() // sq_size) + int(t_rect.y() // sq_size)) % 2 == 0
                    else dark_sq
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

        # Build set of squares whose pieces are currently in flight/drag
        suppressed_squares: set[str] = {a["to_sq"] for a in self._animations}
        if self._is_dragging and self._drag_square:
            suppressed_squares.add(self._drag_square)

        # 4. Draw Stationary Pieces
        for sq in chess.SQUARES:
            sq_name = chess.square_name(sq)
            if sq_name in suppressed_squares:
                continue

            piece_info = self._service.display_board.piece_at(sq_name)
            if not piece_info:
                continue

            rect = self._square_rect(sq_name)
            renderer = self._renderers.get(piece_info)
            if not renderer:
                continue

            renderer.render(painter, rect)

        # 5. Draw Active Move Animations in Flight
        for anim_item in self._animations:
            piece = anim_item["piece"]
            renderer = self._renderers.get(piece)
            if renderer:
                pos: QPointF = anim_item["current_pos"]
                rect = QRectF(pos.x() - sq_size / 2.0, pos.y() - sq_size / 2.0, sq_size, sq_size)
                renderer.render(painter, rect)

        # 6. Draw Directional Hint Arrow (if active)
        if self._hint_move:
            self._draw_hint_arrow(painter, self._hint_move[0], self._hint_move[1])

        # 7. Draw Keyboard Accessibility Focus Cursor (if widget focused)
        if self.hasFocus() and self._cursor_square:
            self._draw_focus_cursor(painter, self._cursor_square)

        # 8. Draw Snap-back Piece
        if self._snapback_piece and self._snapback_pos:
            renderer = self._renderers.get(self._snapback_piece)
            if renderer:
                pos = self._snapback_pos
                rect = QRectF(pos.x() - sq_size / 2.0, pos.y() - sq_size / 2.0, sq_size, sq_size)
                renderer.render(painter, rect)

        # 9. Draw Dragged Piece under Cursor
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

    def _draw_hint_arrow(self, painter: QPainter, from_sq: str, to_sq: str) -> None:
        """Render a glowing modern directional arrow from from_sq to to_sq."""
        from_pt = self._square_rect(from_sq).center()
        to_pt = self._square_rect(to_sq).center()

        dx = to_pt.x() - from_pt.x()
        dy = to_pt.y() - from_pt.y()
        dist = math.hypot(dx, dy)
        if dist < 1.0:
            return

        angle = math.atan2(dy, dx)
        sq_size = self._board_rect()[2]
        head_len = sq_size * 0.36
        head_width = sq_size * 0.32
        shaft_width = sq_size * 0.14

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(6, 182, 212, 220), 1.5))
        painter.setBrush(QColor(6, 182, 212, 190))

        p_start = QPointF(
            from_pt.x() + math.cos(angle) * (sq_size * 0.15),
            from_pt.y() + math.sin(angle) * (sq_size * 0.15),
        )
        p_tip = QPointF(
            to_pt.x() - math.cos(angle) * (sq_size * 0.12),
            to_pt.y() - math.sin(angle) * (sq_size * 0.12),
        )
        p_base = QPointF(
            p_tip.x() - math.cos(angle) * head_len,
            p_tip.y() - math.sin(angle) * head_len,
        )

        px = -math.sin(angle)
        py = math.cos(angle)

        path = QPainterPath()
        path.moveTo(p_start.x() + px * (shaft_width / 2.0), p_start.y() + py * (shaft_width / 2.0))
        path.lineTo(p_base.x() + px * (shaft_width / 2.0), p_base.y() + py * (shaft_width / 2.0))
        path.lineTo(p_base.x() + px * (head_width / 2.0), p_base.y() + py * (head_width / 2.0))
        path.lineTo(p_tip.x(), p_tip.y())
        path.lineTo(p_base.x() - px * (head_width / 2.0), p_base.y() - py * (head_width / 2.0))
        path.lineTo(p_base.x() - px * (shaft_width / 2.0), p_base.y() - py * (shaft_width / 2.0))
        path.lineTo(p_start.x() - px * (shaft_width / 2.0), p_start.y() - py * (shaft_width / 2.0))
        path.closeSubpath()

        painter.drawPath(path)
        painter.restore()

    def _draw_focus_cursor(self, painter: QPainter, sq: str) -> None:
        """Render a high-contrast focus indicator around keyboard cursor square."""
        c_rect = self._square_rect(sq).adjusted(2.5, 2.5, -2.5, -2.5)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#38bdf8"), 3.0)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(c_rect, 4.0, 4.0)
        painter.restore()
