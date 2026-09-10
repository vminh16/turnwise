"""Ba lớp cấu hình phải gộp đúng thứ tự, và khoá lạ phải nổ."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from turnwise.config import DEFAULT_CONFIG_PATH, load_settings


def test_default_config_loads() -> None:
    settings = load_settings()
    assert settings.audio.sample_rate_hz == 16000
    assert settings.turn.decider == "fused"
    assert settings.logging.level == "INFO"


def test_measured_thresholds_stay_empty() -> None:
    """SPEC §9.1: số đo do Giai đoạn 0 sinh ra, không điền sẵn."""
    decision = load_settings().turn.decision
    assert decision.take_threshold is None
    assert decision.backchannel_threshold is None


def test_overlay_merges_without_dropping_siblings() -> None:
    settings = load_settings("configs/baseline/silence-threshold.yaml")
    assert settings.turn.decider == "silence_threshold"
    assert settings.turn.silence_threshold_sweep_ms is not None
    assert len(settings.turn.silence_threshold_sweep_ms) > 1
    # Overlay chỉ nêu `turn`, nên `audio` phải còn nguyên từ default.yaml.
    assert settings.audio.sample_rate_hz == 16000
    assert settings.audio.capture_frame_ms == 10


def test_env_overrides_yaml(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TURNWISE_LOG_LEVEL", "DEBUG")
    assert load_settings().logging.level == "DEBUG"


def test_empty_env_device_means_operating_system_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TURNWISE_INPUT_DEVICE", "")
    assert load_settings().audio.input_device is None


def test_config_path_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TURNWISE_CONFIG", "configs/baseline/silence-threshold.yaml")
    assert load_settings().turn.decider == "silence_threshold"


def test_unknown_key_is_rejected(tmp_path: Path) -> None:
    overlay = tmp_path / "typo.yaml"
    overlay.write_text("turn:\n  decidr: fused\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        load_settings(overlay)


def test_feature_frame_must_be_whole_capture_frames(tmp_path: Path) -> None:
    overlay = tmp_path / "skewed.yaml"
    overlay.write_text("audio:\n  feature_frame_ms: 25\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        load_settings(overlay)


def test_default_config_path_points_at_the_committed_file() -> None:
    assert DEFAULT_CONFIG_PATH.is_file()


def test_only_the_config_module_reads_yaml_or_the_environment() -> None:
    """AGENTS.md: cấu hình vào chương trình qua đúng một cửa.

    Một module đọc thẳng YAML hay `os.environ` sẽ chạy đúng trong test của chính nó,
    và lặng lẽ bỏ qua overlay lẫn biến môi trường khi chạy thật.
    """
    package = Path(__file__).resolve().parents[2] / "src" / "turnwise"
    tokens = ("os.environ", "getenv", "import yaml", "dotenv")
    offenders = sorted(
        path.relative_to(package).as_posix()
        for path in package.rglob("*.py")
        if path.name != "config.py"
        and any(token in path.read_text(encoding="utf-8") for token in tokens)
    )
    assert not offenders, offenders
