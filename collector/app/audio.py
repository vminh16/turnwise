"""Kiểm file wav và nhật ký phát trước khi lưu.

Kiểm ở server chứ không tin trình duyệt: một file sai tốc độ lấy mẫu hay một nhật ký chồng
nhau không làm gì hỏng ngay, nó chỉ lộ ra khi gán nhãn, lúc người thu đã về nhà. Các quy tắc
nhật ký trùng với `WavFrameSource` ở `src/turnwise/audio/source.py`, để file đã nhận ở đây
chắc chắn đọc được ở kia.
"""

from __future__ import annotations

import io
import wave
from typing import Any


class InvalidUpload(ValueError):
    """File hoặc nhật ký không đúng hợp đồng; thông điệp trả thẳng cho người thu."""


def check_wav(data: bytes, channels: int, sample_rate_hz: int) -> int:
    """Trả số khung mẫu; ném `InvalidUpload` nếu không phải PCM 16-bit đúng định dạng."""
    try:
        with wave.open(io.BytesIO(data)) as wav:
            got = (wav.getnchannels(), wav.getframerate(), wav.getsampwidth(), wav.getcomptype())
            frames = wav.getnframes()
    except (wave.Error, EOFError) as error:
        raise InvalidUpload(f"not a readable WAV file: {error}") from error
    if got != (channels, sample_rate_hz, 2, "NONE"):
        raise InvalidUpload(
            f"expected PCM16 WAV, {channels} channel(s) at {sample_rate_hz} Hz; "
            f"got {got[0]} channel(s) at {got[1]} Hz, {8 * got[2]}-bit, compression {got[3]}"
        )
    if frames == 0:
        raise InvalidUpload("WAV file has no samples")
    return frames


def check_playback(entries: Any, steps: int, frames: int) -> list[dict[str, Any]]:
    """Kiểm nhật ký phát: mỗi bước một lần, theo thứ tự, không chồng nhau, nằm trong file."""
    if not isinstance(entries, list) or not entries:
        raise InvalidUpload("playback log must be a non-empty list")
    checked: list[dict[str, Any]] = []
    previous_step = -1
    previous_end = 0
    for entry in entries:
        if not isinstance(entry, dict):
            raise InvalidUpload("playback entry must be an object")
        try:
            step = entry["step"]
            pressed = entry["pressed_sample"]
            start = entry["start_sample"]
            end = entry["end_sample"]
        except KeyError as error:
            raise InvalidUpload(f"playback entry missing {error}") from error
        if not all(isinstance(value, int) for value in (step, pressed, start, end)):
            raise InvalidUpload("playback step and sample positions must be integers")
        if not previous_step < step < steps:
            raise InvalidUpload(f"playback step {step} out of order or outside 0..{steps - 1}")
        if not 0 <= pressed <= start < end <= frames:
            raise InvalidUpload(
                f"step {step}: need 0 <= pressed <= start < end <= {frames}, "
                f"got {pressed}, {start}, {end}"
            )
        if start < previous_end:
            raise InvalidUpload(f"step {step} starts before the previous prompt ended")
        previous_step, previous_end = step, end
        checked.append(
            {"step": step, "pressed_sample": pressed, "start_sample": start, "end_sample": end}
        )
    return checked
