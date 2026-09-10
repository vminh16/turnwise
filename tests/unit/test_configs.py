"""Các bất biến của configs/ mà không file code nào được phép vi phạm."""

from pathlib import Path
from typing import Any

import pytest
import yaml

CONFIG_DIR = Path(__file__).resolve().parents[2] / "configs"


def load(name: str) -> dict[str, Any]:
    parsed: dict[str, Any] = yaml.safe_load((CONFIG_DIR / name).read_text(encoding="utf-8"))
    return parsed


@pytest.mark.parametrize("path", sorted(CONFIG_DIR.rglob("*.yaml")), ids=lambda p: p.name)
def test_every_config_parses(path: Path) -> None:
    assert isinstance(yaml.safe_load(path.read_text(encoding="utf-8")), dict)


def test_capture_frame_matches_what_the_echo_canceller_accepts() -> None:
    """WebRTC audio processing xử lý đúng 160 mẫu ở 16 kHz — đổi là AEC hỏng, R5 hỏng."""
    from aec_audio_processing import AudioProcessor

    audio = load("default.yaml")["audio"]
    processor = AudioProcessor()
    processor.set_stream_format(audio["sample_rate_hz"], audio["channels"])
    expected_ms = processor.get_frame_size() / audio["sample_rate_hz"] * 1000
    assert audio["capture_frame_ms"] == expected_ms


def test_feature_frame_is_a_whole_number_of_capture_frames() -> None:
    audio = load("default.yaml")["audio"]
    assert audio["feature_frame_ms"] % audio["capture_frame_ms"] == 0


def test_decision_thresholds_are_not_guessed() -> None:
    """SPEC §9.1: số đo phải do Giai đoạn 0 sinh ra, không điền sẵn."""
    decision = load("default.yaml")["turn"]["decision"]
    assert all(value is None for value in decision.values()), decision


def test_baseline_sweeps_rather_than_selects() -> None:
    """SPEC §9.3 quy tắc 2: baseline là một đường cong, không phải một điểm."""
    sweep = load("baseline/silence-threshold.yaml")["turn"]["silence_threshold_sweep_ms"]
    assert len(sweep) > 1
    assert sweep == sorted(set(sweep))


@pytest.mark.parametrize("overlay", ["deploy/local.yaml", "deploy/container.yaml"])
def test_overlays_only_override_keys_that_exist(overlay: str) -> None:
    """Một overlay đặt khoá lạ sẽ im lặng không có tác dụng — bắt ngay ở đây."""
    default = load("default.yaml")
    for section, values in load(overlay).items():
        assert section in default, f"{overlay}: section lạ {section!r}"
        assert set(values) <= set(default[section]), f"{overlay}: khoá lạ trong {section!r}"
