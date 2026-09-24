"""Domain types for post-game move classification and analysis results."""

from __future__ import annotations

import enum
import json
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

_MATE_SENTINEL = 10_000  # centipawn equivalent used for forced-mate positions


class MoveClassification(enum.Enum):
    """Per-move quality label, matching Chess.com standard buckets."""

    BRILLIANT = "Brilliant"  # objectively best and unexpected / sacrificial
    BEST = "Best"  # matches engine top-choice (cp_loss == 0)
    EXCELLENT = "Excellent"  # < 10 cp loss
    GOOD = "Good"  # < 50 cp loss
    INACCURACY = "Inaccuracy"  # 50–99 cp loss
    MISTAKE = "Mistake"  # 100–299 cp loss
    BLUNDER = "Blunder"  # ≥ 300 cp loss, or mate swing

    @property
    def badge(self) -> str:
        """Short badge text shown next to the move in the history panel."""
        return _BADGES[self]

    @property
    def color_hex(self) -> str:
        """Hex colour for the badge."""
        return _COLORS[self]


_BADGES: dict[MoveClassification, str] = {
    MoveClassification.BRILLIANT: "!!",
    MoveClassification.BEST: "✓",
    MoveClassification.EXCELLENT: "!",
    MoveClassification.GOOD: "",
    MoveClassification.INACCURACY: "?!",
    MoveClassification.MISTAKE: "?",
    MoveClassification.BLUNDER: "??",
}

_COLORS: dict[MoveClassification, str] = {
    MoveClassification.BRILLIANT: "#00bfff",
    MoveClassification.BEST: "#769656",
    MoveClassification.EXCELLENT: "#5aa05a",
    MoveClassification.GOOD: "#b0b0b0",
    MoveClassification.INACCURACY: "#e0a020",
    MoveClassification.MISTAKE: "#e06020",
    MoveClassification.BLUNDER: "#c03030",
}


def classify_move(
    played_uci: str,
    best_uci: str | None,
    eval_before_cp: int | None,
    eval_after_cp: int | None,
    mate_before: int | None,
    mate_after: int | None,
) -> tuple[MoveClassification, int | None]:
    """Classify a single move and compute its centipawn loss.

    All evaluations are from the **side-to-move's perspective** before the
    move is played. ``eval_after_cp`` must be negated by the caller to
    convert from the opponent's perspective (as the engine reports it) back to
    the mover's perspective.

    Returns:
        (classification, cp_loss) where cp_loss is None for mate swings.
    """
    # ---- Special-case mate-in-N swings ---------------------------------------
    # Turning a forced mate for you into a lost position is always a Blunder
    # regardless of raw cp delta.
    if mate_before is not None and mate_before > 0:
        if (mate_after is not None and mate_after < 0) or (
            mate_after is None and eval_after_cp is not None and eval_after_cp < 0
        ):
            return MoveClassification.BLUNDER, None
        if mate_after is None and eval_after_cp is None:
            return MoveClassification.BLUNDER, None

    # If played move matches engine's top choice, it's always Best
    if best_uci and played_uci == best_uci:
        return MoveClassification.BEST, 0

    # If mover still delivered checkmate (mate_after == 0)
    if mate_after == 0:
        return MoveClassification.BEST, 0

    # ---- cp-loss computation -------------------------------------------------
    before_cp = (
        eval_before_cp
        if eval_before_cp is not None
        else (_MATE_SENTINEL if (mate_before is not None and mate_before > 0) else -_MATE_SENTINEL)
    )
    after_cp = (
        eval_after_cp
        if eval_after_cp is not None
        else (_MATE_SENTINEL if (mate_after is not None and mate_after > 0) else -_MATE_SENTINEL)
    )

    cp_loss = max(0, before_cp - after_cp)

    # ---- Classify by thresholds ----------------------------------------------
    if cp_loss == 0:
        cls = MoveClassification.BEST
    elif cp_loss < 10:
        cls = MoveClassification.EXCELLENT
    elif cp_loss < 50:
        cls = MoveClassification.GOOD
    elif cp_loss < 100:
        cls = MoveClassification.INACCURACY
    elif cp_loss < 300:
        cls = MoveClassification.MISTAKE
    else:
        cls = MoveClassification.BLUNDER

    return cls, cp_loss


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MoveAnalysis:
    """Analysis result for a single half-move (ply)."""

    ply: int  # 1-indexed
    played_uci: str
    best_uci: str | None  # engine's top choice at this position
    best_san: str | None  # SAN of best_uci for display (None if same as played)
    cp_loss: int | None  # centipawn loss; None for mate swings
    classification: MoveClassification
    eval_before_cp: int | None  # raw cp eval before move (side-to-move perspective)
    eval_after_cp: int | None  # raw cp eval after move (side-to-move perspective, negated)


@dataclass(frozen=True)
class GameAnalysis:
    """Complete analysis result for a finished game."""

    game_id: str
    moves: list[MoveAnalysis] = field(default_factory=list)
    white_accuracy: float = 0.0  # 0–100
    black_accuracy: float = 0.0  # 0–100


def compute_accuracy(move_analyses: list[MoveAnalysis], is_white: bool) -> float:
    """Compute accuracy percentage for one side using win-probability weighting.

    Uses a standard formula: accuracy = 100 - average(cp_loss) / 3.0,
    clamped to [0, 100]. Moves with no cp_loss (mate swings) contribute 300 cp.
    """
    side_plies = [
        m for m in move_analyses if (m.ply % 2 == 1) == is_white  # odd ply = White, even ply = Black
    ]
    if not side_plies:
        return 100.0

    losses = [(m.cp_loss if m.cp_loss is not None else 300) for m in side_plies]
    avg_loss = sum(losses) / len(losses)
    # Scale: 0 avg loss → 100%, 300+ avg loss → 0%
    accuracy = max(0.0, min(100.0, 100.0 - avg_loss / 3.0))
    return round(accuracy, 1)


# ---------------------------------------------------------------------------
# JSON serialisation helpers (usable by persistence and services)
# ---------------------------------------------------------------------------


def game_analysis_to_json(ga: GameAnalysis) -> str:
    """Serialise a GameAnalysis to a JSON string for SQLite storage."""
    moves_data = [
        {
            "ply": m.ply,
            "played_uci": m.played_uci,
            "best_uci": m.best_uci,
            "best_san": m.best_san,
            "cp_loss": m.cp_loss,
            "classification": m.classification.value,
            "eval_before_cp": m.eval_before_cp,
            "eval_after_cp": m.eval_after_cp,
        }
        for m in ga.moves
    ]
    return json.dumps(
        {
            "game_id": ga.game_id,
            "moves": moves_data,
            "white_accuracy": ga.white_accuracy,
            "black_accuracy": ga.black_accuracy,
        }
    )


def game_analysis_from_json(raw: str) -> GameAnalysis:
    """Deserialise a GameAnalysis from a JSON string stored in SQLite."""
    data: dict[str, Any] = json.loads(raw)
    moves = [
        MoveAnalysis(
            ply=m["ply"],
            played_uci=m["played_uci"],
            best_uci=m.get("best_uci"),
            best_san=m.get("best_san"),
            cp_loss=m.get("cp_loss"),
            classification=MoveClassification(m["classification"]),
            eval_before_cp=m.get("eval_before_cp"),
            eval_after_cp=m.get("eval_after_cp"),
        )
        for m in data["moves"]
    ]
    return GameAnalysis(
        game_id=data["game_id"],
        moves=moves,
        white_accuracy=data.get("white_accuracy", 0.0),
        black_accuracy=data.get("black_accuracy", 0.0),
    )
