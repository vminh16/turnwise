"""Hình phải mang cả hai trục, hoặc không vẽ."""

from pathlib import Path

import pytest

from evaluation.metrics import CurvePoint

pytest.importorskip("matplotlib", reason="matplotlib nằm trong extra `research`")

from evaluation.figures import plot_tradeoff


def point(threshold_ms: int, latency: float | None, no_response: int = 0) -> CurvePoint:
    return CurvePoint(
        threshold_ms=threshold_ms,
        scenarios=5,
        turn_scenarios=4,
        backchannel_scenarios=1,
        latency_source="file-based",
        interruption_rate=0.25,
        median_response_latency_ms=latency,
        p90_response_latency_ms=latency,
        backchannel_error_rate=1.0,
        no_response=no_response,
    )


def test_writes_a_figure(tmp_path: Path) -> None:
    path = plot_tradeoff(
        [point(200, 180.0), point(900, 880.0, no_response=2)],
        tmp_path / "curve.png",
        "fixture",
    )
    assert path.is_file()
    assert path.stat().st_size > 0


def test_a_point_without_latency_is_not_plotted_half_way(tmp_path: Path) -> None:
    """Không có trục độ trễ thì điểm đó không lên hình, chứ không vẽ mỗi tỉ lệ cắt lời."""
    with pytest.raises(ValueError, match="cả hai trục"):
        plot_tradeoff([point(200, None)], tmp_path / "curve.png", "fixture")
