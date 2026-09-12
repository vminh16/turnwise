"""Bất biến của seam `audio/source.py`: khung phải đều, liên tục và chỉ đọc."""

import math
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from turnwise.audio.source import FrameSource, WavFrameSource
from turnwise.config import AudioConfig, load_settings


@pytest.fixture
def audio() -> AudioConfig:
    return load_settings().audio


def write_wav(path: Path, samples: int, sample_rate_hz: int = 16000, channels: int = 1) -> Path:
    rng = np.random.default_rng(0)
    data = rng.standard_normal((samples, channels)).astype(np.float32) * 0.1
    sf.write(path, data, sample_rate_hz, subtype="PCM_16")
    return path


def test_wav_source_satisfies_the_seam(tmp_path: Path, audio: AudioConfig) -> None:
    source = WavFrameSource(write_wav(tmp_path / "a.wav", 1600), audio)
    assert isinstance(source, FrameSource)


@pytest.mark.parametrize("samples", [0, 1, 319, 320, 321, 16000])
def test_frame_count_is_the_file_rounded_up(
    tmp_path: Path, audio: AudioConfig, samples: int
) -> None:
    """Khung cuối được đệm chứ không bị bỏ, nên số khung làm tròn lên."""
    per_frame = audio.sample_rate_hz * audio.feature_frame_ms // 1000
    source = WavFrameSource(write_wav(tmp_path / "a.wav", samples), audio)
    assert len(list(source)) == math.ceil(samples / per_frame)


def test_frames_are_contiguous_and_evenly_spaced(tmp_path: Path, audio: AudioConfig) -> None:
    frames = list(WavFrameSource(write_wav(tmp_path / "a.wav", 16000), audio))
    assert [frame.index for frame in frames] == list(range(len(frames)))
    for frame in frames:
        assert frame.duration_s == pytest.approx(audio.feature_frame_ms / 1000)
        assert frame.start_s == pytest.approx(frame.index * frame.duration_s)


def test_every_frame_is_mono_float32_of_one_frame_length(
    tmp_path: Path, audio: AudioConfig
) -> None:
    per_frame = audio.sample_rate_hz * audio.feature_frame_ms // 1000
    for frame in WavFrameSource(write_wav(tmp_path / "a.wav", 1000), audio):
        assert frame.samples.dtype == np.float32
        assert frame.samples.shape == (per_frame,)


def test_samples_are_read_only(tmp_path: Path, audio: AudioConfig) -> None:
    """types.py: `samples` chỉ được đọc; ai muốn giữ lại phải tự sao chép."""
    for frame in WavFrameSource(write_wav(tmp_path / "a.wav", 400), audio):
        with pytest.raises(ValueError):
            frame.samples[0] = 1.0


def test_frame_length_comes_from_config_not_from_a_literal(tmp_path: Path) -> None:
    audio = load_settings().audio.model_copy(update={"feature_frame_ms": 40})
    frames = list(WavFrameSource(write_wav(tmp_path / "a.wav", 1600), audio))
    assert len(frames) == math.ceil(1600 / (16000 * 40 // 1000))
    assert frames[0].samples.shape == (640,)


def test_no_f0_yet(tmp_path: Path, audio: AudioConfig) -> None:
    """Ước lượng F0 là việc của features.py, không phải của nguồn khung."""
    frames = list(WavFrameSource(write_wav(tmp_path / "a.wav", 640), audio))
    assert all(frame.f0_hz is None for frame in frames)


def test_wrong_sample_rate_is_refused(tmp_path: Path, audio: AudioConfig) -> None:
    path = write_wav(tmp_path / "a.wav", 8000, sample_rate_hz=8000)
    with pytest.raises(ValueError, match="8000 Hz"):
        WavFrameSource(path, audio)


def test_multi_channel_file_is_refused(tmp_path: Path, audio: AudioConfig) -> None:
    path = write_wav(tmp_path / "a.wav", 1600, channels=2)
    with pytest.raises(ValueError, match="2 kênh"):
        WavFrameSource(path, audio)


def test_the_padded_tail_is_reported(tmp_path: Path, audio: AudioConfig) -> None:
    """Khung cuối nói thật nó có bao nhiêu mẫu đệm; các khung đầy thì không có mẫu nào."""
    per_frame = audio.sample_rate_hz * audio.feature_frame_ms // 1000
    frames = list(WavFrameSource(write_wav(tmp_path / "a.wav", per_frame + 10), audio))

    assert [frame.padded_samples for frame in frames] == [0, per_frame - 10]
