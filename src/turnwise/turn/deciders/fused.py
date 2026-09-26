"""Hệ đề xuất: nhiều scorer chấm song song, `fusion` gộp lại, quyết định mang theo từng điểm.

Tắt bật scorer bằng `turn.scorers`, nên một bảng ablation chỉ là nhiều file cấu hình
(`configs/ablation/`). `TurnDecision.scores` ghi điểm của **mọi** scorer đang bật ở mọi khung,
`None` là bỏ phiếu trắng, để một quyết định sai quy được trách nhiệm cho đúng thành phần.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from turnwise.turn import fusion
from turnwise.turn.base import Prediction, Scorer
from turnwise.types import FeatureFrame, TurnDecision


class FusedDecider:
    name = "fused"

    def __init__(
        self, scorers: Sequence[Scorer], take_threshold: float, backchannel_threshold: float
    ) -> None:
        if not scorers:
            raise ValueError("the fused decider needs at least one scorer in turn.scorers")
        self._scorers = list(scorers)
        self._take = take_threshold
        self._backchannel = backchannel_threshold

    def decide(self, frame: FeatureFrame) -> TurnDecision:
        scores: dict[str, float | None] = {}
        grouped: dict[Prediction, list[float | None]] = defaultdict(list)
        for scorer in self._scorers:
            value = scorer.score(frame)
            scores[scorer.name] = value
            grouped[scorer.predicts].append(value)
        outcome = fusion.decide(fusion.combine(grouped), self._take, self._backchannel)
        return TurnDecision(
            outcome=outcome,
            decider=self.name,
            frame_index=frame.index,
            at_s=frame.start_s,
            scores=scores,
            final_tone=None,
        )

    def reset(self) -> None:
        for scorer in self._scorers:
            scorer.reset()
