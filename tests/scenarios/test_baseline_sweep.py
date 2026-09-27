"""Dải quét B1 phải chạy đầu-cuối và cho một đường cong có cả hai trục."""

from pathlib import Path

import pytest

from evaluation.metrics import score, summarise
from evaluation.scenario import load_all, replay
from turnwise.config import load_settings
from turnwise.turn.deciders import build

pytestmark = pytest.mark.scenario

BASELINE_CONFIG = "configs/baseline/silence-threshold.yaml"


def test_the_sweep_produces_one_point_per_threshold(tmp_path: Path) -> None:
    settings = load_settings(BASELINE_CONFIG)
    sweep = settings.turn.silence_threshold_sweep_ms
    assert sweep is not None and settings.turn.gate is not None

    scenarios = load_all()
    points = []
    for threshold_ms in sweep:
        decider = build(settings.turn.model_copy(update={"silence_threshold_ms": threshold_ms}))
        scores = [
            score(
                replay(scenario, decider, settings.audio, tmp_path),
                scenario,
                settings.audio.feature_frame_ms,
            )
            for scenario in scenarios
        ]
        points.append(summarise(threshold_ms, scores))

    assert len(points) == len(sweep)
    assert all(point.scenarios == len(scenarios) for point in points)


def test_no_threshold_wins_both_axes(tmp_path: Path) -> None:
    """Luận điểm trung tâm của SPEC §1, đo chứ không phát biểu.

    Ngưỡng hẹp thì cắt lời khách đang ngập ngừng; ngưỡng rộng thì hết cắt lời nhưng
    đáp chậm hơn hẳn, và tới một mức thì có kịch bản bot không đáp gì trong clip.
    """
    settings = load_settings(BASELINE_CONFIG)
    sweep = settings.turn.silence_threshold_sweep_ms
    assert sweep is not None and settings.turn.gate is not None

    scenarios = load_all()
    points = []
    for threshold_ms in sweep:
        decider = build(settings.turn.model_copy(update={"silence_threshold_ms": threshold_ms}))
        scores = [
            score(
                replay(scenario, decider, settings.audio, tmp_path),
                scenario,
                settings.audio.feature_frame_ms,
            )
            for scenario in scenarios
        ]
        points.append(summarise(threshold_ms, scores))

    narrowest, widest = points[0], points[-1]
    assert narrowest.interruption_rate > widest.interruption_rate
    assert narrowest.median_response_latency_ms is not None
    assert widest.median_response_latency_ms is not None
    assert narrowest.median_response_latency_ms < widest.median_response_latency_ms
    assert widest.no_response > narrowest.no_response


def test_b1_mistakes_the_backchannel_at_every_threshold(tmp_path: Path) -> None:
    """Không ngưỡng nào cứu được R4: cổng năng lượng không có trục để phân biệt."""
    settings = load_settings(BASELINE_CONFIG)
    sweep = settings.turn.silence_threshold_sweep_ms
    assert sweep is not None and settings.turn.gate is not None

    backchannel = next(s for s in load_all() if s.truth.expected == "backchannel")
    for threshold_ms in sweep:
        decider = build(settings.turn.model_copy(update={"silence_threshold_ms": threshold_ms}))
        result = score(
            replay(backchannel, decider, settings.audio, tmp_path),
            backchannel,
            settings.audio.feature_frame_ms,
        )
        assert result.backchannel_mistaken is True
