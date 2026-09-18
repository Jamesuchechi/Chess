"""Chess engine integration package. UCI communication, Stockfish discovery, and workers."""

from chess_desktop.engine.difficulty import Difficulty
from chess_desktop.engine.discovery import find_stockfish_binary
from chess_desktop.engine.engine import ChessEngine
from chess_desktop.engine.fallback_engine import FallbackEngine
from chess_desktop.engine.stockfish import SearchCancelledError, StockfishEngine

__all__ = [
    "ChessEngine",
    "Difficulty",
    "FallbackEngine",
    "SearchCancelledError",
    "StockfishEngine",
    "find_stockfish_binary",
]
