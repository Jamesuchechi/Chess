"""Stockfish UCI engine process manager."""

import logging
import subprocess
import threading
from pathlib import Path

from chess_desktop.engine.discovery import find_stockfish_binary
from chess_desktop.engine.engine import ChessEngine, PositionEval

logger = logging.getLogger(__name__)


class SearchCancelledError(RuntimeError):
    """Raised when an engine search is cancelled by the caller."""


class StockfishEngine(ChessEngine):
    """Encapsulates a Stockfish UCI subprocess and implements ChessEngine."""

    def __init__(self, binary_path: str | Path | None = None) -> None:
        if binary_path:
            self._binary_path = str(binary_path)
        else:
            found = find_stockfish_binary()
            if not found:
                raise FileNotFoundError("Stockfish binary could not be found on the system.")
            self._binary_path = found

        self._process: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()
        self._is_searching = False
        self._is_cancelled = False

    @property
    def binary_path(self) -> str:
        """Path to the underlying Stockfish executable."""
        return self._binary_path

    def start(self) -> None:
        """Start the Stockfish subprocess and perform initial UCI handshake."""
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                return

            try:
                self._process = subprocess.Popen(
                    [self._binary_path],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    bufsize=1,
                )
            except Exception as e:
                raise RuntimeError(
                    f"Failed to launch Stockfish at '{self._binary_path}': {e}"
                ) from e

            # UCI handshake
            self._send_line("uci")
            while True:
                line = self._read_line()
                if line == "uciok":
                    break

            self._send_line("isready")
            while True:
                line = self._read_line()
                if line == "readyok":
                    break

            logger.info("Stockfish engine started successfully (%s)", self._binary_path)

    def _send_line(self, line: str) -> None:
        """Write line to engine stdin."""
        if self._process is None or self._process.stdin is None or self._process.poll() is not None:
            raise RuntimeError("Engine process is not running.")
        self._process.stdin.write(f"{line}\n")
        self._process.stdin.flush()

    def _read_line(self) -> str:
        """Read a single trimmed line from engine stdout."""
        if (
            self._process is None
            or self._process.stdout is None
            or self._process.poll() is not None
        ):
            raise RuntimeError("Engine process is not running.")
        line = self._process.stdout.readline()
        if not line:
            raise RuntimeError("Unexpected EOF reading from engine process.")
        return str(line.strip())

    def set_skill_level(self, skill_level: int) -> None:
        """Set Stockfish 'Skill Level' option (0 to 20)."""
        clamped = max(0, min(20, skill_level))
        self._send_line(f"setoption name Skill Level value {clamped}")
        self._send_line("isready")
        while True:
            if self._read_line() == "readyok":
                break

    def set_position(
        self,
        fen: str | None = None,
        moves_uci: list[str] | None = None,
    ) -> None:
        """Set board position in engine."""
        with self._lock:
            if moves_uci:
                cmd = f"position startpos moves {' '.join(moves_uci)}"
            elif fen and fen != "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1":
                cmd = f"position fen {fen}"
            else:
                cmd = "position startpos"

            self._send_line(cmd)

    def search_best_move(
        self,
        depth: int | None = None,
        time_ms: int | None = None,
        skill_level: int | None = None,
    ) -> str:
        """Search for best move, blocking until bestmove line is received."""
        with self._lock:
            if self._is_cancelled:
                self._is_cancelled = False
                raise SearchCancelledError("Search was cancelled by user.")
            self._is_searching = True
            self._is_cancelled = False

            if skill_level is not None:
                self.set_skill_level(skill_level)

            parts = ["go"]
            if time_ms is not None and time_ms > 0:
                parts.append(f"movetime {time_ms}")
            if depth is not None and depth > 0:
                parts.append(f"depth {depth}")

            self._send_line(" ".join(parts))

        # Read lines until bestmove (outside lock so stop() can be called concurrently)
        best_move: str | None = None
        try:
            while True:
                line = self._read_line()
                if line.startswith("bestmove"):
                    tokens = line.split()
                    if len(tokens) >= 2:
                        best_move = tokens[1]
                    break
        finally:
            with self._lock:
                self._is_searching = False
                was_cancelled = self._is_cancelled
                self._is_cancelled = False

        if was_cancelled:
            raise SearchCancelledError("Search was cancelled by user.")
        if not best_move or best_move == "(none)":
            raise RuntimeError("Engine returned no legal moves.")
        return best_move

    def evaluate_position(
        self,
        depth: int = 14,
        time_ms: int | None = None,
    ) -> PositionEval:
        """Evaluate current position, returning centipawn/mate score and best move.

        Sends a ``go depth N`` (+ optional ``movetime M``) command and collects
        score information from ``info`` lines before the final ``bestmove`` reply.
        Does not modify the position set via :meth:`set_position`.
        """
        with self._lock:
            if self._is_cancelled:
                self._is_cancelled = False
                raise SearchCancelledError("Evaluation cancelled.")
            self._is_searching = True
            self._is_cancelled = False

            parts = ["go"]
            if time_ms is not None and time_ms > 0:
                parts.append(f"movetime {time_ms}")
            if depth > 0:
                parts.append(f"depth {depth}")
            self._send_line(" ".join(parts))

        # Collect score from info lines; update whenever a deeper info arrives.
        score_cp: int | None = None
        mate_in: int | None = None
        reached_depth: int = 0
        best_move: str | None = None

        try:
            while True:
                line = self._read_line()
                if line.startswith("info"):
                    tokens = line.split()
                    # Parse depth
                    if "depth" in tokens:
                        try:
                            reached_depth = int(tokens[tokens.index("depth") + 1])
                        except (ValueError, IndexError):
                            pass
                    # Parse score
                    if "score" in tokens:
                        idx = tokens.index("score")
                        try:
                            kind = tokens[idx + 1]
                            value = int(tokens[idx + 2])
                            if kind == "cp":
                                score_cp = value
                                mate_in = None
                            elif kind == "mate":
                                mate_in = value
                                score_cp = None
                        except (ValueError, IndexError):
                            pass
                elif line.startswith("bestmove"):
                    tokens = line.split()
                    if len(tokens) >= 2 and tokens[1] != "(none)":
                        best_move = tokens[1]
                    break
        finally:
            with self._lock:
                self._is_searching = False
                was_cancelled = self._is_cancelled
                self._is_cancelled = False

        if was_cancelled:
            raise SearchCancelledError("Evaluation cancelled by user.")

        return PositionEval(
            best_move_uci=best_move,
            score_cp=score_cp,
            mate_in=mate_in,
            depth=reached_depth or depth,
        )

    def stop(self) -> None:
        """Send immediate UCI stop command."""
        with self._lock:
            if self._is_searching and self._process is not None:
                self._is_cancelled = True
                try:
                    self._send_line("stop")
                except RuntimeError:
                    pass

    def is_ready(self) -> bool:
        """Check if engine responds to isready."""
        with self._lock:
            if self._process is None or self._process.poll() is not None:
                return False
            try:
                self._send_line("isready")
                return self._read_line() == "readyok"
            except (RuntimeError, OSError):
                return False

    def quit(self) -> None:
        """Cleanly terminate the engine process."""
        with self._lock:
            if self._process is None:
                return

            try:
                self._send_line("quit")
                self._process.wait(timeout=1.0)
            except Exception:
                self._process.kill()
            finally:
                self._process = None
                self._is_searching = False
                logger.info("Stockfish engine shut down.")
