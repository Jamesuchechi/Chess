"""UI tests for HistoryPanel."""

from pytestqt.qtbot import QtBot

from chess_desktop.domain.enums import PlayerType
from chess_desktop.services.game_service import GameService
from chess_desktop.ui.board.history_panel import HistoryPanel


def test_history_panel_initialization(qtbot: QtBot) -> None:
    """Verify HistoryPanel initializes and reflects match configuration."""
    service = GameService()
    service.new_game("Player", "Stockfish", PlayerType.HUMAN, PlayerType.COMPUTER)
    panel = HistoryPanel(service)
    qtbot.addWidget(panel)
    panel.show()

    assert "Play vs Computer" in panel._match_mode_lbl.text()
    assert panel._thinking_card.isHidden()


def test_history_panel_thinking_indicator_toggle(qtbot: QtBot) -> None:
    """Verify HistoryPanel shows and hides thinking card on engine_thinking_changed."""
    service = GameService()
    panel = HistoryPanel(service)
    qtbot.addWidget(panel)
    panel.show()

    # Engine starts thinking
    service.engine_thinking_changed.emit(True)
    assert panel._thinking_card.isVisible()
    assert panel._anim_timer.isActive()

    # Engine stops thinking
    service.engine_thinking_changed.emit(False)
    assert panel._thinking_card.isHidden()
    assert not panel._anim_timer.isActive()


def test_history_panel_move_history_table(qtbot: QtBot) -> None:
    """Verify moves are added to table rows accurately."""
    service = GameService()
    service.new_game("White", "Black", PlayerType.HUMAN, PlayerType.HUMAN)
    panel = HistoryPanel(service)
    qtbot.addWidget(panel)
    panel.show()

    assert panel._table.rowCount() == 0

    assert service.try_move("e2", "e4")
    assert panel._table.rowCount() == 1
    assert panel._table.item(0, 1).text() == "e4"

    assert service.try_move("e7", "e5")
    assert panel._table.rowCount() == 1
    assert panel._table.item(0, 2).text() == "e5"

    service.cleanup()
