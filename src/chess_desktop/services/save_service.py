"""Service orchestrating persistence, PGN import/export, and dirty tracking."""

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from chess_desktop.chess.pgn_service import PgnService
from chess_desktop.domain.game import Game
from chess_desktop.domain.game_state import GameState
from chess_desktop.persistence.database import DatabaseManager
from chess_desktop.persistence.repositories import GameRepository
from chess_desktop.services.game_service import GameService


class SaveService(QObject):
    """Coordinates saving, loading, PGN import/export, and dirty state."""

    game_saved = Signal(str)  # game_id
    game_loaded = Signal(Game)
    dirty_changed = Signal(bool)

    def __init__(
        self,
        game_service: GameService,
        repository: GameRepository | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._game_service = game_service
        if repository is None:
            db = DatabaseManager()
            self._repository = GameRepository(db)
        else:
            self._repository = repository

        self._current_game_id: str | None = None
        self._current_game_title: str | None = None
        self._is_dirty: bool = False

        self._game_service.state_changed.connect(self._on_state_changed)

    @property
    def has_unsaved_changes(self) -> bool:
        """True if the game has moves made since last save."""
        return self._is_dirty

    @property
    def current_game_id(self) -> str | None:
        """Active game's persistent ID, or None if never saved."""
        return self._current_game_id

    @property
    def current_game_title(self) -> str:
        """Title of the current game."""
        return self._current_game_title or ""

    @property
    def repository(self) -> GameRepository:
        """Access underlying repository."""
        return self._repository

    def _on_state_changed(self, state: GameState) -> None:
        if len(state.moves) > 0 and not self._is_dirty:
            self._is_dirty = True
            self.dirty_changed.emit(True)

    def mark_clean(self) -> None:
        """Reset dirty state."""
        if self._is_dirty:
            self._is_dirty = False
            self.dirty_changed.emit(False)

    def reset_tracking(self, new_title: str = "") -> None:
        """Reset tracking for a new game."""
        self._current_game_id = None
        self._current_game_title = new_title
        self._is_dirty = False
        self.dirty_changed.emit(False)

    def save(self) -> str | None:
        """Save using current title if set; otherwise return None to request Save As."""
        if self._current_game_title:
            return self.save_as(self._current_game_title)
        return None

    def save_as(self, title: str) -> str:
        """Save current game under specified title to SQLite."""
        game = self._game_service.get_game()
        pgn_text = PgnService.export_to_pgn(game)
        game_id = self._repository.save(game, title=title, pgn_text=pgn_text)

        self._current_game_id = game_id
        self._current_game_title = title
        self._is_dirty = False
        self.dirty_changed.emit(False)
        self.game_saved.emit(game_id)
        return game_id

    def load_game(self, game_id: str) -> bool:
        """Load game by ID into GameService."""
        result = self._repository.get_by_id(game_id)
        if result is None:
            return False

        game, record = result
        self._game_service.load_game(game)
        self._current_game_id = record.game_id
        self._current_game_title = record.title
        self._is_dirty = False
        self.dirty_changed.emit(False)
        self.game_loaded.emit(game)
        return True

    def export_pgn_file(self, file_path: str) -> None:
        """Export current game to a .pgn file."""
        game = self._game_service.get_game()
        pgn_text = PgnService.export_to_pgn(game)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(pgn_text)

    def import_pgn_file(self, file_path: str) -> bool:
        """Read and parse a .pgn file into GameService."""
        with open(file_path, encoding="utf-8") as f:
            pgn_text = f.read()

        game = PgnService.import_from_pgn(pgn_text)
        self._game_service.load_game(game)
        self._current_game_id = None
        self._current_game_title = Path(file_path).stem
        self._is_dirty = False
        self.dirty_changed.emit(False)
        self.game_loaded.emit(game)
        return True
