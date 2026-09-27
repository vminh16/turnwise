"""Cổng có tiếng / im lặng dùng chung cho mọi decider và mọi scorer.

Một cổng cho cả bốn hệ (B1, B2, B3 và hệ đề xuất), để phép so sánh đo phương pháp chứ không đo
micro. Ngưỡng ở mỗi khung là max(`floor_dbfs`, nền ồn + `margin_db`), nền ồn do tầng `audio`
ước lượng. Trước khi có cổng chung, B1, B2, B3 dùng -45 dBFS cố định; nền ồn micro của S001 là
-34 dBFS, nên với S001 cả ba không bao giờ thấy im lặng.
"""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray

from turnwise.config import GateConfig
from turnwise.types import FeatureFrame


def rms_dbfs(samples: NDArray[np.float32]) -> float:
    """Mức năng lượng của khung, tính bằng dBFS. Khung toàn không cho `-inf`."""
    rms = float(np.sqrt(np.mean(np.square(samples), dtype=np.float64)))
    if rms <= 0.0:
        return -math.inf
    return 20.0 * math.log10(rms)


def real_samples(frame: FeatureFrame) -> NDArray[np.float32]:
    """Bỏ phần đệm của khung cuối: đệm kéo RMS xuống và biến một đuôi nhỏ tiếng thành im lặng."""
    return frame.samples[: len(frame.samples) - frame.padded_samples]


def threshold_dbfs(frame: FeatureFrame, gate: GateConfig) -> float:
    if frame.noise_floor_dbfs is None:
        return gate.floor_dbfs
    return max(gate.floor_dbfs, frame.noise_floor_dbfs + gate.margin_db)


def is_speech(frame: FeatureFrame, gate: GateConfig) -> bool:
    samples = real_samples(frame)
    return bool(len(samples)) and rms_dbfs(samples) > threshold_dbfs(frame, gate)
