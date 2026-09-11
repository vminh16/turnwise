"""Chấm điểm phải giữ hai trục đối kháng cạnh nhau (SPEC §9.3 quy tắc 1)."""

import csv
from pathlib import Path

import pytest

from evaluation.metrics import CurvePoint, RunScore, score, summarise, write_curve
from evaluation.scenario import Scenario, Segment, Truth
from turnwise.types import TurnDecision, TurnOutcome


def scenario(turn_end_ms: int | None, expected: str) -> Scenario:
    return Scenario(
        name="fixture",
        spec="SPEC.md §10",
        flow="N2",
        behaviour="fixture",
        summary="fixture",
        speech_dbfs=-14.0,
        noise_floor_dbfs=-60.0,
        segments=(Segment(kind="speech", ms=100),),
        truth=Truth(turn_end_ms=turn_end_ms, expected=expected),  # type: ignore[arg-type]
        path=Path("fixture.yaml"),
    )


def decisions(take_at_ms: int | None, frames: int = 100) -> list[TurnDecision]:
    out = []
    for index in range(frames):
        at_ms = index * 20
        taken = take_at_ms is not None and at_ms >= take_at_ms
        out.append(
            TurnDecision(
                outcome=TurnOutcome.TAKE if taken else TurnOutcome.HOLD,
                decider="silence_threshold",
                frame_index=index,
                at_s=at_ms / 1000,
            )
        )
    return out


def test_a_take_after_the_turn_ends_is_a_latency() -> None:
    result = score(decisions(take_at_ms=1200), scenario(turn_end_ms=1000, expected="take"))
    assert result.interrupted is False
    assert result.response_latency_ms == 200


def test_a_take_before_the_turn_ends_is_an_interruption() -> None:
    """Cắt lời không có độ trễ: bot chen ngang chứ không phải đáp chậm."""
    result = score(decisions(take_at_ms=600), scenario(turn_end_ms=1000, expected="take"))
    assert result.interrupted is True
    assert result.response_latency_ms is None


def test_never_taking_leaves_both_axes_empty() -> None:
    result = score(decisions(take_at_ms=None), scenario(turn_end_ms=1000, expected="take"))
    assert result.take_at_ms is None
    assert result.interrupted is False
    assert result.response_latency_ms is None


def test_only_the_first_take_counts() -> None:
    """Chuỗi TAKE liền nhau là một sự kiện kéo dài, không phải nhiều lần nhận lượt."""
    result = score(decisions(take_at_ms=1200), scenario(turn_end_ms=1000, expected="take"))
    assert result.take_at_ms == 1200


def test_taking_a_backchannel_is_its_own_error() -> None:
    """Kịch bản tiếng đệm không có lượt nào để cắt, nên nó vào mẫu số riêng."""
    result = score(decisions(take_at_ms=1200), scenario(turn_end_ms=None, expected="backchannel"))
    assert result.backchannel_mistaken is True
    assert result.interrupted is False
    assert result.response_latency_ms is None


def test_summary_keeps_the_two_axes_together() -> None:
    scores = [
        RunScore("a", "take", 1000, 1200, False, 200, False),
        RunScore("b", "take", 1000, 600, True, None, False),
        RunScore("c", "take", 1000, 1400, False, 400, False),
        RunScore("d", "backchannel", None, 900, False, None, True),
    ]
    point = summarise(500, scores)

    assert point.threshold_ms == 500
    assert point.interruption_rate == pytest.approx(1 / 3)
    assert point.median_response_latency_ms == pytest.approx(300.0)
    assert point.backchannel_error_rate == pytest.approx(1.0)
    assert point.scenarios == 4


def test_a_curve_row_never_drops_an_axis(tmp_path: Path) -> None:
    """Cắt bớt cột là cách dễ nhất để vô tình báo một trục mà thiếu trục kia."""
    point = CurvePoint(200, 5, 0.25, 180.0, 180.0, 1.0, 0)
    path = write_curve([point], tmp_path / "curve.csv")

    with path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 1
    assert set(rows[0]) == {
        "threshold_ms",
        "scenarios",
        "interruption_rate",
        "median_response_latency_ms",
        "p90_response_latency_ms",
        "backchannel_error_rate",
        "no_response",
    }
