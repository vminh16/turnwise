"""ASR và TTS của đường chạy sống. Mỏng: chỉ nạp mô hình và đổi định dạng.

Cả hai là hằng số của thí nghiệm (SPEC R8): mọi decider chạy trên cùng ASR và cùng giọng bot,
chọn ở `speech` trong `configs/default.yaml`. Nạp mô hình tốn vài giây, nên chỉ làm một lần lúc
khởi động, không bao giờ trong vòng lặp khung.
"""

from __future__ import annotations

import logging
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from turnwise.config import SpeechConfig, export_model_cache

logger = logging.getLogger(__name__)


class Asr(Protocol):
    def __call__(self, audio: NDArray[np.float32]) -> str: ...


class Tts(Protocol):
    def __call__(self, text: str) -> NDArray[np.float32]: ...


def load_asr(config: SpeechConfig) -> Asr:
    from turnwise.turn.deciders.semantic_onnx import WhisperTranscriber

    return WhisperTranscriber(str(config.asr_model_dir), config.asr_beam_size)


class VieneuTts:
    """Chữ -> tiếng bot ở tần số của đường chạy sống.

    VieNeu sinh ở tần số của nó (48 kHz trong container); lấy mẫu lại xuống `rate_hz` ngay ở
    đây để bộ phát và AEC chỉ thấy một tần số.
    """

    def __init__(self, config: SpeechConfig, rate_hz: int) -> None:
        export_model_cache(config)
        from vieneu import Vieneu

        self._tts = Vieneu(mode=config.tts_model, precision=config.tts_precision)
        self._voice = config.tts_voice
        self._rate = rate_hz
        self._said: dict[str, NDArray[np.float32]] = {}
        """Câu đã sinh. Phần lớn lời bot là câu cố định (lời chào, câu hỏi, lời chào kết thúc);
        sinh lại mỗi lần tốn khoảng 2 giây trên laptop dự án (đo 2026-09-27)."""
        logger.info(
            "TTS ready: %s, %s, %d Hz",
            config.tts_model,
            config.tts_precision,
            self._tts.sample_rate,
        )

    def __call__(self, text: str) -> NDArray[np.float32]:
        if text not in self._said:
            self._said[text] = self._synthesise(text)
        return self._said[text]

    def _synthesise(self, text: str) -> NDArray[np.float32]:
        from math import gcd

        from scipy.signal import resample_poly

        audio = np.asarray(self._tts.infer(text, voice=self._voice), dtype=np.float32)
        source = int(self._tts.sample_rate)
        if source != self._rate:
            step = gcd(source, self._rate)
            audio = resample_poly(audio, self._rate // step, source // step).astype(np.float32)
        return np.clip(audio, -1.0, 1.0)
