"""File thu hai kênh của Giai đoạn 1: tiếng khách vào khung, tiếng bot chỉ thành một cờ.

Hai bất biến đáng giữ nhất ở đây. Một: không mẫu nào của kênh bot lọt vào `samples`, vì
scorer không được nghe tiếng bot (`types.py`, SPEC R5). Hai: cờ `bot_speaking` đi theo
log phát chứ không theo năng lượng, vì trong một chỗ ngắt hơi giữa câu bot vẫn giữ lượt.
"""

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from turnwise.audio.source import WavFrameSource
from turnwise.config import AudioConfig


def frame_samples(audio: AudioConfig) -> int:
    return audio.sample_rate_hz * audio.feature_frame_ms // 1000


def write_stereo(path: Path, audio: AudioConfig, caller: np.ndarray, bot: np.ndarray) -> Path:
    """Ghi file theo bố cục trong config: kênh khách ở `recording_caller_channel`."""
    data = np.zeros((len(caller), 2), dtype=np.float32)
    data[:, audio.recording_caller_channel] = caller
    data[:, 1 - audio.recording_caller_channel] = bot
    sf.write(path, data, audio.sample_rate_hz, subtype="FLOAT")
    return path


def test_a_mono_file_never_raises_the_bot_flag(tmp_path: Path, audio: AudioConfig) -> None:
    """Năm kịch bản và đường cong B1 của Giai đoạn 0 phải chạy y như cũ."""
    path = tmp_path / "mono.wav"
    sf.write(path, np.full(frame_samples(audio) * 3, 0.1, dtype=np.float32), audio.sample_rate_hz)
    assert [frame.bot_speaking for frame in WavFrameSource(path, audio)] == [False] * 3


def test_caller_samples_never_contain_the_bot_channel(tmp_path: Path, audio: AudioConfig) -> None:
    n = frame_samples(audio) * 4
    caller = np.full(n, 0.25, dtype=np.float32)
    bot = np.full(n, -0.75, dtype=np.float32)
    path = write_stereo(tmp_path / "s.wav", audio, caller, bot)

    frames = list(WavFrameSource(path, audio, bot_intervals=[(0.0, 0.01)]))

    assert all(np.all(frame.samples == np.float32(0.25)) for frame in frames)


def test_the_caller_channel_comes_from_config(tmp_path: Path, audio: AudioConfig) -> None:
    swapped = audio.model_copy(update={"recording_caller_channel": 1})
    n = frame_samples(audio) * 2
    path = write_stereo(
        tmp_path / "s.wav",
        swapped,
        np.full(n, 0.5, dtype=np.float32),
        np.zeros(n, dtype=np.float32),
    )

    frames = list(WavFrameSource(path, swapped, bot_intervals=[]))

    assert all(np.all(frame.samples == np.float32(0.5)) for frame in frames)


def test_the_flag_follows_the_playback_log_frame_by_frame(
    tmp_path: Path, audio: AudioConfig
) -> None:
    size = frame_samples(audio)
    frame_s = audio.feature_frame_ms / 1000
    n = size * 10
    path = write_stereo(tmp_path / "s.wav", audio, np.zeros(n, np.float32), np.zeros(n, np.float32))

    # Bot phát từ đầu khung 2 tới hết khung 4, rồi từ đầu khung 7 tới hết khung 7.
    intervals = [(2 * frame_s, 5 * frame_s), (7 * frame_s, 8 * frame_s)]
    flags = [frame.bot_speaking for frame in WavFrameSource(path, audio, bot_intervals=intervals)]

    assert flags == [False, False, True, True, True, False, False, True, False, False]


def test_the_flag_stays_up_through_a_breath_pause_inside_a_prompt(
    tmp_path: Path, audio: AudioConfig
) -> None:
    """Kênh bot im giữa câu (dấu `/` trong kịch bản) nhưng bot vẫn đang giữ lượt."""
    size = frame_samples(audio)
    n = size * 6
    bot = np.full(n, 0.3, dtype=np.float32)
    bot[size * 2 : size * 4] = 0.0  # chỗ ngắt hơi, im tuyệt đối
    path = write_stereo(tmp_path / "s.wav", audio, np.zeros(n, np.float32), bot)

    duration_s = n / audio.sample_rate_hz
    frames = list(WavFrameSource(path, audio, bot_intervals=[(0.0, duration_s)]))

    assert all(frame.bot_speaking for frame in frames)


def test_a_prompt_starting_mid_frame_marks_that_frame(tmp_path: Path, audio: AudioConfig) -> None:
    """Có tiếng bot ở bất kỳ phần nào của khung thì tiếng khách trong khung đó có thể là nói đè."""
    size = frame_samples(audio)
    frame_s = audio.feature_frame_ms / 1000
    n = size * 4
    path = write_stereo(tmp_path / "s.wav", audio, np.zeros(n, np.float32), np.zeros(n, np.float32))

    intervals = [(1.5 * frame_s, 2 * frame_s)]
    flags = [frame.bot_speaking for frame in WavFrameSource(path, audio, bot_intervals=intervals)]

    assert flags == [False, True, False, False]


def test_a_two_channel_file_without_a_playback_log_is_refused(
    tmp_path: Path, audio: AudioConfig
) -> None:
    """Thiếu log mà vẫn chạy thì cờ luôn tắt, và mọi tiếng "dạ" đệm trông như một câu trả lời."""
    n = frame_samples(audio)
    path = write_stereo(tmp_path / "s.wav", audio, np.zeros(n, np.float32), np.zeros(n, np.float32))
    with pytest.raises(ValueError, match="bot_intervals"):
        WavFrameSource(path, audio)


def test_a_three_channel_file_is_refused(tmp_path: Path, audio: AudioConfig) -> None:
    path = tmp_path / "t.wav"
    sf.write(path, np.zeros((1600, 3), dtype=np.float32), audio.sample_rate_hz)
    with pytest.raises(ValueError, match="3 kênh"):
        WavFrameSource(path, audio, bot_intervals=[])


@pytest.mark.parametrize(
    "intervals",
    [
        [(0.10, 0.10)],  # rỗng
        [(0.20, 0.10)],  # ngược
        [(-0.01, 0.10)],  # âm
        [(0.00, 0.10), (0.05, 0.20)],  # chồng nhau: bot không phát hai câu một lúc
    ],
)
def test_a_malformed_playback_log_is_refused(
    tmp_path: Path, audio: AudioConfig, intervals: list[tuple[float, float]]
) -> None:
    n = frame_samples(audio) * 20
    path = write_stereo(tmp_path / "s.wav", audio, np.zeros(n, np.float32), np.zeros(n, np.float32))
    with pytest.raises(ValueError, match="bot_intervals"):
        WavFrameSource(path, audio, bot_intervals=intervals)
