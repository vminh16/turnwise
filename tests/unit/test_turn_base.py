"""Hợp đồng của tầng turn: một cài đặt tối giản phải thoả được protocol."""

import numpy as np

from turnwise.turn.base import Prediction, Scorer, TurnDecider
from turnwise.types import FeatureFrame, TurnDecision, TurnOutcome


class CountingScorer:
    """Scorer bé nhất còn có nghĩa: đếm khung, bỏ phiếu trắng cho tới khi đủ dữ liệu."""

    name = "counting"
    predicts = Prediction.END_OF_TURN

    def __init__(self, warmup_frames: int) -> None:
        self._warmup_frames = warmup_frames
        self._seen = 0

    def score(self, frame: FeatureFrame) -> float | None:
        self._seen += 1
        if self._seen <= self._warmup_frames:
            return None
        return 1.0

    def reset(self) -> None:
        self._seen = 0


class AlwaysHold:
    name = "always_hold"

    def decide(self, frame: FeatureFrame) -> TurnDecision:
        return TurnDecision(
            outcome=TurnOutcome.HOLD,
            decider=self.name,
            frame_index=frame.index,
            at_s=frame.start_s,
        )

    def reset(self) -> None:
        return None


def make_frame(index: int = 0) -> FeatureFrame:
    return FeatureFrame(
        index=index,
        start_s=index * 0.02,
        duration_s=0.02,
        samples=np.zeros(320, dtype=np.float32),
    )


def test_minimal_implementations_satisfy_the_protocols() -> None:
    assert isinstance(CountingScorer(warmup_frames=1), Scorer)
    assert isinstance(AlwaysHold(), TurnDecider)


def test_a_scorer_may_abstain_before_it_has_evidence() -> None:
    scorer = CountingScorer(warmup_frames=2)
    assert scorer.score(make_frame(0)) is None
    assert scorer.score(make_frame(1)) is None
    assert scorer.score(make_frame(2)) == 1.0


def test_reset_clears_state_between_turns() -> None:
    """Trạng thái rò rỉ làm sai điểm mà không crash — bắt nó bằng chính hình dạng test này."""
    scorer = CountingScorer(warmup_frames=1)
    first = [scorer.score(make_frame(i)) for i in range(3)]
    scorer.reset()
    second = [scorer.score(make_frame(i)) for i in range(3)]
    assert first == second


def test_decider_returns_a_decision_for_every_frame() -> None:
    """SPEC R1: ước lượng liên tục, nên một chuỗi HOLD là kết quả hợp lệ."""
    decider = AlwaysHold()
    decisions = [decider.decide(make_frame(i)) for i in range(3)]
    assert [d.outcome for d in decisions] == [TurnOutcome.HOLD] * 3
    assert [d.frame_index for d in decisions] == [0, 1, 2]
    assert {d.decider for d in decisions} == {"always_hold"}
