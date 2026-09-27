"""Ngân sách xử lý mỗi khung, đo trên đường chạy offline.

ĐÂY KHÔNG PHẢI ĐỘ TRỄ THẬT. `SPEC.md` §9.3 quy tắc 4 và `.claude/rules/audio.md`
nói rõ: thời gian đo khi đọc file bỏ qua đệm audio, thời gian TTS khởi động và jitter
mạng. Cái đo được ở đây là **chi phí tính toán mỗi khung** — điều kiện cần để hệ
thống theo kịp luồng audio, không phải điều kiện đủ. Số báo cáo được thuộc Giai đoạn 4,
khi có micro thật.

Cần vậy vì `AGENTS.md` bắt chạy `uv run pytest -m latency` cho mọi thay đổi dưới
`audio/` và `turn/`. Trước pha này marker đó thu 0 test: lệnh chạy xanh mà không kiểm
gì, tức là một cái bẫy chứ không phải một cái cổng.

Số đo phụ thuộc máy. Ngưỡng lấy từ `configs/`, không đặt trong code, và không được
nới ngưỡng để test xanh — ngân sách sai thì đó là một ADR (`.claude/rules/audio.md`).
"""

import time
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest

from turnwise.audio.source import WavFrameSource
from turnwise.config import AudioConfig, GateConfig, LatencyConfig, load_settings
from turnwise.turn.deciders.silence_threshold import SilenceThresholdDecider

GATE = GateConfig(floor_dbfs=-45.0, margin_db=12.0, merge_ms=180)

pytestmark = pytest.mark.latency

WARMUP_FRAMES = 20
"""Bỏ qua vài khung đầu: lần gọi đầu tiên còn trả tiền cho import, cache và cấp phát."""


WavWriter = Callable[..., Path]
"""Fixture `write_wav` ở `tests/conftest.py`."""


@pytest.fixture(scope="module")
def latency() -> LatencyConfig:
    return load_settings().latency


def budget_per_feature_frame_ms(audio: AudioConfig, latency: LatencyConfig) -> float:
    """Ngân sách cho một khung đặc trưng, suy từ ngân sách khung capture trong `configs/`.

    `budget_per_frame_ms` đặt trên khung capture 10ms, tức hệ số thời gian thực
    `budget / capture_frame_ms`. Khung đặc trưng dài gấp đôi nên ngân sách cũng gấp
    đôi. Viết ra công thức thay vì một con số để đổi `feature_frame_ms` trong config
    là ngân sách đi theo, không phải sửa test.
    """
    realtime_factor = latency.budget_per_frame_ms / audio.capture_frame_ms
    return audio.feature_frame_ms * realtime_factor


def median_ms(durations: list[float]) -> float:
    return float(np.median(durations)) * 1000


def test_b1_decides_inside_the_per_frame_budget(
    tmp_path: Path, audio: AudioConfig, latency: LatencyConfig, write_wav: WavWriter
) -> None:
    """`decide()` chạy mỗi khung trên thread tiêu thụ; chi phí của nó nằm trong ngân sách."""
    decider = SilenceThresholdDecider(500, GATE)
    frames = list(
        WavFrameSource(
            write_wav(tmp_path / "a.wav", audio.sample_rate_hz * 10, amplitude=0.2), audio
        )
    )

    durations = []
    for index, frame in enumerate(frames):
        start = time.perf_counter()
        decider.decide(frame)
        if index >= WARMUP_FRAMES:
            durations.append(time.perf_counter() - start)

    budget_ms = budget_per_feature_frame_ms(audio, latency)
    assert median_ms(durations) < budget_ms, (
        f"B1 tốn {median_ms(durations):.3f}ms/khung, ngân sách {budget_ms:.3f}ms"
    )


def test_the_frame_source_keeps_up_with_its_own_frames(
    tmp_path: Path, audio: AudioConfig, latency: LatencyConfig, write_wav: WavWriter
) -> None:
    """Bộ phát khung phải rẻ hơn nhiều so với ngân sách: nó chỉ cắt lát, không tính gì."""
    source = WavFrameSource(
        write_wav(tmp_path / "a.wav", audio.sample_rate_hz * 10, amplitude=0.2), audio
    )

    durations = []
    iterator = iter(source)
    for index in range(WARMUP_FRAMES + 400):
        start = time.perf_counter()
        next(iterator)
        if index >= WARMUP_FRAMES:
            durations.append(time.perf_counter() - start)

    budget_ms = budget_per_feature_frame_ms(audio, latency)
    assert median_ms(durations) < budget_ms


def test_the_whole_offline_path_runs_faster_than_real_time(
    tmp_path: Path, audio: AudioConfig, write_wav: WavWriter
) -> None:
    """Phát lại 10 giây audio phải tốn ít hơn 10 giây, nếu không bộ kịch bản vô dụng.

    Đây là phép kiểm thô nhất và cũng là phép duy nhất ở đây nói được điều gì đó về
    hệ thống thay vì về một hàm: nếu đường chạy offline đã không kịp thời gian thực
    thì đường chạy sống chắc chắn không kịp.
    """
    seconds = 10.0
    decider = SilenceThresholdDecider(500, GATE)
    path = write_wav(tmp_path / "a.wav", int(audio.sample_rate_hz * seconds), amplitude=0.2)

    start = time.perf_counter()
    for frame in WavFrameSource(path, audio):
        decider.decide(frame)
    elapsed = time.perf_counter() - start

    assert elapsed < seconds, f"phát lại {seconds}s audio tốn {elapsed:.3f}s"


def test_echo_cancellation_fits_the_capture_frame_budget(
    audio: AudioConfig, latency: LatencyConfig
) -> None:
    """AEC chạy một lần mỗi khung capture trên luồng tiêu thụ, trước mọi decider."""
    from turnwise.audio.aec import EchoCanceller

    settings = load_settings()
    canceller = EchoCanceller(audio, settings.echo_cancellation)
    n = audio.sample_rate_hz * audio.capture_frame_ms // 1000
    rng = np.random.default_rng(0)
    near = (rng.standard_normal(n) * 0.1).astype(np.float32)
    far = (rng.standard_normal(n) * 0.1).astype(np.float32)
    durations = []
    for _ in range(300):
        start = time.perf_counter()
        canceller.process(near, far)
        durations.append(time.perf_counter() - start)
    assert median_ms(durations) < latency.budget_per_frame_ms
