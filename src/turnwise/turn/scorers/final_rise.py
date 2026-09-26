"""Scorer đuôi lên: độ dốc F0 ở cuối đoạn nói, tính bằng nửa cung mỗi giây.

Giả thuyết đang kiểm chứng, không phải sự thật đã biết (`.claude/rules/turn.md`): Hà & Grice
(2010) thấy chỗ nhường lượt trong tiếng Việt mang đường lên kết thúc ở H%, bất kể thanh của âm
tiết cuối. Scorer này đo đúng điều đó và để fusion quyết nó đáng tin tới đâu.

Nửa cung là thang tương đối, nên độ dốc không phụ thuộc giọng cao hay trầm: không cần chuẩn hoá
theo người nói như F0 thô. Chưa tách thanh điệu khỏi ngữ điệu; đó là bước kế tiếp của GĐ 3.

Chạy một lần mỗi khoảng lặng, khi khách im `trigger_silence_ms`; `to_pitch_ac` trên 300 ms tốn
dưới 1 ms trên laptop dự án (`docs/research/turn-taking-methods.md` §5).
"""

from __future__ import annotations

import math

import numpy as np

from turnwise.config import FinalRiseConfig, GateConfig
from turnwise.turn.base import Prediction
from turnwise.turn.scorers.speech import SpeechTracker
from turnwise.types import FeatureFrame

PITCH_STEP_S = 0.01


class FinalRiseScorer:
    name = "final_rise"
    predicts = Prediction.END_OF_TURN

    def __init__(self, gate: GateConfig, config: FinalRiseConfig) -> None:
        self._config = config
        self._speech = SpeechTracker(gate, keep_s=config.window_ms / 1000 + 1.0)
        self._probability: float | None = None
        self._asked = False

    def score(self, frame: FeatureFrame) -> float | None:
        self._speech.push(frame)
        if self._speech.speaking:
            self._probability, self._asked = None, False
            return None
        if (
            not self._asked
            and self._speech.heard
            and self._speech.silence_ms >= self._config.trigger_silence_ms
        ):
            self._asked = True
            rate = round(len(frame.samples) / frame.duration_s)
            slope = self.slope(
                self._speech.audio(self._speech.ipu_start, self._speech.ipu_end), rate
            )
            if slope is not None:
                z = (slope - self._config.slope_center_st_per_s) / self._config.slope_scale_st_per_s
                self._probability = 1.0 / (1.0 + math.exp(-z))
        return self._probability

    def slope(self, audio: np.ndarray, rate: int) -> float | None:
        """Độ dốc F0 (nửa cung/giây) trên `window_ms` cuối; `None` khi quá ít khung hữu thanh."""
        import parselmouth

        tail = audio[-round(rate * self._config.window_ms / 1000) :].astype(np.float64)
        if len(tail) < rate * 3 / self._config.pitch_floor_hz:
            return None
        pitch = parselmouth.Sound(tail, sampling_frequency=rate).to_pitch_ac(
            time_step=PITCH_STEP_S,
            pitch_floor=self._config.pitch_floor_hz,
            pitch_ceiling=self._config.pitch_ceiling_hz,
        )
        f0 = pitch.selected_array["frequency"]
        voiced = f0 > 0
        if voiced.sum() < self._config.min_voiced_frames:
            return None
        t = pitch.xs()[voiced]
        st = 12 * np.log2(f0[voiced] / np.median(f0[voiced]))
        return float(np.polyfit(t, st, 1)[0])

    def reset(self) -> None:
        self._speech.reset()
        self._probability = None
        self._asked = False
