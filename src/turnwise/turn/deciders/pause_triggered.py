"""Cách vận hành chung của B2 và B3: hỏi một mô hình mỗi lần khách im đủ lâu.

Đây là cách pipecat vận hành smart-turn, và cũng là cách thường dùng cho endpointer đọc chữ:
VAD thấy khách im `trigger_silence_ms` thì hỏi, mô hình nói xong thì nhận lượt, im tới
`fallback_silence_ms` thì nhận lượt dù mô hình nói chưa xong. B2 và B3 khác nhau **chỉ** ở mô
hình được hỏi — nghe âm thanh hay đọc chữ — nên phép so sánh giữa chúng đo đúng khác biệt đó.

Cổng có tiếng / im lặng là cổng năng lượng cố định của B1 (`silence_floor_dbfs`).
"""

from __future__ import annotations

import logging
import time
from collections import deque
from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray

from turnwise.config import PauseTriggerConfig
from turnwise.turn.deciders.silence_threshold import rms_dbfs
from turnwise.types import FeatureFrame, TurnDecision, TurnOutcome

logger = logging.getLogger(__name__)

MODEL_RATE_HZ = 16_000
"""Cả smart-turn lẫn Whisper đều nhận 16 kHz mono."""

Predictor = Callable[[NDArray[np.float32]], float]
"""Âm thanh 16 kHz mono của lượt đang xét -> xác suất khách đã nói xong."""


class PauseTriggeredDecider:
    """Hỏi mô hình mỗi lần khách im đủ lâu; nhận lượt khi nó nói xong hoặc khi im quá lâu."""

    _speech_start: int | None
    _silence_ms: int
    _asked: bool
    _taken: bool

    def __init__(
        self,
        predict: Predictor,
        silence_floor_dbfs: float,
        config: PauseTriggerConfig,
        name: str,
        score_key: str,
    ) -> None:
        self.name = name
        self._score_key = score_key
        self.predict_ms: list[float] = []
        """Thời gian mỗi lần hỏi mô hình. Đo đạc, không phải trạng thái lượt: `reset` không xoá."""
        self._predict = predict
        self._floor_dbfs = silence_floor_dbfs
        self._config = config
        self._frames: deque[tuple[int, NDArray[np.float32]]] = deque()
        self.reset()

    def decide(self, frame: FeatureFrame) -> TurnDecision:
        scores: dict[str, float | None] = {}
        if not self._taken:
            samples = frame.samples[: len(frame.samples) - frame.padded_samples]
            self._check_rate(frame)
            self._remember(frame, samples)
            if len(samples) and rms_dbfs(samples) > self._floor_dbfs:
                if self._speech_start is None:
                    self._speech_start = frame.index
                self._silence_ms = 0
                self._asked = False
            elif self._speech_start is not None:
                self._silence_ms += round(frame.duration_s * 1000)
                if not self._asked and self._silence_ms >= self._config.trigger_silence_ms:
                    self._asked = True
                    started = time.perf_counter()
                    probability = self._predict(self._segment(frame))
                    self.predict_ms.append((time.perf_counter() - started) * 1000)
                    scores[self._score_key] = probability
                    self._taken = probability > self._config.probability_threshold
                if self._silence_ms >= self._config.fallback_silence_ms:
                    self._taken = True
                if self._taken:
                    logger.debug("take at frame %d (%.3fs)", frame.index, frame.start_s)

        return TurnDecision(
            outcome=TurnOutcome.TAKE if self._taken else TurnOutcome.HOLD,
            decider=self.name,
            frame_index=frame.index,
            at_s=frame.start_s,
            scores=scores,
            final_tone=None,
        )

    def reset(self) -> None:
        self._frames.clear()
        self._speech_start = None
        self._silence_ms = 0
        self._asked = False
        self._taken = False

    def _check_rate(self, frame: FeatureFrame) -> None:
        rate = round(len(frame.samples) / frame.duration_s)
        if rate != MODEL_RATE_HZ:
            raise ValueError(f"smart-turn needs {MODEL_RATE_HZ} Hz frames, got {rate} Hz")

    def _remember(self, frame: FeatureFrame, samples: NDArray[np.float32]) -> None:
        """Giữ vừa đủ khung cho một cửa sổ, cộng phần trước lúc bắt đầu nói."""
        self._frames.append((frame.index, samples.copy()))  # khung có thể trỏ vào ring buffer
        keep_ms = self._config.pre_speech_ms
        if self._speech_start is not None:
            keep_ms += self._config.window_s * 1000
        keep = round(keep_ms / (frame.duration_s * 1000)) + 1
        while len(self._frames) > keep:
            self._frames.popleft()

    def _segment(self, frame: FeatureFrame) -> NDArray[np.float32]:
        """Từ `pre_speech_ms` trước lúc bắt đầu nói tới khung hiện tại."""
        assert self._speech_start is not None
        pre_frames = round(self._config.pre_speech_ms / (frame.duration_s * 1000))
        first = self._speech_start - pre_frames
        return np.concatenate([s for i, s in self._frames if i >= first])
