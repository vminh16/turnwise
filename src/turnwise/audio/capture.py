"""Một luồng song công PortAudio: micro vào, tiếng bot ra, cùng một callback.

Cùng một callback cho cả hai chiều là cách rẻ nhất để AEC có far-end thẳng hàng với
near-end: khối bot vừa ghi ra loa và khối micro vừa thu thuộc cùng một chu kỳ 10 ms.

Callback chỉ chép khối vào bộ đệm vòng (`.claude/rules/audio.md`): không suy luận, không cấp
phát, không log, không khoá, không ném lỗi.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from turnwise.audio.ring_buffer import RingBuffer
from turnwise.config import AudioConfig

logger = logging.getLogger(__name__)


class DuplexAudio:
    """Micro -> `mic`, `speaker` -> loa, và bản sao khối vừa phát -> `far` cho AEC."""

    def __init__(self, audio: AudioConfig) -> None:
        self._audio = audio
        self.block = audio.sample_rate_hz * audio.capture_frame_ms // 1000
        ring = audio.sample_rate_hz * audio.ring_buffer_ms // 1000
        self.mic = RingBuffer(ring)
        self.far = RingBuffer(ring)
        self.speaker = RingBuffer(audio.sample_rate_hz * audio.playback_buffer_s)
        self._out = np.zeros(self.block, dtype=np.float32)
        self._stream: Any = None
        self.status_flags = 0
        """Số lần PortAudio báo tràn hoặc thiếu mẫu. Đếm, không log trong callback."""

    @property
    def bot_speaking(self) -> bool:
        return self.speaker.available > 0

    def stop_bot(self) -> None:
        """Bot im từ khối kế tiếp: bị ngắt lời thì dừng ngay (SPEC R3)."""
        self.speaker.request_clear()

    def _callback(self, indata: Any, outdata: Any, frames: int, time: Any, status: Any) -> None:
        if status:
            self.status_flags += 1
        if not self.speaker.read_into(self._out):
            self._out[:] = 0.0
        outdata[:, 0] = self._out
        self.far.write(self._out)
        self.mic.write(indata[:, 0])

    def start(self) -> None:
        import sounddevice as sd

        extra = None
        if self._audio.preferred_host_api == "WASAPI":
            # Chế độ chia sẻ của WASAPI không tự đổi tần số; bật chuyển đổi để mở được 16 kHz.
            extra = sd.WasapiSettings(auto_convert=True)
        self._stream = sd.Stream(
            samplerate=self._audio.sample_rate_hz,
            blocksize=self.block,
            channels=1,
            dtype="float32",
            callback=self._callback,
            device=(self._audio.input_device, self._audio.output_device),
            extra_settings=extra,
        )
        self._stream.start()
        logger.info(
            "audio stream open at %d Hz, %d-sample blocks", self._audio.sample_rate_hz, self.block
        )

    def close(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
