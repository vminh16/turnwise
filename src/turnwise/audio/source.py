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
from collections.abc import Iterator, Sequence
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

    def __init__(
        self,
        path: Path | str,
        audio: AudioConfig,
        bot_intervals: Sequence[tuple[float, float]] | None = None,
    ) -> None:
        """Nạp file.

        File một kênh là tiếng khách, như bộ kịch bản của Giai đoạn 0. File hai kênh là
        bản thu Giai đoạn 1: kênh `audio.recording_caller_channel` là tiếng khách, kênh
        còn lại là tiếng bot, và **bắt buộc** kèm `bot_intervals` — các khoảng
        `(start_s, end_s)` bot phát một câu, lấy từ log phát. Kênh bot không vào khung.
        """
        if audio.channels != 1:
            raise ValueError(
                f"WavFrameSource chỉ phát khung mono, còn audio.channels={audio.channels}."
            )

        self._path = Path(path)
        data, sample_rate_hz = sf.read(self._path, dtype="float32", always_2d=True)

        if sample_rate_hz != audio.sample_rate_hz:
            raise ValueError(
                f"{self._path} lấy mẫu ở {sample_rate_hz} Hz, còn cấu hình đòi "
                f"{audio.sample_rate_hz} Hz. Nguồn này không lấy mẫu lại."
            )

        file_channels = data.shape[1]
        if file_channels == 1:
            caller = data[:, 0]
        elif file_channels == 2:
            if bot_intervals is None:
                raise ValueError(
                    f"{self._path} có 2 kênh (khách + bot) nhưng thiếu `bot_intervals`. "
                    "Không có log phát thì cờ bot_speaking luôn tắt, và mọi tiếng đệm "
                    "trông như một câu trả lời."
                )
            caller = data[:, audio.recording_caller_channel]
        else:
            raise ValueError(
                f"{self._path} có {file_channels} kênh; nguồn này đọc 1 kênh (khách) "
                "hoặc 2 kênh (khách + bot)."
            )

        self._samples: np.ndarray = np.ascontiguousarray(caller, dtype=np.float32)
        self._samples.flags.writeable = False
        self._frame_samples = audio.sample_rate_hz * audio.feature_frame_ms // 1000
        self._duration_s = audio.feature_frame_ms / 1000
        self._bot_frames = self._frames_with_bot(
            bot_intervals or (), audio.sample_rate_hz, len(self._samples)
        )

        logger.debug(
            "%s: %d samples at %d Hz, %d samples per frame",
            self._path.name,
            len(self._samples),
            sample_rate_hz,
            self._frame_samples,
        )

    def _frames_with_bot(
        self,
        intervals: Sequence[tuple[float, float]],
        sample_rate_hz: int,
        total_samples: int,
    ) -> frozenset[int]:
        """Chỉ số các khung có tiếng bot ở bất kỳ phần nào.

        Tính trên chỉ số mẫu nguyên chứ không trên giây, cùng lý do như B1: cộng số thực
        theo khung thì ranh giới trôi dần (`0.02 * 10 != 0.2`). Khoảng là nửa mở
        `[start, end)`, nên một câu kết thúc đúng mép khung không bật cờ khung sau.
        """
        size = self._frame_samples
        frame_count = -(-total_samples // size)
        marked: set[int] = set()
        previous_end = 0
        for start_s, end_s in sorted(intervals):
            start = round(start_s * sample_rate_hz)
            end = round(end_s * sample_rate_hz)
            if start < 0 or end <= start:
                raise ValueError(f"bot_intervals: khoảng ({start_s}, {end_s}) rỗng, ngược hoặc âm")
            if start < previous_end:
                raise ValueError(
                    f"bot_intervals: khoảng bắt đầu ở {start_s}s chồng lên khoảng trước; "
                    "bot không phát hai câu cùng lúc, log phát đang sai"
                )
            previous_end = end
            last = min((end - 1) // size, frame_count - 1)
            marked.update(range(start // size, last + 1))
        return frozenset(marked)

    def __iter__(self) -> Iterator[FeatureFrame]:
        """Phát lần lượt từng khung, khung cuối được đệm không cho đủ độ dài.

        Đệm chứ không cắt bỏ: phần đuôi của một phát ngôn là chỗ quyết định lượt nói
        xảy ra, và bỏ nó đi thì bài đo mất đúng đoạn đang cần đo.

        Khung đệm mang theo `padded_samples` để người tiêu thụ biết phần nào là tín
        hiệu thật. Giữ độ dài cố định mà vẫn nói thật về phần đệm: bộ đệm cố định là
        thứ `.claude/rules/audio.md` đòi, còn năng lượng thì phải tính trên phần thật.
        """
        size = self._frame_samples
        for index, start in enumerate(range(0, len(self._samples), size)):
            chunk = self._samples[start : start + size]
            padded_samples = size - len(chunk)
            if padded_samples:
                padded = np.zeros(size, dtype=np.float32)
                padded[: len(chunk)] = chunk
                padded.flags.writeable = False
                chunk = padded
            yield FeatureFrame(
                index=index,
                start_s=index * self._duration_s,
                duration_s=self._duration_s,
                samples=chunk,
                padded_samples=padded_samples,
                bot_speaking=index in self._bot_frames,
            )
