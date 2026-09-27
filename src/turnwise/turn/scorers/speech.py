"""Theo dõi có tiếng / im lặng từng khung, và giữ âm thanh gần đây cho scorer cần nghe lại.

Mỗi scorer giữ một bộ theo dõi riêng: rẻ (một phép RMS mỗi khung) và giữ các scorer độc lập,
nên tắt một scorer để làm ablation không làm đổi điểm của scorer khác.
"""

from __future__ import annotations

from collections import deque

import numpy as np
from numpy.typing import NDArray

from turnwise.config import GateConfig
from turnwise.turn.gate import is_speech, real_samples
from turnwise.types import FeatureFrame


class SpeechTracker:
    """Cổng năng lượng theo nền ồn của khung, cộng bộ nhớ âm thanh có giới hạn.

    Nền ồn đến từ tầng `audio` (`FeatureFrame.noise_floor_dbfs`), không ước lượng ở đây: nó là
    thuộc tính của micro, và bộ theo dõi này bị xoá ở mỗi ranh giới lượt.
    """

    def __init__(self, gate: GateConfig, keep_s: float) -> None:
        self._gate = gate
        self._keep_s = keep_s
        self._frames: deque[tuple[int, NDArray[np.float32]]] = deque()
        self.reset()

    def reset(self) -> None:
        self._frames.clear()
        self.heard = False
        self.speaking = False
        self.silence_ms = 0
        self.ipu_start: int | None = None
        self.ipu_end: int | None = None  # khung có tiếng cuối cùng của đoạn nói gần nhất

    def push(self, frame: FeatureFrame) -> None:
        samples = real_samples(frame)
        frame_ms = round(frame.duration_s * 1000)
        loud = is_speech(frame, self._gate)

        self._frames.append((frame.index, samples.copy()))  # khung có thể trỏ vào ring buffer
        while len(self._frames) * frame_ms > self._keep_s * 1000:
            self._frames.popleft()

        if loud:
            if self.ipu_start is None or self.silence_ms >= self._gate.merge_ms:
                self.ipu_start = frame.index
            self.ipu_end = frame.index
            self.heard = True
            self.silence_ms = 0
        elif self.heard:
            self.silence_ms += frame_ms
        self.speaking = loud or (self.heard and self.silence_ms < self._gate.merge_ms)

    @property
    def last_ipu_frames(self) -> int:
        if self.ipu_start is None or self.ipu_end is None:
            return 0
        return self.ipu_end - self.ipu_start + 1

    def audio(self, first: int | None = None, last: int | None = None) -> NDArray[np.float32]:
        """Âm thanh đã giữ, từ khung `first` tới khung `last`, cả hai đầu tính."""
        parts = [
            s
            for i, s in self._frames
            if (first is None or i >= first) and (last is None or i <= last)
        ]
        return np.concatenate(parts) if parts else np.zeros(0, dtype=np.float32)
