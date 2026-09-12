"""Fixture dùng chung cho cả bộ test.

Wav sinh tại chỗ chứ không commit vào repo: fixture nhị phân trong git thì không ai
đọc được diff, và một file 10 giây ở 16 kHz đắt hơn nhiều so với ba dòng numpy sinh
lại nó. Sinh tại chỗ cũng buộc mọi thuộc tính của tín hiệu phải viết ra thành tham số,
nên đọc test là biết nó đang cho nghe cái gì.

Hạt giống cố định: hai lần chạy phải cho cùng một tín hiệu, nếu không mọi khác biệt
giữa hai lần chạy đều lẫn vào nhiễu.
"""

from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from turnwise.config import AudioConfig, load_settings

WavWriter = Callable[..., Path]


@pytest.fixture(scope="session")
def audio() -> AudioConfig:
    return load_settings().audio


@pytest.fixture
def write_wav() -> WavWriter:
    """Ghi một file wav nhiễu trắng, trả về đường dẫn.

    `amplitude` là biên độ tuyến tính trong [0, 1]; 0.2 rơi vào khoảng -14 dBFS, tức
    mức tiếng nói bình thường, còn 0.0 cho im lặng tuyệt đối.
    """

    def write(
        path: Path,
        samples: int,
        sample_rate_hz: int = 16000,
        channels: int = 1,
        amplitude: float = 0.1,
        seed: int = 0,
    ) -> Path:
        rng = np.random.default_rng(seed)
        data = (rng.standard_normal((samples, channels)) * amplitude).astype(np.float32)
        sf.write(path, data, sample_rate_hz, subtype="PCM_16")
        return path

    return write
