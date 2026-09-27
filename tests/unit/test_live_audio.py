"""Tầng audio sống, thử không cần micro: bộ đệm vòng, nguồn khung sống với duplex giả, AEC."""

import numpy as np
import pytest

from turnwise.audio.aec import EchoCanceller
from turnwise.audio.ring_buffer import RingBuffer
from turnwise.audio.source import LiveFrameSource
from turnwise.config import AudioConfig, load_settings


def test_ring_buffer_wraps_around_without_losing_order() -> None:
    ring = RingBuffer(5)
    out = np.zeros(3, np.float32)
    assert ring.write(np.array([1, 2, 3], np.float32))
    assert ring.read_into(out) and list(out) == [1, 2, 3]
    assert ring.write(np.array([4, 5, 6, 7], np.float32))  # vắt qua mép mảng
    assert ring.read_into(out) and list(out) == [4, 5, 6]


def test_a_full_ring_drops_the_new_block_and_counts_it() -> None:
    ring = RingBuffer(4)
    assert ring.write(np.ones(3, np.float32))
    assert not ring.write(np.ones(2, np.float32))
    assert ring.overruns == 1 and ring.available == 3


def test_a_short_read_fills_nothing() -> None:
    ring = RingBuffer(8)
    ring.write(np.ones(2, np.float32))
    assert not ring.read_into(np.zeros(3, np.float32)) and ring.available == 2


def test_a_clear_request_empties_the_ring_at_the_next_read() -> None:
    ring = RingBuffer(8)
    ring.write(np.ones(6, np.float32))
    ring.request_clear()
    assert not ring.read_into(np.zeros(2, np.float32)) and ring.available == 0


class FakeDuplex:
    def __init__(self, audio: AudioConfig, seconds: float, bot_from_s: float) -> None:
        n = int(audio.sample_rate_hz * seconds)
        self.mic, self.far = RingBuffer(n), RingBuffer(n)
        self.mic.write((np.random.default_rng(0).standard_normal(n) * 0.1).astype(np.float32))
        far = np.zeros(n, np.float32)
        far[int(audio.sample_rate_hz * bot_from_s) :] = 0.3
        self.far.write(far)

    @property
    def bot_speaking(self) -> bool:
        return False


class Identity:
    def process(self, near: np.ndarray, far: np.ndarray) -> np.ndarray:
        return near


def test_live_frames_are_contiguous_and_flag_the_bot(audio: AudioConfig) -> None:
    source = LiveFrameSource(FakeDuplex(audio, 1.0, bot_from_s=0.5), Identity(), audio)
    frames = []
    for frame in source:
        frames.append(frame)
        if len(frames) == 50:
            source.stop()
    assert [f.index for f in frames] == list(range(50))
    assert len(frames[0].samples) == audio.sample_rate_hz * audio.feature_frame_ms // 1000
    assert not frames[0].bot_speaking and frames[-1].bot_speaking


def test_echo_canceller_keeps_the_frame_size() -> None:
    settings = load_settings()
    pytest.importorskip("aec_audio_processing")
    canceller = EchoCanceller(settings.audio, settings.echo_cancellation)
    n = settings.audio.sample_rate_hz * settings.audio.capture_frame_ms // 1000
    out = canceller.process(np.zeros(n, np.float32), np.zeros(n, np.float32))
    assert out.shape == (n,) and out.dtype == np.float32
