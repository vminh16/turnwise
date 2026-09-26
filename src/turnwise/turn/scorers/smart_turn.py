"""Scorer smart-turn: mô hình của B2, dùng làm một nguồn tín hiệu trong hệ đề xuất.

Cùng mô hình, cùng lúc hỏi như B2 (khi khách im `trigger_silence_ms`), nhưng không tự quyết:
điểm của nó được fusion gộp với các scorer khác. Nhờ vậy bảng ablation trả lời được câu "hệ đề
xuất thêm được gì so với smart-turn một mình".
"""

from __future__ import annotations

from turnwise.config import AcousticOnnxConfig, GateConfig
from turnwise.turn.base import Prediction
from turnwise.turn.deciders.acoustic_onnx import Predictor
from turnwise.turn.scorers.speech import SpeechTracker
from turnwise.types import FeatureFrame


class SmartTurnScorer:
    name = "smart_turn"
    predicts = Prediction.END_OF_TURN

    def __init__(self, predict: Predictor, gate: GateConfig, config: AcousticOnnxConfig) -> None:
        self._predict = predict
        self._config = config
        self._speech = SpeechTracker(gate, keep_s=config.window_s + config.pre_speech_ms / 1000)
        self._first: int | None = None
        self._probability: float | None = None

    def score(self, frame: FeatureFrame) -> float | None:
        self._speech.push(frame)
        if self._speech.speaking:
            if self._first is None:
                pre = round(self._config.pre_speech_ms / (frame.duration_s * 1000))
                self._first = frame.index - pre
            self._probability = None  # khách nói tiếp: câu trả lời cũ hết hiệu lực
            return None
        if (
            self._probability is None
            and self._speech.heard
            and self._speech.silence_ms >= self._config.trigger_silence_ms
        ):
            self._probability = self._predict(self._speech.audio(first=self._first))
        return self._probability

    def reset(self) -> None:
        self._speech.reset()
        self._first = None
        self._probability = None
