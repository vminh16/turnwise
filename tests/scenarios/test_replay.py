"""Phát lại năm kịch bản của SPEC §10 qua B1. Không cần micro, và phải tất định."""

from pathlib import Path

import pytest

from evaluation.scenario import Scenario, load_all, replay
from turnwise.config import TelemetryConfig, load_settings
from turnwise.telemetry.collector import TelemetryCollector
from turnwise.turn.deciders.silence_threshold import SilenceThresholdDecider
from turnwise.types import TurnOutcome

pytestmark = pytest.mark.scenario

SPEC_TESTS = 5


@pytest.fixture(scope="module")
def scenarios() -> list[Scenario]:
    return load_all()


@pytest.fixture
def b1() -> SilenceThresholdDecider:
    turn = load_settings("configs/baseline/silence-threshold.yaml").turn
    assert turn.silence_threshold_sweep_ms is not None
    assert turn.silence_floor_dbfs is not None
    return SilenceThresholdDecider(turn.silence_threshold_sweep_ms[0], turn.silence_floor_dbfs)


def test_all_five_spec_tests_have_a_scenario(scenarios: list[Scenario]) -> None:
    assert len(scenarios) == SPEC_TESTS
    assert len({scenario.name for scenario in scenarios}) == SPEC_TESTS
    assert len({scenario.spec for scenario in scenarios}) == SPEC_TESTS


def test_every_scenario_replays_through_the_file_source(
    scenarios: list[Scenario], b1: SilenceThresholdDecider, tmp_path: Path
) -> None:
    audio = load_settings().audio
    frame_ms = audio.feature_frame_ms

    for scenario in scenarios:
        decisions = replay(scenario, b1, audio, tmp_path)
        assert len(decisions) == -(-scenario.duration_ms // frame_ms)
        assert all(decision.decider == "silence_threshold" for decision in decisions)
        assert [decision.frame_index for decision in decisions] == list(range(len(decisions)))


def test_replay_is_deterministic(
    scenarios: list[Scenario], b1: SilenceThresholdDecider, tmp_path: Path
) -> None:
    """Hai lần chạy cùng kịch bản phải ra cùng một chuỗi quyết định.

    Không tất định thì mọi khác biệt giữa hai cấu hình lẫn vào nhiễu, và đường cong
    đánh đổi ở pha 0.6 không so sánh được với chính nó.
    """
    audio = load_settings().audio
    for scenario in scenarios:
        first = [d.outcome for d in replay(scenario, b1, audio, tmp_path / "a")]
        second = [d.outcome for d in replay(scenario, b1, audio, tmp_path / "b")]
        assert first == second


def test_replay_writes_one_telemetry_line_per_frame(
    scenarios: list[Scenario], b1: SilenceThresholdDecider, tmp_path: Path
) -> None:
    audio = load_settings().audio
    config = TelemetryConfig(dir=tmp_path / "telemetry", enabled=True)

    for scenario in scenarios:
        with TelemetryCollector(config, "silence_threshold", scenario.name) as collector:
            decisions = replay(scenario, b1, audio, tmp_path, collector=collector)
        lines = collector.path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == len(decisions)


def test_silence_before_any_speech_never_takes_the_turn(
    scenarios: list[Scenario], b1: SilenceThresholdDecider, tmp_path: Path
) -> None:
    """Mọi kịch bản mở đầu bằng im lặng; im lặng không phải bằng chứng lượt đã xong."""
    audio = load_settings().audio
    for scenario in scenarios:
        if scenario.segments[0].kind != "silence":
            continue
        opening_frames = scenario.segments[0].ms // audio.feature_frame_ms
        decisions = replay(scenario, b1, audio, tmp_path)
        assert all(d.outcome is TurnOutcome.HOLD for d in decisions[:opening_frames])


def test_b1_cannot_tell_a_backchannel_from_a_turn(
    scenarios: list[Scenario], b1: SilenceThresholdDecider, tmp_path: Path
) -> None:
    """Ghi lại chỗ B1 hỏng SPEC R4 — đây là kết quả cần đo, không phải lỗi cần vá.

    Kịch bản tiếng đệm có `expected: backchannel`, còn B1 không bao giờ trả
    BACKCHANNEL. Test này chốt lại điều đó để pha 0.6 có chỗ neo con số.
    """
    audio = load_settings().audio
    backchannel = next(s for s in scenarios if s.truth.expected == "backchannel")
    outcomes = {d.outcome for d in replay(backchannel, b1, audio, tmp_path)}
    assert TurnOutcome.BACKCHANNEL not in outcomes
    assert TurnOutcome.TAKE in outcomes
