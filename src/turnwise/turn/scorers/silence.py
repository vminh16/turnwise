"""Scorer im lặng: im càng lâu càng có khả năng khách đã xong.

Đây là B1 viết lại thành một nguồn tín hiệu, để fusion so được "chỉ nghe im lặng" với "im lặng
cộng thứ khác" trong cùng một bảng ablation.
"""

from __future__ import annotations

from turnwise.config import GateConfig, SilenceScorerConfig
from turnwise.turn.base import Prediction
from turnwise.turn.scorers.speech import SpeechTracker
from turnwise.types import FeatureFrame


class SilenceScorer:
    name = "silence"
    predicts = Prediction.END_OF_TURN

    def __init__(self, gate: GateConfig, config: SilenceScorerConfig) -> None:
        self._config = config
        self._speech = SpeechTracker(gate, keep_s=0.0)

    def score(self, frame: FeatureFrame) -> float | None:
        self._speech.push(frame)
        if not self._speech.heard:
            return None  # im lặng trước khi ai nói gì không phải bằng chứng của lượt đã xong
        if self._speech.speaking:
            return 0.0
        return min(1.0, self._speech.silence_ms / self._config.full_ms)

    def reset(self) -> None:
        self._speech.reset()
