"""Gộp điểm của các scorer thành một quyết định. Seam trong, chỉ `deciders/fused.py` dùng.

Ba luật của `.claude/rules/turn.md`, và chỉ ba luật đó:

- gộp **riêng từng câu hỏi** (`Prediction`), mỗi câu hỏi một ngưỡng;
- scorer bỏ phiếu trắng bị **loại khỏi** phép gộp, không tính là 0;
- mọi scorer bỏ phiếu trắng thì giữ im (`HOLD`): im lặng không phải bằng chứng lượt đã xong.

Phép gộp là trung bình cộng. Có trọng số hay học một bộ gộp là việc của GĐ 3, sau khi biết từng
scorer đóng góp bao nhiêu.
"""

from __future__ import annotations

from collections.abc import Mapping
from statistics import fmean

from turnwise.turn.base import Prediction
from turnwise.types import TurnOutcome


def combine(scores: Mapping[Prediction, list[float | None]]) -> dict[Prediction, float | None]:
    """Trung bình các điểm không bỏ phiếu trắng, theo từng câu hỏi."""
    out: dict[Prediction, float | None] = {}
    for prediction, values in scores.items():
        voted = [v for v in values if v is not None]
        out[prediction] = fmean(voted) if voted else None
    return out


def decide(
    combined: Mapping[Prediction, float | None], take_threshold: float, backchannel_threshold: float
) -> TurnOutcome:
    """Tiếng đệm được xét trước: "dạ" chêm vào mà bị nhận thành xong lượt là lỗi R4."""
    backchannel = combined.get(Prediction.BACKCHANNEL)
    if backchannel is not None and backchannel >= backchannel_threshold:
        return TurnOutcome.BACKCHANNEL
    end_of_turn = combined.get(Prediction.END_OF_TURN)
    if end_of_turn is not None and end_of_turn >= take_threshold:
        return TurnOutcome.TAKE
    return TurnOutcome.HOLD
