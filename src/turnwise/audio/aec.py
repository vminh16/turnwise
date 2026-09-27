"""Khử tiếng bot khỏi micro, qua WebRTC audio processing (`aec_audio_processing`).

SPEC R5 — bot không bao giờ nhận tiếng mình là ngắt lời — phụ thuộc hoàn toàn vào tầng này
(`.claude/rules/audio.md`). AEC cần cả hai luồng, thẳng hàng theo thời gian: tiếng micro
(near-end) và chính tín hiệu bot vừa phát (far-end, còn gọi là reverse stream). Mỗi lần xử lý
đúng 10 ms; kích thước đó là ràng buộc của thư viện, ghi ở `configs/default.yaml`.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from turnwise.config import AudioConfig, EchoCancellationConfig

PCM16_SCALE = 32767.0


class EchoCanceller:
    def __init__(self, audio: AudioConfig, config: EchoCancellationConfig) -> None:
        import aec_audio_processing

        self._frame = audio.sample_rate_hz * audio.capture_frame_ms // 1000
        self._enabled = config.enabled
        self._ap = aec_audio_processing.AudioProcessor(
            enable_aec=config.enabled,
            enable_ns=config.noise_suppression,
            ns_level=config.noise_suppression_level,
            enable_agc=config.automatic_gain_control,
        )
        self._ap.set_stream_format(audio.sample_rate_hz, 1)
        self._ap.set_reverse_stream_format(audio.sample_rate_hz, 1)
        if self._ap.get_frame_size() != self._frame:
            raise ValueError(
                f"AEC processes {self._ap.get_frame_size()} samples, config gives {self._frame}; "
                "see audio.capture_frame_ms in configs/default.yaml"
            )

    def process(self, near: NDArray[np.float32], far: NDArray[np.float32]) -> NDArray[np.float32]:
        """Một khung capture: tiếng micro trừ tiếng bot. Luồng tiêu thụ, không trong callback."""
        if not self._enabled:
            return near
        self._ap.process_reverse_stream(_pcm16(far))
        cleaned = np.frombuffer(self._ap.process_stream(_pcm16(near)), dtype=np.int16)
        return (cleaned.astype(np.float32) / PCM16_SCALE).astype(np.float32)


def _pcm16(samples: NDArray[np.float32]) -> bytes:
    return (np.clip(samples, -1.0, 1.0) * PCM16_SCALE).astype(np.int16).tobytes()
