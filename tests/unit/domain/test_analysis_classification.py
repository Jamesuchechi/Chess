"""Unit tests for move classification thresholds and accuracy computation.

Pure function tests with no Qt or engine dependency.
"""

import pytest

from chess_desktop.domain.analysis import (
    GameAnalysis,
    MoveAnalysis,
    MoveClassification,
    classify_move,
    compute_accuracy,
    game_analysis_from_json,
    game_analysis_to_json,
)


def test_classify_move_top_choice_is_best():
    """Played move matches engine's top choice: always BEST, cp_loss 0."""
    cls, cp_loss = classify_move(
        played_uci="e2e4",
        best_uci="e2e4",
        eval_before_cp=20,
        eval_after_cp=20,
        mate_before=None,
        mate_after=None,
    )
    assert cls == MoveClassification.BEST
    assert cp_loss == 0


def test_classify_move_zero_loss_is_best():
    """Different move but 0 cp loss: BEST."""
    cls, cp_loss = classify_move(
        played_uci="d2d4",
        best_uci="e2e4",
        eval_before_cp=20,
        eval_after_cp=20,
        mate_before=None,
        mate_after=None,
    )
    assert cls == MoveClassification.BEST
    assert cp_loss == 0


def test_classify_move_excellent_threshold():
    """< 10 cp loss: EXCELLENT."""
    cls, cp_loss = classify_move(
        played_uci="g1f3",
        best_uci="e2e4",
        eval_before_cp=25,
        eval_after_cp=18,  # loss = 7
        mate_before=None,
        mate_after=None,
    )
    assert cls == MoveClassification.EXCELLENT
    assert cp_loss == 7


def test_classify_move_good_threshold():
    """10 <= cp loss < 50: GOOD."""
    cls, cp_loss = classify_move(
        played_uci="c2c4",
        best_uci="e2e4",
        eval_before_cp=30,
        eval_after_cp=5,  # loss = 25
        mate_before=None,
        mate_after=None,
    )
    assert cls == MoveClassification.GOOD
    assert cp_loss == 25


def test_classify_move_inaccuracy_threshold():
    """50 <= cp loss < 100: INACCURACY."""
    cls, cp_loss = classify_move(
        played_uci="b1c3",
        best_uci="e2e4",
        eval_before_cp=40,
        eval_after_cp=-25,  # loss = 65
        mate_before=None,
        mate_after=None,
    )
    assert cls == MoveClassification.INACCURACY
    assert cp_loss == 65


def test_classify_move_mistake_threshold():
    """100 <= cp loss < 300: MISTAKE."""
    cls, cp_loss = classify_move(
        played_uci="a2a3",
        best_uci="e2e4",
        eval_before_cp=50,
        eval_after_cp=-100,  # loss = 150
        mate_before=None,
        mate_after=None,
    )
    assert cls == MoveClassification.MISTAKE
    assert cp_loss == 150


def test_classify_move_blunder_threshold():
    """300+ cp loss: BLUNDER."""
    cls, cp_loss = classify_move(
        played_uci="f2f3",
        best_uci="e2e4",
        eval_before_cp=50,
        eval_after_cp=-350,  # loss = 400
        mate_before=None,
        mate_after=None,
    )
    assert cls == MoveClassification.BLUNDER
    assert cp_loss == 400


def test_classify_mate_in_n_swing_to_lost_position_is_blunder():
    """Turning a forced mate for you into a lost position is always a Blunder."""
    # We had mate in 2, but played a move allowing opponent mate in 1
    cls, cp_loss = classify_move(
        played_uci="g1h3",
        best_uci="d1h5",
        eval_before_cp=None,
        eval_after_cp=None,
        mate_before=2,  # had forced mate for us
        mate_after=-1,  # now opponent has forced mate
    )
    assert cls == MoveClassification.BLUNDER
    assert cp_loss is None

    # We had mate in 1, but played a blunder that drops evaluation to -400
    cls, cp_loss = classify_move(
        played_uci="g1h3",
        best_uci="d1h5",
        eval_before_cp=None,
        eval_after_cp=-400,
        mate_before=1,
        mate_after=None,
    )
    assert cls == MoveClassification.BLUNDER
    assert cp_loss is None


def test_classify_delivering_mate_is_best():
    """Delivering checkmate (mate_after=0) is classified as BEST."""
    cls, cp_loss = classify_move(
        played_uci="d1h5",
        best_uci="d1h5",
        eval_before_cp=None,
        eval_after_cp=None,
        mate_before=1,
        mate_after=0,
    )
    assert cls == MoveClassification.BEST
    assert cp_loss == 0


def test_compute_accuracy_perfect_game():
    """All 0 cp loss results in 100.0% accuracy."""
    moves = [
        MoveAnalysis(
            ply=1,
            played_uci="e2e4",
            best_uci="e2e4",
            best_san=None,
            cp_loss=0,
            classification=MoveClassification.BEST,
            eval_before_cp=20,
            eval_after_cp=20,
        ),
        MoveAnalysis(
            ply=2,
            played_uci="e7e5",
            best_uci="e7e5",
            best_san=None,
            cp_loss=0,
            classification=MoveClassification.BEST,
            eval_before_cp=-20,
            eval_after_cp=-20,
        ),
    ]
    assert compute_accuracy(moves, is_white=True) == 100.0
    assert compute_accuracy(moves, is_white=False) == 100.0


def test_compute_accuracy_with_losses():
    """Cp losses proportionally reduce accuracy."""
    moves = [
        MoveAnalysis(
            ply=1,
            played_uci="e2e4",
            best_uci="e2e4",
            best_san=None,
            cp_loss=30,  # 30 loss -> 100 - 10 = 90%
            classification=MoveClassification.GOOD,
            eval_before_cp=20,
            eval_after_cp=-10,
        ),
    ]
    assert compute_accuracy(moves, is_white=True) == 90.0


def test_game_analysis_json_roundtrip():
    """Test serialization and deserialization roundtrip."""
    original = GameAnalysis(
        game_id="game-123",
        moves=[
            MoveAnalysis(
                ply=1,
                played_uci="e2e4",
                best_uci="e2e4",
                best_san=None,
                cp_loss=0,
                classification=MoveClassification.BEST,
                eval_before_cp=25,
                eval_after_cp=25,
            ),
            MoveAnalysis(
                ply=2,
                played_uci="e7e6",
                best_uci="e7e5",
                best_san="e5",
                cp_loss=15,
                classification=MoveClassification.GOOD,
                eval_before_cp=-25,
                eval_after_cp=-40,
            ),
        ],
        white_accuracy=100.0,
        black_accuracy=95.0,
    )

    json_str = game_analysis_to_json(original)
    loaded = game_analysis_from_json(json_str)

    assert loaded.game_id == original.game_id
    assert len(loaded.moves) == 2
    assert loaded.white_accuracy == 100.0
    assert loaded.black_accuracy == 95.0
    assert loaded.moves[0].played_uci == "e2e4"
    assert loaded.moves[0].classification == MoveClassification.BEST
    assert loaded.moves[1].best_san == "e5"
    assert loaded.moves[1].classification == MoveClassification.GOOD
