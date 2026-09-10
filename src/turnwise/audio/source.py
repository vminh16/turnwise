"""Seam ngoài của tầng `audio`: nơi khung đặc trưng đi ra.

Mọi thứ phía trên tầng này — `turn/`, `dialog/`, bộ chạy kịch bản, `evaluation/` —
chỉ nhìn thấy `FrameSource`. Micro và file wav là hai adapter ở cùng seam đó, và
chính điều này làm cho bộ kịch bản chạy được mà không cần micro
(`.claude/rules/audio.md`).

`WavFrameSource` là adapter đọc file. Nó cố ý **không** làm ba việc:

- Không lấy mẫu lại. Sai tốc độ lấy mẫu thì báo lỗi, vì lấy mẫu lại trong im lặng đổi
  phổ tín hiệu mà không để lại dấu vết nào trong số đo.
- Không ước lượng F0. Đó là việc của `features.py`, và mọi khung ở đây để `f0_hz`
  bằng `None`.
- Không đo độ trễ. Thời gian đọc từ file không phải độ trễ; chỉ đường chạy sống mới
  tính (`AGENTS.md`, `.claude/rules/audio.md`).

Kích thước khung suy ra từ `configs/`, không có literal nào trong file này.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np
import soundfile as sf

from turnwise.config import AudioConfig
from turnwise.types import FeatureFrame

logger = logging.getLogger(__name__)


@runtime_checkable
class FrameSource(Protocol):
    """Một nguồn phát khung đặc trưng cách đều nhau.

    Khung phát ra phải liên tục: `index` tăng đúng một đơn vị mỗi lần, và `start_s`
    cách nhau đúng `duration_s`. Một khung bị mất phải được đếm và báo qua telemetry,
    không được lặng lẽ bỏ qua — một khoảng trống không báo trông giống hệt một khoảng
    im lặng, và im lặng chính là tín hiệu mà cả hệ thống đang đo (`types.py`).
    """

    def __iter__(self) -> Iterator[FeatureFrame]: ...


class WavFrameSource:
    """Phát khung từ một file wav, dùng cho bộ kịch bản và cho `evaluation/`.

    Toàn bộ file được nạp vào bộ nhớ lúc dựng: file kịch bản dài vài giây, và đọc
    một lần rồi thôi giúp vòng lặp phát khung không chạm đĩa lần nào.
    """

    def __init__(self, path: Path | str, audio: AudioConfig) -> None:
        if audio.channels != 1:
            raise ValueError(
                f"WavFrameSource chỉ đọc mono, còn audio.channels={audio.channels}. "
                "Hội thoại hai kênh của Giai đoạn 1 cần một adapter riêng."
            )

        self._path = Path(path)
        data, sample_rate_hz = sf.read(self._path, dtype="float32", always_2d=True)

        if sample_rate_hz != audio.sample_rate_hz:
            raise ValueError(
                f"{self._path} lấy mẫu ở {sample_rate_hz} Hz, còn cấu hình đòi "
                f"{audio.sample_rate_hz} Hz. Nguồn này không lấy mẫu lại."
            )
        if data.shape[1] != audio.channels:
            raise ValueError(
                f"{self._path} có {data.shape[1]} kênh, còn cấu hình đòi {audio.channels}."
            )

        self._samples: np.ndarray = np.ascontiguousarray(data[:, 0], dtype=np.float32)
        self._samples.flags.writeable = False
        self._frame_samples = audio.sample_rate_hz * audio.feature_frame_ms // 1000
        self._duration_s = audio.feature_frame_ms / 1000

        logger.debug(
            "%s: %d samples at %d Hz, %d samples per frame",
            self._path.name,
            len(self._samples),
            sample_rate_hz,
            self._frame_samples,
        )

    def __iter__(self) -> Iterator[FeatureFrame]:
        """Phát lần lượt từng khung, khung cuối được đệm không cho đủ độ dài.

        Đệm chứ không cắt bỏ: phần đuôi của một phát ngôn là chỗ quyết định lượt nói
        xảy ra, và bỏ nó đi thì bài đo mất đúng đoạn đang cần đo.
        """
        size = self._frame_samples
        for index, start in enumerate(range(0, len(self._samples), size)):
            chunk = self._samples[start : start + size]
            if len(chunk) < size:
                padded = np.zeros(size, dtype=np.float32)
                padded[: len(chunk)] = chunk
                padded.flags.writeable = False
                chunk = padded
            yield FeatureFrame(
                index=index,
                start_s=index * self._duration_s,
                duration_s=self._duration_s,
                samples=chunk,
            )
