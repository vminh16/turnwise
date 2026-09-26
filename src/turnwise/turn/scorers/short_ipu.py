"""Scorer đoạn ngắn: một tiếng ngắn rồi im thường là tiếng đệm ("dạ", "ừ"), không phải một lượt.

Chỉ nhìn độ dài, nên nó **không** phân biệt được "dạ" tiếng đệm với "Dạ." trọn lượt — ca khó nhất
của R4. Nó tồn tại để làm mốc: scorer ngôn điệu nào tốt hơn nó mới có giá trị.
"""

from __future__ import annotations

from turnwise.config import GateConfig, ShortIpuConfig
from turnwise.turn.base import Prediction
from turnwise.turn.scorers.speech import SpeechTracker
from turnwise.types import FeatureFrame


class ShortIpuScorer:
    name = "short_ipu"
    predicts = Prediction.BACKCHANNEL

    def __init__(self, gate: GateConfig, config: ShortIpuConfig) -> None:
        self._config = config
        self._speech = SpeechTracker(gate, keep_s=0.0)

    def score(self, frame: FeatureFrame) -> float | None:
        self._speech.push(frame)
        if self._speech.speaking or self._speech.silence_ms < self._config.trigger_silence_ms:
            return None
        if not self._speech.heard:
            return None
        ipu_ms = self._speech.last_ipu_frames * frame.duration_s * 1000
        return max(0.0, 1.0 - ipu_ms / self._config.max_ms)

    def reset(self) -> None:
        self._speech.reset()
