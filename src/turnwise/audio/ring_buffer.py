"""Bộ đệm vòng float32 cấp phát sẵn: một luồng ghi (callback PortAudio), một luồng đọc.

Luật của `.claude/rules/audio.md`: cố định kích thước, không bao giờ lớn thêm; đầy thì **bỏ
khung mới và đếm** chứ không chặn callback. Một khung mất tốt hơn một luồng âm thanh đứng.

Chỉ số đọc và ghi là số nguyên đếm tăng dần, không quay vòng; vị trí trong mảng là phần dư.
Mỗi chỉ số chỉ một luồng ghi, và phép gán số nguyên trong CPython là nguyên tử, nên một
người ghi và một người đọc không cần khoá — callback không được giữ khoá.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


class RingBuffer:
    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError(f"capacity must be positive, got {capacity}")
        self._data = np.zeros(capacity, dtype=np.float32)
        self._capacity = capacity
        self._written = 0
        self._read = 0
        self._clear_requested = False
        self.overruns = 0
        """Số lần ghi bị bỏ vì đầy. Báo qua telemetry, không im lặng nuốt."""

    @property
    def available(self) -> int:
        return self._written - self._read

    def write(self, samples: NDArray[np.float32]) -> bool:
        """Ghi cả khối, hoặc bỏ cả khối nếu không đủ chỗ. An toàn trong callback: không cấp phát."""
        n = len(samples)
        if n > self._capacity - self.available:
            self.overruns += 1
            return False
        start = self._written % self._capacity
        first = min(n, self._capacity - start)
        self._data[start : start + first] = samples[:first]
        self._data[: n - first] = samples[first:]
        self._written += n
        return True

    def read_into(self, out: NDArray[np.float32]) -> bool:
        """Điền đúng `len(out)` mẫu, hoặc không điền gì nếu chưa đủ."""
        if self._clear_requested:
            self._clear_requested = False
            self._read = self._written
        n = len(out)
        if n > self.available:
            return False
        start = self._read % self._capacity
        first = min(n, self._capacity - start)
        out[:first] = self._data[start : start + first]
        out[first:] = self._data[: n - first]
        self._read += n
        return True

    def request_clear(self) -> None:
        """Bỏ mọi mẫu chưa đọc, ở lần đọc kế tiếp.

        Luồng nào cũng gọi được: chỉ bật một cờ, và chính luồng đọc dời chỉ số đọc. Dùng khi
        bot bị ngắt lời — bộ phát (luồng đọc là callback) phải im từ khối kế tiếp.
        """
        self._clear_requested = True
