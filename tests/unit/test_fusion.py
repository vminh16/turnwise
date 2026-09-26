"""Fusion: gộp riêng từng câu hỏi, bỏ phiếu trắng không tính là 0, tất cả trắng thì giữ im."""

import numpy as np

from turnwise.turn import fusion
from turnwise.turn.base import Prediction
from turnwise.turn.deciders.fused import FusedDecider
from turnwise.types import FeatureFrame, TurnOutcome

EOT, BC = Prediction.END_OF_TURN, Prediction.BACKCHANNEL


def test_abstentions_are_excluded_not_counted_as_zero() -> None:
    assert fusion.combine({EOT: [0.8, None]}) == {EOT: 0.8}


def test_all_abstaining_holds() -> None:
    combined = fusion.combine({EOT: [None, None]})
    assert fusion.decide(combined, 0.5, 0.5) == TurnOutcome.HOLD


def test_backchannel_is_checked_before_end_of_turn() -> None:
    combined = fusion.combine({EOT: [0.9], BC: [0.9]})
    assert fusion.decide(combined, 0.5, 0.5) == TurnOutcome.BACKCHANNEL


def test_end_of_turn_above_threshold_takes() -> None:
    assert fusion.decide(fusion.combine({EOT: [0.6, 0.4]}), 0.5, 0.5) == TurnOutcome.TAKE


class Fixed:
    def __init__(self, name: str, predicts: Prediction, value: float | None) -> None:
        self.name, self.predicts, self.value, self.resets = name, predicts, value, 0

    def score(self, frame: FeatureFrame) -> float | None:
        return self.value

    def reset(self) -> None:
        self.resets += 1


FRAME = FeatureFrame(index=0, start_s=0.0, duration_s=0.02, samples=np.zeros(320, np.float32))


def test_the_decision_carries_every_score_including_abstentions() -> None:
    decider = FusedDecider([Fixed("a", EOT, 0.9), Fixed("b", EOT, None)], 0.5, 0.5)
    decision = decider.decide(FRAME)
    assert decision.outcome == TurnOutcome.TAKE
    assert dict(decision.scores) == {"a": 0.9, "b": None}


def test_reset_reaches_every_scorer() -> None:
    scorers = [Fixed("a", EOT, 0.1), Fixed("b", BC, 0.1)]
    FusedDecider(scorers, 0.5, 0.5).reset()
    assert [s.resets for s in scorers] == [1, 1]
