"""Đặc trưng theo khung mà tầng `audio` tính sẵn cho mọi người tiêu thụ.

Nền ồn nằm ở đây chứ không trong scorer: nó là thuộc tính của micro và căn phòng, không của
lượt nói. Scorer bị xoá trạng thái ở mỗi ranh giới lượt (`.claude/rules/turn.md`), nên một
scorer tự ước lượng nền ồn sẽ mất nó đúng lúc cần nhất — đầu lượt, khi khách vừa bắt đầu nói.
Tầng này không biết lượt là gì, nên không bao giờ xoá.
"""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray

DIGITAL_SILENCE_DBFS = -120.0
"""Mức thay cho -inf của một khung toàn số 0, để phân vị không thành NaN."""


def level_dbfs(samples: NDArray[np.float32]) -> float:
    """Năng lượng khung theo dBFS, chặn dưới ở mức im lặng số."""
    if not len(samples):
        return DIGITAL_SILENCE_DBFS
    rms = float(np.sqrt(np.mean(np.square(samples), dtype=np.float64)))
    return DIGITAL_SILENCE_DBFS if rms <= 0.0 else max(20.0 * math.log10(rms), DIGITAL_SILENCE_DBFS)


class NoiseFloor:
    """Phân vị thấp của năng lượng khung trong một cửa sổ trượt, cấp phát sẵn một lần.

    Chưa đủ một cửa sổ thì chưa báo gì (`None`), và cổng dùng sàn cố định. Nếu báo sớm, một
    kênh mở ra bằng tiếng nói sẽ có "nền ồn" bằng chính tiếng nói, và đoạn nói đầu tiên bị bỏ
    qua: đo được trên kịch bản ngập ngừng của GĐ 0, ngưỡng lên tới -2 dBFS.
    """

    def __init__(self, window_frames: int, percentile: float) -> None:
        if window_frames <= 0:
            raise ValueError(f"window_frames must be positive, got {window_frames}")
        self._levels = np.full(window_frames, np.nan)
        self._next = 0
        self._filled = False
        self._percentile = percentile

    def update(self, samples: NDArray[np.float32]) -> float | None:
        self._levels[self._next] = level_dbfs(samples)
        self._next = (self._next + 1) % len(self._levels)
        self._filled = self._filled or self._next == 0
        return float(np.percentile(self._levels, self._percentile)) if self._filled else None
